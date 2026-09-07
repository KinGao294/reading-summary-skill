<h1 align="center">reading-summary-skill</h1>

<p align="center">
  <b>读完一本书，只留一页纸。</b><br>
  给 Agent 一个<b>合法</b> PDF，换回「1 主旨 / 5 要点 / 3 行动 / 1 存疑」。
</p>

<p align="center">
  <a href="LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/License-MIT-yellow.svg"></a>
  <img alt="Legal-first" src="https://img.shields.io/badge/policy-legal--first-brightgreen.svg">
  <a href="skills/reading-summary/SKILL.md"><img alt="Agent Skill" src="https://img.shields.io/badge/agent%20skill-reading--summary-blue.svg"></a>
</p>

---

## 30 秒看懂

大多数 AI 读书笔记的问题不是太短，是**太全**——把目录复述一遍，读完等于没读。

这个技能反着来：**粗放、有损、能用**。它逼 Agent 做取舍，只交付四样东西：

| | 内容 | 为什么是它 |
|---|---|---|
| **1 主旨** | 一句话，能被反驳的那种 | 说不出一句话，就是没读懂 |
| **5 要点** | 撑起论证的承重墙 | 不是五个金句，是五个支点 |
| **3 行动** | 下周一就能做 | 「要更系统地思考」不算行动 |
| **1 存疑** | 这本书最脆的地方 | 没有存疑的笔记只是腰封 |

配额是硬的。5 就是 5，3 就是 3。删不下去，说明还在复述。

## 它做什么 / 不做什么

**做：**

- 从你自己的文件、公有领域、开放获取（OA）、官方免费发布里拿到正文
- 读脊梁不读大纲：主张、承重论点、证据类型、相信它的代价
- 输出一页纸的笔记，标注来源与阅读范围（全书 / 前四章 / 仅摘要）

**不做：**

- 不逐章复述，不生成"内容丰富、值得一读"这类空话
- 不编造页码、引文、研究结论、章节名
- 不搬运原文——短引用带定位，绝不复现大段受版权保护的内容
- **不碰任何盗版路径**（见下方红线）

## 输出长什么样

以《思考，快与慢》为例，来源为**用户自有电子书**。

<table>
<tr><th width="50%">❌ 通常你会拿到</th><th width="50%">✅ 这个技能给你</th></tr>
<tr valign="top"><td>

> 本书由诺贝尔奖得主卡尼曼所著，系统阐述了人类思维的两套系统。第一部分介绍系统 1 与系统 2，第二部分讨论启发式与偏差，第三部分……全书内容丰富，案例翔实，是行为经济学领域的经典之作，值得每一位读者细细品读。

*读完之后，你依然不知道明天该改变什么。*

</td><td>

**主旨**：多数判断失误不是因为系统 1 太蠢，而是因为系统 2 太懒——它常常不去核验，只负责为直觉背书。

**5 要点**（节选 2 条）
1. **锚定**——先出现的数字会污染后续估计，哪怕明知它随机无关。
2. **回归均值**——被误读成因果，于是"批评有效、表扬有害"这类结论被反复生产。

**3 行动**（节选 1 条）
- [ ] 谈判前先写下自己的报价区间，再看对方开价——把锚定挡在门外。

**存疑**：书中社会启动（priming）相关研究在复制危机中大面积翻车，作者本人 2017 年公开承认该章证据薄弱。读第 4 章时打折。

</td></tr>
</table>

> 上表为格式示例，非逐字输出；真实笔记会带来源与阅读范围标注。

## 安装

技能只有一个文件：[`skills/reading-summary/SKILL.md`](skills/reading-summary/SKILL.md)。

```bash
git clone https://github.com/KinGao294/reading-summary-skill.git
```

放到你的 Agent 能发现的目录：

| 环境 | 位置 |
|---|---|
| **Cursor（个人）** | `~/.cursor/skills/reading-summary/SKILL.md` |
| **Cursor（项目）** | `<repo>/.cursor/skills/reading-summary/SKILL.md` |
| **Grok Bot / 其他** | 你的 skills 目录，或直接把全文粘进 system prompt |

```bash
mkdir -p ~/.cursor/skills/reading-summary
cp skills/reading-summary/SKILL.md ~/.cursor/skills/reading-summary/
```

文件头部的 YAML `description` 决定了 Agent 何时自动调用它——别删。不支持 skills 机制的工具，把 SKILL.md 全文当提示词贴进去也能用。

## 怎么用

装好之后，正常说话即可：

```
帮我读一下这个 PDF，出个读书笔记            （附件）
《XXX》我有正版 epub，总结成一页纸           （附件）
arxiv.org/abs/1706.03762 这篇，5 个要点讲清楚
这本书值不值得读？先给我主旨和存疑
```

想改口径，直接说：`只读前三章` / `行动项换成团队视角` / `用英文输出`。

## 合法红线

这条线不接受"就这一次"。

**✅ 走这四条路**

1. 你自己的文件——附件、本地路径、买过的、自己写的
2. 公有领域与开放获取——Project Gutenberg、arXiv、PMC、DOAJ、机构仓储、政府与 NGO 报告
3. 官方免费发布——作者主页、出版社样章、公司白皮书、会议论文集
4. 都没有？那就明说没有，并给出图书馆 / 馆际互借 / 正版购买的替代路径

**❌ 一律不做**

- 盗版库、影子图书馆、破解电子书、种子站
- Sci-Hub 及同类服务——**没有"默认关闭"，也没有"用户说合法就开"**
- 绕过付费墙、登录墙、DRM、频率限制
- 抓取用户未证明拥有访问权的订阅内容

