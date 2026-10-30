# prepare —— 历史数据整理脚本

> **当前流程不要运行本目录脚本。** 自2026-10-22起，项目使用公开的 Moltbook 2026-10-07 快照；当前 `/data/srt/outputs/` 已由管理员准备，分析入口是 `src/analysis/`。本页只保留旧自采数据流程的档案说明。

- `convert_to_parquet.py`：把 `/data/srt/raw/crawl/` 的帖子和评论转成 `/data/srt/outputs/posts.parquet`、`comments.parquet`，按 `id` 去重。

## 2026-10-22 起

`/data/srt/outputs/posts.parquet` 和 `comments.parquet` 改由公开数据集 [jscmp4/Moltbook](https://huggingface.co/datasets/jscmp4/Moltbook) 2026-10-07 快照合并生成。当前分析不要自行重建、覆盖或写入 `/data/srt`；字段和审计见[环境与数据边界教程](../../docs/learn/tutorials/01-核查环境与数据边界.md)。`convert_to_parquet.py` 只适用于旧的 `raw/crawl/`，留作历史参考。
