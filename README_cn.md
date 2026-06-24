# CLI 测试框架

轻量级命令行自动化测试框架，用 JSON/YAML 定义测试用例，一行命令跑完所有验证。

特别适合科学计算场景——对 HDF5 结果文件有深度支持：正则匹配表格、数据过滤、容差对比，轻松搞定仿真结果校验。

## 功能亮点

- **Golden File 断言** — `compare_files` 嵌入测试 `expected`，运行后自动对比产物文件与基准文件，支持容差
- **并行执行** — 多线程/多进程，3-5 倍加速
- **资源感知调度** — 自动管理 CPU 核心分配，防止求解器线程失控
- **顺序步骤测试** — 单个用例内多步执行，失败即停
- **Setup 模块** — 测试前自动配置环境变量，测试后自动清理
- **文件比较** — 文本 / JSON / CSV / XML / HDF5 / 二进制，支持 CLI 独立使用和内嵌断言两种方式
- **筛选运行** — 按名称指定运行哪些用例

## 快速开始

```bash
pip install cli-test-framework
```

### 30 秒上手

1. 写测试用例 `test_cases.json`：

```json
{
    "test_cases": [
        {
            "name": "hello",
            "command": "echo",
            "args": ["Hello World"],
            "expected": {
                "return_code": 0,
                "output_contains": ["Hello World"]
            }
        }
    ]
}
```

2. 运行：

```bash
cli-test run test_cases.json
```

### 测试中对比 Golden File

运行仿真命令，自动对比输出文件与基准：

```json
{
    "test_cases": [
        {
            "name": "FEA 位移检查",
            "command": "my_solver",
            "args": ["--input", "case1.dat", "--output", "out.h5"],
            "expected": {
                "return_code": 0,
                "compare_files": [
                    {
                        "actual": "out.h5",
                        "baseline": "ref/golden.h5",
                        "rtol": 1e-5,
                        "atol": 1e-8,
                        "tables": ["NASTRAN/RESULT/NODAL/DISPLACEMENT"]
                    }
                ]
            }
        }
    ]
}
```

- `actual` — 命令产出的文件
- `baseline` — 用于对比的基准文件
- `type` — 比较器类型（省略时从后缀自动检测：`.h5`→h5, `.json`→json, `.csv`→csv, `.xml`→xml, `.txt`→text）
- 其余字段透传到对应比较器（`rtol`、`atol`、`tables`、`table_regex`、`data_filter`、`encoding`、`structure_only`、`delimiter`、`compare_mode`、`key_field` 等）

支持同时对比多个文件，以及与已有断言混用：

```json
{
    "expected": {
        "return_code": 0,
        "output_contains": ["仿真完成"],
        "compare_files": [
            {"actual": "out.h5", "baseline": "ref/disp.h5", "rtol": 1e-5},
            {"actual": "report.csv", "baseline": "ref/expected.csv", "rtol": 1e-6}
        ]
    }
}
```

### 并行运行

```bash
cli-test run test_cases.json --parallel --workers 4
```

### Python API

```python
from cli_test_framework.runners import JSONRunner, ParallelJSONRunner

# 顺序
runner = JSONRunner(config_file="test_cases.json")
success = runner.run_tests()

# 并行
runner = ParallelJSONRunner(config_file="test_cases.json", max_workers=4, execution_mode="thread")
success = runner.run_tests()
```

### 文件比较（独立 CLI）

```bash
compare-files result1.h5 result2.h5 --h5-table-regex "output_.*" --h5-rtol 1e-5
```

📖 **完整使用说明**：[docs/user_manual.md](docs/user_manual.md)

## 更新日志

### 0.7.0

- **统一日志系统**：所有诊断输出（执行器、runner、scheduler、setup）统一走 Python 标准 `logging` 模块，命名空间 `cli_test_framework`。作为库引用时可通过 `logging.getLogger("cli_test_framework").setLevel(logging.WARNING)` 完全静默。移除了原有的 `print()` + `_print_lock` ad-hoc 模式 — `logging` 模块天然线程安全。
- **默认 Handler**：首次导入时自动安装 `StreamHandler`（INFO 级别），CLI 行为不变。通过 `--verbose` / `--debug` 启用 DEBUG 级别输出。
- **公开 API**：`get_logger(name)` 通过 `cli_test_framework.get_logger` 暴露，供扩展开发统一使用。

### 0.6.0

- **Golden File 断言**：`compare_files` 成为测试 `expected` 中的一等断言，支持在测试定义中直接声明输出文件与基准文件的对比（带容差和全部比较器参数）。`file_comparator` 子系统现已集成到断言管线中，形成从命令执行到产物验证的完整闭环。

### 0.5.1
- 支持按名称筛选运行指定用例（`-t` / `test_case_filter`）

### 0.5.0
- 新增 Steps 功能，单用例内按流程顺序执行多个命令，失败即停

### 0.4.2
- 智能资源调度：自动检测 CPU 核心数，信号量管理核心分配
- 自动注入 `OMP_NUM_THREADS` / `MKL_NUM_THREADS` / `NPROC`，防止求解器线程失控
- 支持每个用例设置 `timeout`，防止卡死

### 0.4.1
- 支持多线程、多进程并行执行，效率提升 3-5 倍

## 参与协作

提交 PR 前，请确保测试全部通过：

```bash
python tests\run_all.py
```

## 许可证

MIT
