# 同样的文字，不同的命运：大模型智能体社区中的内容、时机与运营者

> **方向调整（2026-11-15，待导师／组会确认）**：原立项题目为《大模型智能体社区的集体结构与对话功能》。下文是调整后的工作题目与研究设计；在导师确认前，立项题目与结题时间仍以原立项为准。旧计划已归档（[archive](docs/notes/archive/)），没有删除。

## 研究问题

本项目研究大模型智能体组成的在线社区 Moltbook。核心问题：**把“说了什么”或“被设定成什么样”固定住，智能体社会里的成败还剩多少由内容决定？多少来自发布时机、版面、作者声望、运营者，多少只是运气？**

Moltbook 有一类难得的数据：平台自己产生的“双胞胎”。完全相同文字的帖子被不同账号在不同时间发出；完全相同简介的智能体被批量或独立地创建。这是机器版的 Music Lab（Salganik 等 2006 年研究人类文化市场的经典实验），而且是野外自然实验，不能随机分配，因此只做关联与分解，不做因果宣称。

## 研究设计

三个相连的问题，细节见[研究计划](docs/notes/下一步研究计划.md)和[一页版](docs/notes/下一步研究计划-精简版.md)：

- **RQ1 同样的话，不同的命运**：完全相同文本的帖子组，点赞与评论的组间相关有多高；发布顺序、小时、版面、作者声望各占多少；早期优势在暴露时间校正后还在不在。
- **RQ2 谁造的 agent，比人设写了什么更重要**：同简介的克隆家族，批量创建的与独立采用的，结果相似度差多少。
- **RQ3（附加）agent 会改写自己吗**：用快照里的简介变化，看成功或被无视之后是否改写。

方法以组间相关（ICC）＋置换零分布、方差分解和混合模型为主，辅以稳健性检验（排除 spam、铸币账号、单一作者占比过高的组）。预备分析只是描述性的，见[预备分析](docs/notes/预备分析-2026-11-15.md)。

须写清数据覆盖、缺失与采集偏差：点赞与 karma 是抓取时的累计值，没有 feed 曝光日志，不把单一快照写成社区全貌。立项不预设结题结论；零结果也是结果。

## 结论边界

结题应在数据边界内给出可辩护判断：同文帖与克隆家族的结果差异，主要更接近内容、位置与时机，还是批量运营者，或仍无法区分；并据此讨论点赞、karma 作为智能体“质量”指标的适用范围。不宣称因果效应，也不宣称“首次”——LLM 版 Music Lab 的受控实验已有（见[文献目录](docs/literature/README.md)）。

## 时间计划（待组会确认）

| 时间 | 工作 |
| --- | --- |
| 2026 年 11 月 16 日起三周 | 固定口径（同文组、克隆家族、`_scraped_at`）；主分析；稳健性并决定下一步 |
| 2026 年 12 月至 2027 年 1 月 | 全时段分析、近似重复与敏感性、必要时附加 RQ3 |
| 2027 年 2 月 | 汇总判断并撰写结题报告 |

之前的结构与对话基线（数据审计、两种网络）保留为数据基础，旧主线的计划见[归档](docs/notes/archive/)。

## 目录

```
README.md        项目说明（本文件）
AGENTS.md        协作规范与合并规则
LOG.md           项目关键进展日志，先读它了解做到哪一步
src/collect/     数据采集脚本
src/prepare/     数据整理（jsonl.gz → Parquet）
src/analysis/    分析代码
notebooks/       探索性笔记本
results/         可公开的小图表和汇总表
docs/learn/      学习资料：概念页、教程页
docs/literature/ 2026-11-15 起的重点文献目录（短笔记＋许可允许的 PDF）
docs/papers/     早期文献笔记与论文 PDF
docs/notes/      研究计划、预备分析、组会记录、数据核查；旧计划在 archive/
personal/        个人文件夹，不入库，别人看不到
```

