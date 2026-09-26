"""Unit tests for the GitTool and shared Git models."""

import subprocess
import pytest
from pathlib import Path
from harness.tools.git import (
    GitChange,
    GitCommit,
    GitDiff,
    GitStatus,
    GitStatusResult,
    GitTool,
    get_git_tool_definitions,
    git_diff,
    git_log,
    git_show,
    git_status,
)


def test_git_models_serialization():
    # GitChange
    change = GitChange(
        file="src/harness/main.py",
        status="modified",
        staged=False,
        additions=12,
        deletions=3,
        diff="@@ -1,3 +1,12 @@",
    )
    change_dict = change.to_dict()
    assert change_dict["file"] == "src/harness/main.py"
    assert change_dict["status"] == "modified"
    assert change_dict["additions"] == 12
    restored_change = GitChange.from_dict(change_dict)
    assert restored_change.file == change.file

    # GitStatus
    status = GitStatus(
        branch="context-observability",
        is_clean=False,
        changes=[change],
        staged_files=[],
        unstaged_files=["src/harness/main.py"],
        untracked_files=[],
        ahead=1,
        behind=0,
    )
    status_dict = status.to_dict()
    assert status_dict["branch"] == "context-observability"
    assert len(status_dict["changes"]) == 1
    assert len(status.modified_files) == 1
    assert len(status.added_files) == 0

    restored_status = GitStatus.from_dict(status_dict)
    assert restored_status.branch == "context-observability"
    assert len(restored_status.changes) == 1

    # GitDiff
    diff = GitDiff(
        file_path="src/harness/main.py",
        staged=False,
        diff_text="--- a/main.py\n+++ b/main.py\n+import sys",
        additions=1,
        deletions=0,
    )
    diff_dict = diff.to_dict()
    assert diff_dict["additions"] == 1
    restored_diff = GitDiff.from_dict(diff_dict)
    assert restored_diff.diff_text == diff.diff_text

    # GitCommit
    commit = GitCommit(
        hash="c097d45123456789",
        short_hash="c097d45",
        author="Aryan Goyal <aryan@example.com>",
        date="2026-09-27",
        message="feat: context manager",
    )
    commit_dict = commit.to_dict()
    assert commit_dict["short_hash"] == "c097d45"
    restored_commit = GitCommit.from_dict(commit_dict)
    assert restored_commit.message == "feat: context manager"


def test_git_tool_in_real_repo():
    # The workspace itself is a git repository
    gt = GitTool()
    assert gt.is_git_repository() is True

    status = gt.git_status()
    assert status.branch != "unknown"
    assert isinstance(status.is_clean, bool)
    assert isinstance(status.staged_files, list)
    assert isinstance(status.unstaged_files, list)
    assert isinstance(status.changes, list)

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
    assert len(status1.changes) == 1
    assert status1.changes[0].status == "untracked"

    # Stage and commit
    subprocess.run(["git", "add", "hello.txt"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=tmp_path, check=True)

    status2 = gt.git_status()
    assert status2.is_clean is True

    # Modify file -> test diff
    test_file.write_text("initial content\nmodified line\n")
    diff = gt.git_diff()
    assert isinstance(diff, GitDiff)
    assert "+modified line" in diff.diff_text
    assert diff.additions >= 1

    # Stage modification -> test staged diff
    subprocess.run(["git", "add", "hello.txt"], cwd=tmp_path, check=True)
    staged_diff = gt.git_diff(staged=True)
    assert "+modified line" in staged_diff.diff_text

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
