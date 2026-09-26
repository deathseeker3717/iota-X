"""Offline unit tests for CriticAgent using mocked ModelGateway responses.

Verifies:
1. Acceptable proposal evaluation
2. Rejected proposal evaluation
3. gpt-oss reasoning output (<think> tags stripping)
4. Markdown code block JSON parsing
5. Full context passing (issue, plan, proposal, repo_info, test_results)
6. Malformed model response fallback
7. Exception handling
8. String boolean and score boundary handling
"""

import json
import os
from typing import Any, Dict, List, Optional
import pytest

from harness.agents.critic import CriticAgent
from harness.agents.prompts import CRITIC_SYSTEM_PROMPT
from harness.model import (
    CodeEdit,
    CodeProposal,
    CriticEvaluation,
    Message,
    ModelGateway,
    ModelInterface,
    ModelRequest,
    ModelResponse,
    Plan,
)


class MockModelProvider(ModelInterface):
    """Mock model provider returning predefined responses without network calls."""

    def __init__(self, response_content: str) -> None:
        self.response_content = response_content
        self.last_request: Optional[ModelRequest] = None

    def generate(self, request: ModelRequest) -> ModelResponse:
        self.last_request = request
        return ModelResponse(content=self.response_content)


class FailingMockProvider(ModelInterface):
    """Mock provider that raises an exception during generation."""

    def generate(self, request: ModelRequest) -> ModelResponse:
        raise RuntimeError("Simulated gateway network failure")


@pytest.fixture
def sample_issue() -> Dict[str, Any]:
    return {
        "title": "Add optional tag filtering to GET /items",
        "description": "Allow filtering items by ?tag=security. If tag is provided, return matching items.",
    }


@pytest.fixture
def sample_plan() -> Plan:
    return Plan(
        goal="Add optional tag filtering to GET /items",
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
        potential_risks=["Empty string query param handling"],
    )


@pytest.fixture
def sample_proposal() -> CodeProposal:
    return CodeProposal(
        thought_process="Add tag query parameter in routes and filter in service layer.",
        explanation="Implemented tag filtering in routes and service layer.",
        files_to_modify=["src/api/routes.py"],
        changes=[
            CodeEdit(
                file_path="src/api/routes.py",
                action="modify",
                explanation="Add optional tag query parameter",
                new_content="def get_items(tag: Optional[str] = None): ...",
            )
        ],
    )


def test_critic_acceptable_proposal(sample_issue, sample_plan, sample_proposal):
    """1. Test ACCEPTABLE proposal parsing with exact mock payload."""
    mock_payload = {
        "is_acceptable": True,
        "score": 0.95,
        "feedback": "The implementation satisfies the requested behavior.",
        "unresolved_issues": [],
        "suggestions": [
            "Add an additional edge-case test."
        ],
    }

    provider = MockModelProvider(response_content=json.dumps(mock_payload))
    gateway = ModelGateway(provider=provider)
    critic = CriticAgent(model=gateway)

    evaluation = critic.evaluate(
        issue=sample_issue,
        proposal=sample_proposal,
        plan=sample_plan,
    )

    assert isinstance(evaluation, CriticEvaluation)
    assert evaluation.is_acceptable is True
    assert evaluation.score == 0.95
    assert evaluation.feedback == "The implementation satisfies the requested behavior."
    assert evaluation.unresolved_issues == []
    assert evaluation.suggestions == ["Add an additional edge-case test."]


def test_critic_rejected_proposal(sample_issue, sample_plan, sample_proposal):
    """2. Test REJECTED proposal parsing with exact mock payload."""
    mock_payload = {
        "is_acceptable": False,
        "score": 0.35,
        "feedback": "The implementation does not fully satisfy the request.",
        "unresolved_issues": [
            "The requested filtering behavior is missing."
        ],
        "suggestions": [
            "Implement the missing filter."
        ],
    }

    provider = MockModelProvider(response_content=json.dumps(mock_payload))
    gateway = ModelGateway(provider=provider)
    critic = CriticAgent(model=gateway)

    evaluation = critic.evaluate(
        issue=sample_issue,
        proposal=sample_proposal,
        plan=sample_plan,
    )

    assert isinstance(evaluation, CriticEvaluation)
    assert evaluation.is_acceptable is False
    assert evaluation.score == 0.35
    assert evaluation.feedback == "The implementation does not fully satisfy the request."
    assert evaluation.unresolved_issues == ["The requested filtering behavior is missing."]
    assert evaluation.suggestions == ["Implement the missing filter."]


