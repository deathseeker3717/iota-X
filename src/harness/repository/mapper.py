"""Repository mapper for the AI Coding Harness.

Generates a compact, token-budget-aware repository map (inspired by Aider repo-map).
Renders the repository structure with classes, functions, and signatures, prioritized
by dependency importance and optional query relevance.
"""

from __future__ import annotations

import os
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set

from harness.repository.indexer import RepositoryIndex, RepositoryIndexer
from harness.repository.symbols import Symbol, SymbolType


@dataclass
class FileScore:
    """Scored file for repository map prioritization."""

    file_path: str
    score: float
    matched_query: bool = False


COMMON_STOP_WORDS = {
    "the", "a", "an", "and", "or", "in", "on", "at", "to", "for", "of",
    "with", "by", "from", "is", "are", "was", "were", "find", "everything",
    "all", "related", "how", "what", "where", "show", "me", "get", "this",
}


class RepositoryMapper:
    """Generates structured, compact repository maps tailored to prompt token budgets."""

    def __init__(
        self,
        indexer: Optional[RepositoryIndexer] = None,
        root_dir: str = ".",
    ) -> None:
        self.root_dir = Path(root_dir).resolve()
        self.indexer = indexer or RepositoryIndexer(root_dir=str(self.root_dir))

    def _estimate_tokens(self, text: str) -> int:
        """Rough token estimation (approx 3.8 chars per token for code/text)."""
        return max(1, len(text) // 4)

    def _compute_file_importance(
        self,
        index: RepositoryIndex,
        query: Optional[str] = None,
        focused_files: Optional[List[str]] = None,
    ) -> List[FileScore]:
        """Compute an importance score for each file using graph degree and query relevance."""
        scores: Dict[str, float] = defaultdict(float)
        query_terms = (
            [
                t.lower().strip(".,;:?!")
                for t in query.split()
                if t.lower().strip(".,;:?!") not in COMMON_STOP_WORDS and len(t) > 1
            ]
            if query
            else []
        )
        focused_set = set(focused_files or [])

        # 1. Base score from in-degree in reverse import graph (dependency centrality)
        for target, importers in index.reverse_import_graph.items():
            for fpath in index.files:
                if target in fpath or fpath.endswith(target.replace(".", "/") + ".py"):
                    scores[fpath] += len(importers) * 1.5

        # 2. Add score for files with high symbol counts
        for fpath, entry in index.files.items():
            scores[fpath] += min(len(entry.symbols) * 0.2, 5.0)

            # Boost focused files
            if fpath in focused_set:
                scores[fpath] += 50.0

            # 3. Query relevance score
            matched_query = False
            if query_terms:
                file_lower = fpath.lower()
                for qt in query_terms:
                    # File path match
                    if qt in file_lower:
                        scores[fpath] += 20.0
                        matched_query = True
                    # Token match in file tokens
                    if qt in entry.tokens:
                        scores[fpath] += 15.0
                        matched_query = True
                    # Symbol name match
                    for sym in entry.symbols:
                        if qt in sym.name.lower():
                            scores[fpath] += 25.0
                            matched_query = True

        file_scores: List[FileScore] = []
        for fpath in index.files:
            file_scores.append(
                FileScore(
                    file_path=fpath,
                    score=scores[fpath],
                    matched_query=any(
                        qt in fpath.lower() or qt in index.files[fpath].tokens
                        for qt in query_terms
                    )
                    if query_terms
                    else False,
                )
            )

        # Sort descending by score
        file_scores.sort(key=lambda x: x.score, reverse=True)
        return file_scores

    def generate_map(
        self,
        query: Optional[str] = None,
        max_tokens: int = 2000,
        focused_files: Optional[List[str]] = None,
    ) -> str:
        """Generate a hierarchical repository map within a token budget.

        Args:
            query: Optional issue or query string (e.g. 'authentication').
            max_tokens: Upper bound on estimated tokens for the generated map.
            focused_files: Specific files that should definitely be expanded.

        Returns:
            Formatted tree string of the repository structure with symbol signatures.
        """
        index = self.indexer.get_index()
        if not index.files:
            return "(Empty repository)"

        file_scores = self._compute_file_importance(index, query, focused_files)

        # Build map with top files first, staying within budget
        lines: List[str] = []
        current_tokens = 0

        # Header
        header = f"# Repository Map ({len(index.files)} files indexed)"
        if query:
            header += f" [Relevance focus: '{query}']"
        lines.append(header)
        current_tokens += self._estimate_tokens(header)

        # Organize files into directory groups
        files_to_render = [fs.file_path for fs in file_scores]

        file_score_map = {fs.file_path: fs for fs in file_scores}

        for fpath in files_to_render:
            entry = index.files[fpath]
            fs = file_score_map.get(fpath)
            if focused_files is not None:
                is_focused = fpath in focused_files
            elif query:
                is_focused = bool(fs and fs.matched_query)
            else:
                is_focused = True

            file_block_lines: List[str] = []

            if not is_focused:
                # Collapse non-relevant files to save context tokens
                sym_summary = f"{len(entry.symbols)} symbols" if entry.symbols else f"{entry.line_count} lines"
                file_block_lines.append(f"  {fpath} ({sym_summary}) [collapsed]")
            else:
                file_header = f"{fpath}:"
                file_block_lines.append(f"  {file_header}")

                # Collect top-level symbols and classes with their methods
                classes: Dict[str, List[Symbol]] = defaultdict(list)
                top_level: List[Symbol] = []

                for sym in entry.symbols:
                    if sym.parent_symbol:
                        classes[sym.parent_symbol].append(sym)
                    elif sym.symbol_type == SymbolType.CLASS:
                        classes[sym.name] = classes.get(sym.name, [])
                    else:
                        top_level.append(sym)

                # Render classes and methods
                for class_name, methods in classes.items():
                    file_block_lines.append(f"    class {class_name}:")
                    for m in methods:
                        sig = m.signature if m.signature else f"def {m.name.split('.')[-1]}(...)"
                        file_block_lines.append(f"      {sig}")

                # Render top-level functions and variables
                for sym in top_level:
                    if sym.symbol_type in (SymbolType.FUNCTION, SymbolType.ASYNC_FUNCTION):
                        sig = sym.signature if sym.signature else f"def {sym.name}(...)"
                        file_block_lines.append(f"    {sig}")
                    elif sym.symbol_type == SymbolType.VARIABLE:
                        file_block_lines.append(f"    {sym.signature}")

                if not entry.symbols:
                    file_block_lines.append(f"    ({entry.line_count} lines)")

            file_text = "\n".join(file_block_lines)
            est = self._estimate_tokens(file_text)

            if current_tokens + est > max_tokens:
                # If budget full, append collapsed files summary
                remaining = len(files_to_render) - len(lines)
                if remaining > 0:
                    lines.append(f"\n  ... and {remaining} other files elided for brevity.")
                break

            lines.extend(file_block_lines)
            current_tokens += est

        return "\n".join(lines)
