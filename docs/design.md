# CLI Test Framework 设计文档

## 1. 架构总览

```
┌─────────────────────────────────────────────────┐
│                  CLI 入口                         │
│         cli-test run / compare-files             │
└──────────┬──────────────────────┬───────────────┘
           │                      │
┌──────────▼──────────┐  ┌───────▼────────────────┐
│     Runner 体系      │  │    File Comparator     │
│  ┌───────────────┐  │  │  ┌──────────────────┐  │
│  │  BaseRunner   │  │  │  │ BaseComparator   │  │
│  │  ├JSONRunner  │  │  │  │ ├TextComparator  │  │
│  │  ├YAMLRunner  │  │  │  │ ├JsonComparator  │  │
│  │  └Parallel──► │  │  │  │ ├H5Comparator    │  │
│  │    └P-JSONRnr │  │  │  │ └BinaryComparator│  │
│  └───────────────┘  │  │  └──────────────────┘  │
│                     │  │  ComparatorFactory      │
└──────────┬──────────┘  └────────────────────────┘
           │
┌──────────▼──────────────────────────────────────┐
│                   Core 层                        │
│  TestCase │ Assertions │ Setup │ PathResolver    │
│  Execution│ Types      │Manager│ ReportGenerator │
└─────────────────────────────────────────────────┘
```

框架分为三层：**CLI 入口层**、**Runner / Comparator 业务层**、**Core 基础层**。

## 2. 模块职责

### 2.1 目录结构

```
src/cli_test_framework/
├── __init__.py                  # 包入口，导出公共 API
├── cli.py                       # cli-test 命令入口
├── core/                        # 核心抽象与基础组件
│   ├── base_runner.py           # BaseRunner 抽象基类
│   ├── parallel_runner.py       # ParallelRunner 并行基类
│   ├── execution.py             # 单测试执行逻辑
│   ├── process_worker.py        # 多进程 worker
│   ├── assertions.py            # 断言引擎
│   ├── setup.py                 # Setup 插件体系
│   ├── test_case.py             # TestCase 数据类
│   └── types.py                 # TypedDict 类型定义
├── runners/                     # 具体运行器
│   ├── json_runner.py           # JSONRunner
│   ├── yaml_runner.py           # YAMLRunner
│   └── parallel_json_runner.py  # ParallelJSONRunner
├── file_comparator/             # 文件比较子系统
│   ├── base_comparator.py       # BaseComparator 抽象基类
│   ├── result.py                # ComparisonResult / Difference
│   ├── factory.py               # ComparatorFactory 工厂
│   ├── text_comparator.py       # 文本比较
│   ├── json_comparator.py       # JSON 比较
│   ├── csv_comparator.py        # CSV 比较
│   ├── xml_comparator.py        # XML 比较
│   ├── binary_comparator.py     # 二进制比较
│   └── h5_comparator.py         # HDF5 比较
├── commands/                    # CLI 子命令
│   └── compare.py               # compare-files 入口
└── utils/                       # 工具模块
    ├── path_resolver.py         # 路径解析
    └── report_generator.py      # 报告生成
```

### 2.2 入口点

| 命令 | 映射 |
|---|---|
| `cli-test` | `cli_test_framework.cli:main` |
| `compare-files` | `cli_test_framework.commands.compare:main` |

## 3. 核心类设计

### 3.1 Runner 继承体系

```
BaseRunner (ABC)
├── JSONRunner
├── YAMLRunner
└── ParallelRunner
    └── ParallelJSONRunner
```

#### BaseRunner

所有 Runner 的抽象基类，定义测试执行的模板流程。

```python
class BaseRunner(ABC):
    def __init__(self, config_file: str, workspace: Optional[str] = None,
                 test_case_filter: Optional[List[str]] = None)
```

**模板方法 `run_tests()`**：

```
load_test_cases() → _apply_test_case_filter() → setup_manager.setup_all()
    → [run_single_test(case) for case in test_cases]  # 顺序执行
    → setup_manager.teardown_all()
```

**关键属性**：

| 属性 | 类型 | 说明 |
|---|---|---|
| `workspace` | `Path` | 工作目录 |
| `test_cases` | `List[TestCase]` | 加载后的测试用例 |
| `results` | `Dict` | 运行结果 `{total_tests, passed, failed, details}` |
| `assertions` | `Assertions` | 断言引擎实例 |
| `setup_manager` | `SetupManager` | Setup 管理器 |

**抽象方法**：

| 方法 | 职责 |
|---|---|
| `load_test_cases()` | 解析配置文件，填充 `self.test_cases` |
| `run_single_test(case)` | 执行单个测试，返回结果字典 |

**步骤序列执行 `_run_sequence(case)`**：

