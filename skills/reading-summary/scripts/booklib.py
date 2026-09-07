#!/usr/bin/env python3
"""booklib — acquire a book into a local library, index it, read and search it.

Subcommands
-----------
  search   <query>              find candidate sources (Gutenberg catalog + Wikisource)
  fetch    <source> <ref>       download into library/<slug>/ and write META.json
  add      <path>               register a file the user already owns
  index    <slug>               build chapters.json (chapter offsets + titles)
  read     <slug>               print a chapter or a line window
  grep     <slug> <pattern>     regex search, reports chapter locators
  list                          show every book in the library
  show     <slug>               show META.json + index stats for one book

Design credits (adapted, not vendored):
  * Storage/outline/windowed-read architecture follows blazickjp/arxiv-mcp-server
    (Apache-2.0) — resources/papers.py, tools/paper_outline.py.
  * Multi-source acquisition ladder follows sea9401/philosophy-mcp (MIT) — src/books.ts,
    with Gutendex swapped for the Gutenberg catalog CSV, which has no rate limit or
    bot-challenge dependency.

Standard library only. Python 3.8+.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import html
import io
import json
import os
import re
import shutil
import subprocess
import sys
import unicodedata
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

UA = "reading-summary-skill/2.0 (+https://github.com/KinGao294/reading-summary-skill)"
GUTENBERG_MIRROR = os.environ.get("GUTENBERG_MIRROR", "https://www.gutenberg.org")
PG_CATALOG_URL = "https://www.gutenberg.org/cache/epub/feeds/pg_catalog.csv.gz"
WIKISOURCE_LANGS = {"zh": "zh.wikisource.org", "en": "en.wikisource.org"}

csv.field_size_limit(10_000_000)


# --------------------------------------------------------------------------- utils


def log(msg: str) -> None:
    print(msg, file=sys.stderr)


def die(msg: str, code: int = 1) -> "None":
    print(f"error: {msg}", file=sys.stderr)
    raise SystemExit(code)


def http_get(url: str, params: "dict | None" = None, binary: bool = False, timeout: int = 60):
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
    return raw if binary else raw.decode("utf-8", errors="replace")


def library_root() -> Path:
    root = Path(os.environ.get("BOOKLIB_ROOT", "library")).resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def slugify(text: str) -> str:
    """ASCII slug when possible; otherwise pinyin-free fallback keeping CJK readable."""
    text = text.strip()
    ascii_form = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    base = ascii_form if ascii_form.strip() else text
    base = re.sub(r"[^\w\u4e00-\u9fff]+", "-", base, flags=re.UNICODE).strip("-").lower()
    return (base or "book")[:60]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def book_dir(slug: str, create: bool = False) -> Path:
    d = library_root() / slug
    if create:
        (d / "source").mkdir(parents=True, exist_ok=True)
    elif not d.is_dir():
        die(f"no such book in library: {slug}. Run `booklib.py list` to see what is there.")
    return d


def write_meta(d: Path, meta: dict) -> None:
    (d / "META.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_meta(d: Path) -> dict:
    p = d / "META.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def cjk_count(text: str) -> int:
    return sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff")


def finalize(d: Path, meta: dict, sections: "list[dict] | None" = None) -> None:
    """Write text.txt stats into META, then index."""
    text_path = d / "text.txt"
    body = text_path.read_text(encoding="utf-8")
    meta["chars"] = len(body)
    meta["cjk_chars"] = cjk_count(body)
    meta["text_sha256"] = sha256(text_path)
    meta["acquired_at"] = meta.get("acquired_at") or now_iso()
    write_meta(d, meta)
    n = build_index(d, explicit=sections)
    log(f"ok: library/{d.name}/  {meta['chars']:,} chars, {n} sections indexed")
    log(f"    next: booklib.py read {d.name} --chapter 1")


# ------------------------------------------------------------------ text extraction


def strip_html(markup: str) -> str:
    markup = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", "", markup)
    markup = re.sub(r"(?i)<br\s*/?>", "\n", markup)
    markup = re.sub(r"(?i)</(p|div|h[1-6]|li|tr)>", "\n\n", markup)
    markup = re.sub(r"<[^>]+>", "", markup)
    return re.sub(r"\n{3,}", "\n\n", html.unescape(markup)).strip()


def epub_to_text(path: Path) -> str:
    parts = []
    with zipfile.ZipFile(path) as zf:
        names = [n for n in zf.namelist() if n.lower().endswith((".xhtml", ".html", ".htm"))]
        opf = next((n for n in zf.namelist() if n.lower().endswith(".opf")), None)
        if opf:  # honour spine order when we can
            spine = re.findall(r'idref="([^"]+)"', zf.read(opf).decode("utf-8", "replace"))
            ids = dict(re.findall(r'id="([^"]+)"[^>]*href="([^"]+)"', zf.read(opf).decode("utf-8", "replace")))
            base = os.path.dirname(opf)
            ordered = [os.path.normpath(os.path.join(base, ids[i])) for i in spine if i in ids]
            names = [n for n in ordered if n in zf.namelist()] or names
        for name in names:
            parts.append(strip_html(zf.read(name).decode("utf-8", "replace")))
    return "\n\n".join(p for p in parts if p.strip())


def pdf_to_text(path: Path) -> str:
    if shutil.which("pdftotext"):
        out = subprocess.run(
            ["pdftotext", "-layout", "-enc", "UTF-8", str(path), "-"],
            capture_output=True, text=True,
        )
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout
    try:
        import pypdf  # type: ignore

        reader = pypdf.PdfReader(str(path))
        text = "\n\n".join((page.extract_text() or "") for page in reader.pages)
        if text.strip():
            return text
    except Exception:
        pass
    die(
        f"cannot extract text from {path.name}. Install poppler-utils (`pdftotext`) or "
        "`pip install pypdf`. If the PDF is image-only it has no text layer and needs OCR — "
        "say so instead of guessing at the contents."
    )
    return ""


def any_to_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".epub":
        return epub_to_text(path)
    if suffix == ".pdf":
        return pdf_to_text(path)
    if suffix in {".html", ".htm", ".xhtml"}:
        return strip_html(path.read_text(encoding="utf-8", errors="replace"))
    return path.read_text(encoding="utf-8", errors="replace")


def normalize(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\u3000", "  ")
    return re.sub(r"\n{4,}", "\n\n\n", text).strip() + "\n"


def strip_gutenberg_boilerplate(text: str) -> str:
    start = re.search(r"\*\*\* ?START OF (THE|THIS) PROJECT GUTENBERG EBOOK.*?\*\*\*", text)
    end = re.search(r"\*\*\* ?END OF (THE|THIS) PROJECT GUTENBERG EBOOK.*?\*\*\*", text)
    body = text[start.end() if start else 0 : end.start() if end else len(text)]
    return body.strip()


# ------------------------------------------------------------------ chapter indexing

CN_DIGITS = {"零": 0, "〇": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4,
             "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
ROMAN = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}


def parse_cn_number(s: str) -> "int | None":
    """Handles both 一百二十 (positional) and 一二零 (digit-by-digit) styles."""
    s = s.strip()
    if not s:
        return None
    if s.isdigit():
        return int(s)
    if not any(u in s for u in "十百千") and all(c in CN_DIGITS for c in s):
        return int("".join(str(CN_DIGITS[c]) for c in s))
    total, section, digit = 0, 0, 0
    for ch in s:
        if ch in CN_DIGITS:
            digit = CN_DIGITS[ch]
        elif ch == "十":
            section += (digit or 1) * 10
            digit = 0
        elif ch == "百":
            section += (digit or 1) * 100
            digit = 0
        elif ch == "千":
            section += (digit or 1) * 1000
            digit = 0
        else:
            return None
    return total + section + digit or None


def parse_roman(s: str) -> "int | None":
    s = s.upper()
    if not s or any(c not in ROMAN for c in s):
        return None
    total, prev = 0, 0
    for ch in reversed(s):
        val = ROMAN[ch]
        total = total - val if val < prev else total + val
        prev = max(prev, val)
    return total or None


CN_HEAD = re.compile(r"^\s{0,4}(第\s*([零〇一二三四五六七八九十百千两0-9]{1,8})\s*([回章節节卷篇折出]))\s*(.{0,60})$")
EN_HEAD = re.compile(r"^\s{0,4}((?:CHAPTER|Chapter|BOOK|Book|PART|Part|SECTION|Section)\s+"
                     r"([0-9]{1,4}|[IVXLCDMivxlcdm]{1,8})\b)\.?\s*(.{0,80})$")
# "3 Model Architecture" — the ascending-run filter below discards numeric noise
NUM_HEAD = re.compile(r"^\s{0,3}(([0-9]{1,2})\.?)\s+([A-Z][A-Za-z][^.]{2,70})$")


SEPARATOR = re.compile(r"^[\s\-=_*~—─·.]+$")


def lookahead_title(lines: "list[str]", i: int, span: int = 8) -> str:
    """Many editions put 第三回 on its own line and the couplet a few lines below."""
    for line in lines[i + 1 : i + 1 + span]:
        text = line.strip()
        if not text or SEPARATOR.match(text):
            continue
        if CN_HEAD.match(line) or EN_HEAD.match(line):
            break
        return text[:70] if len(text) <= 70 else ""
    return ""


def find_headings(lines: "list[str]") -> "list[dict]":
    """Candidate headings, then keep the longest run whose numbers ascend.

    Prose that wraps onto a line starting with 第四回 looks exactly like a heading;
    requiring the sequence to ascend by one is what filters those out.
    """
    cands = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or len(stripped) > 90:
            continue
        m = CN_HEAD.match(line)
        if m:
            num = parse_cn_number(m.group(2))
            if num:
                caption = m.group(4).strip() or lookahead_title(lines, i)
                cands.append({"line": i, "num": num, "unit": m.group(3),
                              "title": f"{m.group(1)} {caption}".strip()})
            continue
        m = EN_HEAD.match(line)
        if m:
            token = m.group(2)
            num = int(token) if token.isdigit() else parse_roman(token)
            if num:
                caption = m.group(3).strip() or lookahead_title(lines, i)
                cands.append({"line": i, "num": num, "unit": "chapter",
                              "title": f"{m.group(1)} {caption}".strip()})
            continue
        m = NUM_HEAD.match(line)
        if m:
            cands.append({"line": i, "num": int(m.group(2)), "unit": "numbered",
                          "title": f"{m.group(2)} {m.group(3).strip()}"})
    if not cands:
        return []

    units = {}
    for c in cands:
        units.setdefault(c["unit"], []).append(c)
    best: "list[dict]" = []
    for group in units.values():
        chain: "list[dict]" = []
        for c in group:
            if not chain:
                if c["num"] <= 1:
                    chain = [c]
                continue
            if c["num"] == chain[-1]["num"] + 1:
                chain.append(c)
            elif c["num"] == chain[-1]["num"]:
                continue  # duplicate heading (table of contents echo)
        if len(chain) > len(best):
            best = chain
    return best


def build_index(d: Path, explicit: "list[dict] | None" = None) -> int:
    text = (d / "text.txt").read_text(encoding="utf-8")
    lines = text.split("\n")
    heads = [] if explicit else find_headings(lines)

    sections = []
    if explicit:
        sections = explicit
    elif len(heads) >= 3:
        if heads[0]["line"] > 20:
            sections.append({"n": 0, "title": "前言/序（正文前）", "start_line": 1,
                             "end_line": heads[0]["line"]})
        for idx, h in enumerate(heads):
            end = heads[idx + 1]["line"] if idx + 1 < len(heads) else len(lines)
            sections.append({"n": h["num"], "title": h["title"],
                             "start_line": h["line"] + 1, "end_line": end})
    else:  # no usable headings — fall back to fixed windows so reads stay bounded
        step = 400
        for idx, start in enumerate(range(0, len(lines), step), start=1):
            sections.append({"n": idx, "title": f"（无章节标题）片段 {idx}",
                             "start_line": start + 1,
                             "end_line": min(start + step, len(lines))})

    for s in sections:
        s["end_line"] = min(s["end_line"], len(lines))
        body = "\n".join(lines[s["start_line"] - 1 : s["end_line"]])
        s["chars"] = len(body)
    mode = "source-toc" if explicit else ("headings" if len(heads) >= 3 else "windows")
    payload = {"slug": d.name, "built_at": now_iso(), "mode": mode, "sections": sections}
    (d / "chapters.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                                     encoding="utf-8")
    return len(sections)


def load_index(d: Path) -> dict:
    p = d / "chapters.json"
    if not p.exists():
        build_index(d)
    return json.loads(p.read_text(encoding="utf-8"))


def locate(index: dict, line_no: int) -> str:
    for s in index["sections"]:
        if s["start_line"] <= line_no <= s["end_line"]:
            return s["title"]
    return "?"


# ------------------------------------------------------------------------- sources


def pg_catalog() -> Path:
    """Gutenberg's own catalog dump, cached locally. ~80k rows, offline search."""
    cache = library_root() / ".cache"
    cache.mkdir(parents=True, exist_ok=True)
    path = cache / "pg_catalog.csv"
    if not path.exists() or path.stat().st_size < 1_000_000:
        log("fetching Project Gutenberg catalog (once, ~5 MB) ...")
        blob = http_get(PG_CATALOG_URL, binary=True, timeout=180)
        path.write_bytes(gzip.decompress(blob))
    return path


