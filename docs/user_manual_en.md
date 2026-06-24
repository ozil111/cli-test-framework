# CLI Test Framework User Manual

## Table of Contents

- [Installation](#installation)
- [Test Case Definition](#test-case-definition)
- [Running Tests](#running-tests)
- [Setup Module](#setup-module)
- [Parallel Testing](#parallel-testing)
- [Sequential Step Testing](#sequential-step-testing)
- [Resource-Aware Scheduling](#resource-aware-scheduling)
- [File Comparison](#file-comparison)
- [Extension Development](#extension-development)

## Installation

```bash
pip install cli-test-framework
```

Requirement: Python >= 3.9

For YAML support, install additionally:

```bash
pip install pyyaml
```

## Test Case Definition

### JSON Format

```json
{
    "test_cases": [
        {
            "name": "Test name",
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

### YAML Format

```yaml
test_cases:
  - name: Test name
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

### Field Descriptions

| Field | Required | Description |
|---|---|---|
| `name` | Yes | Test case name |
| `command` | Yes | Command to execute |
| `args` | No | List of command arguments |
| `timeout` | No | Timeout in seconds, default 3600, set `null` for no limit |
| `resources` | No | Resource configuration, see [Resource-Aware Scheduling](#resource-aware-scheduling) |
| `expected.return_code` | No | Expected return code |
| `expected.output_contains` | No | List of strings that output must contain |
| `expected.output_matches` | No | List of regex patterns that output must match |

## Running Tests

### Command Line

```bash
# Run JSON tests
cli-test run test_cases.json

# Run YAML tests
cli-test run test_cases.yaml

# Specify working directory
cli-test run test_cases.json --workspace /path/to/project

# Run in parallel
cli-test run test_cases.json --parallel --workers 4

# Specify parallel mode
cli-test run test_cases.json --parallel --execution-mode process

# Run only specified cases
cli-test run test_cases.json -t test_name_1 -t test_name_2

# Verbose output
cli-test run test_cases.json --verbose

# Debug mode
cli-test run test_cases.json --debug

# JUnit XML output for CI
cli-test run test_cases.json --junit-xml report.xml

# Output format
cli-test run test_cases.json --output-format json|html|text
```

### Python API

```python
from cli_test_framework.runners import JSONRunner, YAMLRunner, ParallelJSONRunner

# Sequential run
runner = JSONRunner(
    config_file="test_cases.json",
    workspace="/path/to/project",    # Optional, defaults to project root
    test_case_filter=["test_1"]      # Optional, run only specified cases
)
success = runner.run_tests()

# YAML format
runner = YAMLRunner(config_file="test_cases.yaml")

# Parallel run
runner = ParallelJSONRunner(
    config_file="test_cases.json",
    max_workers=4,                   # Optional, defaults to CPU core count
    execution_mode="thread",         # "thread" or "process"
    test_case_filter=["test_1"]
)
success = runner.run_tests()
```

### Getting Results

```python
runner.run_tests()

# Summary
runner.results["total_tests"]
runner.results["passed"]
runner.results["failed"]

# Details
for detail in runner.results["details"]:
    print(detail["name"], detail["status"], detail.get("message", ""))
```

### JUnit XML Output (CI Integration)

Generate JUnit-format XML reports for CI tools like GitLab CI, Jenkins, or CircleCI:

```bash
cli-test run test_cases.json --junit-xml report.xml
```

This produces a standard JUnit XML file that can be consumed by CI report panels:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<testsuite name="test_cases" tests="3" failures="1" errors="1" time="12.345">
  <testcase name="test_ok" classname="test_cases" time="0.123" />
  <testcase name="test_fail" classname="test_cases" time="0.456">
    <failure message="expected 'hello'" type="AssertionError">...</failure>
  </testcase>
  <testcase name="test_timeout" classname="test_cases" time="10.0">
    <error message="Timeout reached" type="TimeoutExpired">...</error>
  </testcase>
</testsuite>
```

**CI configuration examples:**

**GitLab CI** (`.gitlab-ci.yml`):
```yaml
test:
  script:
    - cli-test run test_cases.json --junit-xml report.xml
  artifacts:
    reports:
      junit: report.xml
```

**Jenkins Pipeline**:
```groovy
stage('Test') {
    steps {
        sh 'cli-test run test_cases.json --junit-xml report.xml'
        junit 'report.xml'
    }
}
```

**GitHub Actions**:
```yaml
- name: Run tests
  run: cli-test run test_cases.json --junit-xml report.xml
- name: Publish test results
  uses: dorny/test-reporter@v1
  with:
    name: CLI Tests
    path: report.xml
    reporter: java-junit
```

**Python API**:
```python
from cli_test_framework import write_junit_xml

runner = JSONRunner(config_file="test_cases.json")
runner.run_tests()
write_junit_xml(runner.results, "report.xml", suite_name="my_tests")
```

Status mapping:
| Test status | JUnit element | CI interpretation |
|---|---|---|
| `passed` | (no child) | Passed |
| `failed` (assertion) | `<failure>` | Failure |
| `failed` (execution error) | `<error>` | Error |
| `timeout` | `<error>` | Error |

## Setup Module

The Setup module performs initialization before tests and cleanup after tests.

### Environment Variables (Config File Approach)

JSON:

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

YAML:

```yaml
setup:
  environment_variables:
    TEST_ENV: "development"
    API_URL: "http://localhost:8080"
test_cases:
  [...]
```

Environment variables in the config file are set before tests and restored to their original values after tests.

### Custom Setup Plugin

```python
from cli_test_framework import BaseSetup, JSONRunner

class DatabaseSetup(BaseSetup):
    def setup(self):
        # Initialization operations
        pass

    def teardown(self):
        # Cleanup operations (executed even if tests fail)
        pass

runner = JSONRunner("test_cases.json")
runner.setup_manager.add_setup(DatabaseSetup({"connection": "test_db"}))
success = runner.run_tests()
```

Multiple plugins execute `setup()` in addition order and `teardown()` in reverse order.

### Execution Order

1. Load setup configuration from config file (environment variables, etc.)
2. Execute `setup()` for all setup plugins (in addition order)
3. Run tests
4. Execute `teardown()` for all setup plugins (in reverse order, guaranteed to execute)

## Parallel Testing

```python
from cli_test_framework.runners import ParallelJSONRunner

runner = ParallelJSONRunner(
    config_file="test_cases.json",
    max_workers=4,                # Maximum concurrency, defaults to CPU core count
    execution_mode="thread"       # "thread" or "process"
)
success = runner.run_tests()

# Fallback to sequential execution
runner.run_tests_sequential()
```

**Thread mode**: Shared memory, supports resource-aware scheduling (see next section).
**Process mode**: Process isolation, does not support resource scheduling.

## Sequential Step Testing

A test case can contain multiple ordered steps. If any step fails, subsequent steps are skipped (fail-fast).

### JSON

```json
{
    "test_cases": [
        {
            "name": "Multi-step test",
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
  - name: Multi-step test
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

Each step supports `command`, `args`, `expected`, and `timeout` fields. On failure, the result indicates the failed step number, e.g., "Failed at step 2/3".

## Resource-Aware Scheduling

Only effective in thread mode. Configured via the `resources` field; the framework automatically manages CPU core allocation.

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

| Field | Description |
|---|---|
| `cpu_cores` | Required CPU core count, default 1. The framework uses semaphores to control allocation; tasks exceeding the limit wait in queue |
| `estimated_time` | Estimated duration (seconds), used for LPT scheduling (long tasks start first) |
| `min_memory_mb` | Estimated memory (MB), currently used for log warnings only |
| `priority` | Priority 0-10, currently used for informational labeling only |

Framework behavior:
- Automatically detects CPU core count, reserving 2 cores for the system
- Automatically injects `OMP_NUM_THREADS`, `MKL_NUM_THREADS`, `NPROC` environment variables when a task starts, preventing solver thread runaway
- Schedules by `estimated_time` in descending order (LPT strategy)

## File Comparison

### Command Line Tool `compare-files`

```bash
compare-files <file1> <file2> [options]
```

### Common Options

| Option | Description |
|---|---|
| `--file-type` | File type: `auto` (default), `text`, `json`, `h5`, `binary` |
| `--start-line` | Start line number (1-based), default 1 |
| `--end-line` | End line number (1-based) |
| `--start-column` | Start column number (1-based), default 1 |
| `--end-column` | End column number (1-based) |
| `--encoding` | Text encoding, default `utf-8` |
| `--output-format` | Output format: `text`, `json`, `html` |
| `--verbose` / `-v` | Verbose output |
| `--debug` | Debug mode |
| `--num-threads` | Number of parallel threads, default 4 |

### Text File Comparison

```bash
compare-files file1.txt file2.txt --start-line 10 --end-line 20
```

### JSON File Comparison

```bash
# Exact comparison (default)
compare-files data1.json data2.json

# Compare by key field
compare-files data1.json data2.json --json-compare-mode key-based --json-key-field id
```

| Option | Description |
|---|---|
| `--json-compare-mode` | `exact` (default) or `key-based` |
| `--json-key-field` | Matching field for key-based mode, supports comma-separated multi-field |

### HDF5 File Comparison

```bash
# Compare specified tables
compare-files data1.h5 data2.h5 --h5-table table1,table2

# Use regex to match table names
compare-files data1.h5 data2.h5 --h5-table-regex "result_.*"

# Comma-separated multiple regex patterns
compare-files data1.h5 data2.h5 --h5-table-regex "table1,table2,table3"

# Numerical tolerance
compare-files data1.h5 data2.h5 --h5-rtol 1e-5 --h5-atol 1e-8

# Data filtering (compare only data matching the condition)
compare-files data1.h5 data2.h5 --h5-data-filter '>1e-6'
compare-files data1.h5 data2.h5 --h5-data-filter 'abs>1e-9'
compare-files data1.h5 data2.h5 --h5-data-filter '<=0.01'

# Disable automatic group path expansion
compare-files data1.h5 data2.h5 --h5-table group1 --h5-no-expand-path
```

| Option | Description |
|---|---|
| `--h5-table` | Specify table names, comma-separated |
| `--h5-table-regex` | Regex pattern for table names, comma-separated multi-pattern |
| `--h5-structure-only` | Compare structure only, not content |
| `--h5-show-content-diff` | Show content difference details |
| `--h5-rtol` | Relative tolerance, default 1e-5 |
| `--h5-atol` | Absolute tolerance, default 1e-8 |
| `--h5-data-filter` | Data filter expression: `>`, `>=`, `<`, `<=`, `==`, supports `abs` prefix |
| `--h5-no-expand-path` | Disable automatic expansion of sub-items under group paths |

### Binary File Comparison

```bash
compare-files binary1.bin binary2.bin --similarity --chunk-size 16384
```

| Option | Description |
|---|---|
| `--similarity` | Calculate similarity index |
| `--chunk-size` | Read chunk size, default 8192 |

### Python API

```python
from cli_test_framework.file_comparator import ComparatorFactory

# Text comparison
comparator = ComparatorFactory.create_comparator("text", encoding="utf-8", verbose=True)
result = comparator.compare_files("file1.txt", "file2.txt")

# JSON comparison
comparator = ComparatorFactory.create_comparator("json", compare_mode="key-based", key_field="id")
result = comparator.compare_files("data1.json", "data2.json")

# HDF5 comparison
comparator = ComparatorFactory.create_comparator("h5", tables=["table1"], rtol=1e-5)
result = comparator.compare_files("data1.h5", "data2.h5")

# Results
result.identical   # bool
result.differences # list
```

## Extension Development

### Controlling Log Output

The framework uses Python's standard `logging` module. By default, a console handler at `INFO` level is installed. You can suppress or redirect output:

```python
import logging

# Suppress all framework output when used as a library
logging.getLogger("cli_test_framework").setLevel(logging.WARNING)

# Or remove the handler entirely
logging.getLogger("cli_test_framework").handlers.clear()

# Redirect to a file
file_handler = logging.FileHandler("test.log")
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
logging.getLogger("cli_test_framework").addHandler(file_handler)
```

### Custom Runner

```python
from cli_test_framework.runners import BaseRunner

class CustomRunner(BaseRunner):
    def load_test_cases(self):
        # Load test cases into self.test_cases
        pass

    def run_single_test(self, test_case):
        # Execute a single test, return result dictionary
        pass
```

### Custom Setup Plugin

Use `get_logger` for consistent logging in your extensions:

```python
from cli_test_framework import BaseSetup, get_logger

class MySetup(BaseSetup):
    def __init__(self, config=None):
        super().__init__(config)
        self.logger = get_logger(__name__)

    def setup(self):
        self.logger.info("Running MySetup...")

    def teardown(self):
        self.logger.info("Tearing down MySetup...")
```

### Custom Assertions

```python
from cli_test_framework.assertions import BaseAssertion

class CustomAssertion(BaseAssertion):
    def assert_custom_condition(self, actual, expected):
        if not self._check(actual, expected):
            raise AssertionError("Condition not met")
```
