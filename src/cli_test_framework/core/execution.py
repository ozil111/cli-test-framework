import subprocess
import time
import os
from typing import Optional, Dict

from .assertions import Assertions
from .types import ExpectedResult, TestCaseData, TestResultData


def validate_result(expected: ExpectedResult, actual: TestResultData) -> None:
    """
    Pure validation logic. Raises AssertionError on mismatch.
    """
    assertions = Assertions()

    if "return_code" in expected:
        assertions.return_code_equals(actual["return_code"], expected["return_code"])

    if "output_contains" in expected:
        for text in expected["output_contains"]:
            assertions.contains(actual["output"], text)

    if "output_matches" in expected and expected["output_matches"]:
        assertions.matches(actual["output"], expected["output_matches"])


def execute_single_test_case(case: TestCaseData, workspace: Optional[str] = None, env: Optional[Dict[str, str]] = None) -> TestResultData:
    """
    Stateless execution of a single test case.
    
    Args:
        case: Test case data
        workspace: Working directory for test execution
        env: Optional environment variables to inject/override (merged with os.environ)
    """
    start_time = time.time()
    full_command = f"{case['command']} {' '.join(case['args'])}".strip()
    timeout_limit = case.get("timeout", 3600)

    result: TestResultData = {
        "name": case["name"],
        "status": "failed",
        "message": "",
        "command": full_command,
        "output": "",
        "return_code": None,
        "duration": 0.0,
    }

    # Prepare environment variables
    # Default to current environment, merge with provided env if any
    current_env = os.environ.copy()
    if env:
        current_env.update(env)

    try:
        process = subprocess.run(
            full_command,
            cwd=workspace if workspace else None,
            capture_output=True,
            text=True,
            check=False,
            shell=True,
            timeout=timeout_limit if timeout_limit is not None else None,
            env=current_env,
        )

        output = process.stdout + process.stderr
        result["output"] = output
        result["return_code"] = process.returncode

        validate_result(case["expected"], result)
        result["status"] = "passed"
    except subprocess.TimeoutExpired as exc:
        result["status"] = "timeout"
        result["message"] = f"Timeout reached! Killed after {timeout_limit} seconds."
        result["output"] = (exc.stdout or "") + (exc.stderr or "")
        result["return_code"] = None
    except AssertionError as exc:
        result["message"] = str(exc)
    except Exception as exc:
        result["message"] = f"Execution error: {str(exc)}"
    finally:
        result["duration"] = time.time() - start_time

    return result

