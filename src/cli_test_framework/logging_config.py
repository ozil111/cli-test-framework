"""
Central logging configuration for the CLI test framework.

Provides a unified ``get_logger(name)`` helper that returns a logger
configured with a consistent format.  By default a ``StreamHandler``
is attached so that messages are visible when the framework is used
as a CLI tool.  Library users can suppress output entirely by setting
the level on the root or package logger::

    import logging
    logging.getLogger("cli_test_framework").setLevel(logging.WARNING)
    # or disable entirely:
    logging.getLogger("cli_test_framework").propagate = False

Replaces the previous ad-hoc ``print()`` / ``_print_lock`` pattern.
The ``logging`` module is already thread-safe, so the manual locking
is no longer needed.
"""

from __future__ import annotations

import logging
import sys

DEFAULT_FORMAT = "%(levelname)-7s %(name)-35s %(message)s"

# ── package-level logger (used as parent for all child loggers) ──────────────
_logger = logging.getLogger("cli_test_framework")
_logger.setLevel(logging.DEBUG)          # let handlers decide; do not block

# ── default console handler (attached once) ──────────────────────────────────
if not _logger.handlers:
    _handler = logging.StreamHandler(sys.stdout)
    _handler.setLevel(logging.INFO)
    _handler.setFormatter(logging.Formatter(DEFAULT_FORMAT))
    _logger.addHandler(_handler)


def get_logger(name: str) -> logging.Logger:
    """Return a child logger under the ``cli_test_framework`` namespace.

    Usage::

        from cli_test_framework.logging_config import get_logger
        logger = get_logger(__name__)
        logger.info("Hello")
    """
    # Ensure the logger is a child of cli_test_framework so it inherits
    # the handler (unless the user removes / replaces it).
    if not name.startswith("cli_test_framework"):
        name = "cli_test_framework." + name
    return logging.getLogger(name)