def pg_search(query: str, lang: "str | None" = None, limit: int = 10) -> "list[dict]":
    q = query.lower()
    hits = []
    with pg_catalog().open(encoding="utf-8", errors="replace", newline="") as fh:
        for row in csv.DictReader(fh):
            if lang and row.get("Language", "") != lang:
                continue
            title = row.get("Title", "")
            if q in title.lower() or q in row.get("Authors", "").lower():
                hits.append({"id": row["Text#"], "title": title.replace("\n", " "),
                             "author": row.get("Authors", ""), "lang": row.get("Language", "")})
                if len(hits) >= limit:
                    break
    return hits


def pg_fetch(text_id: str, slug: "str | None") -> None:
    text_id = str(text_id).strip()
    urls = [f"{GUTENBERG_MIRROR}/cache/epub/{text_id}/pg{text_id}.txt",
            f"{GUTENBERG_MIRROR}/cache/epub/{text_id}/pg{text_id}-images.html",
            f"{GUTENBERG_MIRROR}/ebooks/{text_id}.epub.noimages"]
    title = next((h["title"] for h in pg_search("", limit=0)), "")  # placeholder, filled below
    meta_row = None
    with pg_catalog().open(encoding="utf-8", errors="replace", newline="") as fh:
        for row in csv.DictReader(fh):
            if row["Text#"] == text_id:
                meta_row = row
                break
    if meta_row:
        title = meta_row.get("Title", "").replace("\n", " ")
    slug = slug or slugify(title or f"pg{text_id}")
    d = book_dir(slug, create=True)

    last_err = None
    for url in urls:
        try:
            log(f"downloading {url}")
            blob = http_get(url, binary=True, timeout=180)
        except Exception as exc:  # try the next format
            last_err = exc
            continue
        ext = ".txt" if url.endswith(".txt") else (".html" if url.endswith(".html") else ".epub")
        raw_path = d / "source" / f"pg{text_id}{ext}"
        raw_path.write_bytes(blob)
        body = any_to_text(raw_path)
        body = strip_gutenberg_boilerplate(body)
        (d / "text.txt").write_text(normalize(body), encoding="utf-8")
        finalize(d, {
            "title": title or slug, "author": (meta_row or {}).get("Authors", ""),
            "language": (meta_row or {}).get("Language", ""),
            "source": "project-gutenberg", "source_url": url,
            "source_id": text_id, "rights": "public domain in the US (Project Gutenberg License)",
            "acquisition": "downloaded", "source_file": f"source/{raw_path.name}",
            "source_sha256": sha256(raw_path),
        })
        return
    die(f"no downloadable format for Gutenberg #{text_id}: {last_err}")


