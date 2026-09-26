"""Git tools for the AI Coding Harness.

Provides inspection and diff tools:
- git_status: Inspect working tree state, staged, unstaged, untracked files
- git_diff: View exact unified diffs of changes
- git_log: View commit history
- git_show: Inspect specific commit details or file versions

Architecture:
Client -> Git API -> Backend -> Git Tool
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from harness.model.schemas import ToolDefinition


GitChangeStatus = Literal["modified", "added", "deleted", "untracked"]


@dataclass
class GitChange:
    """Represents a changed file in the working tree or staging area."""

    file: str
    status: GitChangeStatus
    staged: bool = False
    additions: int = 0
    deletions: int = 0
    old_path: Optional[str] = None
    diff: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GitChange":
        return cls(
            file=data["file"],
            status=data.get("status", "modified"),
            staged=data.get("staged", False),
            additions=data.get("additions", 0),
            deletions=data.get("deletions", 0),
            old_path=data.get("old_path"),
            diff=data.get("diff"),
        )


@dataclass
class GitStatus:
    """Structured representation of repository working tree status."""

    branch: str
    is_clean: bool
    changes: List[GitChange] = field(default_factory=list)
    staged_files: List[str] = field(default_factory=list)
    unstaged_files: List[str] = field(default_factory=list)
    untracked_files: List[str] = field(default_factory=list)
    ahead: int = 0
    behind: int = 0
    raw_output: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "branch": self.branch,
            "is_clean": self.is_clean,
            "changes": [c.to_dict() for c in self.changes],
            "staged_files": self.staged_files,
            "unstaged_files": self.unstaged_files,
            "untracked_files": self.untracked_files,
            "ahead": self.ahead,
            "behind": self.behind,
            "raw_output": self.raw_output,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GitStatus":
        changes = [
            GitChange.from_dict(c) if isinstance(c, dict) else c
            for c in data.get("changes", [])
        ]
        return cls(
            branch=data.get("branch", "unknown"),
            is_clean=data.get("is_clean", True),
            changes=changes,
            staged_files=data.get("staged_files", []),
            unstaged_files=data.get("unstaged_files", []),
            untracked_files=data.get("untracked_files", []),
            ahead=data.get("ahead", 0),
            behind=data.get("behind", 0),
            raw_output=data.get("raw_output", ""),
        )

    @property
    def added_files(self) -> List[GitChange]:
        return [c for c in self.changes if c.status == "added"]

    @property
    def modified_files(self) -> List[GitChange]:
        return [c for c in self.changes if c.status == "modified"]

    @property
    def deleted_files(self) -> List[GitChange]:
        return [c for c in self.changes if c.status == "deleted"]


# Alias for backward compatibility
GitStatusResult = GitStatus


@dataclass
class GitDiff:
    """Structured representation of a unified Git diff."""

    file_path: Optional[str] = None
    staged: bool = False
    commit: Optional[str] = None
    diff_text: str = ""
    additions: int = 0
    deletions: int = 0
    changes: List[GitChange] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_path": self.file_path,
            "staged": self.staged,
            "commit": self.commit,
            "diff_text": self.diff_text,
            "additions": self.additions,
            "deletions": self.deletions,
            "changes": [c.to_dict() for c in self.changes],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GitDiff":
        changes = [
            GitChange.from_dict(c) if isinstance(c, dict) else c
            for c in data.get("changes", [])
        ]
        return cls(
            file_path=data.get("file_path"),
            staged=data.get("staged", False),
            commit=data.get("commit"),
            diff_text=data.get("diff_text", ""),
            additions=data.get("additions", 0),
            deletions=data.get("deletions", 0),
            changes=changes,
        )


@dataclass
class GitCommit:
    """Structured Git commit log entry."""

    hash: str
    short_hash: str
    author: str
    date: str
    message: str
    parent_hashes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GitCommit":
        return cls(
            hash=data["hash"],
            short_hash=data.get("short_hash", data["hash"][:7]),
            author=data.get("author", "unknown"),
            date=data.get("date", ""),
            message=data.get("message", ""),
            parent_hashes=data.get("parent_hashes", []),
        )


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

    def _count_diff_stats(self, diff_text: str) -> tuple[int, int]:
        """Count line additions and deletions from a unified diff text."""
        additions = 0
        deletions = 0
        for line in diff_text.splitlines():
            if line.startswith("+") and not line.startswith("+++"):
                additions += 1
            elif line.startswith("-") and not line.startswith("---"):
                deletions += 1
        return additions, deletions

    def git_status(self) -> GitStatus:
        """Inspect the current working directory status."""
        if not self.is_git_repository():
            return GitStatus(
                branch="unknown",
                is_clean=True,
                changes=[],
                staged_files=[],
                unstaged_files=[],
                untracked_files=[],
                raw_output="Not a git repository",
            )

        code, stdout, stderr = self._run_git(["status", "--porcelain=v1", "-b"])
        if code != 0:
            return GitStatus(
                branch="unknown",
                is_clean=False,
                changes=[],
                staged_files=[],
                unstaged_files=[],
                untracked_files=[],
                raw_output=stderr or stdout,
            )

        lines = stdout.splitlines()
        branch = "HEAD"
        ahead = 0
        behind = 0
        staged: List[str] = []
        unstaged: List[str] = []
        untracked: List[str] = []
        changes: List[GitChange] = []

        for line in lines:
            if line.startswith("## "):
                # Branch line: e.g. "## main...origin/main [ahead 1, behind 2]"
                branch_header = line[3:].strip()
                branch_part = branch_header.split("...")[0].strip()
                branch = branch_part

                # Extract ahead/behind if present
                ahead_match = re.search(r"ahead (\d+)", branch_header)
                behind_match = re.search(r"behind (\d+)", branch_header)
                if ahead_match:
                    ahead = int(ahead_match.group(1))
                if behind_match:
                    behind = int(behind_match.group(1))
                continue

            if len(line) < 3:
                continue

            index_status = line[0]
            worktree_status = line[1]
            file_name = line[3:].strip()

            # Handle renames (e.g. "R  old -> new")
            old_path = None
            if " -> " in file_name:
                old_path, file_name = file_name.split(" -> ", 1)

            if index_status == "?" and worktree_status == "?":
                untracked.append(file_name)
                changes.append(
                    GitChange(
                        file=file_name,
                        status="untracked",
                        staged=False,
                    )
                )
            else:
                # Staged change
                if index_status not in (" ", "?"):
                    staged.append(file_name)
                    staged_status: GitChangeStatus = "modified"
                    if index_status == "A":
                        staged_status = "added"
                    elif index_status == "D":
                        staged_status = "deleted"

                    changes.append(
                        GitChange(
                            file=file_name,
                            status=staged_status,
                            staged=True,
                            old_path=old_path,
                        )
                    )

                # Unstaged working tree change
                if worktree_status not in (" ", "?"):
                    unstaged.append(file_name)
                    unstaged_status: GitChangeStatus = "modified"
                    if worktree_status == "A":
                        unstaged_status = "added"
                    elif worktree_status == "D":
                        unstaged_status = "deleted"

                    changes.append(
                        GitChange(
                            file=file_name,
                            status=unstaged_status,
                            staged=False,
                            old_path=old_path,
                        )
                    )

        is_clean = len(staged) == 0 and len(unstaged) == 0 and len(untracked) == 0

        # Attach additions/deletions stats to changes where diff is available
        for c in changes:
            try:
                diff_out = self.git_diff(staged=c.staged, file_path=c.file)
                if isinstance(diff_out, GitDiff):
                    c.additions = diff_out.additions
                    c.deletions = diff_out.deletions
                    c.diff = diff_out.diff_text
            except Exception:
                pass

        return GitStatus(
            branch=branch,
            is_clean=is_clean,
            changes=changes,
            staged_files=sorted(list(set(staged))),
            unstaged_files=sorted(list(set(unstaged))),
            untracked_files=sorted(untracked),
            ahead=ahead,
            behind=behind,
            raw_output=stdout,
        )

    def git_diff(
        self,
        staged: bool = False,
        file_path: Optional[str] = None,
        commit: Optional[str] = None,
    ) -> GitDiff:
        """Get git unified diff of current changes."""
        if not self.is_git_repository():
            return GitDiff(
                file_path=file_path,
                staged=staged,
                commit=commit,
                diff_text="Not a git repository.",
            )

        args = ["diff"]
        if staged:
            args.append("--staged")
        if commit:
            args.append(commit)
        if file_path:
            args.extend(["--", file_path])

        code, stdout, stderr = self._run_git(args)
        diff_text = stdout if code == 0 else f"Error running git diff: {stderr}"
        additions, deletions = self._count_diff_stats(diff_text)

        return GitDiff(
            file_path=file_path,
            staged=staged,
            commit=commit,
            diff_text=diff_text,
            additions=additions,
            deletions=deletions,
        )

    def git_log(
        self,
        max_count: int = 10,
        file_path: Optional[str] = None,
    ) -> List[GitCommit]:
        """Get commit history."""
        if not self.is_git_repository():
            return []

        # %H=hash, %h=short_hash, %an=author, %ae=email, %ad=date, %s=subject, %P=parent_hashes
        fmt = "%H%x1f%h%x1f%an <%ae>%x1f%ad%x1f%s%x1f%P"
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
                parents = parts[5].split() if len(parts) > 5 and parts[5].strip() else []
                commits.append(
                    GitCommit(
                        hash=parts[0],
                        short_hash=parts[1],
                        author=parts[2],
                        date=parts[3],
                        message=parts[4],
                        parent_hashes=parents,
                    )
                )

        return commits

    def git_show(
        self,
        commit_or_ref: str = "HEAD",
        file_path: Optional[str] = None,
    ) -> str:
        """Inspect a specific commit or view a file at a specific git ref."""
        if not self.is_git_repository():
            return "Not a git repository."

        target = f"{commit_or_ref}:{file_path}" if file_path else commit_or_ref
        code, stdout, stderr = self._run_git(["show", target])
        if code != 0:
            return f"Error running git show: {stderr}"
        return stdout


# Module-level default instance
_default_git = GitTool()


def git_status() -> GitStatus:
    return _default_git.git_status()


def git_diff(
    staged: bool = False,
    file_path: Optional[str] = None,
    commit: Optional[str] = None,
) -> GitDiff:
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
