#!/usr/bin/env python3
"""Demonstration of real model integration flow for Phase 5:

Flow:
GitHub Issue
    ↓
PlannerAgent
    ↓
Plan
    ↓
CoderAgent
    ↓
CodeProposal
    ↓
CriticAgent
    ↓
ModelGateway
    ↓
OllamaClient
    ↓
gpt-oss:20b
    ↓
CriticEvaluation

Usage:
    python scripts/demo_critic_ollama.py
"""

import json
import sys
from typing import Any, Dict

from harness.agents.coder import CoderAgent
from harness.agents.critic import CriticAgent
from harness.agents.planner import PlannerAgent
from harness.model.gateway import ModelGateway
from harness.model.ollama import OllamaClient
from harness.model.schemas import CodeProposal, CriticEvaluation, Plan


def main() -> None:
    print("=" * 80)
    print("DEMO: Real Model Integration Flow (Phase 5: Planner -> Coder -> Critic)")
    print("GitHub Issue -> PlannerAgent -> Plan -> CoderAgent -> CodeProposal -> CriticAgent -> CriticEvaluation")
    print("=" * 80)

    # 1. Incoming GitHub Issue
    issue: Dict[str, Any] = {
        "title": "Add optional tag filtering to GET /items endpoint",
        "description": (
            "Currently GET /items returns all items without filtering. "
            "Users need to filter items by tag (e.g. ?tag=security). "
            "If 'tag' query parameter is provided, return only items that contain the tag. "
            "If no items match, return an empty list with HTTP 200. "
            "Add validation and maintain existing behavior when tag is omitted."
        ),
    }

    repo_info = {
        "tree": "src/\n  api/\n    routes.py\n  services/\n    item_service.py\ntests/\n  test_routes.py",
        "files": (
            "--- src/api/routes.py ---\n"
            "from typing import List, Optional\n"
            "from fastapi import APIRouter, Query\n"
            "from src.services.item_service import get_items_from_db\n\n"
            "router = APIRouter()\n\n"
            "@router.get('/items')\n"
            "def get_items():\n"
            "    return get_items_from_db()\n\n"
            "--- src/services/item_service.py ---\n"
            "from typing import List, Optional, Dict, Any\n\n"
            "ITEMS = [\n"
            "    {'id': 1, 'name': 'Firewall Appliance', 'tags': ['security', 'hardware']},\n"
            "    {'id': 2, 'name': 'Auth Proxy', 'tags': ['security', 'backend']},\n"
            "    {'id': 3, 'name': 'Web Frontend', 'tags': ['frontend']},\n"
            "]\n\n"
            "def get_items_from_db():\n"
            "    return ITEMS\n"
        ),
        "context": "Python FastAPI microservice with in-memory service layer.",
    }

    print("\n[1] Incoming GitHub Issue:")
    print(f"    Title: {issue['title']}")
    print(f"    Description: {issue['description']}")

    # 2. Setup ModelGateway with OllamaClient (gpt-oss:20b)
    print("\n[2] Instantiating OllamaClient and ModelGateway...")
    client = OllamaClient(
        model_name="gpt-oss:20b",
        base_url="http://localhost:11434/v1",
    )
    gateway = ModelGateway(provider=client)
    print(f"    OllamaClient configured for model: {client.model_name}")

    # 3. PlannerAgent produces Plan
    print("\n[3] Step 1: Running PlannerAgent...")
    planner = PlannerAgent(model=gateway, temperature=0.1)
    plan: Plan = planner.plan(issue=issue, repo_info=repo_info)
    print(f"    Plan Goal: {plan.goal}")
    print(f"    Requirements: {len(plan.requirements)} items")
    print(f"    Steps: {len(plan.steps)} items")

    # 4. CoderAgent produces CodeProposal
    print("\n[4] Step 2: Running CoderAgent...")
    coder = CoderAgent(model=gateway, temperature=0.2)
    proposal: CodeProposal = coder.code(
        issue=issue,
        plan=plan,
        repo_info=repo_info,
    )
    print(f"    CodeProposal Explanation: {proposal.explanation}")
    print(f"    Files to Modify: {proposal.files_to_modify}")
    print(f"    Changes Count: {len(proposal.changes)}")

    # 5. Simulated Test Results
    test_results = {
        "status": "passed",
        "output": (
            "============================= test session starts ==============================\n"
            "tests/test_routes.py::test_get_items_no_tag PASSED                       [ 33%]\n"
            "tests/test_routes.py::test_get_items_matching_tag PASSED                 [ 66%]\n"
            "tests/test_routes.py::test_get_items_non_matching_tag PASSED             [100%]\n"
            "============================== 3 passed in 0.04s ==============================="
        ),
    }
    print(f"\n[5] Test Execution Results Provided to Critic:")
    print(f"    Status: {test_results['status']}")
    print(f"    Summary: 3 passed in 0.04s")

    # 6. CriticAgent evaluates CodeProposal + Plan + Issue + Test Results
    print("\n[6] Step 3: Running CriticAgent...")
    critic = CriticAgent(model=gateway, temperature=0.1)
    evaluation: CriticEvaluation = critic.evaluate(
        issue=issue,
        proposal=proposal,
        plan=plan,
        repo_info=repo_info,
        test_results=test_results,
    )

    # 7. Display the structured CriticEvaluation
    print("\n" + "=" * 80)
    print("RESULT: Structured CriticEvaluation Received from CriticAgent")
    print("=" * 80)
    print(f"Type: {type(evaluation).__module__}.{type(evaluation).__name__}")
    print(f"\nIs Acceptable: {evaluation.is_acceptable}")
    print(f"Score:         {evaluation.score} / 1.0")
    print(f"\nFeedback:\n{evaluation.feedback}\n")

    print(f"Unresolved Issues ({len(evaluation.unresolved_issues)}):")
    if evaluation.unresolved_issues:
        for idx, issue_item in enumerate(evaluation.unresolved_issues, 1):
            print(f"  {idx}. {issue_item}")
    else:
        print("  (None)")

    print(f"\nSuggestions ({len(evaluation.suggestions)}):")
    if evaluation.suggestions:
        for idx, sugg in enumerate(evaluation.suggestions, 1):
            print(f"  {idx}. {sugg}")
    else:
        print("  (None)")

    # Assertions
    assert isinstance(evaluation, CriticEvaluation), f"Expected CriticEvaluation, got {type(evaluation)}"
    assert isinstance(evaluation.is_acceptable, bool)
    assert isinstance(evaluation.score, float)
    assert 0.0 <= evaluation.score <= 1.0
    assert len(evaluation.feedback) > 0
    assert isinstance(evaluation.unresolved_issues, list)
    assert isinstance(evaluation.suggestions, list)

    print("\n[Status]: Full Planner -> Coder -> Critic pipeline verified successfully!")


if __name__ == "__main__":
    main()
