from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass
class TestCaseStep:
    """A single step within a sequence test case."""
    __test__ = False
    command: str
    args: List[str]
    expected: Dict[str, Any]
    timeout: Optional[float] = None

@dataclass
class TestCase:
    __test__ = False
    name: str
    command: str = ""
    args: List[str] = field(default_factory=list)
    expected: Dict[str, Any] = field(default_factory=dict)
    description: str = ""
    timeout: Optional[float] = None
    resources: Optional[Dict[str, Any]] = None
    steps: Optional[List[TestCaseStep]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert test case to dictionary format"""
        result = {
            "name": self.name,
            "command": self.command,
            "args": self.args,
            "expected": self.expected,
            "timeout": self.timeout,
            "resources": self.resources,
        }
        if self.steps is not None:
            result["steps"] = [
                {
                    "command": s.command,
                    "args": s.args,
                    "expected": s.expected,
                    "timeout": s.timeout,
                }
                for s in self.steps
            ]
        return result