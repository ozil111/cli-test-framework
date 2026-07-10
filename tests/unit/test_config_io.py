"""Tests for config_io module (load/save/validate)."""

from pathlib import Path
import json
import tempfile
import os
import pytest

from cli_test_framework.config.config_io import (
    load_config,
    save_config,
    validate_config,
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


class TestLoadConfig:
    def test_load_json_no_imports(self):
        """Loading a JSON config without imports returns raw dict."""
        path = FIXTURES / "sub_text_tests.json"
        config = load_config(path)
        assert "test_cases" in config
        assert len(config["test_cases"]) == 2

    def test_load_with_expand(self):
        """Loading main_config with expand=True inlines imports."""
        path = FIXTURES / "main_config.json"
        config = load_config(path, expand=True)
        assert len(config["test_cases"]) == 5

    def test_load_without_expand(self):
        """Loading with expand=False preserves import entries."""
        path = FIXTURES / "main_config.json"
        config = load_config(path, expand=False)
        # Should have import entries, not expanded
        has_import = any("import" in tc for tc in config["test_cases"])
        assert has_import

    def test_load_nonexistent_file(self):
        """Loading a nonexistent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            load_config(Path("nonexistent.json"))


class TestSaveConfig:
    def test_save_and_load_json(self):
        """Round-trip save/load for JSON."""
        config = {
            "test_cases": [
                {"name": "tc1", "command": "echo", "args": ["hi"],
                 "expected": {"return_code": 0}},
            ]
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test_config.json"
            save_config(config, path)
            assert path.exists()

            loaded = load_config(path, expand=False)
            assert loaded["test_cases"][0]["name"] == "tc1"

    def test_save_and_load_yaml(self):
        """Round-trip save/load for YAML."""
        config = {
            "test_cases": [
                {"name": "tc1", "command": "echo", "args": ["hi"],
                 "expected": {"return_code": 0}},
            ]
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test_config.yaml"
            save_config(config, path)
            assert path.exists()

            loaded = load_config(path, expand=False)
            assert loaded["test_cases"][0]["name"] == "tc1"

    def test_save_unsupported_extension(self):
        """Unsupported extension raises ValueError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test_config.txt"
            with pytest.raises(ValueError, match="Unsupported output format"):
                save_config({"test_cases": []}, path)


class TestValidateConfig:
    def test_valid_config_passes(self):
        """A valid config with all required fields passes validation."""
        result = validate_config(FIXTURES / "sub_text_tests.json")
        assert result["valid"] is True
        assert len(result["errors"]) == 0
        assert result["summary"]["cases"] == 2

    def test_valid_config_with_imports(self):
        """Config with valid imports passes validation."""
        result = validate_config(FIXTURES / "main_config.json")
        assert result["valid"] is True

    def test_missing_required_fields(self):
        """Cases missing required fields are reported."""
        result = validate_config(FIXTURES / "missing_fields.json")
        assert result["valid"] is False
        assert len(result["errors"]) > 0
        # First case should be missing 'expected'
        assert any("expected" in err for err in result["errors"])

    def test_import_target_not_found(self):
        """Non-existent import targets are reported."""
        bad_config_path = FIXTURES / "main_config.json"
        # Create a temp config that imports a nonexistent file
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            config = {
                "test_cases": [
                    {"import": "nonexistent.json"}
                ]
            }
            path = tmpdir_path / "bad_main.json"
            save_config(config, path)
            result = validate_config(path)
            assert result["valid"] is False
            assert any("not found" in err for err in result["errors"])

    def test_circular_import_detected(self):
        """Circular imports are detected."""
        result = validate_config(FIXTURES / "circular_config_a.json")
        assert result["valid"] is False
        assert any("Circular" in err for err in result["errors"])

    def test_files_loaded_summary(self):
        """Summary includes file count for configs with imports."""
        result = validate_config(FIXTURES / "main_config.json")
        assert result["summary"]["files"] == 3  # main + 2 sub-files
        assert result["summary"]["cases"] == 5
