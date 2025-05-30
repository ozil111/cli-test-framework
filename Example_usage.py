# Example usage
from src.runners.json_runner import JSONRunner
from src.core.base_runner import BaseRunner
from src.utils.report_generator import ReportGenerator
import sys

def main():
    runner = JSONRunner(config_file="D:/Document/xcode/Compare-File-Tool/test_script/test_cases.json", workspace="D:/Document/xcode/Compare-File-Tool")
    success = runner.run_tests()
    
    # Generate and save the report
    report_generator = ReportGenerator(runner.results, "D:/Document/xcode/Compare-File-Tool/test_script/test_report.txt")
    report_generator.print_report()
    report_generator.save_report()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()