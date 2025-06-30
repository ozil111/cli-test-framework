# CLI Testing Framework User Manual

## Table of Contents
1. [Introduction](#introduction)
2. [Installation](#installation)
3. [Basic Usage](#basic-usage)
4. [Test Case Definition](#test-case-definition)
5. [Setup Module](#setup-module)
6. [Parallel Testing](#parallel-testing)
7. [File Comparison](#file-comparison)
8. [Advanced Features](#advanced-features)
9. [Troubleshooting](#troubleshooting)
10. [API Reference](#api-reference)
11. [Examples](#examples)

## Introduction

The CLI Testing Framework is a powerful tool designed for testing command-line applications and scripts. It provides a structured way to define, execute, and verify test cases, with support for parallel execution and advanced file comparison capabilities.

### Key Features
- Parallel test execution with thread and process support
- JSON/YAML test case definition
- Advanced file comparison capabilities
- Comprehensive reporting
- Extensible architecture

## Installation

### Prerequisites
- Python 3.9 or higher
- pip package manager

### Basic Installation
```bash
pip install cli-test-framework
```

### Development Installation
```bash
git clone https://github.com/ozil111/cli-test-framework.git
cd cli-test-framework
pip install -e .
```

## Basic Usage

### Creating a Test Case

1. Create a JSON test case file (e.g., `test_cases.json`):
```json
{
    "test_cases": [
        {
            "name": "Basic Command Test",
            "command": "echo",
            "args": ["Hello, World!"],
            "expected": {
                "return_code": 0,
                "output_contains": ["Hello, World!"]
            }
        }
    ]
}
```

2. Run the test:
```python
from cli_test_framework.runners import JSONRunner

runner = JSONRunner(
    config_file="test_cases.json",
    workspace="/path/to/workspace"
)
success = runner.run_tests()
```

### Using the Command Line

```bash
# Run tests from a JSON file
cli-test run test_cases.json

# Run tests in parallel
cli-test run test_cases.json --parallel --workers 4
```

## Test Case Definition

### JSON Format

```json
{
    "test_cases": [
        {
            "name": "Test Case Name",
            "command": "command_to_execute",
            "args": ["arg1", "arg2"],
            "expected": {
                "return_code": 0,
                "output_contains": ["expected text"],
                "output_matches": [".*regex pattern.*"]
            }
        }
    ]
}
```

### YAML Format

```yaml
test_cases:
  - name: Test Case Name
    command: command_to_execute
    args:
      - arg1
      - arg2
    expected:
      return_code: 0
      output_contains:
        - expected text
      output_matches:
        - ".*regex pattern.*"
```

## Setup Module

The Setup Module provides a plugin-based system for executing pre-test setup tasks and post-test cleanup. It's designed to be extensible and supports multiple setup plugins running in sequence.

### Key Features
- **Plugin Architecture**: Extensible design allowing custom setup plugins
- **Built-in Environment Plugin**: Set environment variables for tests
- **Full Runner Support**: Works with JSONRunner, YAMLRunner, and ParallelJSONRunner
- **Lifecycle Management**: Automatic setup and teardown with proper cleanup

### Environment Variable Setup

#### JSON Configuration
```json
{
  "setup": {
    "environment_variables": {
      "TEST_ENV": "development",
      "DEBUG_MODE": "true",
      "API_URL": "http://localhost:8080",
      "DATABASE_URL": "sqlite:///test.db"
    }
  },
  "test_cases": [
    {
      "name": "Test with environment variables",
      "command": "python",
      "args": ["-c", "import os; print(f'Env: {os.environ.get(\"TEST_ENV\")}')"],
      "expected": {
        "return_code": 0,
        "output_contains": ["Env: development"]
      }
    }
  ]
}
```

#### YAML Configuration
```yaml
setup:
  environment_variables:
    TEST_ENV: "production"
    DATABASE_URL: "postgresql://localhost:5432/test"
    MAX_CONNECTIONS: "10"
    TIMEOUT_SECONDS: "30"

test_cases:
  - name: "Test database environment"
    command: "python"
    args: 
      - "-c"
      - "import os; print(f'DB: {os.environ.get(\"DATABASE_URL\")}')"
    expected:
      return_code: 0
      output_contains:
        - "DB: postgresql://localhost:5432/test"
```

### Custom Setup Plugins

#### Creating Custom Plugins
```python
from cli_test_framework import BaseSetup

class DatabaseSetup(BaseSetup):
    def setup(self):
        """Initialize test database"""
        print("Setting up test database...")
        # Your database initialization code here
        
    def teardown(self):
        """Clean up test database"""
        print("Cleaning up test database...")
        # Your database cleanup code here

class ServiceSetup(BaseSetup):
    def setup(self):
        """Start test services"""
        self.service_port = self.config.get('port', 8080)
        print(f"Starting test service on port {self.service_port}")
        # Your service startup code here
        
    def teardown(self):
        """Stop test services"""
        print("Stopping test services...")
        # Your service shutdown code here
```

#### Using Custom Plugins
```python
from cli_test_framework import JSONRunner

# Create runner
runner = JSONRunner("test_cases.json")

# Add custom setup plugins
db_setup = DatabaseSetup({"connection": "test_db"})
service_setup = ServiceSetup({"port": 9090})

runner.setup_manager.add_setup(db_setup)
runner.setup_manager.add_setup(service_setup)

# Run tests (setup will be executed automatically)
success = runner.run_tests()
```

### Execution Flow

1. **Load Configuration**: Read setup configuration from test file
2. **Setup Phase**: Execute all setup plugins in order
   - Environment variables are set
   - Custom setups are executed
   - Setup status is reported
3. **Test Execution**: Run all test cases with setup environment
4. **Teardown Phase**: Clean up all setups in reverse order
   - Environment variables are restored
   - Custom cleanups are executed
   - Cleanup is guaranteed even if tests fail

### Best Practices

1. **Idempotent Operations**: Make setup operations safe to run multiple times
2. **Proper Cleanup**: Always implement teardown to avoid side effects
3. **Error Handling**: Setup failures stop test execution, teardown failures don't
4. **Resource Management**: Use try-finally patterns in custom plugins
5. **Configuration Validation**: Check required configuration parameters in setup

### Integration Examples

#### With JSON Runner
```bash
cli-test test_with_setup.json
```

#### With YAML Runner
```bash
cli-test test_with_setup.yaml --runner yaml
```

#### With Parallel Runner
```bash
cli-test test_with_setup.json --runner parallel --max-workers 4
```

Note: In parallel mode, setup and teardown run in the main thread to ensure environment consistency.

## Parallel Testing

### Thread Mode
```python
from cli_test_framework.runners import ParallelJSONRunner

runner = ParallelJSONRunner(
    config_file="test_cases.json",
    max_workers=4,
    execution_mode="thread"
)
success = runner.run_tests()
```

### Process Mode
```python
runner = ParallelJSONRunner(
    config_file="test_cases.json",
    max_workers=2,
    execution_mode="process"
)
success = runner.run_tests()
```

## File Comparison

### Basic File Comparison
```bash
# Compare two text files
compare-files file1.txt file2.txt

# Compare with specific options
compare-files file1.txt file2.txt --start-line 10 --end-line 20
```

### JSON File Comparison
```bash
# Exact comparison
compare-files data1.json data2.json

# Key-based comparison
compare-files data1.json data2.json --json-compare-mode key-based --json-key-field id
```

### HDF5 File Comparison
```bash
# Compare specific tables
compare-files data1.h5 data2.h5 --h5-table table1,table2

# Compare with numerical tolerance
compare-files data1.h5 data2.h5 --h5-rtol 1e-5 --h5-atol 1e-8
```

#### Data Filtering (New in 0.3.6)

You can use the `--h5-data-filter` option to only compare data that meets a certain condition. For example:

```bash
# Only compare values greater than 1e-6
compare-files data1.h5 data2.h5 --h5-data-filter '>1e-6'

# Only compare absolute values greater than 1e-6
compare-files data1.h5 data2.h5 --h5-data-filter 'abs>1e-6'

# Only compare values less than or equal to 0.01
compare-files data1.h5 data2.h5 --h5-data-filter '<=0.01'
```

Supported filter expressions: `>`, `>=`, `<`, `<=`, `==`, and `abs` prefix for absolute value filtering.

### Binary File Comparison
```bash
# Compare with similarity check
compare-files binary1.bin binary2.bin --similarity

# Compare with custom chunk size
compare-files binary1.bin binary2.bin --chunk-size 16384
```

## Advanced Features

### Custom Assertions
```python
from cli_test_framework.assertions import BaseAssertion

class CustomAssertion(BaseAssertion):
    def assert_custom_condition(self, actual, expected):
        if not self._check_custom_condition(actual, expected):
            raise AssertionError("Custom condition not met")
```

### Custom Runners
```python
from cli_test_framework.runners import BaseRunner

class CustomRunner(BaseRunner):
    def load_test_cases(self):
        # Custom test case loading logic
        pass

    def run_test(self, test_case):
        # Custom test execution logic
        pass
```

### Output Formats
```python
# JSON output
runner = JSONRunner(config_file="test_cases.json", output_format="json")

# HTML output
runner = JSONRunner(config_file="test_cases.json", output_format="html")
```

## Troubleshooting

### Common Issues

1. **Command Not Found**
   - Ensure the command is in the system PATH
   - Use absolute paths for scripts
   - Check command permissions

2. **Parallel Execution Issues**
   - Reduce number of workers
   - Check for resource conflicts
   - Use process mode for CPU-intensive tests

3. **File Comparison Issues**
   - Verify file permissions
   - Check file encoding
   - Ensure sufficient memory for large files

### Debug Mode
```python
runner = JSONRunner(
    config_file="test_cases.json",
    debug=True
)
```

## API Reference

### Core Classes

#### JSONRunner
```python
class JSONRunner:
    def __init__(self, config_file, workspace=None, debug=False):
        """
        Initialize JSONRunner
        :param config_file: Path to JSON test case file
        :param workspace: Working directory for test execution
        :param debug: Enable debug mode
        """
```

#### ParallelJSONRunner
```python
class ParallelJSONRunner:
    def __init__(self, config_file, max_workers=None, execution_mode="thread"):
        """
        Initialize ParallelJSONRunner
        :param config_file: Path to JSON test case file
        :param max_workers: Maximum number of parallel workers
        :param execution_mode: "thread" or "process"
        """
```

### File Comparison

#### ComparatorFactory
```python
class ComparatorFactory:
    @staticmethod
    def create_comparator(file_type, **kwargs):
        """
        Create a comparator instance
        :param file_type: Type of file to compare
        :param kwargs: Additional comparator options
        :return: Comparator instance
        """
```

## Examples

### Complete Test Suite
```python
from cli_test_framework.runners import JSONRunner
from cli_test_framework.assertions import Assertions

# Create test runner
runner = JSONRunner(
    config_file="test_suite.json",
    workspace="/project/root",
    debug=True
)

# Run tests
success = runner.run_tests()

# Process results
if success:
    print("All tests passed!")
else:
    print("Some tests failed:")
    for result in runner.results["details"]:
        if result["status"] == "failed":
            print(f"- {result['name']}: {result['message']}")
```

### Parallel Test Suite
```python
from cli_test_framework.runners import ParallelJSONRunner
import os

# Create parallel runner
runner = ParallelJSONRunner(
    config_file="test_suite.json",
    max_workers=os.cpu_count() * 2,
    execution_mode="thread"
)

# Run tests in parallel
success = runner.run_tests()

# Generate report
runner.generate_report("test_report.html")
```

### File Comparison Suite
```python
from cli_test_framework.file_comparator import ComparatorFactory

# Compare text files
text_comparator = ComparatorFactory.create_comparator(
    "text",
    encoding="utf-8",
    verbose=True
)
text_result = text_comparator.compare_files("file1.txt", "file2.txt")

# Compare JSON files
json_comparator = ComparatorFactory.create_comparator(
    "json",
    compare_mode="key-based",
    key_field="id"
)
json_result = json_comparator.compare_files("data1.json", "data2.json")
```

## Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details. 