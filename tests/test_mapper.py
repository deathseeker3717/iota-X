"""Unit tests for the RepositoryMapper."""

import pytest
from pathlib import Path
from harness.repository.indexer import RepositoryIndexer
from harness.repository.mapper import RepositoryMapper


def test_generate_repo_map(tmp_path):
    (tmp_path / "gateway.py").write_text("""
class ModelGateway:
    \"\"\"Gateway for foundation models.\"\"\"
    def generate(self, prompt: str) -> str:
        return prompt

def make_gateway() -> ModelGateway:
    return ModelGateway()
""")
    (tmp_path / "schemas.py").write_text("""
class RequestSchema:
    pass

class ResponseSchema:
    pass
""")

    indexer = RepositoryIndexer(root_dir=str(tmp_path))
    mapper = RepositoryMapper(indexer=indexer, root_dir=str(tmp_path))

    repo_map = mapper.generate_map()
    assert "Repository Map" in repo_map
    assert "gateway.py:" in repo_map
    assert "class ModelGateway:" in repo_map
    assert "def generate(" in repo_map
    assert "def make_gateway(" in repo_map
    assert "schemas.py:" in repo_map
    assert "class RequestSchema:" in repo_map


def test_generate_repo_map_query_focus(tmp_path):
    (tmp_path / "auth.py").write_text("class Authenticator:\n    def login(self): pass\n")
    (tmp_path / "other.py").write_text("class OtherThing:\n    def do_work(self): pass\n")

    indexer = RepositoryIndexer(root_dir=str(tmp_path))
    mapper = RepositoryMapper(indexer=indexer, root_dir=str(tmp_path))

    repo_map = mapper.generate_map(query="login authentication")
    assert "auth.py" in repo_map
    assert "class Authenticator:" in repo_map
    assert "def login" in repo_map


def test_generate_repo_map_budget_limit(tmp_path):
    # Create multiple files
    for i in range(15):
        (tmp_path / f"mod_{i}.py").write_text(f"class Class{i}:\n    def method{i}(self): pass\n")

    indexer = RepositoryIndexer(root_dir=str(tmp_path))
    mapper = RepositoryMapper(indexer=indexer, root_dir=str(tmp_path))

    # Low budget to trigger truncation/elision
    repo_map = mapper.generate_map(max_tokens=60)
    assert len(repo_map.splitlines()) < 25
