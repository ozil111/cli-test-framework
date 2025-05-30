import unittest
import tempfile
import json
import os
import sys
import time
from pathlib import Path

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.runners.parallel_json_runner import ParallelJSONRunner
from src.runners.json_runner import JSONRunner

class TestParallelRunner(unittest.TestCase):
    """并行运行器测试类"""
    
    def setUp(self):
        """设置测试环境"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, "test_config.json")
        
        # 创建测试配置
        test_config = {
            "test_cases": [
                {
                    "name": "测试1",
                    "command": "echo",
                    "args": ["test1"],
                    "expected": {
                        "return_code": 0,
                        "output_contains": ["test1"]
                    }
                },
                {
                    "name": "测试2",
                    "command": "echo",
                    "args": ["test2"],
                    "expected": {
                        "return_code": 0,
                        "output_contains": ["test2"]
                    }
                },
                {
                    "name": "测试3",
                    "command": "echo",
                    "args": ["test3"],
                    "expected": {
                        "return_code": 0,
                        "output_contains": ["test3"]
                    }
                },
                {
                    "name": "测试4",
                    "command": "echo",
                    "args": ["test4"],
                    "expected": {
                        "return_code": 0,
                        "output_contains": ["test4"]
                    }
                }
            ]
        }
        
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(test_config, f, ensure_ascii=False, indent=2)
    
    def tearDown(self):
        """清理测试环境"""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_parallel_vs_sequential_performance(self):
        """测试并行执行相比顺序执行的性能提升"""
        # 顺序执行
        sequential_runner = JSONRunner(self.config_file, self.temp_dir)
        start_time = time.time()
        seq_success = sequential_runner.run_tests()
        seq_time = time.time() - start_time
        
        # 并行执行
        parallel_runner = ParallelJSONRunner(
            self.config_file, 
            self.temp_dir, 
            max_workers=2, 
            execution_mode="thread"
        )
        start_time = time.time()
        par_success = parallel_runner.run_tests()
        par_time = time.time() - start_time
        
        # 验证结果
        self.assertTrue(seq_success, "顺序执行应该成功")
        self.assertTrue(par_success, "并行执行应该成功")
        self.assertEqual(
            sequential_runner.results["total"], 
            parallel_runner.results["total"],
            "测试总数应该相同"
        )
        self.assertEqual(
            sequential_runner.results["passed"], 
            parallel_runner.results["passed"],
            "通过的测试数应该相同"
        )
        
        print(f"\n性能比较:")
        print(f"顺序执行时间: {seq_time:.3f}秒")
        print(f"并行执行时间: {par_time:.3f}秒")
        if par_time > 0:
            print(f"加速比: {seq_time/par_time:.2f}x")
    
    def test_thread_vs_process_mode(self):
        """测试线程模式和进程模式"""
        # 线程模式
        thread_runner = ParallelJSONRunner(
            self.config_file, 
            self.temp_dir, 
            max_workers=2, 
            execution_mode="thread"
        )
        thread_success = thread_runner.run_tests()
        
        # 进程模式
        process_runner = ParallelJSONRunner(
            self.config_file, 
            self.temp_dir, 
            max_workers=2, 
            execution_mode="process"
        )
        process_success = process_runner.run_tests()
        
        # 验证结果
        self.assertTrue(thread_success, "线程模式应该成功")
        self.assertTrue(process_success, "进程模式应该成功")
        self.assertEqual(
            thread_runner.results["passed"], 
            process_runner.results["passed"],
            "两种模式的通过测试数应该相同"
        )
    
    def test_max_workers_configuration(self):
        """测试不同的最大工作线程数配置"""
        for max_workers in [1, 2, 4]:
            with self.subTest(max_workers=max_workers):
                runner = ParallelJSONRunner(
                    self.config_file, 
                    self.temp_dir, 
                    max_workers=max_workers, 
                    execution_mode="thread"
                )
                success = runner.run_tests()
                self.assertTrue(success, f"max_workers={max_workers}时应该成功")
                self.assertEqual(runner.results["passed"], 4, "应该通过4个测试")
    
    def test_fallback_to_sequential(self):
        """测试回退到顺序执行"""
        runner = ParallelJSONRunner(
            self.config_file, 
            self.temp_dir, 
            max_workers=2, 
            execution_mode="thread"
        )
        
        # 测试回退功能
        success = runner.run_tests_sequential()
        self.assertTrue(success, "回退到顺序执行应该成功")
        self.assertEqual(runner.results["passed"], 4, "应该通过4个测试")

if __name__ == '__main__':
    unittest.main() 