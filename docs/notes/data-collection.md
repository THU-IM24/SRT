# Moltbook 数据采集

脚本：`src/collect/collect_moltbook.py`。环境要求：`src/collect/README.md`。结果目录：`raw/crawl/`。结果不进入版本库。

## 抓什么

公开接口 `https://www.moltbook.com/api/v1`。不使用登录凭证。

- 帖子：`GET /posts?sort=new`，用 `next_cursor` 从新往旧翻。
- 评论：`GET /posts/{id}/comments`。接口把楼中楼放在 `replies` 里，脚本摊平后写入 `parent_id`。没有回复时 `parent_id` 为 `null`。

`offset` 不能往回翻。2026-09-24 实测，`offset=0`、`500`、`2000`、`5000` 返回同一条新帖。按时间做的起始游标仍然有效，这是脚本使用的方法。

## 时间边界

2026-09-24 的探测结果：

- 从 2026-09-24、2026-02-14 起翻，能落到对应时间的帖子。
- 从 2026-01-28 起翻，得到 1 条 2026-01-27 的帖子，之后没有更多。
- 从 2025-09-24 和 2025-01-01 起翻，返回 0 条。

因此默认 `--cutoff 2026-01-27T00:00:00Z`。这不是「去年全年」。接口没有返回 2025 年的帖子。已有的 2026-01-28 至 2026-02-14 快照可以和这次结果按帖子 ID 合并，但不能把这次采集写成社区全貌。

## 速度

2026-09-24 响应头有两层额度。短窗 30 次/秒，中窗 600 次/分钟，长窗 10000 次/300 秒。另一层无后缀额度按接口分开：帖子列表 200 次/60 秒，这次等过重置后剩余次数回到 199；评论 500 次，重置时间距采样时 59 到 60 秒。评论请求远多于帖子页，持续速率按评论这层计算，上限是每秒 8.3 次。

同日日志里，帖子页从启动到写完 1.4 秒。两条评论请求同时发出，分别在 1.2 秒和 3.0 秒后写完。并发数低于「速率乘以单次耗时」时，实际请求数到不了 `--rate`。脚本默认每秒 8 次请求、32 个评论并发。32 个并发在 3.0 秒单次耗时下能挂住每秒 10.7 次请求，盖住默认发起速率。帖子页必须串行，因为下一页依赖 `next_cursor`。评论请求互相独立，并发放在评论上。

不要把 `--rate` 调到 8.3 以上。评论额度是每 60 秒 500 次，超过后会被 429 拖住，总时间不会更短。

## 运行

```bash
pip install -r src/collect/requirements.txt
python src/collect/collect_moltbook.py
```

常用参数：

```bash
python src/collect/collect_moltbook.py --out raw/crawl --cutoff 2026-01-27T00:00:00Z --rate 8 --workers 32
python src/collect/collect_moltbook.py --max-posts 20 --max-comment-posts 2
```

中断后重新执行同一命令会读取 `raw/crawl/progress.json`，从上次的 `next_cursor` 继续，并跳过已经抓完评论的帖子。断点每 5 秒写一次。评论未完成的帖子如果记下了下一页游标，从该页继续；游标尚未落盘就中断时，该页会重抓，评论文件里会有重复行。后续建边时按评论 ID 去重。

## 输出

```
raw/crawl/posts/posts-00001.jsonl.gz
raw/crawl/comments/comments-00001.jsonl.gz
raw/crawl/progress.json
raw/crawl/collect.log
```

每行一个 JSON 对象。帖子保留接口原字段。评论去掉嵌套的 `replies`，并写入 `post_id` 与 `parent_id`。

## 不要入库

`raw/crawl/` 除本说明外已被 `.gitignore` 排除。不要把这些文件提交到公开仓库，也不要把密钥写进脚本。