def ws_api(lang: str, params: dict) -> dict:
    host = WIKISOURCE_LANGS.get(lang)
    if not host:
        die(f"unsupported wikisource language: {lang}")
    params = {"format": "json", "formatversion": "2", **params}
    return json.loads(http_get(f"https://{host}/w/api.php", params))


def ws_resolve(lang: str, title: str) -> str:
    """Follow redirects — users type 红楼梦, the pages live at 紅樓夢."""
    data = ws_api(lang, {"action": "query", "titles": title, "redirects": "1"})
    pages = data.get("query", {}).get("pages", [])
    if pages and not pages[0].get("missing"):
        return pages[0]["title"]
    hits = ws_api(lang, {"action": "query", "list": "search", "srsearch": title, "srlimit": "5"})
    results = hits.get("query", {}).get("search", [])
    if not results:
        die(f"wikisource has no page for {title!r}")
    log(f"exact title not found; using best search hit: {results[0]['title']}")
    return results[0]["title"]


def ws_extract(lang: str, title: str) -> str:
    data = ws_api(lang, {"action": "query", "prop": "extracts", "explaintext": "1",
                         "titles": title, "redirects": "1"})
    pages = data.get("query", {}).get("pages", [])
    return pages[0].get("extract", "") if pages else ""


WS_AGGREGATE = {"全覽", "全览", "全文", "目錄", "目录", "索引", "序言目錄"}
WS_ORDINAL = re.compile(r"第\s*([零〇一二三四五六七八九十百千0-9]{1,8})")


