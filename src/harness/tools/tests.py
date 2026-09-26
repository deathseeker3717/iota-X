"""Test runner and result parser tools for the AI Coding Harness.

Provides automated test execution and structured output parsing across:
- pytest / python unittest
- npm test / jest / vitest
- cargo test / go test
"""

from __future__ import annotations

import re
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from harness.model.schemas import ToolDefinition
from harness.tools.shell import CommandResult, ShellTool


@dataclass
class TestCaseResult:
    """Individual test case result."""

    name: str
    status: str  # passed, failed, error, skipped
    duration_seconds: float = 0.0
    message: Optional[str] = None
    file_path: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TestSuiteResult:
    """Aggregated test suite execution result."""

    framework: str
    total: int
    passed: int
    failed: int
    errors: int
    skipped: int
    duration_seconds: float
    success: bool
    test_cases: List[TestCaseResult] = field(default_factory=list)
    output: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["test_cases"] = [tc.to_dict() for tc in self.test_cases]
        return d


class TestRunnerTool:
    """Detects, runs, and parses test suite results."""

    __test__ = False

    def __init__(
        self,
        repo_dir: str = ".",
        shell_tool: Optional[ShellTool] = None,
    ) -> None:
        self.repo_dir = Path(repo_dir).resolve()
        self.shell_tool = shell_tool or ShellTool(working_dir=str(self.repo_dir))

    def detect_framework(self) -> str:
        """Auto-detect the test framework in use in the repository."""
        if (self.repo_dir / "pyproject.toml").exists() or (self.repo_dir / "pytest.ini").exists():
            return "pytest"
        if (self.repo_dir / "package.json").exists():
            return "npm"
        if (self.repo_dir / "Cargo.toml").exists():
            return "cargo"
        if (self.repo_dir / "go.mod").exists():
            return "go"
        if (self.repo_dir / "tests").is_dir():
            return "pytest"
        return "pytest"

    def run_tests(
        self,
        framework: Optional[str] = None,
        test_paths: Optional[List[str]] = None,
        filter_name: Optional[str] = None,
        timeout: float = 120.0,
    ) -> TestSuiteResult:
        """Run tests and parse structured results.

        Args:
            framework: Test framework ('pytest', 'npm', 'cargo', etc.). Auto-detected if None.
            test_paths: Specific test files or folders to run.
            filter_name: Test name substring/filter (e.g. -k in pytest).
            timeout: Timeout in seconds.

        Returns:
            TestSuiteResult with pass/fail counts and diagnostic test details.
        """
        fw = framework or self.detect_framework()
        start_time = time.monotonic()

        if fw == "pytest":
            cmd = self._build_pytest_command(test_paths, filter_name)
        elif fw == "npm":
            cmd = self._build_npm_command(test_paths, filter_name)
        elif fw == "cargo":
            cmd = f"cargo test {filter_name or ''}".strip()
        elif fw == "go":
            cmd = f"go test {(' '.join(test_paths)) if test_paths else './...'}"
        else:
            cmd = f"pytest {(' '.join(test_paths)) if test_paths else 'tests'}"

        res: CommandResult = self.shell_tool.execute(cmd, timeout=timeout)
        duration = round(time.monotonic() - start_time, 3)

        if fw == "pytest":
            return self._parse_pytest_output(res, duration)
        elif fw == "npm":
            return self._parse_npm_output(res, duration)
        else:
            return TestSuiteResult(
                framework=fw,
                total=0,
                passed=0,
                failed=0 if res.success else 1,
                errors=0,
                skipped=0,
                duration_seconds=duration,
                success=res.success,
                output=res.combined_output,
            )

    def _build_pytest_command(
        self,
        test_paths: Optional[List[str]],
        filter_name: Optional[str],
    ) -> str:
        # Check if .venv/bin/pytest exists
        venv_pytest = self.repo_dir / ".venv" / "bin" / "pytest"
        runner = f'"{venv_pytest}"' if venv_pytest.exists() else "pytest"
        parts = [runner, "-v"]
        if filter_name:
            parts.extend(["-k", f'"{filter_name}"'])
        if test_paths:
            parts.extend(test_paths)
        else:
            parts.append("tests")
        return " ".join(parts)

    def _build_npm_command(
        self,
        test_paths: Optional[List[str]],
        filter_name: Optional[str],
    ) -> str:
        parts = ["npm", "test", "--"]
        if filter_name:
            parts.extend(["-t", f'"{filter_name}"'])
        if test_paths:
            parts.extend(test_paths)
        return " ".join(parts)

    def _parse_pytest_output(
        self, cmd_res: CommandResult, duration: float
    ) -> TestSuiteResult:
        output = cmd_res.combined_output
        passed = 0
        failed = 0
        errors = 0
        skipped = 0

        # Pattern: e.g. "== 4 passed in 0.05s ==" or "== 1 failed, 3 passed in 0.2s =="
        summary_match = re.search(r"===+ (.*?) in \d+\.\d+s ===+", output)
        if summary_match:
            summary_line = summary_match.group(1)
            p_m = re.search(r"(\d+)\s+passed", summary_line)
            f_m = re.search(r"(\d+)\s+failed", summary_line)
            e_m = re.search(r"(\d+)\s+error", summary_line)
            s_m = re.search(r"(\d+)\s+skipped", summary_line)
            if p_m:
                passed = int(p_m.group(1))
            if f_m:
                failed = int(f_m.group(1))
            if e_m:
                errors = int(e_m.group(1))
            if s_m:
                skipped = int(s_m.group(1))
        else:
            # Fallback counting
            passed = len(re.findall(r"::\w+\s+PASSED", output))
            failed = len(re.findall(r"::\w+\s+FAILED", output))
            errors = len(re.findall(r"::\w+\s+ERROR", output))
            skipped = len(re.findall(r"::\w+\s+SKIPPED", output))

        total = passed + failed + errors + skipped
        success = cmd_res.success and failed == 0 and errors == 0

        # Extract failed test case details
        test_cases: List[TestCaseResult] = []
        for line in output.splitlines():
            m = re.match(r"(tests/\S+::(\S+))\s+(PASSED|FAILED|ERROR|SKIPPED)", line)
            if m:
                full_test_path, test_name, status = m.group(1), m.group(2), m.group(3).lower()
                file_path = full_test_path.split("::")[0]
                test_cases.append(
                    TestCaseResult(
                        name=test_name,
                        status=status,
                        file_path=file_path,
                    )
                )

        return TestSuiteResult(
            framework="pytest",
            total=total,
            passed=passed,
            failed=failed,
            errors=errors,
            skipped=skipped,
            duration_seconds=cmd_res.duration_seconds or duration,
            success=success,
            test_cases=test_cases,
            output=output,
        )

    def _parse_npm_output(
        self, cmd_res: CommandResult, duration: float
    ) -> TestSuiteResult:
        output = cmd_res.combined_output
        passed = 0
        failed = 0
        total = 0

        # Jest summary: "Tests:       1 failed, 4 passed, 5 total"
        m = re.search(r"Tests:\s+(.*)", output)
        if m:
            summary = m.group(1)
            p_m = re.search(r"(\d+)\s+passed", summary)
            f_m = re.search(r"(\d+)\s+failed", summary)
            t_m = re.search(r"(\d+)\s+total", summary)
            if p_m:
                passed = int(p_m.group(1))
            if f_m:
                failed = int(f_m.group(1))
            if t_m:
                total = int(t_m.group(1))

        return TestSuiteResult(
            framework="npm",
            total=total or (passed + failed),
            passed=passed,
            failed=failed,
            errors=0,
            skipped=0,
            duration_seconds=cmd_res.duration_seconds or duration,
            success=cmd_res.success and failed == 0,
            test_cases=[],
            output=output,
        )


# Default module-level instance
_default_test_runner = TestRunnerTool()


def run_tests(
    framework: Optional[str] = None,
    test_paths: Optional[List[str]] = None,
    filter_name: Optional[str] = None,
    timeout: float = 120.0,
) -> TestSuiteResult:
    return _default_test_runner.run_tests(framework, test_paths, filter_name, timeout)


def get_test_tool_definitions() -> List[ToolDefinition]:
    """Return ToolDefinition schemas for test runner tool."""
    return [
        ToolDefinition(
            name="run_tests",
            description="Run test suite (pytest, npm test) and return structured test results with failure diagnostics.",
            parameters={
                "type": "object",
                "properties": {
                    "framework": {
                        "type": "string",
                        "description": "Test runner framework: 'pytest' or 'npm'",
                    },
                    "test_paths": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional list of test files/directories to run",
                    },
                    "filter_name": {
                        "type": "string",
                        "description": "Filter test names matching pattern",
                    },
                },
            },
        )
    ]