def test_critic_gpt_oss_reasoning_output(sample_issue, sample_plan, sample_proposal):
    """3. Test gpt-oss reasoning output with <think> tags."""
    mock_content = """<think>
I should inspect the requirements.
</think>
{
  "is_acceptable": true,
  "score": 0.9,
  "feedback": "Looks correct.",
  "unresolved_issues": [],
  "suggestions": []
}"""

    provider = MockModelProvider(response_content=mock_content)
    gateway = ModelGateway(provider=provider)
    critic = CriticAgent(model=gateway)

    evaluation = critic.evaluate(
        issue=sample_issue,
        proposal=sample_proposal,
        plan=sample_plan,
    )

    assert isinstance(evaluation, CriticEvaluation)
    assert evaluation.is_acceptable is True
    assert evaluation.score == 0.9
    assert evaluation.feedback == "Looks correct."
    assert evaluation.unresolved_issues == []
    assert evaluation.suggestions == []


def test_critic_markdown_json(sample_issue, sample_plan, sample_proposal):
    """4. Test markdown-wrapped JSON extraction."""
    mock_content = """```json
{
  "is_acceptable": true,
  "score": 0.9,
  "feedback": "Looks correct.",
  "unresolved_issues": [],
  "suggestions": []
}
```"""

    provider = MockModelProvider(response_content=mock_content)
    gateway = ModelGateway(provider=provider)
    critic = CriticAgent(model=gateway)

    evaluation = critic.evaluate(
        issue=sample_issue,
        proposal=sample_proposal,
        plan=sample_plan,
    )

    assert isinstance(evaluation, CriticEvaluation)
    assert evaluation.is_acceptable is True
    assert evaluation.score == 0.9
    assert evaluation.feedback == "Looks correct."
    assert evaluation.unresolved_issues == []
    assert evaluation.suggestions == []


def test_critic_full_context_evaluation(sample_issue, sample_plan, sample_proposal):
    """Test that CriticAgent formats and passes issue, plan, proposal, repo_info, and test_results."""
    mock_payload = {
        "is_acceptable": True,
        "score": 0.92,
        "feedback": "Comprehensive verification with passing test results.",
        "unresolved_issues": [],
        "suggestions": [],
    }

    provider = MockModelProvider(response_content=json.dumps(mock_payload))
    gateway = ModelGateway(provider=provider)
    critic = CriticAgent(model=gateway)

    repo_info = {
        "tree": "src/\n  api/\n    routes.py",
        "context": "FastAPI application with pytest test suite.",
    }
    test_results = {
        "status": "passed",
        "output": "2 passed in 0.04s",
    }

    evaluation = critic.evaluate(
        issue=sample_issue,
        proposal=sample_proposal,
        plan=sample_plan,
        repo_info=repo_info,
        test_results=test_results,
    )

    assert isinstance(evaluation, CriticEvaluation)
    assert evaluation.is_acceptable is True
    assert evaluation.score == 0.92

    # Check that provider received all context elements
    assert provider.last_request is not None
    user_prompt = provider.last_request.messages[0].content
    assert "Add optional tag filtering" in user_prompt
    assert "Accept optional tag query parameter" in user_prompt
    assert "Implemented tag filtering in routes" in user_prompt
    assert "FastAPI application with pytest" in user_prompt
    assert "TEST / EXECUTION RESULTS" in user_prompt
    assert "2 passed in 0.04s" in user_prompt
    assert provider.last_request.system_prompt == CRITIC_SYSTEM_PROMPT


