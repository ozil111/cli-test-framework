"""Tests for cli_test_framework.core.execution.

Covers the ``errors="replace"`` behaviour: when a subprocess emits bytes that
cannot be decoded by the platform's default encoding, execution must not crash
with ``UnicodeDecodeError``; the offending bytes are replaced and the legal
portions of the output are preserved.
"""
import sys

from cli_test_framework.core.execution import execute_single_test_case


def _run(command: str, args, expected=None, workspace=None):
    case = {
        "name": "undecodable-output",
        "command": command,
        "args": list(args),
        "expected": expected or {"return_code": 0},
    }
    return execute_single_test_case(case, workspace=workspace)


def test_undecodable_output_bytes_do_not_crash(tmp_path):
    """Subprocess output containing bytes illegal under the default encoding
    must not raise UnicodeDecodeError; execution should still succeed and the
    decodable parts of the output must be preserved.

    ``0x80`` is illegal under both UTF-8 and GBK/cp936 (the two encodings most
    commonly implicated in the original crash), so this test is meaningful on
    both Linux CI and Chinese-Windows environments. Note: bytes like ``0x88``
    are *not* suitable because under GBK they act as a valid lead byte and
    consume the following byte, corrupting the suffix.
    """
    # Write raw bytes: ASCII prefix, an illegal byte, ASCII suffix.
    script = (
        "import sys; "
        "sys.stdout.buffer.write(b'ok-before\\x80ok-after'); "
        "sys.stdout.buffer.flush()"
    )
    result = _run(sys.executable, ["-c", script], workspace=str(tmp_path))

    assert result["status"] == "passed"
    assert result["return_code"] == 0
    # No execution error leaked into the message.
    assert "UnicodeDecodeError" not in result["message"]
    # The decodable portions survive.
    assert "ok-before" in result["output"]
    assert "ok-after" in result["output"]


def test_undecodable_bytes_still_allow_output_contains_assertion(tmp_path):
    """Even with garbage bytes mixed in, a valid ``output_contains`` assertion
    against the decodable part should pass — proving the output stream is usable
    for validation after the fix.
    """
    script = (
        "import sys; "
        "sys.stdout.buffer.write(b'DONE\\xff\\xfe'); "
        "sys.stdout.buffer.flush()"
    )
    result = _run(
        sys.executable,
        ["-c", script],
        expected={"return_code": 0, "output_contains": ["DONE"]},
        workspace=str(tmp_path),
    )

    assert result["status"] == "passed"
    assert "DONE" in result["output"]
    assert "UnicodeDecodeError" not in result["message"]
