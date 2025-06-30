# CLI Testing Framework

## 1. Overview

This is a lightweight and extensible automated testing framework that supports defining test cases via JSON/YAML formats, providing complete test execution, result verification, and report generation capabilities. The framework is designed to provide standardized test management for command-line tools and scripts, with enterprise-grade parallel execution support and advanced file comparison features.

## 2. Features

- **🚀 Parallel Test Execution**: Support for multi-threading and multi-processing parallel testing with significant performance improvements
- **🔧 Setup Module System**: Plugin-based architecture for pre-test setup tasks (environment variables, database initialization, service startup)
- **🏗️ Modular Architecture**: Decoupled design of core components (runner/assertion/report/setup)
- **📄 Multi-Format Support**: Native support for JSON/YAML test case formats
- **🧠 Intelligent Command Parsing**: Smart handling of complex commands like `"python ./script.py"`
- **📁 Smart Path Resolution**: Automatic handling of relative and absolute path conversions
- **✅ Rich Assertion Mechanism**: Return code validation, output content matching, regex verification
- **🔌 Extensible Interfaces**: Quickly implement new test format support by inheriting BaseRunner
- **🔒 Isolated Execution Environment**: Independent sub-process execution ensures test isolation
- **📊 Comprehensive Reports**: Detailed pass rate statistics and failure diagnostics
- **🔧 Thread-Safe Design**: Robust concurrent execution with proper synchronization
- **📝 Advanced File Comparison**: Support for comparing various file types (text, binary, JSON, HDF5) with detailed diff output

## 3. Quick Start

### Environment Requirements

```bash
pip install cli-test-framework
Python >= 3.9
```

### Sequential Execution

```python
from src.runners.json_runner import JSONRunner

runner = JSONRunner(
    config_file="path/to/test_cases.json",
    workspace="/project/root"
)
success = runner.run_tests()
```

### Parallel Execution

```python
from src.runners.parallel_json_runner import ParallelJSONRunner

# Multi-threaded execution (recommended for I/O-intensive tests)
runner = ParallelJSONRunner(
    config_file="path/to/test_cases.json",
    workspace="/project/root",
    max_workers=4,           # Maximum concurrent workers
    execution_mode="thread"  # "thread" or "process"
)
success = runner.run_tests()
```

### Setup Module Usage

```python
from cli_test_framework import JSONRunner, EnvironmentSetup

# Using built-in environment variable setup
runner = JSONRunner("test_cases.json")
env_setup = EnvironmentSetup({
    "TEST_ENV": "development",
    "API_URL": "http://localhost:8080"
})
runner.setup_manager.add_setup(env_setup)
success = runner.run_tests()
```

### File Comparison

```bash
# Compare two text files
compare-files file1.txt file2.txt

# Compare JSON files with key-based comparison
compare-files data1.json data2.json --json-compare-mode key-based --json-key-field id

# Compare HDF5 files with specific options
compare-files data1.h5 data2.h5 --h5-table table1,table2 --h5-rtol 1e-6

# Compare binary files with similarity check
compare-files binary1.bin binary2.bin --similarity
```

## 4. Test Case Format

### JSON Format

```json
{
    "setup": {
        "environment_variables": {
            "TEST_ENV": "development",
            "API_URL": "http://localhost:8080",
            "DEBUG_MODE": "true"
        }
    },
    "test_cases": [
        {
            "name": "Environment Variable Test",
            "command": "python",
            "args": ["-c", "import os; print(f'Environment: {os.environ.get(\"TEST_ENV\")}')"],
            "expected": {
                "return_code": 0,
                "output_contains": ["Environment: development"]
            }
        },
        {
            "name": "File Comparison Test", 
            "command": "compare-files",
            "args": ["file1.txt", "file2.txt", "--verbose"],
            "expected": {
                "return_code": 0,
                "output_contains": ["Files are identical"],
                "output_matches": [".*comparison completed.*"]
            }
        }
    ]
}
```

### YAML Format

```yaml
setup:
  environment_variables:
    TEST_ENV: "production"
    DATABASE_URL: "sqlite:///test.db"

test_cases:
  - name: Environment Test
    command: python
    args:
      - "-c"
      - "import os; print(f'DB: {os.environ.get(\"DATABASE_URL\")}')"
    expected:
      return_code: 0
      output_contains:
        - "DB: sqlite:///test.db"
  
  - name: Directory Scan Test
    command: ls
    args:
      - -l
      - docs/
    expected:
      return_code: 0
      output_matches: ".*\\.md$"
```

## 5. File Comparison Features

### Supported File Types

- **Text Files**: Plain text, source code, markdown, etc.
- **JSON Files**: With exact or key-based comparison
- **HDF5 Files**: Structure and content comparison with numerical tolerance
- **Binary Files**: With optional similarity index calculation

### Comparison Options

#### Text Comparison
```bash
compare-files file1.txt file2.txt \
    --start-line 10 \
    --end-line 20 \
    --encoding utf-8
```

#### JSON Comparison
```bash
compare-files data1.json data2.json \
    --json-compare-mode key-based \
    --json-key-field id,name
```

#### HDF5 Comparison

