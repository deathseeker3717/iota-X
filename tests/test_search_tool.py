"""Unit tests for the SearchTool."""

import pytest
from pathlib import Path
from harness.tools.search import (
    SearchTool,
    get_search_tool_definitions,
    search_files,
    search_symbol,
    find_references,
    find_imports,
)


def test_search_files(tmp_path):
    st = SearchTool(root_dir=str(tmp_path))
    file1 = tmp_path / "service.py"
    file1.write_text("def authenticate_user(username, password):\n    return True\n")
    file2 = tmp_path / "models.py"
    file2.write_text("class UserSession:\n    pass\n")

    # Literal search
    results = st.search_files(pattern="authenticate_user")
    assert len(results) == 1
    assert results[0].file_path == "service.py"
    assert results[0].line_number == 1
    assert "authenticate_user" in results[0].line_content

    # Regex search
    regex_res = st.search_files(pattern=r"def\s+\w+\(", is_regex=True)
    assert len(regex_res) == 1
    assert regex_res[0].file_path == "service.py"


def test_search_symbol(tmp_path):
    st = SearchTool(root_dir=str(tmp_path))
    code = """
class TokenManager:
    \"\"\"Manages JWT tokens.\"\"\"
    def generate_token(self, user_id: str) -> str:
        return "token-123"

def verify_token(token: str) -> bool:
    return True
"""
    (tmp_path / "auth.py").write_text(code)

    # Search for class
    classes = st.search_symbol("TokenManager", symbol_type="class")
    assert len(classes) == 1
    assert classes[0].name == "TokenManager"
    assert classes[0].symbol_type == "class"
    assert "Manages JWT tokens" in classes[0].docstring

    # Search for function
    funcs = st.search_symbol("verify_token", symbol_type="function")
    assert len(funcs) == 1
    assert funcs[0].name == "verify_token"
    assert "def verify_token(token: str) -> bool" in funcs[0].signature

    # Search for method
    methods = st.search_symbol("generate_token", symbol_type="method")
    assert len(methods) == 1
    assert methods[0].name == "TokenManager.generate_token"


def test_find_references(tmp_path):
    st = SearchTool(root_dir=str(tmp_path))
    (tmp_path / "gateway.py").write_text("class ModelGateway:\n    pass\n")
    (tmp_path / "app.py").write_text("gw = ModelGateway()\ngw.run()\n")

    refs = st.find_references("ModelGateway")
    files_with_refs = {r.file_path for r in refs}
    assert "gateway.py" in files_with_refs
    assert "app.py" in files_with_refs


def test_find_imports(tmp_path):
    st = SearchTool(root_dir=str(tmp_path))
    (tmp_path / "consumer.py").write_text(
        "import os\nfrom harness.model import ModelGateway, ModelRequest\nfrom harness.tools import list_files as ls\n"
    )

    # Search for ModelGateway import
    matches = st.find_imports("ModelGateway")
    assert len(matches) == 1
    assert matches[0].file_path == "consumer.py"
    assert matches[0].imported_name == "ModelGateway"

    # Search for module import
    matches_os = st.find_imports("os")
    assert len(matches_os) == 1
    assert matches_os[0].module_name == "os"


def test_search_tool_definitions():
    defs = get_search_tool_definitions()
    names = {d.name for d in defs}
    assert "search_files" in names
    assert "search_symbol" in names
    assert "find_references" in names
    assert "find_imports" in names
