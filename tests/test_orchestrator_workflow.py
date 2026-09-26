"""Comprehensive tests for the Phase 7 Orchestrator workflow.

Tests the full autonomous loop:
Task -> Planner -> Coder -> CodeProposal -> CodeApplier -> Tests -> Critic -> Verification -> Recovery -> Completed/Failed
"""

import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

from harness.model.schemas import CodeEdit, CodeProposal, CriticEvaluation, Plan
from harness.observability.events import EventBus, EventType
from harness.orchestrator import (
    AdaptiveRouter,
    AgentResult,
    HarnessState,
    HarnessStatus,
    Orchestrator,
    PlanStep,
)
from harness.repository.applier import CodeApplier


def init_git_repo(path: Path) -> None:
    """Helper to initialize a clean git repo in a directory."""
    subprocess.run(["git", "init"], cwd=path, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.name", "Test Harness"], cwd=path, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=path, capture_output=True, check=True)


class MockPlannerAgent:
    def __init__(self, steps: Optional[List[str]] = None, files: Optional[List[str]] = None):
        self.steps = steps or ["Analyze math function", "Fix addition logic"]
        self.files = files or ["src/math_utils.py"]
        self.invocations = 0

    def plan(self, issue: Any, repo_info: Optional[Dict[str, Any]] = None) -> Plan:
        self.invocations += 1
        return Plan(
            goal=str(issue.get("title", "Fix issue")),
            requirements=["Addition must return correct sum"],
            steps=list(self.steps),
            files_to_investigate=self.files,
        )


class MockCoderAgent:
    def __init__(self, proposals: Optional[List[CodeProposal]] = None):
        self.proposals = proposals or []
        self.invocations = 0

    def code(self, issue: Any, plan: Any = None, repo_info: Any = None) -> CodeProposal:
        self.invocations += 1
        if self.proposals:
            idx = min(self.invocations - 1, len(self.proposals) - 1)
            return self.proposals[idx]
        return CodeProposal(
            thought_process="No-op change",
            explanation="Default empty proposal",
            files_to_modify=[],
            changes=[],
        )


class MockCriticAgent:
    def __init__(self, evaluations: Optional[List[CriticEvaluation]] = None):
        self.evaluations = evaluations or []
        self.invocations = 0

    def evaluate(self, issue: Any, proposal: Any, plan: Any = None, repo_info: Any = None, test_results: Any = None) -> CriticEvaluation:
        self.invocations += 1
        if self.evaluations:
            idx = min(self.invocations - 1, len(self.evaluations) - 1)
            return self.evaluations[idx]
        return CriticEvaluation(
            is_acceptable=True,
            score=0.95,
            feedback="Default evaluation: acceptable",
            unresolved_issues=[],
            suggestions=[],
        )


class MockVerifier:
    def __init__(self, outcomes: Optional[List[bool]] = None):
        self.outcomes = outcomes or [True]
        self.invocations = 0

    def verify(self, state: HarnessState) -> Dict[str, Any]:
        self.invocations += 1
        idx = min(self.invocations - 1, len(self.outcomes) - 1)
        passed = self.outcomes[idx]
        return {
            "passed": passed,
            "message": "All tests passed" if passed else "AssertionError: expected a + b but got wrong result",
            "command": "pytest tests/",
            "exit_code": 0 if passed else 1,
        }


def test_orchestrator_successful_code_application_flow():
    """Test 1: Full successful autonomous pipeline modifying working tree, inspecting diff, and completing."""
    with tempfile.TemporaryDirectory() as tmp_str:
        tmp_dir = Path(tmp_str).resolve()
        init_git_repo(tmp_dir)

        # Create initial repository file
        src_dir = tmp_dir / "src"
        src_dir.mkdir(parents=True)
        math_file = src_dir / "math_utils.py"
        initial_content = "def add(a: int, b: int) -> int:\n    return 0\n"
        math_file.write_text(initial_content, encoding="utf-8")

        # Initial commit
        subprocess.run(["git", "add", "."], cwd=tmp_dir, check=True)
        subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=tmp_dir, check=True)
        initial_commit_hash = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=tmp_dir, capture_output=True, text=True, check=True
        ).stdout.strip()

        # Proposal to fix the add function
        fixed_content = "def add(a: int, b: int) -> int:\n    return a + b\n"
        proposal = CodeProposal(
            thought_process="The add function incorrectly returns 0. Change return statement to a + b.",
            explanation="Fix add function to return sum of operands.",
            files_to_modify=["src/math_utils.py"],
            changes=[
                CodeEdit(
                    file_path="src/math_utils.py",
                    action="modify",
                    old_content=initial_content,
                    new_content=fixed_content,
                    explanation="Return sum of a and b",
                )
            ],
        )

        planner = MockPlannerAgent(files=["src/math_utils.py"])
        coder = MockCoderAgent(proposals=[proposal])
        critic = MockCriticAgent(
            evaluations=[
                CriticEvaluation(
                    is_acceptable=True,
                    score=0.98,
                    feedback="Addition implementation is correct and complete.",
                    unresolved_issues=[],
                    suggestions=[],
                )
            ]
        )
        verifier = MockVerifier(outcomes=[True])

        orchestrator = Orchestrator(
            planner=planner,
            coder=coder,
            critic=critic,
            verifier=verifier,
            max_iterations=15,
        )

        # Run orchestrator
        state = orchestrator.run("Fix the addition function in math_utils.py", repo_path=str(tmp_dir))

        # 1. State status
        assert state.status == HarnessStatus.COMPLETED
        assert state.recovery_attempts == 0

        # 2. Proposal applied
        assert state.proposal is not None
        assert state.application_result is not None
        assert state.application_result.success is True
        assert len(state.application_result.applied_edits) == 1
        assert state.changes == ["[MODIFY] src/math_utils.py"]

        # 3. File content on disk was actually modified
        actual_disk_content = math_file.read_text(encoding="utf-8")
        assert actual_disk_content == fixed_content

        # 4. Git diff captured
        assert state.git_diff is not None
        assert "+    return a + b" in state.git_diff
        assert "-    return 0" in state.git_diff

        # 5. Git status captured
        assert state.git_status is not None

        # 6. Safety check: DO NOT AUTO-COMMIT
        # Head commit must remain the initial commit
        current_commit_hash = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=tmp_dir, capture_output=True, text=True, check=True
        ).stdout.strip()
        assert current_commit_hash == initial_commit_hash

        # Working tree must still show uncommitted changes
        status_proc = subprocess.run(
            ["git", "status", "--porcelain"], cwd=tmp_dir, capture_output=True, text=True, check=True
        )
        assert "M src/math_utils.py" in status_proc.stdout

        # 7. Critic result verified
        assert state.critic_result is not None
        assert state.critic_result.is_acceptable is True

        # 8. Summary dict format check
        summary = state.to_summary_dict()
        assert summary["status"] == "COMPLETED"
        assert summary["is_completed"] is True
        assert summary["git_diff"] == state.git_diff
        assert summary["proposal"] is not None
        assert summary["application_result"]["success"] is True
        assert summary["critic_result"]["is_acceptable"] is True


