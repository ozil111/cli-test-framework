"""Unit tests for cli_test_framework.core.config_loader — substitute_placeholders."""

import pytest

from cli_test_framework.core.config_loader import substitute_placeholders


# ---------------------------------------------------------------------------
# Basic substitution
# ---------------------------------------------------------------------------

class TestSubstitutePlaceholders:
    """Tests for the substitute_placeholders utility."""

    def test_no_variables_returns_unchanged(self):
        config = {"command": "{solver}", "args": ["--input", "{model}"]}
        result = substitute_placeholders(config, None)
        assert result == config

    def test_empty_variables_returns_unchanged(self):
        config = {"command": "{solver}", "args": ["--input", "{model}"]}
        result = substitute_placeholders(config, {})
        assert result == config

    def test_simple_string_substitution(self):
        config = {"command": "{solver}"}
        result = substitute_placeholders(config, {"solver": "/usr/bin/solver"})
        assert result["command"] == "/usr/bin/solver"

    def test_multiple_placeholders_in_one_string(self):
        config = {"command": "{solver} --input {model}"}
        result = substitute_placeholders(
            config, {"solver": "/usr/bin/solver", "model": "./data.dat"},
        )
        assert result["command"] == "/usr/bin/solver --input ./data.dat"

    def test_placeholder_in_list(self):
        config = {"args": ["--solver", "{solver}", "--input", "{model}"]}
        result = substitute_placeholders(
            config, {"solver": "/usr/bin/solver", "model": "./data.dat"},
        )
        assert result["args"] == ["--solver", "/usr/bin/solver", "--input", "./data.dat"]

    def test_placeholder_in_nested_dict(self):
        config = {
            "test_cases": [
                {
                    "name": "test-{tag}",
                    "command": "{solver}",
                    "args": ["{model}"],
                    "expected": {"return_code": 0},
                }
            ]
        }
        result = substitute_placeholders(
            config, {"solver": "/usr/bin/solver", "model": "./data.dat", "tag": "alpha"},
        )
        case = result["test_cases"][0]
        assert case["name"] == "test-alpha"
        assert case["command"] == "/usr/bin/solver"
        assert case["args"] == ["./data.dat"]

    def test_unmatched_placeholder_preserved(self):
        """Unmatched {xxx} should be kept as-is (safe for regex patterns like {2})."""
        config = {"expected": {"output_matches": r"\d{2,4}"}}
        result = substitute_placeholders(config, {"solver": "/bin/solver"})
        assert result["expected"]["output_matches"] == r"\d{2,4}"

    def test_partial_match_preserved(self):
        """Only entirely matching keys are substituted; partial matches stay."""
        config = {"command": "{solver_extra}"}
        result = substitute_placeholders(config, {"solver": "/bin/solver"})
        assert result["command"] == "{solver_extra}"

    def test_non_string_values_unchanged(self):
        config = {"timeout": 60, "priority": 3.5, "enabled": True, "data": None}
        result = substitute_placeholders(config, {"timeout": "999"})
        assert result["timeout"] == 60
        assert result["priority"] == 3.5
        assert result["enabled"] is True
        assert result["data"] is None

    def test_original_config_not_mutated(self):
        original = {"command": "{solver}", "args": ["{model}"]}
        result = substitute_placeholders(
            original, {"solver": "/usr/bin/solver", "model": "./data.dat"},
        )
        # Original should be unchanged
        assert original["command"] == "{solver}"
        assert original["args"] == ["{model}"]
        # Result should have substitutions
        assert result["command"] == "/usr/bin/solver"
        assert result["args"] == ["./data.dat"]

    def test_variable_value_converted_to_str(self):
        """Non-string variable values should be converted via str()."""
        config = {"command": "{count} {flag}"}
        result = substitute_placeholders(config, {"count": 42, "flag": True})
        assert result["command"] == "42 True"


# ---------------------------------------------------------------------------
# Integration-style: full config dict with placeholders
# ---------------------------------------------------------------------------

class TestPlaceholderInTestCases:
    """End-to-end style tests with realistic config dicts."""

    def test_full_json_config_with_steps(self):
        config = {
            "test_cases": [
                {
                    "name": "Multi-step with placeholders",
                    "steps": [
                        {
                            "command": "{solver}",
                            "args": ["--parse", "{input}"],
                            "expected": {"return_code": 0},
                        },
                        {
                            "command": "{solver}",
                            "args": ["--solve", "{input}"],
                            "expected": {"output_contains": ["Optimal"]},
                        },
                    ],
                }
            ]
        }
        result = substitute_placeholders(
            config, {"solver": "/opt/solver", "input": "model.dat"},
        )
        steps = result["test_cases"][0]["steps"]
        assert steps[0]["command"] == "/opt/solver"
        assert steps[0]["args"] == ["--parse", "model.dat"]
        assert steps[1]["command"] == "/opt/solver"
        assert steps[1]["args"] == ["--solve", "model.dat"]
