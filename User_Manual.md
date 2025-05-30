# 📘 CLI-Test-Framework 使用手册

本框架是一个用于命令行工具的自动化测试框架，支持 **JSON/YAML 测试配置文件**、**顺序执行**与**并行执行（线程/进程）**，可自动比对输出、返回码，并生成测试报告。

------

## ✅ 安装方式

### 从 PyPI 安装：

```bash
pip install cli-test-framework
```

------

## 📂 项目结构推荐

```bash
your_project/
├── test_cases.json          # 测试用例配置文件
├── test_report.txt          # 测试报告（可选输出）
└── run_tests.py             # 测试执行脚本
```

------

## 🧪 示例测试用例（JSON 格式）

```json
{
  "test_cases": [
    {
      "name": "版本检查测试",
      "command": "python",
      "args": ["--version"],
      "expected": {
        "return_code": 0,
        "output_contains": ["Python"]
      }
    }
  ]
}
```

------

## 🚀 快速使用示例

### 顺序执行测试

```python
from cli_test_framework.runners import JSONRunner

runner = JSONRunner(config_file="test_cases.json", workspace=".")
runner.run_tests()
```

### 并行执行测试（线程模式）

```python
from cli_test_framework.runners import ParallelJSONRunner

runner = ParallelJSONRunner(
    config_file="test_cases.json",
    workspace=".",
    max_workers=4,
    execution_mode="thread"  # 可为 "thread" 或 "process"
)
runner.run_tests()
```

------

## 📄 生成测试报告

```python
from cli_test_framework.utils import ReportGenerator

report = ReportGenerator(runner.results, "test_report.txt")
report.print_report()  # 打印至终端
report.save_report()   # 保存至文件
```

------

## ⚙️ 支持的字段说明

| 字段              | 类型      | 说明                               |
| ----------------- | --------- | ---------------------------------- |
| `name`            | str       | 测试名称                           |
| `command`         | str       | 要执行的命令（可为系统命令或脚本） |
| `args`            | List[str] | 命令参数                           |
| `expected`        | dict      | 预期结果                           |
| `return_code`     | int       | 预期返回值（可选）                 |
| `output_contains` | List[str] | 输出中必须包含的内容（可选）       |
| `output_matches`  | str       | 输出需匹配的正则表达式（可选）     |



------

## 🧠 并行执行说明

### 执行模式选项：

| 模式      | 说明                              | 适用场景        |
| --------- | --------------------------------- | --------------- |
| `thread`  | 多线程，适合 I/O 密集型测试       | 网络/文件操作   |
| `process` | 多进程，适合 CPU 密集型、隔离需求 | 重计算/崩溃测试 |



### 设置最大并发数：

```python
import os
max_workers = os.cpu_count() * 2  # 推荐值
```

------

## 📦 高级用法

- 支持 YAML 测试文件：使用 `YAMLRunner`
- 自定义断言模块：继承 `Assertions` 类添加新规则
- 自定义测试格式：继承 `BaseRunner`

------

## 🛠 常见问题排查

| 问题                     | 可能原因                                    |
| ------------------------ | ------------------------------------------- |
| 命令未执行成功           | command 路径错误 / 环境未激活               |
| output_contains 断言失败 | 输出为 stderr 而非 stdout                   |
| 并行模式下报错           | 可能为 `args` 或 `command` 含不可序列化对象 |



------

## 🧪 快速性能对比（可选）

运行内置性能测试脚本：

```bash
python tests/performance_test.py
```

输出示例：

```makefile
顺序执行时间:      2.34 秒
并行执行(线程):    0.88 秒 (加速比: 2.66x)
```

------

## 📎 附加说明

- **支持平台**：Windows / Linux / macOS
- **Python 版本**：3.6+
- **依赖项**：
  - `PyYAML`（仅用于 YAMLRunner）
  - 其余使用标准库（无额外依赖）

------

## 📬 联系方式（可选）

作者：Xiaotong Wang
 邮箱：xiaotongwang98@gmail.com
 GitHub：`https://github.com/ozil111/cli-test-framework`