当 TestCase 含 `steps` 字段时，按顺序执行每个 step，某步失败则跳过后续（fail-fast）。结果标注失败步骤编号。

#### ParallelRunner

继承 BaseRunner，覆写 `run_tests()` 为并行版本。

```python
class ParallelRunner(BaseRunner):
    def __init__(self, config_file, workspace=None,
                 max_workers=None, execution_mode="thread",
                 test_case_filter=None)
```

- 线程模式：`ThreadPoolExecutor`，共享内存，支持资源调度
- 进程模式：`ProcessPoolExecutor` + `process_worker.run_test_in_process()`，进程隔离
- 线程安全：`_results_lock` / `_print_lock` 保护共享状态
- 回退方法：`run_tests_sequential()`

#### ParallelJSONRunner

在 ParallelRunner 基础上增加**资源感知调度**：

1. 加载用例后按 `estimated_time` 降序排序（LPT 策略）
2. 创建 `Semaphore(safe_capacity)` 资源池，`safe_capacity = max(1, cpu_count - 2)`
3. 每个 case 执行前 acquire `cpu_cores` 个信号量，执行后 release
4. 自动注入 `OMP_NUM_THREADS`、`MKL_NUM_THREADS`、`NPROC` 环境变量

### 3.2 TestCase 数据模型

```python
@dataclass
class TestCaseStep:
    command: str
    args: Optional[List[str]] = None
    expected: Optional[Dict] = None
    timeout: Optional[float] = None

@dataclass
class TestCase:
    name: str
    command: Optional[str] = None
    args: Optional[List[str]] = None
    expected: Optional[Dict] = None
    timeout: Optional[float] = None
    steps: Optional[List[TestCaseStep]] = None
    resources: Optional[Dict] = None
```

两种模式：
- **单命令模式**：`command` + `args` + `expected`
- **步骤序列模式**：`steps` 列表，每个 step 含 `command` + `args` + `expected`

### 3.3 Assertions

```python
class Assertions:
    def assert_return_code(self, actual, expected) -> bool
    def assert_output_contains(self, output, expected_strings) -> bool
    def assert_output_matches(self, output, expected_patterns) -> bool
```

断言逻辑：返回码精确匹配，`output_contains` 做子串匹配，`output_matches` 做正则匹配。所有断言均为可选，未指定的字段不做校验。

### 3.4 Setup 插件体系

```python
class BaseSetup(ABC):
    def __init__(self, config: Dict)
    @abstractmethod
    def setup(self) -> None
    @abstractmethod
    def teardown(self) -> None

class EnvironmentSetup(BaseSetup):
    # setup(): 设置环境变量（保存旧值）
    # teardown(): 恢复环境变量

class SetupManager:
    def add_setup(self, setup: BaseSetup) -> None
    def setup_all(self) -> None      # 按添加顺序执行
    def teardown_all(self) -> None   # 逆序执行，保证即使出错也继续清理
```

**配置文件集成**：BaseRunner.load_setup_from_config() 从 JSON/YAML 的 `setup.environment_variables` 字段自动创建 EnvironmentSetup 并注册。

### 3.5 PathResolver

```python
class PathResolver:
    SYSTEM_COMMANDS = {'echo', 'python', 'node', 'java', ...}

    def resolve_command(self, command: str) -> str
    def resolve_path(self, path: str) -> str
    def parse_command_string(self, cmd_str: str) -> Tuple[str, List[str]]
```

职责：
- 系统命令原样返回，非系统命令拼接到 workspace 路径
- 复合命令（如 `"python ./script.py"`）拆分后分别解析

### 3.6 Execution

`execute_single_test_case(case, workspace)` — 单测试的独立执行函数：

1. PathResolver 解析命令和参数
2. `subprocess.run()` 执行，捕获 stdout/stderr/returncode
3. Assertions 逐项校验
4. 返回结果字典

### 3.7 ReportGenerator

```python
class ReportGenerator:
    @staticmethod
    def generate(results: Dict, format: str) -> str  # "text" / "json" / "html"
```

## 4. 文件比较子系统

### 4.1 类继承

```
BaseComparator (ABC)
├── TextComparator     # 基于difflib行级比较
│   ├── JsonComparator # 按key字段对齐后比较
│   ├── CsvComparator  # CSV结构化比较
│   └── XmlComparator  # XML结构化比较
├── H5Comparator       # HDF5科学数据比较
└── BinaryComparator   # 二进制流式分块+LCS相似度
```

### 4.2 BaseComparator

