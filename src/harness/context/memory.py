"""Multi-tier Memory Architecture for AI Coding Harness.

Provides short-term, task-level (episodic), and repository-level (semantic) memory
to maintain critical context across agent executions while preventing token bloat.
"""

from dataclasses import dataclass, field
from enum import Enum
import json
import time
from typing import Any, Dict, List, Optional, Set


class MemoryTier(str, Enum):
    """Hierarchy of memory persistence and scope."""

    SHORT_TERM = "SHORT_TERM"      # Working memory for the immediate step/action
    TASK = "TASK"                  # Episodic memory for the current issue/task
    REPOSITORY = "REPOSITORY"      # Semantic memory reusable across multiple tasks


@dataclass
class MemoryFact:
    """An atomic piece of learned knowledge or discovery."""

    content: str
    category: str = "general"       # e.g., "architecture", "auth", "bug_location", "test", "convention"
    source_agent: Optional[str] = None
    confidence: float = 1.0
    timestamp: float = field(default_factory=time.time)
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": self.content,
            "category": self.category,
            "source_agent": self.source_agent,
            "confidence": self.confidence,
            "timestamp": self.timestamp,
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryFact":
        return cls(
            content=data["content"],
            category=data.get("category", "general"),
            source_agent=data.get("source_agent"),
            confidence=data.get("confidence", 1.0),
            timestamp=data.get("timestamp", time.time()),
            tags=data.get("tags", []),
        )


@dataclass
class ShortTermMemory:
    """Working memory for current execution step."""

    current_plan_step: Optional[str] = None
    active_files: List[str] = field(default_factory=list)
    recent_tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    recent_errors: List[str] = field(default_factory=list)
    working_diffs: List[str] = field(default_factory=list)
    scratchpad: Dict[str, Any] = field(default_factory=dict)

    def clear(self) -> None:
        self.current_plan_step = None
        self.active_files.clear()
        self.recent_tool_calls.clear()
        self.recent_errors.clear()
        self.working_diffs.clear()
        self.scratchpad.clear()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "current_plan_step": self.current_plan_step,
            "active_files": self.active_files,
            "recent_tool_calls": self.recent_tool_calls,
            "recent_errors": self.recent_errors,
            "working_diffs": self.working_diffs,
            "scratchpad": self.scratchpad,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ShortTermMemory":
        return cls(
            current_plan_step=data.get("current_plan_step"),
            active_files=data.get("active_files", []),
            recent_tool_calls=data.get("recent_tool_calls", []),
            recent_errors=data.get("recent_errors", []),
            working_diffs=data.get("working_diffs", []),
            scratchpad=data.get("scratchpad", {}),
        )


