from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional, Union

from harness.context.manager import ContextManager
from harness.model.gateway import ModelGateway
from harness.model.schemas import CodeProposal, Plan, CriticEvaluation
from harness.observability.events import EventBus, EventType
from harness.observability.logger import AgentTrajectory
from harness.observability.metrics import MetricsCollector
from harness.observability.tracer import ExecutionTracer
from harness.orchestrator.router import AdaptiveRouter
from harness.orchestrator.state import AgentResult, HarnessState, HarnessStatus, PlanStep
from harness.orchestrator.workflow import (
    AgentInterface,
    ContextManagerInterface,
    VerificationInterface,
)
from harness.repository.applier import ApplicationResult, CodeApplier
from harness.tools.git import GitTool
from harness.tools.tests import TestRunnerTool, TestSuiteResult

logger = logging.getLogger(__name__)


class PlannerAgentAdapter:
    """Adapts PlannerAgent to AgentInterface."""

    def __init__(self, planner: Any) -> None:
        self.planner = planner
        self.name = "planner"

    def execute(self, state: HarnessState) -> AgentResult:
        issue = {"title": state.task, "description": state.task}
        repo_info = state.metadata.get("repo_info") or {
            "relevant_files": list(state.relevant_files),
            "context": state.context,
        }
        try:
            plan_obj = self.planner.plan(issue=issue, repo_info=repo_info)
            if hasattr(plan_obj, "steps"):
                state.plan = [
                    PlanStep(
                        step_id=getattr(step, "step_number", idx + 1),
                        description=getattr(step, "description", str(step)),
                    )
                    for idx, step in enumerate(plan_obj.steps)
                ]
            if hasattr(plan_obj, "files_to_investigate") and plan_obj.files_to_investigate:
                for f in plan_obj.files_to_investigate:
                    if f not in state.relevant_files:
                        state.relevant_files.append(f)
            state.metadata["plan_object"] = plan_obj
            return AgentResult(
                agent_name="planner",
                success=True,
                message=f"Plan generated: {getattr(plan_obj, 'goal', state.task)}",
                data={"plan": plan_obj.to_dict() if hasattr(plan_obj, "to_dict") else {}},
            )
        except Exception as e:
            return AgentResult(
                agent_name="planner",
                success=False,
                errors=[f"Planner failed: {e}"],
            )


class CoderAgentAdapter:
    """Adapts CoderAgent to AgentInterface."""

    def __init__(self, coder: Any, applier: Optional[CodeApplier] = None) -> None:
        self.coder = coder
        self.applier = applier
        self.name = "coder"

    def execute(self, state: HarnessState) -> AgentResult:
        issue = {"title": state.task, "description": state.task}
        plan = state.metadata.get("plan_object")
        if not plan and state.plan:
            plan = {"steps": [p.description for p in state.plan]}

        repo_info = state.metadata.get("repo_info") or {
            "relevant_files": list(state.relevant_files),
            "context": state.context,
        }

        # If files exist, attach their content to repo_info so Coder can see original code
        if self.applier and state.relevant_files and "files" not in repo_info:
            file_snippets = []
            for rf in state.relevant_files:
                try:
                    content = self.applier.read_file(rf)
                    file_snippets.append(f"--- {rf} ---\n{content}")
                except Exception:
                    pass
            if file_snippets:
                repo_info["files"] = "\n\n".join(file_snippets)

        # In recovery, pass previous failure details to coder
        if state.recovery_attempts > 0 and state.metadata.get("last_errors"):
            prev_errs = "\n".join(state.metadata["last_errors"])
            issue["description"] = f"{state.task}\n\n[PREVIOUS FAILURE/ERRORS TO RECOVER FROM]:\n{prev_errs}"

        try:
            proposal = self.coder.code(
                issue=issue,
                plan=plan,
                repo_info=repo_info,
            )
            state.proposal = proposal
            state.application_result = None  # Reset for this proposal
            return AgentResult(
                agent_name="coder",
                success=True,
                message=f"CodeProposal generated with {len(proposal.changes)} edit(s)",
                data={"proposal": proposal.to_dict() if hasattr(proposal, "to_dict") else {}},
            )
        except Exception as e:
            return AgentResult(
                agent_name="coder",
                success=False,
                errors=[f"Coder failed: {e}"],
            )


