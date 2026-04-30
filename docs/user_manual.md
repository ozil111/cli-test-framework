# CLI Test Framework 使用说明书

## 目录

- [安装](#安装)
- [测试用例定义](#测试用例定义)
- [运行测试](#运行测试)
- [Setup 模块](#setup-模块)
- [并行测试](#并行测试)
- [顺序步骤测试](#顺序步骤测试)
- [资源感知调度](#资源感知调度)
- [文件比较](#文件比较)
- [扩展开发](#扩展开发)

## 安装

```bash
pip install cli-test-framework
```

要求：Python >= 3.9

YAML 支持需额外安装：

```bash
pip install pyyaml
```

## 测试用例定义

### JSON 格式

```json
{
    "test_cases": [
        {
            "name": "测试名称",
            "command": "echo",
            "args": ["Hello"],
            "timeout": 60,
            "resources": {
                "cpu_cores": 2,
                "estimated_time": 300,
                "min_memory_mb": 1024,
                "priority": 5
            },
            "expected": {
                "return_code": 0,
                "output_contains": ["Hello"],
                "output_matches": [".*regex.*"]
            }
        }
    ]
}
```

### YAML 格式

```yaml
test_cases:
  - name: 测试名称
    command: echo
    args: ["Hello"]
    timeout: 60
    resources:
      cpu_cores: 2
      estimated_time: 300
      min_memory_mb: 1024
      priority: 5
    expected:
      return_code: 0
      output_contains:
        - "Hello"
      output_matches:
        - ".*regex.*"
```

### 字段说明

| 字段 | 必填 | 说明 |
|---|---|---|
| `name` | 是 | 测试用例名称 |
| `command` | 是 | 要执行的命令 |
| `args` | 否 | 命令参数列表 |
| `timeout` | 否 | 超时秒数，默认 3600，设 `null` 无限制 |
| `resources` | 否 | 资源配置，见[资源感知调度](#资源感知调度) |
| `expected.return_code` | 否 | 期望返回码 |
| `expected.output_contains` | 否 | 输出需包含的字符串列表 |
| `expected.output_matches` | 否 | 输出需匹配的正则列表 |

## 运行测试

### 命令行

```bash
# 运行 JSON 测试
cli-test run test_cases.json

# 运行 YAML 测试
cli-test run test_cases.yaml

# 指定工作目录
cli-test run test_cases.json --workspace /path/to/project

# 并行运行
cli-test run test_cases.json --parallel --workers 4

# 指定并行模式
cli-test run test_cases.json --parallel --execution-mode process

# 只运行指定用例
cli-test run test_cases.json -t test_name_1 -t test_name_2

# 详细输出
cli-test run test_cases.json --verbose

# 调试模式
cli-test run test_cases.json --debug

# 输出格式
cli-test run test_cases.json --output-format json|html|text
```

### Python API

```python
from cli_test_framework.runners import JSONRunner, YAMLRunner, ParallelJSONRunner

# 顺序运行
runner = JSONRunner(
    config_file="test_cases.json",
    workspace="/path/to/project",    # 可选，默认项目根目录
    test_case_filter=["test_1"]      # 可选，只运行指定用例
)
success = runner.run_tests()

# YAML 格式
runner = YAMLRunner(config_file="test_cases.yaml")

# 并行运行
runner = ParallelJSONRunner(
    config_file="test_cases.json",
    max_workers=4,                   # 可选，默认 CPU 核心数
    execution_mode="thread",         # "thread" 或 "process"
    test_case_filter=["test_1"]
)
success = runner.run_tests()
```

### 获取结果

```python
runner.run_tests()

# 汇总
runner.results["total_tests"]
runner.results["passed"]
runner.results["failed"]

# 详情
for detail in runner.results["details"]:
    print(detail["name"], detail["status"], detail.get("message", ""))
```

## Setup 模块

Setup 模块在测试前执行初始化、测试后执行清理。

### 环境变量（配置文件方式）

JSON：

```json
{
    "setup": {
        "environment_variables": {
            "TEST_ENV": "development",
            "API_URL": "http://localhost:8080"
        }
    },
    "test_cases": [...]
}
```

YAML：

```yaml
setup:
  environment_variables:
    TEST_ENV: "development"
    API_URL: "http://localhost:8080"
test_cases:
  [...]
```

配置文件中的环境变量会在测试前设置、测试后恢复原值。

### 自定义 Setup 插件

```python
from cli_test_framework import BaseSetup, JSONRunner

class DatabaseSetup(BaseSetup):
    def setup(self):
        # 初始化操作
        pass

    def teardown(self):
        # 清理操作（即使测试失败也会执行）
        pass

runner = JSONRunner("test_cases.json")
runner.setup_manager.add_setup(DatabaseSetup({"connection": "test_db"}))
success = runner.run_tests()
```

多个插件按添加顺序执行 setup，按逆序执行 teardown。

### 执行顺序

1. 加载配置文件中的 setup 配置（环境变量等）
2. 执行所有 setup 插件的 `setup()`（按添加顺序）
3. 运行测试
4. 执行所有 setup 插件的 `teardown()`（逆序，保证执行）

## 并行测试

```python
from cli_test_framework.runners import ParallelJSONRunner

runner = ParallelJSONRunner(
    config_file="test_cases.json",
    max_workers=4,                # 最大并发数，默认 CPU 核心数
    execution_mode="thread"       # "thread" 或 "process"
)
success = runner.run_tests()

# 回退到顺序执行
runner.run_tests_sequential()
```

**线程模式**：共享内存，支持资源感知调度（见下节）。  
**进程模式**：进程隔离，不支持资源调度。

## 顺序步骤测试

一个测试用例可包含多个有序步骤，某步失败则跳过后续步骤（fail-fast）。

### JSON

```json
{
    "test_cases": [
        {
            "name": "多步骤测试",
            "steps": [
                {
                    "command": "echo",
                    "args": ["step1"],
                    "expected": { "return_code": 0 }
                },
                {
                    "command": "echo",
                    "args": ["step2"],
                    "expected": { "return_code": 0 }
                }
            ]
        }
    ]
}
```

### YAML

```yaml
test_cases:
  - name: 多步骤测试
    steps:
      - command: echo
        args: ["step1"]
        expected:
          return_code: 0
      - command: echo
        args: ["step2"]
        expected:
          return_code: 0
```

每个 step 支持 `command`、`args`、`expected`、`timeout` 字段。失败时结果会标注失败步骤编号，如 "Failed at step 2/3"。

## 资源感知调度

仅线程模式生效。通过 `resources` 字段配置，框架自动管理 CPU 核心分配。

```json
{
    "name": "Heavy_Simulation",
    "command": "solver",
    "args": ["-i", "input.dat"],
    "timeout": 36000,
    "resources": {
        "cpu_cores": 4,
        "estimated_time": 18000,
        "min_memory_mb": 16000,
        "priority": 10
    },
    "expected": { "return_code": 0 }
}
```

| 字段 | 说明 |
|---|---|
| `cpu_cores` | 所需 CPU 核心数，默认 1。框架用信号量控制分配，超限任务排队等待 |
| `estimated_time` | 预估耗时（秒），用于 LPT 调度（长任务优先启动） |
| `min_memory_mb` | 预估内存（MB），目前仅用于日志警告 |
| `priority` | 优先级 0-10，目前仅用于信息标注 |

框架行为：
- 自动检测 CPU 核心数，预留 2 核给系统
- 任务启动时自动注入 `OMP_NUM_THREADS`、`MKL_NUM_THREADS`、`NPROC` 环境变量，防止求解器线程失控
- 按 `estimated_time` 降序调度（LPT 策略）

## 文件比较

### 命令行工具 `compare-files`

```bash
compare-files <file1> <file2> [选项]
```

### 通用选项

| 选项 | 说明 |
|---|---|
| `--file-type` | 文件类型：`auto`（默认）、`text`、`json`、`h5`、`binary` |
| `--start-line` | 起始行号（1-based），默认 1 |
| `--end-line` | 结束行号（1-based） |
| `--start-column` | 起始列号（1-based），默认 1 |
| `--end-column` | 结束列号（1-based） |
| `--encoding` | 文本编码，默认 `utf-8` |
| `--output-format` | 输出格式：`text`、`json`、`html` |
| `--verbose` / `-v` | 详细输出 |
| `--debug` | 调试模式 |
| `--num-threads` | 并行线程数，默认 4 |

### 文本文件比较

```bash
compare-files file1.txt file2.txt --start-line 10 --end-line 20
```

### JSON 文件比较

```bash
# 精确比较（默认）
compare-files data1.json data2.json

# 按 key 字段比较
compare-files data1.json data2.json --json-compare-mode key-based --json-key-field id
```

| 选项 | 说明 |
|---|---|
| `--json-compare-mode` | `exact`（默认）或 `key-based` |
| `--json-key-field` | key-based 模式的匹配字段，支持逗号分隔多字段 |

### HDF5 文件比较

```bash
# 比较指定表
compare-files data1.h5 data2.h5 --h5-table table1,table2

# 用正则匹配表名
compare-files data1.h5 data2.h5 --h5-table-regex "result_.*"

# 逗号分隔多个正则
compare-files data1.h5 data2.h5 --h5-table-regex "table1,table2,table3"

# 数值容差
compare-files data1.h5 data2.h5 --h5-rtol 1e-5 --h5-atol 1e-8

# 数据过滤（只比较满足条件的数据）
compare-files data1.h5 data2.h5 --h5-data-filter '>1e-6'
compare-files data1.h5 data2.h5 --h5-data-filter 'abs>1e-9'
compare-files data1.h5 data2.h5 --h5-data-filter '<=0.01'

# 禁止自动展开 group 路径
compare-files data1.h5 data2.h5 --h5-table group1 --h5-no-expand-path
```

| 选项 | 说明 |
|---|---|
| `--h5-table` | 指定表名，逗号分隔 |
| `--h5-table-regex` | 正则匹配表名，逗号分隔多个模式 |
| `--h5-structure-only` | 只比较结构，不比较内容 |
| `--h5-show-content-diff` | 显示内容差异详情 |
| `--h5-rtol` | 相对容差，默认 1e-5 |
| `--h5-atol` | 绝对容差，默认 1e-8 |
| `--h5-data-filter` | 数据过滤表达式：`>`, `>=`, `<`, `<=`, `==`，支持 `abs` 前缀 |
| `--h5-no-expand-path` | 禁止自动展开 group 路径下的子项 |

### 二进制文件比较

```bash
compare-files binary1.bin binary2.bin --similarity --chunk-size 16384
```

| 选项 | 说明 |
|---|---|
| `--similarity` | 计算相似度指数 |
| `--chunk-size` | 读取块大小，默认 8192 |

### Python API

```python
from cli_test_framework.file_comparator import ComparatorFactory

# 文本比较
comparator = ComparatorFactory.create_comparator("text", encoding="utf-8", verbose=True)
result = comparator.compare_files("file1.txt", "file2.txt")

# JSON 比较
comparator = ComparatorFactory.create_comparator("json", compare_mode="key-based", key_field="id")
result = comparator.compare_files("data1.json", "data2.json")

# HDF5 比较
comparator = ComparatorFactory.create_comparator("h5", tables=["table1"], rtol=1e-5)
result = comparator.compare_files("data1.h5", "data2.h5")

# 结果
result.identical   # bool
result.differences # list
```

## 扩展开发

### 自定义 Runner

```python
from cli_test_framework.runners import BaseRunner

class CustomRunner(BaseRunner):
    def load_test_cases(self):
        # 加载测试用例到 self.test_cases
        pass

    def run_single_test(self, test_case):
        # 执行单个测试，返回结果字典
        pass
```

### 自定义 Setup 插件

```python
from cli_test_framework import BaseSetup

class MySetup(BaseSetup):
    def setup(self):
        # self.config 可获取传入的配置字典
        pass

    def teardown(self):
        pass
```

### 自定义断言

```python
from cli_test_framework.assertions import BaseAssertion

class CustomAssertion(BaseAssertion):
    def assert_custom_condition(self, actual, expected):
        if not self._check(actual, expected):
            raise AssertionError("Condition not met")
```
