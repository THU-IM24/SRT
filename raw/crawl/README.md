# raw/crawl —— 本次采集结果

`src/collect/collect_moltbook.py` 把新抓到的帖子和评论写到这里。说明见 `docs/data-collection.md`。

- `posts/`：帖子，gzip 压缩的 JSONL。
- `comments/`：评论。楼中楼已摊平，`parent_id` 指向父评论。
- `progress.json`：断点。
- `collect.log`：运行日志。

这些结果不进入版本库。覆盖范围、缺失和采集偏差以 `progress.json` 里的 `oldest`、`newest` 和日志为准，不把单次抓取写成社区全貌。