class CriticAgentAdapter:
    """Adapts CriticAgent to AgentInterface."""

    def __init__(self, critic: Any) -> None:
        self.critic = critic
        self.name = "critic"

    def execute(self, state: HarnessState) -> AgentResult:
        issue = {"title": state.task, "description": state.task}
        proposal = state.proposal
        plan = state.metadata.get("plan_object")
        repo_info = state.metadata.get("repo_info") or {
            "relevant_files": list(state.relevant_files),
            "git_diff": state.git_diff,
            "git_status": state.git_status,
        }
        test_results = {
            "tests": list(state.test_results),
            "git_diff": state.git_diff,
        }
        try:
            evaluation = self.critic.evaluate(
                issue=issue,
                proposal=proposal,
                plan=plan,
                repo_info=repo_info,
                test_results=test_results,
            )
            state.critic_result = evaluation
            is_acceptable = getattr(evaluation, "is_acceptable", False)
            return AgentResult(
                agent_name="critic",
                success=is_acceptable,
                message=getattr(evaluation, "feedback", "Critic evaluation completed"),
                data=evaluation.to_dict() if hasattr(evaluation, "to_dict") else {},
                errors=list(getattr(evaluation, "unresolved_issues", [])) if not is_acceptable else [],
            )
        except Exception as e:
            return AgentResult(
                agent_name="critic",
                success=False,
                errors=[f"Critic evaluation failed: {e}"],
            )


def adapt_agent(role: str, agent: Any, applier: Optional[CodeApplier] = None) -> Any:
    """Wraps agent implementations into AgentInterface if needed."""
    if hasattr(agent, "execute"):
        return agent
    if role == "planner" and hasattr(agent, "plan"):
        return PlannerAgentAdapter(agent)
    if role == "coder" and hasattr(agent, "code"):
        return CoderAgentAdapter(agent, applier=applier)
    if role == "critic" and hasattr(agent, "evaluate"):
        return CriticAgentAdapter(agent)
    return agent


