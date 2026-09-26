"""Unit and integration tests for Planner, Coder, and Critic agents."""

import json
import os
from typing import Dict, Any

import pytest

from harness.agents import CoderAgent, CriticAgent, PlannerAgent
from harness.model import (
    CodeEdit,
    CodeProposal,
    CriticEvaluation,
    Message,
    ModelGateway,
    ModelInterface,
    ModelRequest,
    ModelResponse,
    OllamaClient,
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


def test_planner_agent_with_markdown_json():
    """Verify PlannerAgent correctly parses JSON wrapped in markdown code blocks."""
    plan_dict = {
        "goal": "Refactor database connection pool",
        "requirements": ["Use connection pooling", "Set max connections to 20"],
        "steps": ["Update config", "Instantiate pool"],
        "files_to_investigate": ["src/db.py"],
        "potential_risks": ["Pool exhaustion if connections are not returned"],
    }
    markdown_content = f"Here is the plan:\n```json\n{json.dumps(plan_dict, indent=2)}\n```\nGood luck!"

    class MarkdownMockProvider(ModelInterface):
        def generate(self, request: ModelRequest) -> ModelResponse:
            return ModelResponse(content=markdown_content)

    gateway = ModelGateway(provider=MarkdownMockProvider())
    planner = PlannerAgent(model=gateway)

    plan = planner.plan({"title": "Refactor DB", "description": "Add connection pool"})
    assert isinstance(plan, Plan)
    assert plan.goal == "Refactor database connection pool"
    assert len(plan.requirements) == 2
    assert "src/db.py" in plan.files_to_investigate
    assert len(plan.potential_risks) == 1


def test_planner_agent_with_string_issue_and_repo_context():
    """Verify PlannerAgent handles string issue input and repository context."""
    last_req = None

    class CaptureMockProvider(ModelInterface):
        def generate(self, request: ModelRequest) -> ModelResponse:
            nonlocal last_req
            last_req = request
            return ModelResponse(
                content=json.dumps({
                    "goal": "Implement rate limiting",
                    "requirements": ["Limit to 60 req/min"],
                    "steps": ["Add middleware"],
                    "files_to_investigate": ["src/middleware.py"],
                    "potential_risks": ["False positives"],
                })
            )

    gateway = ModelGateway(provider=CaptureMockProvider())
    planner = PlannerAgent(model=gateway)

    plan = planner.plan(
        issue="Implement rate limiting on /api",
        repo_info={
            "tree": "src/\n  middleware.py\n  api.py",
            "files": "middleware.py",
            "context": "FastAPI application",
        },
    )

    assert isinstance(plan, Plan)
    assert plan.goal == "Implement rate limiting"
    assert last_req is not None
    user_prompt = last_req.messages[0].content
    assert "Implement rate limiting on /api" in user_prompt
    assert "Directory Structure:" in user_prompt
    assert "FastAPI application" in user_prompt


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


def test_coder_agent_with_markdown_json():
    """Verify CoderAgent correctly parses JSON wrapped in markdown code blocks."""
    code_dict = {
        "thought_process": "Refactored pool size handling.",
        "explanation": "Updated connection pool limit to 20.",
        "files_to_modify": ["src/db.py"],
        "changes": [
            {
                "file_path": "src/db.py",
                "action": "modify",
                "explanation": "Increase max connections to 20",
                "old_content": "MAX_CONNS = 5",
                "new_content": "MAX_CONNS = 20",
                "diff": None,
            }
        ],
    }
    markdown_content = f"Here is the proposed code change:\n```json\n{json.dumps(code_dict, indent=2)}\n```\nAll done!"

    class MarkdownCodeMockProvider(ModelInterface):
        def generate(self, request: ModelRequest) -> ModelResponse:
            return ModelResponse(content=markdown_content)

    gateway = ModelGateway(provider=MarkdownCodeMockProvider())
    coder = CoderAgent(model=gateway)

    proposal = coder.code(
        issue={"title": "Increase pool", "description": "Increase max connections"},
        plan=Plan(goal="Increase max connections", requirements=["MAX_CONNS=20"]),
    )

    assert isinstance(proposal, CodeProposal)
    assert proposal.explanation == "Updated connection pool limit to 20."
    assert len(proposal.changes) == 1
    assert proposal.changes[0].file_path == "src/db.py"
    assert proposal.changes[0].new_content == "MAX_CONNS = 20"


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


def test_critic_agent_with_markdown_json():
    """Verify CriticAgent correctly parses JSON wrapped in markdown code blocks."""
    critic_dict = {
        "is_acceptable": True,
        "score": 0.88,
        "feedback": "Clean implementation with solid test coverage.",
        "unresolved_issues": [],
        "suggestions": ["Add type annotations to helper function"],
    }
    markdown_content = f"Here is the evaluation:\n```json\n{json.dumps(critic_dict, indent=2)}\n```\nLGTM!"

    class MarkdownCriticMockProvider(ModelInterface):
        def generate(self, request: ModelRequest) -> ModelResponse:
            return ModelResponse(content=markdown_content)

    gateway = ModelGateway(provider=MarkdownCriticMockProvider())
    critic = CriticAgent(model=gateway)

    evaluation = critic.evaluate(
        issue={"title": "Fix bug", "description": "Fix memory leak"},
        proposal=CodeProposal(thought_process="Fixed leak", explanation="Fixed", files_to_modify=["leak.py"]),
    )

    assert isinstance(evaluation, CriticEvaluation)
    assert evaluation.is_acceptable is True
    assert evaluation.score == 0.88
    assert "type annotations" in evaluation.suggestions[0]


def test_critic_agent_with_test_results_and_repo_info():
    """Verify CriticAgent formats user prompt with repo info and test failure results."""
    last_req = None

    class CaptureCriticMockProvider(ModelInterface):
        def generate(self, request: ModelRequest) -> ModelResponse:
            nonlocal last_req
            last_req = request
            return ModelResponse(
                content=json.dumps({
                    "is_acceptable": False,
                    "score": 0.3,
                    "feedback": "Tests failed because of missing route parameter.",
                    "unresolved_issues": ["TypeError in get_items"],
                    "suggestions": ["Pass tag parameter"],
                })
            )

    gateway = ModelGateway(provider=CaptureCriticMockProvider())
    critic = CriticAgent(model=gateway)

    evaluation = critic.evaluate(
        issue={"title": "Add tag filtering", "description": "Filter by tag"},
        proposal=CodeProposal(thought_process="Implemented", explanation="Added route", files_to_modify=["routes.py"]),
        plan=Plan(goal="Tag filtering", requirements=["Optional tag"]),
        repo_info={"context": "FastAPI service"},
        test_results={
            "status": "failed",
            "output": "FAILED tests/test_routes.py::test_get_items",
            "failures": "TypeError: get_items() got an unexpected keyword argument 'tag'",
        },
    )

    assert isinstance(evaluation, CriticEvaluation)
    assert evaluation.is_acceptable is False
    assert evaluation.score == 0.3
    assert last_req is not None
    user_prompt = last_req.messages[0].content
    assert "FastAPI service" in user_prompt
    assert "TEST / EXECUTION RESULTS" in user_prompt
    assert "TypeError: get_items() got an unexpected keyword argument 'tag'" in user_prompt


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


@pytest.mark.skipif(
    not os.getenv("ENABLE_OLLAMA_INTEGRATION_TESTS"),
    reason="Ollama integration test disabled. Set ENABLE_OLLAMA_INTEGRATION_TESTS=1 to run.",
)
def test_planner_agent_live_ollama_integration():
    """Live integration test: User/GitHub issue -> PlannerAgent -> ModelGateway -> OllamaClient -> gpt-oss:20b -> Plan."""
    client = OllamaClient(model_name="gpt-oss:20b")
    gateway = ModelGateway(provider=client)
    planner = PlannerAgent(model=gateway)

    issue = {
        "title": "Fix off-by-one error in pagination calculation",
        "description": (
            "When calculating total pages for items = 10 and page_size = 5, "
            "it works, but for items = 11 it returns 2 instead of 3. "
            "Use math.ceil or integer ceiling formula."
        ),
    }

    plan = planner.plan(
        issue=issue,
        repo_info={
            "files": ["src/pagination.py", "tests/test_pagination.py"],
            "context": "Python library for API utilities",
        },
    )

    assert isinstance(plan, Plan)
    assert isinstance(plan.goal, str) and len(plan.goal) > 0
    assert isinstance(plan.requirements, list) and len(plan.requirements) > 0
    assert isinstance(plan.steps, list) and len(plan.steps) > 0
    assert isinstance(plan.files_to_investigate, list)
    assert isinstance(plan.potential_risks, list)


@pytest.mark.skipif(
    not os.getenv("ENABLE_OLLAMA_INTEGRATION_TESTS"),
    reason="Ollama integration test disabled. Set ENABLE_OLLAMA_INTEGRATION_TESTS=1 to run.",
)
def test_coder_agent_live_ollama_integration():
    """Live integration test: User/GitHub issue + Plan -> CoderAgent -> ModelGateway -> OllamaClient -> gpt-oss:20b -> CodeProposal."""
    client = OllamaClient(model_name="gpt-oss:20b")
    gateway = ModelGateway(provider=client)
    coder = CoderAgent(model=gateway)

    issue = {
        "title": "Add optional tag filtering to GET /items endpoint",
        "description": "Currently GET /items returns all items without filtering. Users need to filter items by tag (e.g. ?tag=security).",
    }

    plan = Plan(
        goal="Add optional tag filtering to GET /items endpoint",
        requirements=[
            "Accept optional tag query parameter",
            "Filter items containing tag",
            "Return empty list if no items match",
        ],
        steps=[
            "Update get_items route in src/api/routes.py",
            "Add tag filtering in src/services/item_service.py",
        ],
        files_to_investigate=["src/api/routes.py", "src/services/item_service.py"],
        potential_risks=["Empty string handling"],
    )

    repo_info = {
        "files": (
            "src/api/routes.py:\n"
            "from fastapi import APIRouter\n"
            "from src.services.item_service import get_items_from_db\n"
            "router = APIRouter()\n"
            "@router.get('/items')\n"
            "def get_items():\n"
            "    return get_items_from_db()\n\n"
            "src/services/item_service.py:\n"
            "ITEMS = [{'id': 1, 'name': 'Item A', 'tags': ['security']}]\n"
            "def get_items_from_db():\n"
            "    return ITEMS\n"
        )
    }

    proposal = coder.code(issue=issue, plan=plan, repo_info=repo_info)

    assert isinstance(proposal, CodeProposal)
    assert isinstance(proposal.files_to_modify, list) and len(proposal.files_to_modify) > 0
    assert isinstance(proposal.changes, list) and len(proposal.changes) > 0
    for change in proposal.changes:
        assert isinstance(change, CodeEdit)
        assert change.file_path != ""
        assert change.action in ("modify", "create", "delete")
        assert change.explanation != ""
        assert change.new_content is not None or change.diff is not None


@pytest.mark.skipif(
    not os.getenv("ENABLE_OLLAMA_INTEGRATION_TESTS"),
    reason="Ollama integration test disabled. Set ENABLE_OLLAMA_INTEGRATION_TESTS=1 to run.",
)
def test_critic_agent_live_ollama_integration():
    """Live integration test: Issue + Plan + CodeProposal + TestResults -> CriticAgent -> ModelGateway -> OllamaClient -> gpt-oss:20b -> CriticEvaluation."""
    client = OllamaClient(model_name="gpt-oss:20b")
    gateway = ModelGateway(provider=client)
    critic = CriticAgent(model=gateway)

    issue = {
        "title": "Add optional tag filtering to GET /items endpoint",
        "description": "Currently GET /items returns all items without filtering. Users need to filter items by tag (e.g. ?tag=security). If tag query parameter is provided, return only items that contain the tag. If no items match, return an empty list with HTTP 200.",
    }

    plan = Plan(
        goal="Add optional tag filtering to GET /items endpoint",
        requirements=[
            "Accept optional tag query parameter",
            "Filter items containing tag",
            "Return empty list if no items match",
        ],
        steps=[
            "Update get_items route in src/api/routes.py",
            "Add tag filtering in src/services/item_service.py",
        ],
        files_to_investigate=["src/api/routes.py", "src/services/item_service.py"],
        potential_risks=["Empty string handling"],
    )

    proposal = CodeProposal(
        thought_process="Add tag query parameter in routes and filter list in item_service.",
        explanation="Implemented tag filtering in routes and service layer.",
        files_to_modify=["src/api/routes.py", "src/services/item_service.py"],
        changes=[
            CodeEdit(
                file_path="src/api/routes.py",
                action="modify",
                explanation="Add optional tag query parameter",
                new_content=(
                    "from typing import List, Optional\n"
                    "from fastapi import APIRouter, Query\n"
                    "from src.services.item_service import get_items_from_db\n\n"
                    "router = APIRouter()\n\n"
                    "@router.get('/items')\n"
                    "def get_items(tag: Optional[str] = Query(None)):\n"
                    "    return get_items_from_db(tag=tag)\n"
                ),
            ),
            CodeEdit(
                file_path="src/services/item_service.py",
                action="modify",
                explanation="Add tag filtering parameter to get_items_from_db",
                new_content=(
                    "from typing import List, Optional, Dict, Any\n\n"
                    "ITEMS = [\n"
                    "    {'id': 1, 'name': 'Item A', 'tags': ['security', 'backend']},\n"
                    "    {'id': 2, 'name': 'Item B', 'tags': ['frontend']},\n"
                    "]\n\n"
                    "def get_items_from_db(tag: Optional[str] = None) -> List[Dict[str, Any]]:\n"
                    "    if tag is None:\n"
                    "        return ITEMS\n"
                    "    return [item for item in ITEMS if tag in item.get('tags', [])]\n"
                ),
            ),
        ],
    )

    test_results = {
        "status": "passed",
        "output": "tests/test_routes.py::test_get_items_filtered PASSED\ntests/test_routes.py::test_get_items_unfiltered PASSED\n2 passed in 0.04s",
    }

    evaluation = critic.evaluate(
        issue=issue,
        proposal=proposal,
        plan=plan,
        test_results=test_results,
    )

    assert isinstance(evaluation, CriticEvaluation)
    assert isinstance(evaluation.is_acceptable, bool)
    assert isinstance(evaluation.score, float)
    assert 0.0 <= evaluation.score <= 1.0
    assert isinstance(evaluation.feedback, str) and len(evaluation.feedback) > 0
    assert isinstance(evaluation.unresolved_issues, list)
    assert isinstance(evaluation.suggestions, list)



