#!/usr/bin/env python3
"""Demonstration of real model integration flow for Phase 5:

Pipeline:
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

    # 1. Incoming GitHub Issue (same scenario as planner/coder demos)
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
    print(f"    Title:       {issue['title']}")
    print(f"    Description: {issue['description']}")

    # 2. Setup ModelGateway with OllamaClient (gpt-oss:20b)
    print("\n[2] Setting up ModelGateway with OllamaClient...")
    client = OllamaClient(
        model_name="gpt-oss:20b",
        base_url="http://localhost:11434/v1",
    )
    gateway = ModelGateway(provider=client)
    print(f"    OllamaClient endpoint: {client.base_url}")
    print(f"    Model name:            {client.model_name}")

    # 3. PlannerAgent produces Plan
    print("\n[3] Step 1: Running PlannerAgent (gpt-oss:20b)...")
    planner = PlannerAgent(model=gateway, temperature=0.1)
    plan: Plan = planner.plan(issue=issue, repo_info=repo_info)

    print("\n" + "-" * 40 + " PLAN " + "-" * 40)
    print(f"Goal: {plan.goal}")
    print(f"\nRequirements ({len(plan.requirements)}):")
    for idx, req in enumerate(plan.requirements, 1):
        print(f"  {idx}. {req}")
    print(f"\nSteps ({len(plan.steps)}):")
    for idx, step in enumerate(plan.steps, 1):
        print(f"  {idx}. {step}")
    print(f"\nFiles to Investigate ({len(plan.files_to_investigate)}):")
    for idx, f in enumerate(plan.files_to_investigate, 1):
        print(f"  {idx}. {f}")
    print(f"\nPotential Risks ({len(plan.potential_risks)}):")
    for idx, risk in enumerate(plan.potential_risks, 1):
        print(f"  {idx}. {risk}")

    # 4. CoderAgent produces CodeProposal
    print("\n[4] Step 2: Running CoderAgent (gpt-oss:20b)...")
    coder = CoderAgent(model=gateway, temperature=0.2)
    proposal: CodeProposal = coder.code(
        issue=issue,
        plan=plan,
        repo_info=repo_info,
    )

    print("\n" + "-" * 37 + " CODE PROPOSAL " + "-" * 38)
    print(f"Explanation: {proposal.explanation}")
    print(f"Files to Modify: {proposal.files_to_modify}")
    print(f"\nChanges ({len(proposal.changes)}):")
    for idx, ch in enumerate(proposal.changes, 1):
        print(f"  Change #{idx}: {ch.file_path} ({ch.action}) - {ch.explanation}")
        if ch.new_content:
            preview = ch.new_content[:150].strip() + ("..." if len(ch.new_content) > 150 else "")
            print(f"    Preview:\n      {preview.replace(chr(10), chr(10) + '      ')}")

    # 5. Test/Execution Context Provided to CriticAgent
    print("\n[5] Test / Execution Context Provided to CriticAgent:")
    print("    NOTE: The following is simulated test execution context provided as evaluation evidence:")
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
    print(f"    Status: {test_results['status']}")
    print("    Output Summary: 3 tests passed in 0.04s")

    # 6. CriticAgent evaluates CodeProposal + Plan + Issue + Context
    print("\n[6] Step 3: Running CriticAgent (gpt-oss:20b)...")
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
    print(f"Object Type:   {type(evaluation).__module__}.{type(evaluation).__name__}")
    print(f"Is Acceptable: {evaluation.is_acceptable}")
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

    # Assertions / Validations
    assert isinstance(evaluation, CriticEvaluation), f"Expected CriticEvaluation, got {type(evaluation)}"
    assert not evaluation.feedback.startswith("CriticAgent evaluation failed:"), f"Critic failed: {evaluation.feedback}"
    assert isinstance(evaluation.is_acceptable, bool)
    assert isinstance(evaluation.score, (int, float))
    assert 0.0 <= evaluation.score <= 1.0
    assert len(evaluation.feedback.strip()) > 0
    assert isinstance(evaluation.unresolved_issues, list)
    assert isinstance(evaluation.suggestions, list)

    print("\n" + "=" * 80)
    print("[STATUS]: Full Planner -> Coder -> Critic pipeline verified successfully with gpt-oss:20b!")
    print("=" * 80)


if __name__ == "__main__":
    main()
