"""YAMLRunner – thin backward-compatible wrapper around ConfigRunner."""
import logging
from typing import Optional

from .config_runner import ConfigRunner

logger = logging.getLogger("cli_test_framework.runners.yaml_runner")


def _yaml_load(f):
    """Lazy-load yaml.safe_load so the package is importable without PyYAML."""
    import yaml
    return yaml.safe_load(f)


class YAMLRunner(ConfigRunner):
    """Sequential YAML test runner (backward-compatible thin wrapper)."""

    def __init__(self, config_file="test_cases.yaml",
                 workspace: Optional[str] = None,
                 test_case_filter: Optional[list] = None,
                 test_case_tag_filter: Optional[list] = None,
                 history_dir: Optional[str] = None,
                 regression_threshold: float = 1.5):
        super().__init__(
            config_file=config_file,
            workspace=workspace,
            test_case_filter=test_case_filter,
            test_case_tag_filter=test_case_tag_filter,
            history_dir=history_dir,
            regression_threshold=regression_threshold,
            config_loader=_yaml_load,
        )
