# 获取模块：从「一个书名」到 `library/<slug>/`

本文件是 `scripts/booklib.py` 的使用说明与来源清单。SKILL.md 描述做什么，这里描述怎么做。

所有命令假定在用户项目根目录执行，书库落在 `./library/`。要换位置就设
`BOOKLIB_ROOT=/path/to/library`。

---

## 来源阶梯

逐级下探，命中即停。上层来源质量更高、歧义更少。

| 级别 | 来源 | 适用 | 命令 |
|---|---|---|---|
| 1 | **用户自有文件** | 用户已买 / 已有 / 自己写的 | `booklib.py add <path>` |
| 2 | **Project Gutenberg** | 公有领域，中英文都有，含中文四大名著 | `booklib.py fetch gutenberg <id>` |
| 2 | **维基文库 Wikisource** | 中文古典，**分回质量最好** | `booklib.py fetch wikisource "<标题>"` |
| 3 | **arXiv** | 预印本论文 | `booklib.py fetch arxiv <id>` |
| 3 | **开放获取 / 官方免费发布** | OA 论文、政府与 NGO 报告、出版社免费全书 | `booklib.py fetch url <url> --rights "..."` |
| 4 | **都没有** | 仍在版权保护期且无免费全文 | 走 SKILL.md 的拒绝口径 |

### 用户自有文件优先于一切

用户已经给了文件路径或附件，就**不要再去搜网络源**。直接：

```bash
python3 scripts/booklib.py add ~/Downloads/book.epub --slug my-book --title "书名"
```

支持 `.txt` / `.epub` / `.html` / `.pdf`。EPUB 会按 spine 顺序抽章；PDF 走
`pdftotext`（优先）或 `pypdf`。

---

## Project Gutenberg

### 检索

```bash
python3 scripts/booklib.py search "红楼梦" --lang zh
python3 scripts/booklib.py search "pride and prejudice" --lang en
```

首次运行会下载官方目录 `pg_catalog.csv`（约 5 MB，8 万条）到 `library/.cache/`，
之后全部离线检索。**不要改用 gutendex.com**：那个 API 在受限网络环境下会返回
Cloudflare 质询页，curl 无法通过。

### 中文的两个坑

**简繁**：用户打「红楼梦」，古登堡目录里存的是「紅樓夢」，直接子串匹配查不到。
`search` 已经通过维基文库的重定向表自动补上繁体变体，所以照常传简体即可。

**同名英译**：搜 "Dream of the Red Chamber" 会命中 #9603/#9604，那是**节译本英文版**，
不是中文原著。用户用中文提问时务必带 `--lang zh`。

### 已验证的中文书号

| ID | 书名 | 备注 |
|---|---|---|
| 24264 | 紅樓夢 | 120 回全，72 万汉字 |
| 23962 | 西遊記 | |
| 23863 | 水滸傳 | |
| 23950 | 三國志演義 | 注意**不叫**「三國演義」，按后者搜不到 |
| 23839 | 論語 | |
| 7337 | 道德經 | |
| 24226 | 史記 | |
| 25202 | 補紅樓夢 | 续书，**不是**原著，别拿错 |

### 下载

```bash
python3 scripts/booklib.py fetch gutenberg 24264 --slug hong-lou-meng
```

依次尝试 `pg<id>.txt` → `pg<id>-images.html` → `.epub`，取第一个成功的，并自动剥掉
Project Gutenberg 的页眉页脚授权文本。

镜像可换（主站限流时有用）：

```bash
GUTENBERG_MIRROR=https://gutenberg.pglaf.org python3 scripts/booklib.py fetch gutenberg 1342
```

---

## 维基文库（中文古典首选）

```bash
python3 scripts/booklib.py fetch wikisource "红楼梦" --slug hong-lou-meng
python3 scripts/booklib.py fetch wikisource "论语" --slug lunyu
python3 scripts/booklib.py fetch wikisource "Walden" --slug walden --lang en
```

相比古登堡的优势：**分回是数据结构，不是靠正则猜的**。维基文库把每一回放在
`紅樓夢/第001回` 这样的子页面上，`fetch` 直接把子页面列表当章节索引
（`chapters.json` 里 `mode: source-toc`），比从正文里认回目稳得多。

三件已经处理好的事，别自己重写：

- **简繁重定向**：传「红楼梦」会自动解析到「紅樓夢」；
- **章节排序**：MediaWiki 返回的链接是按字母序的，不是阅读顺序。已改为按标题里的
  中文序数排（「學而第一」→1，「先進第十一」→11）；
