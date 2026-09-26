/**
 * Terminal API Service
 *
 * Implements the cross-platform Terminal / Controlled Shell Tool contract.
 *
 * ARCHITECTURAL CONSTRAINTS:
 * - Clients MUST NOT execute arbitrary shell commands themselves.
 * - All terminal requests route to:
 *   Web / macOS / Android -> Terminal API -> Harness Backend -> Controlled Shell Tool -> Repository
 * - The backend Shell Tool enforces sandboxing, blocked commands, and timeout safety.
 */

import {
  CommandRequest,
  CommandResult,
  TerminalOutput,
} from '../types/terminalContract';

export interface TerminalApiService {
  /** Execute a shell command through the backend's controlled shell tool */
  executeCommand(request: CommandRequest): Promise<CommandResult>;

  /** Abort an active shell command execution */
  cancelCommand(commandId: string): Promise<boolean>;

  /** Retrieve recent terminal output history */
  getHistory(): Promise<TerminalOutput[]>;

  /** Clear terminal output history */
  clearHistory(): Promise<boolean>;
}

// ============================================================================
// Concrete Implementation: MockTerminalApiService
// Clearly separated mock service simulating the backend's controlled shell tool.
// ============================================================================

export class MockTerminalApiService implements TerminalApiService {
  private history: TerminalOutput[] = [];
  private activeExecutions: Set<string> = new Set();