def test_critic_malformed_unparseable_output_fallback(sample_issue, sample_proposal):
    """Test safe fallback when model output contains no parseable JSON."""
    plain_text_content = "I reviewed the code and think it has some problems, but I cannot write JSON."

    provider = MockModelProvider(response_content=plain_text_content)
    gateway = ModelGateway(provider=provider)
    critic = CriticAgent(model=gateway)

    evaluation = critic.evaluate(
        issue=sample_issue,
        proposal=sample_proposal,
    )

    assert isinstance(evaluation, CriticEvaluation)
    assert evaluation.is_acceptable is False
    assert evaluation.score == 0.0
    assert plain_text_content in evaluation.feedback


def test_critic_exception_handling(sample_issue, sample_proposal):
    """Test safe handling when ModelGateway raises an exception."""
    provider = FailingMockProvider()
    gateway = ModelGateway(provider=provider)
    critic = CriticAgent(model=gateway)

    evaluation = critic.evaluate(
        issue=sample_issue,
        proposal=sample_proposal,
    )

    assert isinstance(evaluation, CriticEvaluation)
    assert evaluation.is_acceptable is False
    assert evaluation.score == 0.0
    assert "Simulated gateway network failure" in evaluation.feedback
    assert len(evaluation.unresolved_issues) > 0


def test_critic_string_boolean_and_score_clamping(sample_issue, sample_proposal):
    """Test string boolean parsing and score bounds clamping."""
    # Test "false" string and score > 1.0
    payload_false = {
        "is_acceptable": "false",
        "score": 1.5,
        "feedback": "String boolean rejection",
        "unresolved_issues": ["Issue 1"],
        "suggestions": ["Suggestion 1"],
    }
    provider = MockModelProvider(response_content=json.dumps(payload_false))
    gateway = ModelGateway(provider=provider)
    critic = CriticAgent(model=gateway)

    eval_false = critic.evaluate(issue=sample_issue, proposal=sample_proposal)
    assert eval_false.is_acceptable is False
    assert eval_false.score == 1.0  # Clamped to 1.0

    # Test "true" string and score < 0.0
    payload_true = {
        "is_acceptable": "true",
        "score": -0.5,
        "feedback": "String boolean acceptance",
        "unresolved_issues": [],
        "suggestions": [],
    }
    provider.response_content = json.dumps(payload_true)
    eval_true = critic.evaluate(issue=sample_issue, proposal=sample_proposal)
    assert eval_true.is_acceptable is True
    assert eval_true.score == 0.0  # Clamped to 0.0


@pytest.mark.skipif(
    not os.getenv("ENABLE_OLLAMA_INTEGRATION_TESTS"),
    reason="Ollama integration test disabled. Set ENABLE_OLLAMA_INTEGRATION_TESTS=1 to run.",
)
def test_critic_agent_live_ollama_integration(sample_issue, sample_plan, sample_proposal):
    """Live integration test: Issue + Plan + CodeProposal + TestResults -> CriticAgent -> ModelGateway -> OllamaClient -> gpt-oss:20b -> CriticEvaluation."""
    from harness.model.ollama import OllamaClient

    client = OllamaClient(model_name="gpt-oss:20b")
    gateway = ModelGateway(provider=client)
    critic = CriticAgent(model=gateway)

    test_results = {
        "status": "passed",
        "output": "tests/test_routes.py::test_get_items_filtered PASSED\n1 passed in 0.02s",
    }

    evaluation = critic.evaluate(
        issue=sample_issue,
        proposal=sample_proposal,
        plan=sample_plan,
        test_results=test_results,
    )

    # 1. Model responds (no exception fallback)
    assert not evaluation.feedback.startswith("CriticAgent evaluation failed:"), (
        f"Live model call failed: {evaluation.feedback}"
    )

    # 2. CriticAgent returns CriticEvaluation
    assert isinstance(evaluation, CriticEvaluation)

    # 3. is_acceptable is boolean
    assert isinstance(evaluation.is_acceptable, bool)

    # 4. score is numeric and bounded
    assert isinstance(evaluation.score, (int, float))
    assert 0.0 <= evaluation.score <= 1.0

    # 5. feedback is non-empty
    assert isinstance(evaluation.feedback, str) and len(evaluation.feedback.strip()) > 0

    # 6. unresolved_issues is a list
    assert isinstance(evaluation.unresolved_issues, list)

    # 7. suggestions is a list
    assert isinstance(evaluation.suggestions, list)

