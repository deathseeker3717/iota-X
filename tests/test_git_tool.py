"""Unit tests for the GitTool."""

import subprocess
import pytest
from pathlib import Path
from harness.tools.git import (
    GitTool,
    get_git_tool_definitions,
    git_status,
    git_diff,
    git_log,
    git_show,
)


def test_git_tool_in_real_repo():
    # The workspace itself is a git repository
    gt = GitTool()
    assert gt.is_git_repository() is True

    status = gt.git_status()
    assert status.branch != "unknown"
    assert isinstance(status.is_clean, bool)
    assert isinstance(status.staged_files, list)
    assert isinstance(status.unstaged_files, list)

    log = gt.git_log(max_count=2)
    assert isinstance(log, list)
    if log:
        assert len(log[0].hash) > 0
        assert len(log[0].short_hash) > 0
        assert len(log[0].author) > 0


def test_git_tool_in_temp_git_repo(tmp_path):
    # Initialize a temporary git repo to test commits and diffs
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "TestUser"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True)

    gt = GitTool(repo_dir=str(tmp_path))
    assert gt.is_git_repository() is True

    # Untracked file
    test_file = tmp_path / "hello.txt"
    test_file.write_text("initial content\n")

    status1 = gt.git_status()
    assert "hello.txt" in status1.untracked_files
    assert status1.is_clean is False

    # Stage and commit
    subprocess.run(["git", "add", "hello.txt"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=tmp_path, check=True)

    status2 = gt.git_status()
    assert status2.is_clean is True

    # Modify file -> test diff
    test_file.write_text("initial content\nmodified line\n")
    diff = gt.git_diff()
    assert "+modified line" in diff

    # Stage modification -> test staged diff
    subprocess.run(["git", "add", "hello.txt"], cwd=tmp_path, check=True)
    staged_diff = gt.git_diff(staged=True)
    assert "+modified line" in staged_diff

    # Log
    log = gt.git_log(max_count=5)
    assert len(log) == 1
    assert log[0].message == "Initial commit"
    assert log[0].author == "TestUser <test@example.com>"

    # Show
    show_res = gt.git_show("HEAD")
    assert "Initial commit" in show_res


def test_git_tool_definitions():
    defs = get_git_tool_definitions()
    names = {d.name for d in defs}
    assert "git_status" in names
    assert "git_diff" in names
    assert "git_log" in names
    assert "git_show" in names
