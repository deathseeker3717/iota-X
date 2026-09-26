/**
 * Realistic Mock API Service for AI Coding Harness
 *
 * Simulates complete backend functionality:
 * - File tree & contents
 * - Autonomous coding agent execution (Planning -> Search -> Coding -> Tests -> Verification)
 * - Controlled terminal execution
 * - Git diffs
 * - Test suite verification
 */

import {
  AgentStep,
  ChatMessage,
  GitChange,
  TerminalOutput,
  VerificationResult,
  WorkspaceFile,
} from '../types';
import { HarnessApiService } from './api';

const MOCK_FILES: Record<string, string> = {
  'src/harness/tools/filesystem.py': `"""Filesystem tools for the AI Coding Harness.

Provides safe, sandboxed file operations: listing, reading, writing, and editing files.
"""

from __future__ import annotations

import fnmatch
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

class FilesystemTool:
    """Provides sandboxed filesystem operations."""

    def __init__(self, root_dir: str = ".", enforce_sandbox: bool = True) -> None:
        self.root_dir = Path(root_dir).resolve()
        self.enforce_sandbox = enforce_sandbox

    def list_files(self, directory: str = ".") -> List[str]:
        return ["src/auth/session.py", "src/auth/login.py"]

    def read_file(self, path: str) -> str:
        return Path(path).read_text()
`,
  'src/harness/repository/context.py': `"""Repository context selection for the AI Coding Harness.

Implements query-driven context selection:
Issue / Query -> Repository Search -> Relevant Files -> Relevant Functions/Classes.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List

@dataclass
class RelevantFile:
    file_path: str
    score: float
    rationale: str

class RepositoryContextManager:
    def find_relevant_context(self, query: str) -> List[RelevantFile]:
        # Expands query tokens, computes multi-factor relevance
        return [
            RelevantFile("src/auth/session.py", 0.95, "Contains token timeout logic"),
            RelevantFile("src/auth/login.py", 0.88, "Handles authentication flow")
        ]
`,
  'src/harness/orchestrator/orchestrator.py': `"""Central Orchestrator managing specialized agent roles and workflow."""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

@dataclass
class TaskContext:
    task_id: str
    description: str
    state: str = "INITIALIZED"

class CentralOrchestrator:
    def __init__(self) -> None:
        self.iteration_limit = 10
        self.current_state = "IDLE"

    async def execute_task(self, prompt: str) -> Dict[str, Any]:
        """Runs the autonomous harness cycle: Plan -> Code -> Verify."""
        return {"status": "SUCCESS", "verified": True}
`,
  'src/auth/session.py': `"""User Session and JWT management."""

import time
from typing import Optional

class SessionManager:
    def __init__(self, session_timeout_seconds: int = 300) -> None:
        # BUG: Timeout was hardcoded to 5 seconds causing frequent drops
        self.session_timeout_seconds = session_timeout_seconds
        self.active_sessions: dict = {}

    def is_session_valid(self, session_id: str, last_activity: float) -> bool:
        """Verify if session has exceeded expiration limit."""
        elapsed = time.time() - last_activity
        if elapsed > self.session_timeout_seconds:
            return False
        return True

    def refresh_session(self, session_id: str) -> bool:
        if session_id in self.active_sessions:
            self.active_sessions[session_id] = time.time()
            return True
        return False
`,
  'tests/test_auth.py': `"""Tests for session and authentication flows."""

import time
import pytest
from src.auth.session import SessionManager

def test_session_expiration():
    manager = SessionManager(session_timeout_seconds=2)
    now = time.time()
    assert manager.is_session_valid("user_1", now) is True
    assert manager.is_session_valid("user_1", now - 5) is False

def test_session_refresh():
    manager = SessionManager(session_timeout_seconds=60)
    manager.active_sessions["s123"] = time.time() - 30
    assert manager.refresh_session("s123") is True
`,
  'README.md': `# AI Coding Harness (Hackathon 2026)

Centralized orchestrated foundation model harness for autonomous software engineering.
`,
  'pyproject.toml': `[project]
name = "ai-coding-harness"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = [
    "pyyaml>=6.0.1",
    "python-dotenv>=1.0.0",
]
`,
};

export class MockApiService implements HarnessApiService {
  private files: Record<string, string> = { ...MOCK_FILES };

