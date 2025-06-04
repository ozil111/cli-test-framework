#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
@file binary_comparator.py
@brief Binary file comparator implementation with efficient byte-level comparison
@author Xiaotong Wang
@date 2025
"""

import hashlib
from .base_comparator import BaseComparator
from .result import Difference
from concurrent.futures import ThreadPoolExecutor

class BinaryComparator(BaseComparator):
    """
    @brief Comparator for binary files with efficient byte-level comparison
    @details This class implements binary file comparison with support for:
             - Byte-level difference detection
             - Similarity index calculation using LCS
             - Parallel processing for large files
             - File hash calculation
    """
    
    def __init__(self, encoding="utf-8", chunk_size=8192, verbose=False, similarity=False, num_threads=4):
        """
        @brief Initialize the binary comparator
        @param encoding str: File encoding (not used for binary files)
        @param chunk_size int: Size of chunks for reading large files
        @param verbose bool: Enable verbose logging
        @param similarity bool: Enable similarity index calculation
        @param num_threads int: Number of threads for parallel processing
        """
        super().__init__(encoding, chunk_size, verbose)
        self.similarity = similarity
        self.num_threads = num_threads

    def read_content(self, file_path, start_line=0, end_line=None, start_column=0, end_column=None):
        """
        @brief Read binary content with specified range
        @param file_path Path: Path to the binary file to read
        @param start_line int: Starting byte offset (interpreted as bytes for binary files)
        @param end_line int: Ending byte offset (interpreted as bytes for binary files)
        @param start_column int: Ignored for binary files
        @param end_column int: Ignored for binary files
        @return bytes: Binary content within the specified range
        @throws ValueError: If byte offsets are invalid
        @throws FileNotFoundError: If file doesn't exist
        @throws IOError: If there are other file reading errors
        """
        try:
            self.logger.debug(f"Reading binary file: {file_path}")
            
            # For binary files, interpret start_line as byte offset
            start_offset = start_line
            end_offset = end_line
            
            with open(file_path, 'rb') as f:
                if start_offset > 0:
                    f.seek(start_offset)
                
                if end_offset is not None:
                    if end_offset <= start_offset:
                        raise ValueError("End offset must be greater than start offset")
                    bytes_to_read = end_offset - start_offset
                    content = f.read(bytes_to_read)
                else:
                    content = f.read()
                    
            return content
                
        except FileNotFoundError:
            raise ValueError(f"File not found: {file_path}")
        except IOError as e:
            raise ValueError(f"Error reading file {file_path}: {str(e)}")
    
    def compare_content(self, content1, content2):
        """
        @brief Compare binary content efficiently
        @param content1 bytes: First binary content to compare
        @param content2 bytes: Second binary content to compare
        @return tuple: (bool, list) - (identical, differences)
        @details Performs efficient byte-level comparison of binary content.
                 Reports differences with hex context and limits the number
                 of differences to avoid overwhelming output.
        """
        self.logger.debug(f"Comparing binary content")
        
        if len(content1) != len(content2):
            differences = [Difference(
                position="file size",
                expected=f"{len(content1)} bytes",
                actual=f"{len(content2)} bytes",
                diff_type="size"
            )]
            identical = False
        elif content1 == content2:
            differences = []
            identical = True
        else:
            identical = False
            differences = []
            offset = 0
            max_differences = 10  # Limit number of differences reported
        
            for i in range(0, len(content1), self.chunk_size):
                chunk1 = content1[i:i+self.chunk_size]
                chunk2 = content2[i:i+self.chunk_size]
                
                if chunk1 != chunk2:
                    # Find the exact byte position where the difference starts
                    for j in range(len(chunk1)):
                        if j >= len(chunk2) or chunk1[j] != chunk2[j]:
                            diff_pos = i + j
                            # Show a few bytes before and after the difference for context
                            context_size = 8
                            start_ctx = max(0, diff_pos - context_size)
                            end_ctx = min(len(content1), diff_pos + context_size)
                            
                            # Create hex representations of the differing sections
                            expected_bytes = content1[start_ctx:end_ctx]
                            actual_bytes = content2[start_ctx:min(len(content2), end_ctx)]
                            
                            expected_hex = ' '.join(f"{b:02x}" for b in expected_bytes)
                            actual_hex = ' '.join(f"{b:02x}" for b in actual_bytes)
                            
                            differences.append(Difference(
                                position=f"byte {diff_pos}",
                                expected=expected_hex,
                                actual=actual_hex,
                                diff_type="content"
                            ))
                            break
                            
                    if len(differences) >= max_differences:
                        differences.append(Difference(
                            position=None,
                            expected=None,
                            actual=None,
                            diff_type=f"more differences not shown"
                        ))
                        break
        
        return identical, differences

    def compute_lcs_length(self, a: bytes, b: bytes) -> int:
        """
        @brief Compute the length of the longest common subsequence
        @param a bytes: First binary sequence
        @param b bytes: Second binary sequence
        @return int: Length of the longest common subsequence
        @details Uses dynamic programming to compute LCS accurately.
        """
        if not a or not b:
            return 0

        # Initialize a 2D array for dynamic programming
        dp = [[0] * (len(b) + 1) for _ in range(len(a) + 1)]

        # Fill the DP table
        for i in range(1, len(a) + 1):
            for j in range(1, len(b) + 1):
                if a[i - 1] == b[j - 1]:
                    dp[i][j] = dp[i - 1][j - 1] + 1
                else:
                    dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])

        # The bottom-right cell contains the LCS length
        return dp[len(a)][len(b)]

    def compare_files(self, file1, file2, start_line=0, end_line=None, start_column=0, end_column=None):
        """
        @brief Compare two binary files with optional similarity calculation
        @param file1 Path: Path to the first binary file
        @param file2 Path: Path to the second binary file
        @param start_line int: Starting byte offset
        @param end_line int: Ending byte offset
        @param start_column int: Ignored for binary files
        @param end_column int: Ignored for binary files
        @return ComparisonResult: Result object containing comparison details
        """
        from pathlib import Path
        from .result import ComparisonResult
        result = ComparisonResult(
            file1=str(file1),
            file2=str(file2),
            start_line=start_line,
            end_line=end_line,
            start_column=start_column,
            end_column=end_column
        )
        try:
            self.logger.info(f"Comparing files: {file1} and {file2}")
            file1_path = Path(file1)
            file2_path = Path(file2)
            result.file1_size = file1_path.stat().st_size
            result.file2_size = file2_path.stat().st_size
            self.logger.debug("Reading content from files")
            content1 = self.read_content(file1, start_line, end_line, start_column, end_column)
            content2 = self.read_content(file2, start_line, end_line, start_column, end_column)
            self.logger.debug("Comparing content")
            identical, differences = self.compare_content(content1, content2)
            result.identical = identical
            result.differences = differences
            if self.similarity:
                if (len(content1) + len(content2)) > 0:
                    lcs_len = self.compute_lcs_length(content1, content2)
                    similarity = 2 * lcs_len / (len(content1) + len(content2))
                else:
                    similarity = 1
                result.similarity = similarity
            return result
        except Exception as e:
            self.logger.error(f"Error during comparison: {str(e)}")
            result.error = str(e)
            result.identical = False
            return result

    def get_file_hash(self, file_path, chunk_size=8192):
        """
        @brief Calculate SHA-256 hash of a file efficiently
        @param file_path Path: Path to the file to hash
        @param chunk_size int: Size of chunks for reading large files
        @return str: Hexadecimal representation of the file's SHA-256 hash
        """
        h = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(chunk_size), b''):
                h.update(chunk)
        return h.hexdigest()