def ws_order_subpages(root_title: str, subpages: "list[str]") -> "list[str]":
    """The API returns links alphabetically. Chapter ordinals give the true reading order."""
    leaves = [(s, s.split("/", 1)[1]) for s in subpages]
    keyed = []
    for full, leaf in leaves:
        m = WS_ORDINAL.search(leaf)
        keyed.append((parse_cn_number(m.group(1)) if m else None, full))
    if sum(1 for k, _ in keyed if k is not None) >= max(3, int(0.8 * len(keyed))):
        return [full for _, full in sorted(keyed, key=lambda kv: (kv[0] is None, kv[0] or 0, kv[1]))]
    return subpages


def ws_fetch(title: str, slug: "str | None", lang: str = "zh") -> None:
    root_title = ws_resolve(lang, title)
    links = ws_api(lang, {"action": "parse", "page": root_title, "prop": "links"})
    subpages = sorted({
        l["title"] for l in links.get("parse", {}).get("links", [])
        if l.get("ns") == 0 and l["title"].startswith(root_title + "/") and not l.get("missing")
        and l["title"].split("/", 1)[1] not in WS_AGGREGATE
    })
    subpages = ws_order_subpages(root_title, subpages)
    slug = slug or slugify(root_title)
    d = book_dir(slug, create=True)

    chunks, sections, cursor = [], [], 1
    if subpages:
        log(f"{root_title}: {len(subpages)} subpages")
        for i, sub in enumerate(subpages, 1):
            body = ws_extract(lang, sub)
            if not body.strip():
                continue
            heading = sub.split("/", 1)[1]
            chunk = f"{heading}\n\n{body}"
            chunks.append(chunk)
            span = chunk.count("\n") + 1
            # subpages ARE the table of contents; no need to re-derive it from prose
            sections.append({"n": len(sections) + 1, "title": heading,
                             "start_line": cursor, "end_line": cursor + span - 1})
            cursor += span + 3  # the "\n\n\n" join between chunks
            if i % 20 == 0:
                log(f"  {i}/{len(subpages)}")
    else:
        chunks.append(ws_extract(lang, root_title))
    if not any(c.strip() for c in chunks):
        die(f"wikisource returned no text for {root_title}")

    joined = "\n\n\n".join(chunks)
    raw_path = d / "source" / f"{slugify(root_title)}.wikisource.txt"
    raw_path.write_text(joined, encoding="utf-8")
    (d / "text.txt").write_text(normalize(joined), encoding="utf-8")
    finalize(d, {
        "title": root_title, "author": "", "language": lang,
        "source": "wikisource", "source_url": f"https://{WIKISOURCE_LANGS[lang]}/wiki/"
                                              f"{urllib.parse.quote(root_title)}",
        "source_id": root_title, "rights": "CC BY-SA 4.0 (wiki text); underlying work public domain",
        "acquisition": "downloaded", "source_file": f"source/{raw_path.name}",
        "source_sha256": sha256(raw_path), "subpages": len(subpages),
    }, sections=sections or None)


