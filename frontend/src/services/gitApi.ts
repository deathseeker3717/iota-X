/**
 * AI Coding Harness — Git Integration API Service
 *
 * Exclusively queries the backend Git Tool (src/harness/tools/git.py).
 * Clients MUST NOT execute Git commands directly on host machines.
 */

import {
  GitCommit,
  GitDiff,
  GitDiffOptions,
  GitLogOptions,
  GitStatus,
  IGitApiService,
} from '../types/gitContract';

export const USE_MOCK_GIT_API = true;

/**
 * Production Git API Client communicating with the Harness Backend API.
 */
export class GitApiService implements IGitApiService {
  private baseUrl: string;

  constructor(baseUrl: string = '/api/v1/git') {
    this.baseUrl = baseUrl;
  }

  async getStatus(): Promise<GitStatus> {
    const res = await fetch(`${this.baseUrl}/status`);
    if (!res.ok) {
      throw new Error(`Failed to fetch git status: ${res.statusText}`);
    }
    return res.json();
  }

  async getDiff(options?: GitDiffOptions): Promise<GitDiff> {
    const params = new URLSearchParams();
    if (options?.staged) params.append('staged', 'true');
    if (options?.filePath) params.append('file_path', options.filePath);
    if (options?.commit) params.append('commit', options.commit);

    const query = params.toString() ? `?${params.toString()}` : '';
    const res = await fetch(`${this.baseUrl}/diff${query}`);
    if (!res.ok) {
      throw new Error(`Failed to fetch git diff: ${res.statusText}`);
    }
    return res.json();
  }

  async getLog(options?: GitLogOptions): Promise<GitCommit[]> {
    const params = new URLSearchParams();
    if (options?.maxCount) params.append('max_count', options.maxCount.toString());
    if (options?.filePath) params.append('file_path', options.filePath);

    const query = params.toString() ? `?${params.toString()}` : '';
    const res = await fetch(`${this.baseUrl}/log${query}`);
    if (!res.ok) {
      throw new Error(`Failed to fetch git log: ${res.statusText}`);
    }
    return res.json();
  }

  async getShow(commitOrRef: string = 'HEAD', filePath?: string): Promise<string> {
    const params = new URLSearchParams({ commit: commitOrRef });
    if (filePath) params.append('file_path', filePath);

    const res = await fetch(`${this.baseUrl}/show?${params.toString()}`);
    if (!res.ok) {
      throw new Error(`Failed to fetch git show: ${res.statusText}`);
    }
    const data = await res.json();
    return data.output || '';
  }
}

/**
 * Mock Git API Service simulating backend Git Tool capabilities
 * for decoupled client development and offline verification.
 */
