"""Git tools for the AI Coding Harness.

Provides inspection and diff tools:
- git_status: Inspect working tree state, staged, unstaged, untracked files
- git_diff: View exact unified diffs of changes
- git_log: View commit history
- git_show: Inspect specific commit details or file versions
"""

from __future__ import annotations

import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from harness.model.schemas import ToolDefinition


@dataclass
class GitStatusResult:
    """Structured representation of repository status."""

    branch: str
    is_clean: bool
    staged_files: List[str]
    unstaged_files: List[str]
    untracked_files: List[str]
    raw_output: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class GitCommit:
    """Structured Git commit log entry."""

    hash: str
    short_hash: str
    author: str
    date: str
    message: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class GitTool:
    """Git repository inspection and history tool."""

    def __init__(self, repo_dir: str = ".") -> None:
        self.repo_dir = Path(repo_dir).resolve()

    def _run_git(self, args: List[str], timeout: float = 30.0) -> tuple[int, str, str]:
        """Run a git command in the repository directory."""
        try:
            res = subprocess.run(
                ["git"] + args,
                cwd=self.repo_dir,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return res.returncode, res.stdout, res.stderr
        except FileNotFoundError:
            return -1, "", "git executable not found on system PATH."
        except Exception as e:
            return -1, "", f"Git command failed: {e}"

    def is_git_repository(self) -> bool:
        """Check if target directory is inside a Git repository."""
        code, stdout, _ = self._run_git(["rev-parse", "--is-inside-work-tree"])
        return code == 0 and "true" in stdout.strip()

    def git_status(self) -> GitStatusResult:
        """Inspect the current working directory status."""
        if not self.is_git_repository():
            return GitStatusResult(
                branch="unknown",
                is_clean=True,
                staged_files=[],
                unstaged_files=[],
                untracked_files=[],
                raw_output="Not a git repository",
            )

        code, stdout, stderr = self._run_git(["status", "--porcelain=v1", "-b"])
        if code != 0:
            return GitStatusResult(
                branch="unknown",
                is_clean=False,
                staged_files=[],
                unstaged_files=[],
                untracked_files=[],
                raw_output=stderr or stdout,
            )

        lines = stdout.splitlines()
        branch = "HEAD"
        staged: List[str] = []
        unstaged: List[str] = []
        untracked: List[str] = []

        for line in lines:
            if line.startswith("## "):
                # Branch line: e.g. "## main...origin/main [ahead 1]"
                branch_info = line[3:].split("...")[0].strip()
                branch = branch_info
                continue

            if len(line) < 3:
                continue

            index_status = line[0]
            worktree_status = line[1]
            file_name = line[3:].strip()

            if index_status == "?" and worktree_status == "?":
                untracked.append(file_name)
            else:
                if index_status not in (" ", "?"):
                    staged.append(file_name)
                if worktree_status not in (" ", "?"):
                    unstaged.append(file_name)

        is_clean = len(staged) == 0 and len(unstaged) == 0 and len(untracked) == 0

        return GitStatusResult(
            branch=branch,
            is_clean=is_clean,
            staged_files=sorted(list(set(staged))),
            unstaged_files=sorted(list(set(unstaged))),
            untracked_files=sorted(untracked),
            raw_output=stdout,
        )

    def git_diff(
        self,
        staged: bool = False,
        file_path: Optional[str] = None,
        commit: Optional[str] = None,
    ) -> str:
        """Get git unified diff of current changes.

        Args:
            staged: If True, show diff of staged changes (--staged).
            file_path: Optional specific file path to diff.
            commit: Optional commit hash or ref to diff against.

        Returns:
            Unified diff text.
        """
        if not self.is_git_repository():
            return "Not a git repository."

        args = ["diff"]
        if staged:
            args.append("--staged")
        if commit:
            args.append(commit)
        if file_path:
            args.extend(["--", file_path])

        code, stdout, stderr = self._run_git(args)
        if code != 0:
            return f"Error running git diff: {stderr}"
        return stdout

    def git_log(
        self,
        max_count: int = 10,
        file_path: Optional[str] = None,
    ) -> List[GitCommit]:
        """Get commit history.

        Args:
            max_count: Number of commits to retrieve (default: 10).
            file_path: Optional file path to filter history.

        Returns:
            List of GitCommit objects.
        """
        if not self.is_git_repository():
            return []

        # Use unit separator %x1f to split fields safely
        fmt = "%H%x1f%h%x1f%an <%ae>%x1f%ad%x1f%s"
        args = ["log", f"-n{max_count}", f"--format={fmt}", "--date=short"]
        if file_path:
            args.extend(["--", file_path])

        code, stdout, _ = self._run_git(args)
        if code != 0 or not stdout.strip():
            return []

        commits: List[GitCommit] = []
        for line in stdout.splitlines():
            parts = line.split("\x1f")
            if len(parts) >= 5:
                commits.append(
                    GitCommit(
                        hash=parts[0],
                        short_hash=parts[1],
                        author=parts[2],
                        date=parts[3],
                        message=parts[4],
                    )
                )

        return commits

    def git_show(
        self,
        commit_or_ref: str = "HEAD",
        file_path: Optional[str] = None,
    ) -> str:
        """Inspect a specific commit or view a file at a specific git ref.

        Args:
            commit_or_ref: Commit hash, tag, or branch (default: 'HEAD').
            file_path: Optional path to show specific file version at that ref.

        Returns:
            Commit details or file content at specified ref.
        """
        if not self.is_git_repository():
            return "Not a git repository."

        target = f"{commit_or_ref}:{file_path}" if file_path else commit_or_ref
        code, stdout, stderr = self._run_git(["show", target])
        if code != 0:
            return f"Error running git show: {stderr}"
        return stdout


# Module-level default instance
_default_git = GitTool()


def git_status() -> GitStatusResult:
    return _default_git.git_status()


def git_diff(
    staged: bool = False,
    file_path: Optional[str] = None,
    commit: Optional[str] = None,
) -> str:
    return _default_git.git_diff(staged, file_path, commit)


def git_log(
    max_count: int = 10,
    file_path: Optional[str] = None,
) -> List[GitCommit]:
    return _default_git.git_log(max_count, file_path)


def git_show(
    commit_or_ref: str = "HEAD",
    file_path: Optional[str] = None,
) -> str:
    return _default_git.git_show(commit_or_ref, file_path)


def get_git_tool_definitions() -> List[ToolDefinition]:
    """Return ToolDefinition schemas for git tools."""
    return [
        ToolDefinition(
            name="git_status",
            description="Get the git status: current branch, staged, unstaged, and untracked files.",
            parameters={"type": "object", "properties": {}},
        ),
        ToolDefinition(
            name="git_diff",
            description="View unified git diff of unstaged or staged changes.",
            parameters={
                "type": "object",
                "properties": {
                    "staged": {
                        "type": "boolean",
                        "description": "Show staged diff if true (default: false)",
                        "default": False,
                    },
                    "file_path": {
                        "type": "string",
                        "description": "Optional file path filter",
                    },
                    "commit": {
                        "type": "string",
                        "description": "Optional commit to diff against",
                    },
                },
            },
        ),
        ToolDefinition(
            name="git_log",
            description="View recent git commit history.",
            parameters={
                "type": "object",
                "properties": {
                    "max_count": {
                        "type": "integer",
                        "description": "Max commits to return (default: 10)",
                        "default": 10,
                    },
                    "file_path": {
                        "type": "string",
                        "description": "Optional file path filter",
                    },
                },
            },
        ),
        ToolDefinition(
            name="git_show",
            description="Inspect a git commit or view a file at a specific commit/ref.",
            parameters={
                "type": "object",
                "properties": {
                    "commit_or_ref": {
                        "type": "string",
                        "description": "Commit hash, ref or tag (default: 'HEAD')",
                        "default": "HEAD",
                    },
                    "file_path": {
                        "type": "string",
                        "description": "Optional file path relative to repo root",
                    },
                },
            },
        ),
    ]
