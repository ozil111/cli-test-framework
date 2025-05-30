# 并行测试示例用法
from src.runners.parallel_json_runner import ParallelJSONRunner
from src.runners.json_runner import JSONRunner
from src.utils.report_generator import ReportGenerator
import sys
import time

def run_sequential_test():
    """运行顺序测试"""
    print("=" * 60)
    print("运行顺序测试...")
    print("=" * 60)
    
    start_time = time.time()
    runner = JSONRunner(config_file="D:/Document/xcode/cli-test-framework/tests/fixtures/test_cases.json", workspace=".")
    success = runner.run_tests()
    end_time = time.time()
    
    print(f"\n顺序测试完成，耗时: {end_time - start_time:.2f} 秒")
    return success, runner.results, end_time - start_time

def run_parallel_test(max_workers=None, execution_mode="thread"):
    """运行并行测试"""
    print("=" * 60)
    print(f"运行并行测试 (模式: {execution_mode}, 工作线程: {max_workers or 'auto'})...")
    print("=" * 60)
    
    start_time = time.time()
    runner = ParallelJSONRunner(
        config_file="D:/Document/xcode/cli-test-framework/tests/fixtures/test_cases.json", 
        workspace=".",
        max_workers=max_workers,
        execution_mode=execution_mode
    )
    success = runner.run_tests()
    end_time = time.time()
    
    print(f"\n并行测试完成，耗时: {end_time - start_time:.2f} 秒")
    return success, runner.results, end_time - start_time

def main():
    """主函数：比较顺序和并行测试的性能"""
    
    # 运行顺序测试
    seq_success, seq_results, seq_time = run_sequential_test()
    
    # 运行并行测试（线程模式）
    par_success, par_results, par_time = run_parallel_test(max_workers=4, execution_mode="thread")
    
    # 运行并行测试（进程模式）
    proc_success, proc_results, proc_time = run_parallel_test(max_workers=2, execution_mode="process")
    
    # 性能比较
    print("\n" + "=" * 60)
    print("性能比较结果:")
    print("=" * 60)
    print(f"顺序执行时间:     {seq_time:.2f} 秒")
    print(f"并行执行时间(线程): {par_time:.2f} 秒 (加速比: {seq_time/par_time:.2f}x)")
    print(f"并行执行时间(进程): {proc_time:.2f} 秒 (加速比: {seq_time/proc_time:.2f}x)")
    
    # 生成报告
    if par_success:
        report_generator = ReportGenerator(par_results, "parallel_test_report.txt")
        report_generator.print_report()
        report_generator.save_report()
        print(f"\n并行测试报告已保存到: parallel_test_report.txt")
    
    # 返回最终结果
    return seq_success and par_success and proc_success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 