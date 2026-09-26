"""Repository Code Applier for the AI Coding Harness.

Provides safe, sandboxed application of CodeProposal and CodeEdit operations
to the repository workspace.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from harness.model.schemas import CodeEdit, CodeProposal
from harness.tools.filesystem import FilesystemTool


@dataclass
class EditResult:
    """Result of applying an individual CodeEdit."""

    file_path: str
    action: str
    success: bool
    error: Optional[str] = None
    explanation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_path": self.file_path,
            "action": self.action,
            "success": self.success,
            "error": self.error,
            "explanation": self.explanation,
        }


@dataclass
class ApplicationResult:
    """Aggregated result of applying a CodeProposal."""

    success: bool
    applied_edits: List[EditResult] = field(default_factory=list)
    failed_edits: List[EditResult] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "applied_edits": [e.to_dict() for e in self.applied_edits],
            "failed_edits": [e.to_dict() for e in self.failed_edits],
            "errors": self.errors,
        }


class CodeApplier:
    """Safely applies CodeProposal objects to a repository directory."""

    SUPPORTED_ACTIONS = {"create", "modify", "delete"}

    def __init__(self, root_dir: str = ".", enforce_sandbox: bool = True) -> None:
        self.root_dir = Path(root_dir).resolve()
        self.enforce_sandbox = enforce_sandbox
        self.fs = FilesystemTool(root_dir=str(self.root_dir), enforce_sandbox=enforce_sandbox)

    def resolve_path(self, relative_or_absolute: str) -> Path:
        """Resolve a path safely within the repository root directory.

        Args:
            relative_or_absolute: Path string to resolve.

        Returns:
            Resolved absolute Path.

        Raises:
            ValueError: If path is empty or contains null bytes.
            PermissionError: If path escapes repository root when sandbox is enforced.
        """
        if not relative_or_absolute or not relative_or_absolute.strip():
            raise ValueError("File path cannot be empty or whitespace.")

        if "\0" in relative_or_absolute:
            raise ValueError("File path cannot contain null bytes.")

        path = Path(relative_or_absolute)
        if not path.is_absolute():
            resolved = (self.root_dir / path).resolve()
        else:
            resolved = path.resolve()

        if self.enforce_sandbox:
            try:
                resolved.relative_to(self.root_dir)
            except ValueError:
                raise PermissionError(
                    f"Access denied: Path '{relative_or_absolute}' is outside repository root '{self.root_dir}'"
                )

        return resolved

    def read_file(self, path: str) -> str:
        """Read current content of a file in the repository."""
        return self.fs.read_file(path)

    def create_file(self, path: str, content: str = "") -> bool:
        """Create a new file. Fails if file already exists."""
        return self.fs.create_file(path, content=content, create_dirs=True)

    def modify_file(
        self,
        path: str,
        new_content: Optional[str] = None,
        old_content: Optional[str] = None,
        diff: Optional[str] = None,
    ) -> bool:
        """Modify an existing file with staleness protection.

        Args:
            path: Target file path.
            new_content: New text content for the file.
            old_content: Optional expected previous content or snippet.
            diff: Optional diff representation.

        Returns:
            True on successful modification.

        Raises:
            FileNotFoundError: If target file does not exist.
            ValueError: If old_content is supplied and does not match current state.
        """
        target_path = self.resolve_path(path)
        if not target_path.exists():
            raise FileNotFoundError(f"Cannot modify non-existent file: {path}")
        if not target_path.is_file():
            raise IsADirectoryError(f"Path is a directory, not a file: {path}")

        current_content = target_path.read_text(encoding="utf-8", errors="replace")

        # Staleness protection: check old_content if provided
        if old_content is not None and old_content.strip() != "":
            # Case 1: Exact / normalized full file match
            if old_content.strip() == current_content.strip():
                content_to_write = new_content if new_content is not None else ""
            # Case 2: Target snippet substring replacement
            elif old_content in current_content:
                if new_content is not None:
                    content_to_write = current_content.replace(old_content, new_content, 1)
                else:
                    content_to_write = current_content
            # Case 3: Stale content conflict
            else:
                raise ValueError(
                    "File changed since proposal generation; old_content does not match current repository state."
                )
        else:
            # Whole file replacement
            content_to_write = new_content if new_content is not None else ""

        target_path.write_text(content_to_write, encoding="utf-8")
        return True

    def delete_file(self, path: str) -> bool:
        """Delete an existing file in the repository."""
        target_path = self.resolve_path(path)
        if not target_path.exists():
            raise FileNotFoundError(f"Cannot delete non-existent file: {path}")
        if not target_path.is_file():
            raise IsADirectoryError(f"Path is a directory, not a file: {path}")
        target_path.unlink()
        return True

    def validate_edit(self, edit: CodeEdit) -> Optional[str]:
        """Validate an individual edit before application.

        Returns:
            Error message if invalid, or None if valid.
        """
        # 1. Path safety and format
        try:
            target_path = self.resolve_path(edit.file_path)
        except (ValueError, PermissionError) as e:
            return f"Invalid or unsafe path: {e}"

        # 2. Action validation
        action = (edit.action or "").lower().strip()
        if action not in self.SUPPORTED_ACTIONS:
            return (
                f"Unsupported action: '{edit.action}'. "
                f"Supported actions are: {sorted(self.SUPPORTED_ACTIONS)}."
            )

        # 3. Action-specific precondition checks
        if action == "create":
            if target_path.exists():
                return f"File already exists for create action: '{edit.file_path}'"

        elif action == "modify":
            if not target_path.exists():
                return f"File does not exist for modify action: '{edit.file_path}'"
            if not target_path.is_file():
                return f"Path is not a regular file for modify action: '{edit.file_path}'"

            # Check stale old_content if provided
            if edit.old_content is not None and edit.old_content.strip() != "":
                current = target_path.read_text(encoding="utf-8", errors="replace")
                if (
                    edit.old_content.strip() != current.strip()
                    and edit.old_content not in current
                ):
                    return (
                        "File changed since proposal generation; "
                        "old_content does not match current repository state."
                    )

        elif action == "delete":
            if not target_path.exists():
                return f"File does not exist for delete action: '{edit.file_path}'"
            if not target_path.is_file():
                return f"Path is not a regular file for delete action: '{edit.file_path}'"

        return None

    def validate_proposal(self, proposal: CodeProposal) -> List[str]:
        """Validate all edits in a CodeProposal without applying changes.

        Returns:
            List of validation error strings (empty if valid).
        """
        errors: List[str] = []
        for idx, edit in enumerate(proposal.changes, 1):
            err = self.validate_edit(edit)
            if err:
                errors.append(f"Edit #{idx} ({edit.file_path}): {err}")
        return errors

    def apply_edit(self, edit: CodeEdit) -> EditResult:
        """Apply a single CodeEdit to the repository."""
        action = (edit.action or "").lower().strip()

        try:
            if action == "create":
                self.create_file(edit.file_path, content=edit.new_content or "")
            elif action == "modify":
                self.modify_file(
                    path=edit.file_path,
                    new_content=edit.new_content,
                    old_content=edit.old_content,
                    diff=edit.diff,
                )
            elif action == "delete":
                self.delete_file(edit.file_path)
            else:
                return EditResult(
                    file_path=edit.file_path,
                    action=edit.action,
                    success=False,
                    error=f"Unsupported action: '{edit.action}'",
                    explanation=edit.explanation,
                )

            return EditResult(
                file_path=edit.file_path,
                action=edit.action,
                success=True,
                explanation=edit.explanation,
            )
        except Exception as e:
            return EditResult(
                file_path=edit.file_path,
                action=edit.action,
                success=False,
                error=str(e),
                explanation=edit.explanation,
            )

    def apply_proposal(
        self,
        proposal: CodeProposal,
        atomic: bool = True,
    ) -> ApplicationResult:
        """Apply all edits in a CodeProposal to the repository.

        Args:
            proposal: CodeProposal to apply.
            atomic: If True, validates all edits before applying any changes.
                    If validation fails, no files are modified.

        Returns:
            ApplicationResult containing applied and failed edits.
        """
        if not proposal.changes:
            return ApplicationResult(success=True)

        # Pre-validation phase (atomic protection)
        if atomic:
            validation_errors = self.validate_proposal(proposal)
            if validation_errors:
                failed = []
                for edit in proposal.changes:
                    err = self.validate_edit(edit)
                    failed.append(
                        EditResult(
                            file_path=edit.file_path,
                            action=edit.action,
                            success=False,
                            error=err or "Validation failed on another edit in atomic batch",
                            explanation=edit.explanation,
                        )
                    )
                return ApplicationResult(
                    success=False,
                    applied_edits=[],
                    failed_edits=failed,
                    errors=validation_errors,
                )

        # Execution phase
        applied: List[EditResult] = []
        failed: List[EditResult] = []
        errors: List[str] = []

        for edit in proposal.changes:
            res = self.apply_edit(edit)
            if res.success:
                applied.append(res)
            else:
                failed.append(res)
                if res.error:
                    errors.append(f"{edit.file_path}: {res.error}")

        success = len(failed) == 0
        return ApplicationResult(
            success=success,
            applied_edits=applied,
            failed_edits=failed,
            errors=errors,
        )
