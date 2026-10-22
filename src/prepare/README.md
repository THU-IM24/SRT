# prepare —— 数据整理

- `convert_to_parquet.py`：把 `/data/srt/raw/crawl/` 的帖子和评论转成 `/data/srt/outputs/posts.parquet`、`comments.parquet`，按 `id` 去重。

在仓库根目录运行：

```bash
conda activate srt
tmux new -s conv 'nice -n 19 ionice -c3 python src/prepare/convert_to_parquet.py'
```

## 2026-10-22 起

`/data/srt/outputs/posts.parquet` 和 `comments.parquet` 改由公开数据集 [jscmp4/Moltbook](https://huggingface.co/datasets/jscmp4/Moltbook) 2026-10-07 快照合并生成：把 `/data/srt/raw/moltbook-2026-10-07/parquet/posts/` 和 `comments/`（按月分文件）用 duckdb 各合并成一个文件，不改字段。字段名沿用 Moltbook 接口原名，与旧表一致；说明见 `/data/srt/outputs/README.md`。`convert_to_parquet.py` 只适用于旧的 `raw/crawl/`，留作参考。
