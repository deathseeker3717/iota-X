"""Unit tests for the ShellTool."""

import pytest
from pathlib import Path
from harness.tools.shell import (
    CommandResult,
    ShellTool,
    execute_command,
    get_shell_tool_definitions,
)


def test_execute_simple_command(tmp_path):
    shell = ShellTool(working_dir=str(tmp_path))
    res = shell.execute("echo 'hello shell'")

    assert res.success is True
    assert res.exit_code == 0
    assert "hello shell" in res.stdout
    assert res.timed_out is False
    assert res.duration_seconds >= 0.0


def test_execute_command_failure(tmp_path):
    shell = ShellTool(working_dir=str(tmp_path))
    res = shell.execute("exit 42")

    assert res.success is False
    assert res.exit_code == 42


def test_execute_dangerous_command_blocked(tmp_path):
    shell = ShellTool(working_dir=str(tmp_path))
    res = shell.execute("rm -rf /")

    assert res.success is False
    assert res.exit_code == -1
    assert "Security violation" in res.stderr


def test_execute_timeout(tmp_path):
    shell = ShellTool(working_dir=str(tmp_path))
    # Python one-liner to sleep
    res = shell.execute("python3 -c 'import time; time.sleep(2)'", timeout=0.2)

    assert res.timed_out is True
    assert res.success is False
    assert "timed out" in res.stderr


def test_output_truncation(tmp_path):
    shell = ShellTool(working_dir=str(tmp_path), max_output_chars=100)
    res = shell.execute("python3 -c 'print(\"A\" * 500)'")

    assert res.success is True
    assert len(res.stdout) > 100
    assert "Output truncated" in res.stdout


def test_command_whitelisting(tmp_path):
    shell = ShellTool(working_dir=str(tmp_path), allowed_commands=["pytest", "echo"])
    res1 = shell.execute("echo test")
    assert res1.success is True

    res2 = shell.execute("cat file.txt")
    assert res2.success is False
    assert "not in the allowed list" in res2.stderr


def test_shell_tool_definitions():
    defs = get_shell_tool_definitions()
    assert len(defs) == 1
    assert defs[0].name == "execute_command"
