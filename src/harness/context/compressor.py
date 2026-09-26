"""Context compression, history distillation, and token budgeting utilities."""

import re
from typing import Any, Dict, List, Optional, Tuple

from harness.context.memory import MemoryFact


class ContextCompressor:
    """Compresses verbose agent histories, tool outputs, and error logs into dense, high-signal context."""

    def __init__(self, char_to_token_ratio: float = 4.0) -> None:
        self.char_to_token_ratio = char_to_token_ratio

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for a text string using char and whitespace heuristic."""
        if not text:
            return 0
        # Roughly 1 token ~= 4 characters / 0.75 words
        return max(1, int(len(text) / self.char_to_token_ratio))

    def truncate_to_token_budget(self, text: str, max_tokens: int, suffix: str = "\n...[truncated for token limit]") -> str:
        """Truncate text to stay strictly within token budget."""
        if max_tokens <= 0:
            return ""
        est_tokens = self.estimate_tokens(text)
        if est_tokens <= max_tokens:
            return text

        max_chars = int(max_tokens * self.char_to_token_ratio) - len(suffix)
        if max_chars <= 0:
            return suffix[:int(max_tokens * self.char_to_token_ratio)]
        return text[:max_chars] + suffix

    def compress_tool_output(self, output: str, max_lines: int = 15, max_chars: int = 600) -> str:
        """Compress large tool execution outputs (e.g. git diff, pytest run, grep)."""
        if not output:
            return ""

        output = output.strip()
        lines = output.splitlines()

        if len(lines) <= max_lines and len(output) <= max_chars:
            return output

        # If it's a test failure, preserve the failure summary and last lines
        if "FAILED" in output or "ERROR" in output or "Traceback" in output:
            # Find traceback or error lines
            error_lines = [l for l in lines if any(k in l for k in ("FAIL", "ERROR", "Error:", "Exception:", "assert", "Traceback"))]
            tail_lines = lines[-min(5, len(lines)):]
            condensed = error_lines[:min(8, len(error_lines))] + ["..."] + tail_lines
            res = "\n".join(condensed)
            if len(res) > max_chars:
                return res[:max_chars] + "\n...[truncated output]"
            return res

        # General long output: take head and tail
        half_lines = max(2, max_lines // 2)
        head = lines[:half_lines]
        tail = lines[-half_lines:]
        condensed = head + [f"... ({len(lines) - 2 * half_lines} lines omitted) ..."] + tail
        result = "\n".join(condensed)
        if len(result) > max_chars:
            return result[:max_chars] + "\n...[truncated output]"
        return result

    def deduplicate_errors(self, errors: List[str]) -> List[str]:
        """Normalize and deduplicate repeated error messages and stack traces."""
        seen = set()
        deduped = []

        for err in errors:
            if not err:
                continue
            # Normalize common variable parts like line numbers and memory addresses
            normalized = re.sub(r"0x[0-9a-fA-F]+", "0x...", err)
            normalized = re.sub(r"line \d+", "line <N>", normalized)
            normalized_key = normalized.strip()

            if normalized_key not in seen:
                seen.add(normalized_key)
                deduped.append(err.strip())

        return deduped

    def compress_agent_outputs(
        self,
        agent_outputs: List[Any],
        max_recent_full: int = 3,
    ) -> List[Dict[str, Any]]:
        """Summarize older agent results into compact bullet points while keeping recent ones detailed."""
        if not agent_outputs:
            return []

        summarized: List[Dict[str, Any]] = []
        total = len(agent_outputs)

        for i, res in enumerate(agent_outputs):
            agent_name = getattr(res, "agent_name", str(res))
            success = getattr(res, "success", True)
            message = getattr(res, "message", "")
            errors = getattr(res, "errors", [])

            # For recent outputs, keep more detail
            if i >= total - max_recent_full:
                summarized.append({
                    "step": i + 1,
                    "agent": agent_name,
                    "status": "SUCCESS" if success else "FAILED",
                    "summary": message,
                    "errors": errors,
                    "detailed": True,
                })
            else:
                # Older outputs: compress to 1-line gist
                gist = message.splitlines()[0] if message else ("Completed successfully" if success else "Failed")
                if len(gist) > 120:
                    gist = gist[:117] + "..."
                summarized.append({
                    "step": i + 1,
                    "agent": agent_name,
                    "status": "SUCCESS" if success else "FAILED",
                    "summary": gist,
                    "detailed": False,
                })

        return summarized

    def extract_facts_from_text(self, text: str, source: Optional[str] = None) -> List[MemoryFact]:
        """Heuristic rule-based fact extractor for identifying architecture, symbols, and test locations."""
        facts: List[MemoryFact] = []
        if not text:
            return facts

        # Pattern 1: Module / Service handles X
        for match in re.finditer(r"([A-Za-z0-9_]+)\s+(handles|manages|implements|controls)\s+([^.\n]+)", text, re.IGNORECASE):
            facts.append(
                MemoryFact(
                    content=f"{match.group(1)} {match.group(2)} {match.group(3).strip()}",
                    category="architecture",
                    source_agent=source,
                    tags=["discovered", "component"],
                )
            )

        # Pattern 2: Bug located in / Root cause in X
        for match in re.finditer(r"(bug|root cause|issue|error)\s+(is located in|in|caused by)\s+([`A-Za-z0-9_./]+)", text, re.IGNORECASE):
            facts.append(
                MemoryFact(
                    content=f"Root cause in {match.group(3).strip('`')}",
                    category="bug_location",
                    source_agent=source,
                    tags=["root_cause"],
                )
            )

        # Pattern 3: Tests located in X
        for match in re.finditer(r"tests?\s+(are in|located in|found in)\s+([`A-Za-z0-9_./]+)", text, re.IGNORECASE):
            facts.append(
                MemoryFact(
                    content=f"Tests in {match.group(2).strip('`')}",
                    category="test",
                    source_agent=source,
                    tags=["tests"],
                )
            )

        return facts
