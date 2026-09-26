# AI Coding Harness — Git Integration & Cross-Platform Contract

## 1. Architectural Overview

The **AI Coding Harness** provides a centralized Git integration subsystem. The Git tools are owned and executed exclusively on the Python backend to ensure safety, state consistency, and centralized security.

Three client platforms connect to this common Git interface without directly executing shell or git commands:

```
┌────────────────────────┐   ┌────────────────────────┐   ┌────────────────────────┐
│  Web / Desktop Web     │   │     macOS Client       │   │     Android Client     │
│   (React + TypeScript) │   │   (Native SwiftUI)     │   │ (Kotlin + Compose)     │
└───────────┬────────────┘   └───────────┬────────────┘   └───────────┬────────────┘
            │                            │                            │
            └────────────────────────────┼────────────────────────────┘
                                         ▼
                             ┌────────────────────────┐
                             │       Git API          │
                             │  - /api/git/status     │
                             │  - /api/git/diff       │
                             │  - /api/git/log        │
                             │  - /api/git/show       │
                             └───────────┬────────────┘
                                         ▼
                             ┌────────────────────────┐
                             │     Harness Backend    │
                             └───────────┬────────────┘
                                         ▼
                             ┌────────────────────────┐
                             │        Git Tool        │
                             │   (src/harness/tools)  │
                             └────────────────────────┘
```

### Critical Architectural Invariant
> **The clients must NOT directly execute Git commands.**
>
> All Git actions must route through the Git API into the backend `GitTool`. The backend encapsulates repository inspection, diff parsing, history pagination, and sandboxed execution.

---

## 2. Backend Capabilities

The backend exposes four core Git inspection capabilities:

| Capability | Parameters | Description |
|---|---|---|
| `git_status` | *(none)* | Inspects working tree: current branch, staged, unstaged, untracked files, and ahead/behind counts. |
| `git_diff` | `staged: bool = False`, `file_path: Optional[str]`, `commit: Optional[str]` | Generates unified diff of changes with line additions and deletions stats. |
| `git_log` | `max_count: int = 10`, `file_path: Optional[str]` | Retrieves recent commit history with author, date, subject, and hashes. |
| `git_show` | `commit_or_ref: str = "HEAD"`, `file_path: Optional[str]` | Returns full details of a specific commit or file at that ref. |

---

## 3. Shared Conceptual Models

The contract defines four core data models:

1. **`GitChange`**: Represents a single file modification (modified, added, deleted, or untracked).
2. **`GitStatus`**: Complete snapshot of repository working tree, branch, and active changes.
3. **`GitDiff`**: Unified diff representation containing hunk headers, line statistics, and change details.
4. **`GitCommit`**: Commit history entry with author, timestamp, hash, and commit message.

---

## 4. Cross-Platform Language Implementations

### A. TypeScript Definitions (Web Client)

```typescript
export type GitChangeStatus = 'modified' | 'added' | 'deleted' | 'untracked';

export interface GitChange {
  file: string;
  status: GitChangeStatus;
  staged: boolean;
  additions: number;
  deletions: number;
  oldPath?: string;
  diff?: string;
}

export interface GitStatus {
  branch: string;
  isClean: boolean;
  changes: GitChange[];
  stagedFiles: string[];
  unstagedFiles: string[];
  untrackedFiles: string[];
  ahead: number;
  behind: number;
  rawOutput?: string;
}

export interface GitDiff {
  filePath?: string;
  staged: boolean;
  commit?: string;
  diffText: string;
  additions: number;
  deletions: number;
  changes?: GitChange[];
}

export interface GitCommit {
  hash: string;
  shortHash: string;
  author: string;
  date: string;
  message: string;
  parentHashes?: string[];
}
```

---

### B. Swift Definitions (macOS Native Client)

