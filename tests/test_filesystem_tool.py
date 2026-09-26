"""Unit tests for the FilesystemTool."""

import pytest
from pathlib import Path
from harness.tools.filesystem import (
    FilesystemTool,
    get_filesystem_tool_definitions,
    list_files,
    read_file,
    write_file,
    edit_file,
)


def test_write_and_read_file(tmp_path):
    fs = FilesystemTool(root_dir=str(tmp_path))
    target = "subdir/sample.txt"
    content = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5\n"

    # Write file
    assert fs.write_file(target, content) is True

    # Read all
    read_content = fs.read_file(target)
    assert read_content == content

    # Read range
    slice_content = fs.read_file(target, start_line=2, end_line=4)
    assert slice_content == "Line 2\nLine 3\nLine 4\n"


def test_read_file_truncation(tmp_path):
    fs = FilesystemTool(root_dir=str(tmp_path))
    content = "\n".join(f"Line {i}" for i in range(1, 20))
    fs.write_file("long.txt", content)

    result = fs.read_file("long.txt", max_lines=5)
    assert "Line 1" in result
    assert "Line 5" in result
    assert "Truncated: 14 more lines" in result


def test_list_files(tmp_path):
    fs = FilesystemTool(root_dir=str(tmp_path))
    fs.write_file("src/main.py", "print('hello')")
    fs.write_file("src/utils.py", "def util(): pass")
    fs.write_file("src/temp.txt", "temp")
    fs.write_file(".venv/lib/ignored.py", "ignored")

    # Recursive listing with default excludes
    files = fs.list_files("src")
    assert "src/main.py" in files
    assert "src/utils.py" in files
    assert "src/temp.txt" in files
    assert not any(".venv" in f for f in files)

    # Pattern filtering
    py_files = fs.list_files("src", pattern="*.py")
    assert "src/main.py" in py_files
    assert "src/utils.py" in py_files
    assert "src/temp.txt" not in py_files


def test_edit_file(tmp_path):
    fs = FilesystemTool(root_dir=str(tmp_path))
    fs.write_file("app.py", "def old_name():\n    return 42\n")

    # Successful single edit
    assert fs.edit_file("app.py", "old_name", "new_name") is True
    assert "def new_name():" in fs.read_file("app.py")

    # Missing target raises ValueError
    with pytest.raises(ValueError, match="Target string not found"):
        fs.edit_file("app.py", "nonexistent", "replacement")

    # Duplicate target without allow_multiple raises ValueError
    fs.write_file("dup.py", "value = 1\nvalue = 1\n")
    with pytest.raises(ValueError, match="Target string found 2 times"):
        fs.edit_file("dup.py", "value = 1", "value = 2", allow_multiple=False)

    # Duplicate target with allow_multiple works
    assert fs.edit_file("dup.py", "value = 1", "value = 2", allow_multiple=True) is True
    assert fs.read_file("dup.py") == "value = 2\nvalue = 2\n"


def test_sandbox_traversal_protection(tmp_path):
    sandbox_dir = tmp_path / "sandbox"
    sandbox_dir.mkdir()
    outside_file = tmp_path / "secret.txt"
    outside_file.write_text("secret_password")

    fs = FilesystemTool(root_dir=str(sandbox_dir), enforce_sandbox=True)

    with pytest.raises(PermissionError, match="Access denied"):
        fs.read_file("../secret.txt")

    with pytest.raises(PermissionError, match="Access denied"):
        fs.write_file("../forbidden.txt", "attack")


def test_tool_definitions():
    defs = get_filesystem_tool_definitions()
    names = {d.name for d in defs}
    assert "list_files" in names
    assert "read_file" in names
    assert "write_file" in names
    assert "edit_file" in names
