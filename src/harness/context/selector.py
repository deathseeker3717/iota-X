"""Hierarchical Context Selector: Tailors context views for specific agent roles."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from harness.context.compressor import ContextCompressor
from harness.context.memory import AgentMemory


@dataclass
class TaskContext:
    """The task dimension of context."""

    task_description: str
    goal: Optional[str] = None
    requirements: List[str] = field(default_factory=list)
    current_step: Optional[str] = None


@dataclass
class RepoContext:
    """The repository dimension of context."""

    repo_path: str = "."
    relevant_files: List[str] = field(default_factory=list)
    file_contents: Dict[str, str] = field(default_factory=dict)
    symbols: Dict[str, str] = field(default_factory=dict)
    architecture_summary: Optional[str] = None


@dataclass
class HistoryContext:
    """The execution history dimension of context."""

    recent_actions: List[Dict[str, Any]] = field(default_factory=list)
    active_errors: List[str] = field(default_factory=list)
    test_failures: List[Dict[str, Any]] = field(default_factory=list)
    recent_changes: List[str] = field(default_factory=list)
    iteration: int = 0


@dataclass
class AgentContext:
    """Structured context packaged specifically for an agent role's execution."""

    role: str
    task: TaskContext
    repo: RepoContext
    history: HistoryContext
    memory_summary: str = ""
    token_budget: int = 4000
    estimated_tokens: int = 0

    def to_prompt(self) -> str:
        """Render the complete context as a structured, Markdown-formatted prompt string."""
        sections: List[str] = []

        # 1. TASK SECTION
        sections.append("## 1. TASK OBJECTIVE")
        sections.append(f"Issue / Request: {self.task.task_description}")
        if self.task.goal:
            sections.append(f"Goal: {self.task.goal}")
        if self.task.current_step:
            sections.append(f"Current Step: {self.task.current_step}")
        if self.task.requirements:
            sections.append("Requirements:")
            for req in self.task.requirements:
                sections.append(f"- {req}")

        # 2. REPOSITORY & CODE CONTEXT
        if self.repo.architecture_summary or self.repo.relevant_files or self.repo.file_contents:
            sections.append("\n## 2. REPOSITORY CONTEXT")
            if self.repo.architecture_summary:
                sections.append(f"Architecture: {self.repo.architecture_summary}")
            if self.repo.relevant_files:
                sections.append(f"Relevant Files: {', '.join(self.repo.relevant_files)}")
            if self.repo.symbols:
                sections.append("Key Symbols:")
                for sym, desc in self.repo.symbols.items():
                    sections.append(f"- `{sym}`: {desc}")
            if self.repo.file_contents:
                sections.append("File Contents:")
                for fpath, content in self.repo.file_contents.items():
                    sections.append(f"--- File: {fpath} ---\n{content}\n--- End File ---")

        # 3. MEMORY & DISCOVERIES
        if self.memory_summary:
            sections.append("\n## 3. HARNESS MEMORY & DISCOVERIES")
            sections.append(self.memory_summary)

        # 4. EXECUTION HISTORY & ERRORS
        if self.history.recent_actions or self.history.active_errors or self.history.test_failures or self.history.recent_changes:
            sections.append("\n## 4. EXECUTION HISTORY & STATE")
            if self.history.iteration > 0:
                sections.append(f"Current Iteration: {self.history.iteration}")
            if self.history.recent_changes:
                sections.append("Applied Changes:")
                for chg in self.history.recent_changes:
                    sections.append(f"- {chg}")
            if self.history.recent_actions:
                sections.append("Recent Actions:")
                for act in self.history.recent_actions:
                    status = act.get("status", "DONE")
                    agent = act.get("agent", "agent")
                    summary = act.get("summary", "")
                    sections.append(f"- Step {act.get('step', '?')} [{agent}] ({status}): {summary}")
            if self.history.active_errors:
                sections.append("Active Errors:")
                for err in self.history.active_errors:
                    sections.append(f"```\n{err}\n```")
            if self.history.test_failures:
                sections.append("Test Failures:")
                for tf in self.history.test_failures:
                    sections.append(f"- {tf.get('message', 'Failed test')}")

        return "\n".join(sections)

    def to_messages(self, system_prompt: Optional[str] = None) -> List[Dict[str, str]]:
        """Convert context to chat messages suitable for ModelGateway."""
        messages: List[Dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": self.to_prompt()})
        return messages


class ContextSelector:
    """Selects and filters context based on the agent's specific role and operational goals."""

    def __init__(self, compressor: Optional[ContextCompressor] = None) -> None:
        self.compressor = compressor or ContextCompressor()

    def select_context(
        self,
        role: str,
        state: Any,
        memory: AgentMemory,
        token_budget: int = 4000,
        file_loader: Optional[Any] = None,
    ) -> AgentContext:
        """Route context selection to the specialized role selector."""
        role_normalized = role.lower().strip()

        if "plan" in role_normalized:
            return self.select_for_planner(state, memory, token_budget)
        elif "research" in role_normalized or "repo" in role_normalized:
            return self.select_for_researcher(state, memory, token_budget)
        elif "code" in role_normalized or "coder" in role_normalized:
            return self.select_for_coder(state, memory, token_budget, file_loader=file_loader)
        elif "recover" in role_normalized:
            return self.select_for_recovery(state, memory, token_budget, file_loader=file_loader)
        elif "verif" in role_normalized or "test" in role_normalized or "critic" in role_normalized:
            return self.select_for_verifier(state, memory, token_budget)
        else:
            return self._select_generic(role, state, memory, token_budget)

    def select_for_planner(
        self,
        state: Any,
        memory: AgentMemory,
        token_budget: int = 3000,
    ) -> AgentContext:
        """Planner needs: Issue/Task + High-level Repo Summary + Key Architecture Facts."""
        task_ctx = TaskContext(
            task_description=state.task,
            goal="Analyze the request, decompose it into actionable plan steps, and identify focus areas.",
        )

        repo_ctx = RepoContext(
            repo_path=getattr(state, "repo_path", "."),
            architecture_summary=memory.repository.architecture_overview or "Standard codebase structure",
            symbols=dict(list(memory.repository.key_symbols.items())[:5]),
        )

        history_ctx = HistoryContext(
            iteration=getattr(state, "iteration", 0),
            active_errors=self.compressor.deduplicate_errors(getattr(state, "errors", [])),
        )

        summary = memory.get_summary_for_prompt(max_facts=5)

        context = AgentContext(
            role="planner",
            task=task_ctx,
            repo=repo_ctx,
            history=history_ctx,
            memory_summary=summary,
            token_budget=token_budget,
        )
        context.estimated_tokens = self.compressor.estimate_tokens(context.to_prompt())
        return context

    def select_for_researcher(
        self,
        state: Any,
        memory: AgentMemory,
        token_budget: int = 4000,
    ) -> AgentContext:
        """Researcher needs: Issue + Search Objective + Known Structure + Previous Research."""
        task_ctx = TaskContext(
            task_description=state.task,
            goal="Identify exact files, functions, classes, and tests relevant to fixing this issue.",
        )

        repo_ctx = RepoContext(
            repo_path=getattr(state, "repo_path", "."),
            relevant_files=list(getattr(state, "relevant_files", [])),
            architecture_summary=memory.repository.architecture_overview,
        )

        history_ctx = HistoryContext(
            iteration=getattr(state, "iteration", 0),
            recent_actions=self.compressor.compress_agent_outputs(getattr(state, "agent_outputs", []), max_recent_full=2),
        )

        context = AgentContext(
            role="researcher",
            task=task_ctx,
            repo=repo_ctx,
            history=history_ctx,
            memory_summary=memory.get_summary_for_prompt(max_facts=6),
            token_budget=token_budget,
        )
        context.estimated_tokens = self.compressor.estimate_tokens(context.to_prompt())
        return context

    def select_for_coder(
        self,
        state: Any,
        memory: AgentMemory,
        token_budget: int = 6000,
        file_loader: Optional[Any] = None,
    ) -> AgentContext:
        """Coder needs: Issue + Plan + Selected File Contents + Relevant Symbols + Test Requirements."""
        plan_steps = getattr(state, "plan", [])
        current_step_desc = None
        if plan_steps:
            current_step_desc = "\n".join(
                [f"[{'X' if p.completed else ' '}] Step {p.step_id}: {p.description}" for p in plan_steps]
            )

        task_ctx = TaskContext(
            task_description=state.task,
            goal="Implement minimal, precise, and correct modifications to resolve the issue.",
            current_step=current_step_desc,
        )

        relevant_files = list(getattr(state, "relevant_files", []))
        file_contents: Dict[str, str] = {}

        if file_loader and relevant_files:
            for fpath in relevant_files[:3]:  # Top 3 files
                try:
                    content = file_loader(fpath)
                    compressed = self.compressor.compress_tool_output(content, max_lines=60, max_chars=2500)
                    file_contents[fpath] = compressed
                except Exception:
                    pass

        repo_ctx = RepoContext(
            repo_path=getattr(state, "repo_path", "."),
            relevant_files=relevant_files,
            file_contents=file_contents,
            symbols=dict(list(memory.repository.key_symbols.items())[:6]),
        )

        history_ctx = HistoryContext(
            iteration=getattr(state, "iteration", 0),
            recent_changes=list(getattr(state, "changes", [])),
            active_errors=self.compressor.deduplicate_errors(getattr(state, "errors", [])),
        )

        context = AgentContext(
            role="coder",
            task=task_ctx,
            repo=repo_ctx,
            history=history_ctx,
            memory_summary=memory.get_summary_for_prompt(max_facts=6),
            token_budget=token_budget,
        )
        context.estimated_tokens = self.compressor.estimate_tokens(context.to_prompt())
        return context

    def select_for_recovery(
        self,
        state: Any,
        memory: AgentMemory,
        token_budget: int = 5000,
        file_loader: Optional[Any] = None,
    ) -> AgentContext:
        """Recovery needs: Issue + Current changes + Test failures/errors + Discarded paths + Recent actions."""
        task_ctx = TaskContext(
            task_description=state.task,
            goal="Diagnose the failure cause, revert bad assumptions, and formulate a targeted recovery patch.",
            requirements=["Do not repeat discarded attempts.", "Focus strictly on fixing the root failure."],
        )

        # Gather test failures
        test_results = getattr(state, "test_results", [])
        failures = [t for t in test_results if not t.get("passed", False)]

        history_ctx = HistoryContext(
            iteration=getattr(state, "iteration", 0),
            recent_changes=list(getattr(state, "changes", [])),
            active_errors=self.compressor.deduplicate_errors(getattr(state, "errors", [])),
            test_failures=failures,
            recent_actions=self.compressor.compress_agent_outputs(getattr(state, "agent_outputs", []), max_recent_full=3),
        )

        repo_ctx = RepoContext(
            repo_path=getattr(state, "repo_path", "."),
            relevant_files=list(getattr(state, "relevant_files", [])),
        )

        context = AgentContext(
            role="recovery",
            task=task_ctx,
            repo=repo_ctx,
            history=history_ctx,
            memory_summary=memory.get_summary_for_prompt(max_facts=8),
            token_budget=token_budget,
        )
        context.estimated_tokens = self.compressor.estimate_tokens(context.to_prompt())
        return context

    def select_for_verifier(
        self,
        state: Any,
        memory: AgentMemory,
        token_budget: int = 4000,
    ) -> AgentContext:
        """Verifier needs: Issue + Changes applied + Test requirements + Verification expectations."""
        task_ctx = TaskContext(
            task_description=state.task,
            goal="Verify all modified functionality, ensure no regressions, and validate acceptance criteria.",
        )

        repo_ctx = RepoContext(
            repo_path=getattr(state, "repo_path", "."),
            relevant_files=list(getattr(state, "relevant_files", [])),
        )

        history_ctx = HistoryContext(
            iteration=getattr(state, "iteration", 0),
            recent_changes=list(getattr(state, "changes", [])),
            test_failures=[t for t in getattr(state, "test_results", []) if not t.get("passed", False)],
        )

        context = AgentContext(
            role="verifier",
            task=task_ctx,
            repo=repo_ctx,
            history=history_ctx,
            memory_summary=memory.get_summary_for_prompt(max_facts=4),
            token_budget=token_budget,
        )
        context.estimated_tokens = self.compressor.estimate_tokens(context.to_prompt())
        return context

    def _select_generic(
        self,
        role: str,
        state: Any,
        memory: AgentMemory,
        token_budget: int = 4000,
    ) -> AgentContext:
        task_ctx = TaskContext(task_description=getattr(state, "task", ""))
        repo_ctx = RepoContext(
            repo_path=getattr(state, "repo_path", "."),
            relevant_files=list(getattr(state, "relevant_files", [])),
        )
        history_ctx = HistoryContext(
            iteration=getattr(state, "iteration", 0),
            recent_changes=list(getattr(state, "changes", [])),
            active_errors=self.compressor.deduplicate_errors(getattr(state, "errors", [])),
            recent_actions=self.compressor.compress_agent_outputs(getattr(state, "agent_outputs", []), max_recent_full=2),
        )
        context = AgentContext(
            role=role,
            task=task_ctx,
            repo=repo_ctx,
            history=history_ctx,
            memory_summary=memory.get_summary_for_prompt(max_facts=5),
            token_budget=token_budget,
        )
        context.estimated_tokens = self.compressor.estimate_tokens(context.to_prompt())
        return context