export class MockGitApiService implements IGitApiService {
  private status: GitStatus = {
    branch: 'frontend-workspace',
    isClean: false,
    stagedFiles: [
      'frontend/src/types/gitContract.ts',
      'docs/git_contract.md',
    ],
    unstagedFiles: [
      'src/harness/tools/shell.py',
      'frontend/src/pages/Workspace.tsx',
      'tests/test_shell_tool.py',
    ],
    untrackedFiles: [
      'scratch/temp_diff.patch',
    ],
    changes: [
      {
        file: 'src/harness/tools/shell.py',
        status: 'modified',
        additions: 18,
        deletions: 4,
        diff: `diff --git a/src/harness/tools/shell.py b/src/harness/tools/shell.py
index 4b8291a..c9103e2 100644
--- a/src/harness/tools/shell.py
+++ b/src/harness/tools/shell.py
@@ -45,10 +45,14 @@ class ShellTool:
         self.timeout = timeout
+        self._execution_lock = threading.Lock()
 
     def execute(self, command: str) -> CommandResult:
-        # Run command without concurrency control
-        res = subprocess.run(command, shell=True)
+        # Controlled execution through backend sandbox
+        with self._execution_lock:
+            self._validate_command_safety(command)
+            return self._run_confined(command)
`,
      },
      {
        file: 'frontend/src/pages/Workspace.tsx',
        status: 'modified',
        additions: 12,
        deletions: 2,
        diff: `diff --git a/frontend/src/pages/Workspace.tsx b/frontend/src/pages/Workspace.tsx
index 8912cd3..12f8901 100644
--- a/frontend/src/pages/Workspace.tsx
+++ b/frontend/src/pages/Workspace.tsx
@@ -201,6 +201,10 @@ export const Workspace: React.FC = () => {
               terminalHistory={terminalHistory}
               onRunTerminalCommand={runTerminalCommand}
               onClearTerminal={clearTerminal}
+              gitStatus={gitStatus}
+              onRefreshGit={refreshGit}
+              onSelectGitCommit={selectGitCommit}
               verificationResult={verificationResult}
`,
      },
      {
        file: 'frontend/src/types/gitContract.ts',
        status: 'added',
        additions: 45,
        deletions: 0,
        diff: `diff --git a/frontend/src/types/gitContract.ts b/frontend/src/types/gitContract.ts
new file mode 100644
index 0000000..8a91b2c
--- /dev/null
+++ b/frontend/src/types/gitContract.ts
@@ -0,0 +1,45 @@
+export type GitFileStatus = 'modified' | 'added' | 'deleted' | 'untracked';
+
+export interface GitChange {
+  file: string;
+  status: GitFileStatus;
+  additions: number;
+  deletions: number;
+  diff?: string;
+}
+
+export interface GitStatus {
+  branch: string;
+  isClean: boolean;
+  changes: GitChange[];
+}
`,
      },
      {
        file: 'docs/git_contract.md',
        status: 'added',
        additions: 120,
        deletions: 0,
        diff: `diff --git a/docs/git_contract.md b/docs/git_contract.md
new file mode 100644
index 0000000..7b10214
--- /dev/null
+++ b/docs/git_contract.md
@@ -0,0 +1,120 @@
+# AI Coding Harness — Cross-Platform Git Integration Contract
+
+## Architecture:
+Client -> Git API -> Backend -> Git Tool
+
+Clients MUST NOT execute arbitrary Git commands directly on host machines.
`,
      },
      {
        file: 'src/harness/legacy_runner.py',
        status: 'deleted',
        additions: 0,
        deletions: 34,
        diff: `diff --git a/src/harness/legacy_runner.py b/src/harness/legacy_runner.py
deleted file mode 100644
index e839102..0000000
--- a/src/harness/legacy_runner.py
+++ /dev/null
@@ -1,34 +0,0 @@
-class LegacyRunner:
-    def run(self):
-        pass
`,
      },
      {
        file: 'scratch/temp_diff.patch',
        status: 'untracked',
        additions: 8,
        deletions: 0,
        diff: `diff --git a/scratch/temp_diff.patch b/scratch/temp_diff.patch
new file mode 100644
index 0000000..a9b8c7d
--- /dev/null
+++ b/scratch/temp_diff.patch
@@ -0,0 +1,8 @@
+Temporary experimental patch for review
`,
      },
    ],
    rawOutput: `## frontend-workspace...origin/frontend-workspace
M  src/harness/tools/shell.py
M  frontend/src/pages/Workspace.tsx
A  frontend/src/types/gitContract.ts
A  docs/git_contract.md
D  src/harness/legacy_runner.py
?? scratch/temp_diff.patch`,
  };

