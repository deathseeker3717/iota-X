"""Comprehensive unit tests for the Context Management subsystem."""

import json
import pytest

from harness.context import (
    AgentContext,
    AgentMemory,
    ContextCompressor,
    ContextManager,
    ContextSelector,
    HistoryContext,
    MemoryFact,
    MemoryTier,
    RepoContext,
    RepositoryMemory,
    ShortTermMemory,
    TaskContext,
    TaskMemory,
)
from harness.orchestrator.state import AgentResult, HarnessState, PlanStep


# ---------------------------------------------------------------------------
# 1. AgentMemory Tests
# ---------------------------------------------------------------------------


def test_short_term_memory_lifecycle():
    stm = ShortTermMemory()
    stm.current_plan_step = "Step 1"
    stm.active_files = ["src/auth.py"]
    stm.recent_errors = ["Error 1"]
    stm.scratchpad["key"] = "value"

    data = stm.to_dict()
    assert data["current_plan_step"] == "Step 1"
    assert data["active_files"] == ["src/auth.py"]

    restored = ShortTermMemory.from_dict(data)
    assert restored.current_plan_step == "Step 1"
    assert restored.scratchpad["key"] == "value"

    stm.clear()
    assert stm.current_plan_step is None
    assert len(stm.active_files) == 0
    assert len(stm.scratchpad) == 0


def test_task_memory_facts_and_decisions():
    tm = TaskMemory()
    fact = tm.add_fact(
        content="AuthService handles token refresh",
        category="architecture",
        source_agent="researcher",
        tags=["auth", "token"],
    )
    assert fact.content == "AuthService handles token refresh"
    assert len(tm.facts) == 1

    tm.record_decision("Use JWT bearer tokens instead of session cookies")
    tm.record_decision("Use JWT bearer tokens instead of session cookies")  # deduplicated
    assert len(tm.key_decisions) == 1

    tm.record_discarded_path("Direct database update without token invalidation")
    assert len(tm.discarded_paths) == 1

    arch_facts = tm.get_facts_by_category("architecture")
    assert len(arch_facts) == 1
    assert arch_facts[0].source_agent == "researcher"

    # Serialization roundtrip
    serialized = tm.to_dict()
    restored = TaskMemory.from_dict(serialized)
    assert len(restored.facts) == 1
    assert restored.facts[0].content == "AuthService handles token refresh"
    assert restored.key_decisions == ["Use JWT bearer tokens instead of session cookies"]


def test_repository_memory_and_full_agent_memory_roundtrip():
    memory = AgentMemory(repo_path="/workspace/repo")
    memory.repository.architecture_overview = "FastAPI backend with SQLAlchemy ORM"
    memory.repository.build_system = "poetry"
    memory.repository.test_framework = "pytest"
    memory.repository.set_module_description("auth", "Authentication and token lifecycle")
    memory.repository.set_symbol("verify_token", "Validates JWT signature and expiration")
    memory.repository.add_convention("All DB sessions must be managed with context managers")

    memory.record_fact("Bug located in refresh_token()", category="bug_location", source_agent="researcher")
    memory.record_decision("Refactor refresh_token to check revocation list")
    memory.record_discarded_path("Skipping expiration check")
    memory.update_short_term(
        plan_step="Refactor auth token logic",
        active_files=["src/auth/service.py"],
        error="InvalidSignatureError",
    )

    summary = memory.get_summary_for_prompt()
    assert "FastAPI backend" in summary
    assert "pytest" in summary
    assert "Bug located in refresh_token()" in summary
    assert "Refactor refresh_token" in summary
    assert "Skipping expiration check" in summary
    assert "src/auth/service.py" in summary

    json_str = memory.to_json()
    reloaded = AgentMemory.from_json(json_str)
    assert reloaded.repository.architecture_overview == "FastAPI backend with SQLAlchemy ORM"
    assert reloaded.repository.build_system == "poetry"
    assert len(reloaded.task.facts) == 1
    assert reloaded.task.facts[0].category == "bug_location"


# ---------------------------------------------------------------------------
# 2. ContextCompressor Tests
# ---------------------------------------------------------------------------


def test_context_compressor_token_estimation_and_truncation():
    compressor = ContextCompressor(char_to_token_ratio=4.0)

    text = "a" * 400
    est = compressor.estimate_tokens(text)
    assert est == 100

    # Truncate to 50 tokens (approx 200 chars)
    truncated = compressor.truncate_to_token_budget(text, max_tokens=50)
    assert len(truncated) < len(text)
    assert "...[truncated for token limit]" in truncated


def test_context_compressor_tool_output_compression():
    compressor = ContextCompressor()

    # Test failure log compression
    long_failure = (
        "pytest run starts...\n"
        + "\n".join([f"test line {i}" for i in range(50)])
        + "\nFAILED tests/test_auth.py::test_refresh - AssertionError: token mismatch\n"
        + "Traceback (most recent call last):\n"
        + "  File 'src/auth.py', line 42, in refresh\n"
        + "    assert token.is_valid\n"
        + "1 failed, 12 passed in 0.45s\n"
    )

    compressed = compressor.compress_tool_output(long_failure, max_lines=10, max_chars=400)
    assert "FAILED" in compressed
    assert len(compressed) <= 500

    # General output compression
    long_general = "\n".join([f"log item {i}" for i in range(100)])
    compressed_gen = compressor.compress_tool_output(long_general, max_lines=6, max_chars=200)
    assert "omitted" in compressed_gen or "truncated" in compressed_gen


