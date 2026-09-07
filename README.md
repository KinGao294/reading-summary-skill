# reading-summary-skill

An Agent skill for creating structured book summaries from legal PDFs.

Agent skill: **download a legal PDF first**, then write a coarse weekly-style book note with structured outputs.

---

**中文简介**

Agent 技能：先合法下载/落地 PDF，再输出结构化的粗放读书笔记（1个主旨 / 5个要点 / 3个行动 / 1个存疑）。

---

## Features

- Downloads legal PDFs from public sources or user-provided files
- Generates structured book notes with:
  - 1 main thesis
  - 5 key points
  - 3 actionable items
  - 1 critical question
- Enforces legal-only content policy by default

## Installation

Copy `skills/reading-summary/SKILL.md` to your agent skills folder:

- **Cursor**: `~/.cursor/skills/` or your workspace `.cursor/skills/`
- **Other agent systems**: Place in your configured skills directory

The skill will be automatically discovered by agents that support the skills framework.

## Usage

Once installed, agents will be able to:
1. Recognize requests for book summaries
2. Download legal PDFs (public domain, open access, author-provided, or user-owned files)
3. Generate structured reading notes in the specified format

## Legal Policy

This skill enforces a **legal-only** policy by default:

✅ **Supported sources:**
- Public domain PDFs
- Official publisher/author releases
- Open Access (OA) publications
- User-owned files and attachments

❌ **Not supported:**
- Pirate sites
- Cracked or DRM-stripped ebooks
- Paywall bypass techniques
- Sci-Hub or similar services (by default)

**Important:** The skill includes built-in guardrails to prevent illegal content access. Users are responsible for ensuring they have legal rights to access any content they process.

## License

MIT License - Copyright (c) 2026 KinGao294

See [LICENSE](LICENSE) file for full details.
