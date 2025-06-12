import unittest
import os
import tempfile
import json
from unittest.mock import patch, MagicMock
from src.cli_test_framework.core.setup import BaseSetup, EnvironmentSetup, SetupManager
from src.cli_test_framework.runners.json_runner import JSONRunner
from src.cli_test_framework.runners.yaml_runner import YAMLRunner
from src.cli_test_framework.runners.parallel_json_runner import ParallelJSONRunner


class TestBaseSetup(unittest.TestCase):
    """测试BaseSetup基类"""
    
    def test_abstract_methods(self):
        """测试抽象方法"""
        # BaseSetup是抽象类，不能直接实例化
        with self.assertRaises(TypeError):
            BaseSetup()

    def test_get_name(self):
        """测试获取setup名称"""
        class TestSetup(BaseSetup):
            def setup(self):
                pass
            def teardown(self):
                pass
        
        test_setup = TestSetup()
        self.assertEqual(test_setup.get_name(), "TestSetup")


class TestEnvironmentSetup(unittest.TestCase):
    """测试EnvironmentSetup插件"""
    
    def setUp(self):
        """测试前准备"""
        # 保存原始环境
        self.original_env = dict(os.environ)
    
    def tearDown(self):
        """测试后清理"""
        # 恢复原始环境
        os.environ.clear()
        os.environ.update(self.original_env)
    
    def test_setup_new_environment_variables(self):
        """测试设置新的环境变量"""
        config = {
            "environment_variables": {
                "TEST_VAR1": "value1",
                "TEST_VAR2": "value2"
            }
        }
        
        env_setup = EnvironmentSetup(config)
        env_setup.setup()
        
        # 验证环境变量已设置
        self.assertEqual(os.environ.get("TEST_VAR1"), "value1")
        self.assertEqual(os.environ.get("TEST_VAR2"), "value2")
    
    def test_setup_overwrite_existing_variables(self):
        """测试覆盖现有环境变量"""
        # 设置原有变量
        os.environ["EXISTING_VAR"] = "original_value"
        
        config = {
            "environment_variables": {
                "EXISTING_VAR": "new_value"
            }
        }
        
        env_setup = EnvironmentSetup(config)
        env_setup.setup()
        
        # 验证变量被覆盖
        self.assertEqual(os.environ.get("EXISTING_VAR"), "new_value")
    
    def test_teardown_restore_original_variables(self):
        """测试teardown恢复原始变量"""
        # 设置原有变量
        os.environ["EXISTING_VAR"] = "original_value"
        
        config = {
            "environment_variables": {
                "EXISTING_VAR": "new_value",
                "NEW_VAR": "new_var_value"
            }
        }
        
        env_setup = EnvironmentSetup(config)
        env_setup.setup()
        
        # 验证变量已更改
        self.assertEqual(os.environ.get("EXISTING_VAR"), "new_value")
        self.assertEqual(os.environ.get("NEW_VAR"), "new_var_value")
        
        # 执行teardown
        env_setup.teardown()
        
        # 验证原变量已恢复，新变量已删除
        self.assertEqual(os.environ.get("EXISTING_VAR"), "original_value")
        self.assertIsNone(os.environ.get("NEW_VAR"))
    
    def test_empty_config(self):
        """测试空配置"""
        env_setup = EnvironmentSetup({})
        
        # 应该不抛出异常
        env_setup.setup()
        env_setup.teardown()
    
    def test_none_config(self):
        """测试None配置"""
        env_setup = EnvironmentSetup()
        
        # 应该不抛出异常
        env_setup.setup()
        env_setup.teardown()


class TestSetupManager(unittest.TestCase):
    """测试SetupManager"""
    
    def setUp(self):
        """测试前准备"""
        self.manager = SetupManager()
        self.original_env = dict(os.environ)
    
    def tearDown(self):
        """测试后清理"""
        # 恢复原始环境
        os.environ.clear()
        os.environ.update(self.original_env)
    
    def test_add_setup(self):
        """测试添加setup"""
        env_setup = EnvironmentSetup({"environment_variables": {"TEST": "value"}})
        self.manager.add_setup(env_setup)
        
        self.assertEqual(len(self.manager.setups), 1)
        self.assertEqual(self.manager.setups[0], env_setup)
    
    def test_setup_all(self):
        """测试执行所有setup"""
        config = {"environment_variables": {"TEST_VAR": "test_value"}}
        env_setup = EnvironmentSetup(config)
        self.manager.add_setup(env_setup)
        
        # 执行setup
        self.manager.setup_all()
        
        # 验证环境变量已设置
        self.assertEqual(os.environ.get("TEST_VAR"), "test_value")
    
    def test_teardown_all(self):
        """测试执行所有teardown"""
        config = {"environment_variables": {"TEST_VAR": "test_value"}}
        env_setup = EnvironmentSetup(config)
        self.manager.add_setup(env_setup)
        
        # 执行setup和teardown
        self.manager.setup_all()
        self.assertEqual(os.environ.get("TEST_VAR"), "test_value")
        
        self.manager.teardown_all()
        self.assertIsNone(os.environ.get("TEST_VAR"))
    
    def test_multiple_setups_execution_order(self):
        """测试多个setup的执行顺序"""
        execution_order = []
        
        class TestSetup1(BaseSetup):
            def setup(self):
                execution_order.append("setup1")
            def teardown(self):
                execution_order.append("teardown1")
        
        class TestSetup2(BaseSetup):
            def setup(self):
                execution_order.append("setup2")
            def teardown(self):
                execution_order.append("teardown2")
        
        self.manager.add_setup(TestSetup1())
        self.manager.add_setup(TestSetup2())
        
        # 执行setup
        self.manager.setup_all()
        self.assertEqual(execution_order, ["setup1", "setup2"])
        
        # 执行teardown（应该逆序）
        execution_order.clear()
        self.manager.teardown_all()
        self.assertEqual(execution_order, ["teardown2", "teardown1"])
    
    def test_empty_manager(self):
        """测试空manager"""
        # 应该不抛出异常
        self.manager.setup_all()
        self.manager.teardown_all()


