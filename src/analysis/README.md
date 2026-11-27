# 分析代码

基于 DuckDB 的本地只读分析脚本，直接读取从 Hugging Face 下载的 `jscmp4/Moltbook` Parquet 文件。

| 文件 | 功能 |
|---|---|
| `audit_snapshot.py` | 全量主键、时间、父子关系与覆盖审计，输出聚合 JSON |
| `build_analysis_tables.py` | 限定事件时间窗，建立事件表、主网络和回复网络 |
| `test_analysis_tables.py` | 合成数据单元测试（不依赖真实数据） |

## 运行示例

假设本地数据在 `D:\data\moltbook`（可通过环境变量 `SRT_DATA_DIR` 指定，或用 `--posts` / `--comments` 传路径，支持单文件或通配符）：

```bash
python -m unittest discover -s src/analysis -p "test_*.py" -v

# 数据核查（输出路径须在仓库之外）
python src/analysis/audit_snapshot.py --out D:\data\moltbook-out\audit-check

# 构建某月事件表与两种网络
python src/analysis/build_analysis_tables.py \
  --start 2026-09-01T00:00:00Z --end 2026-10-01T00:00:00Z \
  --out D:\data\moltbook-out\september-clean
```

事件时间窗为左闭右开；父节点查找使用全评论表。默认排除 `is_spam` / `is_deleted` 标记，加 `--keep-flagged` 可做敏感性对比。
