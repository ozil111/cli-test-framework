"""
进程工作器模块
用于多进程并行测试执行，避免序列化问题
"""

from typing import Dict, Any
from .execution import execute_single_test_case
from .types import TestCaseData

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