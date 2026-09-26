"""Unit tests for Repository Intelligence context selection.

Validates the core success criterion:
Given a repository and query "Find everything related to authentication",
return the relevant files and functions efficiently without dumping the whole repository.
"""

import pytest
from pathlib import Path
from harness.repository.context import (
    RepositoryContextManager,
    find_relevant_context,
)


@pytest.fixture
def sample_codebase(tmp_path):
    # Auth files
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "auth").mkdir()
    (tmp_path / "src" / "billing").mkdir()
    (tmp_path / "src" / "reports").mkdir()

    (tmp_path / "src" / "auth" / "service.py").write_text("""
\"\"\"Authentication service handling credentials and token validation.\"\"\"

class AuthService:
    \"\"\"Core authentication service.\"\"\"

    def __init__(self, jwt_secret: str) -> None:
        self.jwt_secret = jwt_secret

    def login(self, username: str, password_hash: str) -> str:
        \"\"\"Authenticate user and return a signed JWT token.\"\"\"
        if username == "admin":
            return "jwt-valid-token-12345"
        raise ValueError("Invalid credentials")

    def verify_token(self, token: str) -> bool:
        \"\"\"Verify an authentication token.\"\"\"
        return token.startswith("jwt-")
""")

    (tmp_path / "src" / "auth" / "models.py").write_text("""
class UserCredentials:
    username: str
    password_hash: str

class AuthToken:
    access_token: str
    token_type: str = "bearer"
""")

    # Irrelevant files: Billing
    (tmp_path / "src" / "billing" / "service.py").write_text("""
class BillingService:
    def charge_invoice(self, invoice_id: str, amount: float) -> bool:
        print(f"Charging {amount} for {invoice_id}")
        return True

    def calculate_taxes(self, subtotal: float) -> float:
        return subtotal * 0.1
""")

    # Irrelevant files: Reports
    (tmp_path / "src" / "reports" / "export.py").write_text("""
def export_csv_summary(data: list) -> str:
    return "csv_content"
""")

    return tmp_path


def test_success_criterion_find_everything_related_to_authentication(sample_codebase):
    ctx_mgr = RepositoryContextManager(root_dir=str(sample_codebase))

    query = "Find everything related to authentication."
    context = ctx_mgr.find_relevant_context(query)

    # 1. Relevant files check
    matched_file_paths = [f.file_path for f in context.relevant_files]
    assert len(matched_file_paths) > 0
    # Top files must be in src/auth
    assert "src/auth/service.py" in matched_file_paths
    assert "src/auth/models.py" in matched_file_paths
    # Billing and reports should not outrank auth
    top_file = context.relevant_files[0].file_path
    assert "auth" in top_file

    # 2. Relevant functions / classes check
    matched_symbol_names = [s.symbol.name for s in context.relevant_symbols]
    assert any("AuthService" in name for name in matched_symbol_names)
    assert any("login" in name for name in matched_symbol_names)
    assert any("verify_token" in name for name in matched_symbol_names)
    assert any("UserCredentials" in name or "AuthToken" in name for name in matched_symbol_names)

    # Billing functions must NOT be in top relevant symbols
    assert not any("charge_invoice" in name for name in matched_symbol_names)

    # 3. Exact line-numbered snippet check
    login_symbol = next(
        s for s in context.relevant_symbols if "login" in s.symbol.name
    )
    assert login_symbol.symbol.start_line > 0
    assert "def login" in login_symbol.code_snippet
    assert "jwt-valid-token" in login_symbol.code_snippet
    # Line number prefix format "   N | "
    assert "|" in login_symbol.code_snippet

    # 4. Formatted prompt context is markdown ready
    prompt_text = context.formatted_prompt_context
    assert "## Repository Intelligence Context" in prompt_text
    assert "src/auth/service.py" in prompt_text
    assert "AuthService.login" in prompt_text
    assert "```python" in prompt_text
    assert "Repository Structure Map:" in prompt_text

    # 5. It does not dump the entire repository: snippets are focused
    assert "charge_invoice" not in prompt_text


def test_query_expansion():
    ctx_mgr = RepositoryContextManager()
    tokens = ctx_mgr._expand_query("How does authentication and login work?")
    assert "auth" in tokens
    assert "authentication" in tokens
    assert "login" in tokens
    assert "token" in tokens
    assert "jwt" in tokens
