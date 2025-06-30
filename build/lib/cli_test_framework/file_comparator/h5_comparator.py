from .base_comparator import BaseComparator
import h5py
import numpy as np
import logging
import re

class H5Comparator(BaseComparator):
    def __init__(self, tables=None, table_regex=None, structure_only=False, show_content_diff=False, debug=False, rtol=1e-5, atol=1e-8, expand_path=True, data_filter=None, **kwargs):
        """
        Initialize H5 comparator
        :param tables: List of table names to compare. If None, compare all tables
        :param table_regex: Regular expression pattern to match table names
        :param structure_only: If True, only compare file structure without comparing content
        :param show_content_diff: If True, show detailed content differences
        :param debug: If True, enable debug mode
        :param rtol: Relative tolerance for numerical comparison
        :param atol: Absolute tolerance for numerical comparison
        :param expand_path: If True, expand group paths to compare all sub-items. Defaults to True.
        :param data_filter: String filter expression for data comparison (e.g., '>1e-6', 'abs>1e-9')
        """
        super().__init__(**kwargs)
        self.tables = tables
        self.table_regex = table_regex
        self.structure_only = structure_only
        self.show_content_diff = show_content_diff
        self.rtol = rtol
        self.atol = atol
        self.expand_path = expand_path
        self.data_filter = data_filter
        self.filter_func = self._parse_filter()
        
        # Set debug level if verbose is enabled
        if kwargs.get('verbose', False) or debug:
            self.logger.setLevel(logging.DEBUG)
            
        self.logger.debug(f"Initialized H5Comparator with structure_only={structure_only}, show_content_diff={show_content_diff}, rtol={rtol}, atol={atol}, expand_path={expand_path}, data_filter={data_filter}")
        if table_regex:
            self.logger.debug(f"Using table regex pattern: {table_regex}")

    def read_content(self, file_path, start_line=0, end_line=None, start_column=0, end_column=None):
        """Read H5 file content"""
        content = {}
        processed_paths = set()
        
        # Log whether we're in structure-only mode
        self.logger.debug(f"Reading file {file_path} in structure-only mode: {self.structure_only}")
        self.logger.debug(f"Tables parameter: {self.tables}")
        self.logger.debug(f"Table regex parameter: {self.table_regex}")
        
        with h5py.File(file_path, 'r') as f:
            # Function to collect structure information
            def collect_structure(name, obj):
                if name in processed_paths:
                    self.logger.debug(f"Path {name} already processed, skipping.")
                    return

                if isinstance(obj, h5py.Dataset):
                    content[name] = {
                        'type': 'dataset',
                        'shape': obj.shape,
                        'dtype': str(obj.dtype),
                        'attrs': dict(obj.attrs)
                    }
                    self.logger.debug(f"Collected structure for dataset: {name}")
                    processed_paths.add(name)
                elif isinstance(obj, h5py.Group) and name:  # Skip root group
                    content[name] = {
                        'type': 'group',
                        'keys': list(obj.keys()),
                        'attrs': dict(obj.attrs)
                    }
                    self.logger.debug(f"Collected structure for group: {name}")
                    processed_paths.add(name)
            
            # Function to collect structure and data
            def collect_structure_and_data(name, obj):
                if name in processed_paths:
                    self.logger.debug(f"Path {name} already processed, skipping.")
                    return

                if isinstance(obj, h5py.Dataset):
                    dataset_info = {
                        'type': 'dataset',
                        'shape': obj.shape,
                        'dtype': str(obj.dtype),
                        'attrs': dict(obj.attrs)
                    }
                    
                    # Read data with range constraints
                    try:
                        data = obj[:]
                        if isinstance(data, np.ndarray):
                            if end_line is None:
                                end_line_actual = data.shape[0]
                            else:
                                end_line_actual = min(end_line, data.shape[0])
                                
                            if len(data.shape) == 1:
                                data = data[start_line:end_line_actual]
                            elif len(data.shape) > 1:
                                if end_column is None:
                                    end_column_actual = data.shape[1]
                                else:
                                    end_column_actual = min(end_column, data.shape[1])
                                data = data[start_line:end_line_actual, start_column:end_column_actual]
                        
                        dataset_info['data'] = data
                        self.logger.debug(f"Collected data for dataset: {name}")
                    except Exception as e:
                        self.logger.error(f"Error reading data from {name}: {str(e)}")
                    
                    content[name] = dataset_info
                    processed_paths.add(name)
                    
                elif isinstance(obj, h5py.Group) and name:  # Skip root group
                    content[name] = {
                        'type': 'group',
                        'keys': list(obj.keys()),
                        'attrs': dict(obj.attrs)
                    }
                    self.logger.debug(f"Collected structure for group: {name}")
                    processed_paths.add(name)
            
            if self.tables or self.table_regex:
                # If specific tables or regex pattern is specified
                if self.table_regex:
                    # If the regex looks like a simple path (no regex metacharacters except . and /),
                    # escape it to treat it as a literal string
                    regex_str = self.table_regex
                    self.logger.debug(f"Original table_regex: {regex_str}")
                    # Check if it contains regex metacharacters other than . and /
                    import string
                    regex_metacharacters = set('[]{}()*+?^$|\\')
                    if not any(char in regex_str for char in regex_metacharacters):
                        # Escape dots and other special characters for literal matching
                        regex_str = re.escape(regex_str)
                        self.logger.debug(f"Treating table_regex as literal path, escaped: {regex_str}")
                    else:
                        self.logger.debug(f"Using table_regex as regular expression: {regex_str}")
                    regex_pattern = re.compile(regex_str)
                else:
                    regex_pattern = None
                
                def should_process(name):
                    if self.tables and name in self.tables:
                        self.logger.debug(f"Matched by tables list: {name}")
                        return True
                    if regex_pattern and regex_pattern.fullmatch(name):
                        self.logger.debug(f"Matched by regex: {name}")
                        return True
                    return False
                
                def process_item(name, item):
                    try:
                        # Process the current item first
                        if self.structure_only:
                            collect_structure(name, item)
                        else:
                            collect_structure_and_data(name, item)

                        # If it's a group and expand_path is enabled, visit all its members
                        if self.expand_path and isinstance(item, h5py.Group):
                            self.logger.debug(f"Expanding group path: {name}")
                            
                            def visitor(sub_name, sub_obj):
                                full_path = f"{name}/{sub_name}"
                                self.logger.debug(f"Processing sub-item from expansion: {full_path}")
                                if self.structure_only:
                                    collect_structure(full_path, sub_obj)
                                else:
                                    collect_structure_and_data(full_path, sub_obj)
                            
                            item.visititems(visitor)

                    except Exception as e:
                        self.logger.error(f"Error processing {name}: {str(e)}")
                
                # First try direct path access for table names
                if self.tables:
                    for table_path in self.tables:
                        try:
                            if table_path in f:
                                process_item(table_path, f[table_path])
                            else:
                                self.logger.warning(f"Table {table_path} not found in {file_path}")
                        except Exception as e:
                            self.logger.error(f"Error processing {table_path}: {str(e)}")
                
                # Then process regex pattern if specified
                if regex_pattern:
                    def visit_with_regex(name, obj):
                        self.logger.debug(f"Checking path: {name}")
                        if should_process(name):
                            self.logger.debug(f"Processing matched path: {name}")
                            process_item(name, obj)
                        else:
                            self.logger.debug(f"Skipping path: {name}")
                    f.visititems(visit_with_regex)
            else:
                # If no tables specified, read all datasets
                if self.structure_only:
                    f.visititems(collect_structure)
                else:
                    f.visititems(collect_structure_and_data)
        
        self.logger.debug(f"Read {len(content)} items from {file_path}")
        self.logger.debug(f"Items read: {list(content.keys())}")
        return content

    def compare_content(self, content1, content2):
        """Compare two H5 file contents"""
        identical = True
        differences = []

        # Get all unique table names
        all_tables = set(content1.keys()) | set(content2.keys())
        
        # Debug log
        self.logger.debug(f"Structure-only mode: {self.structure_only}")
        self.logger.debug(f"Number of tables to compare: {len(all_tables)}")
        
        for table_name in all_tables:
            # Debug log
            self.logger.debug(f"Comparing table: {table_name}")
            if table_name in content1 and table_name in content2:
                self.logger.debug(f"Table1 keys: {content1[table_name].keys()}")
                self.logger.debug(f"Table2 keys: {content2[table_name].keys()}")
            
            # Check if table exists in both files
            if table_name not in content1:
                differences.append(self._create_difference(
                    position=table_name,
                    expected="Table exists",
                    actual="Table missing",
                    diff_type="structure"
                ))
                identical = False
                continue
                
            if table_name not in content2:
                differences.append(self._create_difference(
                    position=table_name,
                    expected="Table exists",
                    actual="Table missing",
                    diff_type="structure"
                ))
                identical = False
                continue
            
            table1 = content1[table_name]
            table2 = content2[table_name]
            
            # Compare table type
            if table1.get('type') != table2.get('type'):
                differences.append(self._create_difference(
                    position=f"{table_name}/type",
                    expected=table1.get('type'),
                    actual=table2.get('type'),
                    diff_type="structure"
                ))
                identical = False
                continue
            
            # For datasets, compare shape and dtype
            if table1.get('type') == 'dataset':
                if table1['shape'] != table2['shape']:
                    differences.append(self._create_difference(
                        position=f"{table_name}/shape",
                        expected=str(table1['shape']),
                        actual=str(table2['shape']),
                        diff_type="structure"
                    ))
                    identical = False
                
                if table1['dtype'] != table2['dtype']:
                    differences.append(self._create_difference(
                        position=f"{table_name}/dtype",
                        expected=str(table1['dtype']),
                        actual=str(table2['dtype']),
                        diff_type="structure"
                    ))
                    identical = False
            
            # For groups, compare keys
            elif table1.get('type') == 'group':
                keys1 = set(table1['keys'])
                keys2 = set(table2['keys'])
                if keys1 != keys2:
                    missing_keys = keys1 - keys2
                    extra_keys = keys2 - keys1
                    if missing_keys:
                        differences.append(self._create_difference(
                            position=f"{table_name}/keys",
                            expected=str(sorted(missing_keys)),
                            actual="Keys missing",
                            diff_type="structure"
                        ))
                    if extra_keys:
                        differences.append(self._create_difference(
                            position=f"{table_name}/keys",
                            expected="No extra keys",
                            actual=str(sorted(extra_keys)),
                            diff_type="structure"
                        ))
                    identical = False
            
            # Only compare attributes and data if not in structure-only mode
            if not self.structure_only:
                self.logger.debug(f"Comparing attributes and data for {table_name}")
                
                # Compare attributes
                attr_diff = self._compare_attributes(table1['attrs'], table2['attrs'], table_name)
                if attr_diff:
                    differences.extend(attr_diff)
                    identical = False
                
                # Compare data content
                if 'data' in table1 and 'data' in table2:
                    data1 = table1['data']
                    data2 = table2['data']
                    
                    if isinstance(data1, np.ndarray) and isinstance(data2, np.ndarray):
                        try:
                            # 应用过滤器
                            mask1 = self.filter_func(data1) if self.filter_func else np.ones_like(data1, dtype=bool)
                            mask2 = self.filter_func(data2) if self.filter_func else np.ones_like(data2, dtype=bool)
                            
                            # 我们只关心两个文件中都满足条件的位置
                            combined_mask = mask1 & mask2
                            
                            # 过滤后的数据
                            filtered_data1 = data1[combined_mask]
                            filtered_data2 = data2[combined_mask]
                            
                            if self.filter_func:
                                self.logger.debug(f"Applied filter to {table_name}: {np.sum(combined_mask)}/{data1.size} elements meet criteria")
                            
                            # 对于数值类型数据使用 isclose
                            if np.issubdtype(data1.dtype, np.number) and np.issubdtype(data2.dtype, np.number):
                                if not np.all(np.isclose(filtered_data1, filtered_data2, equal_nan=True, rtol=self.rtol, atol=self.atol)):
                                    if self.show_content_diff:
                                        # 如果过滤后数据不相等，需要找到原始数据的索引来报告差异
                                        # 简化处理：直接报告内容不同
                                        differences.append(self._create_difference(
                                            position=table_name,
                                            expected="Same content (after filtering)",
                                            actual="Content differs (after filtering)",
                                            diff_type="content"
                                        ))
                                    else:
                                        # Just report that content differs
                                        differences.append(self._create_difference(
                                            position=table_name,
                                            expected="Same content (after filtering)",
                                            actual="Content differs (after filtering)",
                                            diff_type="content"
                                        ))
                                    identical = False
                            # 对于字符串或其他类型直接比较
                            else:
                                if not np.array_equal(filtered_data1, filtered_data2):
                                    if self.show_content_diff:
                                        # For non-numeric arrays, find the first difference
                                        diff_indices = np.where(filtered_data1 != filtered_data2)
                                        for idx in zip(*diff_indices)[:10]:
                                            position = f"{table_name}[{','.join(map(str, idx))}]"
                                            differences.append(self._create_difference(
                                                position=position,
                                                expected=str(filtered_data1[idx]),
                                                actual=str(filtered_data2[idx]),
                                                diff_type="content"
                                            ))
                                    else:
                                        differences.append(self._create_difference(
                                            position=table_name,
                                            expected="Same content (after filtering)",
                                            actual="Content differs (after filtering)",
                                            diff_type="content"
                                        ))
                                    identical = False
                        except Exception as e:
                            self.logger.error(f"Error comparing data in table {table_name}: {str(e)}")
                            differences.append(self._create_difference(
                                position=table_name,
                                expected=f"Data type: {table1.get('dtype', 'unknown')}",
                                actual=f"Data type: {table2.get('dtype', 'unknown')}",
                                diff_type="error"
                            ))
                            identical = False
        
        return identical, differences

    def _compare_attributes(self, attrs1, attrs2, table_name):
        """Compare HDF5 attributes"""
        differences = []
        
        # Compare attribute keys
        keys1 = set(attrs1.keys())
        keys2 = set(attrs2.keys())
        
        # Check for missing attributes
        for key in keys1 - keys2:
            differences.append(self._create_difference(
                position=f"{table_name}/attrs/{key}",
                expected=str(attrs1[key]),
                actual="Attribute missing",
                diff_type="missing_attribute"
            ))
            
        for key in keys2 - keys1:
            differences.append(self._create_difference(
                position=f"{table_name}/attrs/{key}",
                expected="Attribute missing",
                actual=str(attrs2[key]),
                diff_type="extra_attribute"
            ))
            
        # Compare common attributes
        for key in keys1 & keys2:
            val1 = attrs1[key]
            val2 = attrs2[key]
            
            # Handle numpy arrays in attributes
            if isinstance(val1, np.ndarray) and isinstance(val2, np.ndarray):
                try:
                    if not np.array_equal(val1, val2):
                        differences.append(self._create_difference(
                            position=f"{table_name}/attrs/{key}",
                            expected=str(val1),
                            actual=str(val2),
                            diff_type="attribute"
                        ))
                except Exception as e:
                    self.logger.error(f"Error comparing array attribute {key}: {str(e)}")
                    differences.append(self._create_difference(
                        position=f"{table_name}/attrs/{key}",
                        expected=str(val1),
                        actual=str(val2),
                        diff_type="attribute"
                    ))
            elif isinstance(val1, np.ndarray) or isinstance(val2, np.ndarray):
                # One is array, one is not - they're different
                differences.append(self._create_difference(
                    position=f"{table_name}/attrs/{key}",
                    expected=str(val1),
                    actual=str(val2),
                    diff_type="attribute"
                ))
            else:
                # Regular comparison for non-array values
                if val1 != val2:
                    differences.append(self._create_difference(
                        position=f"{table_name}/attrs/{key}",
                        expected=str(val1),
                        actual=str(val2),
                        diff_type="attribute"
                    ))
                
        return differences

    def _create_difference(self, position, expected, actual, diff_type):
        """Create a Difference object"""
        from .result import Difference
        return Difference(position=position, expected=expected, actual=actual, diff_type=diff_type)

    def _parse_filter(self):
        """Parse data filter string and return a filter function"""
        if not self.data_filter:
            return None

        self.logger.debug(f"Parsing data filter: {self.data_filter}")
        try:
            # 匹配模式，例如 'abs>0.1', '>=1e-5', '<-10'
            match = re.match(r"^(abs)?([><]=?|==)([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)$", self.data_filter.replace(" ", ""))
            if not match:
                self.logger.warning(f"Invalid data filter format: {self.data_filter}. Ignoring filter.")
                return None

            use_abs, op, value_str = match.groups()
            value = float(value_str)

            op_map = {
                '>': np.greater,
                '>=': np.greater_equal,
                '<': np.less,
                '<=': np.less_equal,
                '==': np.equal
            }

            def filter_func(data):
                if not isinstance(data, np.ndarray) or not np.issubdtype(data.dtype, np.number):
                    return np.ones_like(data, dtype=bool)  # 对于非数字类型，不过滤
                
                target_data = np.abs(data) if use_abs else data
                return op_map[op](target_data, value)

            self.logger.debug(f"Created filter function for pattern: {use_abs or ''}{op}{value}")
            return filter_func
        except Exception as e:
            self.logger.error(f"Failed to parse data filter '{self.data_filter}': {e}. Ignoring filter.")
            return None

# Register the new comparator
from .factory import ComparatorFactory
ComparatorFactory.register_comparator('h5', H5Comparator)