- **聚合页去重**：「全覽」这类把全书塞进一页的子页面会被剔除，否则正文直接翻倍。

用哪个源？**有分回子页面就用维基文库，要单文件全本就用古登堡。** 两个都入库也行，
用不同 slug 区分。

---

## arXiv 与开放获取

```bash
python3 scripts/booklib.py fetch arxiv 1706.03762 --slug attention
```

自动取标题与作者写进 `META.json`。PDF 抽取需要 `pdftotext`（`apt install poppler-utils`）
或 `pip install pypdf`；两个都没有会明确报错——**这时候要如实告诉用户抽不出文本，
不要根据标题和摘要猜论文内容**。

其他 OA 源先自己拿到 PDF 直链，再用 `fetch url`：

```bash
# OpenAlex 找 OA 直链（无需 key）
curl -s "https://api.openalex.org/works?search=<标题>&per-page=1" \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['results'][0]['best_oa_location']['pdf_url'])"

# Europe PMC 全文（无需 key）
curl -s "https://www.ebi.ac.uk/europepmc/webservices/rest/PMC3531190/fullTextXML" -o paper.xml

python3 scripts/booklib.py fetch url "<pdf_url>" --slug some-paper \
        --title "论文标题" --rights "OpenAlex 标记为 OA"
```

`--rights` 一定要填，说明这份为什么可以免费拿到。`META.json` 里留着这行，
下次任何人翻这个书库都知道来源是什么。

---

## 索引校验

下载完必看一眼：

```bash
python3 scripts/booklib.py show <slug> --sections 15
```

`chapters.json` 的 `mode` 有三种：

| mode | 含义 | 可信度 |
|---|---|---|
| `source-toc` | 来源自带目录结构（维基文库子页面） | 最高 |
| `headings` | 从正文里识别出的章节标题 | 高，但要核对总数 |
| `windows` | 没找到章节，退化为每 400 行一段 | 只能保证读取有界，定位不精确 |

**核对总数**：《红楼梦》必须是 120，《水浒传》120 或 70（看版本），
《论语》20 篇。对不上就说明识别歪了。

`mode: windows` 时不要写「第 N 章」这种定位，改用行号（`L8000`）引用，
并在 SUMMARY 的「版本与阅读范围」里说明这个版本没有可识别的章节结构。

识别规则（了解即可，一般不用改）：中文认 `第N回/章/节/卷/篇`，兼容
「第一二零回」逐字式和「第一百二十回」进位式两种写法；英文认 `Chapter/Book/Part N`
与 `3 Model Architecture` 这类编号小标题。所有候选都要通过**序号必须逐一递增**的过滤——
正文换行恰好以「第四回」开头的句子会被这一步剔掉。

---

## 没有合法全文时

按 SKILL.md 的口径拒绝，然后给出路。可以主动提供的替代信息：

- 该书的**公开书评、作者访谈、官方简介**——但产出必须标注「二手资料，未读正文」，
  且**不写入 `library/`**；
- 同主题的公有领域或 OA 替代读物，并说明为什么可比；
- 提醒用户可以通过图书馆借阅或购买正版后，把文件给回来入库。

不做的事：影子图书馆与盗版站、Sci-Hub 一类未授权论文分发、绕过付费墙 / 登录墙 / DRM、
抓取用户未证明有权访问的订阅内容。一句话带过即可，不要说教，也不要暗示存在变通办法。

---

## 命令速查

```bash
booklib.py search "红楼梦" --lang zh              # 找源
booklib.py fetch gutenberg 24264 --slug hlm       # 下载入库（自动建索引）
booklib.py fetch wikisource "红楼梦" --slug hlm
booklib.py fetch arxiv 1706.03762 --slug attn
booklib.py fetch url "<url>" --slug s --rights "" # 官方免费发布 / OA
booklib.py add ./book.epub --slug mine            # 用户自有文件
booklib.py list                                   # 书库总览
booklib.py show hlm --sections 20                 # 元数据 + 章节索引
booklib.py index hlm                              # 重建索引
booklib.py read hlm --chapter 27                  # 读一回
booklib.py read hlm --start 6300 --limit 200      # 读一个行窗口
booklib.py grep hlm "葬花" --max 20               # 检索（输出带章节定位）
```

## 设计出处

存储 + 大纲 + 窗口读取的架构取自
[blazickjp/arxiv-mcp-server](https://github.com/blazickjp/arxiv-mcp-server)（Apache-2.0）；
多来源逐级下探的获取阶梯取自
[sea9401/philosophy-mcp](https://github.com/sea9401/philosophy-mcp)（MIT）。
两者均为适配重写，未直接引入代码。