class TestRunnerIntegration(unittest.TestCase):
    """测试runner与setup模块的集成"""
    
    def setUp(self):
        """测试前准备"""
        self.original_env = dict(os.environ)
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """测试后清理"""
        # 恢复原始环境
        os.environ.clear()
        os.environ.update(self.original_env)
    
    def create_test_config_file(self, config_data, filename="test_config.json"):
        """创建临时测试配置文件"""
        config_path = os.path.join(self.temp_dir, filename)
        with open(config_path, 'w') as f:
            json.dump(config_data, f)
        return config_path
    
    def test_json_runner_with_setup(self):
        """测试JSONRunner与setup的集成"""
        config = {
            "setup": {
                "environment_variables": {
                    "TEST_ENV": "test_value"
                }
            },
            "test_cases": [
                {
                    "name": "Test env var",
                    "command": "python",
                    "args": ["-c", "import os; print(os.environ.get('TEST_ENV', 'NOT_SET'))"],
                    "expected": {
                        "return_code": 0,
                        "output_contains": ["test_value"]
                    }
                }
            ]
        }
        
        config_path = self.create_test_config_file(config)
        
        # 运行测试
        runner = JSONRunner(config_path, workspace=self.temp_dir)
        
        # Mock subprocess.run to avoid actual execution
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="test_value\n",
                stderr=""
            )
            
            # 执行测试前环境变量不应存在
            self.assertIsNone(os.environ.get("TEST_ENV"))
            
            # 运行测试（会执行setup）
            result = runner.run_tests()
            
            # 测试完成后环境变量应该被清理
            self.assertIsNone(os.environ.get("TEST_ENV"))
    
    def test_setup_configuration_loading(self):
        """测试setup配置加载"""
        config = {
            "setup": {
                "environment_variables": {
                    "VAR1": "value1",
                    "VAR2": "value2"
                }
            },
            "test_cases": []
        }
        
        config_path = self.create_test_config_file(config)
        runner = JSONRunner(config_path, workspace=self.temp_dir)
        runner.load_test_cases()
        
        # 验证setup已加载
        self.assertEqual(len(runner.setup_manager.setups), 1)
        self.assertIsInstance(runner.setup_manager.setups[0], EnvironmentSetup)
    
    def test_yaml_runner_with_setup(self):
        """测试YAMLRunner与setup的集成"""
        import yaml
        
        config = {
            "setup": {
                "environment_variables": {
                    "YAML_TEST_ENV": "yaml_value"
                }
            },
            "test_cases": [
                {
                    "name": "Test YAML env var",
                    "command": "echo",
                    "args": ["test"],
                    "expected": {
                        "return_code": 0
                    }
                }
            ]
        }
        
        yaml_path = os.path.join(self.temp_dir, "test_config.yaml")
        with open(yaml_path, 'w') as f:
            yaml.dump(config, f)
        
        runner = YAMLRunner(yaml_path, workspace=self.temp_dir)
        runner.load_test_cases()
        
        # 验证setup已加载
        self.assertEqual(len(runner.setup_manager.setups), 1)
        self.assertIsInstance(runner.setup_manager.setups[0], EnvironmentSetup)
    
    def test_parallel_runner_with_setup(self):
        """测试ParallelJSONRunner与setup的集成"""
        config = {
            "setup": {
                "environment_variables": {
                    "PARALLEL_TEST_ENV": "parallel_value"
                }
            },
            "test_cases": [
                {
                    "name": "Test parallel env var",
                    "command": "echo",
                    "args": ["test"],
                    "expected": {
                        "return_code": 0
                    }
                }
            ]
        }
        
        config_path = self.create_test_config_file(config)
        runner = ParallelJSONRunner(config_path, workspace=self.temp_dir, max_workers=2)
        runner.load_test_cases()
        
        # 验证setup已加载
        self.assertEqual(len(runner.setup_manager.setups), 1)
        self.assertIsInstance(runner.setup_manager.setups[0], EnvironmentSetup)


if __name__ == "__main__":
    unittest.main() 