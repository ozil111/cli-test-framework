import sys
import os
# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import unittest
from src.runners.json_runner import JSONRunner
from src.core.base_runner import BaseRunner
from src.utils.report_generator import ReportGenerator

def main():
    runner = JSONRunner(
        config_file="D:/Document/xcode/cli-test-framework/tests/fixtures/test_cases1.json",
        workspace="D:/Document/xcode/Compare-File-Tool"
    )
    success = runner.run_tests()
    
    # 生成报告
    report_generator = ReportGenerator(
        runner.results, 
        "D:/Document/xcode/cli-test-framework/tests/test_report.txt"
    )
    report_generator.print_report()  # 打印到控制台
    report_generator.save_report()   # 保存到文件
    
    print(f"\n报告已保存到: D:/Document/xcode/cli-test-framework/tests/test_report.txt")
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()