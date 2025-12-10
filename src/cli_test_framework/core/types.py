from typing import Any, Dict, List, Optional, TypedDict


class ExpectedResult(TypedDict, total=False):
    """Expectation configuration for a single test case."""

    return_code: Optional[int]
    output_contains: List[str]
    output_matches: Optional[str]


class ResourceRequirements(TypedDict, total=False):
    """Optional resource hints for scheduling."""

    estimated_time: float  # seconds, used for ordering (LPT)
    min_memory_mb: float  # soft hint to avoid OOM
    priority: int  # higher value => higher priority


class TestCaseData(TypedDict):
    """Input data shape for a test case after解析/路径处理."""

    name: str
    command: str
    args: List[str]
    expected: ExpectedResult
    description: Optional[str]
    timeout: Optional[float]
    resources: Optional[ResourceRequirements]


class SetupConfig(TypedDict):
    """Setup configuration (currently environment variables only)."""

    environment_variables: Dict[str, str]


class TestSuiteConfig(TypedDict):
    """Top-level configuration for a suite loaded from JSON/YAML."""

    setup: Optional[SetupConfig]
    test_cases: List[TestCaseData]


class TestResultData(TypedDict):
    """Normalized result produced by executing a single test case."""

    name: str
    status: str  # 'passed', 'failed'
    message: str
    command: str
    output: str
    return_code: Optional[int]
    duration: float