def test_orchestrator_test_failure_triggers_recovery():
    """Test 2: Test failure triggers recovery and a second proposal that passes completes the task."""
    with tempfile.TemporaryDirectory() as tmp_str:
        tmp_dir = Path(tmp_str).resolve()
        init_git_repo(tmp_dir)

        file_path = tmp_dir / "calc.py"
        file_path.write_text("VALUE = 0\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=tmp_dir, check=True)
        subprocess.run(["git", "commit", "-m", "Initial"], cwd=tmp_dir, check=True)

        # Proposal 1: produces wrong value 5
        proposal_1 = CodeProposal(
            thought_process="First try",
            explanation="Set to 5",
            files_to_modify=["calc.py"],
            changes=[
                CodeEdit(
                    file_path="calc.py",
                    action="modify",
                    explanation="Set value to 5",
                    old_content="VALUE = 0\n",
                    new_content="VALUE = 5\n",
                )
            ],
        )
        # Proposal 2 (recovery): produces correct value 10
        proposal_2 = CodeProposal(
            thought_process="Fix value after test failure",
            explanation="Set to 10",
            files_to_modify=["calc.py"],
            changes=[
                CodeEdit(
                    file_path="calc.py",
                    action="modify",
                    explanation="Set value to 10",
                    old_content="VALUE = 5\n",
                    new_content="VALUE = 10\n",
                )
            ],
        )

        planner = MockPlannerAgent(files=["calc.py"])
        coder = MockCoderAgent(proposals=[proposal_1, proposal_2])
        critic = MockCriticAgent(evaluations=[CriticEvaluation(is_acceptable=True, score=1.0, feedback="Good")])
        # Verifier fails first time, passes second time
        verifier = MockVerifier(outcomes=[False, True])

        orchestrator = Orchestrator(
            planner=planner,
            coder=coder,
            critic=critic,
            verifier=verifier,
            max_iterations=15,
        )

        state = orchestrator.run("Set VALUE to 10 in calc.py", repo_path=str(tmp_dir))

        assert state.status == HarnessStatus.COMPLETED
        assert state.recovery_attempts == 1
        assert coder.invocations == 2
        assert file_path.read_text(encoding="utf-8") == "VALUE = 10\n"


def test_orchestrator_recovery_exhaustion_limit():
    """Test 3: Repeated failures exhaust recovery limit and terminate in FAILED status."""
    with tempfile.TemporaryDirectory() as tmp_str:
        tmp_dir = Path(tmp_str).resolve()
        init_git_repo(tmp_dir)

        planner = MockPlannerAgent()
        coder = MockCoderAgent()
        # Verifier always fails
        verifier = MockVerifier(outcomes=[False, False, False, False, False])

        orchestrator = Orchestrator(
            planner=planner,
            coder=coder,
            verifier=verifier,
            max_iterations=15,
        )

        state = orchestrator.run("Fix impossible bug", repo_path=str(tmp_dir))

        assert state.status == HarnessStatus.FAILED
        assert state.recovery_attempts == state.max_recovery_attempts
        assert len(state.errors) > 0


def test_orchestrator_code_applier_failure_cannot_complete():
    """Test 4: Proposal with invalid preconditions (e.g. stale old_content) fails and does not report COMPLETED."""
    with tempfile.TemporaryDirectory() as tmp_str:
        tmp_dir = Path(tmp_str).resolve()
        init_git_repo(tmp_dir)

        file_path = tmp_dir / "service.py"
        file_path.write_text("CURRENT_VERSION = 2\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=tmp_dir, check=True)
        subprocess.run(["git", "commit", "-m", "Initial"], cwd=tmp_dir, check=True)

        # Proposal has stale old_content that does not match CURRENT_VERSION = 2
        stale_proposal = CodeProposal(
            thought_process="Modify with stale content",
            explanation="Update version",
            files_to_modify=["service.py"],
            changes=[
                CodeEdit(
                    file_path="service.py",
                    action="modify",
                    explanation="Bump version with stale old content",
                    old_content="CURRENT_VERSION = 1\n",  # Mismatch!
                    new_content="CURRENT_VERSION = 3\n",
                )
            ],
        )

        planner = MockPlannerAgent(files=["service.py"])
        coder = MockCoderAgent(proposals=[stale_proposal, stale_proposal, stale_proposal, stale_proposal])
        verifier = MockVerifier(outcomes=[True])

        orchestrator = Orchestrator(
            planner=planner,
            coder=coder,
            verifier=verifier,
            max_iterations=10,
        )

        state = orchestrator.run("Bump version to 3", repo_path=str(tmp_dir))

        # Must NOT report COMPLETED
        assert state.status != HarnessStatus.COMPLETED
        assert state.application_result is not None
        assert state.application_result.success is False
        # Target file must remain untouched
        assert file_path.read_text(encoding="utf-8") == "CURRENT_VERSION = 2\n"


def test_orchestrator_invalid_proposal_path_traversal_protection():
    """Test 5: Proposal with path traversal attempt is blocked by sandbox and does not modify filesystem."""
    with tempfile.TemporaryDirectory() as tmp_str:
        tmp_dir = Path(tmp_str).resolve()
        init_git_repo(tmp_dir)

        traversal_proposal = CodeProposal(
            thought_process="Attempt directory traversal",
            explanation="Malicious edit",
            files_to_modify=["../../escape.txt"],
            changes=[
                CodeEdit(
                    file_path="../../escape.txt",
                    action="create",
                    explanation="Path traversal payload",
                    new_content="Escape payload",
                )
            ],
        )

        planner = MockPlannerAgent()
        coder = MockCoderAgent(proposals=[traversal_proposal, traversal_proposal, traversal_proposal])
        verifier = MockVerifier(outcomes=[True])

        orchestrator = Orchestrator(
            planner=planner,
            coder=coder,
            verifier=verifier,
            max_iterations=10,
        )

        state = orchestrator.run("Attempt traversal", repo_path=str(tmp_dir))

        assert state.status != HarnessStatus.COMPLETED
        # Escape file must not exist
        escaped_file = tmp_dir.parent / "escape.txt"
        assert not escaped_file.exists()


def test_orchestrator_critic_rejection_triggers_recovery():
    """Test 6: Critic rejection triggers recovery loop until accepted."""
    with tempfile.TemporaryDirectory() as tmp_str:
        tmp_dir = Path(tmp_str).resolve()
        init_git_repo(tmp_dir)

        target_file = tmp_dir / "greet.py"
        target_file.write_text("def greet(): return 'hi'\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=tmp_dir, check=True)
        subprocess.run(["git", "commit", "-m", "Initial"], cwd=tmp_dir, check=True)

        proposal_1 = CodeProposal(
            thought_process="Incomplete greeting",
            explanation="Say hello",
            files_to_modify=["greet.py"],
            changes=[
                CodeEdit(
                    file_path="greet.py",
                    action="modify",
                    explanation="Basic greet",
                    old_content="def greet(): return 'hi'\n",
                    new_content="def greet(): return 'hello'\n",
                )
            ],
        )
        proposal_2 = CodeProposal(
            thought_process="Complete greeting with name parameter",
            explanation="Add name parameter",
            files_to_modify=["greet.py"],
            changes=[
                CodeEdit(
                    file_path="greet.py",
                    action="modify",
                    explanation="Greet with name",
                    old_content="def greet(): return 'hello'\n",
                    new_content="def greet(name: str): return f'hello {name}'\n",
                )
            ],
        )

        planner = MockPlannerAgent(files=["greet.py"])
        coder = MockCoderAgent(proposals=[proposal_1, proposal_2])
        # Critic rejects first time (missing parameter), approves second time
        critic = MockCriticAgent(
            evaluations=[
                CriticEvaluation(
                    is_acceptable=False,
                    score=0.4,
                    feedback="The requirement specifies adding a name parameter.",
                    unresolved_issues=["Missing name parameter in greet()"],
                    suggestions=["Add name parameter"],
                ),
                CriticEvaluation(
                    is_acceptable=True,
                    score=0.99,
                    feedback="Perfect implementation with name parameter.",
                    unresolved_issues=[],
                    suggestions=[],
                ),
            ]
        )
        verifier = MockVerifier(outcomes=[True, True])

        orchestrator = Orchestrator(
            planner=planner,
            coder=coder,
            critic=critic,
            verifier=verifier,
            max_iterations=15,
        )

        state = orchestrator.run("Update greet to take name parameter", repo_path=str(tmp_dir))

        assert state.status == HarnessStatus.COMPLETED
        assert state.recovery_attempts == 1
        assert critic.invocations == 2
        assert "hello {name}" in target_file.read_text(encoding="utf-8")


def test_orchestrator_observability_event_stream():
    """Test 7: Verify all 16 major workflow transition events are recorded during execution."""
    with tempfile.TemporaryDirectory() as tmp_str:
        tmp_dir = Path(tmp_str).resolve()
        init_git_repo(tmp_dir)

        test_file = tmp_dir / "app.py"
        test_file.write_text("x = 1\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=tmp_dir, check=True)
        subprocess.run(["git", "commit", "-m", "Initial"], cwd=tmp_dir, check=True)

        proposal = CodeProposal(
            thought_process="Update x",
            explanation="Change x to 2",
            files_to_modify=["app.py"],
            changes=[
                CodeEdit(
                    file_path="app.py",
                    action="modify",
                    explanation="Update x value",
                    old_content="x = 1\n",
                    new_content="x = 2\n",
                )
            ],
        )

        event_bus = EventBus()
        captured_events: List[EventType] = []
        event_bus.subscribe(lambda e: captured_events.append(e.event_type))

        planner = MockPlannerAgent(files=["app.py"])
        coder = MockCoderAgent(proposals=[proposal])
        critic = MockCriticAgent(evaluations=[CriticEvaluation(is_acceptable=True, score=1.0, feedback="OK")])
        verifier = MockVerifier(outcomes=[True])

        orchestrator = Orchestrator(
            planner=planner,
            coder=coder,
            critic=critic,
            verifier=verifier,
            event_bus=event_bus,
            max_iterations=10,
        )

        state = orchestrator.run("Update app.py", repo_path=str(tmp_dir))

        assert state.status == HarnessStatus.COMPLETED

        # Check that key Phase 7 events were emitted
        expected_events = [
            EventType.TASK_RECEIVED,
            EventType.PLANNING_STARTED,
            EventType.PLANNING_COMPLETED,
            EventType.CODING_STARTED,
            EventType.PROPOSAL_GENERATED,
            EventType.APPLYING_CHANGES,
            EventType.CHANGES_APPLIED,
            EventType.TESTING_STARTED,
            EventType.TESTS_COMPLETED,
            EventType.CRITIC_STARTED,
            EventType.CRITIC_COMPLETED,
            EventType.VERIFICATION_STARTED,
            EventType.TASK_COMPLETED,
        ]

        for ev in expected_events:
            assert ev in captured_events, f"Expected event {ev} was not emitted. Captured: {captured_events}"