**New Feature**: HDF5 group path expansion! By default, when you specify a group path in `--h5-table`, the comparator will automatically expand and compare all datasets and subgroups within that path.

```bash
# Compare specific tables/groups with auto-expansion (default behavior)
compare-files data1.h5 data2.h5 \
    --h5-table group1/subgroupA \
    --h5-rtol 1e-5 \
    --h5-atol 1e-8

# Disable auto-expansion to compare only the specified path itself
compare-files data1.h5 data2.h5 \
    --h5-table group1 \
    --h5-no-expand-path

# Use regex patterns (also supports auto-expansion)
compare-files data1.h5 data2.h5 \
    --h5-table-regex "group1/.*" \
    --h5-structure-only

# Use comma-separated table names with regex (New in 0.3.7)
compare-files data1.h5 data2.h5 \
    --h5-table-regex "table1,table2,table3" \
    --h5-rtol 1e-6
```

#### Binary Comparison
```bash
compare-files binary1.bin binary2.bin \
    --similarity \
    --chunk-size 16384
```

### Output Formats

- **Text**: Human-readable diff output
- **JSON**: Structured comparison results
- **HTML**: Visual diff with syntax highlighting

## 6. System Architecture

### Enhanced Architecture Flow

```mermaid
graph TD
    A[Test Cases] --> B{Execution Mode}
    B -->|Sequential| C[JSONRunner/YAMLRunner]
    B -->|Parallel| D[ParallelRunner]
    D --> E[ThreadPoolExecutor/ProcessPoolExecutor]
    C --> F[Command Parser]
    E --> F
    F --> G[Path Resolver]
    G --> H[Sub-process Execution]
    H --> I[Assertion Engine]
    I --> J[Thread-Safe Result Collection]
    J --> K[Report Generator]
    L[File Comparator] --> M[Text Comparator]
    L --> N[JSON Comparator]
    L --> O[HDF5 Comparator]
    L --> P[Binary Comparator]
```

### Core Components

#### 1. Intelligent Command Parser
```python
# Handles complex commands like "python ./script.py"
command_parts = case["command"].split()
if len(command_parts) > 1:
    actual_command = resolve_command(command_parts[0])  # "python"
    script_parts = resolve_paths(command_parts[1:])     # "./script.py" -> full path
    final_command = f"{actual_command} {' '.join(script_parts)}"
```

#### 2. Enhanced Path Resolver
```python
def resolve_command(self, command: str) -> str:
    system_commands = {
        'echo', 'ping', 'python', 'node', 'java', 'docker', ...
    }
    if command in system_commands or Path(command).is_absolute():
        return command
    return str(self.workspace / command)
```

#### 3. Parallel Runner Base Class
```python
class ParallelRunner(BaseRunner):
    def __init__(self, max_workers=None, execution_mode="thread"):
        self.max_workers = max_workers or os.cpu_count()
        self.execution_mode = execution_mode
        self._results_lock = threading.Lock()
        self._print_lock = threading.Lock()
```

## 7. Advanced Usage

### Performance Testing

```python
# Quick performance test
python performance_test.py

# Unit tests for parallel functionality
python -m pytest tests/test_parallel_runner.py -v
```

### Error Handling and Fallback

```python
try:
    runner = ParallelJSONRunner(config_file="test_cases.json")
    success = runner.run_tests()
    
    if not success:
        # Check failed tests
        for detail in runner.results["details"]:
            if detail["status"] == "failed":
                print(f"Failed test: {detail['name']}")
                print(f"Error: {detail['message']}")
                
except Exception as e:
    print(f"Execution error: {e}")
    # Fallback to sequential execution
    runner.run_tests_sequential()
```

### Best Practices

1. **Choose Appropriate Concurrency**:
   ```python
   import os
   
   # For CPU-intensive tasks
   max_workers = os.cpu_count()
   
   # For I/O-intensive tasks
   max_workers = os.cpu_count() * 2
   ```

2. **Test Case Design**:
   - ✅ Ensure test independence (no dependencies between tests)
   - ✅ Avoid shared resource conflicts (different files/ports)
   - ✅ Use relative paths (framework handles resolution automatically)

3. **Debugging**:
   ```python
   # Enable verbose output for debugging
   runner = ParallelJSONRunner(
       config_file="test_cases.json",
       max_workers=1,  # Set to 1 for easier debugging
       execution_mode="thread"
   )
   ```

## 8. Example Demonstrations

### Input Example

```json
{
    "test_cases": [
        {
            "name": "Python Version Check",
            "command": "python --version",
            "args": [],
            "expected": {
                "output_matches": "Python 3\\.[89]\\.",
                "return_code": 0
            }
        },
        {
            "name": "File Processing Test",
            "command": "python ./process_file.py",
            "args": ["input.txt", "--output", "result.txt"],
            "expected": {
                "return_code": 0,
                "output_contains": ["Processing completed"]
            }
        }
    ]
}
```

### Output Report

```
Test Results Summary:
Total Tests: 15
Passed: 15
Failed: 0

Performance Statistics:
Sequential execution time: 12.45 seconds
Parallel execution time:   3.21 seconds
Speedup ratio:            3.88x

Detailed Results:
✓ Python Version Check
✓ File Processing Test
✓ JSON Comparison Test
...
```

