class ReportGenerator:
    def __init__(self, results: dict, file_path: str):
        self.results = results
        self.file_path = file_path

    def generate_report(self) -> str:
        report = "Test Results Summary:\n"
        report += f"Total Tests: {self.results['total']}\n"
        report += f"Passed: {self.results['passed']}\n"
        report += f"Failed: {self.results['failed']}\n\n"
        report += "Detailed Results:\n"
        for detail in self.results['details']:
            status_icon = "✓" if detail['status'] == 'passed' else "✗"
            report += f"{status_icon} {detail['name']}\n"
            if detail.get('message'):
                report += f"   -> {detail['message']}\n"
        return report

    def save_report(self) -> None:
        report = self.generate_report()
        with open(self.file_path, 'w', encoding='utf-8') as f:
            f.write(report)

    def print_report(self) -> None:
        report = self.generate_report()
        print(report)