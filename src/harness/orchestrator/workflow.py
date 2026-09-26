"""Subsystem interfaces and workflow contracts for team integration."""

from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

from harness.orchestrator.state import AgentResult, HarnessState


@runtime_checkable
class AgentInterface(Protocol):
    """Contract for Arnav's agents (Planner, Research, Coder, Recovery, etc.)."""

    name: str

    def execute(self, state: HarnessState) -> AgentResult:
        """Execute agent action given the current harness state and return structured result."""
        ...


@runtime_checkable
class ToolLayerInterface(Protocol):
    """Contract for Shaurya's shared tool layer (file edits, bash execution, git)."""

    def read_file(self, path: str) -> str:
        ...

    def write_file(self, path: str, content: str) -> bool:
        ...

    def execute_command(self, cmd: str, cwd: str = ".") -> Dict[str, Any]:
        ...


@runtime_checkable
class VerificationInterface(Protocol):
    """Contract for verification subsystems."""

    def verify(self, state: HarnessState) -> Dict[str, Any]:
        """Run verification suite, checks, and regression tests."""
        ...


@runtime_checkable
class ContextManagerInterface(Protocol):
    """Contract for Aryan's Context Management subsystem."""

    def get_context_for_agent(self, role: str, state: HarnessState, token_budget: Optional[int] = None) -> Any:
        ...

    def update_from_state(self, state: HarnessState) -> None:
        ...

    def record_discovery(self, fact: str, category: str = "general", source_agent: Optional[str] = None) -> Any:
        ...
