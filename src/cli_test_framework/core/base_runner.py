from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict, Any, Optional
from .test_case import TestCase
from .assertions import Assertions
from .setup import SetupManager, EnvironmentSetup
from .execution import execute_single_test_case

class BaseRunner(ABC):
    def __init__(self, config_file: str, workspace: Optional[str] = None,
                 test_case_filter: Optional[List[str]] = None):
        if workspace:
            self.workspace = Path(workspace)
        else:
            self.workspace = Path(__file__).parent.parent.parent
        self.config_path = self.workspace / config_file
        self.test_cases: List[TestCase] = []
        self.test_case_filter: Optional[List[str]] = test_case_filter
        self.results: Dict[str, Any] = {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "details": []
        }
        self.assertions = Assertions()
        self.setup_manager = SetupManager()

    @abstractmethod
    def load_test_cases(self) -> None:
        """Load test cases from configuration file"""
        pass
    
    def load_setup_from_config(self, config: Dict[str, Any]) -> None:
        """从配置文件加载setup配置"""
        setup_config = config.get("setup", {})
        
        # 处理环境变量设置
        if "environment_variables" in setup_config:
            env_setup = EnvironmentSetup({"environment_variables": setup_config["environment_variables"]})
            self.setup_manager.add_setup(env_setup)
        
        # 这里可以扩展支持其他类型的setup插件
        # 例如：
        # if "custom_setups" in setup_config:
        #     for custom_setup_config in setup_config["custom_setups"]:
        #         # 动态加载自定义setup插件
        #         pass

    def _apply_test_case_filter(self) -> None:
        """根据 test_case_filter 过滤测试用例"""
        if self.test_case_filter:
            original_count = len(self.test_cases)
            self.test_cases = [tc for tc in self.test_cases if tc.name in self.test_case_filter]
            filtered_out = original_count - len(self.test_cases)
            if filtered_out > 0:
                print(f"Filtered out {filtered_out} test case(s). Running {len(self.test_cases)} specified case(s).")
            if not self.test_cases:
                print(f"Warning: No matching test cases found for: {self.test_case_filter}")

    def run_tests(self) -> bool:
        """Run all test cases and return whether all tests passed"""
        try:
            self.load_test_cases()
            self._apply_test_case_filter()
            self.results["total"] = len(self.test_cases)
            
            if self.results["total"] == 0:
                print("No test cases to run.")
                return False
            
            # 执行setup任务
            self.setup_manager.setup_all()
            
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
        finally:
            # 确保teardown总是被执行
            self.setup_manager.teardown_all()

    def _run_sequence(self, case: TestCase) -> Dict[str, Any]:
        """Run a sequence test case with multiple steps (fail-fast)."""
        combined_output = ""
        total_duration = 0.0
        all_passed = True
        last_result = None
        failed_step = None

        for i, step in enumerate(case.steps):
            step_name = f"{case.name} [step {i+1}/{len(case.steps)}]"
            case_data = {
                "name": step_name,
                "command": step.command,
                "args": step.args,
                "expected": step.expected,
                "description": None,
                "timeout": step.timeout,
                "resources": None,
            }

            command_preview = f"{step.command} {' '.join(step.args)}".strip()
            print(f"  Executing step {i+1}/{len(case.steps)}: {command_preview}")

            result = execute_single_test_case(
                case_data, str(self.workspace) if self.workspace else None
            )

            if result["output"].strip():
                print("  Command output:")
                for line in result["output"].splitlines():
                    print(f"    {line}")

            combined_output += result["output"]
            total_duration += result["duration"]
            last_result = result

            if result["status"] != "passed":
                all_passed = False
                failed_step = i + 1
                if result.get("message"):
                    print(f"  Error at step {i+1}: {result['message']}")
                break

        status = "passed" if all_passed else last_result["status"]
        message = ""
        if not all_passed:
            message = f"Failed at step {failed_step}/{len(case.steps)}: {last_result['message']}"

        command_summary = " -> ".join(
            f"{s.command} {' '.join(s.args)}".strip() for s in case.steps
        )

        return {
            "name": case.name,
            "status": status,
            "message": message,
            "command": command_summary,
            "output": combined_output,
            "return_code": last_result["return_code"] if last_result else None,
            "duration": total_duration,
        }

    @abstractmethod
    def run_single_test(self, case: TestCase) -> Dict[str, str]:
        """Run a single test case and return the result"""
        pass