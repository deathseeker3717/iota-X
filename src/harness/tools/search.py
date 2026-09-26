"""Search tools for the AI Coding Harness.

Provides targeted repository search capabilities beyond basic grep:
- Content search with regex and glob filtering
- Symbol definition search (functions, classes, methods)
- Reference finding (usages across codebase)
- Import analysis (who imports what)
"""

from __future__ import annotations

import ast
import fnmatch
import os
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from harness.model.schemas import ToolDefinition
from harness.tools.filesystem import DEFAULT_EXCLUDE_PATTERNS


@dataclass
class SearchResult:
    """Result of a content search in a file."""

    file_path: str
    line_number: int
    line_content: str
    match_start: int = 0
    match_end: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SymbolMatch:
    """Result of a symbol search."""

    name: str
    symbol_type: str  # function, class, method, variable
    file_path: str
    line_number: int
    signature: str = ""
    docstring: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ReferenceMatch:
    """Result of finding references to a symbol."""

    symbol_name: str
    file_path: str
    line_number: int
    line_content: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ImportMatch:
    """Result of searching for imports."""

    imported_name: str
    module_name: str
    file_path: str
    line_number: int
    raw_statement: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class SearchTool:
    """Search operations across a repository workspace."""

    def __init__(self, root_dir: str = ".") -> None:
        self.root_dir = Path(root_dir).resolve()

    def _should_skip_dir(self, dir_name: str, rel_path: str) -> bool:
        for exc in DEFAULT_EXCLUDE_PATTERNS:
            if fnmatch.fnmatch(dir_name, exc) or fnmatch.fnmatch(rel_path, exc):
                return True
        return False

    def _iter_files(
        self,
        base_path: Path,
        file_pattern: Optional[str] = None,
    ) -> List[Path]:
        """Collect all relevant files under base_path respecting exclusions."""
        target_dir = base_path if base_path.is_dir() else base_path.parent
        if not target_dir.exists():
            return []

        matched_files: List[Path] = []
        if base_path.is_file():
            return [base_path]

        for root, dirs, files in os.walk(target_dir):
            root_p = Path(root)
            try:
                rel_root = str(root_p.relative_to(self.root_dir))
            except ValueError:
                rel_root = root

            # Filter dirs in-place
            dirs[:] = [
                d
                for d in dirs
                if not self._should_skip_dir(
                    d, f"{rel_root}/{d}".lstrip("./") if rel_root != "." else d
                )
            ]

            for file_name in files:
                rel_file = (
                    f"{rel_root}/{file_name}".lstrip("./")
                    if rel_root != "."
                    else file_name
                )
                if any(fnmatch.fnmatch(file_name, exc) for exc in DEFAULT_EXCLUDE_PATTERNS):
                    continue

                if file_pattern and not fnmatch.fnmatch(file_name, file_pattern):
                    continue

                matched_files.append(root_p / file_name)

        return matched_files

    def _read_file_safe(self, file_path: Path) -> Optional[str]:
        """Read file safely; returns None if binary or unreadable."""
        try:
            return file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            try:
                return file_path.read_text(encoding="latin-1")
            except Exception:
                return None
        except Exception:
            return None

    def search_files(
        self,
        pattern: str,
        path: str = ".",
        is_regex: bool = False,
        case_sensitive: bool = False,
        file_pattern: Optional[str] = None,
        max_results: int = 100,
    ) -> List[SearchResult]:
        """Search text across files in repository.

        Args:
            pattern: Search query or regex string.
            path: Target directory or file relative to root.
            is_regex: Whether pattern is a regular expression.
            case_sensitive: Case sensitivity.
            file_pattern: Optional glob for file names (e.g. '*.py').
            max_results: Cap on returned matches.

        Returns:
            List of SearchResult objects.
        """
        target = (self.root_dir / path).resolve()
        files = self._iter_files(target, file_pattern=file_pattern)

        flags = 0 if case_sensitive else re.IGNORECASE
        if not is_regex:
            regex_str = re.escape(pattern)
        else:
            regex_str = pattern

        try:
            compiled_re = re.compile(regex_str, flags)
        except re.error as e:
            raise ValueError(f"Invalid regular expression '{pattern}': {e}")

        results: List[SearchResult] = []
        for file_path in files:
            content = self._read_file_safe(file_path)
            if content is None:
                continue

            try:
                rel_path = str(file_path.relative_to(self.root_dir))
            except ValueError:
                rel_path = str(file_path)

            for line_no, line in enumerate(content.splitlines(), start=1):
                match = compiled_re.search(line)
                if match:
                    results.append(
                        SearchResult(
                            file_path=rel_path,
                            line_number=line_no,
                            line_content=line.strip(),
                            match_start=match.start(),
                            match_end=match.end(),
                        )
                    )
                    if len(results) >= max_results:
                        return results

        return results

    def search_symbol(
        self,
        name: str,
        symbol_type: Optional[str] = None,
        path: str = ".",
    ) -> List[SymbolMatch]:
        """Search for symbol definitions (classes, functions, methods) in codebase.

        Args:
            name: Exact symbol name or pattern substring.
            symbol_type: Optional filter: 'function', 'class', 'method'.
            path: Target directory or file relative to root.

        Returns:
            List of SymbolMatch objects.
        """
        target = (self.root_dir / path).resolve()
        files = self._iter_files(target, file_pattern="*.py")

        name_lower = name.lower()
        results: List[SymbolMatch] = []

        for file_path in files:
            content = self._read_file_safe(file_path)
            if not content:
                continue

            try:
                rel_path = str(file_path.relative_to(self.root_dir))
            except ValueError:
                rel_path = str(file_path)

            try:
                tree = ast.parse(content, filename=str(file_path))
            except SyntaxError:
                continue

            for node in ast.walk(tree):
                # Check functions / async functions
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    stype = "function"
                    # Determine if it's a method by checking if parent is a ClassDef
                    # ast.walk does not keep parent pointers, but we can do a structured visitor
                    pass

            # Structured AST traversal to detect class vs method vs function
            for node in tree.body:
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if name_lower in node.name.lower():
                        if not symbol_type or symbol_type == "function":
                            results.append(
                                SymbolMatch(
                                    name=node.name,
                                    symbol_type="function",
                                    file_path=rel_path,
                                    line_number=node.lineno,
                                    signature=self._format_func_signature(node),
                                    docstring=ast.get_docstring(node) or "",
                                )
                            )
                elif isinstance(node, ast.ClassDef):
                    if name_lower in node.name.lower():
                        if not symbol_type or symbol_type == "class":
                            results.append(
                                SymbolMatch(
                                    name=node.name,
                                    symbol_type="class",
                                    file_path=rel_path,
                                    line_number=node.lineno,
                                    signature=f"class {node.name}",
                                    docstring=ast.get_docstring(node) or "",
                                )
                            )
                    # Check methods inside class
                    for item in node.body:
                        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            if name_lower in item.name.lower() or name_lower in node.name.lower():
                                if not symbol_type or symbol_type in ("method", "function"):
                                    results.append(
                                        SymbolMatch(
                                            name=f"{node.name}.{item.name}",
                                            symbol_type="method",
                                            file_path=rel_path,
                                            line_number=item.lineno,
                                            signature=self._format_func_signature(item),
                                            docstring=ast.get_docstring(item) or "",
                                        )
                                    )

        return results

    def find_references(
        self,
        symbol_name: str,
        path: str = ".",
        max_results: int = 100,
    ) -> List[ReferenceMatch]:
        """Find references/usages of a symbol across the codebase.

        Args:
            symbol_name: Name of symbol (e.g. 'ModelGateway').
            path: Directory or file to search within.
            max_results: Max results to return.

        Returns:
            List of ReferenceMatch objects.
        """
        pattern = rf"\b{re.escape(symbol_name)}\b"
        search_res = self.search_files(
            pattern=pattern,
            path=path,
            is_regex=True,
            case_sensitive=True,
            max_results=max_results,
        )
        return [
            ReferenceMatch(
                symbol_name=symbol_name,
                file_path=res.file_path,
                line_number=res.line_number,
                line_content=res.line_content,
            )
            for res in search_res
        ]

    def find_imports(
        self,
        module_or_symbol: str,
        path: str = ".",
    ) -> List[ImportMatch]:
        """Find files and statements importing a given module or symbol.

        Args:
            module_or_symbol: Target module (e.g. 'os') or symbol (e.g. 'ModelGateway').
            path: Directory or file to search within.

        Returns:
            List of ImportMatch objects.
        """
        target = (self.root_dir / path).resolve()
        files = self._iter_files(target, file_pattern="*.py")
        results: List[ImportMatch] = []
        target_name = module_or_symbol.lower()

        for file_path in files:
            content = self._read_file_safe(file_path)
            if not content:
                continue

            try:
                rel_path = str(file_path.relative_to(self.root_dir))
            except ValueError:
                rel_path = str(file_path)

            try:
                tree = ast.parse(content, filename=str(file_path))
            except SyntaxError:
                continue

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if (
                            target_name in alias.name.lower()
                            or (alias.asname and target_name in alias.asname.lower())
                        ):
                            raw = f"import {alias.name}" + (
                                f" as {alias.asname}" if alias.asname else ""
                            )
                            results.append(
                                ImportMatch(
                                    imported_name=alias.asname or alias.name,
                                    module_name=alias.name,
                                    file_path=rel_path,
                                    line_number=node.lineno,
                                    raw_statement=raw,
                                )
                            )
                elif isinstance(node, ast.ImportFrom):
                    mod = node.module or ""
                    mod_matches = target_name in mod.lower()
                    for alias in node.names:
                        sym_matches = (
                            target_name in alias.name.lower()
                            or (alias.asname and target_name in alias.asname.lower())
                        )
                        if mod_matches or sym_matches:
                            raw = f"from {mod} import {alias.name}" + (
                                f" as {alias.asname}" if alias.asname else ""
                            )
                            results.append(
                                ImportMatch(
                                    imported_name=alias.asname or alias.name,
                                    module_name=mod,
                                    file_path=rel_path,
                                    line_number=node.lineno,
                                    raw_statement=raw,
                                )
                            )

        return results

    def _format_func_signature(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef
    ) -> str:
        """Helper to format a function's argument signature."""
        prefix = "async def " if isinstance(node, ast.AsyncFunctionDef) else "def "
        args = []
        for arg in node.args.args:
            arg_str = arg.arg
            if arg.annotation:
                try:
                    arg_str += f": {ast.unparse(arg.annotation)}"
                except Exception:
                    pass
            args.append(arg_str)

        ret = ""
        if node.returns:
            try:
                ret = f" -> {ast.unparse(node.returns)}"
            except Exception:
                pass

        return f"{prefix}{node.name}({', '.join(args)}){ret}"