class Orchestrator:
    """The central brain controlling execution flow, state, context, observability, and team subsystems."""

    def __init__(
        self,
        model_gateway: Optional[ModelGateway] = None,
        router: Optional[AdaptiveRouter] = None,
        context_manager: Optional[ContextManagerInterface] = None,
        tracer: Optional[ExecutionTracer] = None,
        metrics: Optional[MetricsCollector] = None,
        event_bus: Optional[EventBus] = None,
        max_iterations: int = 25,
        planner: Optional[Any] = None,
        researcher: Optional[Any] = None,
        coder: Optional[Any] = None,
        critic: Optional[Any] = None,
        recovery: Optional[Any] = None,
        tester: Optional[Any] = None,
        verifier: Optional[VerificationInterface] = None,
        applier: Optional[CodeApplier] = None,
        test_runner: Optional[TestRunnerTool] = None,
        git_tool: Optional[GitTool] = None,
    ) -> None:
        self.model_gateway = model_gateway
        self.router = router or AdaptiveRouter()
        self.max_iterations = max_iterations

        # Context Management & Observability Subsystems
        self.context_manager = context_manager or ContextManager()
        self.tracer = tracer or ExecutionTracer()
        self.metrics = metrics or MetricsCollector()
        self.event_bus = event_bus or EventBus()
        self.trajectory: Optional[AgentTrajectory] = None

        # Tools & Infrastructure
        self.applier = applier
        self.test_runner = test_runner
        self.git_tool = git_tool

        # Registry for agents
        self.agents: Dict[str, Any] = {}
        if planner:
            self.register_agent("planner", planner)
        if researcher:
            self.register_agent("researcher", researcher)
        if coder:
            self.register_agent("coder", coder)
        if critic:
            self.register_agent("critic", critic)
        if recovery:
            self.register_agent("recovery", recovery)
        if tester:
            self.register_agent("tester", tester)

        self.critic = self.agents.get("critic")

        # Verification subsystem
        self.verifier: Optional[VerificationInterface] = verifier

    def register_agent(self, role: str, agent: Any) -> None:
        """Register an agent implementation for a specific role/status."""
        adapted = adapt_agent(role, agent, applier=self.applier)
        self.agents[role] = adapted
        if role == "critic":
            self.critic = adapted

    def register_verifier(self, verifier: VerificationInterface) -> None:
        """Register the verification subsystem."""
        self.verifier = verifier

    def run(self, task: str, repo_path: str = ".") -> HarnessState:
        """Execute the complete harness loop given an issue or task description."""
        start_time = time.time()
        task_id = f"task_{int(start_time)}"

        # Ensure tools are initialized for this repo_path if not explicitly provided
        if self.applier is None:
            self.applier = CodeApplier(root_dir=repo_path, enforce_sandbox=True)
        if self.git_tool is None:
            self.git_tool = GitTool(repo_dir=repo_path)
        if self.test_runner is None:
            self.test_runner = TestRunnerTool(repo_dir=repo_path)

        # Update coder adapter's applier if needed
        if "coder" in self.agents and isinstance(self.agents["coder"], CoderAgentAdapter):
            self.agents["coder"].applier = self.applier

        # Initialize state, tracer, metrics, and trajectory
        state = HarnessState(
            task=task,
            repo_path=repo_path,
            max_iterations=self.max_iterations,
        )

        # Set critic_enabled flag in metadata if critic is registered
        has_critic = ("critic" in self.agents) or (self.critic is not None)
        state.metadata["critic_enabled"] = has_critic

        self.tracer = ExecutionTracer(task_name=f"Task: {task[:30]}")
        self.trajectory = AgentTrajectory(task_id=task_id, task_description=task)
        self.metrics.set_active_task(task_id)

        # Observability: TASK_RECEIVED and PHASE_STARTED
        self.event_bus.emit(
            EventType.TASK_RECEIVED,
            data={"task": task, "repo_path": repo_path},
            task_id=task_id,
        )
        self.event_bus.emit(
            EventType.PHASE_STARTED,
            data={"task": task, "repo_path": repo_path},
            task_id=task_id,
        )

        logger.info(f"Starting Orchestrator run for task: {task[:60]}...")

        while not state.is_finished():
            state.iteration += 1

            # 1. Determine next phase via Adaptive Router
            next_status = self.router.route_next(state)
            state.status = next_status

            if state.is_finished():
                break

            # 2. Dispatch to the appropriate subsystem with context & observability
            self._dispatch_phase(state, task_id)

        total_duration = time.time() - start_time
        self.metrics.set_execution_time(total_duration, task_id=task_id)

        # Store observability artifacts in state metadata
        state.metadata["tracer"] = self.tracer
        state.metadata["trace_ascii"] = self.tracer.render_ascii_trace()
        state.metadata["metrics"] = self.metrics.get_task_metrics(task_id)
        state.metadata["metrics_collector"] = self.metrics
        state.metadata["trajectory"] = self.trajectory
        state.metadata["context_manager"] = self.context_manager

        if state.status == HarnessStatus.COMPLETED:
            self.event_bus.emit(
                EventType.TASK_COMPLETED,
                data={"status": state.status.value, "duration": total_duration},
                task_id=task_id,
            )
            self.event_bus.emit(
                EventType.PHASE_COMPLETED,
                data={"status": state.status.value, "duration": total_duration},
                task_id=task_id,
            )
        else:
            self.event_bus.emit(
                EventType.TASK_FAILED,
                data={"status": state.status.value, "errors": state.errors},
                task_id=task_id,
            )
            self.event_bus.emit(
                EventType.PHASE_FAILED,
                data={"status": state.status.value, "errors": state.errors},
                task_id=task_id,
            )

        logger.info(f"Orchestrator run finished with status: {state.status.value}")
        return state

    def _dispatch_phase(self, state: HarnessState, task_id: str = "default_task") -> None:
        """Dispatch control to the corresponding registered agent, tool, or verifier."""
        role_map = {
            HarnessStatus.PLANNING: "planner",
            HarnessStatus.RESEARCHING: "researcher",
            HarnessStatus.CODING: "coder",
            HarnessStatus.CRITIC: "critic",
            HarnessStatus.RECOVERING: "recovery",
        }

        # 1. APPLYING phase (Applying CodeProposal to repository)
        if state.status == HarnessStatus.APPLYING:
            span = self.tracer.start_phase(phase_name="APPLYING", agent_name="applier")
            phase_start = time.time()

            self.event_bus.emit(
                EventType.APPLYING_CHANGES,
                data={"task": state.task, "iteration": state.iteration},
                task_id=task_id,
            )

            if state.proposal is None:
                err = "No CodeProposal available to apply."
                state.errors.append(err)
                self.tracer.end_phase(span, success=False, error=err)
                return

            if self.applier is None:
                err = "Applier tool is required to apply proposals."
                state.errors.append(err)
                self.tracer.end_phase(span, success=False, error=err)
                return

            app_result = self.applier.apply_proposal(state.proposal, atomic=True)
            state.application_result = app_result

            # Update changes list
            for edit_res in app_result.applied_edits:
                state.changes.append(f"[{edit_res.action.upper()}] {edit_res.file_path}")

            # Inspect Git diff and status
            if self.git_tool:
                try:
                    state.git_diff = self.git_tool.git_diff()
                    git_stat = self.git_tool.git_status()
                    state.git_status = git_stat.raw_output
                except Exception as e:
                    logger.warning(f"Git inspection failed: {e}")

            phase_dur = time.time() - phase_start
            if app_result.success:
                self.event_bus.emit(
                    EventType.CHANGES_APPLIED,
                    data={
                        "applied_count": len(app_result.applied_edits),
                        "files_changed": list(state.changes),
                    },
                    task_id=task_id,
                )
                self.tracer.end_phase(span, success=True)
                state.record_agent_result(
                    AgentResult(
                        agent_name="applier",
                        success=True,
                        message=f"Successfully applied {len(app_result.applied_edits)} code change(s)",
                        data=app_result.to_dict(),
                    )
                )
            else:
                state.errors.extend(app_result.errors)
                err_msg = "; ".join(app_result.errors)
                self.tracer.end_phase(span, success=False, error=err_msg)
                state.record_agent_result(
                    AgentResult(
                        agent_name="applier",
                        success=False,
                        errors=list(app_result.errors),
                        data=app_result.to_dict(),
                    )
                )
            return

        # 2. TESTING phase
        if state.status == HarnessStatus.TESTING:
            span = self.tracer.start_phase(phase_name="TESTING", agent_name="testing")
            phase_start = time.time()

            self.event_bus.emit(
                EventType.TESTING_STARTED,
                data={"iteration": state.iteration},
                task_id=task_id,
            )

            if "tester" in self.agents:
                res = self.agents["tester"].execute(state)
                state.record_agent_result(res)
                passed = res.success
                test_output = res.message
            elif self.verifier:
                v_result = self.verifier.verify(state)
                state.test_results.append(v_result)
                passed = v_result.get("passed", False)
                if not passed:
                    state.errors.append(v_result.get("message", "Test verification failed"))
                test_output = v_result.get("message", "")
            elif self.test_runner:
                test_suite_res = self.test_runner.run_tests()
                passed = test_suite_res.success
                t_dict = {
                    "command": f"{test_suite_res.framework} test",
                    "exit_code": 0 if test_suite_res.success else 1,
                    "passed": test_suite_res.success,
                    "total": test_suite_res.total,
                    "passed_count": test_suite_res.passed,
                    "failed_count": test_suite_res.failed,
                    "duration": test_suite_res.duration_seconds,
                    "output": test_suite_res.output,
                }
                state.test_results.append(t_dict)
                if not passed:
                    state.errors.append(
                        f"Tests failed: {test_suite_res.failed} failure(s) out of {test_suite_res.total} tests"
                    )
                test_output = test_suite_res.output
            else:
                passed = True
                test_output = "No tester, verifier, or test_runner configured. Passing tests by default."

            self.event_bus.emit(
                EventType.TESTS_COMPLETED,
                data={"passed": passed, "output": test_output[:200] if test_output else ""},
                task_id=task_id,
            )

            phase_dur = time.time() - phase_start
            self.tracer.end_phase(span, success=passed, error=None if passed else "Tests failed")
            return

        # 3. CRITIC phase
        if state.status == HarnessStatus.CRITIC:
            span = self.tracer.start_phase(phase_name="CRITIC", agent_name="critic")
            phase_start = time.time()

            self.event_bus.emit(
                EventType.CRITIC_STARTED,
                data={"iteration": state.iteration},
                task_id=task_id,
            )

            if "critic" in self.agents:
                agent = self.agents["critic"]
                result = agent.execute(state)
                state.record_agent_result(result)
                is_acceptable = result.success
                if not is_acceptable:
                    if result.errors:
                        state.errors.extend(result.errors)
                    else:
                        state.errors.append(f"Critic rejected proposal: {result.message}")
            else:
                is_acceptable = True
                state.record_agent_result(
                    AgentResult(
                        agent_name="critic",
                        success=True,
                        message="No critic agent registered; skipped.",
                    )
                )

            self.event_bus.emit(
                EventType.CRITIC_COMPLETED,
                data={"is_acceptable": is_acceptable},
                task_id=task_id,
            )

            phase_dur = time.time() - phase_start
            self.tracer.end_phase(
                span,
                success=is_acceptable,
                error=None if is_acceptable else "Critic rejected proposal",
            )
            return

        # 4. VERIFYING phase
        if state.status == HarnessStatus.VERIFYING:
            span = self.tracer.start_phase(phase_name="VERIFYING", agent_name="verifying")
            phase_start = time.time()

            self.event_bus.emit(
                EventType.VERIFICATION_STARTED,
                data={"iteration": state.iteration},
                task_id=task_id,
            )

            if self.verifier:
                v_result = self.verifier.verify(state)
                state.test_results.append(v_result)
                if not v_result.get("passed", False):
                    state.errors.append(v_result.get("message", "Verification failed"))

            # Evidence Verification
            if state.proposal is not None and (
                state.application_result is None or not state.application_result.success
            ):
                state.errors.append("Evidence check: CodeProposal was not applied successfully")

            if state.test_results and any(not t.get("passed", False) for t in state.test_results[-1:]):
                state.errors.append("Evidence check: Latest tests did not pass")

            if state.critic_result is not None and not getattr(state.critic_result, "is_acceptable", False):
                state.errors.append("Evidence check: Critic rejected the solution")

            passed = len(state.errors) == 0
            phase_dur = time.time() - phase_start
            self.tracer.end_phase(
                span,
                success=passed,
                error="; ".join(state.errors) if not passed else None,
            )
            return

        # 5. RECOVERING phase
        if state.status == HarnessStatus.RECOVERING:
            span = self.tracer.start_phase(phase_name="RECOVERING", agent_name="recovery")
            phase_start = time.time()

            state.recovery_attempts += 1
            state.metadata["last_errors"] = list(state.errors)
            state.errors.clear()
            state.application_result = None  # Reset so new proposal can be applied

            self.event_bus.emit(
                EventType.RECOVERY_STARTED,
                data={"attempt": state.recovery_attempts},
                task_id=task_id,
            )
            self.event_bus.emit(
                EventType.RECOVERY_TRIGGERED,
                data={"attempt": state.recovery_attempts},
                task_id=task_id,
            )

            if "recovery" in self.agents:
                rec_agent = self.agents["recovery"]
                rec_res = rec_agent.execute(state)
                state.record_agent_result(rec_res)
            else:
                state.record_agent_result(
                    AgentResult(
                        agent_name="recovery",
                        success=True,
                        message=f"Recovery attempt {state.recovery_attempts} initiated",
                    )
                )

            phase_dur = time.time() - phase_start
            self.tracer.end_phase(span, success=True)
            return

        # 6. Standard Agent dispatch (PLANNING, RESEARCHING, CODING)
        current_role = role_map.get(state.status, state.status.value.lower())
        span = self.tracer.start_phase(phase_name=state.status.value, agent_name=current_role)
        phase_start = time.time()

        if state.status == HarnessStatus.PLANNING:
            self.event_bus.emit(EventType.PLANNING_STARTED, data={"iteration": state.iteration}, task_id=task_id)
        elif state.status == HarnessStatus.RESEARCHING:
            self.event_bus.emit(EventType.RESEARCH_STARTED, data={"iteration": state.iteration}, task_id=task_id)
        elif state.status == HarnessStatus.CODING:
            self.event_bus.emit(EventType.CODING_STARTED, data={"iteration": state.iteration}, task_id=task_id)

        # Context Manager
        if self.context_manager:
            agent_context = self.context_manager.get_context_for_agent(current_role, state)
            state.metadata["current_context"] = agent_context

        if current_role in self.agents:
            agent = self.agents[current_role]
            self.event_bus.emit(
                EventType.AGENT_INVOKED,
                data={"agent": current_role, "iteration": state.iteration},
                task_id=task_id,
            )

            result = agent.execute(state)
            state.record_agent_result(result)

            if state.status == HarnessStatus.PLANNING:
                self.event_bus.emit(EventType.PLANNING_COMPLETED, data={"plan": [p.description for p in state.plan]}, task_id=task_id)
            elif state.status == HarnessStatus.CODING and state.proposal is not None:
                self.event_bus.emit(
                    EventType.PROPOSAL_GENERATED,
                    data={"changes_count": len(getattr(state.proposal, "changes", []))},
                    task_id=task_id,
                )

            # Ingest discoveries and update context manager memory
            if self.context_manager:
                self.context_manager.update_from_state(state)

            phase_dur = time.time() - phase_start
            self.tracer.end_phase(span, success=result.success, error="; ".join(result.errors) if result.errors else None)

            if self.trajectory:
                self.trajectory.record_step(
                    agent=current_role,
                    action=f"execute_{current_role}",
                    inputs={"iteration": state.iteration},
                    outputs={"message": result.message, "success": result.success},
                    success=result.success,
                    duration=phase_dur,
                    error_message="; ".join(result.errors) if result.errors else None,
                )

            self.event_bus.emit(
                EventType.AGENT_COMPLETED if result.success else EventType.AGENT_FAILED,
                data={"agent": current_role, "success": result.success, "message": result.message},
                task_id=task_id,
            )
        else:
            state.record_agent_result(
                AgentResult(
                    agent_name=str(state.status.value),
                    success=True,
                    message=f"No agent registered for {state.status.value}; step recorded.",
                )
            )
            if state.status == HarnessStatus.PLANNING and not state.plan:
                state.plan.append(PlanStep(step_id=1, description=f"Plan for: {state.task}"))
            elif state.status == HarnessStatus.RESEARCHING and not state.relevant_files:
                state.relevant_files.append("src/")

            phase_dur = time.time() - phase_start
            self.tracer.end_phase(span, success=True)