def arxiv_fetch(paper_id: str, slug: "str | None") -> None:
    paper_id = paper_id.strip().replace("arxiv:", "").replace("https://arxiv.org/abs/", "")
    feed = http_get("http://export.arxiv.org/api/query",
                    {"id_list": paper_id, "max_results": "1"})
    title = re.search(r"<title>(.*?)</title>", feed, re.S)
    titles = re.findall(r"<title>(.*?)</title>", feed, re.S)
    title = html.unescape(re.sub(r"\s+", " ", titles[1]).strip()) if len(titles) > 1 else paper_id
    authors = [html.unescape(a.strip()) for a in re.findall(r"<name>(.*?)</name>", feed, re.S)]
    slug = slug or slugify(title)
    d = book_dir(slug, create=True)
    url = f"https://arxiv.org/pdf/{paper_id}"
    log(f"downloading {url}")
    raw_path = d / "source" / f"{paper_id.replace('/', '_')}.pdf"
    raw_path.write_bytes(http_get(url, binary=True, timeout=180))
    (d / "text.txt").write_text(normalize(any_to_text(raw_path)), encoding="utf-8")
    finalize(d, {
        "title": title, "author": ", ".join(authors[:8]), "language": "en",
        "source": "arxiv", "source_url": f"https://arxiv.org/abs/{paper_id}",
        "source_id": paper_id, "rights": "open access (see arXiv license on the abstract page)",
        "acquisition": "downloaded", "source_file": f"source/{raw_path.name}",
        "source_sha256": sha256(raw_path),
    })


