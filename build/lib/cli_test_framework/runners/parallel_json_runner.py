from typing import Optional, Dict, Any
from ..core.parallel_runner import ParallelRunner
from ..core.test_case import TestCase
from ..utils.path_resolver import PathResolver
import json
import subprocess
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

                case["command"] = self.path_resolver.parse_command_string(case["command"])
                case["args"] = self.path_resolver.resolve_paths(case["args"])
                self.test_cases.append(TestCase(**case))

            print(f"Successfully loaded {len(self.test_cases)} test cases")
        except Exception as e:
            sys.exit(f"Failed to load configuration file: {str(e)}")

    def run_single_test(self, case: TestCase) -> Dict[str, Any]:
        """运行单个测试用例（线程安全版本）"""
        result = {
            "name": case.name,
            "status": "failed",
            "message": "",
            "output": "",
            "command": "",
            "return_code": None
        }

        try:
            command = f"{case.command} {' '.join(case.args)}"
            result["command"] = command
            
            # 线程安全的输出
            with self._print_lock:
                print(f"  [Worker] Executing command: {command}")
            
            process = subprocess.run(
                command,
                cwd=self.workspace if self.workspace else None,
                capture_output=True,
                text=True,
                check=False,
                shell=True
            )

            output = process.stdout + process.stderr
            result["output"] = output
            result["return_code"] = process.returncode
            
            # 线程安全的输出
            if output.strip():
                with self._print_lock:
                    print(f"  [Worker] Command output for {case.name}:")
                    for line in output.splitlines():
                        print(f"    {line}")

            # 检查返回码
            if "return_code" in case.expected:
                with self._print_lock:
                    print(f"  [Worker] Checking return code for {case.name}: {process.returncode} (expected: {case.expected['return_code']})")
                self.assertions.return_code_equals(
                    process.returncode,
                    case.expected["return_code"]
                )

            # 检查输出包含
            if "output_contains" in case.expected:
                with self._print_lock:
                    print(f"  [Worker] Checking output contains for {case.name}...")
                for expected_text in case.expected["output_contains"]:
                    self.assertions.contains(output, expected_text)

            # 检查正则匹配
            if "output_matches" in case.expected:
                with self._print_lock:
                    print(f"  [Worker] Checking output matches regex for {case.name}...")
                self.assertions.matches(output, case.expected["output_matches"])

            result["status"] = "passed"
            
        except AssertionError as e:
            result["message"] = str(e)
        except Exception as e:
            result["message"] = f"Execution error: {str(e)}"

        return result 