# AI Coding Harness — Cross-Platform Git Integration Contract

## 1. Architectural Principles

The **Git Integration** feature surfaces the Harness Backend's **Git Tool** (`src/harness/tools/git.py`) to developers. It provides clean, structured visibility into repository changes, file modifications, unified diffs, and commit history.

### The Unified Flow:
```
┌─────────────────────────────────┐   ┌─────────────────────────────────┐   ┌─────────────────────────────────┐
│           Web Client            │   │          macOS Client           │   │         Android Client          │
│        (React / Monaco)         │   │         (SwiftUI Git)           │   │      (Jetpack Compose Git)      │
└────────────────┬────────────────┘   └────────────────┬────────────────┘   └────────────────┬────────────────┘
                 │                                     │                                     │
                 └─────────────────────────────────────┼─────────────────────────────────────┘
                                                       ▼
                                              Git API (REST / JSON)
                                           GET /api/v1/git/status
                                           GET /api/v1/git/diff
                                           GET /api/v1/git/log
                                           GET /api/v1/git/show
                                                       ▼
                                            ┌───────────────────────┐
                                            │  Harness Backend API  │
                                            └───────────┬───────────┘
                                                        ▼
                                            ┌───────────────────────┐
                                            │       Git Tool        │
                                            │(src/harness/tools/    │
                                            │       git.py)         │
                                            └───────────┬───────────┘
                                                        ▼
                                            ┌───────────────────────┐
                                            │ Repository Git Engine │
                                            └───────────────────────┘
```

### Critical Architectural Constraints:
1. **Clients MUST NOT directly execute Git commands**:
   - Web browsers, native macOS apps, and Android clients have zero local shell or git execution permissions.
   - All Git inspections proxy through the Backend Git Tool (`src/harness/tools/git.py`).
2. **Backend Capabilities Exposed**:
   - `git_status`: Branch, clean state, staged files, unstaged files, untracked files.
   - `git_diff`: Unified diffs of staged or unstaged changes, with optional file filtering.
   - `git_log`: Commit history with full hash, short hash, author, date, and commit message.
   - `git_show`: Commit details and file snapshots at specific Git refs.
3. **Single Uniform Contract**:
   - Web, macOS (Swift), and Android (Kotlin) consume identical data structures and endpoints.

---

## 2. Shared Conceptual API Models

```text
GitStatus
GitChange
GitDiff
GitCommit
```

---

## 3. Platform Model Definitions

### A. TypeScript / Web Client

