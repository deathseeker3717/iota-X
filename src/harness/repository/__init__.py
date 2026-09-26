"""Repository Intelligence package public exports for AI Coding Harness."""

from harness.repository.applier import (
    ApplicationResult,
    CodeApplier,
    EditResult,
)
from harness.repository.context import (
    RelevantFile,
    RelevantSymbol,
    RepositoryContext,
    RepositoryContextManager,
    find_relevant_context,
)
from harness.repository.indexer import (
    FileIndexEntry,
    RepositoryIndex,
    RepositoryIndexer,
)
from harness.repository.mapper import RepositoryMapper
from harness.repository.symbols import (
    FileSymbols,
    ImportItem,
    Symbol,
    SymbolExtractor,
    SymbolType,
)

__all__ = [
    # Applier
    "CodeApplier",
    "EditResult",
    "ApplicationResult",
    # Symbols
    "Symbol",
    "SymbolType",
    "ImportItem",
    "FileSymbols",
    "SymbolExtractor",
    # Indexer
    "FileIndexEntry",
    "RepositoryIndex",
    "RepositoryIndexer",
    # Mapper
    "RepositoryMapper",
    # Context
    "RelevantFile",
    "RelevantSymbol",
    "RepositoryContext",
    "RepositoryContextManager",
    "find_relevant_context",
]