  async getRepositoryTree(): Promise<WorkspaceFile[]> {
    return [
      {
        id: 'src',
        name: 'src',
        path: 'src',
        type: 'directory',
        children: [
          {
            id: 'src/auth',
            name: 'auth',
            path: 'src/auth',
            type: 'directory',
            children: [
              {
                id: 'src/auth/session.py',
                name: 'session.py',
                path: 'src/auth/session.py',
                type: 'file',
                language: 'python',
              },
            ],
          },
          {
            id: 'src/harness',
            name: 'harness',
            path: 'src/harness',
            type: 'directory',
            children: [
              {
                id: 'src/harness/tools',
                name: 'tools',
                path: 'src/harness/tools',
                type: 'directory',
                children: [
                  {
                    id: 'src/harness/tools/filesystem.py',
                    name: 'filesystem.py',
                    path: 'src/harness/tools/filesystem.py',
                    type: 'file',
                    language: 'python',
                  },
                ],
              },
              {
                id: 'src/harness/repository',
                name: 'repository',
                path: 'src/harness/repository',
                type: 'directory',
                children: [
                  {
                    id: 'src/harness/repository/context.py',
                    name: 'context.py',
                    path: 'src/harness/repository/context.py',
                    type: 'file',
                    language: 'python',
                  },
                ],
              },
              {
                id: 'src/harness/orchestrator',
                name: 'orchestrator',
                path: 'src/harness/orchestrator',
                type: 'directory',
                children: [
                  {
                    id: 'src/harness/orchestrator/orchestrator.py',
                    name: 'orchestrator.py',
                    path: 'src/harness/orchestrator/orchestrator.py',
                    type: 'file',
                    language: 'python',
                  },
                ],
              },
            ],
          },
        ],
      },
      {
        id: 'tests',
        name: 'tests',
        path: 'tests',
        type: 'directory',
        children: [
          {
            id: 'tests/test_auth.py',
            name: 'test_auth.py',
            path: 'tests/test_auth.py',
            type: 'file',
            language: 'python',
          },
        ],
      },
      {
        id: 'README.md',
        name: 'README.md',
        path: 'README.md',
        type: 'file',
        language: 'markdown',
      },
      {
        id: 'pyproject.toml',
        name: 'pyproject.toml',
        path: 'pyproject.toml',
        type: 'file',
        language: 'toml',
      },
    ];
  }

  async getFileContent(path: string): Promise<string> {
    return (
      this.files[path] ||
      `# Content for ${path}\n# Auto-generated or not yet written.\n`
    );
  }

  async saveFileContent(path: string, content: string): Promise<boolean> {
    this.files[path] = content;
    return true;
  }

  async sendMessage(
    message: string,
    history: ChatMessage[],
    onChunk?: (chunk: string) => void
  ): Promise<ChatMessage> {
    // Simulate streaming delay
    const responseText = `I have investigated the task: **"${message}"**.

### 1. Repository Intelligence Research
Using \`RepositoryContextManager\`, I located the relevant files:
- \`src/auth/session.py\` (Relevance: 0.95)
- \`tests/test_auth.py\` (Relevance: 0.88)

### 2. Root Cause Analysis
In \`SessionManager\`, session expiration checked elapsed seconds against an aggressively short threshold. I have updated the timeout configuration and added safe session refresh handling.

\`\`\`python
# src/auth/session.py
def is_session_valid(self, session_id: str, last_activity: float) -> bool:
    elapsed = time.time() - last_activity
    if elapsed > self.session_timeout_seconds:
        return False
    return True
\`\`\`

### 3. Verification
Ran \`pytest tests/test_auth.py\`:
**2 passed in 0.04s (100% verified)**.
`;

    if (onChunk) {
      const words = responseText.split(' ');
      for (let i = 0; i < words.length; i++) {
        await new Promise((r) => setTimeout(r, 15));
        onChunk(words[i] + ' ');
      }
    }

    return {
      id: `msg_${Date.now()}`,
      role: 'assistant',
      content: responseText,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      referencedFiles: ['src/auth/session.py', 'tests/test_auth.py'],
      actions: [
        {
          id: `act_${Date.now()}`,
          type: 'file_edit',
          file: 'src/auth/session.py',
          summary: 'Fixed session timeout handling and added refresh_session support',
          diff: `--- src/auth/session.py
+++ src/auth/session.py
@@ -10,3 +10,7 @@
-        self.session_timeout_seconds = 5
+        self.session_timeout_seconds = session_timeout_seconds
+    def refresh_session(self, session_id: str) -> bool:
+        if session_id in self.active_sessions:
+            self.active_sessions[session_id] = time.time()
+            return True
+        return False`,
          status: 'pending',
        },
      ],
    };
  }

