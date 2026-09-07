---
name: reading-summary
description: 把一本书真正下载下来读完，产出体系化精读报告，并建成可持续追问的本地书库。当用户说「总结一下红楼梦讲了什么」「帮我读完这本书」「这本书主题是什么」，或给出书名、PDF、EPUB、arXiv 链接要求总结、精读、写读书笔记时使用；也用于对已入库书籍的后续追问（「黛玉葬花在第几回」「再讲讲宝钗」）。流程：用 booklib.py 从 Project Gutenberg、维基文库、arXiv、开放获取或用户自有文件取得正文 → 存入 library/<book-slug>/ 并建章节索引 → 分章精读 → 输出不少于 300–500 字的七段式精读报告 → 后续问答一律回到库中原文并标注章节出处。Use for downloading, deep-reading and summarizing books and papers, and for grounded follow-up Q&A against the local library.
license: MIT
compatibility: 需要 Python 3.8+ 与网络访问（gutenberg.org、wikisource.org、arxiv.org）。PDF 需 pdftotext 或 pypdf；纯文本与 EPUB 无额外依赖。
---

# reading-summary：下载 → 精读 → 入库 → 追问

这个技能的产出不是一段书评，是**一个能长期追问的本地书库**。

一次完整交付包含四件事，缺一件就算没做完：

1. 正文真的下载到了 `library/<slug>/`，`META.json` 记得清出处；
2. 你**读的是这份文件**，不是记忆里的印象、书评或腰封；
3. `SUMMARY.md` 是一份 ≥300–500 字的七段式精读报告，不是要点罗列；
4. 用户下一句追问时，你回到原文定位作答，并给出章节出处。

判断标准很简单：**如果用户关掉对话、明天重开一个新会话，`library/` 里的东西还能让你继续答题，才算成功。**

---

## 工作流

```
用户说「总结一下红楼梦」
      │
      ├─ 0. 库里已有？ ──是──▶ 直接进入「追问模式」（见 references/qa-protocol.md）
      │                          不要重新下载，不要重写 SUMMARY.md
      ▼ 否
  1. 定位来源      booklib.py search "红楼梦" --lang zh
  2. 下载入库      booklib.py fetch gutenberg 24264 --slug hong-lou-meng
  3. 建索引        （fetch 自动完成）show 一眼确认章节数对不对
  4. 分章精读      booklib.py read <slug> --chapter N   ← 真的逐段读
  5. 写 SUMMARY.md 七段式，≥300–500 字
  6. 交付 + 引导   告诉用户书已入库，可以继续追问
```

### 第 0 步：先查库

**每次都先查。** 重复下载一本已有的书是明确的错误。

```bash
python3 scripts/booklib.py list
```

命中已有条目就跳到追问模式；只有用户明说「重新下载 / 换个版本」才重取。

### 第 1 步：定位来源

```bash
python3 scripts/booklib.py search "红楼梦" --lang zh
```

`search` 同时查 Project Gutenberg 与维基文库，并会自动把简体书名映射到繁体标题
（用户打「红楼梦」，古登堡目录里是「紅樓夢」，不做这层映射会直接查不到）。

来源顺序、各源的取舍、以及找不到正文时怎么办，见
**[`references/acquire.md`](references/acquire.md)**。

### 第 2 步：下载入库

```bash
python3 scripts/booklib.py fetch gutenberg 24264 --slug hong-lou-meng
python3 scripts/booklib.py fetch wikisource "紅樓夢" --slug hong-lou-meng
python3 scripts/booklib.py fetch arxiv 1706.03762 --slug attention
python3 scripts/booklib.py fetch url "https://example.org/官方免费全书.pdf" \
        --slug some-book --title "书名" --rights "出版社官网免费发布"
python3 scripts/booklib.py add ~/Downloads/我买的书.epub --slug my-book
```

`--slug` 用小写 ASCII，稳定、好敲、以后追问要用它。

### 第 3 步：确认索引没歪

```bash
python3 scripts/booklib.py show hong-lou-meng --sections 10
```

章节数对不上真实卷回数就停下来查，别硬着头皮往下读——索引歪了，后面所有引用都会错位。
索引质量诊断见 `references/acquire.md` 的「索引校验」。

