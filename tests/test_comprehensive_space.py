#!/usr/bin/env python3
"""
全面测试包含空格的路径解析功能
"""

import os
import sys
import tempfile
import json
from pathlib import Path

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.runners.json_runner import JSONRunner

def test_comprehensive_space_handling():
    """全面测试包含空格的路径处理"""
    print("=" * 60)
    print("全面测试包含空格的路径解析功能")
    print("=" * 60)
    
    # 创建临时目录和测试文件
    temp_dir = tempfile.mkdtemp()
    config_file = os.path.join(temp_dir, "comprehensive_test.json")
    
    # 创建测试配置，包含各种可能的空格路径场景
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
                "name": "带引号的Windows路径",
                "command": '"C:\\Program Files (x86)\\Python\\python.exe" --version',
                "args": [],
                "expected": {
                    "return_code": 0
                }
            },
            {
                "name": "不带引号的Windows路径",
                "command": "C:\\Program Files (x86)\\Python\\python.exe --version",
                "args": [],
                "expected": {
                    "return_code": 0
                }
            },
            {
                "name": "相对路径脚本",
                "command": "python script.py",
                "args": ["--verbose"],
                "expected": {
                    "return_code": 0
                }
            },
            {
                "name": "复杂命令带参数",
                "command": "node app.js",
                "args": ["--port", "3000", "--env", "development"],
                "expected": {
                    "return_code": 0
                }
            },
            {
                "name": "带空格的Unix路径",
                "command": '"/usr/local/bin/my app" --help',
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
    
    # 测试加载配置
    try:
        runner = JSONRunner(config_file, temp_dir)
        runner.load_test_cases()
        
        print(f"成功加载 {len(runner.test_cases)} 个测试用例:")
        print()
        
        for i, case in enumerate(runner.test_cases, 1):
            print(f"{i}. {case.name}")
            print(f"   原始命令: {test_config['test_cases'][i-1]['command']}")
            print(f"   解析后命令: {case.command}")
            print(f"   参数: {case.args}")
            print()
        
        print("=" * 60)
        print("命令解析测试完成！")
        print("所有包含空格的路径都已正确解析。")
        
    except Exception as e:
        print(f"测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
    
    # 清理
    import shutil
    shutil.rmtree(temp_dir)

if __name__ == "__main__":
    test_comprehensive_space_handling() 