# library/ —— 本地书库

`booklib.py` 把书下载到这里。每本书一个目录，目录名就是它的 slug。

```
library/
├── .cache/                     # 古登堡目录缓存（自动生成，可随时删）
└── hong-lou-meng/
    ├── META.json               # 出处、版本、校验和、字数、获取时间
    ├── text.txt                # 规范化正文 —— 所有回答的唯一依据
    ├── chapters.json           # 章节索引：序号 / 标题 / 起止行 / 字数
    ├── SUMMARY.md              # 七段式精读报告
    ├── notes.md                # 分章笔记，每条带定位
    └── source/
        └── pg24264.txt         # 原始下载件，只读
```

## 书籍内容不进 git

同级的 `.gitignore` 默认忽略正文、原始文件与索引。`SUMMARY.md` 和 `notes.md`
是你自己写的分析产物，**默认会被提交**——这通常是你想要的：
笔记值得进版本库，几十兆的原文不值得。

不想提交笔记就删掉 `.gitignore` 里的 `!*/*.md` 那一行。

在你自己的项目里第一次运行 `booklib.py` 时，这份 `.gitignore` 会自动生成，
不用手动拷贝。

## META.json 长什么样

```json
{
  "title": "紅樓夢",
  "author": "Cao, Xueqin, 1717?-1763",
  "language": "zh",
  "source": "project-gutenberg",
  "source_url": "https://www.gutenberg.org/cache/epub/24264/pg24264.txt",
  "source_id": "24264",
  "rights": "public domain in the US (Project Gutenberg License)",
  "acquisition": "downloaded",
  "source_file": "source/pg24264.txt",
  "source_sha256": "ff1526996bf4b81807651921a85e5c1c0f1d1d123c9fa4553057ba6a3ec72011",
  "chars": 911506,
  "cjk_chars": 724619,
  "text_sha256": "134439abc6c3733d5a34420ea3b3f9a39e2f6765bfdfb673cf1665dc004b62a4",
  "acquired_at": "2026-09-07T04:42:03Z"
}
```

校验和让你随时能确认手上这份正文没被改过——引用出处时这一点很实在。

## 换个位置

```bash
BOOKLIB_ROOT=~/books python3 scripts/booklib.py list
```
