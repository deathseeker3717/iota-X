"""Unit tests for the unified ToolRegistry."""

import pytest
from pathlib import Path
from harness.tools import ToolRegistry


def test_tool_registry_definitions():
    registry = ToolRegistry()
    definitions = registry.get_tool_definitions()

    # Verify all tools have valid definitions
    names = {d.name for d in definitions}
    expected = {
        "list_files",
        "read_file",
        "write_file",
        "edit_file",
        "search_files",
        "search_symbol",
        "find_references",
        "find_imports",
        "execute_command",
        "git_status",
        "git_diff",
        "git_log",
        "git_show",
        "run_tests",
    }
    assert expected.issubset(names)


def test_tool_registry_execution(tmp_path):
    registry = ToolRegistry(root_dir=str(tmp_path))

    # Write file via registry
    res_w = registry.execute(
        "write_file", {"path": "test.txt", "content": "hello world"}
    )
    assert res_w is True

    # Read file via registry
    res_r = registry.execute("read_file", {"path": "test.txt"})
    assert res_r == "hello world"

    # List files via registry
    res_l = registry.execute("list_files", {"directory": "."})
    assert "test.txt" in res_l

    # Execute command via registry
    res_c = registry.execute("execute_command", {"command": "echo 123"})
    assert res_c.success is True
    assert "123" in res_c.stdout

    # Unknown tool
    with pytest.raises(ValueError, match="Unknown tool"):
        registry.execute("unknown_tool", {})
