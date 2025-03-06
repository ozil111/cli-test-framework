from pathlib import Path
from typing import List

class PathResolver:
    def __init__(self, workspace: Path):
        self.workspace = workspace

    def resolve_paths(self, args: List[str]) -> List[str]:
        resolved_args = []
        for arg in args:
            if not arg.startswith("--"):
                resolved_args.append(str(self.workspace / arg))
            else:
                resolved_args.append(arg)
        return resolved_args

    def resolve_command(self, command: str) -> str:
        if not command.startswith("python"):
            return str(self.workspace / command)
        return command