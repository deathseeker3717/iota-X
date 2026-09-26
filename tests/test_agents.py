"""Unit and integration tests for Planner, Coder, and Critic agents."""

import json
from typing import Dict, Any

import pytest

from harness.agents import CoderAgent, CriticAgent, PlannerAgent
from harness.model import (
    CodeProposal,
    CriticEvaluation,
    Message,
    ModelGateway,
    ModelInterface,
    ModelRequest,
    ModelResponse,
    Plan,
    ToolCall,
    ToolDefinition,
)


class MockAgentProvider(ModelInterface):
    """Mock model provider returning custom responses based on prompt keywords."""

    def __init__(self) -> None:
        self.last_request = None

    def generate(self, request: ModelRequest) -> ModelResponse:
        self.last_request = request
        system_prompt = request.system_prompt or ""

        if "Lead Software Architect" in system_prompt:
            # Planner response
            plan_json = {
                "goal": "Add pagination support to the /users API endpoint",
                "requirements": [
                    "Support page and limit query parameters",
                    "Default to page=1 and limit=20",
                    "Return paginated metadata (total_count, total_pages)",
                ],
                "steps": [
                    "Update /users endpoint handler in src/routes/users.py",
                    "Add pagination helper query in src/services/user_service.py",
                    "Add unit test for paginated /users endpoint in tests/test_users.py",
                ],
                "files_to_investigate": [
                    "src/routes/users.py",
                    "src/services/user_service.py",
                ],
                "potential_risks": [
                    "Database performance impact without proper offset indexing",
                    "Breaking change if response envelope format is changed",
                ],
            }
            return ModelResponse(content=json.dumps(plan_json))

        elif "Senior Software Engineer" in system_prompt:
            # Coder response
            code_json = {
                "thought_process": "1. What: Add page & limit query params to /users.\n2. Where: src/routes/users.py.\n3. How: Extract query params, pass offset to service layer.",
                "explanation": "Implemented pagination logic with default limit=20 and page=1.",
                "files_to_modify": ["src/routes/users.py"],
                "changes": [
                    {
                        "file_path": "src/routes/users.py",
                        "action": "modify",
                        "explanation": "Add page and limit query params and pass offset to user_service.",
                        "old_content": "@app.get('/users')\ndef get_users():\n    return user_service.get_all()",
                        "new_content": "@app.get('/users')\ndef get_users(page: int = 1, limit: int = 20):\n    offset = (page - 1) * limit\n    users, total = user_service.get_paginated(offset=offset, limit=limit)\n    return {'data': users, 'page': page, 'limit': limit, 'total': total}",
                        "diff": "@@ -1,3 +1,5 @@\n-@app.get('/users')\n-def get_users():\n-    return user_service.get_all()\n+@app.get('/users')\n+def get_users(page: int = 1, limit: int = 20):\n+    offset = (page - 1) * limit\n+    users, total = user_service.get_paginated(offset=offset, limit=limit)\n+    return {'data': users, 'page': page, 'limit': limit, 'total': total}",
                    }
                ],
            }
            return ModelResponse(content=json.dumps(code_json))

        elif "Principal Code Reviewer" in system_prompt:
            # Critic response
            critic_json = {
                "is_acceptable": True,
                "score": 0.95,
                "feedback": "The proposed change cleanly adds pagination to /users with backward compatibility.",
                "unresolved_issues": [],
                "suggestions": ["Consider validating max limit upper bound (e.g. limit <= 100)"],
            }
            return ModelResponse(content=json.dumps(critic_json))

        return ModelResponse(content="{}")


def test_planner_agent():
    provider = MockAgentProvider()
    gateway = ModelGateway(provider=provider)
    planner = PlannerAgent(model=gateway)

    issue = {
        "title": "Add pagination to /users",
        "description": "The /users endpoint currently returns all users at once, causing memory issues.",
    }

    plan = planner.plan(issue)

    assert isinstance(plan, Plan)
    assert plan.goal == "Add pagination support to the /users API endpoint"
    assert len(plan.requirements) == 3
    assert "src/routes/users.py" in plan.files_to_investigate
    assert len(plan.potential_risks) > 0


