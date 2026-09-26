"""Filesystem tools for the AI Coding Harness.

Provides safe, sandboxed file operations: listing, reading, writing, and editing files.
"""

from __future__ import annotations

import fnmatch
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from harness.model.schemas import ToolDefinition

DEFAULT_EXCLUDE_PATTERNS = [
    ".git",
    ".git/*",
    "*.pyc",
    "__pycache__",
    "__pycache__/*",
    ".venv",
    ".venv/*",
    "venv",
    "venv/*",
    "node_modules",
    "node_modules/*",
    ".pytest_cache",
    ".pytest_cache/*",
    "*.egg-info",
    "*.egg-info/*",
    ".coverage",
    "htmlcov",
    "htmlcov/*",
    "build",
    "build/*",
    "dist",
    "dist/*",
]


class FilesystemTool:
    """Provides sandboxed filesystem operations."""

    def __init__(self, root_dir: str = ".", enforce_sandbox: bool = True) -> None:
        self.root_dir = Path(root_dir).resolve()
        self.enforce_sandbox = enforce_sandbox

    def _resolve_path(self, relative_or_absolute: str) -> Path:
        """Resolve a path safely within the sandbox root directory."""
        path = Path(relative_or_absolute)
        if not path.is_absolute():
            resolved = (self.root_dir / path).resolve()
        else:
            resolved = path.resolve()

        if self.enforce_sandbox:
            try:
                resolved.relative_to(self.root_dir)
            except ValueError:
                raise PermissionError(
                    f"Access denied: Path '{relative_or_absolute}' is outside sandbox root '{self.root_dir}'"
                )
        return resolved

    def _to_rel_path(self, path: Path) -> str:
        """Convert an absolute path to a relative path from root_dir if possible."""
        try:
            return str(path.relative_to(self.root_dir))
        except ValueError:
            return str(path)

    def list_files(
        self,
        directory: str = ".",
        recursive: bool = True,
        pattern: Optional[str] = None,
        exclude_patterns: Optional[List[str]] = None,
    ) -> List[str]:
        """List files in the specified directory.

        Args:
            directory: Directory path relative to root_dir.
            recursive: Whether to list files recursively.
            pattern: Optional glob pattern to match (e.g. '*.py').
            exclude_patterns: Optional list of glob patterns to exclude.

        Returns:
            Sorted list of relative file paths.
        """
        target_dir = self._resolve_path(directory)
        if not target_dir.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")
        if not target_dir.is_dir():
            raise NotADirectoryError(f"Path is not a directory: {directory}")

        excludes = list(DEFAULT_EXCLUDE_PATTERNS)
        if exclude_patterns:
            excludes.extend(exclude_patterns)

        results: List[str] = []

        if recursive:
            for root, dirs, files in os.walk(target_dir):
                root_path = Path(root)
                rel_root = self._to_rel_path(root_path)

                # Filter directories in-place to avoid descending into ignored trees
                filtered_dirs = []
                for d in dirs:
                    d_rel = (
                        f"{rel_root}/{d}".lstrip("./")
                        if rel_root != "."
                        else d
                    )
                    should_skip = any(
                        fnmatch.fnmatch(d, exc) or fnmatch.fnmatch(d_rel, exc)
                        for exc in excludes
                    )
                    if not should_skip:
                        filtered_dirs.append(d)
                dirs[:] = filtered_dirs

                for file_name in files:
                    file_path = root_path / file_name
                    rel_file = self._to_rel_path(file_path)

                    should_skip = any(
                        fnmatch.fnmatch(file_name, exc)
                        or fnmatch.fnmatch(rel_file, exc)
                        for exc in excludes
                    )
                    if should_skip:
                        continue

                    if pattern and not fnmatch.fnmatch(file_name, pattern):
                        continue

                    results.append(rel_file)
        else:
            for entry in target_dir.iterdir():
                if entry.is_file():
                    rel_file = self._to_rel_path(entry)
                    should_skip = any(
                        fnmatch.fnmatch(entry.name, exc)
                        or fnmatch.fnmatch(rel_file, exc)
                        for exc in excludes
                    )
                    if should_skip:
                        continue
                    if pattern and not fnmatch.fnmatch(entry.name, pattern):
                        continue
                    results.append(rel_file)

        return sorted(results)

    def read_file(
        self,
        path: str,
        start_line: Optional[int] = None,
        end_line: Optional[int] = None,
        max_lines: Optional[int] = None,
    ) -> str:
        """Read content from a file, optionally within line bounds (1-indexed).

        Args:
            path: File path relative to root_dir.
            start_line: Optional starting line number (1-based, inclusive).
            end_line: Optional ending line number (1-based, inclusive).
            max_lines: Optional maximum lines to return.

        Returns:
            String content of the file or requested slice.
        """
        file_path = self._resolve_path(path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        if not file_path.is_file():
            raise IsADirectoryError(f"Path is a directory, not a file: {path}")

        try:
            content = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            content = file_path.read_text(encoding="latin-1", errors="replace")

        lines = content.splitlines(keepends=True)
        total_lines = len(lines)

        s = (start_line - 1) if (start_line is not None and start_line > 0) else 0
        e = end_line if (end_line is not None and end_line > 0) else total_lines

        selected_lines = lines[s:e]
        if max_lines is not None and len(selected_lines) > max_lines:
            truncated_count = len(selected_lines) - max_lines
            selected_lines = selected_lines[:max_lines]
            selected_lines.append(f"\n... [Truncated: {truncated_count} more lines]\n")

        return "".join(selected_lines)

    def write_file(self, path: str, content: str, create_dirs: bool = True) -> bool:
        """Write content to a file, optionally creating parent directories.

        Args:
            path: Target file path relative to root_dir.
            content: Content to write.
            create_dirs: Whether to create missing parent directories.

        Returns:
            True on success.
        """
        file_path = self._resolve_path(path)
        if create_dirs:
            file_path.parent.mkdir(parents=True, exist_ok=True)
        elif not file_path.parent.exists():
            raise FileNotFoundError(
                f"Parent directory does not exist for: {path}"
            )

        file_path.write_text(content, encoding="utf-8")
        return True

    def edit_file(
        self,
        path: str,
        target: str,
        replacement: str,
        allow_multiple: bool = False,
    ) -> bool:
        """Edit a file by replacing occurrences of target string with replacement.

        Args:
            path: Target file path relative to root_dir.
            target: Exact text block to locate and replace.
            replacement: New text to put in place of target.
            allow_multiple: If False, enforces that target appears exactly once.

        Returns:
            True on successful edit.

        Raises:
            ValueError: If target is not found or occurs multiple times when allow_multiple is False.
        """
        file_path = self._resolve_path(path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        content = file_path.read_text(encoding="utf-8")
        occurrences = content.count(target)

        if occurrences == 0:
            raise ValueError(
                f"Target string not found in '{path}'. Make sure whitespace and formatting match exactly."
            )
        if occurrences > 1 and not allow_multiple:
            raise ValueError(
                f"Target string found {occurrences} times in '{path}'. "
                "Provide more surrounding context to make target unique, or pass allow_multiple=True."
            )

        new_content = (
            content.replace(target, replacement)
            if allow_multiple
            else content.replace(target, replacement, 1)
        )
        file_path.write_text(new_content, encoding="utf-8")
        return True


# Default instance and module-level helpers
_default_fs = FilesystemTool()


def list_files(
    directory: str = ".",
    recursive: bool = True,
    pattern: Optional[str] = None,
    exclude_patterns: Optional[List[str]] = None,
) -> List[str]:
    """List files in the directory."""
    return _default_fs.list_files(directory, recursive, pattern, exclude_patterns)


def read_file(
    path: str,
    start_line: Optional[int] = None,
    end_line: Optional[int] = None,
    max_lines: Optional[int] = None,
) -> str:
    """Read file content."""
    return _default_fs.read_file(path, start_line, end_line, max_lines)


def write_file(path: str, content: str, create_dirs: bool = True) -> bool:
    """Write content to file."""
    return _default_fs.write_file(path, content, create_dirs)


def edit_file(
    path: str, target: str, replacement: str, allow_multiple: bool = False
) -> bool:
    """Edit file with string replacement."""
    return _default_fs.edit_file(path, target, replacement, allow_multiple)


def get_filesystem_tool_definitions() -> List[ToolDefinition]:
    """Return ToolDefinition schemas for filesystem tools for LLM use."""
    return [
        ToolDefinition(
            name="list_files",
            description="List files in a directory with glob filtering and default exclusions for build/cache dirs.",
            parameters={
                "type": "object",
                "properties": {
                    "directory": {
                        "type": "string",
                        "description": "Directory path to list (default: '.')",
                        "default": ".",
                    },
                    "recursive": {
                        "type": "boolean",
                        "description": "Whether to list recursively (default: true)",
                        "default": True,
                    },
                    "pattern": {
                        "type": "string",
                        "description": "Optional glob pattern filter, e.g. '*.py'",
                    },
                },
            },
        ),
        ToolDefinition(
            name="read_file",
            description="Read file content with optional line-range slicing (1-indexed).",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative file path"},
                    "start_line": {
                        "type": "integer",
                        "description": "Starting line number (1-based, inclusive)",
                    },
                    "end_line": {
                        "type": "integer",
                        "description": "Ending line number (1-based, inclusive)",
                    },
                    "max_lines": {
                        "type": "integer",
                        "description": "Maximum number of lines to return",
                    },
                },
                "required": ["path"],
            },
        ),
        ToolDefinition(
            name="write_file",
            description="Write full content to a file, creating parent directories if needed.",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative file path"},
                    "content": {"type": "string", "description": "Text content to write"},
                    "create_dirs": {
                        "type": "boolean",
                        "description": "Whether to create parent directories",
                        "default": True,
                    },
                },
                "required": ["path", "content"],
            },
        ),
        ToolDefinition(
            name="edit_file",
            description="Perform a precise targeted replacement in a file.",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative file path"},
                    "target": {"type": "string", "description": "Exact text to replace"},
                    "replacement": {
                        "type": "string",
                        "description": "Replacement text",
                    },
                    "allow_multiple": {
                        "type": "boolean",
                        "description": "Allow replacing multiple matches",
                        "default": False,
                    },
                },
                "required": ["path", "target", "replacement"],
            },
        ),
    ]
