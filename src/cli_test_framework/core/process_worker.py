"""
进程工作器模块
用于多进程并行测试执行，避免序列化问题
"""

from typing import Dict, Any, List
from .execution import execute_single_test_case
from .types import TestCaseData

def _run_sequence_in_process(test_index: int, case_data: Dict[str, Any], workspace: str = None) -> Dict[str, Any]:
    """Run a sequence test case with multiple steps (fail-fast) in a process worker."""
    steps: List[Dict[str, Any]] = case_data["steps"]
    combined_output = ""
    total_duration = 0.0
    all_passed = True
    last_result = None
    failed_step = None

    for i, step in enumerate(steps):
        step_name = f"{case_data['name']} [step {i+1}/{len(steps)}]"
        step_case: TestCaseData = {
            "name": step_name,
            "command": step["command"],
            "args": step["args"],
            "expected": step["expected"],
            "description": None,
            "timeout": step.get("timeout"),
            "resources": None,
        }

        command_preview = f"{step['command']} {' '.join(step['args'])}".strip()
        print(f"  [Process Worker {test_index}] Executing step {i+1}/{len(steps)}: {command_preview}")

        result = execute_single_test_case(step_case, workspace)

        if result["output"].strip():
            print(f"  [Process Worker {test_index}] Command output for {step_name}:")
            for line in result["output"].splitlines():
                print(f"    {line}")

        combined_output += result["output"]
        total_duration += result["duration"]
        last_result = result

        if result["status"] != "passed":
            all_passed = False
            failed_step = i + 1
            if result.get("message"):
                print(f"  [Process Worker {test_index}] Error at step {i+1}: {result['message']}")
            break

    status = "passed" if all_passed else last_result["status"]
    message = ""
    if not all_passed:
        message = f"Failed at step {failed_step}/{len(steps)}: {last_result['message']}"

    command_summary = " -> ".join(
        f"{s['command']} {' '.join(s['args'])}".strip() for s in steps
    )

    return {
        "name": case_data["name"],
        "status": status,
        "message": message,
        "command": command_summary,
        "output": combined_output,
        "return_code": last_result["return_code"] if last_result else None,
        "duration": total_duration,
    }

def run_test_in_process(test_index: int, case_data: Dict[str, Any], workspace: str = None) -> Dict[str, Any]:
    """
    在独立进程中运行单个测试用例
    
    Args:
        test_index: 测试索引
        case_data: 测试用例数据字典
        workspace: 工作目录
    
    Returns:
        测试结果字典
    """
    # Sequence mode
    if case_data.get("steps"):
        return _run_sequence_in_process(test_index, case_data, workspace)

    # Single command mode
    case: TestCaseData = {
        "name": case_data["name"],
        "command": case_data["command"],
        "args": case_data["args"],
        "expected": case_data["expected"],
        "description": case_data.get("description"),
        "timeout": case_data.get("timeout"),
        "resources": case_data.get("resources"),
    }

    command_preview = f"{case['command']} {' '.join(case['args'])}".strip()
    print(f"  [Process Worker {test_index}] Executing command: {command_preview}")

    result = execute_single_test_case(case, workspace)

    if result["output"].strip():
        print(f"  [Process Worker {test_index}] Command output for {case['name']}:")
        for line in result["output"].splitlines():
            print(f"    {line}")

    if result["status"] != "passed" and result.get("message"):
        print(f"  [Process Worker {test_index}] Error for {case['name']}: {result['message']}")

    return result 