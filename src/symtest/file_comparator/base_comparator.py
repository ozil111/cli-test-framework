#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
@file base_comparator.py
@brief Root comparator contract: ``compare(ctx) -> ComparisonResult``
@author Xiaotong Wang
@date 2025

Plugin contract v2 (three lanes, breaking change vs. the legacy two-file
``BaseComparator``):

- :class:`~symtest.file_comparator.file_comparator_base.FileComparator`
  — **file lane**: two-file comparison; implements ``read_content`` /
  ``compare_content`` (text/json/csv/xml/h5/binary).
- :class:`~symtest.file_comparator.extractor_comparator.ExtractorComparator`
  — **data lane**: plugin extracts ``{channel: (expected, actual)}`` data;
  verdict is owned by the framework via per-channel numeric tolerance.
- direct subclasses — **autonomous lane**: the plugin owns the verdict and
  returns a fully populated ``ComparisonResult`` (``script`` comparator,
  analysis-style plugins such as ``hourglass_tangent``).

All lanes share the same invocation convention: the framework builds a
:class:`CompareContext` and calls :meth:`ComparatorBase.compare`.  Path-like
constructor parameters listed in ``path_params`` are resolved relative to the
workspace by the framework before ``compare`` is invoked — plugins must not
resolve paths against ``os.getcwd()`` themselves.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import logging
from typing import Any, Dict, Optional

from .result import ComparisonResult


@dataclass
class CompareContext:
    """
    @brief Invocation context handed to every comparator's ``compare()``.
    @param workspace str|None: Workspace root; framework already resolved
           ``actual``/``baseline`` and ``path_params``-declared parameters
           against it before ``compare()`` was called.
    @param actual str|None: Path produced by the test command (optional for
           autonomous-lane plugins).
    @param baseline str|None: Golden/reference path (optional).
    @param params dict: Full compareSpec passthrough (everything except
           ``actual``/``baseline``/``type``).  File-lane comparators consume
           ``start_line``/``end_line``/``start_column``/``end_column`` from
           here; all remaining keys were forwarded to the constructor.
    @param error_analysis bool: Whether streaming error statistics were
           requested (``--error-analysis``).
    """
    workspace: Optional[str] = None
    actual: Optional[str] = None
    baseline: Optional[str] = None
    params: Dict[str, Any] = field(default_factory=dict)
    error_analysis: bool = False


class ComparatorBase(ABC):
    """
    @brief Root abstract class for all comparators.
    @details The only contract is :meth:`compare`.  Subclasses declare
             ``path_params`` so the framework can resolve workspace-relative
             path arguments uniformly; plugins never resolve paths themselves.
    """

    #: Constructor parameter names that hold filesystem paths.  The framework
    #: resolves each of them relative to the workspace (when not absolute)
    #: before invoking :meth:`compare`.  ``actual``/``baseline`` are always
    #: resolved and need not be listed here.
    path_params: tuple = ()

    def __init__(self, encoding: str = "utf-8", verbose: bool = False, **kwargs):
        """
        @brief Initialize the base comparator
        @param encoding str: Default file encoding (default: "utf-8")
        @param verbose bool: Enable verbose logging (default: False)
        @param **kwargs: Accepted and ignored for forward compatibility
        """
        self.encoding = encoding
        self.logger = logging.getLogger(f"file_comparator.{self.__class__.__name__}")
        if verbose:
            self.logger.setLevel(logging.DEBUG)

    @abstractmethod
    def compare(self, ctx: CompareContext) -> ComparisonResult:
        """
        @brief Run the comparison and return a fully populated result.
        @param ctx CompareContext: Invocation context (paths already resolved).
        @return ComparisonResult: Result with ``identical``/``differences`` and
                optionally ``error``/``error_stats``/``channels``/
                ``command_output`` populated.
        """


# Historical import-path alias: plugins written against the old API used
# ``from symtest.file_comparator.base_comparator import BaseComparator``.
# The name now refers to the same root contract; the *interface* change
# (read_content/compare_content → compare) is the intentional breaking part.
BaseComparator = ComparatorBase
