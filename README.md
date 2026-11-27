# Moltbook 大模型智能体社区研究

本项目研究大模型智能体组成的在线社区 **Moltbook**，数据来自公开数据集 [jscmp4/Moltbook](https://huggingface.co/datasets/jscmp4/Moltbook)（2026-10-07 快照，覆盖 2026-01-27 至 2026-10-07，含 3,699,521 条帖子、19,728,495 条评论、103,631 个 agent）。

具体研究切入点与假设将在团队阅读核心文献、熟悉数据边界后确定，不预设结题结论。

## 目录

```text
README.md           项目说明与本地上手（本文件）
AGENTS.md           协作与仓库规范
LOG.md              项目关键进展日志
docs/papers/        7 篇核心论文（中文笔记 + CC BY 4.0 原文 PDF）
docs/concepts/      12 篇核心概念页
docs/notes/         数据核查与组会记录
docs/slides/        文献分享 PPT
src/analysis/       本地分析与数据核查脚本
notebooks/          探索性笔记本
results/            可公开的小图表与汇总表
personal/           个人草稿区（不入库）
```

## 本地数据下载

数据**不放在仓库里**，请在自己电脑的**仓库外目录**（例如 `D:\data\moltbook` 或 `~/data/moltbook`）直接从 Hugging Face 下载 `parquet/` 下的核心表（共约 **3.63 GB**；根目录几十 GB 的 `.jsonl` 原始文件无需下载）：

- `parquet/posts/`：10 个文件，约 1.01 GB
- `parquet/comments/`：10 个文件，约 2.60 GB
- `parquet/agents/`：1 个文件，约 7.3 MB

安装依赖后，用 Python 一行命令即可下载（国内直连慢时可先设镜像 `HF_ENDPOINT=https://hf-mirror.com`）：

```bash
pip install -r requirements-venv.txt

# Windows PowerShell（如直连慢可先执行：$env:HF_ENDPOINT="https://hf-mirror.com"）
python -c "from huggingface_hub import snapshot_download; snapshot_download('jscmp4/Moltbook', repo_type='dataset', allow_patterns=['parquet/posts/*','parquet/comments/*','parquet/agents/*','README.md','submolts.json'], local_dir=r'D:\data\moltbook')"
```

也可直接从网页 [jscmp4/Moltbook/tree/main/parquet](https://huggingface.co/datasets/jscmp4/Moltbook/tree/main/parquet) 手动下载对应目录。

### 引用数据集

```bibtex
@dataset{jia2026moltbook,
  author       = {Jia, Shichao},
  title        = {{Moltbook AI Agent Social Media Corpus}},
  year         = {2026},
  publisher    = {Hugging Face},
  version      = {2026-10-07},
  url          = {https://huggingface.co/datasets/jscmp4/Moltbook},
  institution  = {Stevens Institute of Technology}
}
```

## 快速开始

在本地通过环境变量 `SRT_DATA_DIR` 指定数据目录（也可以在命令行直接传路径），用 DuckDB 直接读取分片 Parquet：

```python
import os
import duckdb

data_dir = os.environ.get("SRT_DATA_DIR", r"D:\data\moltbook")
con = duckdb.connect()
con.sql(f"""
    SELECT count(*) AS n_posts
    FROM read_parquet('{data_dir}/parquet/posts/*.parquet')
""").show()
```

阅读资料按以下顺序即可：

1. [核心论文（7 篇）](docs/papers/README.md)
2. [核心概念（12 篇）](docs/concepts/README.md)
3. [数据边界与字段核查](docs/notes/当前数据核查-2026-10-23.md)

## 协作方式

- 所有代码与文档改动都新建分支并通过 Pull Request 合并到 `main`，不直接推送 `main`。
- 详情见 [AGENTS.md](AGENTS.md) 与 [Git 分支与 PR](docs/concepts/Git分支与PR.md)。

## 指导教师

郭迅华，清华大学经济管理学院管理科学与工程系教授。研究领域为管理信息系统、电子商务、社会网络、商务智能，关注设计科学与行为分析及人智融合行为。
