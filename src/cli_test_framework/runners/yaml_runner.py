import sys
import logging
from typing import Optional, Dict, Any

from ..core.base_runner import BaseRunner
from ..core.config_loader import parse_test_cases
from ..core.test_case import TestCase
from ..core.execution import execute_single_test_case
from ..core.types import TestCaseData
from ..utils.path_resolver import PathResolver

logger = logging.getLogger("cli_test_framework.runners.yaml_runner")

class YAMLRunner(BaseRunner):
    def __init__(self, config_file="test_cases.yaml", workspace: Optional[str] = None,
                 test_case_filter: Optional[list] = None,
                 history_dir: Optional[str] = None,
                 regression_threshold: float = 1.5):
        super().__init__(config_file, workspace, test_case_filter, history_dir, regression_threshold)
        # Backward-compatible attribute for tests that patch path_resolver
        self.path_resolver = PathResolver(self.workspace)

    def load_test_cases(self):
        """Load test cases from a YAML file."""
        try:
            import yaml
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)

            self.load_setup_from_config(config)
            self.test_cases = parse_test_cases(config, self.workspace, self.path_resolver)

            logger.info("Successfully loaded %d test cases", len(self.test_cases))
        except Exception as e:
            sys.exit(f"Failed to load configuration file: {str(e)}")

    def run_single_test(self, case: TestCase) -> Dict[str, Any]:
        """Run a single test case and return the result"""
        if case.steps:
            return self._run_sequence(case)

        case_data: TestCaseData = {
            "name": case.name,
            "command": case.command,
            "args": case.args,
            "expected": case.expected,
            "description": case.description or None,
            "timeout": case.timeout,
            "resources": case.resources,
        }

        command_preview = f"{case_data['command']} {' '.join(case_data['args'])}".strip()
        logger.info("  Executing command: %s", command_preview)

        result = execute_single_test_case(case_data, str(self.workspace) if self.workspace else None)

        if result["output"].strip():
            logger.debug("  Command output:")
            for line in result["output"].splitlines():
                logger.debug("    %s", line)

        if result["status"] != "passed" and result.get("message"):
            logger.error("  Error: %s", result["message"])

        return result