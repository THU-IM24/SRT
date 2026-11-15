# LLM Multi-Agent Systems Are Vulnerable to Herding and Runaway Cascades

- 作者：Farnoosh Hashemi, Shiyu Ji, Joice Chen, Michael W. Macy
- 年份 / 发表处：2026 / arXiv 预印本 2610.30769v1（2026-10-22 首次提交）
- 链接：<https://arxiv.org/abs/2610.30769>
- 许可：CC BY 4.0
- PDF：[pdf/Hashemi-2026-LLMHerding-arXiv2610.30769v1.pdf](pdf/Hashemi-2026-LLMHerding-arXiv2610.30769v1.pdf)（CC BY 4.0，原样转载，署名见 [pdf/README.md](pdf/README.md)）
- 在本项目中的角色：最近的前作

**问题**：大模型智能体群体在“看到累计推荐数”时，会不会出现羊群与失控级联？

**数据与方法**：按经典 Music Lab 的设计，让大规模 LLM 智能体推荐陌生歌曲，一组看得到累计推荐数，一组看不到；并与人类对照。

**主要发现**（摘要所述，非我们复核）：暴露于累计计数导致失控级联，群体推荐与歌曲内在吸引力越来越背离；与人类相比，LLM 群体更容易羊群，且级联更难自我纠正。

**和本项目的关系**：这是与本项目最近的前作之一：它是受控的 Music Lab 实验（自己安排实验、可随机分配），不是 Moltbook 的野外数据。我们的差别是：用平台里已经存在的完全相同文本与同简介克隆做“自然实验”，并拆分内容、时间、版面、运营者与运气。写作时必须引用并明确区分，不得宣称“首次把 Music Lab 用于 AI 智能体”。

> 核读程度：本笔记依据论文摘要与检索到的片段，没有逐篇通读全文；引用前须对照原文核对数字与表述。
