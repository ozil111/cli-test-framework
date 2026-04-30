# CLI Test Framework Design Document

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────┐
│                  CLI Entry                       │
│         cli-test run / compare-files             │
└──────────┬──────────────────────┬───────────────┘
           │                      │
┌──────────▼──────────┐  ┌───────▼────────────────┐
│     Runner System    │  │    File Comparator     │
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
│                   Core Layer                     │
│  TestCase │ Assertions │ Setup │ PathResolver    │
│  Execution│ Types      │Manager│ ReportGenerator │
└─────────────────────────────────────────────────┘
```

The framework is divided into three layers: **CLI Entry Layer**, **Runner / Comparator Business Layer**, and **Core Foundation Layer**.

## 2. Module Responsibilities

### 2.1 Directory Structure

```
src/cli_test_framework/
├── __init__.py                  # Package entry, exports public API
├── cli.py                       # cli-test command entry
├── core/                        # Core abstractions and base components
│   ├── base_runner.py           # BaseRunner abstract base class
│   ├── parallel_runner.py       # ParallelRunner parallel base class
│   ├── execution.py             # Single test execution logic
│   ├── process_worker.py        # Multi-process worker
│   ├── assertions.py            # Assertion engine
│   ├── setup.py                 # Setup plugin system
│   ├── test_case.py             # TestCase data class
│   └── types.py                 # TypedDict type definitions
├── runners/                     # Concrete runners
│   ├── json_runner.py           # JSONRunner
│   ├── yaml_runner.py           # YAMLRunner
│   └── parallel_json_runner.py  # ParallelJSONRunner
├── file_comparator/             # File comparison subsystem
│   ├── base_comparator.py       # BaseComparator abstract base class
│   ├── result.py                # ComparisonResult / Difference
│   ├── factory.py               # ComparatorFactory factory
│   ├── text_comparator.py       # Text comparison
│   ├── json_comparator.py       # JSON comparison
│   ├── csv_comparator.py        # CSV comparison
│   ├── xml_comparator.py        # XML comparison
│   ├── binary_comparator.py     # Binary comparison
│   └── h5_comparator.py         # HDF5 comparison
├── commands/                    # CLI subcommands
│   └── compare.py               # compare-files entry
└── utils/                       # Utility modules
    ├── path_resolver.py         # Path resolution
    └── report_generator.py      # Report generation
```

### 2.2 Entry Points

| Command | Mapping |
|---|---|
| `cli-test` | `cli_test_framework.cli:main` |
| `compare-files` | `cli_test_framework.commands.compare:main` |

## 3. Core Class Design

### 3.1 Runner Inheritance Hierarchy

```
BaseRunner (ABC)
├── JSONRunner
├── YAMLRunner
└── ParallelRunner
    └── ParallelJSONRunner
```

#### BaseRunner

The abstract base class for all Runners, defining the template workflow for test execution.

```python
class BaseRunner(ABC):
    def __init__(self, config_file: str, workspace: Optional[str] = None,
                 test_case_filter: Optional[List[str]] = None)
```

**Template method `run_tests()`**:

```
load_test_cases() → _apply_test_case_filter() → setup_manager.setup_all()
    → [run_single_test(case) for case in test_cases]  # Sequential execution
    → setup_manager.teardown_all()
```

**Key attributes**:

| Attribute | Type | Description |
|---|---|---|
| `workspace` | `Path` | Working directory |
| `test_cases` | `List[TestCase]` | Loaded test cases |
| `results` | `Dict` | Run results `{total_tests, passed, failed, details}` |
| `assertions` | `Assertions` | Assertion engine instance |
| `setup_manager` | `SetupManager` | Setup manager |

**Abstract methods**:

| Method | Responsibility |
|---|---|
| `load_test_cases()` | Parse config file, populate `self.test_cases` |
| `run_single_test(case)` | Execute a single test, return result dictionary |

**Step sequence execution `_run_sequence(case)`**:

When a TestCase contains a `steps` field, each step is executed in order. If any step fails, subsequent steps are skipped (fail-fast). The result indicates the failed step number.

#### ParallelRunner

Inherits BaseRunner, overrides `run_tests()` with a parallel version.

```python
class ParallelRunner(BaseRunner):
    def __init__(self, config_file, workspace=None,
                 max_workers=None, execution_mode="thread",
                 test_case_filter=None)
