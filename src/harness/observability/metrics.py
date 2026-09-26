"""Token and API usage tracking, cost estimation, and efficiency analytics."""

from dataclasses import dataclass, field
import json
import time
from typing import Any, Dict, List, Optional


@dataclass
class ModelPricing:
    """Pricing configuration in USD per 1,000 tokens."""

    input_cost_per_1k: float = 0.0009    # Default ~$0.90 per million
    output_cost_per_1k: float = 0.0009   # Default ~$0.90 per million

    @classmethod
    def default_for_model(cls, model_name: str) -> "ModelPricing":
        name = model_name.lower()
        if "70b" in name:
            return cls(input_cost_per_1k=0.0009, output_cost_per_1k=0.0009)
        elif "8b" in name:
            return cls(input_cost_per_1k=0.0002, output_cost_per_1k=0.0002)
        elif "405b" in name:
            return cls(input_cost_per_1k=0.003, output_cost_per_1k=0.003)
        elif "gpt-4o" in name:
            return cls(input_cost_per_1k=0.005, output_cost_per_1k=0.015)
        elif "claude-3-5" in name:
            return cls(input_cost_per_1k=0.003, output_cost_per_1k=0.015)
        return cls()


@dataclass
class ModelCallRecord:
    """Record of a single model inference call."""

    model_name: str
    input_tokens: int
    output_tokens: int
    latency: float = 0.0
    agent_role: Optional[str] = None
    cost: float = 0.0
    timestamp: float = field(default_factory=time.time)


@dataclass
class ToolCallRecord:
    """Record of a single tool execution."""

    tool_name: str
    latency: float = 0.0
    success: bool = True
    agent_role: Optional[str] = None
    timestamp: float = field(default_factory=time.time)


@dataclass
class TaskMetrics:
    """Consolidated metrics and cost tally for a task execution."""

    task_id: str
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    num_model_calls: int = 0
    num_tool_calls: int = 0
    execution_time_seconds: float = 0.0
    estimated_cost_usd: float = 0.0

    # Detailed breakdowns
    agent_breakdown: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    model_calls: List[ModelCallRecord] = field(default_factory=list)
    tool_calls: List[ToolCallRecord] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "num_model_calls": self.num_model_calls,
            "num_tool_calls": self.num_tool_calls,
            "execution_time_seconds": round(self.execution_time_seconds, 3),
            "estimated_cost_usd": round(self.estimated_cost_usd, 6),
            "agent_breakdown": self.agent_breakdown,
        }


