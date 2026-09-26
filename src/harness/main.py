"""Main entry point for the AI Coding Harness."""

import os
import sys


def main() -> None:
    api_key = os.getenv("AI_API_KEY")
    if not api_key:
        print("Warning: AI_API_KEY environment variable is not set.", file=sys.stderr)
    print("AI Coding Harness initialized.")

    from harness.orchestrator.orchestrator import Orchestrator
    from harness.orchestrator.state import AgentResult, HarnessState
    from harness.orchestrator.workflow import AgentInterface, VerificationInterface

    class MockAgent(AgentInterface):
        def __init__(self, name: str):
            self.name = name

        def execute(self, state: HarnessState) -> AgentResult:
            print(f"[{self.name.upper()}] Running phase...")
            if self.name == "planner":
                from harness.orchestrator.state import PlanStep
                state.plan.append(PlanStep(step_id=1, description="Mock Plan"))
            elif self.name == "researcher":
                state.relevant_files.append("src/main.py")
            elif self.name == "coder" or self.name == "recovery":
                state.changes.append("Mock fix applied")
            elif self.name == "tester":
                pass
            return AgentResult(agent_name=self.name, success=True, message=f"{self.name} completed.")

    class MockVerifier(VerificationInterface):
        def verify(self, state: HarnessState) -> dict:
            print("[VERIFIER] Running verification...")
            return {"passed": True, "message": "All mock tests passed."}

    print("\nStarting simulated workflow...")
    orchestrator = Orchestrator(
        planner=MockAgent("planner"),
        researcher=MockAgent("researcher"),
        coder=MockAgent("coder"),
        recovery=MockAgent("recovery"),
        tester=MockAgent("tester"),
        verifier=MockVerifier()
    )

    final_state = orchestrator.run(task="Fix issue #42: Simulated task")
    print(f"\nWorkflow finished with status: {final_state.status.value}")
    print(f"Iterations: {final_state.iteration}")


if __name__ == "__main__":
    main()
