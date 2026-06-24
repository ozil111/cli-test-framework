import subprocess
import signal
import time
import os
import shlex
from typing import Any, List, Optional, Dict

from .assertions import Assertions
from .types import ExpectedResult, TestCaseData, TestResultData

# Commands that are shell builtins (not real executables).
# With shell=False, these must be wrapped via the platform shell.
if os.name == 'nt':
    _SHELL_BUILTINS = frozenset(['echo', 'dir', 'type', 'copy', 'del', 'ren',
                                  'cd', 'md', 'rd', 'set', 'cls', 'move'])
else:
    _SHELL_BUILTINS = frozenset(['echo', 'cd', 'pwd', 'export', 'source'])


def _normalize_cmd_list(command: str, args: List[str]) -> List[str]:
    """If command is a shell builtin, wrap with the platform shell interpreter."""
    if command.lower() in _SHELL_BUILTINS:
        if os.name == 'nt':
            return ['cmd', '/d', '/c', command, *args]
        else:
            return ['/bin/sh', '-c', shlex.join([command, *args])]
    return [command, *args]


def validate_result(
    expected: ExpectedResult,
    actual: TestResultData,
    workspace: Optional[str] = None,
) -> None:
    """
    Pure validation logic. Raises AssertionError on mismatch.

    :param expected:  Expected result specification from the test case.
    :param actual:    Actual test result data produced by command execution.
    :param workspace: Working directory; used to resolve relative file paths in
                      ``compare_files`` assertions.
    """
    assertions = Assertions()

    if "return_code" in expected:
        assertions.return_code_equals(actual["return_code"], expected["return_code"])

    if "output_contains" in expected:
        for text in expected["output_contains"]:
            assertions.contains(actual["output"], text)

    if "output_matches" in expected and expected["output_matches"]:
        assertions.matches(actual["output"], expected["output_matches"])

    if "compare_files" in expected:
        for spec in expected["compare_files"]:
            _dispatch_file_compare(spec, workspace, assertions)


def _dispatch_file_compare(
    spec: Dict[str, Any],
    workspace: Optional[str],
    assertions: Assertions,
) -> None:
    """Extract fields from a compare_files spec dict and delegate to Assertions.compare_files."""
    actual_path = spec.get("actual", "")
    baseline_path = spec.get("baseline", "")
    file_type = spec.get("type", None)

    # All remaining keys are forwarded as comparator kwargs
    known_keys = {"actual", "baseline", "type"}
    comparator_kwargs = {k: v for k, v in spec.items() if k not in known_keys}

    assertions.compare_files(
        actual_path=actual_path,
        baseline_path=baseline_path,
        file_type=file_type,
        workspace=workspace,
        **comparator_kwargs,
    )


def execute_single_test_case(case: TestCaseData, workspace: Optional[str] = None, env: Optional[Dict[str, str]] = None) -> TestResultData:
    """
    Stateless execution of a single test case.
    
    Args:
        case: Test case data
        workspace: Working directory for test execution
        env: Optional environment variables to inject/override (merged with os.environ)
    """
    start_time = time.time()
    cmd_list = _normalize_cmd_list(case["command"], [str(arg) for arg in case["args"]])
    timeout_limit = case.get("timeout", 3600)

    full_command = " ".join(cmd_list)

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
        process = subprocess.Popen(
            cmd_list,
            cwd=workspace if workspace else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            errors="replace",
            start_new_session=True,
            env=current_env,
        )

        try:
            stdout, stderr = process.communicate(timeout=timeout_limit)
        except subprocess.TimeoutExpired:
            # Kill the entire process group to avoid orphan processes
            # (e.g. when the tested program forks and those children
            # would otherwise outlive the timeout kill of the direct child).
            try:
                if os.name == 'posix':
                    os.killpg(process.pid, signal.SIGKILL)
                else:
                    process.kill()
            except (ProcessLookupError, OSError):
                pass  # process already exited
            stdout, stderr = process.communicate()  # reap the process
            result["status"] = "timeout"
            result["message"] = f"Timeout reached! Killed after {timeout_limit} seconds."
            result["output"] = (stdout or "") + (stderr or "")
            result["return_code"] = None
        else:
            output = stdout + stderr
            result["output"] = output
            result["return_code"] = process.returncode

            validate_result(case["expected"], result, workspace)
            result["status"] = "passed"
    except AssertionError as exc:
        result["message"] = str(exc)
    except Exception as exc:
        result["message"] = f"Execution error: {str(exc)}"
    finally:
        result["duration"] = time.time() - start_time

    return result

