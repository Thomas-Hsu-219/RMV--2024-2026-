# RMV 文献资料库 · 2024–2026

保存 **Reviews in Medical Virology（RMV）** 的论文题目、摘要、作者关键词及可追溯来源，便于直接阅读、AI 分析、拟定论文题目和制作 Skill。

GitHub 仓库：[Thomas-Hsu-219 / RMV--2024-2026-](https://github.com/Thomas-Hsu-219/RMV--2024-2026-)。

**数据快照截至 2026-09-27，共 294 条记录，273 条有摘要、262 条有原始作者关键词。2026 年尚未结束，当前不是完整全年数据。**

## 从这里开始

- [全部文献题目目录](data/catalogue.md)
- [2024 年：题目、摘要、关键词](data/2024.md)
- [2025 年：题目、摘要、关键词](data/2025.md)
- [2026 年：题目、摘要、关键词](data/2026.md)
- [给 AI 的读取与引用说明](AI_README.md)
- [完整 JSON](data/articles.json) · [JSONL（每行一篇）](data/articles.jsonl) · [CSV（可用 Excel 打开）](data/articles.csv)
- [缺失字段清单](data/missing-fields.json) · [质量报告](data/quality-report.json) · [来源与校验信息](data/source-manifest.json)
- [详细数据说明](data/README.md)

原网站的直接访问无法保证，因此本仓库完整保存了全部数据，不依赖原网站加载。本人可直接打开 Markdown 阅读；AI 可读取 JSON/JSONL 或按年份分批读取。读取工具能否联网访问 GitHub 仍取决于各工具的权限与网络情况。

供其他 AI 直接读取的原始文件链接：

- [AI 读取与引用说明（Raw）](https://raw.githubusercontent.com/Thomas-Hsu-219/RMV--2024-2026-/main/AI_README.md)
- [完整 JSON（Raw）](https://raw.githubusercontent.com/Thomas-Hsu-219/RMV--2024-2026-/main/data/articles.json)
- [2024 JSON（Raw）](https://raw.githubusercontent.com/Thomas-Hsu-219/RMV--2024-2026-/main/data/2024.json) · [2025 JSON（Raw）](https://raw.githubusercontent.com/Thomas-Hsu-219/RMV--2024-2026-/main/data/2025.json) · [2026 JSON（Raw）](https://raw.githubusercontent.com/Thomas-Hsu-219/RMV--2024-2026-/main/data/2026.json)
- [AI 文件导航](llms.txt)

## 收录范围与核验边界

| 卷期年 | 内容记录 | 有摘要 | 有原始作者关键词 |
|---|---:|---:|---:|
| 2024 | 106 | 100 | 99 |
| 2025 | 72 | 63 | 59 |
| 2026（截至 9 月 27 日） | 116 | 110 | 104 |
| 合计 | 294 | 273 | 262 |

包含综述、社论、来信、评论及更正；排除整期 DOI 和封面等非内容记录。年份按期刊卷期年归档，并保留在线发表日期，不能将两种年份口径混用。

2024 年六期共 106 篇的 DOI 已与出版商目录核对。2025 年第 2–6 期共 65 篇已核对题目与卷期；**第 1 期的 7 篇已入库，但因 Wiley 目录当时不可读，未完成官网目录独立核验，仅完成索引核对**。2026 年已出五期共 116 篇核对了题目，其中 91 个 DOI 链接直接验证、25 个文章链接未能取得。详见 [2024 核验](data/coverage/wiley_2024_coverage.json)、[2025 核验](data/coverage/wiley_2025_coverage.json)、[2026 核验](data/coverage/wiley_2026_coverage.json)。

没有用 AI 编造或补齐摘要、关键词。空值表示本次检索来源未获取该字段，不证明原作者从未提供。本仓库使用上方文件链接阅读。

## 手动更新

本资料库没有自动更新任务。保留原有手动更新脚本，需 Python 3.10+ 和联网环境，在仓库根目录运行：

```sh
python scripts/refresh.py --cutoff 2026-09-27
```

将截止日期改为所需的非未来日期（限 2024–2026 年）。脚本取得 Crossref、PubMed、Europe PMC 公开元数据并重建根目录的 `data/`；默认截止日期为运行当天与 2026-12-31 的较早值。原始响应保存在 `.refresh-sources/`。本次迁移没有执行重新抓取。

更新后须检查 [质量报告](data/quality-report.json) 和 [缺失字段](data/missing-fields.json)，重新核验出版商目录，并更新 README 与数据说明中的日期、统计及核验范围。已有 coverage 文件是历史核验，脚本不会自动完成新的官网核验。确认结果后再提交到 GitHub，脚本不会自动发布。

## 来源与权利

期刊官网：[Reviews in Medical Virology](https://onlinelibrary.wiley.com/journal/10991654)。来源包括 Wiley、Crossref、PubMed 和 Europe PMC，各记录保留 DOI、来源链接、字段来源与已有版权/许可信息。

不包含论文全文。题目、摘要与关键词的权利归相应原作者或出版商；整理保存不改变其许可，也不向他人统一授予这些原文的新许可证。
