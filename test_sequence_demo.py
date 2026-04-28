"""Quick demo to verify sequence feature works."""
import json
import tempfile
import os
from cli_test_framework.runners.json_runner import JSONRunner

config = {
    "test_cases": [
        {
            "name": "sequence_all_pass",
            "steps": [
                {"command": "echo", "args": ["step1"], "expected": {"return_code": 0, "output_contains": ["step1"]}},
                {"command": "echo", "args": ["step2"], "expected": {"return_code": 0, "output_contains": ["step2"]}},
            ]
        },
        {
            "name": "sequence_fail_at_step2",
            "steps": [
                {"command": "echo", "args": ["ok"], "expected": {"return_code": 0}},
                # Use python to produce non-zero exit code, with raw: prefix to avoid path resolution
                {"command": "python", "args": ["raw:-c", "raw:import sys; sys.exit(1)"], "expected": {"return_code": 0}},
                {"command": "echo", "args": ["should_not_run"], "expected": {"return_code": 0}},
            ]
        },
        {
            "name": "sequence_step_timeout",
            "steps": [
                # ping with -n flag gets resolved; use python sleep instead with raw: prefix
                {"command": "python", "args": ["raw:-c", "raw:import time; time.sleep(10)"], "expected": {"return_code": 0}, "timeout": 1},
                {"command": "echo", "args": ["after_timeout"], "expected": {"return_code": 0}},
            ]
        },
        {
            "name": "single_command_backward_compat",
            "command": "echo",
            "args": ["hello"],
            "expected": {"return_code": 0, "output_contains": ["hello"]}
        },
    ]
}

with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
    json.dump(config, f, ensure_ascii=False)
    tmp_path = f.name

try:
    runner = JSONRunner(os.path.basename(tmp_path), os.path.dirname(tmp_path))
    all_passed = runner.run_tests()
    print()
    print("=== Summary ===")
    for d in runner.results["details"]:
        cmd_short = d["command"][:80]
        msg_short = d.get("message", "")[:80]
        print("  {}: {} | cmd: {} | msg: {}".format(d["name"], d["status"], cmd_short, msg_short))
    print("All passed: {}".format(all_passed))

    # Verify expectations
    details = runner.results["details"]
    assert details[0]["status"] == "passed", "sequence_all_pass should pass"
    assert details[1]["status"] == "failed", "sequence_fail_at_step2 should fail"
    assert "step 2" in details[1]["message"], "should fail at step 2"
    assert details[2]["status"] == "failed", "sequence_step_timeout should fail"
    assert "step 1" in details[2]["message"], "should fail at step 1"
    assert details[3]["status"] == "passed", "single_command_backward_compat should pass"
    print("\nAll assertions passed!")
finally:
    os.unlink(tmp_path)
