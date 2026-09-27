# AI Coding Harness — Cross-Platform Contract & Native Boundaries

## 1. Architectural Overview

The **AI Coding Harness** is designed as a unified, cross-platform autonomous software engineering environment. A single centralized Python backend provides all repository intelligence, AST parsing, inverted indexing, tool execution, and multi-agent orchestration.

Three client interfaces connect to this common backend without duplicating business logic:

```
┌────────────────────────┐   ┌────────────────────────┐   ┌────────────────────────┐
│  Web / Desktop Web     │   │     macOS Client       │   │     Android Client     │
│   (React + TypeScript) │   │   (Native SwiftUI)     │   │ (Kotlin + Compose)     │
└───────────┬────────────┘   └───────────┬────────────┘   └───────────┬────────────┘
            │                            │                            │
            └────────────────────────────┼────────────────────────────┘
                                         ▼
                             ┌────────────────────────┐
                             │   Harness REST / WS    │
                             │        API             │
                             └───────────┬────────────┘
                                         ▼
                             ┌────────────────────────┐
                             │ Python Coding Harness  │
                             │  - Central Orchestrator│
                             │  - Multi-Agent Roles   │
                             │  - Tool Subsystem      │
                             │  - Repo Intelligence   │
                             └────────────────────────┘
```

### Critical Architectural Invariant
> **Do NOT duplicate repository intelligence or AI-agent logic inside the clients.**
> 
> The clients (React Web, macOS SwiftUI, Android Compose) are strictly presentation and interaction layers. All heavy lifting—AST symbol extraction, dependency graph traversal, inverted token indexing, sandboxed execution, and LLM reasoning—remains strictly inside the Python AI Coding Harness.

---

## 2. Shared Conceptual Contract

The contract defines four foundational schemas implemented across all three client languages:

1. **`RepositoryTree`**: Hierarchical representation of the repository's directories and files.
2. **`RepositoryFile`**: Content, encoding, and metadata of a specific file.
3. **`FileChange`**: Mutation payload sent to the backend when saving or creating files.
4. **`EditorState`**: Client session state tracking open tabs, active file, and unsaved changes.

---

### A. TypeScript Definitions (Web Client)

```typescript
// 1. Repository Node & Tree
export type RepositoryNodeType = 'file' | 'directory';

export interface RepositoryNode {
  id: string;
  name: string;
  path: string;
  type: RepositoryNodeType;
  size?: number;
  language?: string;
  lastModified?: string;
  children?: RepositoryNode[];
}

export interface RepositoryTree {
  rootPath: string;
  repositoryName: string;
  branch: string;
  nodes: RepositoryNode[];
  totalFiles: number;
  totalDirectories: number;
}

// 2. Repository File
export interface RepositoryFile {
  id: string;
  path: string;
  name: string;
  content: string;
  language: string;
  size: number;
  encoding: string;
  isReadOnly?: boolean;
  lineCount?: number;
  lastModified?: string;
}

// 3. File Change Payload
export type FileChangeType = 'edit' | 'create' | 'delete';

export interface FileChange {
  path: string;
  content: string;
  originalContent?: string;
  changeType: FileChangeType;
  timestamp: string;
}

// 4. Editor Session State
export interface EditorState {
  openFiles: RepositoryFile[];
  activeFilePath: string | null;
  modifiedFilePaths: string[];
  cursorPosition?: { line: number; column: number };
  isReadOnly?: boolean;
}
```

---

### B. Swift Native Definitions (macOS Client)

```swift
import Foundation

// MARK: - 1. Repository Node & Tree
public enum RepositoryNodeType: String, Codable, Sendable {
    case file
    case directory
}

public struct RepositoryNode: Codable, Identifiable, Sendable {
    public var id: String { path }
    public let name: String
    public let path: String
    public let type: RepositoryNodeType
    public let size: Int?
    public let language: String?
    public let lastModified: String?
    public let children: [RepositoryNode]?
}

public struct RepositoryTree: Codable, Sendable {
    public let rootPath: String
    public let repositoryName: String
    public let branch: String
    public let nodes: [RepositoryNode]
    public let totalFiles: Int
    public let totalDirectories: Int
}

// MARK: - 2. Repository File
public struct RepositoryFile: Codable, Identifiable, Sendable {
    public var id: String { path }
    public let path: String
    public let name: String
    public var content: String
    public let language: String
    public let size: Int
    public let encoding: String
    public let isReadOnly: Bool?
    public let lineCount: Int?
    public let lastModified: String?
}

// MARK: - 3. File Change Payload
public enum FileChangeType: String, Codable, Sendable {
    case edit
    case create
    case delete
}

public struct FileChange: Codable, Sendable {
    public let path: String
    public let content: String
    public let originalContent: String?
    public let changeType: FileChangeType
    public let timestamp: String
}

// MARK: - 4. Editor Session State
@Observable
public final class EditorState {
    public var openFiles: [RepositoryFile] = []
    public var activeFilePath: String? = nil
    public var modifiedFilePaths: Set<String> = []
    public var isReadOnly: Bool = false
    
    public var activeFile: RepositoryFile? {
        guard let path = activeFilePath else { return nil }
        return openFiles.first(where: { $0.path == path })
    }
}
```

