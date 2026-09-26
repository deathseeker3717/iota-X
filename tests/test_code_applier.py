"""Unit and integration tests for CodeApplier and CodeProposal application (Phase 6).

Covers all required scenarios:
1. read existing file
2. create file
3. modify file
4. delete file
5. invalid path
6. path traversal attempt
7. absolute path outside repository
8. modify with matching old_content
9. modify with mismatched old_content
10. unsupported action
11. multiple CodeEdits
12. partial failure reporting
13. repository remains safe after failed validation
14. end-to-end integration test with CodeProposal
"""

import os
from pathlib import Path
import pytest

from harness.model.schemas import CodeEdit, CodeProposal
from harness.repository.applier import ApplicationResult, CodeApplier, EditResult


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """Setup a sample repository structure in a temporary directory."""
    src_dir = tmp_path / "src"
    src_dir.mkdir(parents=True)
    (src_dir / "main.py").write_text("def hello():\n    return 'hello'\n", encoding="utf-8")
    (src_dir / "utils.py").write_text("MAX_RETRIES = 3\nTIMEOUT = 30\n", encoding="utf-8")
    (tmp_path / "obsolete.txt").write_text("deprecated file\n", encoding="utf-8")
    return tmp_path


def test_read_existing_file(repo: Path):
    """1. Test reading existing file content."""
    applier = CodeApplier(root_dir=str(repo))
    content = applier.read_file("src/main.py")
    assert "return 'hello'" in content


def test_create_file(repo: Path):
    """2. Test creating a new file only when action is create."""
    applier = CodeApplier(root_dir=str(repo))
    target = "src/services/auth.py"
    content = "def authenticate():\n    return True\n"

    assert applier.create_file(target, content=content) is True
    assert (repo / target).exists()
    assert (repo / target).read_text(encoding="utf-8") == content

    # Creating an already existing file must raise FileExistsError
    with pytest.raises(FileExistsError, match="File already exists"):
        applier.create_file(target, content="overwrite")


def test_modify_file(repo: Path):
    """3. Test modifying an existing file."""
    applier = CodeApplier(root_dir=str(repo))
    new_content = "def hello():\n    return 'hello world'\n"

    assert applier.modify_file("src/main.py", new_content=new_content) is True
    assert applier.read_file("src/main.py") == new_content

    # Modifying non-existent file must raise FileNotFoundError
    with pytest.raises(FileNotFoundError, match="Cannot modify non-existent file"):
        applier.modify_file("src/missing.py", new_content="content")


def test_delete_file(repo: Path):
    """4. Test deleting an existing file."""
    applier = CodeApplier(root_dir=str(repo))
    assert (repo / "obsolete.txt").exists()

    assert applier.delete_file("obsolete.txt") is True
    assert not (repo / "obsolete.txt").exists()

    # Deleting non-existent file must raise FileNotFoundError
    with pytest.raises(FileNotFoundError, match="Cannot delete non-existent file"):
        applier.delete_file("obsolete.txt")


def test_invalid_path(repo: Path):
    """5. Test invalid path validation (empty or null bytes)."""
    applier = CodeApplier(root_dir=str(repo))

    with pytest.raises(ValueError, match="cannot be empty"):
        applier.resolve_path("")

    with pytest.raises(ValueError, match="cannot be empty"):
        applier.resolve_path("   ")

    with pytest.raises(ValueError, match="null bytes"):
        applier.resolve_path("src/foo\0bar.py")


def test_path_traversal_attempt(repo: Path):
    """6. Test path traversal attempts are rejected."""
    applier = CodeApplier(root_dir=str(repo), enforce_sandbox=True)

    with pytest.raises(PermissionError, match="Access denied"):
        applier.resolve_path("../../etc/passwd")

    with pytest.raises(PermissionError, match="Access denied"):
        applier.resolve_path("src/../../outside.txt")


def test_absolute_path_outside_repository(repo: Path):
    """7. Test absolute path outside repository is rejected."""
    applier = CodeApplier(root_dir=str(repo), enforce_sandbox=True)

    with pytest.raises(PermissionError, match="Access denied"):
        applier.resolve_path("/etc/passwd")

    with pytest.raises(PermissionError, match="Access denied"):
        applier.resolve_path("/var/log/system.log")


def test_modify_with_matching_old_content(repo: Path):
    """8. Test modify with matching old_content snippet."""
    applier = CodeApplier(root_dir=str(repo))

    # Snippet replacement
    assert applier.modify_file(
        path="src/utils.py",
        old_content="MAX_RETRIES = 3",
        new_content="MAX_RETRIES = 5",
    ) is True

    updated = applier.read_file("src/utils.py")
    assert "MAX_RETRIES = 5" in updated
    assert "TIMEOUT = 30" in updated

    # Full content matching replacement
    assert applier.modify_file(
        path="src/utils.py",
        old_content=updated,
        new_content="# Entirely replaced\n",
    ) is True
    assert applier.read_file("src/utils.py") == "# Entirely replaced\n"


def test_modify_with_mismatched_old_content(repo: Path):
    """9. Test modify with mismatched old_content raises conflict error."""
    applier = CodeApplier(root_dir=str(repo))

    with pytest.raises(
        ValueError,
        match="File changed since proposal generation; old_content does not match current repository state.",
    ):
        applier.modify_file(
            path="src/utils.py",
            old_content="MAX_RETRIES = 999",  # Does not match real value (3)
            new_content="MAX_RETRIES = 10",
        )


