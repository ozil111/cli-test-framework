#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
@file factory.py
@brief Factory class for creating file comparators based on file type
@author Xiaotong Wang
@date 2025
"""

import os
import importlib
import pkgutil
from pathlib import Path

class ComparatorFactory:
    """
    @brief Factory class for creating file comparators
    @details This class manages the creation and registration of different types of file comparators.
             It provides a centralized way to create appropriate comparators based on file type
             and handles parameter filtering for different comparator types.
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
                # Only pass TextComparator supported parameters
                text_kwargs = {k: v for k, v in kwargs.items() 
                              if k in ['encoding', 'chunk_size', 'verbose']}
                return TextComparator(**text_kwargs)
            else:
                from .binary_comparator import BinaryComparator
                # Pass all BinaryComparator supported parameters
                binary_kwargs = {k: v for k, v in kwargs.items()
                               if k in ['chunk_size', 'verbose', 'similarity', 'num_threads']}
                return BinaryComparator(**binary_kwargs)

        # Filter parameters based on comparator type
        if file_type.lower() == 'h5':
            # H5 comparator accepts specific parameters
            h5_kwargs = {k: v for k, v in kwargs.items()
                        if k in ['tables', 'table_regex', 'encoding', 'chunk_size', 'verbose', 'structure_only', 'show_content_diff', 'debug', 'rtol', 'atol']}
            return comparator_class(**h5_kwargs)
        elif file_type.lower() == 'binary':
            # Binary comparator accepts all parameters, including num_threads
            binary_kwargs = {k: v for k, v in kwargs.items()
                           if k in ['chunk_size', 'verbose', 'similarity', 'num_threads']}
            return comparator_class(**binary_kwargs)
        elif file_type.lower() == 'json':
            # JSON comparator accepts specific parameters
            json_kwargs = {k: v for k, v in kwargs.items()
                         if k in ['encoding', 'chunk_size', 'verbose', 'compare_mode', 'key_field']}
            return comparator_class(**json_kwargs)
        else:
            # Other comparators only accept basic parameters
            basic_kwargs = {k: v for k, v in kwargs.items()
                          if k in ['encoding', 'chunk_size', 'verbose']}
            return comparator_class(**basic_kwargs)

    @staticmethod
    def _load_comparators():
        """
        @brief Load and register all available comparators
        @details Automatically discovers and registers comparator classes from the package.
                 This includes both built-in comparators and any additional comparators
                 that follow the naming convention '*_comparator.py'.
        """
        from .text_comparator import TextComparator
        from .binary_comparator import BinaryComparator

        ComparatorFactory.register_comparator('text', TextComparator)
        ComparatorFactory.register_comparator('binary', BinaryComparator)

        package_dir = Path(__file__).parent
        for module_info in pkgutil.iter_modules([str(package_dir)]):
            if module_info.name.endswith('_comparator') and module_info.name not in [
                'base_comparator', 'text_comparator', 'binary_comparator'
            ]:
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
                    print(f"Failed to import comparator module {module_info.name}: {e}")

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

# Register built-in comparators
from .json_comparator import JsonComparator
from .xml_comparator import XmlComparator
from .csv_comparator import CsvComparator
from .text_comparator import TextComparator
from .binary_comparator import BinaryComparator

ComparatorFactory.register_comparator('json', JsonComparator)
ComparatorFactory.register_comparator('xml', XmlComparator)
ComparatorFactory.register_comparator('csv', CsvComparator)
ComparatorFactory.register_comparator('text', TextComparator)
ComparatorFactory.register_comparator('binary', BinaryComparator)