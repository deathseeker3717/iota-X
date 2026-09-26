"""Critic Agent: Evaluates proposed code implementations against issue requirements."""

from typing import Any, Dict, Optional, Union

from harness.agents.prompts import CRITIC_SYSTEM_PROMPT, format_critic_user_prompt
from harness.model.gateway import ModelGateway
from harness.model.schemas import CodeProposal, CriticEvaluation, Message, Plan


class CriticAgent:
    """Agent responsible for code review and verification of proposed solutions.
    
    Evaluates:
    - Does this actually solve the issue?
    - Is it complete and free of regression risks?
    - Separate from automated testing.
    """

    def __init__(
        self,
        model: ModelGateway,
        temperature: float = 0.1,
    ) -> None:
        self.model = model
        self.temperature = temperature

    def evaluate(
        self,
        issue: Union[str, Dict[str, Any]],
        proposal: Union[CodeProposal, Dict[str, Any]],
        plan: Optional[Union[Plan, Dict[str, Any]]] = None,
        repo_info: Optional[Dict[str, Any]] = None,
        test_results: Optional[Union[str, Dict[str, Any]]] = None,
    ) -> CriticEvaluation:
        """Evaluate a proposed code implementation."""
        if isinstance(issue, str):
            issue_dict = {"title": issue, "description": issue}
        else:
            issue_dict = issue

        proposal_dict = proposal.to_dict() if isinstance(proposal, CodeProposal) else proposal
        plan_dict = plan.to_dict() if isinstance(plan, Plan) else plan

        user_prompt = format_critic_user_prompt(
            issue=issue_dict,
            proposal=proposal_dict,
            plan=plan_dict,
            repo_info=repo_info,
            test_results=test_results,
        )

        messages = [Message(role="user", content=user_prompt)]

        result_dict = self.model.generate_structured(
            messages=messages,
            schema_cls=CriticEvaluation,
            system_prompt=CRITIC_SYSTEM_PROMPT,
            temperature=self.temperature,
        )

        if isinstance(result_dict, CriticEvaluation):
            return result_dict

        return CriticEvaluation.from_dict(result_dict)
