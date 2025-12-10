from typing import Optional, Dict, Any
from ..core.parallel_runner import ParallelRunner
from ..core.test_case import TestCase
from ..core.execution import execute_single_test_case
from ..core.types import TestCaseData
from ..utils.path_resolver import PathResolver, parse_command_string, resolve_paths
import json
import sys
import threading
import os

class ParallelJSONRunner(ParallelRunner):
    """并行JSON测试运行器"""
    
    def __init__(self, config_file="test_cases.json", workspace: Optional[str] = None,
                 max_workers: Optional[int] = None, execution_mode: str = "thread"):
        """
        初始化并行JSON运行器
        
        Args:
            config_file: JSON配置文件路径
            workspace: 工作目录
            max_workers: 最大并发数
            execution_mode: 执行模式，'thread' 或 'process'
        """
        # 1. 自动感知：获取物理核心数
        # 如果获取失败默认为 4，留 2 个核给系统/Python (防止 GUI 卡死)
        self.total_physical = os.cpu_count() or 4
        self.safe_capacity = max(1, self.total_physical - 2)
        
        # 2. 设置 Worker 数量
        # 注意：这里 max_workers 可以设得很大（比如等于总核数），
        # 因为我们不再靠 worker 数量限制并发，而是靠下面的 semaphore 限制。
        if max_workers is None:
            max_workers = self.total_physical
            
        super().__init__(config_file, workspace, max_workers, execution_mode)
        # Backward-compatible attribute for potential external patches/tests
        self.path_resolver = PathResolver(self.workspace)
        self._print_lock = threading.Lock()  # 用于控制输出顺序
        
        # 3. 初始化资源池 (Semaphore)
        # 这里的 value 代表"当前剩余可用的核心数"
        # Note: Semaphore only works for thread mode. Process mode will use original behavior.
        self.cpu_semaphore = threading.Semaphore(self.safe_capacity) if execution_mode == "thread" else None
        
        print(f"✅ [Resource Manager] Detected {self.total_physical} CPUs. Pool size set to {self.safe_capacity}.")

    def load_test_cases(self) -> None:
        """从JSON文件加载测试用例"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)

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

            # Heuristic scheduling: longest estimated time first to improve parallel utilization.
            if self.test_cases:
                print("Optimizing execution order based on estimated duration...")
                self.test_cases.sort(
                    key=lambda c: (c.resources or {}).get("estimated_time", 0),
                    reverse=True,
                )
                top_case = self.test_cases[0]
                top_est = (top_case.resources or {}).get("estimated_time", 0)
                print(f"Heaviest task: {top_case.name} (Est: {top_est}s)")
        except Exception as e:
            sys.exit(f"Failed to load configuration file: {str(e)}")

    def run_single_test(self, case: TestCase) -> Dict[str, Any]:
        """
        运行单个测试用例（线程安全版本，支持资源感知调度）
        
        对于 thread 模式：使用信号量控制 CPU 核心分配
        对于 process 模式：回退到原始行为（进程间信号量需要额外实现）
        """
        # 1. 获取任务所需核数
        # 优先读取 json 配置，如果没有配置，默认假设它是轻型任务 (1核)
        # 如果你的 json 里有很多重型任务，可以在配置中明确指定
        required_cores = 1
        if case.resources and "cpu_cores" in case.resources:
            required_cores = case.resources["cpu_cores"]
        
        # 安全钳位：如果任务需要的核数超过了机器总核数，强制降级，避免死锁
        if required_cores > self.safe_capacity:
            required_cores = self.safe_capacity
        
        tokens_acquired = 0
        task_env = None
        
        # 只在 thread 模式下使用信号量进行资源管理
        if self.execution_mode == "thread" and self.cpu_semaphore is not None:
            try:
                # 2. 申请资源 (阻塞等待)
                # 必须循环申请，因为 Semaphore 一次只给 1 个
                for _ in range(required_cores):
                    self.cpu_semaphore.acquire()
                    tokens_acquired += 1
                
                # 3. 构造环境约束
                # 这步非常重要：显式告诉求解器"你只能用这么多核"
                # 这能防止求解器无视 Python 的调度，私自占满 CPU
                task_env = {
                    "OMP_NUM_THREADS": str(required_cores),
                    "MKL_NUM_THREADS": str(required_cores),  # 针对 Intel 数学库
                    "NPROC": str(required_cores)             # 某些求解器专用
                }
                
                # 打印调试信息
                with self._print_lock:
                    print(f"  [Scheduler] Task '{case.name}' acquired {tokens_acquired} cores. Running...")
            except Exception as e:
                # 如果获取资源失败，记录错误但不阻塞
                with self._print_lock:
                    print(f"  [Scheduler] Warning: Failed to acquire resources for '{case.name}': {e}")
        
        # 准备测试用例数据
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
        with self._print_lock:
            if self.execution_mode != "thread" or self.cpu_semaphore is None:
                print(f"  [Worker] Executing command: {command_preview}")

        # 4. 执行测试 (传入 env)
        result = execute_single_test_case(
            case_data, 
            str(self.workspace) if self.workspace else None,
            env=task_env  # 注入环境变量
        )

        if result["output"].strip():
            with self._print_lock:
                print(f"  [Worker] Command output for {case.name}:")
                for line in result["output"].splitlines():
                    print(f"    {line}")

        if result["status"] != "passed" and result.get("message"):
            with self._print_lock:
                print(f"  [Worker] Error for {case.name}: {result['message']}")
        
        # 5. 归还资源
        if self.execution_mode == "thread" and self.cpu_semaphore is not None and tokens_acquired > 0:
            try:
                for _ in range(tokens_acquired):
                    self.cpu_semaphore.release()
                
                with self._print_lock:
                    # 只有看到这条日志，说明资源释放了，下一个排队的任务才能开始
                    print(f"  [Scheduler] Task '{case.name}' released {tokens_acquired} cores.")
            except Exception as e:
                with self._print_lock:
                    print(f"  [Scheduler] Warning: Failed to release resources for '{case.name}': {e}")

        return result 