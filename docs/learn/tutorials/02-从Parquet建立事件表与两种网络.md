# 02 从 Parquet 建立事件表与两种网络

**版本**：2026-10-30 复核版
**目标**：在明确的 UTC 时间窗内建立事件表、主网络和直接回复网络，并保留无法解析的事件状态。
**先读**：[网络边定义](../concepts/网络边定义.md)、[度与强度](../concepts/度与强度.md)、[互惠性](../concepts/互惠性.md)。

## 1. 先手算，再跑测试

帖子 P 由 A 发布，B 评论帖子，C 回复 B，A 回复 C。事件表保留三条：

- 主网络：`B→A`、`C→A`；帖主 A 的自评不进入主网络。
- 直接回复网络：`B→A`、`C→B`、`A→C`；帖主回楼保留。

两张网络不是谁“更真实”，而是回答不同问题。先跑合成测试：

```bash
REPO_DIR="$HOME/SRT-research"  # 按你的账号实际目录修改
cd "$REPO_DIR"
source ~/venv-srt/bin/activate
python -m unittest discover -s src/analysis -p 'test_*.py' -v
```

测试覆盖跨窗口父节点、帖主回复、自环、缺父、平台标记、半开时间窗和禁止覆盖旧输出。合成测试只验证代码规则，不证明真实社区结论。

## 2. 选择窗口，但不要截断父节点查找

时间窗按评论的动作时间选择，采用左闭右开 `[start, end)`；评论发生在9月但可以指向2月帖子。帖子和父评论必须从**全体输入表**查找，不能把它们一起裁成9月。

以下命令是可执行的9月示例；输出目录必须是自己的新目录：

```bash
REPO_DIR="$HOME/SRT-research"  # 按你的账号实际目录修改
cd "$REPO_DIR"
source ~/venv-srt/bin/activate
python src/analysis/build_analysis_tables.py \
  --start 2026-09-01T00:00:00Z \
  --end 2026-10-01T00:00:00Z \
  --memory 1GB \
  --threads 2 \
  --out ~/srt-work/september-clean-$(date +%Y%m%d-%H%M%S)
```

大任务放 tmux，一次只跑一份全量窗口。脚本默认最多使用5GB临时溢写；`/` 与 `/data` 同盘，先用 `df -h` 检查空间。

## 3. 读取四个输出

| 文件 | 一行是什么 | 用于什么 |
|---|---|---|
| `events.parquet` | 窗口内一条评论及解析状态 | 核对事件、过滤、回楼和抽样 |
| `main_edges.parquet` | 评论者 `src` → 帖子作者 `dst`，含次数 | 项目主网络 |
| `reply_edges.parquet` | 回复者 `src` → 实际父消息作者 `dst`，含次数 | 直接回复关系 |
| `manifest.json` | 参数、输入、状态计数和网络汇总 | 复现、审计和比较 |

`events.parquet`只包含事件时间落在窗口内的评论；父节点查找仍使用全评论表。`source_depth`是原数据字段，不是重建树深。`event_status`至少区分 `valid`、缺帖子、缺作者和时间异常；`reply_status`区分顶层、已解析父节点、缺父、跨帖和时间异常。

缺父的事件若其他字段合格，仍可进入主网络，但不能进入直接回复网络。正式祖先遍历见[04 回复树](04-核对回复树与帖主回应.md)，本脚本不声称已完成全祖先环检查。

## 4. 当前可执行基线

默认基线要求帖子、评论作者ID非空，帖子存在，时间可解析且评论不早于帖子；主网络去评论者与帖主相同的自评；直接回复网络去回复同一账号的自环。默认排除平台标记为 `spam` 或 `deleted` 的评论及帖子，直接回复还排除被标记的父评论。

这只是预先声明的可重复过滤，不是 spam 的真实金标准。事件表保留状态和标记，便于敏感性分析；不要把默认过滤后的图叫“完整原始图”。

## 5. 做平台标记敏感性对照

```bash
source ~/venv-srt/bin/activate
python src/analysis/build_analysis_tables.py \
  --start 2026-09-01T00:00:00Z \
  --end 2026-10-01T00:00:00Z \
  --keep-flagged \
  --out ~/srt-work/september-keep-flagged-$(date +%Y%m%d-%H%M%S)
```

`--keep-flagged`仍会排除缺ID、错误时间和自环，所以它不是完全原始网络。比较两个 manifest 的节点数、二值边数、事件权重、互惠和状态计数；若差异明显，先报告样本构成，不急着解释为行为变化。

## 6. 用 DuckDB 做最低验收

把 `<本次目录>` 替换成实际绝对路径。只读汇总，不打印账号排名：

```bash
source ~/venv-srt/bin/activate
OUT="$HOME/srt-work/september-clean-20261030"  # 改成你本次实际输出目录
test -d "$OUT"
mkdir -p "$OUT/duckdb_tmp"
OUT="$OUT" python - <<'PY'
import os
from pathlib import Path
import duckdb

out = Path(os.environ['OUT']).resolve()
con = duckdb.connect()
con.execute("SET memory_limit='1GB'")
con.execute("SET threads=2")
con.execute("SET temp_directory = ?", [str(out / 'duckdb_tmp')])
con.read_parquet(str(out / 'main_edges.parquet')).create_view('e')
con.sql('SELECT count(*) AS binary_edges, sum(weight) AS comment_events FROM e').show()
con.sql('SELECT count(*) AS bad FROM e WHERE src=dst OR src IS NULL OR dst IS NULL').show()
con.sql('SELECT count(*) AS duplicate_pairs FROM (SELECT src,dst,count(*) FROM e GROUP BY 1,2 HAVING count(*)>1)').show()
PY
```

最后两个结果应为0。二值边数、事件权重和节点数必须分开报告，不能用其中一个替代另一个。

下一步读[03 计算结构与互惠基线](03-计算结构与互惠基线.md)。
