"""
进程工作器模块
用于多进程并行测试执行，避免序列化问题
"""

import subprocess
import sys
from typing import Dict, Any
from .test_case import TestCase
from .assertions import Assertions

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
    # 重新创建TestCase对象（避免序列化问题）
    case = TestCase(
        name=case_data["name"],
        command=case_data["command"],
        args=case_data["args"],
        expected=case_data["expected"]
    )
    
    # 创建断言对象
    assertions = Assertions()
    
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
        print(f"  [Process Worker {test_index}] Executing command: {command}")
        
        process = subprocess.run(
            command,
            cwd=workspace if workspace else None,
            capture_output=True,
            text=True,
            check=False,
            shell=True
        )

        output = process.stdout + process.stderr
        result["output"] = output
        result["return_code"] = process.returncode
        
        if output.strip():
            print(f"  [Process Worker {test_index}] Command output for {case.name}:")
            for line in output.splitlines():
                print(f"    {line}")

        # 检查返回码
        if "return_code" in case.expected:
            print(f"  [Process Worker {test_index}] Checking return code for {case.name}: {process.returncode} (expected: {case.expected['return_code']})")
            assertions.return_code_equals(
                process.returncode,
                case.expected["return_code"]
            )

        # 检查输出包含
        if "output_contains" in case.expected:
            print(f"  [Process Worker {test_index}] Checking output contains for {case.name}...")
            for expected_text in case.expected["output_contains"]:
                assertions.contains(output, expected_text)

        # 检查正则匹配
        if "output_matches" in case.expected:
            print(f"  [Process Worker {test_index}] Checking output matches regex for {case.name}...")
            assertions.matches(output, case.expected["output_matches"])

        result["status"] = "passed"
        
    except AssertionError as e:
        result["message"] = str(e)
    except Exception as e:
        result["message"] = f"Execution error: {str(e)}"

    return result 