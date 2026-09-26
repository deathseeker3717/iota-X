"""Coding Agent: Performs code reasoning and generates concrete changes using tools."""

from typing import Any, Callable, Dict, List, Optional, Union

from harness.agents.prompts import CODER_SYSTEM_PROMPT, format_coder_user_prompt
from harness.model.gateway import ModelGateway
from harness.model.schemas import CodeProposal, Message, Plan, ToolCall, ToolDefinition


class CoderAgent:
    """Agent responsible for reasoning about code changes and executing tools.
    
    Reasons about:
    - What should change?
    - Where should it change?
    - How should it change?
    """

    def __init__(
        self,
        model: ModelGateway,
        temperature: float = 0.2,
        max_tool_iterations: int = 5,
    ) -> None:
        self.model = model
        self.temperature = temperature
        self.max_tool_iterations = max_tool_iterations

    def code(
        self,
        issue: Union[str, Dict[str, Any]],
        plan: Optional[Union[Plan, Dict[str, Any]]] = None,
        repo_info: Optional[Dict[str, Any]] = None,
        tools: Optional[List[ToolDefinition]] = None,
        tool_executor: Optional[Callable[[ToolCall], str]] = None,
    ) -> CodeProposal:
        """Generate a code implementation proposal using plan and tools."""
        if isinstance(issue, str):
            issue_dict = {"title": issue, "description": issue}
        else:
            issue_dict = issue

        plan_dict = plan.to_dict() if isinstance(plan, Plan) else plan

        history: List[Dict[str, Any]] = []

        # Tool execution loop if tool_executor and tools are available
        if tools and tool_executor:
            iterations = 0
            while iterations < self.max_tool_iterations:
                user_prompt = format_coder_user_prompt(
                    issue=issue_dict,
                    plan=plan_dict,
                    repo_info=repo_info,
                    history=history if history else None,
                )

                messages = [Message(role="user", content=user_prompt)]

                response = self.model.generate(
                    messages=messages,
                    system_prompt=CODER_SYSTEM_PROMPT,
                    tools=tools,
                    temperature=self.temperature,
                )

                # If tool calls returned by model and tool executor is available
                if response.tool_calls:
                    for tc in response.tool_calls:
                        output = tool_executor(tc)
                        history.append({"tool": tc.name, "arguments": tc.arguments, "output": output})
                    iterations += 1
                    continue
                else:
                    # No more tool calls returned, proceed to final structured proposal
                    break

        # Final structured generation
        user_prompt = format_coder_user_prompt(
            issue=issue_dict,
            plan=plan_dict,
            repo_info=repo_info,
            history=history if history else None,
        )

        result_dict = self.model.generate_structured(
            messages=[Message(role="user", content=user_prompt)],
            schema_cls=CodeProposal,
            system_prompt=CODER_SYSTEM_PROMPT,
            temperature=self.temperature,
        )

        if isinstance(result_dict, CodeProposal):
            return result_dict

        return CodeProposal.from_dict(result_dict)
