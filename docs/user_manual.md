# CLI Testing Framework User Manual

## Table of Contents
1. [Introduction](#introduction)
2. [Installation](#installation)
3. [Basic Usage](#basic-usage)
4. [Test Case Definition](#test-case-definition)
5. [Parallel Testing](#parallel-testing)
6. [File Comparison](#file-comparison)
7. [Advanced Features](#advanced-features)
8. [Troubleshooting](#troubleshooting)
9. [API Reference](#api-reference)
10. [Examples](#examples)

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
- Python 3.6 or higher
- pip package manager

### Basic Installation
```bash
pip install cli-test-framework
```

### Development Installation
```bash
git clone https://github.com/yourusername/cli-test-framework.git
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