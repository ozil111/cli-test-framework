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
        
        for case in self.test_cases:
            result = self.run_single_test(case)
            # print("result: ", result)
            self.results["details"].append(result)
            if result["status"] == "passed":
                self.results["passed"] += 1
            else:
                self.results["failed"] += 1
                
        return self.results["failed"] == 0

    @abstractmethod
    def run_single_test(self, case: TestCase) -> Dict[str, str]:
        """Run a single test case and return the result"""
        pass