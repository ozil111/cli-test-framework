#!/usr/bin/env python3
"""
测试并行运行器的空格路径处理
"""

import os
import sys
import tempfile
import json

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.runners.parallel_json_runner import ParallelJSONRunner

def test_parallel_space_handling():
    """测试并行运行器的空格路径处理"""
    print("=" * 60)
    print("测试并行运行器的空格路径处理")
    print("=" * 60)
    
    # 创建临时目录和测试文件
    temp_dir = tempfile.mkdtemp()
    config_file = os.path.join(temp_dir, "parallel_space_test.json")
    
    # 创建测试配置
    test_config = {
        "test_cases": [
            {
                "name": "简单命令",
                "command": "echo hello",
                "args": [],
                "expected": {
                    "return_code": 0,
                    "output_contains": ["hello"]
                }
            },
            {
                "name": "带引号的路径",
                "command": '"C:\\Program Files (x86)\\Python\\python.exe" --version',
                "args": [],
                "expected": {
                    "return_code": 0
                }
            },
            {
                "name": "不带引号的路径",
                "command": "C:\\Program Files (x86)\\Python\\python.exe --version",
                "args": [],
                "expected": {
                    "return_code": 0
                }
            }
        ]
    }
    
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(test_config, f, ensure_ascii=False, indent=2)
    
    print(f"测试配置文件: {config_file}")
    print(f"临时目录: {temp_dir}")
    print()
    
    # 测试并行运行器
    try:
        runner = ParallelJSONRunner(
            config_file, 
            temp_dir, 
            max_workers=2, 
            execution_mode="thread"
        )
        runner.load_test_cases()
        
        print(f"成功加载 {len(runner.test_cases)} 个测试用例:")
        for i, case in enumerate(runner.test_cases, 1):
            print(f"{i}. {case.name}")
            print(f"   解析后命令: {case.command}")
            print(f"   参数: {case.args}")
        
        print("\n" + "=" * 60)
        print("并行运行器空格路径解析测试完成！")
        
    except Exception as e:
        print(f"测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
    
    # 清理
    import shutil
    shutil.rmtree(temp_dir)

if __name__ == "__main__":
    test_parallel_space_handling() 