  private commits: GitCommit[] = [
    {
      hash: 'cfb818a7b923d81023e1f0293847291a0293841a',
      shortHash: 'cfb818a',
      author: 'AI Harness Agent <agent@harness.ai>',
      date: '2026-09-27 03:05',
      message: 'feat(terminal): implement controlled shell terminal interface and cross-platform contract',
      diff: `commit cfb818a7b923d81023e1f0293847291a0293841a
Author: AI Harness Agent <agent@harness.ai>
Date:   Sat Sep 27 03:05:04 2026 +0530

    feat(terminal): implement controlled shell terminal interface and cross-platform contract

 frontend/src/components/bottom/TerminalView.tsx | 269 ++++++++++++++++++------
 docs/terminal_contract.md                       | 180 ++++++++++++++++
 2 files changed, 449 insertions(+)`,
    },
    {
      hash: '8833c31a72910bcdef0192837461524310293842',
      shortHash: '8833c31',
      author: 'AI Harness Agent <agent@harness.ai>',
      date: '2026-09-27 02:45',
      message: 'feat(attachments): implement cross-platform file attachment and upload system',
      diff: `commit 8833c31a72910bcdef0192837461524310293842
Author: AI Harness Agent <agent@harness.ai>
Date:   Sat Sep 27 02:45:10 2026 +0530

    feat(attachments): implement cross-platform file attachment and upload system

 frontend/src/components/chat/AttachmentList.tsx | 150 ++++++++++++++
 docs/attachment_contract.md                    | 180 ++++++++++++++
 2 files changed, 330 insertions(+)`,
    },
    {
      hash: '64b5840a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e',
      shortHash: '64b5840',
      author: 'AI Harness Agent <agent@harness.ai>',
      date: '2026-09-27 02:15',
      message: 'feat(chat): implement cross-platform AI chat system with markdown, code copy & regeneration',
      diff: `commit 64b5840a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e
Author: AI Harness Agent <agent@harness.ai>
Date:   Sat Sep 27 02:15:22 2026 +0530

    feat(chat): implement cross-platform AI chat system with markdown, code copy & regeneration

 frontend/src/components/chat/ChatPanel.tsx | 280 ++++++++++++++++++++++
 docs/chat_contract.md                      | 210 +++++++++++++++++
 2 files changed, 490 insertions(+)`,
    },
    {
      hash: '561937c98f7e6d5c4b3a20192837465019283746',
      shortHash: '561937c',
      author: 'AI Harness Agent <agent@harness.ai>',
      date: '2026-09-27 01:50',
      message: 'feat(editor): implement monaco code editor, multi-tab state, and file explorer',
      diff: `commit 561937c98f7e6d5c4b3a20192837465019283746
Author: AI Harness Agent <agent@harness.ai>
Date:   Sat Sep 27 01:50:33 2026 +0530

    feat(editor): implement monaco code editor, multi-tab state, and file explorer

 frontend/src/components/editor/EditorContainer.tsx | 195 +++++++++++++++
 frontend/src/components/explorer/FileTree.tsx       | 160 +++++++++++++
 2 files changed, 355 insertions(+)`,
    },
    {
      hash: 'b5a92da019283746501928374650192837465019',
      shortHash: 'b5a92da',
      author: 'AI Harness Agent <agent@harness.ai>',
      date: '2026-09-26 23:30',
      message: 'feat(workspace): build desktop web workspace layout for AI Coding Harness',
      diff: `commit b5a92da019283746501928374650192837465019
Author: AI Harness Agent <agent@harness.ai>
Date:   Sat Sep 26 23:30:15 2026 +0530

    feat(workspace): build desktop web workspace layout for AI Coding Harness

 frontend/src/pages/Workspace.tsx | 259 ++++++++++++++++++++++++++++++
 1 file changed, 259 insertions(+)`,
    },
  ];

  async getStatus(): Promise<GitStatus> {
    // Simulate brief network latency
    await new Promise((resolve) => setTimeout(resolve, 150));
    return JSON.parse(JSON.stringify(this.status));
  }

  async getDiff(options?: GitDiffOptions): Promise<GitDiff> {
    await new Promise((resolve) => setTimeout(resolve, 120));

    if (options?.filePath) {
      const match = this.status.changes.find((c) => c.file === options.filePath);
      if (match) {
        return {
          file: match.file,
          unifiedDiff: match.diff || '',
          staged: !!options.staged,
          additions: match.additions,
          deletions: match.deletions,
        };
      }
    }

    const allDiffs = this.status.changes.map((c) => c.diff).filter(Boolean).join('\n\n');
    const totalAdditions = this.status.changes.reduce((sum, c) => sum + c.additions, 0);
    const totalDeletions = this.status.changes.reduce((sum, c) => sum + c.deletions, 0);

    return {
      unifiedDiff: allDiffs,
      staged: !!options?.staged,
      additions: totalAdditions,
      deletions: totalDeletions,
    };
  }

  async getLog(options?: GitLogOptions): Promise<GitCommit[]> {
    await new Promise((resolve) => setTimeout(resolve, 150));
    const limit = options?.maxCount || 10;
    return this.commits.slice(0, limit);
  }

  async getShow(commitOrRef: string = 'HEAD', filePath?: string): Promise<string> {
    await new Promise((resolve) => setTimeout(resolve, 150));
    const match = this.commits.find(
      (c) => c.hash.startsWith(commitOrRef) || c.shortHash === commitOrRef
    );
    if (match) {
      return match.diff || `Commit ${match.shortHash}: ${match.message}`;
    }
    return `commit ${commitOrRef}\nAuthor: Unknown\n\nNo details available for ref: ${commitOrRef}`;
  }
}

export const gitApi: IGitApiService = USE_MOCK_GIT_API
  ? new MockGitApiService()
  : new GitApiService();