  async runCommand(command: string): Promise<TerminalOutput> {
    await new Promise((r) => setTimeout(r, 600));

    if (command.includes('pytest')) {
      return {
        id: `term_${Date.now()}`,
        command,
        stdout: `============================= test session starts ==============================
platform darwin -- Python 3.14.2, pytest-9.1.1, pluggy-1.6.0
rootdir: /workspace/ai-coding-harness
collected 67 items

tests/test_agents.py .....                                               [  7%]
tests/test_context.py ..                                                 [ 10%]
tests/test_context_manager.py ..........                                 [ 25%]
tests/test_filesystem_tool.py ......                                     [ 34%]
tests/test_git_tool.py ...                                               [ 38%]
tests/test_indexer.py ...                                                [ 43%]
tests/test_mapper.py ...                                                 [ 47%]
tests/test_model_gateway.py ....                                         [ 53%]
tests/test_observability.py .....                                        [ 61%]
tests/test_orchestrator.py .....                                         [ 68%]
tests/test_orchestrator_integration.py .                                 [ 70%]
tests/test_search_tool.py .....                                          [ 77%]
tests/test_shell_tool.py .......                                         [ 88%]
tests/test_symbols.py ..                                                 [ 91%]
tests/test_tests_tool.py ....                                            [ 97%]
tests/test_tool_registry.py ..                                           [100%]

============================== 67 passed in 1.08s ==============================`,
        stderr: '',
        exitCode: 0,
        durationSeconds: 1.08,
        status: 'success',
        timestamp: new Date().toLocaleTimeString(),
      };
    }

    if (command.includes('git status')) {
      return {
        id: `term_${Date.now()}`,
        command,
        stdout: `On branch tools-repository\nYour branch is up to date with 'origin/tools-repository'.\n\nChanges not staged for commit:\n  modified:   src/auth/session.py\n\nno changes added to commit (use "git add" to track)`,
        stderr: '',
        exitCode: 0,
        durationSeconds: 0.12,
        status: 'success',
        timestamp: new Date().toLocaleTimeString(),
      };
    }

    return {
      id: `term_${Date.now()}`,
      command,
      stdout: `$ ${command}\nTask executed successfully with code 0.`,
      stderr: '',
      exitCode: 0,
      durationSeconds: 0.45,
      status: 'success',
      timestamp: new Date().toLocaleTimeString(),
    };
  }

  async getGitChanges(): Promise<GitChange[]> {
    return [
      {
        file: 'src/auth/session.py',
        status: 'modified',
        additions: 12,
        deletions: 3,
        diff: `@@ -10,3 +10,12 @@
-        self.session_timeout_seconds = 5
+        self.session_timeout_seconds = session_timeout_seconds
+        self.active_sessions: dict = {}
+
+    def is_session_valid(self, session_id: str, last_activity: float) -> bool:
+        elapsed = time.time() - last_activity
+        if elapsed > self.session_timeout_seconds:
+            return False
+        return True
+
+    def refresh_session(self, session_id: str) -> bool:
+        if session_id in self.active_sessions:
+            self.active_sessions[session_id] = time.time()
+            return True
+        return False`,
      },
      {
        file: 'tests/test_auth.py',
        status: 'modified',
        additions: 8,
        deletions: 1,
        diff: `@@ -12,2 +12,9 @@
+def test_session_refresh():
+    manager = SessionManager(session_timeout_seconds=60)
+    manager.active_sessions["s123"] = time.time() - 30
+    assert manager.refresh_session("s123") is True`,
      },
    ];
  }

  async getGitDiff(file?: string): Promise<string> {
    const changes = await this.getGitChanges();
    if (file) {
      const match = changes.find((c) => c.file === file);
      return match?.diff || '';
    }
    return changes.map((c) => `--- a/${c.file}\n+++ b/${c.file}\n${c.diff || ''}`).join('\n\n');
  }

  async runTests(filter?: string): Promise<VerificationResult> {
    await new Promise((r) => setTimeout(r, 700));

    return {
      status: 'verified',
      testsPassed: true,
      totalTests: 67,
      passedTests: 67,
      failedTests: 0,
      typeCheckPassed: true,
      lintPassed: true,
      requirementsSatisfied: true,
      failures: [],
      durationSeconds: 1.08,
    };
  }

  async getAgentWorkflow(): Promise<AgentStep[]> {
    return [
      {
        id: '1',
        title: 'Task received: "Fix authentication timeout issue"',
        status: 'completed',
        details: 'Parsed requirements and established acceptance criteria.',
      },
      {
        id: '2',
        title: 'Repository research & indexing',
        status: 'completed',
        details: 'Scanned 33 source files; identified session.py and test_auth.py.',
        subSteps: ['Token-budget repo map generated', 'Symbol AST parsed: SessionManager'],
      },
      {
        id: '3',
        title: 'Formulating code edit plan',
        status: 'completed',
        details: 'Plan approved: parameterize session timeout and implement refresh_session().',
      },
      {
        id: '4',
        title: 'Applying targeted code modifications',
        status: 'completed',
        details: 'Patched src/auth/session.py lines 10-22 using edit_file tool.',
      },
      {
        id: '5',
        title: 'Test suite execution & verification',
        status: 'completed',
        details: 'Executed pytest tests: 67 passed in 1.08s.',
        subSteps: ['Pyright typecheck: 0 errors', 'Ruff lint: clean'],
      },
      {
        id: '6',
        title: 'Task Verified',
        status: 'completed',
        details: 'Solution verified and ready for git commit.',
      },
    ];
  }
}

export const mockApiService = new MockApiService();
