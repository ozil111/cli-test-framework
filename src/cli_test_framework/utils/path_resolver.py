from pathlib import Path
from typing import List, Union
import shlex
import os
import shutil

WorkspaceLike = Union[str, Path]


def _as_workspace_path(workspace: WorkspaceLike) -> Path:
    return workspace if isinstance(workspace, Path) else Path(workspace)


def resolve_paths(args: List[str], workspace: WorkspaceLike) -> List[str]:
    """Resolve relative paths in args against the workspace."""
    workspace_path = _as_workspace_path(workspace)
    resolved_args = []
    for arg in args:
        if not arg.startswith("--"):
            if not Path(arg).is_absolute():
                resolved_args.append(str(workspace_path / arg))
            else:
                resolved_args.append(arg)
        else:
            resolved_args.append(arg)
    return resolved_args


def resolve_command(command: str, workspace: WorkspaceLike) -> str:
    """
    Resolve command path:
    - absolute path: keep
    - available in PATH: keep
    - known system command: keep
    - otherwise treat as relative to workspace
    """
    workspace_path = _as_workspace_path(workspace)

    if Path(command).is_absolute():
        return command

    if shutil.which(command) is not None:
        return command

    system_commands = {
        'echo', 'ping', 'dir', 'ls', 'cat', 'grep', 'find', 'sort',
        'head', 'tail', 'wc', 'curl', 'wget', 'git', 'python', 'node',
        'npm', 'pip', 'java', 'javac', 'gcc', 'make', 'cmake', 'docker',
        'kubectl', 'helm', 'terraform', 'ansible', 'ssh', 'scp', 'rsync'
    }

    if command in system_commands:
        return command

    return str(workspace_path / command)


def parse_command_string(command_string: str, workspace: WorkspaceLike) -> str:
    """
    Parse command string with smart handling of quoted paths and relative segments.
    """
    workspace_path = _as_workspace_path(workspace)

    if '"' in command_string or "'" in command_string:
        try:
            parts = shlex.split(command_string, posix=True)

            if not parts:
                return command_string

            command_part = parts[0]
            remaining_parts = parts[1:]

            if Path(command_part).is_absolute():
                resolved_command = command_part
            else:
                resolved_command = resolve_command(command_part, workspace_path)

            # Preserve scripts passed via "-c" as a single argument to avoid losing quotes
            resolved_parts = []
            if "-c" in remaining_parts:
                c_index = remaining_parts.index("-c")
                before_c = remaining_parts[:c_index]
                script_body = " ".join(remaining_parts[c_index + 1 :])
                for part in before_c:
                    if part.startswith("-"):
                        resolved_parts.append(part)
                    elif ('.' in part or '/' in part or '\\' in part) and not part.isdigit():
                        if not Path(part).is_absolute():
                            resolved_parts.append(str(workspace_path / part))
                        else:
                            resolved_parts.append(part)
                    else:
                        resolved_parts.append(part)
                resolved_parts.append("-c")
                resolved_parts.append(script_body)
            else:
                for part in remaining_parts:
                    if part.startswith('-'):
                        resolved_parts.append(part)
                    elif ('.' in part or '/' in part or '\\' in part) and not part.isdigit():
                        if not Path(part).is_absolute():
                            resolved_parts.append(str(workspace_path / part))
                        else:
                            resolved_parts.append(part)
                    else:
                        resolved_parts.append(part)

            return f"{resolved_command} {' '.join(resolved_parts)}"

        except ValueError:
            pass

    if _starts_with_absolute_path(command_string):
        return _parse_absolute_path_command(command_string, workspace_path)
    else:
        parts = command_string.split()
        if not parts:
            return command_string

        if len(parts) == 1:
            return resolve_command(parts[0], workspace_path)
        else:
            command_part = parts[0]
            remaining_parts = parts[1:]

            resolved_command = resolve_command(command_part, workspace_path)

            if "-c" in remaining_parts:
                c_index = remaining_parts.index("-c")
                before_c = remaining_parts[:c_index]
                script_body = " ".join(remaining_parts[c_index + 1 :])
                resolved_parts = before_c + ["-c", script_body]
            else:
                resolved_parts = []
                for part in remaining_parts:
                    if part.startswith('-'):
                        resolved_parts.append(part)
                    elif ('.' in part or '/' in part or '\\' in part) and not part.isdigit():
                        if not Path(part).is_absolute():
                            resolved_parts.append(str(workspace_path / part))
                        else:
                            resolved_parts.append(part)
                    else:
                        resolved_parts.append(part)

            return f"{resolved_command} {' '.join(resolved_parts)}"


def _starts_with_absolute_path(command_string: str) -> bool:
    """检查命令字符串是否以绝对路径开头"""
    if os.name == 'nt':
        return (len(command_string) >= 3 and
                command_string[1:3] == ':\\') or command_string.startswith('\\\\')
    else:
        return command_string.startswith('/')


def _parse_absolute_path_command(command_string: str, workspace: WorkspaceLike) -> str:
    workspace_path = _as_workspace_path(workspace)

    if os.name == 'nt':
        exe_extensions = ['.exe', '.bat', '.cmd', '.com']

        for ext in exe_extensions:
            if ext in command_string:
                ext_pos = command_string.find(ext)
                if ext_pos != -1:
                    command_end = ext_pos + len(ext)
                    command_part = command_string[:command_end]
                    remaining = command_string[command_end:].strip()

                    if remaining:
                        remaining_parts = remaining.split()
                        resolved_parts = []

                        for part in remaining_parts:
                            if part.startswith('-'):
                                resolved_parts.append(part)
                            elif ('.' in part or '/' in part or '\\' in part) and not part.isdigit():
                                if not Path(part).is_absolute():
                                    resolved_parts.append(str(workspace_path / part))
                                else:
                                    resolved_parts.append(part)
                            else:
                                resolved_parts.append(part)

                        return f"{command_part} {' '.join(resolved_parts)}"
                    else:
                        return command_part

    parts = command_string.split()
    if not parts:
        return command_string

    command_part = parts[0]
    remaining_parts = parts[1:]

    resolved_parts = []
    for part in remaining_parts:
        if part.startswith('-'):
            resolved_parts.append(part)
        elif ('.' in part or '/' in part or '\\' in part) and not part.isdigit():
            if not Path(part).is_absolute():
                resolved_parts.append(str(workspace_path / part))
            else:
                resolved_parts.append(part)
        else:
            resolved_parts.append(part)

    return f"{command_part} {' '.join(resolved_parts)}"


class PathResolver:
    """
    Backwards-compatible wrapper; delegates to pure functions.
    """

    def __init__(self, workspace: Path):
        self.workspace = workspace

    def resolve_paths(self, args: List[str]) -> List[str]:
        return resolve_paths(args, self.workspace)

    def resolve_command(self, command: str) -> str:
        return resolve_command(command, self.workspace)

    def parse_command_string(self, command_string: str) -> str:
        return parse_command_string(command_string, self.workspace)