数据不在仓库里，统一放在服务器 `/data/srt`（只读）。具体规则见 `AGENTS.md`。

## 快速开始

数据已放在云服务器上，登录后就能分析：

```bash
ssh -i 你的密钥.pem 用户名@服务器IP
REPO_DIR="$HOME/SRT-research"  # 当前账号示例；其他账号改成自己的仓库目录
cd "$REPO_DIR"
source ~/venv-srt/bin/activate
python --version
```

整理好的数据在 `/data/srt/outputs/`：`posts.parquet`（帖子）和 `comments.parquet`（评论）。用 duckdb 读一下：

```python
import duckdb
con = duckdb.connect()
con.execute("SET memory_limit='1GB'")
con.execute("SET threads=2")
con.sql("""
    SELECT post_id, count(*) AS n
    FROM '/data/srt/outputs/comments.parquet'
    GROUP BY post_id ORDER BY n DESC LIMIT 5
""").show()
```

当前分析使用服务器上的独立环境 `~/venv-srt`，Jupyter 内核名为 `srt`；依赖清单见 `requirements-venv.txt`。先读[环境与数据核查教程](docs/learn/tutorials/01-核查环境与数据边界.md)。

学习资料从[学习路线](docs/learn/README.md)开始看。重点文献见[文献目录](docs/literature/README.md)，早期四篇原文的术语与操作对应见[概念对照表](docs/papers/四篇论文概念对照表.md)；新的研究问题、三周计划和完成标准见[研究计划一页版](docs/notes/下一步研究计划-精简版.md)及[详细方案](docs/notes/下一步研究计划.md)。学习路线在方向调整后的阅读建议见[必读路线](docs/learn/必读路线.md)开头。

## 数据采集

从 2026-10-22 起，数据改用公开数据集 [jscmp4/Moltbook](https://huggingface.co/datasets/jscmp4/Moltbook) 的 2026-10-07 快照，维护者是 Stevens Institute of Technology 的 Shichao Jia。覆盖 2026-01-27 到 2026-10-07，共 3,699,521 条帖子、19,728,495 条评论、103,631 个 agent。原始文件放在 `/data/srt/raw/moltbook-2026-10-07/`，合并后的表放在 `/data/srt/outputs/`，字段说明见 `/data/srt/outputs/README.md`。使用时按数据集页面引用：

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

我们自己的抓取脚本 `src/collect/` 已停用，只留作参考。自己抓的数据（帖子到 2026-09-30）不再放在服务器上。

## 如何参与

代码与文档的修改都通过 Pull Request 提交。`main` 分支由 GitHub 账号 `feiys22` 审核后合并，不直接推送。提交前请先读 `AGENTS.md`。

## 指导教师

郭迅华，清华大学经济管理学院管理科学与工程系教授。公开研究领域为管理信息系统、电子商务、社会网络、商务智能；研究工作同时做设计科学与行为分析，关注人智融合行为。2005 年起至今在清华大学经济管理学院管理科学与工程系担任教职。现为清华大学经济管理学院教授，兼任国际信息协会中国分会（CNAIS）常务理事兼秘书长、中国信息经济学会副理事长、中国管理现代化研究会信息管理专业委员会秘书长、《信息系统学报》主编助理等职。

## 在服务器上一起工作

- 每人一个自己的账号。登录后把仓库克隆到自己的主目录；仓库目录名由各账号自行决定，例如 `~/SRT-research` 或 `~/SRT`。
- 自己仓库目录下的 `personal/` 是个人文件夹，放草稿和练习，不进仓库，别人看不到。
- 数据在 `/data/srt`，大家共用一份，只读：原始数据在 `/data/srt/raw/moltbook-2026-10-07/`，整理好的表在 `/data/srt/outputs/`。
- 改代码或写文档时，先建自己的分支，写完推送并开 PR，别人批准后合并进 main。
- 想看别人已经合并的文档和代码，在自己的仓库目录里运行 `git pull`。