def test_coder_agent():
    provider = MockAgentProvider()
    gateway = ModelGateway(provider=provider)
    coder = CoderAgent(model=gateway)

    issue = {"title": "Add pagination to /users", "description": "Add page/limit params"}
    plan = Plan(
        goal="Add pagination",
        requirements=["page and limit"],
        steps=["Update route handler"],
        files_to_investigate=["src/routes/users.py"],
    )

    proposal = coder.code(issue=issue, plan=plan)

    assert isinstance(proposal, CodeProposal)
    assert "src/routes/users.py" in proposal.files_to_modify
    assert len(proposal.changes) == 1
    assert proposal.changes[0].action == "modify"
    assert "page: int = 1" in proposal.changes[0].new_content


def test_critic_agent():
    provider = MockAgentProvider()
    gateway = ModelGateway(provider=provider)
    critic = CriticAgent(model=gateway)

    issue = {"title": "Add pagination to /users"}
    proposal = CodeProposal(
        thought_process="Added page and limit params",
        explanation="Added pagination",
        files_to_modify=["src/routes/users.py"],
    )

    evaluation = critic.evaluate(issue=issue, proposal=proposal)

    assert isinstance(evaluation, CriticEvaluation)
    assert evaluation.is_acceptable is True
    assert evaluation.score >= 0.9
    assert len(evaluation.suggestions) > 0


def test_coder_agent_with_tool_execution():
    """Test CoderAgent tool invocation loop."""
    executed_tools = []

    def mock_tool_executor(tool_call: ToolCall) -> str:
        executed_tools.append(tool_call.name)
        return "File content of src/routes/users.py"

    class ToolMockProvider(ModelInterface):
        def __init__(self):
            self.turn = 0

        def generate(self, request: ModelRequest) -> ModelResponse:
            self.turn += 1
            if self.turn == 1:
                # Return tool call first
                return ModelResponse(
                    content="Let me check the file content",
                    tool_calls=[
                        ToolCall(id="call_1", name="read_file", arguments={"path": "src/routes/users.py"})
                    ],
                )
            else:
                # Return final structured response
                code_json = {
                    "thought_process": "Read file and updated endpoint.",
                    "explanation": "Added pagination parameters.",
                    "files_to_modify": ["src/routes/users.py"],
                    "changes": [],
                }
                return ModelResponse(content=json.dumps(code_json))

    gateway = ModelGateway(provider=ToolMockProvider())
    coder = CoderAgent(model=gateway)

    tools = [
        ToolDefinition(name="read_file", description="Read file", parameters={"type": "object"})
    ]

    proposal = coder.code(
        issue="Add pagination to /users",
        tools=tools,
        tool_executor=mock_tool_executor,
    )

    assert "read_file" in executed_tools
    assert proposal.explanation == "Added pagination parameters."


def test_success_criterion_flow():
    """Success criterion end-to-end integration test:
    Given a software issue: 'Add pagination to /users'
    Planner produces a useful implementation plan,
    Coder produces a sensible change,
    Critic evaluates the change.
    """
    provider = MockAgentProvider()
    gateway = ModelGateway(provider=provider)

    planner = PlannerAgent(model=gateway)
    coder = CoderAgent(model=gateway)
    critic = CriticAgent(model=gateway)

    issue = {
        "title": "Add pagination to /users",
        "description": "Support page and limit query parameters on /users endpoint.",
    }

    # 1. Planner Agent
    plan = planner.plan(issue)
    assert plan.goal != ""
    assert len(plan.steps) > 0

    # 2. Coder Agent
    proposal = coder.code(issue=issue, plan=plan)
    assert len(proposal.changes) > 0
    assert "users" in proposal.files_to_modify[0]

    # 3. Critic Agent
    eval_result = critic.evaluate(issue=issue, proposal=proposal, plan=plan)
    assert eval_result.is_acceptable is True