### 第 4 步：真的去读

长书塞不进上下文，所以按章读、边读边记：

```bash
python3 scripts/booklib.py read hong-lou-meng --chapter 5
python3 scripts/booklib.py read hong-lou-meng --start 8000 --limit 300   # 任意行窗口
python3 scripts/booklib.py grep hong-lou-meng "冷香丸"                    # 带章节定位
```

**读法（map-reduce）**

- 120 回这种体量，不要指望一次读完。先读 `show` 出来的全部章节标题建立骨架
  （章回小说的回目本身就是提纲，信息密度极高）；
- 再按 map-reduce 推进：抽读关键章 → 每章写 2–4 条带定位的笔记进
  `library/<slug>/notes.md` → 最后据笔记归纳，而不是据记忆归纳；
- 至少要真读：开头两章、结尾两章、以及 `grep` 命中的所有关键情节章。抽读多少可以权衡，
  **但抽读范围必须如实写进 SUMMARY.md 的「版本与阅读范围」里**；
- 每写一条笔记就带上 `第N回` 或行号。没有定位的笔记等于没有笔记，后面追问时无法复查。

**硬规则：只要 `library/<slug>/text.txt` 存在，任何结论都必须能在这份文件里找到落点。**
凭印象补进来的内容，就是这个技能唯一真正的失败模式。

### 第 5 步：写 SUMMARY.md

套用七段式框架，写到 `library/<slug>/SUMMARY.md`。

框架全文、字数配比、虚构 / 非虚构分支、以及一份真实样例，见
**[`references/summary-framework.md`](references/summary-framework.md)**。

骨架如下（每段的详细写法以 references 为准）：

| # | 段落 | 篇幅 | 核心要求 |
|---|---|---|---|
| 1 | 一句话主旨 | 40–60 字 | 全书的统一性压成一句。先写这句，它约束后面所有段落 |
| 2 | 结构与脉络 | 80–120 字 | major parts 的顺序与相互关系，不是复述情节 |
| 3 | 人物与关系 | 100–150 字 | 主要人物、动机、变化，以及关系网 |
| 4 | 关键事件与转折 | 80–120 字 | 3–5 个转折点，**每个带章节定位** |
| 5 | 主题与母题 | 100–150 字 | 每个主题走「论点 → 文本证据 → 阐释」 |
| 6 | 读这本书能带走什么 | 60–100 字 | 适合谁读、为什么值得读 |
| 7 | 版本与阅读范围 | 2–3 行 | 出处、版本、实际读了多少 |

必填段落加起来自然落在 500–750 字，长篇经典更多。**300–500 字是地板，不是目标。**

### 第 6 步：交付并引导追问

回复结尾必须告诉用户书已入库、以及可以怎么接着问。这是这个技能的主要价值，
不说用户就不知道能用：

```
《红楼梦》已入库：library/hong-lou-meng/（120 回，72 万字，Project Gutenberg #24264）
接下来可以直接问我，比如：
  · 黛玉葬花在第几回？前后发生了什么？
  · 王熙凤的权力是怎么一步步失去的？
  · 第五回的判词分别对应谁？
```

---

## 追问模式（这个技能的主要价值）

用户对**已入库**的书提问时，不要重新总结，也不要凭记忆答。标准动作：

```bash
python3 scripts/booklib.py grep <slug> "关键词"        # 先定位
python3 scripts/booklib.py read <slug> --chapter N     # 再读原文
```

**先检索，再读，最后答。** 每个事实性回答都要带 `第N回` 之类的定位，让用户能自己复查。
原文里找不到就直说找不到——检索不到不等于可以补脑补。

完整协议（多关键词展开、跨章追踪、答案格式、找不到时的口径）见
**[`references/qa-protocol.md`](references/qa-protocol.md)**。

---

## 书库布局

```
library/
├── .cache/                     # 古登堡目录缓存，可随时删
└── hong-lou-meng/
    ├── META.json               # 出处、版本、校验和、字数、获取时间
    ├── text.txt                # 规范化正文 —— 所有回答的唯一依据
    ├── chapters.json           # 章节索引：序号 / 标题 / 起止行 / 字数
    ├── SUMMARY.md              # 七段式精读报告
    ├── notes.md                # 分章笔记，每条带定位（追问时先看这里）
    └── source/
        └── pg24264.txt         # 原始下载件，不改动
```

