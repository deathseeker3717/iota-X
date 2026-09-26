"""Repository indexer for the AI Coding Harness.

Builds an inverted index of:
- files
- functions and classes
- imports and dependency graphs
- cross-file symbol references
- full-text token inverted index
"""

from __future__ import annotations

import fnmatch
import hashlib
import os
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from harness.repository.symbols import (
    FileSymbols,
    ImportItem,
    Symbol,
    SymbolExtractor,
    SymbolType,
)
from harness.tools.filesystem import DEFAULT_EXCLUDE_PATTERNS

SUPPORTED_CODE_EXTENSIONS = {
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".md",
    ".sh",
    ".sql",
    ".html",
    ".css",
}


@dataclass
class FileIndexEntry:
    """Index entry for a single file."""

    file_path: str
    mtime: float
    size_bytes: int
    content_hash: str
    line_count: int
    symbols: List[Symbol] = field(default_factory=list)
    imports: List[ImportItem] = field(default_factory=list)
    tokens: Set[str] = field(default_factory=set)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_path": self.file_path,
            "mtime": self.mtime,
            "size_bytes": self.size_bytes,
            "content_hash": self.content_hash,
            "line_count": self.line_count,
            "symbols": [s.to_dict() for s in self.symbols],
            "imports": [i.to_dict() for i in self.imports],
            "tokens": sorted(list(self.tokens)),
        }


@dataclass
class RepositoryIndex:
    """Complete aggregated index for a repository."""

    root_dir: str
    files: Dict[str, FileIndexEntry] = field(default_factory=dict)
    symbol_definitions: Dict[str, List[Symbol]] = field(
        default_factory=lambda: defaultdict(list)
    )
    symbol_references: Dict[str, Set[str]] = field(
        default_factory=lambda: defaultdict(set)
    )
    import_graph: Dict[str, Set[str]] = field(
        default_factory=lambda: defaultdict(set)
    )
    reverse_import_graph: Dict[str, Set[str]] = field(
        default_factory=lambda: defaultdict(set)
    )
    token_to_files: Dict[str, Set[str]] = field(
        default_factory=lambda: defaultdict(set)
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "root_dir": self.root_dir,
            "file_count": len(self.files),
            "files": {k: v.to_dict() for k, v in self.files.items()},
            "symbol_count": sum(len(v) for v in self.symbol_definitions.values()),
            "import_graph": {k: sorted(list(v)) for k, v in self.import_graph.items()},
            "reverse_import_graph": {
                k: sorted(list(v)) for k, v in self.reverse_import_graph.items()
            },
        }