```

- Thread mode: `ThreadPoolExecutor`, shared memory, supports resource scheduling
- Process mode: `ProcessPoolExecutor` + `process_worker.run_test_in_process()`, process isolation
- Thread safety: `_results_lock` / `_print_lock` protect shared state
- Fallback method: `run_tests_sequential()`

#### ParallelJSONRunner

Extends ParallelRunner with **resource-aware scheduling**:

1. After loading cases, sort by `estimated_time` in descending order (LPT strategy)
2. Create `Semaphore(safe_capacity)` resource pool, `safe_capacity = max(1, cpu_count - 2)`
3. Before each case executes, acquire `cpu_cores` semaphores; release after execution
4. Automatically inject `OMP_NUM_THREADS`, `MKL_NUM_THREADS`, `NPROC` environment variables

### 3.2 TestCase Data Model

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

Two modes:
- **Single command mode**: `command` + `args` + `expected`
- **Step sequence mode**: `steps` list, each step contains `command` + `args` + `expected`

### 3.3 Assertions

```python
class Assertions:
    def assert_return_code(self, actual, expected) -> bool
    def assert_output_contains(self, output, expected_strings) -> bool
    def assert_output_matches(self, output, expected_patterns) -> bool
```

Assertion logic: return code exact match, `output_contains` does substring matching, `output_matches` does regex matching. All assertions are optional; unspecified fields are not validated.

### 3.4 Setup Plugin System

```python
class BaseSetup(ABC):
    def __init__(self, config: Dict)
    @abstractmethod
    def setup(self) -> None
    @abstractmethod
    def teardown(self) -> None

class EnvironmentSetup(BaseSetup):
    # setup(): Set environment variables (save old values)
    # teardown(): Restore environment variables

class SetupManager:
    def add_setup(self, setup: BaseSetup) -> None
    def setup_all(self) -> None      # Execute in addition order
    def teardown_all(self) -> None   # Execute in reverse order, ensuring cleanup continues even on errors
```

**Config file integration**: BaseRunner.load_setup_from_config() automatically creates EnvironmentSetup from the `setup.environment_variables` field in JSON/YAML and registers it.

### 3.5 PathResolver

```python
class PathResolver:
    SYSTEM_COMMANDS = {'echo', 'python', 'node', 'java', ...}

    def resolve_command(self, command: str) -> str
    def resolve_path(self, path: str) -> str
    def parse_command_string(self, cmd_str: str) -> Tuple[str, List[str]]
```

Responsibilities:
- System commands are returned as-is; non-system commands are resolved relative to workspace path
- Compound commands (e.g., `"python ./script.py"`) are split and resolved separately

### 3.6 Execution

`execute_single_test_case(case, workspace)` — Independent execution function for a single test:

1. PathResolver resolves command and arguments
2. `subprocess.run()` executes, capturing stdout/stderr/returncode
3. Assertions validate each item
4. Returns result dictionary

### 3.7 ReportGenerator

```python
class ReportGenerator:
    @staticmethod
    def generate(results: Dict, format: str) -> str  # "text" / "json" / "html"
```

## 4. File Comparison Subsystem

### 4.1 Class Hierarchy

```
BaseComparator (ABC)
├── TextComparator     # Line-level comparison based on difflib
│   ├── JsonComparator # Compare after aligning by key field
│   ├── CsvComparator  # CSV structured comparison
│   └── XmlComparator  # XML structured comparison
├── H5Comparator       # HDF5 scientific data comparison
└── BinaryComparator   # Binary stream chunking + LCS similarity
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

Template method: `compare_files()` → `read_content()` × 2 → `compare_content()` → `ComparisonResult`

