# papers —— 文献笔记与论文 PDF

一篇文献一个 md 笔记，文件名用 `第一作者-年份-短标题.md`。

## 论文 PDF

论文 PDF 可以直接提交到本目录，和笔记一起走 PR。文件名统一为 `序号-发表处或第一作者单位-研究平台.pdf`：

- **序号**：两位数，按入库顺序递增，如 `01`、`02`。
- **发表处**：已发表或已录用的写期刊或会议的常用简称，如 `ICWSM`、`CSCW`、`DIM`；只是预印本的写第一作者单位简称，如 `CMU`、`Passau`。
- **研究平台**：论文研究的网络平台，如 `Moltbook`、`Twitter`、`Reddit`。
- 只用英文字母、数字和连字符，不要空格。例如 `01-DIM-Chirper.pdf`。

**注意版权**：仓库是公开的，只提交许可证允许转载的 PDF，比如开放获取（CC BY、CC BY-NC-ND 等）或 arXiv 上带 CC 许可证的版本。出版社版权所有的 PDF（如首页写着 "exclusive license to Springer"）不要提交，在下表里只登记链接，"文件"一栏写"未入库"。

| 文件 | 标题 | 作者 | 年份 | 发表处 | 研究平台 | 许可证 | 链接 |
|---|---|---|---|---|---|---|---|
| `01-DIM-Chirper.pdf` | Unveiling the collective behaviors of large language model-based autonomous agents in an online community: A social network analysis perspective | Huiru Chen, Zhenhua Wang, Ming Ren | 2026 | Data and Information Management, 10, 100107 | Chirper | CC BY-NC-ND 4.0 | [doi:10.1016/j.dim.2025.100107](https://doi.org/10.1016/j.dim.2025.100107) |
| 未入库（拟用名 `02-SBP-BRiMS-Twitter.pdf`） | Are LLM-Powered Social Media Bots Realistic? | Lynnette Hui Xian Ng, Kathleen M. Carley | 2026 | SBP-BRiMS 2025, LNCS 16127, pp. 14–23 | Twitter/X（模拟） | Springer 版权所有 | [doi:10.1007/978-3-032-07715-8_2](https://doi.org/10.1007/978-3-032-07715-8_2) |
| `03-Passau-Moltbook.pdf` | Form Without Function: Agent Social Behavior in the Moltbook Network | Saber Zerhoudi et al.（共 12 人） | 2026 | arXiv 预印本（University of Passau） | Moltbook | CC BY 4.0 | [arXiv:2604.13052](https://arxiv.org/abs/2604.13052) |
| `04-Konstanz-Moltbook.pdf` | Collective Behavior of AI Agents: the Case of Moltbook | Giordano De Marzo, Andres L. Marin, David Garcia | 2026 | arXiv 预印本（University of Konstanz） | Moltbook | CC BY 4.0 | [arXiv:2602.09270](https://arxiv.org/abs/2602.09270)（v2） |

## 笔记模板

```markdown
# 标题

- 作者 / 年份 / 期刊：
- 链接或 DOI：
- PDF：本目录下的文件名（未入库就写链接）

**问题**：……
**数据与方法**：……
**主要发现**：……
**和本项目的关系**：……
```
