"""Context Manager: Central coordinator for role-specific context preparation, memory, and compression."""

import logging
from typing import Any, Callable, Dict, List, Optional

from harness.context.compressor import ContextCompressor
from harness.context.memory import AgentMemory, MemoryFact
from harness.context.selector import AgentContext, ContextSelector

logger = logging.getLogger(__name__)


class ContextManager:
    """Manages the lifecycle of context, multi-tier memory, and context compression across all agents."""

    def __init__(
        self,
        repo_path: str = ".",
        memory: Optional[AgentMemory] = None,
        compressor: Optional[ContextCompressor] = None,
        selector: Optional[ContextSelector] = None,
        default_token_budget: int = 4000,
        role_budgets: Optional[Dict[str, int]] = None,
        file_loader: Optional[Callable[[str], str]] = None,
    ) -> None:
        self.repo_path = repo_path
        self.memory = memory or AgentMemory(repo_path=repo_path)
        self.compressor = compressor or ContextCompressor()
        self.selector = selector or ContextSelector(compressor=self.compressor)
        self.default_token_budget = default_token_budget
        self.role_budgets = role_budgets or {
            "planner": 3000,
            "researcher": 4500,
            "coder": 6500,
            "recovery": 5000,
            "verifier": 3500,
        }
        self.file_loader = file_loader

    def get_context_for_agent(
        self,
        role: str,
        state: Any,
        token_budget: Optional[int] = None,
    ) -> AgentContext:
        """Construct a tailored, compressed, and budget-enforced context for a specific agent role."""
        budget = token_budget or self.role_budgets.get(role.lower(), self.default_token_budget)

        # 1. Select the structured role-specific context
        context = self.selector.select_context(
            role=role,
            state=state,
            memory=self.memory,
            token_budget=budget,
            file_loader=self.file_loader,
        )

        # 2. Check if context exceeds token budget; if so, compress further
        prompt_text = context.to_prompt()
        est_tokens = self.compressor.estimate_tokens(prompt_text)

        if est_tokens > budget:
            logger.warning(
                f"Context for role '{role}' ({est_tokens} tokens) exceeds budget ({budget} tokens). Compressing..."
            )
            # Truncate file contents or history if needed
            if context.repo.file_contents:
                for fpath in list(context.repo.file_contents.keys()):
                    context.repo.file_contents[fpath] = self.compressor.truncate_to_token_budget(
                        context.repo.file_contents[fpath],
                        max_tokens=budget // 3,
                    )
            context.estimated_tokens = self.compressor.estimate_tokens(context.to_prompt())

        return context

    def record_discovery(
        self,
        fact: str,
        category: str = "general",
        source_agent: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> MemoryFact:
        """Explicitly record a key finding into memory."""
        return self.memory.record_fact(
            content=fact,
            category=category,
            source_agent=source_agent,
            tags=tags,
        )

    def record_decision(self, decision: str) -> None:
        """Record an architectural or algorithmic decision."""
        self.memory.record_decision(decision)

    def record_discarded_path(self, reason: str) -> None:
        """Record a failed approach or hypothesis to prevent repeating mistakes."""
        self.memory.record_discarded_path(reason)

    def update_from_state(self, state: Any) -> None:
        """Ingest state updates to extract facts, update active files, and refresh working memory."""
        # Update working active files
        if hasattr(state, "relevant_files") and state.relevant_files:
            self.memory.update_short_term(active_files=state.relevant_files)

        # Update working plan step
        if hasattr(state, "plan") and state.plan:
            current = next((p.description for p in state.plan if not p.completed), None)
            if current:
                self.memory.update_short_term(plan_step=current)

        # Extract facts from recent agent outputs
        if hasattr(state, "agent_outputs") and state.agent_outputs:
            for out in state.agent_outputs[-2:]:
                msg = getattr(out, "message", "")
                agent_name = getattr(out, "agent_name", "agent")
                facts = self.compressor.extract_facts_from_text(msg, source=agent_name)
                for f in facts:
                    self.memory.record_fact(
                        content=f.content,
                        category=f.category,
                        source_agent=f.source_agent,
                        tags=f.tags,
                    )

        # Extract facts from recent errors
        if hasattr(state, "errors") and state.errors:
            for err in state.errors[-2:]:
                self.memory.update_short_term(error=err)
                facts = self.compressor.extract_facts_from_text(err, source="system_error")
                for f in facts:
                    self.memory.record_fact(
                        content=f.content,
                        category=f.category,
                        source_agent=f.source_agent,
                        tags=f.tags,
                    )

    def get_system_prompt_for_agent(self, role: str) -> str:
        """Provide a standard, high-guidance system prompt tailored to the agent role."""
        role_normalized = role.lower().strip()

        base_guidelines = (
            "You are an expert AI software engineering agent working in a controlled harness. "
            "Be precise, adhere strictly to the given context, and never hallucinate file paths or assumptions."
        )

        if "plan" in role_normalized:
            return (
                f"{base_guidelines}\n\n"
                "ROLE: PLANNER AGENT\n"
                "YOUR RESPONSIBILITY: Analyze the issue and repository summary. Deconstruct the task into "
                "minimal, verifiable steps. Clearly identify what parts of the codebase require investigation."
            )
        elif "research" in role_normalized or "repo" in role_normalized:
            return (
                f"{base_guidelines}\n\n"
                "ROLE: REPOSITORY RESEARCH AGENT\n"
                "YOUR RESPONSIBILITY: Locate relevant source files, classes, methods, and existing test suites. "
                "Output specific, confirmed file paths and symbol references."
            )
        elif "code" in role_normalized or "coder" in role_normalized:
            return (
                f"{base_guidelines}\n\n"
                "ROLE: CODING AGENT\n"
                "YOUR RESPONSIBILITY: Implement minimal, high-quality, surgical code changes that directly solve "
                "the issue without introducing regressions. Follow existing codebase conventions."
            )
        elif "recover" in role_normalized:
            return (
                f"{base_guidelines}\n\n"
                "ROLE: RECOVERY AGENT\n"
                "YOUR RESPONSIBILITY: Analyze test failures, stack traces, and previous attempts. Diagnose the root "
                "cause, avoid repeating failed strategies, and produce a corrected solution."
            )
        elif "verif" in role_normalized or "test" in role_normalized:
            return (
                f"{base_guidelines}\n\n"
                "ROLE: VERIFICATION AGENT\n"
                "YOUR RESPONSIBILITY: Rigorously validate the patch against existing and new test cases. "
                "Verify edge cases, backward compatibility, and execution correctness."
            )

        return base_guidelines