# Module-level defaults
_default_search = SearchTool()


def search_files(
    pattern: str,
    path: str = ".",
    is_regex: bool = False,
    case_sensitive: bool = False,
    file_pattern: Optional[str] = None,
    max_results: int = 100,
) -> List[SearchResult]:
    return _default_search.search_files(
        pattern, path, is_regex, case_sensitive, file_pattern, max_results
    )


def search_symbol(
    name: str,
    symbol_type: Optional[str] = None,
    path: str = ".",
) -> List[SymbolMatch]:
    return _default_search.search_symbol(name, symbol_type, path)


def find_references(
    symbol_name: str,
    path: str = ".",
    max_results: int = 100,
) -> List[ReferenceMatch]:
    return _default_search.find_references(symbol_name, path, max_results)


def find_imports(
    module_or_symbol: str,
    path: str = ".",
) -> List[ImportMatch]:
    return _default_search.find_imports(module_or_symbol, path)


def get_search_tool_definitions() -> List[ToolDefinition]:
    """Return ToolDefinition schemas for search tools."""
    return [
        ToolDefinition(
            name="search_files",
            description="Search text or regex across repository files.",
            parameters={
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Search query or regex"},
                    "path": {"type": "string", "description": "Directory or file to search", "default": "."},
                    "is_regex": {"type": "boolean", "description": "Whether pattern is regex", "default": False},
                    "case_sensitive": {"type": "boolean", "description": "Case sensitivity", "default": False},
                    "file_pattern": {"type": "string", "description": "File glob pattern e.g. '*.py'"},
                    "max_results": {"type": "integer", "description": "Maximum number of results", "default": 100},
                },
                "required": ["pattern"],
            },
        ),
        ToolDefinition(
            name="search_symbol",
            description="Find function, method, or class definitions matching name.",
            parameters={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Symbol name or substring"},
                    "symbol_type": {
                        "type": "string",
                        "description": "Optional filter: 'function', 'class', 'method'",
                    },
                    "path": {"type": "string", "description": "Search root path", "default": "."},
                },
                "required": ["name"],
            },
        ),
        ToolDefinition(
            name="find_references",
            description="Find occurrences and usages of a symbol across repository.",
            parameters={
                "type": "object",
                "properties": {
                    "symbol_name": {"type": "string", "description": "Exact name of symbol"},
                    "path": {"type": "string", "description": "Search path", "default": "."},
                },
                "required": ["symbol_name"],
            },
        ),
        ToolDefinition(
            name="find_imports",
            description="Find import statements for a module or symbol.",
            parameters={
                "type": "object",
                "properties": {
                    "module_or_symbol": {
                        "type": "string",
                        "description": "Module or symbol name to search for",
                    },
                    "path": {"type": "string", "description": "Search path", "default": "."},
                },
                "required": ["module_or_symbol"],
            },
        ),
    ]
