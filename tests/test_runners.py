import unittest
from src.runners.json_runner import JSONRunner
from src.runners.yaml_runner import YAMLRunner

class TestJSONRunner(unittest.TestCase):
    def setUp(self):
        self.runner = JSONRunner("tests/fixtures/test_cases.json")

    def test_load_test_cases(self):
        self.runner.load_test_cases()
        self.assertGreater(len(self.runner.test_cases), 0, "No test cases loaded")

    def test_run_tests(self):
        self.runner.load_test_cases()
        results = self.runner.run_all_tests()
        self.assertTrue(results, "Some tests failed")

class TestYAMLRunner(unittest.TestCase):
    def setUp(self):
        self.runner = YAMLRunner("tests/fixtures/test_cases.yaml")

    def test_load_test_cases(self):
        self.runner.load_test_cases()
        self.assertGreater(len(self.runner.test_cases), 0, "No test cases loaded")

    def test_run_tests(self):
        self.runner.load_test_cases()
        results = self.runner.run_all_tests()
        self.assertTrue(results, "Some tests failed")

if __name__ == "__main__":
    unittest.main()