def url_fetch(url: str, slug: "str | None", title: str = "", rights: str = "") -> None:
    """For an official free release or an OA PDF whose URL you already have."""
    name = os.path.basename(urllib.parse.urlparse(url).path) or "download"
    if "." not in name:
        name += ".html"
    slug = slug or slugify(title or os.path.splitext(name)[0])
    d = book_dir(slug, create=True)
    log(f"downloading {url}")
    raw_path = d / "source" / name
    raw_path.write_bytes(http_get(url, binary=True, timeout=180))
    (d / "text.txt").write_text(normalize(any_to_text(raw_path)), encoding="utf-8")
    finalize(d, {
        "title": title or os.path.splitext(name)[0], "author": "", "language": "",
        "source": "direct-url", "source_url": url, "source_id": "",
        "rights": rights or "UNVERIFIED — record why this copy is available at no cost",
        "acquisition": "downloaded", "source_file": f"source/{name}",
        "source_sha256": sha256(raw_path),
    })


def add_local(path_str: str, slug: "str | None", title: str = "") -> None:
    src = Path(path_str).expanduser()
    if not src.is_file():
        die(f"no such file: {src}")
    slug = slug or slugify(title or src.stem)
    d = book_dir(slug, create=True)
    raw_path = d / "source" / src.name
    shutil.copy2(src, raw_path)
    (d / "text.txt").write_text(normalize(any_to_text(raw_path)), encoding="utf-8")
    finalize(d, {
        "title": title or src.stem, "author": "", "language": "",
        "source": "user-provided", "source_url": "", "source_id": "",
        "rights": "user states they hold a copy", "acquisition": "user-supplied file",
        "source_file": f"source/{src.name}", "source_sha256": sha256(raw_path),
        "original_path": str(src),
    })