```python
class BaseComparator(ABC):
    def __init__(self, encoding="utf-8", chunk_size=8192, verbose=False)

    @abstractmethod
    def read_content(self, file_path, start_line, end_line, start_column, end_column)

    @abstractmethod
    def compare_content(self, content1, content2) -> Tuple[bool, List[Difference]]

    def compare_files(self, file1, file2, start_line, end_line,
                      start_column, end_column) -> ComparisonResult
```

模板方法：`compare_files()` → `read_content()` × 2 → `compare_content()` → `ComparisonResult`

### 4.3 ComparatorFactory

```python
class ComparatorFactory:
    @staticmethod
    def create_comparator(file_type: str, **kwargs) -> BaseComparator
```

`file_type` 取值：`"text"` / `"json"` / `"h5"` / `"binary"`

### 4.4 ComparisonResult

```python
class ComparisonResult:
    file1: str
    file2: str
    identical: bool
    differences: List[Difference]
    error: Optional[str]
    # 支持输出: str() / to_json() / to_html()
```

### 4.5 H5Comparator 特殊设计

HDF5 比较器是框架中实现最复杂的比较器，针对科学计算场景：

- **表格选择**：`tables`（精确匹配）+ `table_regex`（正则匹配，逗号分隔多模式）
- **路径展开**：默认展开 group 下所有子数据集，可 `expand_path=False` 关闭
- **数值容差**：`rtol`（相对）+ `atol`（绝对），`np.allclose` 语义
- **数据过滤**：`data_filter` 表达式（`>1e-6`、`abs>1e-9` 等），过滤后再比较
- **分块读取**：大数据集分块处理，避免内存溢出
- **结构比较**：`structure_only=True` 只比较层级结构

## 5. 数据流

### 5.1 测试执行流

```
配置文件 (JSON/YAML)
       │
       ▼
  load_test_cases()          # 解析为 List[TestCase]
       │
       ▼
  _apply_test_case_filter()  # 按名称过滤
       │
       ▼
  setup_manager.setup_all()  # 环境变量 + 自定义插件
       │
       ▼
  ┌─────────────────────────────┐
  │  for each TestCase:         │
  │    PathResolver 解析命令     │
  │    subprocess.run() 执行    │
  │    Assertions 校验结果       │
  │    收集到 results["details"] │
  └─────────────────────────────┘
       │
       ▼
  setup_manager.teardown_all() # 逆序清理
       │
       ▼
  ReportGenerator.generate()   # text / json / html
```

### 5.2 并行执行流

```
ParallelJSONRunner.run_tests()
       │
       ▼
  LPT 排序 (estimated_time 降序)
       │
       ▼
  ┌──────────────────────────────────────┐
  │  ThreadPoolExecutor.map():           │
  │    Semaphore.acquire(cpu_cores)      │
  │    注入 OMP/MKL/NPROC 环境变量       │
  │    execute_single_test_case()        │
  │    Semaphore.release(cpu_cores)      │
  │    _update_results() (线程安全)      │
  └──────────────────────────────────────┘
```

### 5.3 文件比较流

```
compare-files file1 file2 [options]
       │
       ▼
  自动检测 / 指定 file_type
       │
       ▼
  ComparatorFactory.create_comparator(file_type, **kwargs)
       │
       ▼
  comparator.compare_files(file1, file2, ...)
       │
       ├── read_content() × 2
       ├── compare_content()
       └── ComparisonResult
       │
       ▼
  format_result(result, output_format)  # text / json / html
```

## 6. 扩展点

| 扩展点 | 基类 | 用途 |
|---|---|---|
| 新配置格式 | `BaseRunner` | 支持新的测试定义格式（如 XML、TOML） |
| 自定义 Setup | `BaseSetup` | 数据库初始化、服务启停等 |
| 自定义断言 | `BaseAssertion` | 特定业务校验逻辑 |
| 新比较器 | `BaseComparator` | 支持新的文件格式比较 |
| 新 Runner | `ParallelRunner` | 自定义并行策略 |

## 7. 设计决策

| 决策 | 原因 |
|---|---|
| Runner 用模板方法模式 | 统一执行流程（load → filter → setup → run → teardown），子类只需实现配置解析和单测试执行 |
| Setup 逆序 teardown | 类似栈语义，后初始化的依赖先清理 |
| 信号量管理 CPU 核心 | 比线程池 worker 数更精细，允许不同 case 声明不同核心需求 |
| LPT 调度策略 | 长任务先启动，减少尾延迟，提升整体吞吐 |
| 环境变量注入 | 科学计算求解器常忽略 Python 级线程控制，需通过 `OMP_NUM_THREADS` 等底层变量约束 |
| Comparator 工厂模式 | 按文件类型创建比较器，CLI 和 Python API 共用 |
| subprocess 隔离执行 | 每个 test case 独立子进程，保证测试间互不影响 |
