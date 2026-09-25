# 采集

公开抓取 Moltbook 帖子和评论。脚本是 `collect_moltbook.py`。结果写入 `raw/crawl/`，不进入版本库。不使用登录凭证。

数据边界和截止时间见 `docs/data-collection.md`。

## 环境

- Python 3.10 或以上。脚本使用了 `list[str] | None` 这类内置泛型注解。
- 能访问 `https://www.moltbook.com/api/v1`。
- 不需要 API key，也不要把密钥写进脚本或日志。

在仓库根目录安装依赖：

```bash
pip install -r src/collect/requirements.txt
```

依赖只有 `requests>=2.32.0`。没有别的第三方包。

## 运行

```bash
python src/collect/collect_moltbook.py
```

常用参数：

```bash
python src/collect/collect_moltbook.py --out raw/crawl --cutoff 2026-01-27T00:00:00Z --rate 8 --workers 32
python src/collect/collect_moltbook.py --max-posts 20 --max-comment-posts 2
```

中断后重新执行同一命令会读取 `raw/crawl/progress.json`。断点每 5 秒写一次。已经抓完评论的帖子会跳过；未完成的评论帖如果记下了下一页游标，从该页继续。游标尚未落盘就中断时，该页会重抓，评论文件里会有重复行。建边时按评论 ID 去重。

## 速度

2026-09-24 响应头有两层额度。短窗 30 次/秒，中窗 600 次/分钟，长窗 10000 次/300 秒。另一层无后缀额度按接口分开：帖子列表 200 次/60 秒，这次等过重置后剩余次数回到 199；评论 500 次，重置时间距采样时 59 到 60 秒。评论是大头，持续速率按 500/60 秒计算，上限是每秒 8.3 次。

同日 `raw/crawl/collect.log` 里，帖子页从启动到写完 1.4 秒。两条评论请求同时发出，分别在 1.2 秒和 3.0 秒后写完。并发数低于「速率乘以单次耗时」时，实际请求数到不了 `--rate`。按 3.0 秒计，8 个并发的上限是每秒 2.7 次。

默认 `--rate 8`、`--workers 32`。8 次/秒留在评论额度以内。32 个并发在 3.0 秒单次耗时下能挂住每秒 10.7 次请求，盖住默认发起速率。`--workers` 只增加同时挂着的请求，不把发起速率抬过 `--rate`。帖子列表和评论的无后缀额度分开计算，帖子列表更紧时不会把评论请求一起压到每秒 3.3 次。

响应头里的剩余额度更紧时，脚本按剩余次数和重置时间放慢。连续遇到 429 时，把本次运行的上限下调 10%，最低到每秒 1 次。不要把 `--rate` 调到 8.3 以上。

帖子页必须串行，下一页依赖 `next_cursor`。评论按帖子并发。日志里的 `rps` 是本次运行已经发出的请求数除以运行秒数。
