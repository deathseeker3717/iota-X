"""Execution tracer and visual trace rendering for harness performance monitoring."""

from dataclasses import dataclass, field
from enum import Enum
import json
import time
from typing import Any, Dict, List, Optional


class SpanStatus(str, Enum):
    """Lifecycle status of a traced execution span."""

    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


@dataclass
class TraceSpan:
    """Represents a single timed execution span or phase in the harness."""

    span_id: str
    name: str
    agent_name: Optional[str] = None
    status: SpanStatus = SpanStatus.RUNNING
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    duration: float = 0.0
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    parent_id: Optional[str] = None

    def finish(self, success: bool = True, error: Optional[str] = None) -> None:
        """Mark span as finished and calculate duration."""
        self.end_time = time.time()
        self.duration = max(0.0, self.end_time - self.start_time)
        if success:
            self.status = SpanStatus.SUCCESS
        else:
            self.status = SpanStatus.FAILED
            self.error_message = error

    def to_dict(self) -> Dict[str, Any]:
        return {
            "span_id": self.span_id,
            "name": self.name,
            "agent_name": self.agent_name,
            "status": self.status.value,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": round(self.duration, 3),
            "error_message": self.error_message,
            "metadata": self.metadata,
            "parent_id": self.parent_id,
        }


class ExecutionTracer:
    """Collects timed execution spans and renders visual traces."""

    def __init__(self, task_name: str = "Harness Task") -> None:
        self.task_name = task_name
        self.spans: List[TraceSpan] = []
        self._active_spans: Dict[str, TraceSpan] = {}
        self._span_counter = 0

    def start_phase(
        self,
        phase_name: str,
        agent_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> TraceSpan:
        """Start a top-level phase span."""
        self._span_counter += 1
        span_id = f"span_{self._span_counter}_{phase_name}"
        span = TraceSpan(
            span_id=span_id,
            name=phase_name,
            agent_name=agent_name,
            metadata=metadata or {},
        )
        self.spans.append(span)
        self._active_spans[span_id] = span
        self._active_spans[phase_name] = span  # Also index by name for quick lookup
        return span

    def end_phase(
        self,
        span_or_name: Any,
        success: bool = True,
        error: Optional[str] = None,
    ) -> Optional[TraceSpan]:
        """Finish a phase span."""
        span: Optional[TraceSpan] = None
        if isinstance(span_or_name, TraceSpan):
            span = span_or_name
        elif isinstance(span_or_name, str):
            span = self._active_spans.get(span_or_name)

        if span:
            span.finish(success=success, error=error)
            self._active_spans.pop(span.span_id, None)
            self._active_spans.pop(span.name, None)
        return span

    def render_ascii_trace(self, title: Optional[str] = None, width: int = 36) -> str:
        """Render a clean ASCII box showing the execution trace and timings.

        Example Output:
        ┌──────────────────────────────────┐
        │ TASK #42                         │
        ├──────────────────────────────────┤
        │ Planner       ✓  2.4s            │
        │ Repository    ✓  4.1s            │
        │ Coder         ✓  8.7s            │
        │ Tests         ✗  3.2s            │
        │ Recovery      ✓  5.8s            │
        │ Coder         ✓  6.2s            │
        │ Verification  ✓  2.1s            │
        └──────────────────────────────────┘
        """
        box_title = title or self.task_name
        inner_width = max(width - 2, len(box_title) + 2)

        top_border = "┌" + "─" * inner_width + "┐"
        title_line = f"│ {box_title}".ljust(inner_width + 1) + "│"
        sep_border = "├" + "─" * inner_width + "┤"
        bottom_border = "└" + "─" * inner_width + "┘"

        lines = [top_border, title_line, sep_border]

        if not self.spans:
            empty_msg = "(No spans recorded)"
            lines.append(f"│ {empty_msg}".ljust(inner_width + 1) + "│")
        else:
            for span in self.spans:
                raw_name = span.agent_name or span.name
                display_name = raw_name.capitalize()
                if display_name == "Researcher":
                    display_name = "Repository"
                elif display_name in ("Testing", "Verifying"):
                    display_name = "Tests" if display_name == "Testing" else "Verification"
                # Status symbol
                if span.status == SpanStatus.SUCCESS:
                    symbol = "✓"
                elif span.status == SpanStatus.FAILED:
                    symbol = "✗"
                elif span.status == SpanStatus.RUNNING:
                    symbol = "⋯"
                else:
                    symbol = "-"

                dur_str = f"{span.duration:.1f}s" if span.duration > 0 else "<0.1s"

                # Layout: Name (left), Symbol (mid), Duration (right)
                left_col = display_name[:14].ljust(14)
                row_content = f"{left_col} {symbol}  {dur_str:>6}"
                line = f"│ {row_content}".ljust(inner_width + 1) + "│"
                lines.append(line)

        lines.append(bottom_border)
        return "\n".join(lines)

    def get_total_duration(self) -> float:
        """Calculate total execution time across all recorded spans."""
        return sum(s.duration for s in self.spans)

    def to_dict(self) -> Dict[str, Any]:
        """Export trace details to dictionary."""
        return {
            "task_name": self.task_name,
            "total_duration": round(self.get_total_duration(), 3),
            "spans": [s.to_dict() for s in self.spans],
        }

    def to_json(self, indent: int = 2) -> str:
        """Export trace details to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)
