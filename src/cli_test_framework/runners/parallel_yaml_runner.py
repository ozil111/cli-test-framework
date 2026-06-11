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


class ParallelYAMLRunner(ParallelRunner):
    """并行YAML测试运行器"""

    def __init__(self, config_file="test_cases.yaml", workspace: Optional[str] = None,
                 max_workers: Optional[int] = None, execution_mode: str = "thread",
                 test_case_filter: Optional[list] = None,
                 history_dir: Optional[str] = None,
                 regression_threshold: float = 1.5):
        self.total_physical = os.cpu_count() or 4
        self.safe_capacity = max(1, self.total_physical - 2)

        if max_workers is None:
            max_workers = self.total_physical

        super().__init__(config_file, workspace, max_workers, execution_mode, test_case_filter,
                         history_dir, regression_threshold)
        self.path_resolver = PathResolver(self.workspace)
        self._print_lock = threading.Lock()

        self.cpu_semaphore = AtomicSemaphore(self.safe_capacity) if execution_mode == "thread" else None

        print(f"✅ [Resource Manager] Detected {self.total_physical} CPUs. Pool size set to {self.safe_capacity}.")

    def _assign_relative_cpu_cores(self) -> None:
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
            for case in candidates:
                if not case.resources:
                    case.resources = {}
                case.resources["cpu_cores"] = 1
            return

        allocated = 0
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
        """从YAML文件加载测试用例"""
        try:
            import yaml
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)

            self.load_setup_from_config(config)
            self.test_cases = parse_test_cases(config, self.workspace, self.path_resolver)

            print(f"Successfully loaded {len(self.test_cases)} test cases")

            if self.test_cases:
                history_cases = {}
                if self.history_dir:
                    from ..core.history_store import load_history
                    hist = load_history(self.history_dir)
                    history_cases = hist.get("cases", {})

                def get_estimated_time(case):
                    if case.name in history_cases:
                        return history_cases[case.name]["avg_duration"]
                    return (case.resources or {}).get("estimated_time", 0)

                print("Optimizing execution order based on estimated duration...")
                self.test_cases.sort(key=get_estimated_time, reverse=True)
                top_case = self.test_cases[0]
                top_est = get_estimated_time(top_case)
                source = "history" if top_case.name in history_cases else "config"
                print(f"Heaviest task: {top_case.name} (Est: {top_est:.2f}s, source: {source})")

            self._assign_relative_cpu_cores()
        except Exception as e:
            sys.exit(f"Failed to load configuration file: {str(e)}")

    def _run_sequence(self, case: TestCase) -> Dict[str, Any]:
        return execute_sequence(
            case_name=case.name,
            steps=case.steps,
            workspace=str(self.workspace) if self.workspace else None,
            print_prefix="[Worker]",
            lock=self._print_lock,
        )

    def run_single_test(self, case: TestCase) -> Dict[str, Any]:
        required_cores = 1
        if case.resources and "cpu_cores" in case.resources:
            required_cores = case.resources["cpu_cores"]

        if required_cores > self.safe_capacity:
            required_cores = self.safe_capacity

        tokens_acquired = 0
        task_env = None

        if self.execution_mode == "thread" and self.cpu_semaphore is not None:
            if not self.cpu_semaphore.acquire(required_cores):
                required_cores = 1
                self.cpu_semaphore.acquire(1)
                tokens_acquired = 1
            else:
                tokens_acquired = required_cores

            task_env = {
                "OMP_NUM_THREADS": str(required_cores),
                "MKL_NUM_THREADS": str(required_cores),
                "NPROC": str(required_cores),
            }

            with self._print_lock:
                print(f"  [Scheduler] Task '{case.name}' acquired {tokens_acquired} cores. Running...")

        if case.steps:
            result = self._run_sequence(case)
        else:
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

            result = execute_single_test_case(
                case_data,
                str(self.workspace) if self.workspace else None,
                env=task_env
            )

            if result["output"].strip():
                with self._print_lock:
                    print(f"  [Worker] Command output for {case.name}:")
                    for line in result["output"].splitlines():
                        print(f"    {line}")

            if result["status"] != "passed" and result.get("message"):
                with self._print_lock:
                    print(f"  [Worker] Error for {case.name}: {result['message']}")

        if self.execution_mode == "thread" and self.cpu_semaphore is not None and tokens_acquired > 0:
            self.cpu_semaphore.release(tokens_acquired)
            with self._print_lock:
                print(f"  [Scheduler] Task '{case.name}' released {tokens_acquired} cores.")

        return result
