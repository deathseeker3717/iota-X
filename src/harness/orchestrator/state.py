"""Orchestrator state definitions and lifecycle management."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from harness.model.schemas import CodeProposal, CriticEvaluation
    from harness.repository.applier import ApplicationResult


class HarnessStatus(str, Enum):
    """Lifecycle status of the harness execution."""

    INITIALIZING = "INITIALIZING"
    PLANNING = "PLANNING"
    RESEARCHING = "RESEARCHING"
    CODING = "CODING"
    APPLYING = "APPLYING"
    TESTING = "TESTING"
    CRITIC = "CRITIC"
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

    # Modifications, Proposals & Code Application (Phase 6 & 7)
    proposal: Optional[Any] = None  # Optional[CodeProposal]
    application_result: Optional[Any] = None  # Optional[ApplicationResult]
    critic_result: Optional[Any] = None  # Optional[CriticEvaluation]
    git_diff: Optional[str] = None
    git_status: Optional[str] = None

    changes: List[str] = field(default_factory=list)
    test_results: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    # Failure recovery tracking
    recovery_attempts: int = 0
    max_recovery_attempts: int = 3

    # Metadata & context bag for subsystems
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def repository(self) -> str:
        return self.repo_path

    @property
    def current_step(self) -> int:
        return self.current_step_index

    @property
    def iterations(self) -> int:
        return self.iteration

    @property
    def context(self) -> Dict[str, Any]:
        return self.metadata.get("current_context", {})

    def record_agent_result(self, result: AgentResult) -> None:
        """Append an agent output and collect any errors."""
        self.agent_outputs.append(result)
        if result.errors:
            self.errors.extend(result.errors)

    def is_finished(self) -> bool:
        """Check if execution reached terminal state."""
        return self.status in (HarnessStatus.COMPLETED, HarnessStatus.FAILED)

    def to_summary_dict(self) -> Dict[str, Any]:
        """Produce structured dictionary for UI/API consumption."""
        return {
            "task": self.task,
            "status": self.status.value,
            "current_step": self.current_step_index,
            "iteration": self.iteration,
            "recovery_attempts": self.recovery_attempts,
            "files_investigated": list(self.relevant_files),
            "files_changed": list(self.changes),
            "git_diff": self.git_diff,
            "git_status": self.git_status,
            "proposal": self.proposal.to_dict() if hasattr(self.proposal, "to_dict") else None,
            "application_result": (
                self.application_result.to_dict()
                if hasattr(self.application_result, "to_dict")
                else None
            ),
            "critic_result": (
                {
                    "is_acceptable": getattr(self.critic_result, "is_acceptable", False),
                    "score": getattr(self.critic_result, "score", 0.0),
                    "feedback": getattr(self.critic_result, "feedback", ""),
                    "unresolved_issues": getattr(self.critic_result, "unresolved_issues", []),
                    "suggestions": getattr(self.critic_result, "suggestions", []),
                }
                if self.critic_result is not None
                else None
            ),
            "tests": list(self.test_results),
            "errors": list(self.errors),
            "is_completed": self.status == HarnessStatus.COMPLETED,
        }