拿不到正文时，技能会退到「摘要 + 公开书评 + 作者演讲」并**明确标注阅读范围**，而不是假装读过全书。版权合规的最终责任在使用者。

## 为什么会有这个东西

三个让人恼火的现实：

1. **模型倾向于讨好，不倾向于取舍。** 不给硬配额，它就把所有章节都塞给你，因为那样不会出错。
2. **大多数"总结"没有立场。** 没有主旨就无从反驳，没有存疑就等于软广。
3. **多数读书工具对来源装糊涂。** 与其事后免责，不如把合法性写进第一步。

所以这里的设计就三句话：**先合法拿到正文，再强制取舍，最后必须留一处怀疑。**

## FAQ

**Q：只有摘要，没有全文，还能用吗？**
能。技能会基于摘要和公开材料输出，并在「阅读范围」里写清楚是摘要级，不冒充读完。

**Q：为什么必须有「1 存疑」？**
因为它是唯一防止笔记退化成推荐语的结构。书真的很扎实，就去质疑它的适用边界。

**Q：能出英文笔记吗？**
能。默认跟随你的提问语言，也可以直接指定。

**Q：论文、财报、行研报告能用吗？**
能，任何长文档都行。OA 论文反而是最省事的场景。

**Q：能改成 10 要点 / 5 行动吗？**
能，但先按 5/3 跑一遍。配额带来的痛苦就是这个技能的价值本身。

**Q：会读扫描件吗？**
取决于你的 Agent 有没有 OCR。纯图片 PDF 抽不出文本，效果会明显变差。

**Q：需要联网 / API Key 吗？**
不需要。这是一个 Markdown 提示词文件，能力全部来自你的 Agent。

## 参与

Issue 和 PR 都欢迎，尤其是：让输出更狠的措辞、更多合法来源清单、其他 Agent 平台的安装说明。不接受任何形式的盗版获取逻辑。

## License

[MIT](LICENSE) © 2026 KinGao294

开源不等于免责：使用者需自行确保对所处理内容拥有合法权利。

---

# English

**Give the agent one legally obtained PDF, get back one page: 1 thesis / 5 points / 3 actions / 1 doubt.**

## The idea

Most AI book summaries fail by being *complete*, not by being short — they replay the table of
contents and leave you with nothing to do. This skill forces the opposite: coarse, lossy, usable.

| | What | Why |
|---|---|---|
| **1 thesis** | One sentence someone could argue against | Can't state it? You didn't get it. |
| **5 points** | The load-bearing ideas, not five nice quotes | The argument's actual supports |
| **3 actions** | Doable next Monday | "Think more systematically" doesn't count |
| **1 doubt** | The weakest link in the book | A note with no doubt is a book jacket |

The quotas are hard. Five means five, three means three. Cutting is the work.

## Does / doesn't

**Does:** pull text from your own files, public domain, open access, or official free releases;
read for the spine (claim, supports, evidence type, cost of believing it); label source and
reading scope (full book / ch. 1–4 / abstract only).

**Doesn't:** recap chapter by chapter; invent page numbers, quotes, or findings; reproduce
substantial copyrighted text; touch any piracy route.

## Install

The skill is one file: [`skills/reading-summary/SKILL.md`](skills/reading-summary/SKILL.md).

```bash
git clone https://github.com/KinGao294/reading-summary-skill.git
mkdir -p ~/.cursor/skills/reading-summary
cp skills/reading-summary/SKILL.md ~/.cursor/skills/reading-summary/
```

- **Cursor (personal):** `~/.cursor/skills/reading-summary/SKILL.md`
- **Cursor (project):** `<repo>/.cursor/skills/reading-summary/SKILL.md`
- **Grok Bot / others:** your skills directory, or paste the file into the system prompt

Keep the YAML `description` at the top — that's what triggers auto-invocation.

## Usage

```
Summarize this PDF as a reading note            (attach the file)
I own the epub of <title> — give me one page    (attach the file)
arxiv.org/abs/1706.03762 — five points, plainly
Is this book worth reading? Thesis and doubt first.
```

Steer it in plain language: `first three chapters only`, `actions from a team lead's view`,
`answer in English`.

## Legal red lines

Sources, in order: **your own files** → **public domain / open access** (Gutenberg, arXiv, PMC,
DOAJ, institutional repositories, government and NGO reports) → **official free releases**
(author sites, publisher sample chapters, whitepapers, proceedings) → **say there isn't one** and
point at the library, interlibrary loan, or a purchase link.

Never: shadow libraries, cracked ebooks, torrents, DRM stripping, paywall/login-wall bypass, or
Sci-Hub — no default-off toggle, no "the user said it's legal here" exception. When no legal full
text exists, the skill falls back to abstract plus public reviews and **says so** in the reading
scope line. You remain responsible for your rights to any content you process.

## FAQ

- **Abstract only?** Works, and labels itself as abstract-level.
- **Why is the doubt mandatory?** It's the only thing stopping a note from becoming an ad.
- **Papers and reports?** Yes — OA papers are the easiest case.
- **Change 5/3 to something else?** Sure, but run it as 5/3 once first. The squeeze is the point.
- **Scanned PDFs?** Only as well as your agent's OCR.
- **API key or network?** Neither. It's a Markdown prompt file; all capability comes from your agent.

## Contributing

Issues and PRs welcome — sharper output wording, more legal source lists, install notes for other
agent platforms. No acquisition logic of any kind will be accepted.

## License

[MIT](LICENSE) © 2026 KinGao294. Open source is not a liability waiver: you must hold the rights
to whatever you process.