class MetricsCollector:
    """Collects token counts, API latency, tool usage, and computes cost estimates."""

    def __init__(self, default_pricing: Optional[ModelPricing] = None) -> None:
        self.default_pricing = default_pricing or ModelPricing()
        self.tasks: Dict[str, TaskMetrics] = {}
        self.current_task_id: str = "default_task"
        self._get_or_create_task(self.current_task_id)

    def set_active_task(self, task_id: str) -> None:
        """Switch or initialize the active task context."""
        self.current_task_id = task_id
        self._get_or_create_task(task_id)

    def _get_or_create_task(self, task_id: str) -> TaskMetrics:
        if task_id not in self.tasks:
            self.tasks[task_id] = TaskMetrics(task_id=task_id)
        return self.tasks[task_id]

    def record_model_call(
        self,
        model_name: str,
        input_tokens: int,
        output_tokens: int,
        latency: float = 0.0,
        agent_role: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> float:
        """Record model inference usage, compute cost, and return the calculated cost in USD."""
        t_id = task_id or self.current_task_id
        task = self._get_or_create_task(t_id)

        pricing = ModelPricing.default_for_model(model_name)
        cost = (
            (input_tokens / 1000.0) * pricing.input_cost_per_1k
            + (output_tokens / 1000.0) * pricing.output_cost_per_1k
        )

        record = ModelCallRecord(
            model_name=model_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency=latency,
            agent_role=agent_role,
            cost=cost,
        )

        task.model_calls.append(record)
        task.input_tokens += input_tokens
        task.output_tokens += output_tokens
        task.total_tokens += (input_tokens + output_tokens)
        task.num_model_calls += 1
        task.estimated_cost_usd += cost

        # Update per-agent breakdown
        role = agent_role or "unknown"
        if role not in task.agent_breakdown:
            task.agent_breakdown[role] = {
                "model_calls": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "cost_usd": 0.0,
                "tool_calls": 0,
            }

        task.agent_breakdown[role]["model_calls"] += 1
        task.agent_breakdown[role]["input_tokens"] += input_tokens
        task.agent_breakdown[role]["output_tokens"] += output_tokens
        task.agent_breakdown[role]["total_tokens"] += (input_tokens + output_tokens)
        task.agent_breakdown[role]["cost_usd"] += cost

        return cost

    def record_tool_call(
        self,
        tool_name: str,
        latency: float = 0.0,
        success: bool = True,
        agent_role: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> None:
        """Record a tool execution."""
        t_id = task_id or self.current_task_id
        task = self._get_or_create_task(t_id)

        record = ToolCallRecord(
            tool_name=tool_name,
            latency=latency,
            success=success,
            agent_role=agent_role,
        )

        task.tool_calls.append(record)
        task.num_tool_calls += 1

        role = agent_role or "unknown"
        if role not in task.agent_breakdown:
            task.agent_breakdown[role] = {
                "model_calls": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "cost_usd": 0.0,
                "tool_calls": 0,
            }
        task.agent_breakdown[role]["tool_calls"] += 1

    def set_execution_time(self, seconds: float, task_id: Optional[str] = None) -> None:
        """Set total execution duration for the task."""
        t_id = task_id or self.current_task_id
        task = self._get_or_create_task(t_id)
        task.execution_time_seconds = seconds

    def get_task_metrics(self, task_id: Optional[str] = None) -> TaskMetrics:
        """Get metrics object for a task."""
        t_id = task_id or self.current_task_id
        return self._get_or_create_task(t_id)

    def compare_tasks(self, task_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """Analyze differences between multiple tasks to detect inefficiencies (e.g. 8 vs 43 model calls)."""
        target_ids = task_ids or list(self.tasks.keys())
        tasks = [self.tasks[tid] for tid in target_ids if tid in self.tasks]

        if not tasks:
            return {"error": "No tasks available to compare"}

        comparison: Dict[str, Any] = {
            "tasks_analyzed": len(tasks),
            "summary": {},
            "inefficiency_flags": [],
        }

        # Calculate averages
        avg_model_calls = sum(t.num_model_calls for t in tasks) / len(tasks)
        avg_tokens = sum(t.total_tokens for t in tasks) / len(tasks)

        for t in tasks:
            comparison["summary"][t.task_id] = {
                "model_calls": t.num_model_calls,
                "tool_calls": t.num_tool_calls,
                "total_tokens": t.total_tokens,
                "cost_usd": round(t.estimated_cost_usd, 5),
                "duration_seconds": round(t.execution_time_seconds, 2),
            }

            # Flag tasks that used significantly more calls than average
            if t.num_model_calls > max(15, avg_model_calls * 1.5):
                comparison["inefficiency_flags"].append({
                    "task_id": t.task_id,
                    "reason": f"High model call volume ({t.num_model_calls} calls vs average {avg_model_calls:.1f})",
                    "suggestion": "Review loop recovery and context selector to reduce redundant retries.",
                })

        return comparison

    def render_summary_table(self, task_id: Optional[str] = None) -> str:
        """Render a readable text summary of token usage and costs."""
        metrics = self.get_task_metrics(task_id)

        lines = [
            f"=== Usage & Observability Report [{metrics.task_id}] ===",
            f"• Total Input Tokens:  {metrics.input_tokens:,}",
            f"• Total Output Tokens: {metrics.output_tokens:,}",
            f"• Combined Tokens:     {metrics.total_tokens:,}",
            f"• Model Calls:         {metrics.num_model_calls}",
            f"• Tool Calls:          {metrics.num_tool_calls}",
            f"• Execution Time:      {metrics.execution_time_seconds:.2f}s",
            f"• Estimated Cost:      ${metrics.estimated_cost_usd:.5f} USD",
        ]

        if metrics.agent_breakdown:
            lines.append("\nBreakdown by Agent Role:")
            for role, stats in metrics.agent_breakdown.items():
                lines.append(
                    f"  - {role:<12}: {stats['model_calls']} model calls | {stats['tool_calls']} tool calls | {stats['total_tokens']:,} tokens | ${stats['cost_usd']:.5f}"
                )

        return "\n".join(lines)
