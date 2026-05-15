from unittest.mock import MagicMock, patch

import tests.run_all as run_all


def test_extra_arguments_preserve_quoted_values(monkeypatch):
    monkeypatch.setattr(
        "sys.argv",
        ["run_all.py", "--scope", "unit", "--extra", "-k 'json or yaml' --maxfail=1"],
    )

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        assert run_all.main() == 0

    pytest_args = mock_run.call_args.args[0]
    assert pytest_args[-3:] == ["-k", "json or yaml", "--maxfail=1"]

