from argparse import Namespace

import pytest

from cli_test_framework import cli


class DummyRunner:
    def __init__(self, *args, **kwargs):
        self.init_args = args
        self.init_kwargs = kwargs
        self.results = {
            "total": 2,
            "passed": 1,
            "failed": 1,
            "details": [
                {"name": "ok", "status": "passed"},
                {"name": "bad", "status": "failed", "message": "boom"},
            ],
        }

    def run_tests(self):
        return self.init_kwargs.get("success", False)


def make_args(config_file, **overrides):
    values = {
        "config_file": str(config_file),
        "workspace": None,
        "parallel": False,
        "workers": None,
        "execution_mode": "thread",
        "output_format": "text",
        "test_case": None,
        "verbose": False,
        "debug": False,
    }
    values.update(overrides)
    return Namespace(**values)


def test_run_tests_rejects_missing_config(caplog):
    success = cli.run_tests(make_args("missing.json"))

    assert not success
    assert "Configuration file not found" in caplog.text


def test_run_tests_rejects_unsupported_config_format(tmp_path, caplog):
    config = tmp_path / "cases.toml"
    config.write_text("", encoding="utf-8")

    success = cli.run_tests(make_args(config))

    assert not success
    assert "Unsupported configuration file format" in caplog.text


def test_run_tests_uses_json_runner_and_prints_totals(tmp_path, monkeypatch, caplog):
    config = tmp_path / "cases.json"
    config.write_text('{"test_cases": []}', encoding="utf-8")

    class PassingRunner(DummyRunner):
        def run_tests(self):
            return True

    monkeypatch.setattr(cli, "JSONRunner", PassingRunner)

    success = cli.run_tests(make_args(config, verbose=True, test_case=["ok"]))

    log_text = caplog.text
    assert success
    assert "Total Tests: 2" in log_text
    assert "Passed: 1" in log_text
    assert "bad" in log_text
    assert "boom" in log_text


def test_run_tests_uses_parallel_runner(tmp_path, monkeypatch):
    config = tmp_path / "cases.json"
    config.write_text('{"test_cases": []}', encoding="utf-8")
    captured = {}

    class PassingParallelRunner(DummyRunner):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            captured.update(kwargs)

        def run_tests(self):
            return True

    monkeypatch.setattr(cli, "ParallelJSONRunner", PassingParallelRunner)

    success = cli.run_tests(
        make_args(config, parallel=True, workers=3, execution_mode="process")
    )

    assert success
    assert captured["max_workers"] == 3
    assert captured["execution_mode"] == "process"


def test_main_exits_nonzero_without_command(monkeypatch):
    monkeypatch.setattr("sys.argv", ["cli-test"])

    with pytest.raises(SystemExit) as exc:
        cli.main()

    assert exc.value.code == 1

