"""Orchestrator state definitions and lifecycle management."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class HarnessStatus(str, Enum):
    """Lifecycle status of the harness execution."""

    INITIALIZING = "INITIALIZING"
    PLANNING = "PLANNING"
    RESEARCHING = "RESEARCHING"
    CODING = "CODING"
    TESTING = "TESTING"
    RECOVERING = "RECOVERING"
    VERIFYING = "VERIFYING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass
class PlanStep:
    """Represents an atomic step in an execution plan."""

    step_id: int
    description: str
    completed: bool = False
    assigned_agent: Optional[str] = None
    output: Optional[str] = None


@dataclass
class AgentResult:
    """Structured result returned by an agent invocation."""

    agent_name: str
    success: bool
    message: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)


@dataclass
class HarnessState:
    """Complete, serializable state of the harness execution.
    
    The orchestrator exclusively mutates and coordinates through this state.
    """

    task: str
    repo_path: str = "."
    status: HarnessStatus = HarnessStatus.INITIALIZING
    current_step_index: int = 0
    iteration: int = 0
    max_iterations: int = 25

    # Planning & Research
    plan: List[PlanStep] = field(default_factory=list)
    relevant_files: List[str] = field(default_factory=list)

    # Agent execution log
    agent_outputs: List[AgentResult] = field(default_factory=list)

    # Modifications & Verifications
    changes: List[str] = field(default_factory=list)
    test_results: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    # Failure recovery tracking
    recovery_attempts: int = 0
    max_recovery_attempts: int = 3

    # Metadata & context bag for teammates' subsystems
    metadata: Dict[str, Any] = field(default_factory=dict)

    def record_agent_result(self, result: AgentResult) -> None:
        """Append an agent output and collect any errors."""
        self.agent_outputs.append(result)
        if result.errors:
            self.errors.extend(result.errors)

    def is_finished(self) -> bool:
        """Check if execution reached terminal state."""
        return self.status in (HarnessStatus.COMPLETED, HarnessStatus.FAILED)
