# CLI Test Framework 使用说明书

## 目录

- [安装](#安装)
- [测试用例定义](#测试用例定义)
- [配置拆分机制](#配置拆分机制)
- [配置校验](#配置校验)
- [运行测试](#运行测试)
- [标签过滤](#标签过滤)
- [Setup 模块](#setup-模块)
- [并行测试](#并行测试)
- [顺序步骤测试](#顺序步骤测试)
- [资源感知调度](#资源感知调度)
- [历史记录与回归检测](#历史记录与回归检测)
- [JUnit XML 报告](#junit-xml-报告)
- [日志配置](#日志配置)
- [文件比较](#文件比较)
- [扩展开发](#扩展开发)
- [运行框架自带测试](#运行框架自带测试)

## 安装

```bash
pip install cli-test-framework
```

要求：Python >= 3.9

YAML 支持需额外安装：

```bash
pip install pyyaml
```

HDF5 文件比较依赖 `h5py`（已随框架安装）。如需在无 HDF5 环境下使用其他比较功能，可单独卸载，但 HDF5 比较将不可用。

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
                "output_matches": ".*regex.*",
                "compare_files": [
                    {
                        "actual": "output.txt",
                        "baseline": "baseline.txt",
                        "type": "text"
                    }
                ]
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
      output_matches: ".*regex.*"
      compare_files:
        - actual: output.txt
          baseline: baseline.txt
          type: text
```

### 字段说明

| 字段 | 必填 | 说明 |
|---|---|---|
| `name` | 是 | 测试用例名称 |
| `command` | 是 | 要执行的命令（支持带参数的命令字符串，如 `python ./run.py`，框架会自动拆分并解析路径） |
| `args` | 否 | 命令参数列表 |
| `description` | 否 | 测试用例描述 |
| `timeout` | 否 | 超时秒数，默认 3600，设 `null` 无限制 |
| `tags` | 否 | 标签列表，用于批量过滤（如 `["smoke", "fast"]`） |
| `resources` | 否 | 资源配置，见[资源感知调度](#资源感知调度) |
| `expected.return_code` | 否 | 期望返回码 |
| `expected.output_contains` | 否 | 输出需包含的字符串列表 |
| `expected.output_matches` | 否 | 输出需匹配的正则表达式（单个字符串） |
| `expected.compare_files` | 否 | 文件比较断言列表，见下文 |

### 文件比较断言（compare_files）

在 `expected` 中通过 `compare_files` 可声明一条或多条文件比较规则，框架会在命令执行后自动用对应的比较器对比实际产出文件与基线文件。所有比较通过才算用例通过，可与 `return_code`、`output_contains` 等断言共存。

每个比较规则的字段：

| 字段 | 必填 | 说明 |
|---|---|---|
| `actual` | 是 | 测试命令产出的文件路径（相对路径按 workspace 解析） |
| `baseline` | 是 | 基线/参考文件路径（相对路径按 workspace 解析） |
| `type` | 否 | 比较器类型：`text`、`json`、`csv`、`xml`、`h5`、`binary`；省略时按扩展名自动识别 |
| 其他 | 否 | 透传给对应比较器的参数，如 `rtol`、`atol`、`encoding`、`tables`、`data_filter` 等 |

```json
"expected": {
    "return_code": 0,
    "compare_files": [
        {
            "actual": "result.h5",
            "baseline": "baseline/result.h5",
            "type": "h5",
            "rtol": 1e-5,
            "atol": 1e-8,
            "tables": ["/stress", "/displacement"]
        },
        {
            "actual": "summary.csv",
            "baseline": "baseline/summary.csv"
        }
    ]
}
```

## 配置拆分机制

当测试项目规模增长、用例数量达到数十甚至数百条时，单个配置文件可能变得难以维护。配置拆分机制允许将大文件按模块/功能拆分为多个子文件，通过 `import` 引用组装，运行时自动合并加载。

### 主配置文件

在主配置文件中，通过 `"import"` 字段引用子文件。`import` 是 `test_cases` 数组中的一个特殊元素，框架会在加载时将其**展开替换**为子文件的测试用例：

```json
{
    "setup": {
        "environment_variables": {
            "PYTHONPATH": "./src"
        }
    },
    "test_cases": [
        {
            "name": "内联测试用例",
            "command": "echo",
            "args": ["hello"],
            "expected": { "return_code": 0 }
        },
        { "import": "cases/text_tests.json" },
        { "import": "cases/json_tests.yaml" },
        { "import": "cases/h5_tests.json" }
    ]
}
```

> **注意**：`import` 路径相对**主配置文件所在目录**解析，不相对当前工作目录（cwd）。这保证了配置文件的可移植性——无论从哪个目录运行测试，拆分关系都不受影响。

### 子文件格式

子文件结构与主文件一致，顶层同样是 `test_cases` 数组（可包含 `setup`）：

```json
{
    "test_cases": [
        {
            "name": "text_identical",
            "command": "python",
            "args": ["./compare_text.py"],
            "expected": { "return_code": 0 },
            "tags": ["text"]
        },
        {
            "name": "text_diff",
            "command": "python",
            "args": ["./compare_text.py", "--mode", "diff"],
            "expected": { "return_code": 1 },
            "tags": ["text"]
        }
    ]
}
```

### 工作原理

1. **加载时展开**：Runner 在读取配置文件后、解析 `TestCase` 对象前，自动执行 import 展开。对 Runner 和执行引擎**完全透明**，无需修改测试用例或 Runner 代码。
2. **递归展开**：子文件内可以继续 `import` 其他文件，支持多层嵌套。
3. **循环引用保护**：框架维护已加载文件路径集合，检测到循环引用时抛出明确错误。
4. **向后兼容**：不含 `import` 字段的配置文件行为与之前完全一致，零迁移成本。

### 跨格式支持

主配置为 JSON 时可以 import YAML 子文件，反之亦然。框架根据子文件扩展名（`.json` / `.yaml` / `.yml`）自动选择解析器。

### Setup 合并规则

如果主文件和子文件都定义了 `setup`，它们会深度合并（deep merge）：
- **同名变量冲突**：子文件的 `setup` 覆盖主文件的同名字段。
- **环境变量**：合并为一个字典，子文件优先。

```json
// 主文件 setup
{ "environment_variables": { "BASE": "from_main", "OVERRIDE": "from_main" } }

// 子文件 setup
{ "environment_variables": { "SUB_KEY": "from_sub", "OVERRIDE": "from_sub" } }

// 合并结果
{ "environment_variables": {
    "BASE": "from_main",
    "SUB_KEY": "from_sub",
    "OVERRIDE": "from_sub"  // 子文件覆盖
} }
```

### 渐进式迁移

无需一次性迁移所有配置：
1. 先用 `validate` 命令确认现有配置无问题（见[配置校验](#配置校验)）
2. 逐步将大文件中的部分用例移到子文件，用 `import` 引用
3. 内联用例与 import 引用可在同一个 `test_cases` 数组中混合使用

## 配置校验

`validate` 命令在不运行测试的情况下检查配置文件的正确性，适合在 CI 流水线中做配置合法性检查。

### 用法

```bash
# 校验单个配置文件
cli-test validate test_cases.json

# 校验带 import 的主配置（自动展开并检查所有子文件）
cli-test validate main_config.json

# 指定工作目录
cli-test validate test_cases.json --workspace /path/to/project
```

### 校验内容

| 检查项 | 说明 |
|---|---|
| 语法正确性 | JSON/YAML 格式是否合法（加载时隐式检查） |
| 必填字段 | 每条用例是否包含 `name`、`command`、`args`、`expected`（序列模式检查每个 step） |
| import 引用 | 被引用的子文件是否存在 |
| 循环引用 | import 链中是否存在 A→B→A 的循环 |

### 输出示例

成功时：
```
  [OK] Loaded 15 test cases from 3 file(s)
  [OK] All required fields present
  [OK] No circular imports detected

  Files:
    - /project/main_config.json
    - /project/cases/text_tests.json
    - /project/cases/json_tests.yaml
```

有错误时：
```
  [OK] Loaded 3 test cases from 1 file(s)
  [FAIL] case 'bad_case': missing required field 'expected'
  [FAIL] Import target not found: /project/cases/nonexistent.json
```

## 运行测试

### 命令行

```bash
# 运行 JSON 测试
cli-test run test_cases.json

# 运行 YAML 测试
cli-test run test_cases.yaml

# 运行带 import 拆分的主配置（自动展开子文件）
cli-test run main_config.json

# 指定工作目录
cli-test run test_cases.json --workspace /path/to/project

# 并行运行
cli-test run test_cases.json --parallel --workers 4

# 指定并行模式
cli-test run test_cases.json --parallel --execution-mode process

# 只运行指定用例
cli-test run test_cases.json -t test_name_1 -t test_name_2

# 按标签过滤
cli-test run test_cases.json --tag smoke
cli-test run test_cases.json --tag smoke --tag regression

# 同时按名称和标签过滤（AND 关系）
cli-test run test_cases.json -t test_name_1 --tag smoke

# 详细输出
cli-test run test_cases.json --verbose

# 调试模式
cli-test run test_cases.json --debug

# 输出格式
cli-test run test_cases.json --output-format json|html|text

# 启用历史记录（智能调度 + 回归检测）
cli-test run test_cases.json --history-dir ./hist

# 自定义回归检测阈值（默认 1.5 倍）
cli-test run test_cases.json --history-dir ./hist --regression-threshold 2.0

# 输出 JUnit XML 报告（可供 Jenkins/GitLab CI 等工具解析）
cli-test run test_cases.json --junit-xml report.xml
```

### Python API

```python
from cli_test_framework.runners import JSONRunner, YAMLRunner, ParallelJSONRunner

# 顺序运行
runner = JSONRunner(
    config_file="test_cases.json",
    workspace="/path/to/project",    # 可选，默认项目根目录
    test_case_filter=["test_1"],     # 可选，只运行指定用例
    test_case_tag_filter=["smoke"],  # 可选，只运行包含指定标签的用例
    history_dir="./hist",            # 可选，启用历史记录与回归检测
    regression_threshold=2.0,        # 可选，回归阈值倍数，默认 1.5
)
success = runner.run_tests()

# YAML 格式
runner = YAMLRunner(config_file="test_cases.yaml")

# 并行运行（JSON）
runner = ParallelJSONRunner(
    config_file="test_cases.json",
    max_workers=4,                   # 可选，默认 CPU 核心数
    execution_mode="thread",         # "thread" 或 "process"
    test_case_filter=["test_1"],
    history_dir="./hist",            # 可选，启用历史记录与智能调度
    regression_threshold=2.0,        # 可选，回归阈值倍数，默认 1.5
)
success = runner.run_tests()

# 并行运行（YAML）
from cli_test_framework.runners import ParallelYAMLRunner
runner = ParallelYAMLRunner(
    config_file="test_cases.yaml",
    max_workers=4,
    execution_mode="thread",
)
success = runner.run_tests()
```

### 获取结果

```python
runner.run_tests()

# 汇总
runner.results["total"]
runner.results["passed"]
runner.results["failed"]

# 详情
for detail in runner.results["details"]:
    print(detail["name"], detail["status"], detail.get("message", ""))
```

## 标签过滤

通过标签（tags）可以对测试用例进行分类，并在运行时按标签批量过滤。标签过滤与名称过滤可同时使用，满足 AND 关系（两个条件都必须满足）。

### 在测试用例中定义标签

JSON：

```json
{
    "test_cases": [
        {
            "name": "快速测试",
            "command": "echo",
            "args": ["hello"],
            "tags": ["smoke", "fast"],
            "expected": { "return_code": 0 }
        },
        {
            "name": "完整回归测试",
            "command": "python",
            "args": ["long_test.py"],
            "tags": ["regression", "slow"],
            "expected": { "return_code": 0 }
        }
    ]
}
```

YAML：

```yaml
test_cases:
  - name: 快速测试
    command: echo
    args: ["hello"]
    tags: ["smoke", "fast"]
    expected:
      return_code: 0
```

`tags` 是可选字段，不指定则默认为空列表。每个用例可以有多个标签。

### 运行时过滤

```bash
# 只运行带 "smoke" 标签的用例
cli-test run test_cases.json --tag smoke

# 运行带 "smoke" 或 "regression" 标签的用例（OR 关系）
cli-test run test_cases.json --tag smoke --tag regression

# 同时按名称和标签过滤（AND 关系）
cli-test run test_cases.json -t alpha --tag fast
```

### Python API

```python
runner = JSONRunner(
    config_file="test_cases.json",
    test_case_tag_filter=["smoke"],     # 只运行含 smoke 标签的用例
)
success = runner.run_tests()

# 结合名称过滤
runner = JSONRunner(
    config_file="test_cases.json",
    test_case_filter=["alpha", "beta"],
    test_case_tag_filter=["fast"],
)
success = runner.run_tests()
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
- 按 `estimated_time` 降序调度（LPT 策略）；若启用 `--history-dir`，优先使用历史 `avg_duration` 排序

## 历史记录与回归检测

通过 `--history-dir` 指定一个目录，框架会在该目录下维护一个 `.symtest` 文件，记录每个 case 的历史运行时间。

### 工作原理

1. **首次运行**：目录下没有 `.symtest`，自动创建空文件，排序仍使用配置中的 `estimated_time`
2. **后续运行**：读取 `.symtest` 中的历史数据，优先使用 `avg_duration` 做调度排序
3. **回归检测**：每次运行结束后，如果某 case 耗时超过历史均值的阈值倍数（默认 1.5），打印警告

### CLI 用法

```bash
# 启用历史记录
cli-test run test_cases.json --history-dir ./hist

# 自定义回归阈值（超过 2 倍均值才警告）
cli-test run test_cases.json --history-dir ./hist --regression-threshold 2.0
```

### Python API

```python
from cli_test_framework.runners import JSONRunner, ParallelJSONRunner

# 顺序运行 + 历史记录
runner = JSONRunner(
    config_file="test_cases.json",
    history_dir="./hist",
    regression_threshold=2.0,  # 可选，默认 1.5
)
success = runner.run_tests()

# 并行运行 + 历史记录（调度排序也会使用历史数据）
runner = ParallelJSONRunner(
    config_file="test_cases.json",
    history_dir="./hist",
)
success = runner.run_tests()
```

### .symtest 文件格式

```json
{
  "version": 1,
  "cases": {
    "case_name_1": {
      "avg_duration": 3.5,
      "last_duration": 3.2,
      "run_count": 5
    }
  }
}
```

| 字段 | 说明 |
|---|---|
| `avg_duration` | 累计平均耗时（秒），用于调度排序和回归基线 |
| `last_duration` | 最近一次运行耗时 |
| `run_count` | 历史运行次数 |

### 回归警告示例

当某 case 运行时间超过历史均值的阈值倍数时：

```
⚠ WARNING: Case 'heavy_simulation' regressed: 18.2s vs avg 10.5s (1.73x slower)
```

### 不启用历史记录

不传 `--history-dir` 时行为与之前完全一致，不创建任何额外文件。

## JUnit XML 报告

通过 `--junit-xml` 可在运行测试的同时输出 JUnit 格式的 XML 报告，兼容 Jenkins、GitLab CI、CircleCI 等 CI 工具。

### CLI 用法

```bash
cli-test run test_cases.json --junit-xml report.xml
```

`--junit-xml` 是补充输出，与 `--output-format`（text/json/html）并存，不影响控制台报告。

### Python API

```python
from cli_test_framework import write_junit_xml

runner.run_tests()
write_junit_xml(runner.results, "report.xml", suite_name="my_suite")
```

状态映射：`passed` 记为通过；`failed`（断言失败）记为 failure；`timeout` 与执行错误记为 error。每个 testcase 元素附带命令输出与失败原因。

## 日志配置

框架所有诊断与状态信息都通过 Python 标准 `logging` 模块输出，统一挂在 `cli_test_framework` 命名空间下。日志默认写入 **stderr**，因此 `stdout` 始终保持干净，可安全配合 `--output-format json` 做机器可读输出。

### 命令行控制日志级别

`run` 与 `compare` 子命令均支持：

| 选项 | 说明 |
|---|---|
| `--verbose` / `-v` | 详细输出，日志级别提升至 DEBUG |
| `--debug` | 调试模式，同样提升至 DEBUG，并在出错时打印完整堆栈 |

默认级别为 INFO，仅显示关键进度与错误；加 `--verbose` 或 `--debug` 后会输出命令输出、调度细节等 DEBUG 级信息。

```bash
# 详细模式（含命令输出等 DEBUG 信息）
cli-test run test_cases.json --verbose

# 调试模式（出错时打印堆栈）
cli-test run test_cases.json --debug
```

### 库使用方式

作为库被 import 时，框架默认只挂载 `NullHandler`，不产生任何输出（符合库的礼貌日志规范）。需要看到日志时，调用 `setup_console_logging()` 启用控制台输出：

```python
import logging
from cli_test_framework.logging_config import setup_console_logging, get_logger

# 启用控制台日志（stderr），可指定级别
setup_console_logging(level=logging.DEBUG)

logger = get_logger(__name__)   # 自动归入 cli_test_framework 命名空间
logger.info("自定义日志信息")
```

### 输出到日志文件

框架未内置 `--log-file` 选项，但可借助 Python 标准 `logging` 自行为 `cli_test_framework` logger 添加文件处理器：

```python
import logging
from cli_test_framework.logging_config import get_logger

file_handler = logging.FileHandler("run.log", encoding="utf-8")
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(
    logging.Formatter("%(asctime)s %(levelname)-7s %(name)s %(message)s")
)

# 给框架根 logger 加文件处理器，所有子 logger 都会继承
logging.getLogger("cli_test_framework").addHandler(file_handler)
```

上述代码既适用于库调用，也可放在脚本中配合 `cli-test` 一起使用。控制台与文件处理器可并存。

## 文件比较

框架提供独立的文件比较能力，支持文本、JSON、CSV、XML、HDF5、二进制等多种格式。既可通过命令行工具使用，也可在测试用例的 `expected.compare_files` 中自动调用（见[文件比较断言](#文件比较断言compare_files)）。

### 命令行工具

有两种等价的调用方式，参数完全一致：

```bash
# 独立命令
compare-files <file1> <file2> [选项]

# cli-test 子命令
cli-test compare <file1> <file2> [选项]
```

### 通用选项

| 选项 | 说明 |
|---|---|
| `--file-type` | 文件类型：`auto`（默认）、`text`、`json`、`csv`、`xml`、`h5`、`binary` |
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

### CSV 文件比较

```bash
# 基本比较
compare-files data1.csv data2.csv

# 自定义分隔符与数值容差
compare-files data1.csv data2.csv --csv-delimiter ';' --csv-rtol 1e-4 --csv-atol 1e-6

# TSV 文件（自动识别为 csv 类型）
compare-files data1.tsv data2.tsv
```

| 选项 | 说明 |
|---|---|
| `--csv-rtol` | 数值相对容差，默认 1e-5 |
| `--csv-atol` | 数值绝对容差，默认 1e-8 |
| `--csv-delimiter` | 字段分隔符，默认 `,` |
| `--csv-quotechar` | 引用字符，默认 `"` |

CSV 比较按行列结构逐单元格比对；数值单元格在容差范围内视为相等。差异报告包含行数、列数不匹配与单元格不一致，最多列出 10 条。

### XML 文件比较

```bash
# 结构化比较（标签、属性、文本、子元素）
compare-files config1.xml config2.xml

# HTML 文件（自动识别为 xml 类型）
compare-files page1.html page2.html
```

XML 比较按 DOM 结构递归比对标签、属性、文本内容与子元素数量。差异报告定位到具体路径（如 `/root/item[0]/@id`），最多列出 10 条。

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

# CSV 比较
comparator = ComparatorFactory.create_comparator("csv", rtol=1e-5, atol=1e-8, delimiter=",")
result = comparator.compare_files("data1.csv", "data2.csv")

# XML 比较
comparator = ComparatorFactory.create_comparator("xml", encoding="utf-8")
result = comparator.compare_files("config1.xml", "config2.xml")

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
from cli_test_framework.core.base_runner import BaseRunner

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

### 自定义文件比较器

`ComparatorFactory` 会在首次使用时自动扫描 `file_comparator` 包内所有 `*_comparator.py` 模块并注册其中的 `*Comparator` 类。如需注册自定义比较器，调用 `register_comparator` 即可：

```python
from cli_test_framework.file_comparator import ComparatorFactory
from cli_test_framework.file_comparator.base_comparator import BaseComparator

class FooComparator(BaseComparator):
    # 实现 read_content / compare_content 等方法
    pass

ComparatorFactory.register_comparator("foo", FooComparator)

# 之后即可在 compare_files 断言或命令行 --file-type foo 中使用
comparator = ComparatorFactory.create_comparator("foo")
```

### 断言与文件比较

`Assertions` 类提供静态断言方法，`expected` 中的校验均由其完成：

```python
from cli_test_framework.core.assertions import Assertions

Assertions.return_code_equals(actual_code, 0)
Assertions.contains(output, "expected text")
Assertions.matches(output, r".*regex.*")
Assertions.compare_files("actual.txt", "baseline.txt", file_type="text", workspace="/ws")
```

`compare_files` 会自动按扩展名识别类型（`.h5/.hdf5/.hdf`→h5、`.json`→json、`.csv/.tsv`→csv、`.xml/.html/.htm`→xml、`.txt/.log/.out/.py`→text、其余→binary），相对路径按 `workspace` 解析，额外参数透传给比较器。

## 运行框架自带测试

项目自带统一测试入口 `tests/run_all.py`，通过 `--scope` 选择测试范围（test target），并可用 `--extra` 透传任意 pytest 参数。

### 测试范围

| scope | 说明 | 对应目录 |
|---|---|---|
| `unit` | 单元测试（core、runners 等） | `tests/unit` |
| `integration` | 集成测试（文件比较、并行、路径处理等） | `tests/integration` |
| `e2e` | 端到端测试（用户流程） | `tests/e2e` |
| `all` | 运行上述全部范围（默认） | 三者合集 |

> 注：`tests/demos/` 下的脚本为手动/交互演示，不纳入 scope 运行，需单独执行。

### 用法

```bash
# 运行全部测试（默认）
python tests/run_all.py

# 只运行单元测试
python tests/run_all.py --scope unit

# 只运行集成测试
python tests/run_all.py --scope integration

# 只运行端到端测试
python tests/run_all.py --scope e2e

# 透传 pytest 参数，例如按关键字过滤
python tests/run_all.py --scope integration --extra "-k h5"

# 透传多个 pytest 参数
python tests/run_all.py --scope unit --extra "-v -k assertions"
```

`--extra` 接收的字符串会经 `shlex` 拆分后追加到 pytest 命令行。脚本通过当前解释器（`sys.executable -m pytest`）调用 pytest，确保使用激活的环境而非 PATH 中首个 `pytest`。

测试环境需先激活 conda 环境：

```bash
conda activate xiaotong
python tests/run_all.py
```
