from typing import Optional, Dict, Any
from ..core.parallel_runner import ParallelRunner
from ..core.test_case import TestCase
from ..core.execution import execute_single_test_case
from ..core.types import TestCaseData
from ..utils.path_resolver import PathResolver, parse_command_string, resolve_paths
import json
import sys
import threading

class ParallelJSONRunner(ParallelRunner):
    """并行JSON测试运行器"""
    
    def __init__(self, config_file="test_cases.json", workspace: Optional[str] = None,
                 max_workers: Optional[int] = None, execution_mode: str = "thread"):
        """
        初始化并行JSON运行器
        
        Args:
            config_file: JSON配置文件路径
            workspace: 工作目录
            max_workers: 最大并发数
            execution_mode: 执行模式，'thread' 或 'process'
        """
        super().__init__(config_file, workspace, max_workers, execution_mode)
        # Backward-compatible attribute for potential external patches/tests
        self.path_resolver = PathResolver(self.workspace)
        self._print_lock = threading.Lock()  # 用于控制输出顺序

    def load_test_cases(self) -> None:
        """从JSON文件加载测试用例"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)

            # 加载setup配置
            self.load_setup_from_config(config)

            required_fields = ["name", "command", "args", "expected"]
            for case in config["test_cases"]:
                if not all(field in case for field in required_fields):
                    raise ValueError(f"Test case {case.get('name', 'unnamed')} is missing required fields")

                # Use resolver attribute (keeps backward compatibility with tests monkeypatching it)
                case["command"] = self.path_resolver.parse_command_string(case["command"])
                case["args"] = self.path_resolver.resolve_paths(case["args"])
                self.test_cases.append(TestCase(**case))

            print(f"Successfully loaded {len(self.test_cases)} test cases")

            # Heuristic scheduling: longest estimated time first to improve parallel utilization.
            if self.test_cases:
                print("Optimizing execution order based on estimated duration...")
                self.test_cases.sort(
                    key=lambda c: (c.resources or {}).get("estimated_time", 0),
                    reverse=True,
                )
                top_case = self.test_cases[0]
                top_est = (top_case.resources or {}).get("estimated_time", 0)
                print(f"Heaviest task: {top_case.name} (Est: {top_est}s)")
        except Exception as e:
            sys.exit(f"Failed to load configuration file: {str(e)}")

    def run_single_test(self, case: TestCase) -> Dict[str, Any]:
        """运行单个测试用例（线程安全版本）"""
        case_data: TestCaseData = {
            "name": case.name,
            "command": case.command,
            "args": case.args,
            "expected": case.expected,
            "description": case.description or None,
            "timeout": case.timeout,
            "resources": case.resources,
        }

        command_preview = f"{case_data['command']} {' '.join(case_data['args'])}".strip()
        with self._print_lock:
            print(f"  [Worker] Executing command: {command_preview}")

        result = execute_single_test_case(case_data, str(self.workspace) if self.workspace else None)

        if result["output"].strip():
            with self._print_lock:
                print(f"  [Worker] Command output for {case.name}:")
                for line in result["output"].splitlines():
                    print(f"    {line}")

        if result["status"] != "passed" and result.get("message"):
            with self._print_lock:
                print(f"  [Worker] Error for {case.name}: {result['message']}")

        return result 