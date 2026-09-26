"""Event subsystem for agent lifecycle, telemetry, and pub/sub notifications."""

from dataclasses import dataclass, field
from enum import Enum
import time
from typing import Any, Callable, Dict, List, Optional


class EventType(str, Enum):
    """Enumeration of all lifecycle and operational event types."""

    PHASE_STARTED = "PHASE_STARTED"
    PHASE_COMPLETED = "PHASE_COMPLETED"
    PHASE_FAILED = "PHASE_FAILED"
    AGENT_INVOKED = "AGENT_INVOKED"
    AGENT_COMPLETED = "AGENT_COMPLETED"
    AGENT_FAILED = "AGENT_FAILED"
    TOOL_CALLED = "TOOL_CALLED"
    TOOL_COMPLETED = "TOOL_COMPLETED"
    MODEL_CALLED = "MODEL_CALLED"
    ERROR_OCCURRED = "ERROR_OCCURRED"
    RECOVERY_TRIGGERED = "RECOVERY_TRIGGERED"
    MEMORY_UPDATED = "MEMORY_UPDATED"
    STATE_TRANSITION = "STATE_TRANSITION"


@dataclass
class HarnessEvent:
    """Base event payload captured across harness executions."""

    event_type: EventType
    task_id: str = "default_task"
    timestamp: float = field(default_factory=time.time)
    data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type.value,
            "task_id": self.task_id,
            "timestamp": self.timestamp,
            "data": self.data,
            "metadata": self.metadata,
        }


class EventBus:
    """Publish-Subscribe message broker for harness observability and telemetry."""

    def __init__(self) -> None:
        self._subscribers: Dict[Optional[EventType], List[Callable[[HarnessEvent], None]]] = {}
        self._history: List[HarnessEvent] = []

    def subscribe(
        self,
        callback: Callable[[HarnessEvent], None],
        event_type: Optional[EventType] = None,
    ) -> None:
        """Subscribe a listener to a specific event type, or all events if event_type is None."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)

    def publish(self, event: HarnessEvent) -> None:
        """Publish an event to all interested subscribers."""
        self._history.append(event)

        # 1. Notify specific subscribers
        if event.event_type in self._subscribers:
            for cb in self._subscribers[event.event_type]:
                try:
                    cb(event)
                except Exception:
                    pass

        # 2. Notify global subscribers (subscribed to None)
        if None in self._subscribers:
            for cb in self._subscribers[None]:
                try:
                    cb(event)
                except Exception:
                    pass

    def emit(
        self,
        event_type: EventType,
        data: Optional[Dict[str, Any]] = None,
        task_id: str = "default_task",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> HarnessEvent:
        """Convenience helper to construct and publish an event."""
        event = HarnessEvent(
            event_type=event_type,
            task_id=task_id,
            data=data or {},
            metadata=metadata or {},
        )
        self.publish(event)
        return event

    def get_history(self, event_type: Optional[EventType] = None) -> List[HarnessEvent]:
        """Retrieve recorded event history, optionally filtered by event type."""
        if event_type is None:
            return list(self._history)
        return [e for e in self._history if e.event_type == event_type]

    def clear(self) -> None:
        """Clear event history."""
        self._history.clear()