`text.txt` 是事实来源，`notes.md` 是你上一轮的工作成果。新会话接手一本书时，
先读 `META.json` + `chapters.json` + `notes.md`，比重读全文快得多。

**不要把下载的正文提交进 git。** 仓库里的 `library/.gitignore` 已经默认忽略书籍内容，
只保留目录结构。

---

## 来源与边界

获取顺序：**用户自有文件 → 公有领域（Project Gutenberg、维基文库）→ 开放获取
（arXiv、PMC、DOAJ、OpenAlex）→ 官方免费发布**。逐级下探，命中即停。详见
[`references/acquire.md`](references/acquire.md)。

不做的事，简短说明即可，不必展开说教：影子图书馆与盗版站、Sci-Hub 一类未授权论文分发、
绕过付费墙 / 登录墙 / DRM、以及抓取用户未证明有权访问的订阅内容。这些路径不写进
`booklib.py`，也不临时用 `curl` 绕开。

**四级都没有正文时**，用这个口径——一句话说明，然后立刻给出路，不要长篇免责：

```
《书名》仍在版权保护期，我没找到可下载的公开全文，所以这本我没法真的读完。

三条路：
1. 你有正版电子版就直接给我文件路径，我入库后照常精读；
2. 有官方样章 / 免费章节的链接也可以，我按实际范围读；
3. 或者我基于公开书评和作者访谈出一版「二手资料概要」——会明确标注我没读过正文，
   而且不会写进 library/ 冒充精读报告。
```

第 3 条的产出必须显著标注「二手资料，未读正文」，**不写入 `SUMMARY.md`**，避免污染书库。

---

## 交付前自检

- [ ] `library/<slug>/` 下 `META.json` / `text.txt` / `chapters.json` / `SUMMARY.md` 齐了？
- [ ] `show` 出来的章节数和这本书真实的卷回数对得上？
- [ ] SUMMARY 七段齐全，且总字数 ≥300–500 字？
- [ ] 第 4 段每个转折点都有章节定位，且定位真的能 `read` 到？
- [ ] 「阅读范围」如实写了抽读了哪些章，没有把抽读说成通读？
- [ ] 第 2+4 段（情节部分）没有超过全文约 40%？超了就是在复述而不是分析。
- [ ] 没有出现原文里查不到的人名、情节、引文？
- [ ] 回复结尾给了具体的追问示例？

---

## 约束

- **不编造。** 人名、情节、页码、引文、章节名，一律以 `text.txt` 为准。
- **不整本复制。** 引用一次一两句并带定位；`SUMMARY.md` 是分析产物，不是原文摘录集。
- **跟随用户语言。** 默认中文，用户用英文就用英文；专名保留原文。
- **不重复劳动。** 库里有就接着用，不要重下、不要覆写既有 `SUMMARY.md`（除非用户要求）。
- **索引可疑就停。** 章节数明显不对时先修索引，不要基于错位的定位继续输出。

---

## 致谢

`scripts/booklib.py` 的架构参考了两个现成的开源项目，均为适配重写而非直接搬运：

- [blazickjp/arxiv-mcp-server](https://github.com/blazickjp/arxiv-mcp-server)（Apache-2.0）——
  持久化存储 + 章节大纲 + 窗口式读取（`resources/papers.py`、`tools/paper_outline.py`）。
  「文献留在磁盘上，按 section 定位读取」这个核心思路来自它。
- [sea9401/philosophy-mcp](https://github.com/sea9401/philosophy-mcp)（MIT）——
  多来源逐级下探的获取阶梯（`src/books.ts`）。本技能把其中的 Gutendex 换成了古登堡官方
  目录 CSV：Gutendex 在受限网络下会撞 Cloudflare 质询页，官方 CSV 下载一次即可离线检索。

许可证：MIT © 2026 KinGao294。使用者需自行确保对所处理内容拥有合法权利。