---

### C. Kotlin Native Definitions (Android Client)

```kotlin
package ai.codingharness.client.model

import kotlinx.serialization.Serializable

// 1. Repository Node & Tree
@Serializable
enum class RepositoryNodeType {
    file, directory
}

@Serializable
data class RepositoryNode(
    val id: String,
    val name: String,
    val path: String,
    val type: RepositoryNodeType,
    val size: Long? = null,
    val language: String? = null,
    val lastModified: String? = null,
    val children: List<RepositoryNode>? = null
)

@Serializable
data class RepositoryTree(
    val rootPath: String,
    val repositoryName: String,
    val branch: String,
    val nodes: List<RepositoryNode>,
    val totalFiles: Int,
    val totalDirectories: Int
)

// 2. Repository File
@Serializable
data class RepositoryFile(
    val id: String,
    val path: String,
    val name: String,
    val content: String,
    val language: String,
    val size: Long,
    val encoding: String = "utf-8",
    val isReadOnly: Boolean = false,
    val lineCount: Int? = null,
    val lastModified: String? = null
)

// 3. File Change Payload
@Serializable
enum class FileChangeType {
    edit, create, delete
}

@Serializable
data class FileChange(
    val path: String,
    val content: String,
    val originalContent: String? = null,
    val changeType: FileChangeType = FileChangeType.edit,
    val timestamp: String
)

// 4. Editor Session State
data class EditorState(
    val openFiles: List<RepositoryFile> = emptyList(),
    val activeFilePath: String? = null,
    val modifiedFilePaths: Set<String> = emptySet(),
    val isReadOnly: Boolean = false
) {
    val activeFile: RepositoryFile?
        get() = openFiles.find { it.path == activeFilePath }
}
```

---

## 3. macOS Native Implementation Boundary

The macOS application will be built as a native SwiftUI desktop app targeting macOS 14+ (Sonoma) / macOS 15+ (Sequoia).

### Implementation Flow:
```
SwiftUI View Hierarchy
│  ├── NavigationSplitView (Sidebar: OutlineGroup file tree)
│  ├── Detail Area (Native Tab Bar + Native Code Editor)
│  └── Inspector (AI Assistant chat panel)
│
▼
HarnessAPIClient (URLSession / Swift Concurrency async/await)
│  ├── fetchRepositoryTree() -> RepositoryTree
│  ├── fetchFile(path) -> RepositoryFile
│  ├── saveFile(FileChange) -> RepositoryFile
│  └── streamAgentChat(prompt) -> AsyncThrowingStream<AgentEvent, Error>
│
▼
Harness API Service (HTTP/JSON + WebSocket)
│
▼
Python Backend Harness
```

### Boundary Guarantees:
1. **Native Editor UI**: The macOS client will use a native text rendering engine (e.g. `NSTextView`, `TextEditor`, or Swift-native syntax highlighters such as `Sourceful` or `Highlightr`).
2. **Zero Sandboxing Conflicts**: Browser security limitations do not apply; however, the client **must still delegate file mutations to the Harness API** rather than writing directly to local disk, guaranteeing that backend file watchers, indexers, and git tracking remain synchronized.
3. **No Redundant Parsers**: AST parsing (Python `ast`, `libcst`) and symbol graphs remain 100% on the server.

---

## 4. Android Native Implementation Boundary

The Android application will be built using Jetpack Compose and Kotlin Coroutines.

### Implementation Flow:
```
Jetpack Compose Hierarchy
│  ├── Scaffold (TopAppBar with active branch & status)
│  ├── ModalNavigationDrawer / BottomSheet (File Explorer tree)
│  ├── Main Content (Multi-tab Pager + BasicTextField code editor)
│  └── BottomSheet / Floating Action (AI Chat & Verification results)
│
▼
HarnessRepository (Ktor / Retrofit + Kotlinx Serialization)
│  ├── getTree(): Flow<RepositoryTree>
│  ├── getFile(path): RepositoryFile
│  ├── saveFile(change): Result<RepositoryFile>
│  └── observeAgentEvents(): Flow<AgentEvent>
│
▼
Harness API Service
│
▼
Python Backend Harness
```

### Boundary Guarantees:
1. **Lightweight Mobile Footprint**: Mobile devices do not need to run Python runtime or heavy AST indexing.
2. **Network Resilience**: Ktor client handles offline caching, reconnection, and token-based authentication.
3. **Consistent State**: All modifications route through the same `FileChange` contract, ensuring Web, macOS, and Android users experience identical repository states.