@dataclass
class TaskMemory:
    """Episodic memory captured during the execution of the current issue/task."""

    facts: List[MemoryFact] = field(default_factory=list)
    hypotheses_tested: List[Dict[str, Any]] = field(default_factory=list)
    key_decisions: List[str] = field(default_factory=list)
    discarded_paths: List[str] = field(default_factory=list)

    def add_fact(
        self,
        content: str,
        category: str = "general",
        source_agent: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> MemoryFact:
        fact = MemoryFact(
            content=content,
            category=category,
            source_agent=source_agent,
            tags=tags or [],
        )
        self.facts.append(fact)
        return fact

    def record_decision(self, decision: str) -> None:
        if decision not in self.key_decisions:
            self.key_decisions.append(decision)

    def record_discarded_path(self, reason: str) -> None:
        if reason not in self.discarded_paths:
            self.discarded_paths.append(reason)

    def get_facts_by_category(self, category: str) -> List[MemoryFact]:
        return [f for f in self.facts if f.category == category]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "facts": [f.to_dict() for f in self.facts],
            "hypotheses_tested": self.hypotheses_tested,
            "key_decisions": self.key_decisions,
            "discarded_paths": self.discarded_paths,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaskMemory":
        return cls(
            facts=[MemoryFact.from_dict(f) for f in data.get("facts", [])],
            hypotheses_tested=data.get("hypotheses_tested", []),
            key_decisions=data.get("key_decisions", []),
            discarded_paths=data.get("discarded_paths", []),
        )


@dataclass
class RepositoryMemory:
    """Semantic memory describing the codebase, reusable across multiple tasks."""

    repo_path: str = "."
    architecture_overview: str = ""
    module_descriptions: Dict[str, str] = field(default_factory=dict)
    key_symbols: Dict[str, str] = field(default_factory=dict)  # Symbol name -> definition/purpose
    build_system: Optional[str] = None
    test_framework: Optional[str] = None
    package_manager: Optional[str] = None
    conventions: List[str] = field(default_factory=list)
    environment_variables: List[str] = field(default_factory=list)

    def set_module_description(self, module_name: str, description: str) -> None:
        self.module_descriptions[module_name] = description

    def set_symbol(self, symbol_name: str, details: str) -> None:
        self.key_symbols[symbol_name] = details

    def add_convention(self, convention: str) -> None:
        if convention not in self.conventions:
            self.conventions.append(convention)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "repo_path": self.repo_path,
            "architecture_overview": self.architecture_overview,
            "module_descriptions": self.module_descriptions,
            "key_symbols": self.key_symbols,
            "build_system": self.build_system,
            "test_framework": self.test_framework,
            "package_manager": self.package_manager,
            "conventions": self.conventions,
            "environment_variables": self.environment_variables,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RepositoryMemory":
        return cls(
            repo_path=data.get("repo_path", "."),
            architecture_overview=data.get("architecture_overview", ""),
            module_descriptions=data.get("module_descriptions", {}),
            key_symbols=data.get("key_symbols", {}),
            build_system=data.get("build_system"),
            test_framework=data.get("test_framework"),
            package_manager=data.get("package_manager"),
            conventions=data.get("conventions", []),
            environment_variables=data.get("environment_variables", []),
        )


class AgentMemory:
    """Unified multi-tier memory store combining short-term, task, and repo memory."""

    def __init__(self, repo_path: str = ".") -> None:
        self.short_term = ShortTermMemory()
        self.task = TaskMemory()
        self.repository = RepositoryMemory(repo_path=repo_path)

    def record_fact(
        self,
        content: str,
        category: str = "general",
        source_agent: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> MemoryFact:
        """Record a discovered fact into task memory."""
        return self.task.add_fact(
            content=content,
            category=category,
            source_agent=source_agent,
            tags=tags,
        )

    def record_decision(self, decision: str) -> None:
        """Record an architectural or algorithmic decision."""
        self.task.record_decision(decision)

    def record_discarded_path(self, reason: str) -> None:
        """Record a path or fix attempt that was tried and discarded."""
        self.task.record_discarded_path(reason)

    def update_short_term(
        self,
        plan_step: Optional[str] = None,
        active_files: Optional[List[str]] = None,
        recent_tool_call: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        diff: Optional[str] = None,
    ) -> None:
        """Update active short-term working memory."""
        if plan_step is not None:
            self.short_term.current_plan_step = plan_step
        if active_files is not None:
            self.short_term.active_files = list(active_files)
        if recent_tool_call is not None:
            self.short_term.recent_tool_calls.append(recent_tool_call)
            # Limit recent tool calls in short term memory to last 5
            if len(self.short_term.recent_tool_calls) > 5:
                self.short_term.recent_tool_calls = self.short_term.recent_tool_calls[-5:]
        if error is not None:
            self.short_term.recent_errors.append(error)
            if len(self.short_term.recent_errors) > 5:
                self.short_term.recent_errors = self.short_term.recent_errors[-5:]
        if diff is not None:
            self.short_term.working_diffs.append(diff)

    def get_summary_for_prompt(self, max_facts: int = 8) -> str:
        """Generate a concise prompt-friendly summary of current memory."""
        lines: List[str] = []

        # Repository level memory
        if self.repository.architecture_overview:
            lines.append(f"Architecture: {self.repository.architecture_overview}")
        if self.repository.test_framework:
            lines.append(f"Testing Framework: {self.repository.test_framework}")
        if self.repository.build_system:
            lines.append(f"Build System: {self.repository.build_system}")

        # Task level discoveries
        if self.task.facts:
            lines.append("Key Discoveries:")
            for fact in self.task.facts[-max_facts:]:
                lines.append(f"- [{fact.category}] {fact.content}")

        if self.task.key_decisions:
            lines.append("Key Decisions:")
            for dec in self.task.key_decisions[-4:]:
                lines.append(f"- {dec}")

        if self.task.discarded_paths:
            lines.append("Discarded Attempts (Do not repeat):")
            for disc in self.task.discarded_paths[-3:]:
                lines.append(f"- {disc}")

        # Short-term working context
        if self.short_term.active_files:
            lines.append(f"Active Working Files: {', '.join(self.short_term.active_files)}")

        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize complete memory state."""
        return {
            "short_term": self.short_term.to_dict(),
            "task": self.task.to_dict(),
            "repository": self.repository.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentMemory":
        """Reconstruct memory from serialized dictionary."""
        instance = cls(repo_path=data.get("repository", {}).get("repo_path", "."))
        if "short_term" in data:
            instance.short_term = ShortTermMemory.from_dict(data["short_term"])
        if "task" in data:
            instance.task = TaskMemory.from_dict(data["task"])
        if "repository" in data:
            instance.repository = RepositoryMemory.from_dict(data["repository"])
        return instance

    def to_json(self, indent: int = 2) -> str:
        """Export memory state as JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_json(cls, json_str: str) -> "AgentMemory":
        """Load memory state from JSON string."""
        return cls.from_dict(json.loads(json_str))
