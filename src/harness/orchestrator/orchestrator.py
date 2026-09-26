"""Central Orchestrator implementation for AI Coding Harness."""

import logging
import time
from typing import Any, Dict, Optional

from harness.context.manager import ContextManager
from harness.model.gateway import ModelGateway
from harness.observability.events import EventBus, EventType
from harness.observability.logger import AgentTrajectory
from harness.observability.metrics import MetricsCollector
from harness.observability.tracer import ExecutionTracer
from harness.orchestrator.router import AdaptiveRouter
from harness.orchestrator.state import AgentResult, HarnessState, HarnessStatus
from harness.orchestrator.workflow import (
    AgentInterface,
    ContextManagerInterface,
    VerificationInterface,
)

logger = logging.getLogger(__name__)


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
    ) -> None:
        self.model_gateway = model_gateway
        self.router = router or AdaptiveRouter()
        self.max_iterations = max_iterations

        # Context Management & Observability Subsystems (Aryan)
        self.context_manager = context_manager or ContextManager()
        self.tracer = tracer or ExecutionTracer()
        self.metrics = metrics or MetricsCollector()
        self.event_bus = event_bus or EventBus()
        self.trajectory: Optional[AgentTrajectory] = None

        # Registry for agents (Arnav's agents: planner, research, coder, recovery)
        self.agents: Dict[str, AgentInterface] = {}
        # Verification subsystem
        self.verifier: Optional[VerificationInterface] = None

    def register_agent(self, role: str, agent: AgentInterface) -> None:
        """Register an agent implementation for a specific role/status."""
        self.agents[role] = agent

    def register_verifier(self, verifier: VerificationInterface) -> None:
        """Register the verification subsystem."""
        self.verifier = verifier

    def run(self, task: str, repo_path: str = ".") -> HarnessState:
        """Execute the complete harness loop given an issue or task description."""
        start_time = time.time()
        task_id = f"task_{int(start_time)}"
        
        # Initialize state, tracer, metrics, and trajectory
        state = HarnessState(
            task=task,
            repo_path=repo_path,
            max_iterations=self.max_iterations,
        )

        self.tracer = ExecutionTracer(task_name=f"Task: {task[:30]}")
        self.trajectory = AgentTrajectory(task_id=task_id, task_description=task)
        self.metrics.set_active_task(task_id)

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
                EventType.PHASE_COMPLETED,
                data={"status": state.status.value, "duration": total_duration},
                task_id=task_id,
            )
        else:
            self.event_bus.emit(
                EventType.PHASE_FAILED,
                data={"status": state.status.value, "errors": state.errors},
                task_id=task_id,
            )

        logger.info(f"Orchestrator run finished with status: {state.status.value}")
        return state

    def _dispatch_phase(self, state: HarnessState, task_id: str = "default_task") -> None:
        """Dispatch control to the corresponding registered agent or verifier with full context and tracing."""
        role_map = {
            HarnessStatus.PLANNING: "planner",
            HarnessStatus.RESEARCHING: "researcher",
            HarnessStatus.CODING: "coder",
            HarnessStatus.RECOVERING: "recovery",
        }

        current_role = role_map.get(state.status, state.status.value.lower())
        span = self.tracer.start_phase(phase_name=state.status.value, agent_name=current_role)
        phase_start = time.time()

        # Aryan's Context Manager determines the tailored context for the agent
        if self.context_manager:
            agent_context = self.context_manager.get_context_for_agent(current_role, state)
            state.metadata["current_context"] = agent_context

        if current_role in self.agents:
            agent = self.agents[current_role]
            if state.status == HarnessStatus.RECOVERING:
                state.recovery_attempts += 1
                state.errors.clear()
                self.event_bus.emit(
                    EventType.RECOVERY_TRIGGERED,
                    data={"attempt": state.recovery_attempts},
                    task_id=task_id,
                )

            self.event_bus.emit(
                EventType.AGENT_INVOKED,
                data={"agent": current_role, "iteration": state.iteration},
                task_id=task_id,
            )

            result = agent.execute(state)
            state.record_agent_result(result)

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

        elif state.status in (HarnessStatus.TESTING, HarnessStatus.VERIFYING):
            if self.verifier:
                v_result = self.verifier.verify(state)
                state.test_results.append(v_result)
                passed = v_result.get("passed", False)
                if not passed:
                    state.errors.append(v_result.get("message", "Verification failed"))
            else:
                # Stub fallback if verifier not yet registered
                v_result = {"passed": True, "message": "Default verifier passed"}
                state.test_results.append(v_result)
                passed = True

            msg = v_result.get("message")
            error_msg = str(msg) if msg is not None else None

            phase_dur = time.time() - phase_start
            self.tracer.end_phase(span, success=passed, error=error_msg if not passed else None)

            if self.trajectory:
                self.trajectory.record_step(
                    agent="verifier",
                    action="verify_state",
                    inputs={"changes": list(state.changes)},
                    outputs=v_result,
                    success=passed,
                    duration=phase_dur,
                    error_message=error_msg if not passed else None,
                )

        else:
            # Role not registered yet; gracefully log or mark progress
            state.record_agent_result(
                AgentResult(
                    agent_name=str(state.status.value),
                    success=True,
                    message=f"No agent registered for {state.status.value}; step recorded.",
                )
            )
            # Default progression if no agent registered
            if state.status == HarnessStatus.PLANNING and not state.plan:
                from harness.orchestrator.state import PlanStep
                state.plan.append(PlanStep(step_id=1, description=f"Plan for: {state.task}"))
            elif state.status == HarnessStatus.RESEARCHING and not state.relevant_files:
                state.relevant_files.append("src/")

            phase_dur = time.time() - phase_start
            self.tracer.end_phase(span, success=True)
