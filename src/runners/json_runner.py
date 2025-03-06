from typing import Optional
from ..core.base_runner import BaseRunner
from ..core.test_case import TestCase
from ..utils.path_resolver import PathResolver
import json
import subprocess
import sys
from typing import Dict, Any

class JSONRunner(BaseRunner):
    def __init__(self, config_file="test_cases.json", workspace: Optional[str] = None):
        super().__init__(config_file, workspace)
        self.path_resolver = PathResolver(self.workspace)

    def load_test_cases(self) -> None:
        """Load test cases from a JSON file."""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)

            required_fields = ["name", "command", "args", "expected"]
            for case in config["test_cases"]:
                if not all(field in case for field in required_fields):
                    raise ValueError(f"Test case {case.get('name', 'unnamed')} is missing required fields")

                case["command"] = self.path_resolver.resolve_command(case["command"])
                case["args"] = self.path_resolver.resolve_paths(case["args"])
                self.test_cases.append(TestCase(**case))

            print(f"Successfully loaded {len(self.test_cases)} test cases")
            # print(self.test_cases)
        except Exception as e:
            sys.exit(f"Failed to load configuration file: {str(e)}")

    def run_single_test(self, case: TestCase) -> Dict[str, str]:
        result = {
            "name": case.name,
            "status": "failed",
            "message": ""
        }

        try:
            # Use TestCase instance to handle the test
            # print(self.workspace)
            command = f"{case.command} {' '.join(case.args)}"
            # print(command)
            process = subprocess.run(
                command,
                cwd=self.workspace if self.workspace else None,
                capture_output=True,
                text=True,
                check=False,
                shell=True
            )

            output = process.stdout + process.stderr
            # print(output)

            # Check return code
            if "return_code" in case.expected:
                self.assertions.return_code_equals(
                    process.returncode,
                    case.expected["return_code"]
                )

            # Check output contains
            if "output_contains" in case.expected:
                for expected_text in case.expected["output_contains"]:
                    self.assertions.contains(output, expected_text)

            # Check regex patterns
            if "output_matches" in case.expected:
                self.assertions.matches(output, case.expected["output_matches"])

            result["status"] = "passed"
            
        except AssertionError as e:
            result["message"] = str(e)
        except Exception as e:
            result["message"] = f"Execution error: {str(e)}"

        return result