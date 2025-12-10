from dataclasses import dataclass
from typing import List, Dict, Any, Optional

@dataclass
class TestCase:
    name: str
    command: str
    args: List[str]
    expected: Dict[str, Any]
    description: str = ""
    timeout: Optional[float] = None
    resources: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert test case to dictionary format"""
        print("Convert test case to dictionary format")
        print(self.command)
        return {
            "name": self.name,
            "command": self.command,
            "args": self.args,
            "expected": self.expected,
            "timeout": self.timeout,
            "resources": self.resources,
        }