def test_unsupported_action(repo: Path):
    """10. Test unsupported action handling."""
    applier = CodeApplier(root_dir=str(repo))

    edit = CodeEdit(
        file_path="src/main.py",
        action="rename",  # Unsupported
        explanation="Rename file",
    )
    result = applier.apply_edit(edit)

    assert result.success is False
    assert "Unsupported action" in str(result.error)

    # In proposal validation
    proposal = CodeProposal(
        thought_process="test",
        explanation="test",
        changes=[edit],
    )
    app_res = applier.apply_proposal(proposal)
    assert app_res.success is False
    assert any("Unsupported action" in err for err in app_res.errors)


def test_multiple_code_edits(repo: Path):
    """11. Test applying multiple CodeEdits in a proposal."""
    applier = CodeApplier(root_dir=str(repo))

    proposal = CodeProposal(
        thought_process="Multi-file change",
        explanation="Create new, modify existing, delete obsolete",
        changes=[
            CodeEdit(
                file_path="src/config.py",
                action="create",
                explanation="Add config module",
                new_content="DEBUG = False\n",
            ),
            CodeEdit(
                file_path="src/main.py",
                action="modify",
                explanation="Update greeting",
                old_content="return 'hello'",
                new_content="return 'hello from config'",
            ),
            CodeEdit(
                file_path="obsolete.txt",
                action="delete",
                explanation="Remove obsolete file",
            ),
        ],
    )

    result = applier.apply_proposal(proposal)
    assert result.success is True
    assert len(result.applied_edits) == 3
    assert len(result.failed_edits) == 0

    # Verify on disk
    assert (repo / "src/config.py").read_text(encoding="utf-8") == "DEBUG = False\n"
    assert "return 'hello from config'" in (repo / "src/main.py").read_text(encoding="utf-8")
    assert not (repo / "obsolete.txt").exists()


def test_partial_failure_reporting(repo: Path):
    """12. Test clear reporting of partial failure when atomic=False."""
    applier = CodeApplier(root_dir=str(repo))

    proposal = CodeProposal(
        thought_process="Mixed edits",
        explanation="One valid, one failing edit",
        changes=[
            CodeEdit(
                file_path="src/valid.py",
                action="create",
                explanation="Create valid file",
                new_content="VALID = True\n",
            ),
            CodeEdit(
                file_path="src/non_existent.py",
                action="modify",
                explanation="Modify missing file",
                new_content="WILL_FAIL\n",
            ),
        ],
    )

    result = applier.apply_proposal(proposal, atomic=False)
    assert result.success is False
    assert len(result.applied_edits) == 1
    assert result.applied_edits[0].file_path == "src/valid.py"
    assert len(result.failed_edits) == 1
    assert result.failed_edits[0].file_path == "src/non_existent.py"
    assert len(result.errors) > 0


def test_repository_remains_safe_after_failed_validation(repo: Path):
    """13. Test that in atomic mode (default), failed validation leaves repository untouched."""
    applier = CodeApplier(root_dir=str(repo))
    original_main = (repo / "src/main.py").read_text(encoding="utf-8")

    proposal = CodeProposal(
        thought_process="Dangerous batch",
        explanation="Contains a valid edit and a malicious traversal attempt",
        changes=[
            CodeEdit(
                file_path="src/main.py",
                action="modify",
                explanation="Should not be applied if second edit is unsafe",
                new_content="OVERWRITTEN\n",
            ),
            CodeEdit(
                file_path="../../etc/passwd",
                action="modify",
                explanation="Malicious traversal",
                new_content="ATTACK\n",
            ),
        ],
    )

    result = applier.apply_proposal(proposal, atomic=True)
    assert result.success is False
    assert len(result.applied_edits) == 0
    assert len(result.errors) > 0

    # Critical: src/main.py MUST remain untouched
    current_main = (repo / "src/main.py").read_text(encoding="utf-8")
    assert current_main == original_main
    assert "OVERWRITTEN" not in current_main


def test_integration_code_proposal_application(tmp_path: Path):
    """14. Full integration test: CodeProposal -> Repository application -> Actual temporary repository changes."""
    # Setup initial repository state
    app_file = tmp_path / "app.py"
    app_file.write_text("def hello():\n    return 'hello'\n", encoding="utf-8")

    old_file = tmp_path / "legacy.py"
    old_file.write_text("def legacy(): pass\n", encoding="utf-8")

    applier = CodeApplier(root_dir=str(tmp_path))

    # CoderAgent-style CodeProposal
    proposal = CodeProposal(
        thought_process="1. Modify app.py to return 'hello world'. 2. Create tests. 3. Remove legacy.",
        explanation="Updated greeting to 'hello world', added tests, removed legacy module.",
        files_to_modify=["app.py", "test_app.py", "legacy.py"],
        changes=[
            CodeEdit(
                file_path="app.py",
                action="modify",
                explanation="Change greeting return value",
                old_content="def hello():\n    return 'hello'\n",
                new_content="def hello():\n    return 'hello world'\n",
            ),
            CodeEdit(
                file_path="test_app.py",
                action="create",
                explanation="Add test for updated greeting",
                new_content="from app import hello\n\ndef test_hello():\n    assert hello() == 'hello world'\n",
            ),
            CodeEdit(
                file_path="legacy.py",
                action="delete",
                explanation="Delete legacy module",
            ),
        ],
    )

    # Apply proposal
    result = applier.apply_proposal(proposal)

    assert result.success is True
    assert len(result.applied_edits) == 3
    assert len(result.failed_edits) == 0

    # Verify actual disk changes
    assert app_file.read_text(encoding="utf-8") == "def hello():\n    return 'hello world'\n"
    assert (tmp_path / "test_app.py").exists()
    assert "assert hello() == 'hello world'" in (tmp_path / "test_app.py").read_text(encoding="utf-8")
    assert not old_file.exists()
