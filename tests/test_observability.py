"""Comprehensive unit tests for the Observability subsystem."""

import time
import pytest

from harness.observability import (
    AgentTrajectory,
    EventBus,
    EventType,
    ExecutionTracer,
    HarnessEvent,
    MetricsCollector,
    ModelPricing,
    SpanStatus,
    TraceSpan,
    TrajectoryStep,
)


# ---------------------------------------------------------------------------
# 1. ExecutionTracer Tests
# ---------------------------------------------------------------------------


def test_execution_tracer_lifecycle_and_ascii_rendering():
    tracer = ExecutionTracer(task_name="TASK #42")

    s1 = tracer.start_phase("PLANNING", agent_name="Planner")
    time.sleep(0.01)
    tracer.end_phase(s1, success=True)

    s2 = tracer.start_phase("RESEARCHING", agent_name="Repository")
    time.sleep(0.01)
    tracer.end_phase(s2, success=True)

    s3 = tracer.start_phase("TESTING", agent_name="Tests")
    time.sleep(0.01)
    tracer.end_phase(s3, success=False, error="AssertionError")

    s4 = tracer.start_phase("RECOVERING", agent_name="Recovery")
    time.sleep(0.01)
    tracer.end_phase(s4, success=True)

    ascii_box = tracer.render_ascii_trace()

    assert "TASK #42" in ascii_box
    assert "┌" in ascii_box
    assert "└" in ascii_box
    assert "Planner" in ascii_box
    assert "✓" in ascii_box
    assert "Tests" in ascii_box
    assert "✗" in ascii_box
    assert "Recovery" in ascii_box

    # JSON export
    data = tracer.to_dict()
    assert data["task_name"] == "TASK #42"
    assert len(data["spans"]) == 4
    assert data["total_duration"] > 0


# ---------------------------------------------------------------------------
# 2. EventBus Tests
# ---------------------------------------------------------------------------


def test_event_bus_pub_sub_and_filtering():
    bus = EventBus()
    all_events = []
    agent_events = []

    bus.subscribe(lambda e: all_events.append(e), event_type=None)
    bus.subscribe(lambda e: agent_events.append(e), event_type=EventType.AGENT_INVOKED)

    e1 = bus.emit(EventType.PHASE_STARTED, data={"phase": "PLANNING"}, task_id="task_1")
    e2 = bus.emit(EventType.AGENT_INVOKED, data={"agent": "planner"}, task_id="task_1")
    e3 = bus.emit(EventType.AGENT_COMPLETED, data={"agent": "planner"}, task_id="task_1")

    assert len(all_events) == 3
    assert len(agent_events) == 1
    assert agent_events[0].event_type == EventType.AGENT_INVOKED

    history = bus.get_history(EventType.AGENT_INVOKED)
    assert len(history) == 1
    assert history[0].data["agent"] == "planner"

    bus.clear()
    assert len(bus.get_history()) == 0


# ---------------------------------------------------------------------------
# 3. MetricsCollector Tests
# ---------------------------------------------------------------------------


def test_metrics_collector_tokens_cost_and_agent_breakdown():
    collector = MetricsCollector()
    collector.set_active_task("task_auth_fix")

    # Record model call for coder
    cost1 = collector.record_model_call(
        model_name="meta/llama-3.1-70b-instruct",
        input_tokens=1000,
        output_tokens=500,
        latency=1.2,
        agent_role="coder",
    )
    assert cost1 > 0

    # Record model call for recovery
    collector.record_model_call(
        model_name="meta/llama-3.1-70b-instruct",
        input_tokens=800,
        output_tokens=400,
        latency=0.9,
        agent_role="recovery",
    )

    # Record tool calls
    collector.record_tool_call(tool_name="git_diff", latency=0.1, agent_role="coder")
    collector.record_tool_call(tool_name="pytest", latency=2.5, success=True, agent_role="verifier")

    collector.set_execution_time(4.7)

    metrics = collector.get_task_metrics("task_auth_fix")
    assert metrics.input_tokens == 1800
    assert metrics.output_tokens == 900
    assert metrics.total_tokens == 2700
    assert metrics.num_model_calls == 2
    assert metrics.num_tool_calls == 2
    assert metrics.execution_time_seconds == 4.7
    assert metrics.estimated_cost_usd > 0

    assert "coder" in metrics.agent_breakdown
    assert metrics.agent_breakdown["coder"]["model_calls"] == 1
    assert metrics.agent_breakdown["coder"]["tool_calls"] == 1

    # Text report rendering
    table = collector.render_summary_table("task_auth_fix")
    assert "task_auth_fix" in table
    assert "1,800" in table
    assert "900" in table
    assert "coder" in table


