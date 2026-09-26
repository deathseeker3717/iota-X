"""Schemas for the model gateway and agent structured outputs."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union


@dataclass
class Message:
    role: str
    content: str
    name: Optional[str] = None
    tool_call_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"role": self.role, "content": self.content}
        if self.name:
            d["name"] = self.name
        if self.tool_call_id:
            d["tool_call_id"] = self.tool_call_id
        return d


@dataclass
class ToolDefinition:
    name: str
    description: str
    parameters: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: Dict[str, Any]


@dataclass
class ModelRequest:
    messages: List[Message]
    system_prompt: Optional[str] = None
    tools: Optional[List[ToolDefinition]] = None
    temperature: float = 0.2
    max_tokens: Optional[int] = None
    response_format: Optional[Dict[str, Any]] = None
    extra_params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ModelResponse:
    content: Optional[str] = None
    tool_calls: Optional[List[ToolCall]] = None
    raw_response: Optional[Dict[str, Any]] = None
    finish_reason: Optional[str] = None


# Structured Outputs for Agents

@dataclass
class Plan:
    """Structured plan output produced by Planner Agent."""
    goal: str
    requirements: List[str] = field(default_factory=list)
    steps: List[str] = field(default_factory=list)
    files_to_investigate: List[str] = field(default_factory=list)
    potential_risks: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "goal": self.goal,
            "requirements": self.requirements,
            "steps": self.steps,
            "files_to_investigate": self.files_to_investigate,
            "potential_risks": self.potential_risks,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Plan":
        return cls(
            goal=data.get("goal", ""),
            requirements=data.get("requirements", []),
            steps=data.get("steps", []),
            files_to_investigate=data.get("files_to_investigate", []),
            potential_risks=data.get("potential_risks", []),
        )


@dataclass
class CodeEdit:
    """Individual code change representation."""
    file_path: str
    action: str  # "create", "modify", "delete"
    explanation: str
    old_content: Optional[str] = None
    new_content: Optional[str] = None
    diff: Optional[str] = None


@dataclass
class CodeProposal:
    """Structured code generation output produced by Coder Agent."""
    thought_process: str
    explanation: str
    files_to_modify: List[str] = field(default_factory=list)
    changes: List[CodeEdit] = field(default_factory=list)
    tool_calls: List[ToolCall] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "thought_process": self.thought_process,
            "explanation": self.explanation,
            "files_to_modify": self.files_to_modify,
            "changes": [
                {
                    "file_path": edit.file_path,
                    "action": edit.action,
                    "explanation": edit.explanation,
                    "old_content": edit.old_content,
                    "new_content": edit.new_content,
                    "diff": edit.diff,
                }
                for edit in self.changes
            ],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CodeProposal":
        changes = []
        for c in data.get("changes", []):
            changes.append(
                CodeEdit(
                    file_path=c.get("file_path", ""),
                    action=c.get("action", "modify"),
                    explanation=c.get("explanation", ""),
                    old_content=c.get("old_content"),
                    new_content=c.get("new_content"),
                    diff=c.get("diff"),
                )
            )
        return cls(
            thought_process=data.get("thought_process", ""),
            explanation=data.get("explanation", ""),
            files_to_modify=data.get("files_to_modify", []),
            changes=changes,
        )


@dataclass
class CriticEvaluation:
    """Structured evaluation output produced by Critic Agent."""
    is_acceptable: bool
    score: float
    feedback: str
    unresolved_issues: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_acceptable": self.is_acceptable,
            "score": self.score,
            "feedback": self.feedback,
            "unresolved_issues": self.unresolved_issues,
            "suggestions": self.suggestions,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CriticEvaluation":
        score_val = data.get("score", 0.0)
        try:
            score = float(score_val)
        except (ValueError, TypeError):
            score = 0.0

        unresolved = data.get("unresolved_issues") or []
        if isinstance(unresolved, str):
            unresolved = [unresolved]

        suggestions = data.get("suggestions") or []
        if isinstance(suggestions, str):
            suggestions = [suggestions]

        return cls(
            is_acceptable=bool(data.get("is_acceptable", False)),
            score=score,
            feedback=str(data.get("feedback", "")),
            unresolved_issues=[str(i) for i in unresolved],
            suggestions=[str(s) for s in suggestions],
        )