### 4.3 ComparatorFactory

```python
class ComparatorFactory:
    @staticmethod
    def create_comparator(file_type: str, **kwargs) -> BaseComparator
```

`file_type` values: `"text"` / `"json"` / `"h5"` / `"binary"`

### 4.4 ComparisonResult

```python
class ComparisonResult:
    file1: str
    file2: str
    identical: bool
    differences: List[Difference]
    error: Optional[str]
    # Supports output: str() / to_json() / to_html()
```

### 4.5 H5Comparator Special Design

The HDF5 comparator is the most complex comparator in the framework, designed for scientific computing scenarios:

- **Table selection**: `tables` (exact match) + `table_regex` (regex match, comma-separated multi-pattern)
- **Path expansion**: By default, expands all sub-datasets under a group; can be disabled with `expand_path=False`
- **Numerical tolerance**: `rtol` (relative) + `atol` (absolute), `np.allclose` semantics
- **Data filtering**: `data_filter` expressions (`>1e-6`, `abs>1e-9`, etc.), filter before comparison
- **Chunked reading**: Large datasets are processed in chunks to avoid memory overflow
- **Structure comparison**: `structure_only=True` compares only the hierarchical structure

## 5. Data Flow

### 5.1 Test Execution Flow

```
Config file (JSON/YAML)
       │
       ▼
  load_test_cases()          # Parse into List[TestCase]
       │
       ▼
  _apply_test_case_filter()  # Filter by name
       │
       ▼
  setup_manager.setup_all()  # Environment variables + custom plugins
       │
       ▼
  ┌─────────────────────────────┐
  │  for each TestCase:         │
  │    PathResolver resolves    │
  │    subprocess.run() executes│
  │    Assertions validates     │
  │    Collect to results       │
  └─────────────────────────────┘
       │
       ▼
  setup_manager.teardown_all() # Reverse cleanup
       │
       ▼
  ReportGenerator.generate()   # text / json / html
```

### 5.2 Parallel Execution Flow

```
ParallelJSONRunner.run_tests()
       │
       ▼
  LPT sort (estimated_time descending)
       │
       ▼
  ┌──────────────────────────────────────┐
  │  ThreadPoolExecutor.map():           │
  │    Semaphore.acquire(cpu_cores)      │
  │    Inject OMP/MKL/NPROC env vars     │
  │    execute_single_test_case()        │
  │    Semaphore.release(cpu_cores)      │
  │    _update_results() (thread-safe)   │
  └──────────────────────────────────────┘
```

### 5.3 File Comparison Flow

```
compare-files file1 file2 [options]
       │
       ▼
  Auto-detect / specify file_type
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

## 6. Extension Points

| Extension Point | Base Class | Purpose |
|---|---|---|
| New config format | `BaseRunner` | Support new test definition formats (e.g., XML, TOML) |
| Custom Setup | `BaseSetup` | Database initialization, service start/stop, etc. |
| Custom assertions | `BaseAssertion` | Specific business validation logic |
| New comparator | `BaseComparator` | Support comparison of new file formats |
| New Runner | `ParallelRunner` | Custom parallel strategies |

## 7. Design Decisions

| Decision | Reason |
|---|---|
| Runner uses Template Method pattern | Unified execution flow (load → filter → setup → run → teardown), subclasses only implement config parsing and single test execution |
| Setup reverse-order teardown | Stack-like semantics: dependencies initialized later are cleaned up first |
| Semaphore-based CPU core management | More fine-grained than thread pool worker count; allows different cases to declare different core requirements |
| LPT scheduling strategy | Long tasks start first, reducing tail latency and improving overall throughput |
| Environment variable injection | Scientific computing solvers often ignore Python-level thread control; requires low-level variables like `OMP_NUM_THREADS` to constrain |
| Comparator factory pattern | Creates comparators by file type, shared by both CLI and Python API |
| subprocess isolated execution | Each test case runs in an independent subprocess, ensuring tests don't affect each other |