# -------------------------------------------------------------------------- reading


def cmd_read(args) -> None:
    d = book_dir(args.slug)
    index = load_index(d)
    lines = (d / "text.txt").read_text(encoding="utf-8").split("\n")
    if args.chapter is not None:
        matches = [s for s in index["sections"] if s["n"] == args.chapter]
        if not matches:
            die(f"no section numbered {args.chapter}; "
                f"index has {len(index['sections'])} sections (see `booklib.py show {args.slug}`)")
        sec = matches[0]
        start, end = sec["start_line"], sec["end_line"]
        header = f"[{args.slug}] {sec['title']}  (lines {start}-{end}, {sec['chars']:,} chars)"
    else:
        start = max(1, args.start)
        end = min(len(lines), start + args.limit - 1)
        header = f"[{args.slug}] lines {start}-{end} — {locate(index, start)}"
    print(header)
    print("-" * len(header))
    print("\n".join(lines[start - 1 : end]))


def cmd_grep(args) -> None:
    d = book_dir(args.slug)
    index = load_index(d)
    lines = (d / "text.txt").read_text(encoding="utf-8").split("\n")
    pattern = re.compile(args.pattern, 0 if args.case_sensitive else re.IGNORECASE)
    shown = 0
    for i, line in enumerate(lines, 1):
        if pattern.search(line):
            print(f"{locate(index, i)} | L{i}: {line.strip()[:200]}")
            shown += 1
            if shown >= args.max:
                print(f"... (stopped at {args.max} hits; narrow the pattern or raise --max)")
                break
    if not shown:
        print(f"no match for {args.pattern!r} in {args.slug}")


def cmd_list(args) -> None:
    root = library_root()
    books = sorted(p for p in root.iterdir() if p.is_dir() and not p.name.startswith("."))
    if not books:
        print(f"library is empty ({root})")
        return
    for d in books:
        meta = read_meta(d)
        flags = []
        if (d / "SUMMARY.md").exists():
            flags.append("SUMMARY")
        if (d / "notes.md").exists():
            flags.append("notes")
        print(f"{d.name:<28} {meta.get('title', '?')[:38]:<40} "
              f"{meta.get('chars', 0):>9,} chars  {meta.get('source', '?'):<18} {' '.join(flags)}")


def cmd_show(args) -> None:
    d = book_dir(args.slug)
    print(json.dumps(read_meta(d), ensure_ascii=False, indent=2))
    index = load_index(d)
    secs = index["sections"]
    print(f"\nindex: {len(secs)} sections (mode={index['mode']})")
    for s in secs[: args.sections]:
        print(f"  {s['n']:>4}  {s['title'][:60]:<62} {s['chars']:>8,} chars")
    if len(secs) > args.sections:
        print(f"  ... {len(secs) - args.sections} more (raise --sections)")


def title_variants(query: str, lang: "str | None") -> "list[str]":
    """Users type 红楼梦; catalogs hold 紅樓夢. Wikisource's redirect table bridges the two."""
    variants = [query]
    if lang in (None, "zh") and any("\u4e00" <= c <= "\u9fff" for c in query):
        try:
            resolved = ws_resolve("zh", query)
            if resolved and resolved != query:
                variants.append(resolved)
        except SystemExit:
            pass
        except Exception:
            pass
    return variants


