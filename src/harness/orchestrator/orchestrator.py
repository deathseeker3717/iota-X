"""Central Orchestrator implementation for AI Coding Harness."""

import logging
from typing import Dict, Optional

from harness.model.gateway import ModelGateway
from harness.orchestrator.router import AdaptiveRouter
from harness.orchestrator.state import AgentResult, HarnessState, HarnessStatus
from harness.orchestrator.workflow import AgentInterface, VerificationInterface

logger = logging.getLogger(__name__)


class Orchestrator:
    """The central brain controlling execution flow, state, and team subsystems."""

    def __init__(
        self,
        model_gateway: Optional[ModelGateway] = None,
        router: Optional[AdaptiveRouter] = None,
        max_iterations: int = 25,
    ) -> None:
        self.model_gateway = model_gateway
        self.router = router or AdaptiveRouter()
        self.max_iterations = max_iterations

        # Registry for agents (Arnav's agents: planner, research, coder, recovery)
        self.agents: Dict[str, AgentInterface] = {}
        # Verification subsystem (Aryan's verification)
        self.verifier: Optional[VerificationInterface] = None

    def register_agent(self, role: str, agent: AgentInterface) -> None:
        """Register an agent implementation for a specific role/status."""
        self.agents[role] = agent

    def register_verifier(self, verifier: VerificationInterface) -> None:
        """Register the verification subsystem."""
        self.verifier = verifier

    def run(self, task: str, repo_path: str = ".") -> HarnessState:
        """Execute the complete harness loop given an issue or task description."""
        state = HarnessState(
            task=task,
            repo_path=repo_path,
            max_iterations=self.max_iterations,
        )

        logger.info(f"Starting Orchestrator run for task: {task[:60]}...")

        while not state.is_finished():
            state.iteration += 1

            # 1. Determine next phase via Adaptive Router
            next_status = self.router.route_next(state)
            state.status = next_status

            if state.is_finished():
                break

            # 2. Dispatch to the appropriate subsystem
            self._dispatch_phase(state)

        logger.info(f"Orchestrator run finished with status: {state.status.value}")
        return state

    def _dispatch_phase(self, state: HarnessState) -> None:
        """Dispatch control to the corresponding registered agent or verifier."""
        role_map = {
            HarnessStatus.PLANNING: "planner",
            HarnessStatus.RESEARCHING: "researcher",
            HarnessStatus.CODING: "coder",
            HarnessStatus.RECOVERING: "recovery",
        }

        current_role = role_map.get(state.status)

        if current_role and current_role in self.agents:
            agent = self.agents[current_role]
            if state.status == HarnessStatus.RECOVERING:
                state.recovery_attempts += 1
                # Clear active errors to attempt recovery
                state.errors.clear()

            result = agent.execute(state)
            state.record_agent_result(result)

        elif state.status in (HarnessStatus.TESTING, HarnessStatus.VERIFYING):
            if self.verifier:
                v_result = self.verifier.verify(state)
                state.test_results.append(v_result)
                if not v_result.get("passed", False):
                    state.errors.append(v_result.get("message", "Verification failed"))
            else:
                # Stub fallback if verifier not yet registered
                state.test_results.append({"passed": True, "message": "Default verifier passed"})

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
