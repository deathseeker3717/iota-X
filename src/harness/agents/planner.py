"""Planner Agent: Analyzes issue and repo context to produce an implementation plan."""

from typing import Any, Dict, Optional, Union

from harness.agents.prompts import PLANNER_SYSTEM_PROMPT, format_planner_user_prompt
from harness.model.gateway import ModelGateway
from harness.model.schemas import Message, Plan


class PlannerAgent:
    """Agent responsible for high-level architectural planning.
    
    Given a GitHub Issue and repository details, produces a structured Plan containing:
    - Goal
    - Requirements
    - Steps
    - Files to investigate
    - Potential risks
    """

    def __init__(
        self,
        model: ModelGateway,
        temperature: float = 0.1,
    ) -> None:
        self.model = model
        self.temperature = temperature

    def plan(
        self,
        issue: Union[str, Dict[str, Any]],
        repo_info: Optional[Dict[str, Any]] = None,
    ) -> Plan:
        """Generate an implementation plan for the given issue and repository context."""
        if isinstance(issue, str):
            issue_dict = {"title": issue, "description": issue}
        else:
            issue_dict = issue

        user_prompt = format_planner_user_prompt(issue_dict, repo_info)

        messages = [
            Message(role="user", content=user_prompt)
        ]

        # Request structured plan from model gateway
        result_dict = self.model.generate_structured(
            messages=messages,
            schema_cls=Plan,
            system_prompt=PLANNER_SYSTEM_PROMPT,
            temperature=self.temperature,
        )

        if isinstance(result_dict, Plan):
            return result_dict

        # Fallback or construct Plan from dict
        return Plan.from_dict(result_dict)
