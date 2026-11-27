# src —— 分析代码

- 代码以 Python 为主，依赖见仓库根目录 `requirements-venv.txt`。
- 数据路径通过环境变量 `SRT_DATA_DIR` 或命令行参数传入，不在代码里写死本机路径。
- 原始数据与大型中间产物放在仓库外，不提交。

目录：

- `analysis/`：数据核查与基础表构建脚本，见 [analysis/README.md](analysis/README.md)。