def test_metrics_collector_compare_tasks_detects_inefficiency():
    collector = MetricsCollector()

    # Task A: Efficient task (8 model calls)
    collector.set_active_task("task_A")
    for _ in range(8):
        collector.record_model_call(
            model_name="meta/llama-3.1-70b-instruct",
            input_tokens=500,
            output_tokens=200,
            agent_role="coder",
        )

    # Task B: Inefficient runaway task (43 model calls)
    collector.set_active_task("task_B")
    for _ in range(43):
        collector.record_model_call(
            model_name="meta/llama-3.1-70b-instruct",
            input_tokens=500,
            output_tokens=200,
            agent_role="recovery",
        )

    comparison = collector.compare_tasks(["task_A", "task_B"])
    assert comparison["tasks_analyzed"] == 2
    assert "task_A" in comparison["summary"]
    assert "task_B" in comparison["summary"]
    assert comparison["summary"]["task_A"]["model_calls"] == 8
    assert comparison["summary"]["task_B"]["model_calls"] == 43

    flags = comparison["inefficiency_flags"]
    assert len(flags) > 0
    assert any(f["task_id"] == "task_B" for f in flags)


# ---------------------------------------------------------------------------
# 4. AgentTrajectory Tests
# ---------------------------------------------------------------------------


def test_agent_trajectory_recording_and_rendering():
    trajectory = AgentTrajectory(task_id="issue_42", task_description="Fix authentication token refresh")

    trajectory.record_step(
        agent="Planner",
        action="create_plan",
        inputs={"task": "Fix authentication token refresh"},
        outputs={"plan": "Step 1: search_files"},
        success=True,
    )

    trajectory.record_step(
        agent="Repository",
        action="search_files",
        inputs={"query": "authentication"},
        outputs={"matches": ["src/auth.py"]},
        success=True,
    )

    trajectory.record_step(
        agent="Coder",
        action="edit_file",
        inputs={"file": "src/auth.py"},
        outputs={"changes": "applied patch"},
        success=True,
    )

    trajectory.record_step(
        agent="Tool",
        action="run_tests",
        outputs={"passed": False},
        success=False,
        error_message="TestAuth::test_token_refresh failed",
    )

    trajectory.record_step(
        agent="Recovery",
        action="diagnose_failure",
        reasoning="Token expiration format was Unix timestamp instead of ISO format.",
        success=True,
    )

    rendered = trajectory.render_trajectory()
    assert "AgentTrajectory [issue_42]" in rendered
    assert "Step 1" in rendered
    assert "Agent: Planner" in rendered
    assert "Action: create_plan" in rendered
    assert "Step 2" in rendered
    assert "Agent: Repository" in rendered
    assert 'Query: authentication' in rendered
    assert "Step 3" in rendered
    assert "Agent: Coder" in rendered
    assert "Step 4" in rendered
    assert "Agent: Tool" in rendered
    assert "Step 5" in rendered
    assert "Agent: Recovery" in rendered
    assert "Reasoning: Token expiration format" in rendered

    # Trajectory analysis
    diagnosis = trajectory.analyze_trajectory()
    assert diagnosis["total_steps"] == 5
    assert diagnosis["failed_steps_count"] == 1
    assert "TestAuth::test_token_refresh failed" in diagnosis["failure_reasons"]

    # Serialization roundtrip
    data = trajectory.to_dict()
    restored = AgentTrajectory.from_dict(data)
    assert len(restored.steps) == 5
    assert restored.steps[0].agent == "Planner"
    assert restored.steps[4].agent == "Recovery"
