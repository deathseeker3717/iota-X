"""Integration tests for the Orchestrator with Context Management and Observability."""

import pytest

from harness.context import ContextManager
from harness.observability import EventBus, EventType, ExecutionTracer, MetricsCollector
from harness.orchestrator import (
    AdaptiveRouter,
    AgentInterface,
    AgentResult,
    HarnessState,
    HarnessStatus,
    Orchestrator,
    PlanStep,
    VerificationInterface,
)


class MockSmartAgent:
    def __init__(self, name: str):
        self.name = name

    def execute(self, state: HarnessState) -> AgentResult:
        if self.name == "planner":
            state.plan = [
                PlanStep(step_id=1, description="Locate auth module", completed=True),
                PlanStep(step_id=2, description="Fix token refresh error", completed=False),
            ]
            return AgentResult(
                agent_name="planner",
                success=True,
                message="Plan formulated: AuthService handles authentication.",
            )
        elif self.name == "researcher":
            state.relevant_files = ["src/auth.py", "tests/test_auth.py"]
            return AgentResult(
                agent_name="researcher",
                success=True,
                message="Found bug located in src/auth.py. Existing tests are in tests/test_auth.py.",
            )
        elif self.name == "coder":
            state.changes.append("Updated token refresh signature in src/auth.py")
            return AgentResult(
                agent_name="coder",
                success=True,
                message="Applied code changes to src/auth.py.",
            )
        elif self.name == "recovery":
            state.changes.append("Fixed token expiration type conversion")
            return AgentResult(
                agent_name="recovery",
                success=True,
                message="Diagnosed type mismatch error in token refresh.",
            )

        return AgentResult(agent_name=self.name, success=True)


class MockVerificationService:
    def __init__(self, fail_first_time: bool = False):
        self.fail_first_time = fail_first_time
        self.invocations = 0

    def verify(self, state: HarnessState):
        self.invocations += 1
        if self.fail_first_time and self.invocations == 1:
            return {
                "passed": False,
                "message": "AssertionError: Token timestamp was expected to be integer",
            }
        return {"passed": True, "message": "All unit and regression tests passed"}


def test_orchestrator_integration_with_context_and_observability():
    event_bus = EventBus()
    recorded_events = []
    event_bus.subscribe(lambda e: recorded_events.append(e))

    context_manager = ContextManager()
    metrics = MetricsCollector()
    tracer = ExecutionTracer()

    orchestrator = Orchestrator(
        context_manager=context_manager,
        tracer=tracer,
        metrics=metrics,
        event_bus=event_bus,
        max_iterations=12,
    )

    planner = MockSmartAgent("planner")
    researcher = MockSmartAgent("researcher")
    coder = MockSmartAgent("coder")
    recovery = MockSmartAgent("recovery")
    verifier = MockVerificationService(fail_first_time=True)

    orchestrator.register_agent("planner", planner)
    orchestrator.register_agent("researcher", researcher)
    orchestrator.register_agent("coder", coder)
    orchestrator.register_agent("recovery", recovery)
    orchestrator.register_verifier(verifier)

    state = orchestrator.run("Fix issue #42: token refresh throws TypeError")

    # 1. Verify Orchestrator reached completed state
    assert state.status == HarnessStatus.COMPLETED

    # 2. Verify Observability metadata attached to state
    assert "tracer" in state.metadata
    assert "trace_ascii" in state.metadata
    assert "metrics" in state.metadata
    assert "trajectory" in state.metadata
    assert "context_manager" in state.metadata

    # 3. Check ASCII Trace Box
    trace_box = state.metadata["trace_ascii"]
    assert "┌" in trace_box
    assert "└" in trace_box
    assert "Planner" in trace_box
    assert "Tests" in trace_box
    assert "Recovery" in trace_box
    assert "✓" in trace_box
    assert "✗" in trace_box

    # 4. Check Trajectory
    trajectory = state.metadata["trajectory"]
    rendered_traj = trajectory.render_trajectory()
    assert "AgentTrajectory" in rendered_traj
    assert "Step 1" in rendered_traj
    assert "Agent: planner" in rendered_traj or "Agent: Planner" in rendered_traj

    # 5. Check Context Manager Memory Ingestion
    cm = state.metadata["context_manager"]
    assert len(cm.memory.task.facts) > 0
    facts_contents = [f.content for f in cm.memory.task.facts]
    assert any("AuthService handles" in fc or "src/auth.py" in fc for fc in facts_contents)

    # 6. Check Event Bus
    event_types = [e.event_type for e in recorded_events]
    assert EventType.PHASE_STARTED in event_types
    assert EventType.AGENT_INVOKED in event_types
    assert EventType.RECOVERY_TRIGGERED in event_types
    assert EventType.PHASE_COMPLETED in event_types