```swift
import Foundation

public enum GitChangeStatus: String, Codable, Sendable {
    case modified = "modified"
    case added = "added"
    case deleted = "deleted"
    case untracked = "untracked"
}

public struct GitChange: Codable, Identifiable, Sendable {
    public var id: String { file }
    public let file: String
    public let status: GitChangeStatus
    public let staged: Bool
    public let additions: Int
    public let deletions: Int
    public let oldPath: String?
    public let diff: String?

    public init(
        file: String,
        status: GitChangeStatus,
        staged: Bool = false,
        additions: Int = 0,
        deletions: Int = 0,
        oldPath: String? = nil,
        diff: String? = nil
    ) {
        self.file = file
        self.status = status
        self.staged = staged
        self.additions = additions
        self.deletions = deletions
        self.oldPath = oldPath
        self.diff = diff
    }
}

public struct GitStatus: Codable, Sendable {
    public let branch: String
    public let isClean: Bool
    public let changes: [GitChange]
    public let stagedFiles: [String]
    public let unstagedFiles: [String]
    public let untrackedFiles: [String]
    public let ahead: Int
    public let behind: Int
    public let rawOutput: String?

    public var addedFiles: [GitChange] {
        changes.filter { $0.status == .added }
    }
    public var modifiedFiles: [GitChange] {
        changes.filter { $0.status == .modified }
    }
    public var deletedFiles: [GitChange] {
        changes.filter { $0.status == .deleted }
    }
    public var untrackedChanges: [GitChange] {
        changes.filter { $0.status == .untracked }
    }
}

public struct GitDiff: Codable, Sendable {
    public let filePath: String?
    public let staged: Bool
    public let commit: String?
    public let diffText: String
    public let additions: Int
    public let deletions: Int
    public let changes: [GitChange]?
}

public struct GitCommit: Codable, Identifiable, Sendable {
    public var id: String { hash }
    public let hash: String
    public let shortHash: String
    public let author: String
    public let date: String
    public let message: String
    public let parentHashes: [String]?
}
```

---

### C. Kotlin Definitions (Android Client)

```kotlin
package com.harness.git.contract

import kotlinx.serialization.Serializable

@Serializable
enum class GitChangeStatus {
    MODIFIED,
    ADDED,
    DELETED,
    UNTRACKED
}

@Serializable
data class GitChange(
    val file: String,
    val status: GitChangeStatus,
    val staged: Boolean = false,
    val additions: Int = 0,
    val deletions: Int = 0,
    val oldPath: String? = null,
    val diff: String? = null
)

@Serializable
data class GitStatus(
    val branch: String,
    val isClean: Boolean,
    val changes: List<GitChange> = emptyList(),
    val stagedFiles: List<String> = emptyList(),
    val unstagedFiles: List<String> = emptyList(),
    val untrackedFiles: List<String> = emptyList(),
    val ahead: Int = 0,
    val behind: Int = 0,
    val rawOutput: String? = null
) {
    val addedFiles: List<GitChange>
        get() = changes.filter { it.status == GitChangeStatus.ADDED }

    val modifiedFiles: List<GitChange>
        get() = changes.filter { it.status == GitChangeStatus.MODIFIED }

    val deletedFiles: List<GitChange>
        get() = changes.filter { it.status == GitChangeStatus.DELETED }

    val untrackedChanges: List<GitChange>
        get() = changes.filter { it.status == GitChangeStatus.UNTRACKED }
}

@Serializable
data class GitDiff(
    val filePath: String? = null,
    val staged: Boolean = false,
    val commit: String? = null,
    val diffText: String = "",
    val additions: Int = 0,
    val deletions: Int = 0,
    val changes: List<GitChange> = emptyList()
)

@Serializable
data class GitCommit(
    val hash: String,
    val shortHash: String,
    val author: String,
    val date: String,
    val message: String,
    val parentHashes: List<String> = emptyList()
)
```

---

## 5. Web UI Requirements

The web application provides:

1. **Category Breakdown**:
   - Total changed files count & additions/deletions stats (+N -M)
   - Added files (`A` badge / green)
   - Deleted files (`D` badge / red)
   - Modified files (`M` badge / amber)
   - Untracked files (`U` badge / gray)
2. **Unified Diff Viewer**:
   - Line numbers and change indicator (`+`, `-`, `@@`)
   - Syntax-highlighted additions (green tint) and deletions (red tint)
   - Quick action: "Open in Editor"
3. **Commit History**:
   - Paginated commit log with message, author, short hash, and date
   - Commit detail inspector (`git_show`) with one-click view
4. **Interactive Actions**:
   - Refresh button (`RotateCw`) with live spinning feedback
   - Filter by file or view mode (Working Changes vs Commit History)
