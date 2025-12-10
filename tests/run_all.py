#!/usr/bin/env python3
"""
Unified test entrypoint for the project.

Usage:
  python -m tests.run_all --scope unit|integration|e2e|all [--extra "-k filter"]
"""

import argparse
import subprocess
import sys
from pathlib import Path


DEFAULT_SCOPES = {
    "unit": ["tests/unit"],
    "integration": ["tests/integration"],
    "e2e": ["tests/e2e"],
}


def main():
    parser = argparse.ArgumentParser(description="Run project tests via pytest")
    parser.add_argument(
        "--scope",
        choices=["unit", "integration", "e2e", "all"],
        default="all",
        help="Test scope to run",
    )
    parser.add_argument(
        "--extra",
        default="",
        help="Additional arguments passed to pytest (e.g. \"-k h5\")",
    )
    args = parser.parse_args()

    targets = []
    if args.scope == "all":
        for paths in DEFAULT_SCOPES.values():
            targets.extend(paths)
    else:
        targets.extend(DEFAULT_SCOPES.get(args.scope, []))

    # Keep only existing paths to avoid pytest "file not found" errors
    targets = [t for t in targets if (Path(__file__).resolve().parent.parent / t).exists()]

    if not targets:
        print("No targets configured for selected scope.")
        return 1

    pytest_args = ["pytest", *targets]
    if args.extra:
        pytest_args.extend(args.extra.split())

    print(f"Running: {' '.join(pytest_args)}")
    result = subprocess.run(pytest_args, cwd=Path(__file__).resolve().parent.parent)
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())

