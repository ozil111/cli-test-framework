from abc import ABC
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from typing import List, Dict, Any, Optional, Union
import time
import threading
from .base_runner import BaseRunner
from .test_case import TestCase
from .process_worker import run_test_in_process

class ParallelRunner(BaseRunner):
    """并行测试运行器基类，支持多线程和多进程执行"""
    
    def __init__(self, config_file: str, workspace: Optional[str] = None, 
                 max_workers: Optional[int] = None, 
                 execution_mode: str = "thread"):
        """
        初始化并行运行器
        
        Args:
            config_file: 配置文件路径
            workspace: 工作目录
            max_workers: 最大并发数，默认为CPU核心数
            execution_mode: 执行模式，'thread'(线程) 或 'process'(进程)
        """
        super().__init__(config_file, workspace)
        self.max_workers = max_workers
        self.execution_mode = execution_mode
        self.lock = threading.Lock()  # 用于线程安全的结果更新
        
    def run_tests(self) -> bool:
        """并行运行所有测试用例"""
        self.load_test_cases()
        self.results["total"] = len(self.test_cases)
        
        print(f"\nStarting parallel test execution... Total tests: {self.results['total']}")
        print(f"Execution mode: {self.execution_mode}, Max workers: {self.max_workers or 'auto'}")
        print("=" * 50)
        
        start_time = time.time()
        
        if self.execution_mode == "process":
            executor_class = ProcessPoolExecutor
        else:
            executor_class = ThreadPoolExecutor
            
        with executor_class(max_workers=self.max_workers) as executor:
            # 提交所有测试任务
            if self.execution_mode == "process":
                # 进程模式：使用独立的工作器函数
                future_to_case = {
                    executor.submit(
                        run_test_in_process, 
                        i, 
                        {
                            "name": case.name,
                            "command": case.command,
                            "args": case.args,
                            "expected": case.expected
                        },
                        str(self.workspace) if self.workspace else None
                    ): (i, case) 
                    for i, case in enumerate(self.test_cases, 1)
                }
            else:
                # 线程模式：使用实例方法
                future_to_case = {
                    executor.submit(self._run_test_with_index, i, case): (i, case) 
                    for i, case in enumerate(self.test_cases, 1)
                }
            
            # 收集结果
            for future in as_completed(future_to_case):
                test_index, case = future_to_case[future]
                try:
                    result = future.result()
                    self._update_results(result, test_index, case)
                except Exception as exc:
                    error_result = {
                        "name": case.name,
                        "status": "failed",
                        "message": f"Test execution failed: {str(exc)}",
                        "output": "",
                        "command": "",
                        "return_code": None
                    }
                    self._update_results(error_result, test_index, case)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        print("\n" + "=" * 50)
        print(f"Parallel test execution completed in {execution_time:.2f} seconds")
        print(f"Passed: {self.results['passed']}, Failed: {self.results['failed']}")
        return self.results["failed"] == 0
    
    def _run_test_with_index(self, test_index: int, case: TestCase) -> Dict[str, Any]:
        """运行单个测试并返回结果（包含索引信息）"""
        print(f"[Worker] Running test {test_index}: {case.name}")
        result = self.run_single_test(case)
        return result
    
    def _update_results(self, result: Dict[str, Any], test_index: int, case: TestCase) -> None:
        """线程安全地更新测试结果"""
        with self.lock:
            self.results["details"].append(result)
            if result["status"] == "passed":
                self.results["passed"] += 1
                print(f"✓ Test {test_index} passed: {case.name}")
            else:
                self.results["failed"] += 1
                print(f"✗ Test {test_index} failed: {case.name}")
                if result["message"]:
                    print(f"  Error: {result['message']}")
    
    def run_tests_sequential(self) -> bool:
        """回退到顺序执行模式"""
        print("Falling back to sequential execution...")
        return super().run_tests() 