## 9. Troubleshooting

### Common Issues

1. **Process Mode Serialization Error**
   - **Cause**: Objects contain non-serializable attributes (like locks)
   - **Solution**: Use independent process worker functions

2. **Path Resolution Error**
   - **Cause**: System commands treated as relative paths
   - **Solution**: Update `PathResolver` system command list

3. **Performance Not Improved**
   - **Cause**: Test cases too short, parallel overhead exceeds benefits
   - **Solution**: Increase test case count or use more complex tests

4. **Command Not Found Error**
   - **Cause**: Complex commands like `"python ./script.py"` not parsed correctly
   - **Solution**: Framework now automatically handles this (fixed in latest version)

### Debug Tips

```python
# Enable detailed logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Check detailed results
import json
print(json.dumps(runner.results, indent=2, ensure_ascii=False))
```

## 10. Extension and Customization

### Adding New Runners

```python
class XMLRunner(BaseRunner):
    def load_test_cases(self):
        import xml.etree.ElementTree as ET
        # Parse XML structure and convert to TestCase objects
        
class CustomParallelRunner(ParallelRunner):
    def custom_preprocessing(self):
        # Add custom logic before test execution
        pass
```

### Custom Assertions

```python
class CustomAssertions(Assertions):
    @staticmethod
    def performance_threshold(execution_time, max_time):
        if execution_time > max_time:
            raise AssertionError(f"Execution too slow: {execution_time}s > {max_time}s")
```

## 11. Version Compatibility

- **Python Version**: 3.6+
- **Dependencies**: Standard library only (no external dependencies for core functionality)
- **Backward Compatibility**: Fully compatible with existing `JSONRunner` code
- **Platform Support**: Windows, macOS, Linux

## 12. Performance Benchmarks

| Test Scenario | Sequential | Parallel (Thread) | Parallel (Process) | Speedup |
|---------------|------------|-------------------|-------------------|---------|
| 10 I/O tests  | 5.2s       | 1.4s              | 2.1s              | 3.7x    |
| 20 CPU tests  | 12.8s      | 8.9s              | 6.2s              | 2.1x    |
| Mixed tests   | 8.5s       | 2.3s              | 3.1s              | 3.7x    |

## 13. Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass: `python -m pytest tests/ -v`
5. Submit a pull request

## 14. License

This project is licensed under the MIT License - see the LICENSE file for details.

---

## 📚 Complete Documentation

For comprehensive documentation including detailed Setup Module guide, API reference, and advanced usage examples, see:

**[📖 Complete User Manual](https://github.com/ozil111/cli-test-framework/blob/main/docs/user_manual.md)**

The user manual includes:
- 🔧 **Setup Module**: Complete guide for environment variables and custom plugins
- 🚀 **Parallel Testing**: Advanced parallel execution strategies  
- 📁 **File Comparison**: Detailed comparison capabilities for all file types
- 🔌 **API Reference**: Full API documentation and examples
- 🛠️ **Troubleshooting**: Common issues and solutions
- 📝 **Best Practices**: Recommended patterns and configurations

---

**🚀 Ready to supercharge your testing workflow with setup modules, parallel execution and advanced file comparison!**

For detailed parallel testing guide, see: [PARALLEL_TESTING_GUIDE.md](https://github.com/ozil111/cli-test-framework/blob/main/PARALLEL_TESTING_GUIDE.md)

# 支持数据过滤（New in 0.3.6）

你可以通过 `--h5-data-filter` 选项只比较满足特定条件的数据。例如：

```bash
# 只比较大于 1e-6 的数据
compare-files data1.h5 data2.h5 --h5-data-filter '>1e-6'

# 只比较绝对值大于 1e-6 的数据
compare-files data1.h5 data2.h5 --h5-data-filter 'abs>1e-6'

# 只比较小于等于 0.01 的数据
compare-files data1.h5 data2.h5 --h5-data-filter '<=0.01'
```

支持的表达式包括：`>`, `>=`, `<`, `<=`, `==`，以及 `abs` 前缀（绝对值过滤）。

# 版本更新日志

## 0.3.7 (Latest)

### 🐛 Bug Fixes
- **Fixed H5 table regex matching**: `--h5-table-regex=table1,table2` now correctly matches both `table1` and `table2` instead of treating the entire string as a single regex pattern
- **Enhanced regex pattern support**: Multiple comma-separated table names are now supported in `--h5-table-regex` parameter

### ✨ New Features
- **Improved HDF5 comparison**: Better handling of multiple table selection with regex patterns
- **Enhanced debug output**: More detailed logging for HDF5 table matching process

### 🔧 Improvements
- **Backward compatibility**: All existing functionality remains unchanged
- **Better error handling**: More informative error messages for regex pattern parsing

## 0.3.6

### ✨ New Features
- **Data filtering for HDF5 files**: Added `--h5-data-filter` option to compare only data meeting specific criteria
- **Enhanced HDF5 comparison**: Support for absolute value filtering and various comparison operators
