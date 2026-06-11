import json
import sys
import threading
import os
from typing import Optional, Dict, Any

from ..core.parallel_runner import ParallelRunner, AtomicSemaphore
from ..core.config_loader import parse_test_cases, execute_sequence
from ..core.test_case import TestCase
from ..core.execution import execute_single_test_case
from ..core.types import TestCaseData
from ..utils.path_resolver import PathResolver

class ParallelJSONRunner(ParallelRunner):
    """并行JSON测试运行器"""
    
    def __init__(self, config_file="test_cases.json", workspace: Optional[str] = None,
                 max_workers: Optional[int] = None, execution_mode: str = "thread",
                 test_case_filter: Optional[list] = None,
                 history_dir: Optional[str] = None,
                 regression_threshold: float = 1.5):
        """
        初始化并行JSON运行器
        
        Args:
            config_file: JSON配置文件路径
            workspace: 工作目录
            max_workers: 最大并发数
            execution_mode: 执行模式，'thread' 或 'process'
            test_case_filter: 只运行指定名称的测试用例
            history_dir: .symtest 历史记录目录
            regression_threshold: 回归检测阈值
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
            
        super().__init__(config_file, workspace, max_workers, execution_mode, test_case_filter,
                         history_dir, regression_threshold)
        # Backward-compatible attribute for potential external patches/tests
        self.path_resolver = PathResolver(self.workspace)
        self._print_lock = threading.Lock()  # 用于控制输出顺序
        
        # 3. 初始化资源池 (AtomicSemaphore，避免逐个 acquire 的部分占有死锁)
        self.cpu_semaphore = AtomicSemaphore(self.safe_capacity) if execution_mode == "thread" else None
        
        print(f"✅ [Resource Manager] Detected {self.total_physical} CPUs. Pool size set to {self.safe_capacity}.")

    def _assign_relative_cpu_cores(self) -> None:
        """
        Assign cpu_cores proportionally based on estimated_time and min_memory_mb
        for cases without an explicit cpu_cores setting.

        Weight formula: estimated_time (seconds) + min_memory_mb / 100.
        - time component: longer cases get more cores
        - memory component: memory-heavy cases get a small bonus (100 MB ≈ 1 second worth of weight)
        """
        candidates = [c for c in self.test_cases if not (c.resources and "cpu_cores" in c.resources)]
        if not candidates:
            return

        def weight(case: TestCase) -> float:
            res = case.resources or {}
            est = float(res.get("estimated_time") or 0)
            mem = float(res.get("min_memory_mb") or 0)
            return est + mem / 100.0

        weights = [weight(c) for c in candidates]
        total_weight = sum(weights)

        if total_weight <= 0:
            # All weights zero: give every case 1 core
            for case in candidates:
                if not case.resources:
                    case.resources = {}
                case.resources["cpu_cores"] = 1
            return

        allocated = 0
        # Sort by weight descending so heavier cases get rounded-up shares first
        indexed = sorted(enumerate(zip(candidates, weights)), key=lambda x: x[1][1], reverse=True)
        for rank, (idx, (case, w)) in enumerate(indexed):
            if rank == len(indexed) - 1:
                share = max(1, self.safe_capacity - allocated)
            else:
                share = max(1, int(round(self.safe_capacity * w / total_weight)))
            if not case.resources:
                case.resources = {}
            case.resources["cpu_cores"] = share
            allocated += share

    def load_test_cases(self) -> None:
        """从JSON文件加载测试用例"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)

            self.load_setup_from_config(config)
            self.test_cases = parse_test_cases(config, self.workspace, self.path_resolver)

            print(f"Successfully loaded {len(self.test_cases)} test cases")

            # Heuristic scheduling: longest estimated time first to improve parallel utilization.
            if self.test_cases:
                # Load history for smart scheduling if available
                history_cases = {}
                if self.history_dir:
                    from ..core.history_store import load_history
                    hist = load_history(self.history_dir)
                    history_cases = hist.get("cases", {})

                def get_estimated_time(case):
                    """Prefer history avg_duration > config estimated_time > 0"""
                    if case.name in history_cases:
                        return history_cases[case.name]["avg_duration"]
                    return (case.resources or {}).get("estimated_time", 0)

                print("Optimizing execution order based on estimated duration...")
                self.test_cases.sort(key=get_estimated_time, reverse=True)
                top_case = self.test_cases[0]
                top_est = get_estimated_time(top_case)
                source = "history" if top_case.name in history_cases else "config"
                print(f"Heaviest task: {top_case.name} (Est: {top_est:.2f}s, source: {source})")

            # Relative CPU allocation for cases without explicit cpu_cores
            self._assign_relative_cpu_cores()
        except Exception as e:
            sys.exit(f"Failed to load configuration file: {str(e)}")

    def _run_sequence(self, case: TestCase) -> Dict[str, Any]:
        """Run a sequence test case with multiple steps (fail-fast, thread-safe printing)."""
        return execute_sequence(
            case_name=case.name,
            steps=case.steps,
            workspace=str(self.workspace) if self.workspace else None,
            print_prefix="[Worker]",
            lock=self._print_lock,
        )

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
            # 2. 原子申请资源：所有 required_cores 个令牌一次性获取，避免部分占有死锁
            if not self.cpu_semaphore.acquire(required_cores):
                # 超时未获取到资源，降级为 1 核执行
                required_cores = 1
                self.cpu_semaphore.acquire(1)
                tokens_acquired = 1
            else:
                tokens_acquired = required_cores

            # 3. 构造环境约束，限制求解器使用的核心数
            task_env = {
                "OMP_NUM_THREADS": str(required_cores),
                "MKL_NUM_THREADS": str(required_cores),
                "NPROC": str(required_cores),
            }

            with self._print_lock:
                print(f"  [Scheduler] Task '{case.name}' acquired {tokens_acquired} cores. Running...")

        # 4. 执行测试（支持 sequence 和单命令两种模式）
        if case.steps:
            result = self._run_sequence(case)
        else:
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

            # 执行测试 (传入 env)
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
        
        # 5. 归还资源（一次性原子释放）
        if self.execution_mode == "thread" and self.cpu_semaphore is not None and tokens_acquired > 0:
            self.cpu_semaphore.release(tokens_acquired)
            with self._print_lock:
                print(f"  [Scheduler] Task '{case.name}' released {tokens_acquired} cores.")

        return result 