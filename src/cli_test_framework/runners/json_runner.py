from typing import Optional, Dict, Any
from ..core.base_runner import BaseRunner
from ..core.test_case import TestCase
from ..core.execution import execute_single_test_case
from ..core.types import TestCaseData
from ..utils.path_resolver import PathResolver, parse_command_string, resolve_paths
import json
import sys

class JSONRunner(BaseRunner):
    def __init__(self, config_file="test_cases.json", workspace: Optional[str] = None):
        super().__init__(config_file, workspace)
        # Backward-compatible attribute for tests that patch path_resolver
        self.path_resolver = PathResolver(self.workspace)

    def load_test_cases(self) -> None:
        """Load test cases from a JSON file."""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)

            # 加载setup配置
            self.load_setup_from_config(config)

            required_fields = ["name", "command", "args", "expected"]
            for case in config["test_cases"]:
                if not all(field in case for field in required_fields):
                    raise ValueError(f"Test case {case.get('name', 'unnamed')} is missing required fields")

                # 使用智能命令解析，正确处理包含空格的路径
                # Use resolver attribute (keeps backward compatibility with tests monkeypatching it)
                case["command"] = self.path_resolver.parse_command_string(case["command"])
                case["args"] = self.path_resolver.resolve_paths(case["args"])
                self.test_cases.append(TestCase(**case))

            print(f"Successfully loaded {len(self.test_cases)} test cases")
            # print(self.test_cases)
        except Exception as e:
            sys.exit(f"Failed to load configuration file: {str(e)}")

    def run_single_test(self, case: TestCase) -> Dict[str, str]:
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
        print(f"  Executing command: {command_preview}")

        result = execute_single_test_case(case_data, str(self.workspace) if self.workspace else None)

        if result["output"].strip():
            print("  Command output:")
            for line in result["output"].splitlines():
                print(f"    {line}")

        if result["status"] != "passed" and result.get("message"):
            print(f"  Error: {result['message']}")

        return result