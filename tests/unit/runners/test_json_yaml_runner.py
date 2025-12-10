import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
from cli_test_framework.runners.json_runner import JSONRunner
from cli_test_framework.runners.yaml_runner import YAMLRunner


class TestJSONRunner(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        config = {
            "test_cases": [
                {
                    "name": "simple",
                    "command": "echo",
                    "args": ["ok"],
                    "expected": {"return_code": 0},
                }
            ]
        }
        self.config_path = Path(self.temp_dir.name) / "json_config.json"
        self.config_path.write_text(json.dumps(config), encoding="utf-8")
        self.runner = JSONRunner(str(self.config_path), workspace=self.temp_dir.name)

    def test_load_test_cases(self):
        self.runner.load_test_cases()
        self.assertGreater(len(self.runner.test_cases), 0, "No test cases loaded")

    def test_run_tests(self):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="ok\n", stderr="")
            success = self.runner.run_tests()
        self.assertTrue(success, "Some tests failed")

    def tearDown(self):
        self.temp_dir.cleanup()


class TestYAMLRunner(unittest.TestCase):
    def setUp(self):
        import importlib

        try:
            self.yaml = importlib.import_module("yaml")
        except ImportError:
            self.skipTest("pyyaml not installed")

        self.temp_dir = tempfile.TemporaryDirectory()
        config = {
            "test_cases": [
                {
                    "name": "simple",
                    "command": "echo",
                    "args": ["ok"],
                    "expected": {"return_code": 0},
                }
            ]
        }
        self.config_path = Path(self.temp_dir.name) / "yaml_config.yaml"
        self.config_path.write_text(
            self.yaml.safe_dump(config, allow_unicode=True), encoding="utf-8"
        )
        self.runner = YAMLRunner(str(self.config_path), workspace=self.temp_dir.name)

    def test_load_test_cases(self):
        self.runner.load_test_cases()
        self.assertGreater(len(self.runner.test_cases), 0, "No test cases loaded")

    def test_run_tests(self):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="ok\n", stderr="")
            success = self.runner.run_tests()
        self.assertTrue(success, "Some tests failed")

    def tearDown(self):
        self.temp_dir.cleanup()


if __name__ == "__main__":
    unittest.main()