def test_context_compressor_deduplicate_errors():
    compressor = ContextCompressor()
    raw_errors = [
        "NullPointerException at 0x7ffd1234 on line 42",
        "NullPointerException at 0x7ffd9876 on line 42",
        "NullPointerException at 0x7ffd1234 on line 99",
        "DatabaseConnectionTimeout",
    ]
    deduped = compressor.deduplicate_errors(raw_errors)
    # The normalized versions of the first three collapse because they share pattern
    assert len(deduped) <= 3
    assert "DatabaseConnectionTimeout" in deduped


def test_context_compressor_extract_facts():
    compressor = ContextCompressor()
    text = (
        "We discovered that AuthService handles token verification and user sessions. "
        "The bug is located in src/auth/token_manager.py. "
        "Existing tests are in tests/auth/test_tokens.py."
    )
    facts = compressor.extract_facts_from_text(text, source="researcher")
    categories = {f.category for f in facts}

    assert "architecture" in categories
    assert "bug_location" in categories
    assert "test" in categories

    arch_fact = next(f for f in facts if f.category == "architecture")
    assert "AuthService handles" in arch_fact.content


# ---------------------------------------------------------------------------
# 3. ContextSelector Tests
# ---------------------------------------------------------------------------


def test_context_selector_for_all_roles():
    selector = ContextSelector()
    memory = AgentMemory()
    memory.repository.architecture_overview = "Microservices architecture"
    memory.record_fact("AuthService handles token refresh", category="architecture")

    state = HarnessState(task="Fix token expiration crash")
    state.relevant_files = ["src/auth.py", "tests/test_auth.py"]
    state.plan = [PlanStep(step_id=1, description="Inspect AuthService", completed=True)]
    state.changes = ["Modified src/auth.py"]
    state.errors = ["KeyError: 'refresh_token'"]

    # 1. Planner
    p_ctx = selector.select_context("planner", state, memory)
    assert p_ctx.role == "planner"
    prompt_p = p_ctx.to_prompt()
    assert "## 1. TASK OBJECTIVE" in prompt_p
    assert "Fix token expiration crash" in prompt_p

    # 2. Researcher
    r_ctx = selector.select_context("researcher", state, memory)
    assert r_ctx.role == "researcher"
    prompt_r = r_ctx.to_prompt()
    assert "src/auth.py" in prompt_r

    # 3. Coder
    c_ctx = selector.select_context("coder", state, memory)
    assert c_ctx.role == "coder"
    prompt_c = c_ctx.to_prompt()
    assert "Inspect AuthService" in prompt_c

    # 4. Recovery
    state.test_results = [{"passed": False, "message": "AssertionError: Token expired"}]
    rec_ctx = selector.select_context("recovery", state, memory)
    assert rec_ctx.role == "recovery"
    prompt_rec = rec_ctx.to_prompt()
    assert "AssertionError: Token expired" in prompt_rec

    # Messages generation
    msgs = p_ctx.to_messages(system_prompt="You are a planner")
    assert len(msgs) == 2
    assert msgs[0]["role"] == "system"
    assert msgs[1]["role"] == "user"


# ---------------------------------------------------------------------------
# 4. ContextManager Tests
# ---------------------------------------------------------------------------


def test_context_manager_budget_enforcement():
    cm = ContextManager(default_token_budget=200)

    # Large file contents simulator
    def fake_file_loader(path: str) -> str:
        return "x = 1\n" * 1000

    cm.file_loader = fake_file_loader

    state = HarnessState(task="Refactor codebase")
    state.relevant_files = ["big_file.py"]

    context = cm.get_context_for_agent("coder", state, token_budget=150)
    assert context.estimated_tokens <= 250  # Enforced budget with compression


def test_context_manager_state_synchronization_and_system_prompts():
    cm = ContextManager()

    state = HarnessState(task="Fix auth bug")
    state.relevant_files = ["src/auth.py"]
    state.plan = [PlanStep(step_id=1, description="Check tokens", completed=False)]
    state.record_agent_result(
        AgentResult(
            agent_name="researcher",
            success=True,
            message="TokenService handles authentication. The bug is located in src/auth.py.",
        )
    )

    cm.update_from_state(state)

    # Memory should have captured active files and extracted facts
    assert "src/auth.py" in cm.memory.short_term.active_files
    assert cm.memory.short_term.current_plan_step == "Check tokens"
    facts = cm.memory.task.facts
    assert any("TokenService handles" in f.content for f in facts)
    assert any("src/auth.py" in f.content for f in facts)

    # Check system prompts
    planner_prompt = cm.get_system_prompt_for_agent("planner")
    assert "PLANNER AGENT" in planner_prompt

    coder_prompt = cm.get_system_prompt_for_agent("coder")
    assert "CODING AGENT" in coder_prompt

    recovery_prompt = cm.get_system_prompt_for_agent("recovery")
    assert "RECOVERY AGENT" in recovery_prompt
