"""
CLI Test Framework - A powerful command-line testing framework

This package provides tools for testing command-line applications and scripts
with support for parallel execution and advanced file comparison capabilities.
"""

__version__ = "0.3.7"
__author__ = "Xiaotong Wang"
__email__ = "xiaotongwang98@gmail.com"

# Import main classes for convenient access
from .runners.json_runner import JSONRunner
from .runners.parallel_json_runner import ParallelJSONRunner
from .runners.yaml_runner import YAMLRunner
from .core.test_case import TestCase
from .core.assertions import Assertions
from .core.setup import BaseSetup, EnvironmentSetup, SetupManager

__all__ = [
    'JSONRunner',
    'ParallelJSONRunner', 
    'YAMLRunner',
    'TestCase',
    'Assertions',
    'BaseSetup',
    'EnvironmentSetup',
    'SetupManager'
] 