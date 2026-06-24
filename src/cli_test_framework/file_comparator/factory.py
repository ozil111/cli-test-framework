#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
@file factory.py
@brief Factory class for creating file comparators based on file type
@author Xiaotong Wang
@date 2025
"""

import importlib
import pkgutil
import logging
from pathlib import Path

logger = logging.getLogger("cli_test_framework.file_comparator.factory")

class ComparatorFactory:
    """
    @brief Factory class for creating file comparators
    @details This class manages the creation and registration of different types of file comparators.
             It provides a centralized way to create appropriate comparators based on file type
             and automatically discovers and registers comparator classes via plugin scanning.
    """
    _comparators = {}
    _initialized = False

    @staticmethod
    def register_comparator(file_type, comparator_class):
        """
        @brief Register a new comparator class for a specific file type
        @param file_type str: Type of file the comparator handles
        @param comparator_class class: Comparator class to register
        """
        ComparatorFactory._comparators[file_type.lower()] = comparator_class

    @staticmethod
    def create_comparator(file_type, **kwargs):
        """
        @brief Create a comparator instance for the specified file type
        @param file_type str: Type of file to compare
        @param **kwargs: Additional arguments to pass to the comparator
        @return BaseComparator: An instance of the appropriate comparator class
        @details Creates and returns a comparator instance based on the file type.
                 If no specific comparator is found, falls back to TextComparator
                 for text files or BinaryComparator for other types.
        """
        if not ComparatorFactory._initialized:
            ComparatorFactory._load_comparators()

        comparator_class = ComparatorFactory._comparators.get(file_type.lower())
        if not comparator_class:
            if file_type.lower() in ['auto', 'text']:
                from .text_comparator import TextComparator
                return TextComparator(**kwargs)
            else:
                from .binary_comparator import BinaryComparator
                return BinaryComparator(**kwargs)

        return comparator_class(**kwargs)

    @staticmethod
    def _load_comparators():
        """
        @brief Load and register all available comparators
        @details Automatically discovers and registers comparator classes from the package.
                 This includes both built-in comparators and any additional comparators
                 that follow the naming convention '*_comparator.py'.
        """
        package_dir = Path(__file__).parent
        for module_info in pkgutil.iter_modules([str(package_dir)]):
            if module_info.name.endswith('_comparator') and module_info.name != 'base_comparator':
                try:
                    module = importlib.import_module(f".{module_info.name}", package=__package__)

                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if (isinstance(attr, type) and
                            attr.__module__ == module.__name__ and
                            attr_name.endswith('Comparator')):
                            type_name = attr_name.lower().replace('comparator', '')
                            ComparatorFactory.register_comparator(type_name, attr)
                except ImportError as e:
                    logger.warning("Failed to import comparator module %s: %s", module_info.name, e)

        ComparatorFactory._initialized = True

    @staticmethod
    def get_available_comparators():
        """
        @brief Get a list of all registered comparator types
        @return list: List of available comparator type names
        """
        if not ComparatorFactory._initialized:
            ComparatorFactory._load_comparators()
        return sorted(ComparatorFactory._comparators.keys())

