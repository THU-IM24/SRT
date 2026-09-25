# raw —— 原始数据与产物

本目录存放原始数据和由它们生成的产物：Moltbook 数据表、抽取出的边表、编码中间结果等。

- 原始数据与可重新生成的产物不进入版本库，只在本目录保留说明文件。
- `raw/outputs/` 下可重新生成的产物由 `.gitignore` 排除，仅放行 `raw/outputs/README.md`。
- `raw/crawl/` 存放 `src/collect/collect_moltbook.py` 新抓到的帖子和评论，由 `.gitignore` 排除，仅放行 `raw/crawl/README.md`。
- 写清数据覆盖、缺失与采集偏差。不把单一快照写成社区全貌。
- 数据放在本机或云服务器，通过版本库以外的方式分发，不随代码克隆。
