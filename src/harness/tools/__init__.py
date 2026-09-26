"""Tools package public exports for AI Coding Harness."""

from harness.tools.filesystem import (
    DEFAULT_EXCLUDE_PATTERNS,
    FilesystemTool,
    edit_file,
    get_filesystem_tool_definitions,
    list_files,
    read_file,
    write_file,
)
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
from harness.tools.search import (
    ImportMatch,
    ReferenceMatch,
    SearchResult,
    SearchTool,
    SymbolMatch,
    find_imports,
    find_references,
    get_search_tool_definitions,
    search_files,
    search_symbol,
)
from harness.tools.shell import (
    CommandResult,
    ShellTool,
    execute_command,
    get_shell_tool_definitions,
)
from harness.tools.tests import (
    TestCaseResult,
    TestSuiteResult,
    TestRunnerTool,
    get_test_tool_definitions,
    run_tests,
)
from harness.model.schemas import ToolDefinition
from typing import Any, Callable, Dict, List, Optional
from pathlib import Path
import json


class ToolRegistry:
    """Unified tool registry for dispatching model tool calls."""

    def __init__(self, root_dir: str = ".") -> None:
        self.root_dir = Path(root_dir).resolve()
        self.filesystem = FilesystemTool(root_dir=str(self.root_dir))
        self.search = SearchTool(root_dir=str(self.root_dir))
        self.shell = ShellTool(working_dir=str(self.root_dir))
        self.git = GitTool(repo_dir=str(self.root_dir))
        self.tests = TestRunnerTool(repo_dir=str(self.root_dir), shell_tool=self.shell)

        self._dispatch_map: Dict[str, Callable[..., Any]] = {
            # Filesystem
            "list_files": self.filesystem.list_files,
            "read_file": self.filesystem.read_file,
            "write_file": self.filesystem.write_file,
            "edit_file": self.filesystem.edit_file,
            # Search
            "search_files": self.search.search_files,
            "search_symbol": self.search.search_symbol,
            "find_references": self.search.find_references,
            "find_imports": self.search.find_imports,
            # Shell
            "execute_command": self.shell.execute,
            # Git
            "git_status": self.git.git_status,
            "git_diff": self.git.git_diff,
            "git_log": self.git.git_log,
            "git_show": self.git.git_show,
            # Tests
            "run_tests": self.tests.run_tests,
        }

    def get_tool_definitions(self) -> List[ToolDefinition]:
        """Aggregate all tool definitions for ModelGateway."""
        defs: List[ToolDefinition] = []
        defs.extend(get_filesystem_tool_definitions())
        defs.extend(get_search_tool_definitions())
        defs.extend(get_shell_tool_definitions())
        defs.extend(get_git_tool_definitions())
        defs.extend(get_test_tool_definitions())
        return defs

    def execute(self, tool_name: str, arguments: Optional[Dict[str, Any]] = None) -> Any:
        """Execute a tool by name with arguments dict."""
        handler = self._dispatch_map.get(tool_name)
        if not handler:
            raise ValueError(f"Unknown tool: '{tool_name}'")

        args = arguments or {}
        try:
            result = handler(**args)
            return result
        except Exception as e:
            return {"error": f"Tool execution failed: {type(e).__name__}: {e}"}


__all__ = [
    # Filesystem
    "FilesystemTool",
    "list_files",
    "read_file",
    "write_file",
    "edit_file",
    "DEFAULT_EXCLUDE_PATTERNS",
    "get_filesystem_tool_definitions",
    # Search
    "SearchTool",
    "SearchResult",
    "SymbolMatch",
    "ReferenceMatch",
    "ImportMatch",
    "search_files",
    "search_symbol",
    "find_references",
    "find_imports",
    "get_search_tool_definitions",
    # Shell
    "ShellTool",
    "CommandResult",
    "execute_command",
    "get_shell_tool_definitions",
    # Git
    "GitTool",
    "GitStatus",
    "GitStatusResult",
    "GitChange",
    "GitDiff",
    "GitCommit",
    "git_status",
    "git_diff",
    "git_log",
    "git_show",
    "get_git_tool_definitions",
    # Tests
    "TestRunnerTool",
    "TestCaseResult",
    "TestSuiteResult",
    "run_tests",
    "get_test_tool_definitions",
    # Registry
    "ToolRegistry",
]
