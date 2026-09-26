"""Schemas for the model gateway."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Message:
    role: str
    content: str


@dataclass
class ToolDefinition:
    name: str
    description: str
    parameters: Dict[str, Any]


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
    extra_params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ModelResponse:
    content: Optional[str] = None
    tool_calls: Optional[List[ToolCall]] = None
    raw_response: Optional[Dict[str, Any]] = None
