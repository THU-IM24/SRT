# prepare —— 数据整理

- `convert_to_parquet.py`：把 `raw/crawl/` 的帖子和评论转成 `raw/outputs/posts.parquet`、`comments.parquet`，按 `id` 去重。

在仓库根目录运行：

```bash
conda activate srt
tmux new -s conv 'nice -n 19 ionice -c3 python src/prepare/convert_to_parquet.py'
```
