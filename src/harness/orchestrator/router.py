"""Adaptive routing logic for the Central Orchestrator."""

from typing import Optional

from harness.orchestrator.state import HarnessState, HarnessStatus


class AdaptiveRouter:
    """Decides next execution target based on state rather than a rigid pipeline."""

    def route_next(self, state: HarnessState) -> HarnessStatus:
        """Evaluate current state and determine the next phase/action."""
        # 1. Enforce iteration budget limit
        if state.iteration >= state.max_iterations:
            state.errors.append(f"Exceeded max iterations limit ({state.max_iterations})")
            return HarnessStatus.FAILED

        # 2. Check if we need to recover from active errors
        if state.errors and state.status not in (HarnessStatus.RECOVERING, HarnessStatus.FAILED):
            if state.recovery_attempts < state.max_recovery_attempts:
                return HarnessStatus.RECOVERING
            else:
                return HarnessStatus.FAILED

        # 3. State transitions
        if state.status == HarnessStatus.INITIALIZING:
            # Need a plan first
            return HarnessStatus.PLANNING

        elif state.status == HarnessStatus.PLANNING:
            # Plan generated. If no relevant files identified yet, research repo
            if not state.relevant_files:
                return HarnessStatus.RESEARCHING
            return HarnessStatus.CODING

        elif state.status == HarnessStatus.RESEARCHING:
            # Repository researched and files identified, transition to coding
            return HarnessStatus.CODING

        elif state.status == HarnessStatus.CODING:
            # If proposal was generated and needs application, move to APPLYING
            if state.proposal is not None and state.application_result is None:
                return HarnessStatus.APPLYING
            return HarnessStatus.TESTING

        elif state.status == HarnessStatus.APPLYING:
            # Check application outcome
            if state.application_result is not None and not state.application_result.success:
                if state.recovery_attempts < state.max_recovery_attempts:
                    return HarnessStatus.RECOVERING
                return HarnessStatus.FAILED
            # Application succeeded, move to testing
            return HarnessStatus.TESTING

        elif state.status == HarnessStatus.TESTING:
            # Check test outcome from last recorded results
            last_test_failed = any(
                not t.get("passed", False) for t in state.test_results[-1:]
            ) if state.test_results else False

            if last_test_failed:
                if state.recovery_attempts < state.max_recovery_attempts:
                    return HarnessStatus.RECOVERING
                return HarnessStatus.FAILED

            # Tests passed. If critic is enabled or registered, move to CRITIC
            if state.metadata.get("critic_enabled", False):
                return HarnessStatus.CRITIC
            # Otherwise move to final verification
            return HarnessStatus.VERIFYING

        elif state.status == HarnessStatus.CRITIC:
            # Check critic evaluation
            if state.critic_result is not None:
                is_acceptable = getattr(state.critic_result, "is_acceptable", True)
                if not is_acceptable:
                    if state.recovery_attempts < state.max_recovery_attempts:
                        return HarnessStatus.RECOVERING
                    return HarnessStatus.FAILED

            return HarnessStatus.VERIFYING

        elif state.status == HarnessStatus.RECOVERING:
            # Recovery plan/patch devised. Retest or recode depending on recovery step
            return HarnessStatus.CODING

        elif state.status == HarnessStatus.VERIFYING:
            # Final verification: check for unhandled errors
            has_failed_test = any(
                not t.get("passed", False) for t in state.test_results[-1:]
            ) if state.test_results else False
            if state.errors or has_failed_test:
                if state.recovery_attempts < state.max_recovery_attempts:
                    return HarnessStatus.RECOVERING
                return HarnessStatus.FAILED
            return HarnessStatus.COMPLETED

        return state.status
