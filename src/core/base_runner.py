from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict, Any, Optional
from .test_case import TestCase
from .assertions import Assertions

class BaseRunner(ABC):
    def __init__(self, config_file: str, workspace: Optional[str] = None):
        if workspace:
            self.workspace = Path(workspace)
        else:
            self.workspace = Path(__file__).parent.parent.parent
        self.config_path = self.workspace / config_file
        self.test_cases: List[TestCase] = []
        self.results: Dict[str, Any] = {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "details": []
        }
        self.assertions = Assertions()

    @abstractmethod
    def load_test_cases(self) -> None:
        """Load test cases from configuration file"""
        pass

    def run_tests(self) -> bool:
        """Run all test cases and return whether all tests passed"""
        self.load_test_cases()
        self.results["total"] = len(self.test_cases)
        
        print(f"\nStarting test execution... Total tests: {self.results['total']}")
        print("=" * 50)
        
        for i, case in enumerate(self.test_cases, 1):
            print(f"\nRunning test {i}/{self.results['total']}: {case.name}")
            result = self.run_single_test(case)
            self.results["details"].append(result)
            if result["status"] == "passed":
                self.results["passed"] += 1
                print(f"✓ Test passed: {case.name}")
            else:
                self.results["failed"] += 1
                print(f"✗ Test failed: {case.name}")
                if result["message"]:
                    print(f"  Error: {result['message']}")
                
        print("\n" + "=" * 50)
        print(f"Test execution completed. Passed: {self.results['passed']}, Failed: {self.results['failed']}")
        return self.results["failed"] == 0

    @abstractmethod
    def run_single_test(self, case: TestCase) -> Dict[str, str]:
        """Run a single test case and return the result"""
        pass