"""Controlled shell execution tool for the AI Coding Harness.

Enables safe and monitored execution of commands (e.g., pytest, npm test, git)
with sandboxing, timeouts, dangerous command blocking, and output truncation.
"""

from __future__ import annotations

import os
import re
import shlex
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from harness.model.schemas import ToolDefinition

DEFAULT_BLOCKED_PATTERNS = [
    r"\brm\s+-[a-zA-Z]*[rR][a-zA-Z]*\s+(?:/|\~|\*|\$HOME)",  # rm -rf / or ~ or *
    r">\s*/dev/sd[a-z]",                                     # raw disk overwrite
    r">\s*/dev/nvme",
    r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;",                # fork bomb
    r"\bmkfs\b",                                              # formatting filesystems
    r"\bdd\s+if=.*of=/dev/",                                  # raw device dd
    r"\bshutdown\b",                                          # system shutdown
    r"\breboot\b",                                            # system reboot
]


@dataclass
class CommandResult:
    """Result of a shell command execution."""

    command: str
    exit_code: int
    stdout: str
    stderr: str
    duration_seconds: float
    timed_out: bool = False

    @property
    def success(self) -> bool:
        return self.exit_code == 0 and not self.timed_out

    @property
    def combined_output(self) -> str:
        parts = []
        if self.stdout:
            parts.append(self.stdout)
        if self.stderr:
            parts.append(self.stderr)
        return "\n".join(parts)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["success"] = self.success
        d["combined_output"] = self.combined_output
        return d


class ShellTool:
    """Controls and executes shell commands safely within a workspace sandbox."""

    def __init__(
        self,
        working_dir: str = ".",
        default_timeout: float = 60.0,
        max_output_chars: int = 50000,
        allowed_commands: Optional[List[str]] = None,
        blocked_patterns: Optional[List[str]] = None,
    ) -> None:
        self.working_dir = Path(working_dir).resolve()
        self.default_timeout = default_timeout
        self.max_output_chars = max_output_chars
        self.allowed_commands = allowed_commands
        self.blocked_patterns = (
            list(DEFAULT_BLOCKED_PATTERNS)
            if blocked_patterns is None
            else blocked_patterns
        )

    def _is_command_safe(self, command: str) -> tuple[bool, Optional[str]]:
        """Validate that the command does not violate safety restrictions."""
        # Check blocked dangerous patterns
        for pattern in self.blocked_patterns:
            if re.search(pattern, command):
                return False, f"Command matches dangerous pattern: '{pattern}'"

        # Check allowed command prefix if whitelist is set
        if self.allowed_commands is not None:
            tokens = shlex.split(command, comments=False)
            if not tokens:
                return False, "Empty command"
            base_cmd = Path(tokens[0]).name
            if base_cmd not in self.allowed_commands:
                return False, f"Command '{base_cmd}' is not in the allowed list: {self.allowed_commands}"

        return True, None

    def execute(
        self,
        command: str,
        timeout: Optional[float] = None,
        cwd: Optional[str] = None,
        env_vars: Optional[Dict[str, str]] = None,
    ) -> CommandResult:
        """Execute a shell command with monitoring and safety limits.

        Args:
            command: Shell command string to run.
            timeout: Execution timeout in seconds (default: self.default_timeout).
            cwd: Custom working directory relative to sandbox root.
            env_vars: Extra or overridden environment variables.

        Returns:
            CommandResult with exit code, stdout, stderr, and timing.
        """
        is_safe, error_msg = self._is_command_safe(command)
        if not is_safe:
            return CommandResult(
                command=command,
                exit_code=-1,
                stdout="",
                stderr=f"Security violation: {error_msg}",
                duration_seconds=0.0,
                timed_out=False,
            )

        exec_dir = (
            (self.working_dir / cwd).resolve() if cwd else self.working_dir
        )
        if not exec_dir.exists():
            return CommandResult(
                command=command,
                exit_code=-1,
                stdout="",
                stderr=f"Working directory does not exist: {exec_dir}",
                duration_seconds=0.0,
                timed_out=False,
            )

        # Prepare environment
        env = os.environ.copy()
        if env_vars:
            env.update(env_vars)

        # Ensure PYTHONPATH includes src if not set
        src_path = str(self.working_dir / "src")
        current_pythonpath = env.get("PYTHONPATH", "")
        if src_path not in current_pythonpath:
            env["PYTHONPATH"] = (
                f"{src_path}:{current_pythonpath}"
                if current_pythonpath
                else src_path
            )

        effective_timeout = timeout or self.default_timeout
        start_time = time.monotonic()

        try:
            process = subprocess.run(
                command,
                shell=True,
                cwd=exec_dir,
                env=env,
                capture_output=True,
                text=True,
                timeout=effective_timeout,
            )
            duration = time.monotonic() - start_time
            stdout = self._truncate(process.stdout)
            stderr = self._truncate(process.stderr)

            return CommandResult(
                command=command,
                exit_code=process.returncode,
                stdout=stdout,
                stderr=stderr,
                duration_seconds=round(duration, 3),
                timed_out=False,
            )
        except subprocess.TimeoutExpired as exc:
            duration = time.monotonic() - start_time
            stdout = self._truncate(exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or ""))
            stderr = (
                f"Command timed out after {effective_timeout}s\n"
                + self._truncate(exc.stderr.decode() if isinstance(exc.stderr, bytes) else (exc.stderr or ""))
            )
            return CommandResult(
                command=command,
                exit_code=-1,
                stdout=stdout,
                stderr=stderr,
                duration_seconds=round(duration, 3),
                timed_out=True,
            )
        except Exception as exc:
            duration = time.monotonic() - start_time
            return CommandResult(
                command=command,
                exit_code=-1,
                stdout="",
                stderr=f"Execution error: {exc}",
                duration_seconds=round(duration, 3),
                timed_out=False,
            )

    def _truncate(self, text: Optional[str]) -> str:
        """Truncate text if it exceeds maximum character limit."""
        if not text:
            return ""
        if len(text) <= self.max_output_chars:
            return text
        excess = len(text) - self.max_output_chars
        return text[: self.max_output_chars] + f"\n\n... [Output truncated: {excess} characters omitted] ...\n"


# Module-level default
_default_shell = ShellTool()


def execute_command(
    command: str,
    timeout: Optional[float] = None,
    cwd: Optional[str] = None,
    env_vars: Optional[Dict[str, str]] = None,
) -> CommandResult:
    """Run a shell command using default ShellTool."""
    return _default_shell.execute(command, timeout, cwd, env_vars)


def get_shell_tool_definitions() -> List[ToolDefinition]:
    """Return ToolDefinition schemas for shell tools."""
    return [
        ToolDefinition(
            name="execute_command",
            description="Run a controlled bash command in the workspace (e.g. 'pytest', 'npm test').",
            parameters={
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Shell command line to execute"},
                    "timeout": {"type": "number", "description": "Timeout in seconds (default: 60s)"},
                    "cwd": {"type": "string", "description": "Subdirectory to execute within"},
                },
                "required": ["command"],
            },
        )
    ]
