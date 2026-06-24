import logging

logger = logging.getLogger("cli_test_framework.utils.report_generator")


class ReportGenerator:
    def __init__(self, results: dict, file_path: str):
        self.results = results
        self.file_path = file_path

    def generate_report(self) -> str:
        report = "Test Results Summary:\n"
        report += f"Total Tests: {self.results['total']}\n"
        report += f"Passed: {self.results['passed']}\n"
        report += f"Failed: {self.results['failed']}\n"
        total_duration = sum(d.get('duration', 0) for d in self.results['details'])
        report += f"Total Duration: {total_duration:.2f}s\n\n"
        
        report += "Detailed Results:\n"
        for detail in self.results['details']:
            status_icon = "✓" if detail['status'] == 'passed' else "✗"
            duration = detail.get('duration', 0)
            report += f"{status_icon} {detail['name']} ({duration:.2f}s)\n"
            if detail.get('message'):
                report += f"   -> {detail['message']}\n"
        
        # 添加失败案例的详细输出信息（含 timeout 等非通过状态）
        failed_tests = [detail for detail in self.results['details'] if detail['status'] != 'passed']
        if failed_tests:
            report += "\n" + "="*50 + "\n"
            report += "FAILED TEST CASES DETAILS:\n"
            report += "="*50 + "\n\n"
            
            for i, failed_test in enumerate(failed_tests, 1):
                report += f"{i}. Test: {failed_test['name']}\n"
                report += "-" * 40 + "\n"
                
                # 添加执行的命令
                if failed_test.get('command'):
                    report += f"Command: {failed_test['command']}\n"
                
                # 添加返回码
                if failed_test.get('return_code') is not None:
                    report += f"Return Code: {failed_test['return_code']}\n"
                
                # 添加失败原因
                if failed_test.get('message'):
                    report += f"Error Message: {failed_test['message']}\n"
                
                # 添加命令的完整输出（这是最重要的部分）
                if failed_test.get('output'):
                    report += f"\nCommand Output:\n"
                    report += "=" * 30 + "\n"
                    report += f"{failed_test['output']}\n"
                    report += "=" * 30 + "\n"
                
                # 添加错误堆栈信息（如果有的话）
                if failed_test.get('error_trace'):
                    report += f"Error Trace:\n{failed_test['error_trace']}\n"
                
                # 添加执行时间（如果有的话）
                if failed_test.get('duration'):
                    report += f"Duration: {failed_test['duration']:.2f}s\n"
                
                report += "\n"
        
        return report

    def save_report(self) -> None:
        report = self.generate_report()
        with open(self.file_path, 'w', encoding='utf-8') as f:
            f.write(report)

    def print_report(self) -> None:
        report = self.generate_report()
        logger.info(report)