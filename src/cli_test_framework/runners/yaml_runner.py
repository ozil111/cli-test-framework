from typing import Optional, Dict, Any
from ..core.base_runner import BaseRunner
from ..core.test_case import TestCase
from ..utils.path_resolver import PathResolver
import subprocess
import sys

class YAMLRunner(BaseRunner):
    def __init__(self, config_file="test_cases.yaml", workspace: Optional[str] = None):
        super().__init__(config_file, workspace)
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
                
                case["command"] = self.path_resolver.parse_command_string(case["command"])
                case["args"] = self.path_resolver.resolve_paths(case["args"])
                self.test_cases.append(TestCase(**case))
                
            print(f"Successfully loaded {len(self.test_cases)} test cases")
        except Exception as e:
            sys.exit(f"Failed to load configuration file: {str(e)}")

    def run_single_test(self, case: TestCase) -> Dict[str, Any]:
        """Run a single test case and return the result"""
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
            print(f"  Executing command: {command}")
            
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
            
            if output.strip():
                print("  Command output:")
                for line in output.splitlines():
                    print(f"    {line}")

            # Check return code
            if "return_code" in case.expected:
                print(f"  Checking return code: {process.returncode} (expected: {case.expected['return_code']})")
                self.assertions.return_code_equals(
                    process.returncode,
                    case.expected["return_code"]
                )

            # Check output contains
            if "output_contains" in case.expected:
                print("  Checking output contains expected text...")
                for expected_text in case.expected["output_contains"]:
                    self.assertions.contains(output, expected_text)

            # Check regex patterns
            if "output_matches" in case.expected:
                print("  Checking output matches regex pattern...")
                self.assertions.matches(output, case.expected["output_matches"])

            result["status"] = "passed"
            
        except AssertionError as e:
            result["message"] = str(e)
        except Exception as e:
            result["message"] = f"Execution error: {str(e)}"

        return result