Defined in [`frontend/src/types/gitContract.ts`](file:///Users/arnavjindal2008/Desktop/AI%20Hack/iota-X/frontend/src/types/gitContract.ts):

```typescript
export type GitFileStatus = 'modified' | 'added' | 'deleted' | 'untracked';

export interface GitChange {
  file: string;
  status: GitFileStatus;
  additions: number;
  deletions: number;
  diff?: string;
  staged?: boolean;
  oldPath?: string;
}

export interface GitStatus {
  branch: string;
  isClean: boolean;
  stagedFiles: string[];
  unstagedFiles: string[];
  untrackedFiles: string[];
  changes: GitChange[];
  rawOutput: string;
}

export interface GitDiff {
  file?: string;
  unifiedDiff: string;
  staged: boolean;
  commit?: string;
  additions: number;
  deletions: number;
}

export interface GitCommit {
  hash: string;
  shortHash: string;
  author: string;
  date: string;
  message: string;
  diff?: string;
}

export interface IGitApiService {
  getStatus(): Promise<GitStatus>;
  getDiff(options?: { staged?: boolean; filePath?: string; commit?: string }): Promise<GitDiff>;
  getLog(options?: { maxCount?: number; filePath?: string }): Promise<GitCommit[]>;
  getShow(commitOrRef?: string, filePath?: string): Promise<string>;
}
```

---

### B. Swift / macOS Model (SwiftUI)

Native Swift models conforming to `Codable`, `Identifiable`, and `Sendable`:

```swift
import Foundation

public enum GitFileStatus: String, Codable, Sendable {
    case modified
    case added
    case deleted
    case untracked
}

public struct GitChange: Codable, Identifiable, Sendable {
    public var id: String { file }
    public let file: String
    public let status: GitFileStatus
    public let additions: Int
    public let deletions: Int
    public let diff: String?
    public let staged: Bool?
    public let oldPath: String?
}

public struct GitStatus: Codable, Sendable {
    public let branch: String
    public let isClean: Bool
    public let stagedFiles: [String]
    public let unstagedFiles: [String]
    public let untrackedFiles: [String]
    public let changes: [GitChange]
    public let rawOutput: String
}

public struct GitDiff: Codable, Sendable {
    public let file: String?
    public let unifiedDiff: String
    public let staged: Bool
    public let commit: String?
    public let additions: Int
    public let deletions: Int
}

public struct GitCommit: Codable, Identifiable, Sendable {
    public var id: String { hash }
    public let hash: String
    public let shortHash: String
    public let author: String
    public let date: String
    public let message: String
    public let diff: String?
}

/// Native Swift Service Protocol communicating with Harness Backend
public protocol GitServiceProtocol: Sendable {
    func getStatus() async throws -> GitStatus
    func getDiff(staged: Bool?, filePath: String?, commit: String?) async throws -> GitDiff
    func getLog(maxCount: Int?, filePath: String?) async throws -> [GitCommit]
    func getShow(commitOrRef: String, filePath: String?) async throws -> String
}

public actor GitService: GitServiceProtocol {
    private let baseURL: URL
    private let session: URLSession

    public init(baseURL: URL, session: URLSession = .shared) {
        self.baseURL = baseURL
        self.session = session
    }

    public func getStatus() async throws -> GitStatus {
        let url = baseURL.appendingPathComponent("/api/v1/git/status")
        let (data, response) = try await session.data(from: url)
        guard (response as? HTTPURLResponse)?.statusCode == 200 else {
            throw URLError(.badServerResponse)
        }
        return try JSONDecoder().decode(GitStatus.self, from: data)
    }

    public func getDiff(staged: Bool? = nil, filePath: String? = nil, commit: String? = nil) async throws -> GitDiff {
        var components = URLComponents(url: baseURL.appendingPathComponent("/api/v1/git/diff"), resolvingAgainstBaseURL: true)!
        var queryItems: [URLQueryItem] = []
        if let staged { queryItems.append(URLQueryItem(name: "staged", value: String(staged))) }
        if let filePath { queryItems.append(URLQueryItem(name: "file_path", value: filePath)) }
        if let commit { queryItems.append(URLQueryItem(name: "commit", value: commit)) }
        components.queryItems = queryItems.isEmpty ? nil : queryItems

        let (data, _) = try await session.data(from: components.url!)
        return try JSONDecoder().decode(GitDiff.self, from: data)
    }

    public func getLog(maxCount: Int? = 10, filePath: String? = nil) async throws -> [GitCommit] {
        var components = URLComponents(url: baseURL.appendingPathComponent("/api/v1/git/log"), resolvingAgainstBaseURL: true)!
        var queryItems: [URLQueryItem] = []
        if let maxCount { queryItems.append(URLQueryItem(name: "max_count", value: String(maxCount))) }
        if let filePath { queryItems.append(URLQueryItem(name: "file_path", value: filePath)) }
        components.queryItems = queryItems.isEmpty ? nil : queryItems

        let (data, _) = try await session.data(from: components.url!)
        return try JSONDecoder().decode([GitCommit].self, from: data)
    }

    public func getShow(commitOrRef: String = "HEAD", filePath: String? = nil) async throws -> String {
        var components = URLComponents(url: baseURL.appendingPathComponent("/api/v1/git/show"), resolvingAgainstBaseURL: true)!
        var queryItems = [URLQueryItem(name: "commit", value: commitOrRef)]
        if let filePath { queryItems.append(URLQueryItem(name: "file_path", value: filePath)) }
        components.queryItems = queryItems

        let (data, _) = try await session.data(from: components.url!)
        let dict = try JSONSerialization.jsonObject(with: data) as? [String: Any]
        return dict?["output"] as? String ?? ""
    }
}
```

---

### C. Kotlin / Android Model (Jetpack Compose)

Native Kotlin models utilizing `kotlinx.serialization`:

```kotlin
package com.harness.git.model

import kotlinx.serialization.Serializable
import kotlinx.serialization.SerialName

@Serializable
enum class GitFileStatus {
    @SerialName("modified") MODIFIED,
    @SerialName("added") ADDED,
    @SerialName("deleted") DELETED,
    @SerialName("untracked") UNTRACKED
}

@Serializable
data class GitChange(
    val file: String,
    val status: GitFileStatus,
    val additions: Int = 0,
    val deletions: Int = 0,
    val diff: String? = null,
    val staged: Boolean? = false,
    val oldPath: String? = null
)

@Serializable
data class GitStatus(
    val branch: String,
    val isClean: Boolean,
    val stagedFiles: List<String> = emptyList(),
    val unstagedFiles: List<String> = emptyList(),
    val untrackedFiles: List<String> = emptyList(),
    val changes: List<GitChange> = emptyList(),
    val rawOutput: String = ""
)

@Serializable
data class GitDiff(
    val file: String? = null,
    val unifiedDiff: String = "",
    val staged: Boolean = false,
    val commit: String? = null,
    val additions: Int = 0,
    val deletions: Int = 0
)

@Serializable
data class GitCommit(
    val hash: String,
    val shortHash: String,
    val author: String,
    val date: String,
    val message: String,
    val diff: String? = null
)

// Retrofit API Definition
interface GitApi {
    @GET("/api/v1/git/status")
    suspend fun getStatus(): GitStatus

    @GET("/api/v1/git/diff")
    suspend fun getDiff(
        @Query("staged") staged: Boolean? = null,
        @Query("file_path") filePath: String? = null,
        @Query("commit") commit: String? = null
    ): GitDiff

    @GET("/api/v1/git/log")
    suspend fun getLog(
        @Query("max_count") maxCount: Int? = 10,
        @Query("file_path") filePath: String? = null
    ): List<GitCommit>

    @GET("/api/v1/git/show")
    suspend fun getShow(
        @Query("commit") commitOrRef: String = "HEAD",
        @Query("file_path") filePath: String? = null
    ): Map<String, String>
}
```

---

## 4. Web UI Implementation Overview

Implemented in [`frontend/src/components/bottom/GitDiffView.tsx`](file:///Users/arnavjindal2008/Desktop/AI%20Hack/iota-X/frontend/src/components/bottom/GitDiffView.tsx):
- **Working Tree View**:
  - Filter tabs: `All`, `Modified` (amber badge `M`), `Added` (emerald badge `A`), `Deleted` (rose badge `D`), `Untracked` (purple badge `U`).
  - Additions (`+X`) and Deletions (`-Y`) badges.
  - Interactive file selection with unified diff viewer.
  - Line-by-line syntax styling (emerald additions, rose deletions, sky chunk markers).
  - Copy diff button and "Open in Editor" shortcut.
- **Commit History View**:
  - History list with commit hash, author, relative date, and commit message.
  - On commit selection, runs `git_show` to inspect the full commit unified diff.
- **Live Refresh**:
  - Top bar refresh button synchronizes status and log with the backend.
