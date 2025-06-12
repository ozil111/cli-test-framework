#!/usr/bin/env python3
"""
Setup模块使用示例

这个示例展示了如何使用CLI测试框架的setup模块来设置环境变量和自定义前置任务。
"""

import os
import sys
import tempfile
import json

# 添加源代码路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from cli_test_framework import JSONRunner, BaseSetup, EnvironmentSetup


class DatabaseSetup(BaseSetup):
    """自定义数据库设置插件示例"""
    
    def setup(self):
        """初始化测试数据库"""
        print(f"[{self.get_name()}] 初始化测试数据库...")
        print(f"[{self.get_name()}] 数据库连接: {self.config.get('connection', 'default')}")
        # 这里可以添加实际的数据库初始化代码
        
    def teardown(self):
        """清理测试数据库"""
        print(f"[{self.get_name()}] 清理测试数据库...")
        # 这里可以添加数据库清理代码


class ServiceSetup(BaseSetup):
    """自定义服务设置插件示例"""
    
    def setup(self):
        """启动测试服务"""
        port = self.config.get('port', 8080)
        print(f"[{self.get_name()}] 启动测试服务在端口 {port}...")
        # 这里可以添加服务启动代码
        
    def teardown(self):
        """停止测试服务"""
        print(f"[{self.get_name()}] 停止测试服务...")
        # 这里可以添加服务停止代码


def create_test_config():
    """创建测试配置文件"""
    config = {
        "setup": {
            "environment_variables": {
                "EXAMPLE_ENV": "production",
                "DATABASE_URL": "postgresql://localhost:5432/test",
                "API_KEY": "test-api-key-123",
                "DEBUG": "false"
            }
        },
        "test_cases": [
            {
                "name": "检查环境变量设置",
                "command": "python",
                "args": ["-c", "import os; print(f'环境: {os.environ.get(\"EXAMPLE_ENV\")}, 数据库: {os.environ.get(\"DATABASE_URL\")[:20]}...')"],
                "expected": {
                    "return_code": 0,
                    "output_contains": ["环境: production", "数据库: postgresql://localhost"]
                }
            },
            {
                "name": "验证API密钥",
                "command": "python", 
                "args": ["-c", "import os; key = os.environ.get('API_KEY'); print(f'API密钥长度: {len(key)}' if key else 'API密钥未设置')"],
                "expected": {
                    "return_code": 0,
                    "output_contains": ["API密钥长度: 15"]
                }
            },
            {
                "name": "测试调试模式",
                "command": "python",
                "args": ["-c", "import os; print('调试模式已关闭' if os.environ.get('DEBUG') == 'false' else '调试模式已开启')"],
                "expected": {
                    "return_code": 0,
                    "output_contains": ["调试模式已关闭"]
                }
            }
        ]
    }
    
    # 创建临时配置文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
        return f.name


def example_1_basic_environment_setup():
    """示例1: 基本环境变量设置"""
    print("=" * 60)
    print("示例1: 基本环境变量设置")
    print("=" * 60)
    
    # 创建配置文件
    config_file = create_test_config()
    
    try:
        # 创建runner并运行测试
        runner = JSONRunner(config_file)
        success = runner.run_tests()
        
        print(f"\n测试结果: {'✅ 全部通过' if success else '❌ 有测试失败'}")
        print(f"通过: {runner.results['passed']}, 失败: {runner.results['failed']}")
        
    finally:
        # 清理临时文件
        os.unlink(config_file)


def example_2_custom_setup_plugins():
    """示例2: 自定义setup插件"""
    print("\n" + "=" * 60)
    print("示例2: 自定义setup插件")
    print("=" * 60)
    
    # 创建简单的测试配置（不包含setup）
    config = {
        "test_cases": [
            {
                "name": "简单测试",
                "command": "python",
                "args": ["-c", "print('自定义setup插件测试')"],
                "expected": {
                    "return_code": 0,
                    "output_contains": ["自定义setup插件测试"]
                }
            }
        ]
    }
    
    # 创建临时配置文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(config, f)
        config_file = f.name
    
    try:
        # 创建runner
        runner = JSONRunner(config_file)
        
        # 添加自定义setup插件
        db_setup = DatabaseSetup({"connection": "test://localhost:5432/testdb"})
        service_setup = ServiceSetup({"port": 9090})
        env_setup = EnvironmentSetup({
            "environment_variables": {
                "CUSTOM_SETUP_TEST": "active",
                "SERVICE_PORT": "9090"
            }
        })
        
        runner.setup_manager.add_setup(db_setup)
        runner.setup_manager.add_setup(service_setup)
        runner.setup_manager.add_setup(env_setup)
        
        # 运行测试
        success = runner.run_tests()
        
        print(f"\n测试结果: {'✅ 全部通过' if success else '❌ 有测试失败'}")
        
    finally:
        # 清理临时文件
        os.unlink(config_file)


def example_3_manual_setup_lifecycle():
    """示例3: 手动setup生命周期管理"""
    print("\n" + "=" * 60)
    print("示例3: 手动setup生命周期管理")
    print("=" * 60)
    
    # 创建环境设置
    env_setup = EnvironmentSetup({
        "environment_variables": {
            "MANUAL_TEST": "enabled",
            "TIMESTAMP": "2024-01-01"
        }
    })
    
    print("手动执行setup...")
    env_setup.setup()
    
    # 验证环境变量
    print(f"MANUAL_TEST = {os.environ.get('MANUAL_TEST')}")
    print(f"TIMESTAMP = {os.environ.get('TIMESTAMP')}")
    
    print("\n手动执行teardown...")
    env_setup.teardown()
    
    # 验证环境变量已清理
    print(f"清理后 MANUAL_TEST = {os.environ.get('MANUAL_TEST')}")
    print(f"清理后 TIMESTAMP = {os.environ.get('TIMESTAMP')}")


def main():
    """主函数"""
    print("CLI测试框架 Setup模块使用示例")
    print("=" * 60)
    
    try:
        # 运行示例
        example_1_basic_environment_setup()
        example_2_custom_setup_plugins()
        example_3_manual_setup_lifecycle()
        
        print("\n" + "=" * 60)
        print("🎉 所有示例运行完成!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 运行示例时出错: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main()) 