def cmd_search(args) -> None:
    print("== Project Gutenberg ==")
    hits, seen = [], set()
    for variant in title_variants(args.query, args.lang):
        for h in pg_search(variant, lang=args.lang, limit=args.limit):
            if h["id"] not in seen:
                seen.add(h["id"])
                hits.append(h)
    if hits:
        for h in hits:
            print(f"  id={h['id']:<7} [{h['lang']}] {h['title'][:60]}  — {h['author'][:34]}")
        print(f"  fetch with: booklib.py fetch gutenberg {hits[0]['id']}")
    else:
        print("  no match")
    if args.lang in (None, "zh", "en"):
        lang = args.lang or "zh"
        print(f"\n== Wikisource ({lang}) ==")
        try:
            res = ws_api(lang, {"action": "query", "list": "search",
                                "srsearch": args.query, "srlimit": str(args.limit)})
            items = res.get("query", {}).get("search", [])
            for it in items:
                print(f"  {it['title']}")
            if items:
                print(f"  fetch with: booklib.py fetch wikisource '{items[0]['title']}' --lang {lang}")
            else:
                print("  no match")
        except Exception as exc:
            print(f"  unavailable: {exc}")


def cmd_fetch(args) -> None:
    if args.source == "gutenberg":
        pg_fetch(args.ref, args.slug)
    elif args.source == "wikisource":
        ws_fetch(args.ref, args.slug, args.lang or "zh")
    elif args.source == "arxiv":
        arxiv_fetch(args.ref, args.slug)
    elif args.source == "url":
        url_fetch(args.ref, args.slug, args.title, args.rights)
    else:
        die(f"unknown source: {args.source}")


def cmd_index(args) -> None:
    d = book_dir(args.slug)
    print(f"{build_index(d)} sections indexed -> library/{args.slug}/chapters.json")


def main() -> None:
    p = argparse.ArgumentParser(prog="booklib.py", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("search", help="find candidate sources")
    s.add_argument("query")
    s.add_argument("--lang", help="filter by language code, e.g. zh / en")
    s.add_argument("--limit", type=int, default=10)
    s.set_defaults(func=cmd_search)

    s = sub.add_parser("fetch", help="download into the library")
    s.add_argument("source", choices=["gutenberg", "wikisource", "arxiv", "url"])
    s.add_argument("ref", help="Gutenberg id / Wikisource page title / arXiv id / URL")
    s.add_argument("--slug")
    s.add_argument("--lang", help="wikisource language (default zh)")
    s.add_argument("--title", default="", help="for `url`: human title")
    s.add_argument("--rights", default="", help="for `url`: why this copy is free")
    s.set_defaults(func=cmd_fetch)

    s = sub.add_parser("add", help="register a file the user already owns")
    s.add_argument("path")
    s.add_argument("--slug")
    s.add_argument("--title", default="")
    s.set_defaults(func=lambda a: add_local(a.path, a.slug, a.title))

    s = sub.add_parser("index", help="rebuild chapters.json")
    s.add_argument("slug")
    s.set_defaults(func=cmd_index)

    s = sub.add_parser("read", help="print one chapter or a line window")
    s.add_argument("slug")
    s.add_argument("--chapter", type=int)
    s.add_argument("--start", type=int, default=1)
    s.add_argument("--limit", type=int, default=400)
    s.set_defaults(func=cmd_read)

    s = sub.add_parser("grep", help="regex search with chapter locators")
    s.add_argument("slug")
    s.add_argument("pattern")
    s.add_argument("--max", type=int, default=40)
    s.add_argument("--case-sensitive", action="store_true")
    s.set_defaults(func=cmd_grep)

    s = sub.add_parser("list", help="show the library")
    s.set_defaults(func=cmd_list)

    s = sub.add_parser("show", help="metadata + chapter index for one book")
    s.add_argument("slug")
    s.add_argument("--sections", type=int, default=25)
    s.set_defaults(func=cmd_show)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