  constructor() {
    // Seed initial session terminal history
    this.history = [
      {
        id: 'term_init_1',
        command: 'pytest tests',
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

============================== 67 passed in 1.02s ==============================`,
        stderr: '',
        exitCode: 0,
        durationSeconds: 1.02,
        status: 'success',
        timestamp: 'Initial',
        cwd: 'iota-X',
      },
    ];
  }

  async executeCommand(request: CommandRequest): Promise<CommandResult> {
    const execId = `cmd_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`;
    this.activeExecutions.add(execId);

    const cmd = request.command.trim();

    // 1. Security Check: Controlled Shell Tool blocking policy (matching src/harness/tools/shell.py)
    const dangerousPatterns = [
      /\brm\s+-[a-zA-Z]*[rR][a-zA-Z]*\s+(?:\/|\~|\*|\$HOME)/,
      /: \(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;/, // fork bomb
      /\bmkfs\b/,
      /\bshutdown\b/,
      /\breboot\b/,
    ];

    for (const pattern of dangerousPatterns) {
      if (pattern.test(cmd)) {
        this.activeExecutions.delete(execId);
        return {
          id: execId,
          command: cmd,
          stdout: '',
          stderr: `SECURITY ERROR: Command '${cmd}' is blocked by the Controlled Shell Tool security policy.\nDestructive root / fork operations are strictly forbidden.`,
          exitCode: 126,
          durationSeconds: 0.05,
          status: 'failed',
          timestamp: new Date().toISOString(),
        };
      }
    }

    // 2. Simulate process execution duration
    const executionDuration = Math.min(request.timeoutSeconds || 5, 0.7);
    await new Promise((r) => setTimeout(r, executionDuration * 1000));

    if (!this.activeExecutions.has(execId)) {
      return {
        id: execId,
        command: cmd,
        stdout: '',
        stderr: 'Process terminated by user (SIGINT).',
        exitCode: 130,
        durationSeconds: 0.3,
        status: 'cancelled',
        timestamp: new Date().toISOString(),
      };
    }

    this.activeExecutions.delete(execId);

    // 3. Command Output Evaluation
    const result = this.resolveCommandOutput(cmd, execId, executionDuration);

    // Append to internal history
    this.history.push({
      id: result.id,
      command: result.command,
      stdout: result.stdout,
      stderr: result.stderr,
      exitCode: result.exitCode,
      durationSeconds: result.durationSeconds,
      status: result.status === 'success' ? 'success' : 'failed',
      timestamp: new Date().toLocaleTimeString(),
      cwd: request.workingDirectory || 'iota-X',
    });

    return result;
  }

  async cancelCommand(commandId: string): Promise<boolean> {
    if (this.activeExecutions.has(commandId)) {
      this.activeExecutions.delete(commandId);
      return true;
    }
    return false;
  }

  async getHistory(): Promise<TerminalOutput[]> {
    return [...this.history];
  }

  async clearHistory(): Promise<boolean> {
    this.history = [];
    return true;
  }

  private resolveCommandOutput(
    command: string,
    id: string,
    durationSeconds: number
  ): CommandResult {
    const cmd = command.trim();
    const timestamp = new Date().toISOString();

    if (cmd === 'pytest' || cmd.startsWith('pytest')) {
      if (cmd.includes('test_auth')) {
        return {
          id,
          command: cmd,
          stdout: `============================= test session starts ==============================
rootdir: /workspace/ai-coding-harness
collected 2 items

tests/test_auth.py::test_session_expiration PASSED                       [ 50%]
tests/test_auth.py::test_session_refresh PASSED                          [100%]

============================== 2 passed in 0.04s ===============================`,
          stderr: '',
          exitCode: 0,
          durationSeconds: 0.45,
          status: 'success',
          timestamp,
        };
      }

      return {
        id,
        command: cmd,
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

============================== 67 passed in 1.02s ==============================`,
        stderr: '',
        exitCode: 0,
        durationSeconds: 1.02,
        status: 'success',
        timestamp,
      };
    }

    if (cmd === 'git status' || cmd.startsWith('git status')) {
      return {
        id,
        command: cmd,
        stdout: `On branch frontend-workspace\nYour branch is up to date with 'origin/frontend-workspace'.\n\nChanges not staged for commit:\n  (use "git add <file>..." to update what will be committed)\n\tmodified:   src/auth/session.py\n\nno changes added to commit (use "git add" to track)`,
        stderr: '',
        exitCode: 0,
        durationSeconds: 0.12,
        status: 'success',
        timestamp,
      };
    }

    if (cmd === 'git diff' || cmd.startsWith('git diff')) {
      return {
        id,
        command: cmd,
        stdout: `diff --git a/src/auth/session.py b/src/auth/session.py
index 4b825dc..3c9a012 100644
--- a/src/auth/session.py
+++ b/src/auth/session.py
@@ -10,3 +10,8 @@
-        self.session_timeout_seconds = 5
+        self.session_timeout_seconds = session_timeout_seconds
+    def refresh_session(self, session_id: str) -> bool:
+        if session_id in self.active_sessions:
+            self.active_sessions[session_id] = time.time()
+            return True
+        return False`,
        stderr: '',
        exitCode: 0,
        durationSeconds: 0.15,
        status: 'success',
        timestamp,
      };
    }

    if (cmd === 'python -m harness.main') {
      return {
        id,
        command: cmd,
        stdout: `[HARNESS 03:00:12] Initialized AI Coding Harness Orchestrator v0.1.0
[HARNESS 03:00:12] Registered tools: filesystem, search, shell, git, tests
[HARNESS 03:00:13] Inverted index built: 33 files, 128 symbols parsed
[HARNESS 03:00:13] Status: READY. Autonomous agents initialized (Planner, Coder, Critic, Verifier).`,
        stderr: '',
        exitCode: 0,
        durationSeconds: 0.65,
        status: 'success',
        timestamp,
      };
    }

    if (cmd === 'pwd') {
      return {
        id,
        command: cmd,
        stdout: `/workspace/ai-coding-harness/iota-X`,
        stderr: '',
        exitCode: 0,
        durationSeconds: 0.05,
        status: 'success',
        timestamp,
      };
    }

    if (cmd === 'ls' || cmd === 'ls -la') {
      return {
        id,
        command: cmd,
        stdout: `total 64
drwxr-xr-x  14 user  staff   448 Sep 27 02:53 .
drwxr-xr-x   6 user  staff   192 Sep 27 00:00 ..
-rw-r--r--   1 user  staff  1136 Sep 27 02:52 Makefile
-rw-r--r--   1 user  staff  3446 Sep 27 01:00 README.md
drwxr-xr-x   5 user  staff   160 Sep 27 02:53 docs
drwxr-xr-x  16 user  staff   512 Sep 27 02:53 frontend
-rw-r--r--   1 user  staff   536 Sep 27 00:30 pyproject.toml
drwxr-xr-x   4 user  staff   128 Sep 27 00:00 src
drwxr-xr-x  18 user  staff   576 Sep 27 00:00 tests`,
        stderr: '',
        exitCode: 0,
        durationSeconds: 0.08,
        status: 'success',
        timestamp,
      };
    }

    // Default fallback execution
    return {
      id,
      command: cmd,
      stdout: `$ ${cmd}\nProcess executed in controlled sandbox environment.`,
      stderr: '',
      exitCode: 0,
      durationSeconds: Math.max(0.1, durationSeconds),
      status: 'success',
      timestamp,
    };
  }
}

export const terminalApi: TerminalApiService = new MockTerminalApiService();
