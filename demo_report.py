#!/usr/bin/env python3
"""
演示示例：运行测试并生成 test_report.txt 报告
展示每个测试用例的耗时信息
"""

import json
import os
import sys
import tempfile

# 添加源代码路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from cli_test_framework import JSONRunner
from cli_test_framework.utils.report_generator import ReportGenerator


def create_demo_config():
    """创建演示用的测试配置，包含通过和失败的用例"""
    config = {
        "test_cases": [
            {
                "name": "检查Python版本",
                "command": "python",
                "args": ["--version"],
                "expected": {
                    "return_code": 0,
                    "output_contains": ["Python"]
                }
            },
            {
                "name": "计算1到100的和",
                "command": "python",
                "args": ["-c", "print(sum(range(1, 101)))"],
                "expected": {
                    "return_code": 0,
                    "output_contains": ["5050"]
                }
            },
            {
                "name": "延时测试(模拟耗时操作)",
                "command": "python",
                "args": ["-c", "import time; time.sleep(1); print('done after 1s')"],
                "expected": {
                    "return_code": 0,
                    "output_contains": ["done after 1s"]
                }
            },
            {
                "name": "环境变量检查",
                "command": "python",
                "args": ["-c", "import os; print(os.environ.get('PATH', '')[:50])"],
                "expected": {
                    "return_code": 0
                }
            },
            {
                "name": "故意失败的测试-期望不匹配",
                "command": "python",
                "args": ["-c", "print('hello')"],
                "expected": {
                    "return_code": 0,
                    "output_contains": ["goodbye"]
                }
            },
            {
                "name": "故意失败的测试-返回码不对",
                "command": "python",
                "args": ["-c", "import sys; sys.exit(1)"],
                "expected": {
                    "return_code": 0
                }
            }
        ]
    }

    # 写入临时文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
        return f.name


def main():
    config_file = create_demo_config()
    report_path = os.path.join(os.path.dirname(__file__), "test_report.txt")

    try:
        print("=" * 60)
        print("CLI测试框架 - 耗时展示演示")
        print("=" * 60)

        runner = JSONRunner(config_file=config_file, workspace=".")
        success = runner.run_tests()

        # 生成报告
        report_generator = ReportGenerator(runner.results, report_path)
        report_generator.save_report()

        print(f"\n报告已保存到: {report_path}")
        print(f"测试结果: {'全部通过' if success else '有测试失败'}")

    finally:
        # 清理临时文件
        os.unlink(config_file)


if __name__ == "__main__":
    main()