class RepositoryIndexer:
    """Manages incremental indexing of a repository workspace."""

    def __init__(
        self,
        root_dir: str = ".",
        exclude_patterns: Optional[List[str]] = None,
    ) -> None:
        self.root_dir = Path(root_dir).resolve()
        self.exclude_patterns = (
            list(DEFAULT_EXCLUDE_PATTERNS)
            if exclude_patterns is None
            else list(DEFAULT_EXCLUDE_PATTERNS) + exclude_patterns
        )
        self._index = RepositoryIndex(root_dir=str(self.root_dir))

    def get_index(self) -> RepositoryIndex:
        """Get or lazily build repository index."""
        if not self._index.files:
            self.index_repository()
        return self._index

    def _should_skip(self, name: str, rel_path: str) -> bool:
        for exc in self.exclude_patterns:
            if fnmatch.fnmatch(name, exc) or fnmatch.fnmatch(rel_path, exc):
                return True
        return False

    def index_repository(self, force: bool = False) -> RepositoryIndex:
        """Scan and index all repository source files incrementally.

        Args:
            force: If True, re-indexes all files even if mtime hasn't changed.

        Returns:
            Populated RepositoryIndex.
        """
        seen_files: Set[str] = set()

        for root, dirs, files in os.walk(self.root_dir):
            root_p = Path(root)
            try:
                rel_root = str(root_p.relative_to(self.root_dir))
            except ValueError:
                rel_root = root

            # Prune directories
            dirs[:] = [
                d
                for d in dirs
                if not self._should_skip(
                    d, f"{rel_root}/{d}".lstrip("./") if rel_root != "." else d
                )
            ]

            for file_name in files:
                rel_file = (
                    f"{rel_root}/{file_name}".lstrip("./")
                    if rel_root != "."
                    else file_name
                )
                if self._should_skip(file_name, rel_file):
                    continue

                ext = Path(file_name).suffix.lower()
                if ext not in SUPPORTED_CODE_EXTENSIONS and file_name != "Makefile":
                    continue

                abs_file = root_p / file_name
                seen_files.add(rel_file)

                # Check stat for incremental indexing
                try:
                    stat = abs_file.stat()
                except OSError:
                    continue

                existing = self._index.files.get(rel_file)
                if not force and existing and existing.mtime == stat.st_mtime:
                    # File unchanged
                    continue

                # Parse file
                self._index_file(abs_file, rel_file, stat)

        # Remove deleted files from index
        deleted = set(self._index.files.keys()) - seen_files
        for del_file in deleted:
            del self._index.files[del_file]

        # Rebuild cross-file inverted indexes
        self._rebuild_inverted_indices()

        return self._index

    def _index_file(self, abs_file: Path, rel_file: str, stat: os.stat_result) -> None:
        """Extract symbols and tokens from file and store FileIndexEntry."""
        try:
            content = abs_file.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            try:
                content = abs_file.read_text(encoding="latin-1", errors="replace")
            except Exception:
                return
        except Exception:
            return

        hasher = hashlib.sha256()
        hasher.update(content.encode("utf-8", errors="replace"))
        content_hash = hasher.hexdigest()

        file_symbols: FileSymbols = SymbolExtractor.extract_from_code(
            content, file_path=rel_file
        )

        # Tokenize content for text / semantic search
        tokens = set()
        # Include identifiers
        tokens.update(t.lower() for t in file_symbols.referenced_identifiers)
        # Include symbol names
        for s in file_symbols.symbols:
            tokens.add(s.name.lower())
            if s.docstring:
                tokens.update(
                    w.lower() for w in s.docstring.split() if w.isalnum()
                )

        lines = content.splitlines()

        entry = FileIndexEntry(
            file_path=rel_file,
            mtime=stat.st_mtime,
            size_bytes=stat.st_size,
            content_hash=content_hash,
            line_count=len(lines),
            symbols=file_symbols.symbols,
            imports=file_symbols.imports,
            tokens=tokens,
        )
        self._index.files[rel_file] = entry

    def _rebuild_inverted_indices(self) -> None:
        """Reconstruct symbol definitions, references, import graph, and token indices."""
        sym_defs: Dict[str, List[Symbol]] = defaultdict(list)
        sym_refs: Dict[str, Set[str]] = defaultdict(set)
        import_g: Dict[str, Set[str]] = defaultdict(set)
        rev_import_g: Dict[str, Set[str]] = defaultdict(set)
        tok_to_files: Dict[str, Set[str]] = defaultdict(set)

        for rel_file, entry in self._index.files.items():
            # Inverted tokens
            for tok in entry.tokens:
                tok_to_files[tok].add(rel_file)

            # Inverted symbol definitions
            for sym in entry.symbols:
                sym_defs[sym.name.lower()].append(sym)
                # Also index bare method/function name
                if "." in sym.name:
                    bare = sym.name.split(".")[-1].lower()
                    sym_defs[bare].append(sym)

            # Inverted imports
            for imp in entry.imports:
                target = imp.source_module
                import_g[rel_file].add(target)
                rev_import_g[target].add(rel_file)

            # Inverted references: map tokens present in this file
            for tok in entry.tokens:
                sym_refs[tok].add(rel_file)

        self._index.symbol_definitions = sym_defs
        self._index.symbol_references = sym_refs
        self._index.import_graph = import_g
        self._index.reverse_import_graph = rev_import_g
        self._index.token_to_files = tok_to_files

    def search_symbols(
        self,
        query: str,
        symbol_type: Optional[SymbolType] = None,
    ) -> List[Symbol]:
        """Search symbol definitions in the index by query substring."""
        index = self.get_index()
        q = query.lower()
        results: List[Symbol] = []
        seen = set()

        for name, syms in index.symbol_definitions.items():
            if q in name:
                for sym in syms:
                    key = (sym.file_path, sym.name, sym.start_line)
                    if key in seen:
                        continue
                    if symbol_type and sym.symbol_type != symbol_type:
                        continue
                    seen.add(key)
                    results.append(sym)

        return sorted(results, key=lambda s: (s.file_path, s.start_line))

    def find_references(self, symbol_name: str) -> List[str]:
        """Find all file paths that reference the given symbol."""
        index = self.get_index()
        return sorted(list(index.symbol_references.get(symbol_name.lower(), set())))

    def get_dependencies(self, file_path: str) -> List[str]:
        """Get modules or files imported by the given file."""
        index = self.get_index()
        return sorted(list(index.import_graph.get(file_path, set())))

    def get_dependents(self, file_path: str) -> List[str]:
        """Get files that import the given file or module."""
        index = self.get_index()
        return sorted(list(index.reverse_import_graph.get(file_path, set())))
