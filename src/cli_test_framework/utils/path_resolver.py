from pathlib import Path
from typing import List, Union
import shlex
import os
import shutil
import subprocess

WorkspaceLike = Union[str, Path]


def _as_workspace_path(workspace: WorkspaceLike) -> Path:
    return workspace if isinstance(workspace, Path) else Path(workspace)


def _resolve_relative_part(part: str, workspace_path: Path) -> str:
    """
    带标识符的路径解析逻辑：
    1. 检查标识符 'raw:' -> 如果存在，强行按原样返回（剥离标识符）
    2. 跳过旗标 (- 开头)
    3. 跳过纯数字
    4. 启发式解析其他潜在路径
    """
    if part.startswith("raw:"):
        return part[4:]

    if part.startswith("-"):
        return part

    if part.isdigit():
        return part

    if "." in part or "/" in part or "\\" in part:
        if not Path(part).is_absolute():
            return str(workspace_path / part)

    return part


def resolve_paths(args: List[str], workspace: WorkspaceLike) -> List[str]:
    """根据标识符或启发式规则解析参数列表中的路径"""
    workspace_path = _as_workspace_path(workspace)
    return [_resolve_relative_part(arg, workspace_path) for arg in args]


def _shell_join(parts: List[str]) -> str:
    if os.name == "nt":
        return subprocess.list2cmdline(parts)
    return shlex.join(parts)


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

            resolved_command = (
                command_part
                if Path(command_part).is_absolute()
                else resolve_command(command_part, workspace_path)
            )

            resolved_parts = []
            if "-c" in remaining_parts:
                c_index = remaining_parts.index("-c")
                before_c = remaining_parts[:c_index]
                script_body = " ".join(remaining_parts[c_index + 1 :])
                for part in before_c:
                    resolved_parts.append(_resolve_relative_part(part, workspace_path))
                resolved_parts.append("-c")
                resolved_parts.append(script_body)
            else:
                for part in remaining_parts:
                    resolved_parts.append(_resolve_relative_part(part, workspace_path))

            return _shell_join([resolved_command, *resolved_parts])

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
                resolved_parts = [
                    _resolve_relative_part(p, workspace_path) for p in before_c
                ] + ["-c", script_body]
            else:
                resolved_parts = [
                    _resolve_relative_part(p, workspace_path) for p in remaining_parts
                ]

            return _shell_join([resolved_command, *resolved_parts])


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
                        resolved_parts = [
                            _resolve_relative_part(p, workspace_path)
                            for p in remaining_parts
                        ]
                        return _shell_join([command_part, *resolved_parts])
                    else:
                        return command_part

    parts = command_string.split()
    if not parts:
        return command_string

    command_part = parts[0]
    remaining_parts = parts[1:]

    resolved_parts = [
        _resolve_relative_part(p, workspace_path) for p in remaining_parts
    ]
    return _shell_join([command_part, *resolved_parts])


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
