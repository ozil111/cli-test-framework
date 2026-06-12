"""
CLI Test Framework - A powerful command-line testing framework

This package provides tools for testing command-line applications and scripts
with support for parallel execution and advanced file comparison capabilities.

Logging
-------
All diagnostic and status messages go through Python's standard ``logging``
module under the ``cli_test_framework`` namespace.  A ``StreamHandler`` is
installed automatically at ``INFO`` level on first import.  Library users can
suppress output entirely::

    import logging
    logging.getLogger("cli_test_framework").setLevel(logging.WARNING)
    # or remove the handler:
    logging.getLogger("cli_test_framework").handlers.clear()
"""

__version__ = "0.7.0"
__author__ = "Xiaotong Wang"
__email__ = "xiaotongwang98@gmail.com"

# Import main classes for convenient access
from .runners.json_runner import JSONRunner
from .runners.parallel_json_runner import ParallelJSONRunner
from .runners.yaml_runner import YAMLRunner
from .core.test_case import TestCase
from .core.assertions import Assertions
from .core.setup import BaseSetup, EnvironmentSetup, SetupManager
from .logging_config import get_logger

__all__ = [
    'JSONRunner',
    'ParallelJSONRunner', 
    'YAMLRunner',
    'TestCase',
    'Assertions',
    'BaseSetup',
    'EnvironmentSetup',
    'SetupManager',
    'get_logger',
] 