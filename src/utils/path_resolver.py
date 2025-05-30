from pathlib import Path
from typing import List
import shlex
import os

class PathResolver:
    def __init__(self, workspace: Path):
        self.workspace = workspace

    def resolve_paths(self, args: List[str]) -> List[str]:
        resolved_args = []
        for arg in args:
            if not arg.startswith("--"):
                # Only prepend workspace if the path is relative
                if not Path(arg).is_absolute():
                    resolved_args.append(str(self.workspace / arg))
                else:
                    resolved_args.append(arg)
            else:
                resolved_args.append(arg)
        return resolved_args

    def resolve_command(self, command: str) -> str:
        """
        解析命令路径
        - 系统命令（如echo, ping, dir等）保持原样
        - 相对路径的可执行文件转换为绝对路径
        """
        # 常见的系统命令列表
        system_commands = {
            'echo', 'ping', 'dir', 'ls', 'cat', 'grep', 'find', 'sort', 
            'head', 'tail', 'wc', 'curl', 'wget', 'git', 'python', 'node',
            'npm', 'pip', 'java', 'javac', 'gcc', 'make', 'cmake', 'docker',
            'kubectl', 'helm', 'terraform', 'ansible', 'ssh', 'scp', 'rsync'
        }
        
        # 如果是系统命令或绝对路径，保持原样
        if command in system_commands or Path(command).is_absolute():
            return command
        
        # 否则当作相对路径处理
        return str(self.workspace / command)

    def parse_command_string(self, command_string: str) -> str:
        """
        智能解析命令字符串，正确处理包含空格的路径
        
        Args:
            command_string: 原始命令字符串，如 "python ./script.py" 或 r"C:\\Program Files (x86)\\python.exe script.py"
            
        Returns:
            解析后的完整命令字符串
        """
        # 特殊处理：如果命令字符串包含引号，使用shlex解析
        if '"' in command_string or "'" in command_string:
            try:
                # 对于所有系统都使用posix=True来正确处理引号
                # 这样可以去掉引号，但保留路径内容
                parts = shlex.split(command_string, posix=True)
                
                if not parts:
                    return command_string
                
                # 第一部分是命令，其余是参数
                command_part = parts[0]
                remaining_parts = parts[1:]
                
                # 解析命令部分（如果是绝对路径，保持原样；否则解析）
                if Path(command_part).is_absolute():
                    resolved_command = command_part
                else:
                    resolved_command = self.resolve_command(command_part)
                
                # 解析参数部分
                resolved_parts = []
                for part in remaining_parts:
                    if part.startswith('-'):
                        # 选项参数，保持原样
                        resolved_parts.append(part)
                    elif ('.' in part or '/' in part or '\\' in part) and not part.isdigit():
                        # 看起来像文件路径
                        if not Path(part).is_absolute():
                            resolved_parts.append(str(self.workspace / part))
                        else:
                            resolved_parts.append(part)
                    else:
                        # 其他参数，保持原样
                        resolved_parts.append(part)
                
                return f"{resolved_command} {' '.join(resolved_parts)}"
                
            except ValueError:
                # shlex解析失败，回退到简单处理
                pass
        
        # 简单情况：没有引号的命令字符串
        # 先尝试识别是否以绝对路径开头
        if self._starts_with_absolute_path(command_string):
            # 处理以绝对路径开头的命令
            return self._parse_absolute_path_command(command_string)
        else:
            # 普通命令处理
            parts = command_string.split()
            if not parts:
                return command_string
            
            if len(parts) == 1:
                return self.resolve_command(parts[0])
            else:
                command_part = parts[0]
                remaining_parts = parts[1:]
                
                resolved_command = self.resolve_command(command_part)
                resolved_parts = []
                
                for part in remaining_parts:
                    if part.startswith('-'):
                        resolved_parts.append(part)
                    elif ('.' in part or '/' in part or '\\' in part) and not part.isdigit():
                        if not Path(part).is_absolute():
                            resolved_parts.append(str(self.workspace / part))
                        else:
                            resolved_parts.append(part)
                    else:
                        resolved_parts.append(part)
                
                return f"{resolved_command} {' '.join(resolved_parts)}"
    
    def _starts_with_absolute_path(self, command_string: str) -> bool:
        """检查命令字符串是否以绝对路径开头"""
        if os.name == 'nt':  # Windows
            # Windows绝对路径模式：C:\... 或 \\server\...
            return (len(command_string) >= 3 and 
                    command_string[1:3] == ':\\') or command_string.startswith('\\\\')
        else:  # Unix/Linux
            return command_string.startswith('/')
    
    def _parse_absolute_path_command(self, command_string: str) -> str:
        """解析以绝对路径开头的命令字符串"""
        # 对于Windows路径，需要特殊处理空格
        if os.name == 'nt':
            # 尝试找到第一个.exe或.bat等可执行文件扩展名
            exe_extensions = ['.exe', '.bat', '.cmd', '.com']
            
            for ext in exe_extensions:
                if ext in command_string:
                    # 找到可执行文件的结束位置
                    ext_pos = command_string.find(ext)
                    if ext_pos != -1:
                        command_end = ext_pos + len(ext)
                        command_part = command_string[:command_end]
                        remaining = command_string[command_end:].strip()
                        
                        if remaining:
                            # 解析剩余参数
                            remaining_parts = remaining.split()
                            resolved_parts = []
                            
                            for part in remaining_parts:
                                if part.startswith('-'):
                                    resolved_parts.append(part)
                                elif ('.' in part or '/' in part or '\\' in part) and not part.isdigit():
                                    if not Path(part).is_absolute():
                                        resolved_parts.append(str(self.workspace / part))
                                    else:
                                        resolved_parts.append(part)
                                else:
                                    resolved_parts.append(part)
                            
                            return f"{command_part} {' '.join(resolved_parts)}"
                        else:
                            return command_part
        
        # 如果没有找到可执行文件扩展名，回退到简单分割
        parts = command_string.split()
        if not parts:
            return command_string
        
        # 假设第一个部分是命令
        command_part = parts[0]
        remaining_parts = parts[1:]
        
        resolved_parts = []
        for part in remaining_parts:
            if part.startswith('-'):
                resolved_parts.append(part)
            elif ('.' in part or '/' in part or '\\' in part) and not part.isdigit():
                if not Path(part).is_absolute():
                    resolved_parts.append(str(self.workspace / part))
                else:
                    resolved_parts.append(part)
            else:
                resolved_parts.append(part)
        
        return f"{command_part} {' '.join(resolved_parts)}"