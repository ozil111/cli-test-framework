from typing import Optional, Dict, Any
from ..core.base_runner import BaseRunner
from ..core.test_case import TestCase
from ..core.execution import execute_single_test_case
from ..core.types import TestCaseData
from ..utils.path_resolver import PathResolver, parse_command_string, resolve_paths
import sys

class YAMLRunner(BaseRunner):
    def __init__(self, config_file="test_cases.yaml", workspace: Optional[str] = None):
        super().__init__(config_file, workspace)
        # Backward-compatible attribute for tests that patch path_resolver
        self.path_resolver = PathResolver(self.workspace)

    def load_test_cases(self):
        """Load test cases from a YAML file."""
        try:
            import yaml
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                
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
        except Exception as e:
            sys.exit(f"Failed to load configuration file: {str(e)}")

    def run_single_test(self, case: TestCase) -> Dict[str, Any]:
        """Run a single test case and return the result"""
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