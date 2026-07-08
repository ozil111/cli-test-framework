"""
Unified configuration parsing layer.

Shared logic for loading test cases from a config dict (already parsed from
JSON/YAML) into TestCase objects, and for executing sequence test cases.

Backward-compatible: the runner classes still expose ``load_test_cases()`` and
``_run_sequence()`` as before; they merely delegate to the functions here.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .test_case import TestCase, TestCaseStep
from .execution import execute_single_test_case
from ..utils.path_resolver import resolve_paths

logger = logging.getLogger("cli_test_framework.core.config_loader")

# ---------------------------------------------------------------------------
# Placeholder substitution
# ---------------------------------------------------------------------------

_PLACEHOLDER_RE = re.compile(r'\{(\w+)\}')


def substitute_placeholders(
    config: Dict[str, Any],
    variables: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """递归替换 config 中字符串值的 ``{placeholder}`` 占位符。

    只替换 ``variables`` 中存在的 key，未匹配的 ``{xxx}`` 原样保留，
    不会影响 ``expected.matches`` 等字段中的正则模式（如 ``{2}``）。
    """
    if not variables:
        return config

    def _sub(value: Any) -> Any:
        if isinstance(value, str):
            return _PLACEHOLDER_RE.sub(
                lambda m: str(variables[m.group(1)])
                if m.group(1) in variables else m.group(0),
                value,
            )
        if isinstance(value, list):
            return [_sub(item) for item in value]
        if isinstance(value, dict):
            return {k: _sub(v) for k, v in value.items()}
        return value

    return _sub(config)


# ---------------------------------------------------------------------------
# Test-case parsing (loaded dict → list[TestCase])
# ---------------------------------------------------------------------------

def _split_and_resolve(
    command_string: str,
    args: List[str],
    workspace: Path,
    path_resolver: Any,
) -> Tuple[str, List[str]]:
    """Split a command string into executable + leading args, then resolve paths.

    ``path_resolver`` must be a ``PathResolver`` instance (or duck-typed
    equivalent with ``split_command`` / ``resolve_paths`` methods).
    """
    executable, leading_args = path_resolver.split_command(command_string)
    return executable, (
        resolve_paths(leading_args, str(workspace))
        + path_resolver.resolve_paths(args)
    )


def parse_test_cases(
    config: Dict[str, Any],
    workspace: Path,
    path_resolver: Any,
) -> List[TestCase]:
    """Parse ``config['test_cases']`` into a list of ``TestCase`` objects.

    Supports both single-command mode and sequence (``steps``) mode.
    """
    cases: List[TestCase] = []

    for case in config["test_cases"]:
        if "steps" in case:
            # ── Sequence mode ──
            steps: List[TestCaseStep] = []
            for step in case["steps"]:
                step_required = ["command", "args", "expected"]
                if not all(field in step for field in step_required):
                    raise ValueError(
                        f"Step in test case '{case.get('name', 'unnamed')}' "
                        f"is missing required fields"
                    )
                executable, resolved_args = _split_and_resolve(
                    step["command"], step["args"], workspace, path_resolver
                )
                steps.append(TestCaseStep(
                    command=executable,
                    args=resolved_args,
                    expected=step["expected"],
                    timeout=step.get("timeout"),
                ))
            cases.append(TestCase(
                name=case["name"],
                steps=steps,
                description=case.get("description", ""),
                resources=case.get("resources"),
                tags=case.get("tags", []),
            ))
        else:
            # ── Single-command mode (backward-compatible) ──
            required_fields = ["name", "command", "args", "expected"]
            if not all(field in case for field in required_fields):
                raise ValueError(
                    f"Test case {case.get('name', 'unnamed')} "
                    f"is missing required fields"
                )

            executable, resolved_args = _split_and_resolve(
                case["command"], case["args"], workspace, path_resolver
            )
            cases.append(TestCase(
                name=case["name"],
                command=executable,
                args=resolved_args,
                expected=case["expected"],
                description=case.get("description", ""),
                timeout=case.get("timeout"),
                resources=case.get("resources"),
                tags=case.get("tags", []),
            ))

    return cases


# ---------------------------------------------------------------------------
# Step helper (duck-typed access for TestCaseStep / dict)
# ---------------------------------------------------------------------------

def _step_attr(step: Any, key: str, default: Any = None) -> Any:
    """Get attribute from a ``TestCaseStep`` or key from a ``dict``."""
    if isinstance(step, dict):
        return step.get(key, default)
    return getattr(step, key, default)


# ---------------------------------------------------------------------------
# Shared sequence execution (TestCaseStep list → result dict)
# ---------------------------------------------------------------------------

def execute_sequence(
    case_name: str,
    steps: List[Any],
    workspace: Optional[str] = None,
    *,
    print_prefix: str = "",
    lock: Any = None,
    executor: Any = None,
) -> Dict[str, Any]:
    """Execute a sequence test case (fail-fast).

    ``steps`` may be a list of ``TestCaseStep`` objects or plain dicts
    containing ``command`` / ``args`` / ``expected`` / (optional) ``timeout``.

    Parameters
    ----------
    case_name:
        Name of the test case (used in step-names and the result).
    steps:
        Ordered list of steps to execute.
    workspace:
        Working directory for command execution.
    print_prefix:
        Optional prefix printed before every message (e.g. ``"[Worker]"``).
    lock:
        Deprecated; retained for backward compatibility with callers that
        still pass a ``threading.Lock``.  Logging is natively thread-safe,
        so the lock is no longer used.
    executor:
        Optional override for ``execute_single_test_case``.
        Defaults to the canonical import; callers that need monkeypatch
        support (e.g. process_worker) should pass their own reference.
    """
    if executor is None:
        executor = execute_single_test_case

    combined_output = ""
    total_duration = 0.0
    all_passed = True
    last_result = None
    failed_step = None

    prefix = f"{print_prefix} " if print_prefix else ""

    for i, step in enumerate(steps):
        step_name = f"{case_name} [step {i+1}/{len(steps)}]"
        step_case: Dict[str, Any] = {
            "name": step_name,
            "command": _step_attr(step, "command"),
            "args": _step_attr(step, "args"),
            "expected": _step_attr(step, "expected"),
            "description": None,
            "timeout": _step_attr(step, "timeout"),
            "resources": None,
        }

        command_preview = (
            f"{step_case['command']} {' '.join(step_case['args'])}".strip()
        )
        logger.info("  %sExecuting step %d/%d: %s", prefix, i+1, len(steps), command_preview)

        result = executor(step_case, workspace)

        if result["output"].strip():
            logger.debug("  %sCommand output for %s:", prefix, step_name)
            for line in result["output"].splitlines():
                logger.debug("    %s", line)

        combined_output += result["output"]
        total_duration += result["duration"]
        last_result = result

        if result["status"] != "passed":
            all_passed = False
            failed_step = i + 1
            if result.get("message"):
                logger.error("  %sError at step %d: %s", prefix, i+1, result["message"])
            break

    status = "passed" if all_passed else last_result["status"]
    message = ""
    if not all_passed:
        message = (
            f"Failed at step {failed_step}/{len(steps)}: "
            f"{last_result['message']}"
        )

    command_summary = " -> ".join(
        f"{_step_attr(s, 'command')} {' '.join(_step_attr(s, 'args'))}".strip()
        for s in steps
    )

    return {
        "name": case_name,
        "status": status,
        "message": message,
        "command": command_summary,
        "output": combined_output,
        "return_code": last_result["return_code"] if last_result else None,
        "duration": total_duration,
    }
