"""Unit tests for the Orchestrator, AdaptiveRouter, and HarnessState."""

import pytest

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


class DummyAgent:
    def __init__(self, name: str, success: bool = True, output_data: dict = None):
        self.name = name
        self.success = success
        self.output_data = output_data or {}
        self.invocations = 0

    def execute(self, state: HarnessState) -> AgentResult:
        self.invocations += 1
        if self.name == "planner":
            state.plan = [PlanStep(step_id=1, description="Investigate issue")]
        elif self.name == "researcher":
            state.relevant_files = ["src/main.py"]
        elif self.name == "coder":
            state.changes.append("Fix applied in src/main.py")

        return AgentResult(
            agent_name=self.name,
            success=self.success,
            data=self.output_data,
        )


class DummyVerifier:
    def __init__(self, pass_verification: bool = True):
        self.pass_verification = pass_verification

    def verify(self, state: HarnessState):
        return {
            "passed": self.pass_verification,
            "message": "All tests passed" if self.pass_verification else "Tests failed with assertion error",
        }


def test_state_lifecycle_transitions():
    state = HarnessState(task="Fix issue #42")
    router = AdaptiveRouter()

    assert router.route_next(state) == HarnessStatus.PLANNING

    state.status = HarnessStatus.PLANNING
    # No relevant files yet -> should route to RESEARCHING
    assert router.route_next(state) == HarnessStatus.RESEARCHING

    state.relevant_files = ["src/bug.py"]
    # With relevant files -> should route to CODING
    assert router.route_next(state) == HarnessStatus.CODING

    state.status = HarnessStatus.CODING
    assert router.route_next(state) == HarnessStatus.TESTING


def test_router_adaptive_recovery():
    state = HarnessState(task="Fix issue #42")
    router = AdaptiveRouter()

    state.status = HarnessStatus.TESTING
    state.test_results = [{"passed": False, "message": "SyntaxError"}]

    # Adaptive router should trigger recovery when tests fail
    assert router.route_next(state) == HarnessStatus.RECOVERING


def test_router_max_iterations_limit():
    state = HarnessState(task="Fix issue #42", max_iterations=5)
    state.iteration = 5
    router = AdaptiveRouter()

    assert router.route_next(state) == HarnessStatus.FAILED
    assert any("Exceeded max iterations" in err for err in state.errors)


def test_orchestrator_end_to_end_flow():
    orchestrator = Orchestrator(max_iterations=10)

    planner = DummyAgent("planner")
    researcher = DummyAgent("researcher")
    coder = DummyAgent("coder")
    verifier = DummyVerifier(pass_verification=True)

    orchestrator.register_agent("planner", planner)
    orchestrator.register_agent("researcher", researcher)
    orchestrator.register_agent("coder", coder)
    orchestrator.register_verifier(verifier)

    final_state = orchestrator.run("Fix issue: null pointer on init")

    assert final_state.status == HarnessStatus.COMPLETED
    assert planner.invocations == 1
    assert researcher.invocations == 1
    assert coder.invocations == 1
    assert len(final_state.changes) > 0
    assert len(final_state.test_results) > 0
    assert final_state.test_results[-1]["passed"] is True
