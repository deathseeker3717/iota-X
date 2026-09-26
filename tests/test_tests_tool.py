"""Unit tests for the TestRunnerTool."""

import pytest
from pathlib import Path
from harness.tools.tests import (
    TestRunnerTool,
    get_test_tool_definitions,
    run_tests,
)
from harness.tools.shell import CommandResult


def test_detect_framework(tmp_path):
    runner = TestRunnerTool(repo_dir=str(tmp_path))

    # Pytest detection via pyproject.toml
    (tmp_path / "pyproject.toml").write_text("[project]\nname='test'\n")
    assert runner.detect_framework() == "pytest"

    # npm detection
    (tmp_path / "pyproject.toml").unlink()
    (tmp_path / "package.json").write_text('{"name": "test"}')
    assert runner.detect_framework() == "npm"


def test_parse_pytest_output():
    runner = TestRunnerTool()
    sample_output = """
============================= test session starts ==============================
rootdir: /path/to/project
collected 5 items

tests/test_foo.py::test_one PASSED                                       [ 20%]
tests/test_foo.py::test_two PASSED                                       [ 40%]
tests/test_foo.py::test_three FAILED                                     [ 60%]
tests/test_bar.py::test_four SKIPPED                                     [ 80%]
tests/test_bar.py::test_five PASSED                                      [100%]

=================================== FAILURES ===================================
__________________________________ test_three __________________________________
    def test_three():
>       assert 1 == 2
E       assert 1 == 2
=================== 1 failed, 3 passed, 1 skipped in 0.15s ====================
"""
    cmd_res = CommandResult(
        command="pytest",
        exit_code=1,
        stdout=sample_output,
        stderr="",
        duration_seconds=0.15,
    )
    result = runner._parse_pytest_output(cmd_res, duration=0.15)

    assert result.framework == "pytest"
    assert result.passed == 3
    assert result.failed == 1
    assert result.skipped == 1
    assert result.total == 5
    assert result.success is False
    assert len(result.test_cases) == 5

    failed_tc = [tc for tc in result.test_cases if tc.status == "failed"]
    assert len(failed_tc) == 1
    assert failed_tc[0].name == "test_three"
    assert failed_tc[0].file_path == "tests/test_foo.py"


def test_run_real_tests_in_repo():
    # Running a specific test file that passes
    res = run_tests(framework="pytest", test_paths=["tests/test_model_gateway.py"])
    assert res.framework == "pytest"
    assert res.passed == 4
    assert res.failed == 0
    assert res.success is True


def test_test_tool_definitions():
    defs = get_test_tool_definitions()
    assert len(defs) == 1
    assert defs[0].name == "run_tests"
