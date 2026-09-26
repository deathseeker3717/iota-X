"""Repository context selection for the AI Coding Harness.

Implements query-driven context selection:
Issue / Query -> Repository Search -> Relevant Files -> Relevant Functions/Classes.
Supplies the foundation model with high-precision context without dumping the whole repo.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from harness.repository.indexer import RepositoryIndex, RepositoryIndexer
from harness.repository.mapper import RepositoryMapper
from harness.repository.symbols import Symbol, SymbolType

# Synonyms and domain associations for common programming concepts
QUERY_SYNONYMS = {
    "auth": ["authentication", "authenticate", "login", "token", "password", "session", "jwt", "oauth", "credential", "user", "permission"],
    "authentication": ["auth", "authenticate", "login", "token", "password", "session", "jwt", "oauth", "credential", "user"],
    "database": ["db", "sql", "orm", "session", "query", "model", "migration", "sqlite", "postgres", "entity"],
    "db": ["database", "sql", "orm", "query", "model"],
    "test": ["pytest", "unittest", "mock", "assert", "suite", "case", "runner"],
    "model": ["schema", "entity", "dataclass", "pydantic", "gateway", "provider"],
    "api": ["endpoint", "router", "route", "handler", "request", "response", "http", "rest"],
    "config": ["configuration", "settings", "env", "yaml", "options"],
}


@dataclass
class RelevantSymbol:
    """A specific function, class, or method identified as relevant to the query."""

    symbol: Symbol
    file_path: str
    score: float
    matched_terms: List[str]
    code_snippet: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol.to_dict(),
            "file_path": self.file_path,
            "score": round(self.score, 2),
            "matched_terms": self.matched_terms,
            "code_snippet": self.code_snippet,
        }


@dataclass
class RelevantFile:
    """A file identified as containing relevant logic."""

    file_path: str
    score: float
    matched_symbols: List[Symbol]
    rationale: str
    line_count: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_path": self.file_path,
            "score": round(self.score, 2),
            "matched_symbols": [s.to_dict() for s in self.matched_symbols],
            "rationale": self.rationale,
            "line_count": self.line_count,
        }


@dataclass
class RepositoryContext:
    """Consolidated relevant context package ready for model consumption."""

    query: str
    relevant_files: List[RelevantFile]
    relevant_symbols: List[RelevantSymbol]
    repo_map: str
    formatted_prompt_context: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "relevant_files": [f.to_dict() for f in self.relevant_files],
            "relevant_symbols": [s.to_dict() for s in self.relevant_symbols],
            "repo_map": self.repo_map,
            "formatted_prompt_context": self.formatted_prompt_context,
        }


STOP_WORDS = {
    "a", "about", "all", "an", "and", "any", "are", "as", "at", "be", "been",
    "by", "can", "do", "does", "everything", "find", "for", "from", "get",
    "has", "have", "how", "i", "in", "is", "it", "its", "me", "my", "no", "not",
    "of", "on", "or", "our", "out", "related", "show", "so", "some", "that",
    "the", "their", "there", "they", "this", "to", "us", "was", "we", "were",
    "what", "when", "where", "which", "who", "will", "with", "would", "you", "your",
}


class RepositoryContextManager:
    """Selects and formats minimal high-relevance repository context for a given task/query."""

    def __init__(
        self,
        root_dir: str = ".",
        indexer: Optional[RepositoryIndexer] = None,
        mapper: Optional[RepositoryMapper] = None,
    ) -> None:
        self.root_dir = Path(root_dir).resolve()
        self.indexer = indexer or RepositoryIndexer(root_dir=str(self.root_dir))
        self.mapper = mapper or RepositoryMapper(indexer=self.indexer, root_dir=str(self.root_dir))

    def _expand_query(self, query: str) -> Set[str]:
        """Expand user query into normalized tokens and domain synonyms."""
        # Extract word tokens and split camelCase/snake_case
        raw_words = re.findall(r"[A-Za-z0-9]+", query)
        expanded: Set[str] = set()

        for w in raw_words:
            w_lower = w.lower()
            if w_lower in STOP_WORDS:
                continue

            expanded.add(w_lower)
            # CamelCase split
            parts = re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?=[A-Z][a-z]|\d|\W|$)|\d+", w)
            for p in parts:
                p_lower = p.lower()
                if p_lower not in STOP_WORDS:
                    expanded.add(p_lower)

            # Add synonyms
            if w_lower in QUERY_SYNONYMS:
                expanded.update(QUERY_SYNONYMS[w_lower])

        return {t for t in expanded if len(t) > 1 and t not in STOP_WORDS}

    def _extract_snippet(
        self, file_path: str, start_line: int, end_line: int, max_lines: int = 50
    ) -> str:
        """Extract lines of code with 1-based line numbers."""
        full_path = self.root_dir / file_path
        if not full_path.exists():
            return ""

        try:
            content = full_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            content = full_path.read_text(encoding="latin-1", errors="replace")

        lines = content.splitlines()
        s = max(0, start_line - 1)
        e = min(len(lines), end_line)

        if e - s > max_lines:
            truncated = e - s - max_lines
            selected = lines[s : s + max_lines]
            result = [f"{s + i + 1:4d} | {line}" for i, line in enumerate(selected)]
            result.append(f"     ... [Truncated: {truncated} lines omitted]")
            return "\n".join(result)

        return "\n".join(
            f"{s + i + 1:4d} | {line}" for i, line in enumerate(lines[s:e])
        )

    def find_relevant_context(
        self,
        query: str,
        max_files: int = 5,
        max_symbols: int = 8,
        max_tokens: int = 3500,
    ) -> RepositoryContext:
        """Find relevant files and symbol definitions for an issue or natural query.

        Args:
            query: Natural language query (e.g. "Find everything related to authentication").
            max_files: Maximum number of files to select.
            max_symbols: Maximum number of specific functions/classes to extract snippets for.
            max_tokens: Estimated token budget for the context output.

        Returns:
            RepositoryContext object containing ranked files, symbols, snippets, and repo map.
        """
        index = self.indexer.get_index()
        query_terms = self._expand_query(query)

        # 1. Score symbols across repository
        symbol_scores: List[tuple[Symbol, float, List[str]]] = []

        for fpath, entry in index.files.items():
            for sym in entry.symbols:
                score = 0.0
                matched_terms: List[str] = []
                sym_name_lower = sym.name.lower()

                for term in query_terms:
                    # Exact or word-boundary match in symbol name
                    sym_tokens = set(re.findall(r"[a-z0-9]+", sym_name_lower))
                    if term == sym_name_lower or f".{term}" in sym_name_lower or term in sym_tokens:
                        score += 50.0
                        matched_terms.append(term)
                    elif len(term) > 3 and term in sym_name_lower:
                        score += 30.0
                        matched_terms.append(term)

                    # Docstring match
                    if sym.docstring and term in sym.docstring.lower():
                        score += 15.0
                        if term not in matched_terms:
                            matched_terms.append(term)

                    # Signature / parameters match
                    param_tokens = {tok for p in sym.parameters for tok in re.findall(r"[a-z0-9]+", p.lower())}
                    if term in param_tokens or (len(term) > 3 and any(term in p.lower() for p in sym.parameters)):
                        score += 10.0
                        if term not in matched_terms:
                            matched_terms.append(term)

                if score > 0:
                    symbol_scores.append((sym, score, matched_terms))

        symbol_scores.sort(key=lambda x: x[1], reverse=True)

        # 2. Score files
        file_scores: Dict[str, float] = {}
        file_matched_symbols: Dict[str, List[Symbol]] = {
            fp: [] for fp in index.files
        }
        file_rationales: Dict[str, List[str]] = {fp: [] for fp in index.files}

        for sym, score, matched_terms in symbol_scores:
            file_scores[sym.file_path] = file_scores.get(sym.file_path, 0.0) + score
            file_matched_symbols[sym.file_path].append(sym)
            file_rationales[sym.file_path].append(
                f"Symbol '{sym.name}' matches query terms: {', '.join(matched_terms)}"
            )

        # Also score based on file path name
        for fpath, entry in index.files.items():
            fpath_lower = fpath.lower()
            fpath_tokens = set(re.findall(r"[a-z0-9]+", fpath_lower))
            for term in query_terms:
                if term in fpath_tokens or (len(term) > 3 and term in fpath_lower):
                    file_scores[fpath] = file_scores.get(fpath, 0.0) + 25.0
                    file_rationales[fpath].append(f"File path matches term '{term}'")

                # Token frequency in file
                if term in entry.tokens:
                    file_scores[fpath] = file_scores.get(fpath, 0.0) + 5.0

        # Rank files
        ranked_files = sorted(
            [(fp, s) for fp, s in file_scores.items() if s > 0],
            key=lambda x: x[1],
            reverse=True,
        )[:max_files]

        relevant_files: List[RelevantFile] = []
        for fpath, score in ranked_files:
            entry = index.files[fpath]
            symbols = file_matched_symbols.get(fpath, [])
            rationales = file_rationales.get(fpath, [])
            rationale_str = "; ".join(rationales[:3])
            relevant_files.append(
                RelevantFile(
                    file_path=fpath,
                    score=score,
                    matched_symbols=symbols,
                    rationale=rationale_str,
                    line_count=entry.line_count,
                )
            )

        # 3. Extract top relevant symbol code snippets
        relevant_symbols: List[RelevantSymbol] = []
        for sym, score, matched_terms in symbol_scores[:max_symbols]:
            snippet = self._extract_snippet(
                sym.file_path, sym.start_line, sym.end_line
            )
            relevant_symbols.append(
                RelevantSymbol(
                    symbol=sym,
                    file_path=sym.file_path,
                    score=score,
                    matched_terms=matched_terms,
                    code_snippet=snippet,
                )
            )

        # 4. Generate targeted repository map
        focused_paths = [f.file_path for f in relevant_files]
        repo_map = self.mapper.generate_map(
            query=query,
            max_tokens=min(1200, max_tokens // 2),
            focused_files=focused_paths,
        )

        # 5. Format prompt context
        formatted_prompt = self._format_prompt(
            query, relevant_files, relevant_symbols, repo_map
        )

        return RepositoryContext(
            query=query,
            relevant_files=relevant_files,
            relevant_symbols=relevant_symbols,
            repo_map=repo_map,
            formatted_prompt_context=formatted_prompt,
        )

    def _format_prompt(
        self,
        query: str,
        files: List[RelevantFile],
        symbols: List[RelevantSymbol],
        repo_map: str,
    ) -> str:
        """Format the context into an LLM-ready markdown block."""
        parts: List[str] = [
            f"## Repository Intelligence Context for: '{query}'\n",
            "### Relevant Files:",
        ]

        if not files:
            parts.append("No specific matching files found.")
        else:
            for f in files:
                sym_names = [s.name for s in f.matched_symbols[:4]]
                sym_str = f" (Key symbols: {', '.join(sym_names)})" if sym_names else ""
                parts.append(
                    f"- `{f.file_path}` (score: {f.score:.1f}, {f.line_count} lines){sym_str}\n  Rationale: {f.rationale}"
                )

        if symbols:
            parts.append("\n### Relevant Functions & Classes (Extracted Snippets):")
            for rs in symbols:
                parts.append(
                    f"\n#### `{rs.file_path}:{rs.symbol.start_line}-{rs.symbol.end_line}` — `{rs.symbol.name}` ({rs.symbol.symbol_type.value})\n"
                    f"```python\n{rs.code_snippet}\n```"
                )

        parts.append("\n### Repository Structure Map:")
        parts.append(f"```yaml\n{repo_map}\n```")

        return "\n".join(parts)


# Default module-level instance
_default_context_mgr = RepositoryContextManager()


def find_relevant_context(
    query: str,
    max_files: int = 5,
    max_symbols: int = 8,
    max_tokens: int = 3500,
) -> RepositoryContext:
    """Find relevant repository context for a query."""
    return _default_context_mgr.find_relevant_context(
        query, max_files, max_symbols, max_tokens
    )
