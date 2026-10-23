# 02 从Parquet建立事件表与两种网络

**目标**：在限定时间窗内建立事件表、主网络和直接回复网络，保留无法解析的情况。
**先读**：[网络边定义](../concepts/网络边定义.md)、[度与强度](../concepts/度与强度.md)、[互惠性](../concepts/互惠性.md)。

## 1. 先手算三条评论

帖子P由A发布。B评论帖子，C回复B，A回复C。事件表保留三条。主网络得到B→A、C→A，去掉A→A。直接回复网络得到B→A、C→B、A→C。帖主的评论虽然不进主网络，仍然留在事件表中用于回楼指标。

这也是脚本测试的重点。先运行合成数据检查：

```bash
cd ~/SRT
python3 -m unittest discover -s src/analysis -p 'test_*.py' -v
```

检查覆盖跨时间窗父评论、帖主回复、缺失父节点、自环、spam敏感性、半开时间窗及不覆盖旧输出。它们验证规则，不是在合成数据上证明研究发现。

## 2. 选择窗口

下面用UTC的2026年9月，左闭右开。选择的是评论发生时间，不是帖子创建时间。9月评论可能指向2月帖子，所以帖子和父评论查找必须使用全体输入，不能一起裁成9月。

```bash
python3 src/analysis/build_analysis_tables.py   --start 2026-09-01T00:00:00Z   --end 2026-10-01T00:00:00Z   --out ~/srt-work/september-clean
```

输出目录必须在公共数据与公开仓库之外，而且必须是新目录。脚本默认1GB、2线程，临时溢写上限5GB。大任务放tmux，一次运行一份。

## 3. 理解三个文件

| 文件 | 一行是什么 | 用于什么 |
|---|---|---|
| `events.parquet` | 窗口内的一条评论，含解析状态与标记 | 核对事件、筛选、回楼、后续抽样 |
| `main_edges.parquet` | 评论者src→帖作者dst及次数 | README规定的主网络 |
| `reply_edges.parquet` | 回复者src→实际父消息作者dst及次数 | 直接回复关系 |
| `manifest.json` | 参数、计数、网络汇总 | 复现和检查 |

事件表不导出正文。`source_depth`是原数据的depth，不能当作重建树深。`event_status`包括valid、缺帖、缺账号、时间异常等。`reply_status`包括顶层、已解析父节点、缺父节点、跨帖、父节点时间异常等。缺父节点的事件若其他字段合格，仍可进入主网络，但不能进入直接回复网络。

## 4. 清洗规则是什么

当前可执行基线要求帖子和评论账号ID非空、帖子可连接、时间有效且评论不早于帖子。主网络去自评；直接回复网络去回复同一账号的自环。默认排除平台标为spam或deleted的评论及其帖子；楼中楼还排除标为spam/deleted的父评论。

这是预先声明的分析选择，不是真实spam金标准。事件表保留所有选中事件和标记，便于追踪排除原因。脚本不保证全祖先链无环，也不分析语义。正式树形分析还要完成04教程的检查。

## 5. 做一份不过滤标记的对照

```bash
python3 src/analysis/build_analysis_tables.py   --start 2026-09-01T00:00:00Z   --end 2026-10-01T00:00:00Z   --keep-flagged --out ~/srt-work/september-all-flags
```

“不过滤平台标记”仍然保留缺ID、错误时间、自环等基础有效性规则，不能称为完全原始网络。比较两份manifest的节点、二值边、权重和互惠。若差异大，先报告样本构成，不急着解释为行为变化。

## 6. 用SQL检查

```python
from pathlib import Path
import duckdb
con=duckdb.connect()
con.execute("SET memory_limit='1GB'")
con.execute("SET threads=2")
e = str(Path.home()/'srt-work/september-clean/main_edges.parquet')
con.read_parquet(e).create_view('edges')
con.sql('SELECT count(*) AS binary_edges,sum(weight) AS comment_events FROM edges').show()
con.sql('SELECT count(*) FROM edges WHERE src=dst OR src IS NULL OR dst IS NULL').show()
con.sql('SELECT src,dst,count(*) FROM edges GROUP BY 1,2 HAVING count(*)>1').show()
```

后两个结果应分别为0和空表。不要将原事件的条数与二值边数混淆。下一步读[03 结构与互惠基线](03-计算结构与互惠基线.md)。
