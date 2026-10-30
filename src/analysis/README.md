# 分析代码

当前提供低内存、只读输入的可执行基线。服务器使用 `~/venv-srt`（Python 3.12、DuckDB 2.0.0）；运行前先激活该环境。

| 文件 | 功能 |
|---|---|
| `audit_snapshot.py` | 全量主键/时间/连接/覆盖审计，输出聚合JSON |
| `build_analysis_tables.py` | 限定事件时间窗，建立事件、主网络和实际回复网络 |
| `test_analysis_tables.py` | 合成数据检查边定义、跨窗父节点、自环与过滤 |

```bash
source ~/venv-srt/bin/activate
python -m unittest discover -s src/analysis -p 'test_*.py' -v
python src/analysis/audit_snapshot.py --out ~/srt-work/audit-check
python src/analysis/build_analysis_tables.py --start 2026-09-01T00:00:00Z --end 2026-10-01T00:00:00Z --out ~/srt-work/september-clean
```

核心依赖是DuckDB和`pytz`；后者用于DuckDB返回`TIMESTAMPTZ`结果，`requirements.txt`记录本次可复现版本。使用现有解释器即可，不为运行脚本自动改公共环境。输出在仓库及共享数据之外；构建脚本拒绝覆盖已有产物。审计允许在指定输出目录更新中间进度，请为新输入使用新目录。

默认1GB、2线程、5GB临时溢写上限。内存限制不等于整个进程占用上限。长任务用tmux，不同时跑多份全量任务。

事件时间窗为左闭右开。父节点查找使用全评论表。`source_depth`只是原始字段，未重建祖先深度。网络只对合法事件建边，主网络去自评，实际回复网络去自回复。默认排spam/deleted，`--keep-flagged`可做敏感性。

未实现：全线程祖先遍历、内容标注、图算法、机会模型、生存分析或正式回归。不要把这些基线输出当作对话功能结论。详细用法见[教程](../../docs/learn/tutorials/README.md)。
