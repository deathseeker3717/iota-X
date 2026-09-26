"""Agent trajectory logging, execution trace persistence, and post-hoc diagnostics."""

from dataclasses import dataclass, field
import json
import time
from typing import Any, Dict, List, Optional


@dataclass
class TrajectoryStep:
    """A discrete step recorded in the agent's execution trajectory."""

    step_number: int
    agent: str
    action: str
    inputs: Dict[str, Any] = field(default_factory=dict)
    outputs: Dict[str, Any] = field(default_factory=dict)
    success: bool = True
    duration: float = 0.0
    reasoning: Optional[str] = None
    error_message: Optional[str] = None
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_number": self.step_number,
            "agent": self.agent,
            "action": self.action,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "success": self.success,
            "duration": round(self.duration, 3),
            "reasoning": self.reasoning,
            "error_message": self.error_message,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TrajectoryStep":
        return cls(
            step_number=data["step_number"],
            agent=data["agent"],
            action=data["action"],
            inputs=data.get("inputs", {}),
            outputs=data.get("outputs", {}),
            success=data.get("success", True),
            duration=data.get("duration", 0.0),
            reasoning=data.get("reasoning"),
            error_message=data.get("error_message"),
            timestamp=data.get("timestamp", time.time()),
        )


class AgentTrajectory:
    """Sequential record of an agent's reasoning, tool use, and state changes for a task."""

    def __init__(self, task_id: str = "default_task", task_description: str = "") -> None:
        self.task_id = task_id
        self.task_description = task_description
        self.steps: List[TrajectoryStep] = []

    def record_step(
        self,
        agent: str,
        action: str,
        inputs: Optional[Dict[str, Any]] = None,
        outputs: Optional[Dict[str, Any]] = None,
        success: bool = True,
        duration: float = 0.0,
        reasoning: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> TrajectoryStep:
        """Add a step to the execution trajectory."""
        step_number = len(self.steps) + 1
        step = TrajectoryStep(
            step_number=step_number,
            agent=agent,
            action=action,
            inputs=inputs or {},
            outputs=outputs or {},
            success=success,
            duration=duration,
            reasoning=reasoning,
            error_message=error_message,
        )
        self.steps.append(step)
        return step

    def render_trajectory(self) -> str:
        """Render trajectory in the clean, readable format specified for the hackathon."""
        lines = [f"AgentTrajectory [{self.task_id}]"]
        if self.task_description:
            lines.append(f"Task: {self.task_description}\n")

        for step in self.steps:
            lines.append(f"Step {step.step_number}")
            lines.append(f"  Agent: {step.agent}")
            lines.append(f"  Action: {step.action}")

            for k, v in step.inputs.items():
                val_str = str(v)
                if len(val_str) > 80:
                    val_str = val_str[:77] + "..."
                lines.append(f"  {k.capitalize()}: {val_str}")

            if step.reasoning:
                lines.append(f"  Reasoning: {step.reasoning}")

            if not step.success and step.error_message:
                lines.append(f"  Error: {step.error_message}")

            lines.append("")

        return "\n".join(lines).strip()

    def analyze_trajectory(self) -> Dict[str, Any]:
        """Post-hoc analytical inspection: why did the agent succeed or fail?"""
        total_steps = len(self.steps)
        failed_steps = [s for s in self.steps if not s.success]

        # Check for repetitive loops (same agent + action repeating consecutively)
        consecutive_repeats = 0
        for i in range(1, len(self.steps)):
            if (
                self.steps[i].agent == self.steps[i - 1].agent
                and self.steps[i].action == self.steps[i - 1].action
            ):
                consecutive_repeats += 1

        agent_distribution: Dict[str, int] = {}
        for s in self.steps:
            agent_distribution[s.agent] = agent_distribution.get(s.agent, 0) + 1

        diagnosis = {
            "total_steps": total_steps,
            "failed_steps_count": len(failed_steps),
            "agent_distribution": agent_distribution,
            "detected_loops": consecutive_repeats > 2,
            "outcome": "SUCCESS" if (total_steps > 0 and not failed_steps) else ("FAILED" if failed_steps else "EMPTY"),
            "failure_reasons": [s.error_message for s in failed_steps if s.error_message],
        }

        return diagnosis

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "task_description": self.task_description,
            "steps": [s.to_dict() for s in self.steps],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentTrajectory":
        trajectory = cls(
            task_id=data.get("task_id", "default_task"),
            task_description=data.get("task_description", ""),
        )
        trajectory.steps = [TrajectoryStep.from_dict(s) for s in data.get("steps", [])]
        return trajectory

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)
