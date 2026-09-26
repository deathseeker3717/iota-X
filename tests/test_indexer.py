"""Unit tests for the RepositoryIndexer."""

import pytest
from pathlib import Path
from harness.repository.indexer import RepositoryIndexer
from harness.repository.symbols import SymbolType


def test_repository_indexing(tmp_path):
    # Setup mock files
    (tmp_path / "models.py").write_text("class User:\n    pass\n")
    (tmp_path / "service.py").write_text(
        "from models import User\n\ndef get_user():\n    return User()\n"
    )

    indexer = RepositoryIndexer(root_dir=str(tmp_path))
    index = indexer.index_repository()

    # Files indexed
    assert "models.py" in index.files
    assert "service.py" in index.files

    # Symbol definitions
    assert "user" in index.symbol_definitions
    assert "get_user" in index.symbol_definitions

    # Symbol search
    syms = indexer.search_symbols("User", symbol_type=SymbolType.CLASS)
    assert len(syms) == 1
    assert syms[0].name == "User"

    # Dependency checking
    deps = indexer.get_dependencies("service.py")
    assert "models" in deps

    rev_deps = indexer.get_dependents("models")
    assert "service.py" in rev_deps


def test_incremental_indexing(tmp_path):
    file1 = tmp_path / "test_file.py"
    file1.write_text("def v1(): pass\n")

    indexer = RepositoryIndexer(root_dir=str(tmp_path))
    index1 = indexer.index_repository()
    assert "v1" in index1.symbol_definitions

    # Keep file unchanged -> mtime matching
    entry1 = index1.files["test_file.py"]
    index2 = indexer.index_repository()
    assert index2.files["test_file.py"].mtime == entry1.mtime

    # Update file -> re-indexed
    file1.write_text("def v2(): pass\n")
    index3 = indexer.index_repository(force=True)
    assert "v2" in index3.symbol_definitions


def test_deleted_file_cleanup(tmp_path):
    file1 = tmp_path / "temp.py"
    file1.write_text("def to_be_deleted(): pass\n")

    indexer = RepositoryIndexer(root_dir=str(tmp_path))
    index = indexer.index_repository()
    assert "temp.py" in index.files

    file1.unlink()
    index_after = indexer.index_repository()
    assert "temp.py" not in index_after.files
