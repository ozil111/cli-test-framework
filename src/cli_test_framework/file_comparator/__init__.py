"""
File comparison module for cli-test-framework.
This module provides functionality for comparing different types of files.
"""

from .factory import ComparatorFactory
from .result import ComparisonResult

__all__ = ['ComparatorFactory', 'ComparisonResult'] 