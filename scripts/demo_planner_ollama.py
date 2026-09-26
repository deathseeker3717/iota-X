#!/usr/bin/env python3
"""Demonstration of real model integration flow for Phase 3:

Flow:
GitHub issue/request
    ↓
PlannerAgent
    ↓
ModelGateway
    ↓
OllamaClient
    ↓
gpt-oss:20b
    ↓
Plan object

Usage:
    python scripts/demo_planner_ollama.py
"""

import json
import sys
from typing import Any, Dict

from harness.agents.planner import PlannerAgent
from harness.model.gateway import ModelGateway
from harness.model.ollama import OllamaClient
from harness.model.schemas import Plan


def main() -> None:
    print("=" * 70)
    print("DEMO: Real Model Integration Flow (Phase 3)")
    print("GitHub issue -> PlannerAgent -> ModelGateway -> OllamaClient -> gpt-oss:20b -> Plan")
    print("=" * 70)

    # 1. Incoming GitHub Issue
    issue: Dict[str, Any] = {
        "title": "Add optional tag filtering to GET /items endpoint",
        "description": (
            "Currently GET /items returns all items without filtering. "
            "Users need to filter items by tag (e.g. ?tag=security). "
            "If 'tag' query parameter is provided, return only items that contain the tag. "
            "If no items match, return an empty list with HTTP 200. "
            "Add validation and unit tests."
        ),
    }
    repo_info = {
        "tree": "src/\n  api/\n    routes.py\n    models.py\n  services/\n    item_service.py\ntests/\n  test_routes.py",
        "files": ["src/api/routes.py", "src/services/item_service.py"],
        "context": "Python FastAPI application with SQLModel/SQLAlchemy backend.",
    }

    print("\n[1] Incoming GitHub Issue / Request:")
    print(f"    Title: {issue['title']}")
    print(f"    Description: {issue['description']}")
    print(f"    Target Repo Context: {repo_info['context']}")

    # 2. Instantiate OllamaClient (implements ModelInterface)
    print("\n[2] Instantiating OllamaClient...")
    client = OllamaClient(
        model_name="gpt-oss:20b",
        base_url="http://localhost:11434/v1",
    )
    print(f"    OllamaClient configured for model: {client.model_name} at {client.base_url}")

    # 3. Instantiate ModelGateway (separates agent from model provider)
    print("\n[3] Wrapping in ModelGateway...")
    gateway = ModelGateway(provider=client)
    print("    ModelGateway initialized with OllamaClient provider.")

    # 4. Instantiate PlannerAgent with ModelGateway
    print("\n[4] Initializing PlannerAgent with ModelGateway...")
    planner = PlannerAgent(model=gateway, temperature=0.1)

    # 5. Execute PlannerAgent.plan()
    print("\n[5] Dispatching request: PlannerAgent -> ModelGateway -> OllamaClient -> gpt-oss:20b...")
    plan: Plan = planner.plan(issue=issue, repo_info=repo_info)

    # 6. Verify and display the resulting Plan object
    print("\n" + "=" * 70)
    print("RESULT: Structured Plan Object Received")
    print("=" * 70)
    print(f"Plan Type: {type(plan).__module__}.{type(plan).__name__}")
    print(f"\nGoal:\n  {plan.goal}\n")

    print(f"Requirements ({len(plan.requirements)}):")
    for idx, req in enumerate(plan.requirements, 1):
        print(f"  {idx}. {req}")

    print(f"\nSteps ({len(plan.steps)}):")
    for idx, step in enumerate(plan.steps, 1):
        print(f"  {idx}. {step}")

    print(f"\nFiles to Investigate ({len(plan.files_to_investigate)}):")
    for idx, file_path in enumerate(plan.files_to_investigate, 1):
        print(f"  {idx}. {file_path}")

    print(f"\nPotential Risks ({len(plan.potential_risks)}):")
    for idx, risk in enumerate(plan.potential_risks, 1):
        print(f"  {idx}. {risk}")

    # Validation
    assert isinstance(plan, Plan), f"Expected Plan object, got {type(plan)}"
    assert plan.goal, "Plan goal must not be empty"
    assert len(plan.steps) > 0, "Plan must contain steps"
    print("\n[Status]: Real flow verified successfully!")


if __name__ == "__main__":
    main()
