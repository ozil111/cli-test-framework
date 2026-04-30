# CLI 测试框架

轻量级命令行自动化测试框架，用 JSON/YAML 定义测试用例，一行命令跑完所有验证。

特别适合科学计算场景——对 HDF5 结果文件有深度支持：正则匹配表格、数据过滤、容差对比，轻松搞定仿真结果校验。

## 功能亮点

- **并行执行** — 多线程/多进程，3-5 倍加速
- **资源感知调度** — 自动管理 CPU 核心分配，防止求解器线程失控
- **顺序步骤测试** — 单个用例内多步执行，失败即停
- **Setup 模块** — 测试前自动配置环境变量，测试后自动清理
- **文件比较** — 文本 / JSON / HDF5 / 二进制，命令行直接用
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

### 文件比较

```bash
compare-files result1.h5 result2.h5 --h5-table-regex "output_.*" --h5-rtol 1e-5
```

📖 **完整使用说明**：[docs/user_manual.md](docs/user_manual.md)

## 更新日志

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

## 许可证

MIT
