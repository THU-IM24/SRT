# 核心概念配图附件

本目录仅保存学习页用的原创示意图及复现脚本，不放真实账号、数据截图或分析结果。现有仓库规范没有另行指定图片目录或强制命名，本轮采用 `docs/learn/assets/core-concepts/` 集中存放，用相对Markdown路径嵌入；每张图的来源与授权同时写在正文图注。

| 文件 | 嵌入页 | 内容与来源 |
|---|---|---|
| [edge-definitions.png](edge-definitions.png) | [网络边定义](../../concepts/网络边定义.md) | 根据该页虚构P、c1、c2、c3事件绘制，两张账号图与消息树对照 |
| [reciprocity.png](reciprocity.png) | [互惠性](../../concepts/互惠性.md) | 根据A↔B、C→D虚构网络和本页公式绘制，展示2/3与1/2的不同分母 |
| [op-return.png](op-return.png) | [帖主回楼](../../concepts/帖主回楼.md) | 根据B、A、B及C的虚构线程绘制，展示一帖与三个评论机会 |
| [right-censoring.png](right-censoring.png) | [右删失](../../concepts/右删失.md) | 根据相对0—48小时时轴绘制，终点和事件时间均为虚构 |

绘制：SRT项目学习文档，2026-10-24，Python／Matplotlib。四图均为原创、无水印，未复制或改编任何第三方图片。四张PNG与本目录绘图脚本按[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)提供；建议署名“SRT项目学习文档，2026”，转载或改图时保留来源、许可链接及修改说明。此项许可仅覆盖上述原创附件，不改变论文、数据集或仓库其他文件的许可。

## 复现

[generate_diagrams.py](generate_diagrams.py)不读取研究数据；运行后在脚本所在目录生成四张PNG。使用Python 3.13.3及Matplotlib 3.11.2，依赖见[requirements.txt](requirements.txt)。在独立虚拟环境内执行：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe generate_diagrams.py
```

脚本使用Windows的微软雅黑字体 `C:/Windows/Fonts/msyh.ttc`；其他系统需将字体路径改为本机可用的中文字体。虚拟环境与字体缓存不进入仓库。PNG均宽2160像素，已检查中文显示、箭头方向、文字裁切及图片可解码性。
