# src —— 分析与图计算代码

本目录存放结构层与对话层的分析与图计算代码，包括评论互动网的构建、网络指标计算和评论功能编码脚本。

- 代码以 Python 为主。采集依赖写在 `collect/requirements.txt`，不放仓库根目录。
- 不把原始数据和可重新生成的产物放进本目录。
- 修改通过 Pull Request 提交，`main` 由 `feiys22` 审核后合并。

已有代码：

- `collect/`：按 `next_cursor` 抓取 Moltbook 公开帖子和评论，结果写入 `raw/crawl/`。环境要求见 `collect/README.md`，数据边界见 `docs/data-collection.md`。
