# AI Coding Harness — Cross-Platform Controlled Terminal Contract

## 1. Architectural Principles

The **Terminal Interface** represents the Harness Backend's **Controlled Shell Tool** (`src/harness/tools/shell.py`). It enables engineers to inspect command output, run verification suites (e.g. `pytest`), check Git status, and inspect execution results inside the repository environment.

### The Unified Execution Architecture:
```
┌─────────────────────────────────┐   ┌─────────────────────────────────┐   ┌─────────────────────────────────┐
│           Web Client            │   │          macOS Client           │   │         Android Client          │
│        (React / Monaco)         │   │       (SwiftUI Terminal)        │   │    (Jetpack Compose Console)    │
└────────────────┬────────────────┘   └────────────────┬────────────────┘   └────────────────┬────────────────┘
                 │                                     │                                     │
                 └─────────────────────────────────────┼─────────────────────────────────────┘
                                                       ▼
                                            POST /api/v1/terminal/execute
                                          (or cancel: POST /api/v1/terminal/cancel)
                                                       ▼
                                            ┌───────────────────────┐
                                            │  Harness Backend API  │
                                            └───────────┬───────────┘
                                                        ▼
                                            ┌───────────────────────┐
                                            │ Controlled Shell Tool │
                                            │(src/harness/tools/    │
                                            │       shell.py)       │
                                            └───────────┬───────────┘
                                                        ▼
                                            ┌───────────────────────┐
                                            │ Sandboxed Repository  │
                                            │ (Subprocess / Sandbox)│
                                            └───────────────────────┘
```

### Critical Security & Architecture Constraints:
1. **Clients MUST NOT execute arbitrary shell commands themselves**:
   - The browser environment, macOS native app, and Android app have zero local host execution authority.
   - All commands pass through the backend's `Controlled Shell Tool`.
2. **Backend Defense-in-Depth (`src/harness/tools/shell.py`)**:
   - The backend validates commands against a dangerous command blocklist (e.g., fork bombs `:{}:`, destructive root deletes `rm -rf /`, raw disk manipulation `mkfs`, `/dev/sd*`).
   - Commands are confined within the repository's root directory (`cwd`).
   - Commands run with strict timeout limits (default 60s, configurable) to prevent hanging processes.
   - Stdout and stderr streams are captured cleanly, truncated if exceeding buffer limits, and returned with precise exit codes and execution durations.
3. **Identical Contract Across Platforms**:
   - Web, macOS (Swift), and Android (Kotlin) invoke the identical REST / WebSocket API.
   - UI presentations differ to fit native conventions, but model schemas are 100% equivalent.

---

## 2. Shared Conceptual API Models

The shared contract defines three core models:

```text
CommandRequest
CommandResult
TerminalOutput
```

### Display Specifications:
Every client MUST render:
* **command** (e.g., `$ pytest`)
* **stdout** (standard text stream output)
* **stderr** (error text stream, visually distinguished)
* **exit code** (e.g., `Process exited with code 0`)
* **duration** (elapsed time, e.g. `0.85s`)
* **running state** (active spinner, `RUNNING` badge, cancel button)
* **success/failure** (`SUCCESS` with green accent, `FAILED` with red accent)

#### Canonical Example:
```text
$ pytest

42 passed
0 failed

Process exited with code 0
```

---

## 3. Platform Implementations

### A. TypeScript / Web Model

Defined in [`frontend/src/types/terminalContract.ts`](file:///Users/arnavjindal2008/Desktop/AI%20Hack/iota-X/frontend/src/types/terminalContract.ts):

```typescript
export type CommandStatus = 'running' | 'success' | 'failure' | 'cancelled' | 'timeout';

export interface CommandRequest {
  command: string;
  workingDirectory?: string;
  timeoutSeconds?: number;
  environment?: Record<string, string>;
  sessionId?: string;
}

export interface CommandResult {
  id: string;
  command: string;
  stdout: string;
  stderr: string;
  exitCode: number | null;
  durationSeconds: number;
  status: CommandStatus;
  timedOut?: boolean;
  timestamp: string;
}

export interface TerminalOutput {
  id: string;
  command: string;
  stdout: string;
  stderr: string;
  exitCode: number | null;
  durationSeconds: number;
  status: CommandStatus;
  timestamp: string;
  cwd?: string;
}

export interface ITerminalApiService {
  executeCommand(request: CommandRequest): Promise<CommandResult>;
  cancelCommand(commandId: string): Promise<boolean>;
  getHistory(sessionId?: string): Promise<TerminalOutput[]>;
  clearHistory(sessionId?: string): Promise<void>;
}
```

---

### B. Swift / macOS Model (SwiftUI)

Native Swift representation conforming to `Codable`, `Identifiable`, and `Sendable`:

```swift
import Foundation

public enum CommandStatus: String, Codable, Sendable {
    case running
    case success
    case failure
    case cancelled
    case timeout
}

public struct CommandRequest: Codable, Sendable {
    public let command: String
    public let workingDirectory: String?
    public let timeoutSeconds: Double?
    public let environment: [String: String]?
    public let sessionId: String?

    public init(
        command: String,
        workingDirectory: String? = nil,
        timeoutSeconds: Double? = 60.0,
        environment: [String: String]? = nil,
        sessionId: String? = nil
    ) {
        self.command = command
        self.workingDirectory = workingDirectory
        self.timeoutSeconds = timeoutSeconds
        self.environment = environment
        self.sessionId = sessionId
    }
}

public struct CommandResult: Codable, Identifiable, Sendable {
    public let id: String
    public let command: String
    public let stdout: String
    public let stderr: String
    public let exitCode: Int?
    public let durationSeconds: Double
    public let status: CommandStatus
    public let timedOut: Bool?
    public let timestamp: String

    public var isSuccess: Bool {
        return exitCode == 0 && status == .success
    }
}

public struct TerminalOutput: Codable, Identifiable, Sendable {
    public let id: String
    public let command: String
    public let stdout: String
    public let stderr: String
    public let exitCode: Int?
    public let durationSeconds: Double
    public let status: CommandStatus
    public let timestamp: String
    public let cwd: String?
}

/// Native Swift Service Protocol communicating exclusively with backend API
public protocol TerminalServiceProtocol: Sendable {
    func executeCommand(_ request: CommandRequest) async throws -> CommandResult
    func cancelCommand(id: String) async throws -> Bool
    func fetchHistory(sessionId: String?) async throws -> [TerminalOutput]
}

public actor TerminalService: TerminalServiceProtocol {
    private let baseURL: URL
    private let session: URLSession

    public init(baseURL: URL, session: URLSession = .shared) {
        self.baseURL = baseURL
        self.session = session
    }

    public func executeCommand(_ request: CommandRequest) async throws -> CommandResult {
        var urlRequest = URLRequest(url: baseURL.appendingPathComponent("/api/v1/terminal/execute"))
        urlRequest.httpMethod = "POST"
        urlRequest.setValue("application/json", forHTTPHeaderField: "Content-Type")
        urlRequest.httpBody = try JSONEncoder().encode(request)

        let (data, response) = try await session.data(for: urlRequest)
        guard let httpResponse = response as? HTTPURLResponse, (200...299).contains(httpResponse.statusCode) else {
            throw URLError(.badServerResponse)
        }
        return try JSONDecoder().decode(CommandResult.self, from: data)
    }

    public func cancelCommand(id: String) async throws -> Bool {
        var urlRequest = URLRequest(url: baseURL.appendingPathComponent("/api/v1/terminal/cancel"))
        urlRequest.httpMethod = "POST"
        urlRequest.setValue("application/json", forHTTPHeaderField: "Content-Type")
        urlRequest.httpBody = try JSONSerialization.data(withJSONObject: ["id": id])
        let (_, response) = try await session.data(for: urlRequest)
        return (response as? HTTPURLResponse)?.statusCode == 200
    }

    public func fetchHistory(sessionId: String? = nil) async throws -> [TerminalOutput] {
        var url = baseURL.appendingPathComponent("/api/v1/terminal/history")
        if let sessionId {
            url.append(queryItems: [URLQueryItem(name: "sessionId", value: sessionId)])
        }
        let (data, _) = try await session.data(from: url)
        return try JSONDecoder().decode([TerminalOutput].self, from: data)
    }
}
```

---

### C. Kotlin / Android Model (Jetpack Compose)

Native Kotlin model utilizing `kotlinx.serialization`:

```kotlin
package com.harness.terminal.model

import kotlinx.serialization.Serializable
import kotlinx.serialization.SerialName

@Serializable
enum class CommandStatus {
    @SerialName("running") RUNNING,
    @SerialName("success") SUCCESS,
    @SerialName("failure") FAILURE,
    @SerialName("cancelled") CANCELLED,
    @SerialName("timeout") TIMEOUT
}

@Serializable
data class CommandRequest(
    val command: String,
    val workingDirectory: String? = null,
    val timeoutSeconds: Double? = 60.0,
    val environment: Map<String, String>? = null,
    val sessionId: String? = null
)

@Serializable
data class CommandResult(
    val id: String,
    val command: String,
    val stdout: String = "",
    val stderr: String = "",
    val exitCode: Int? = null,
    val durationSeconds: Double = 0.0,
    val status: CommandStatus = CommandStatus.SUCCESS,
    val timedOut: Boolean? = false,
    val timestamp: String
) {
    val isSuccess: Boolean get() = exitCode == 0 && status == CommandStatus.SUCCESS
}

@Serializable
data class TerminalOutput(
    val id: String,
    val command: String,
    val stdout: String = "",
    val stderr: String = "",
    val exitCode: Int? = null,
    val durationSeconds: Double = 0.0,
    val status: CommandStatus,
    val timestamp: String,
    val cwd: String? = null
)

// Retrofit API Definition
interface TerminalApi {
    @POST("/api/v1/terminal/execute")
    suspend fun executeCommand(@Body request: CommandRequest): CommandResult

    @POST("/api/v1/terminal/cancel")
    suspend fun cancelCommand(@Body payload: Map<String, String>): Boolean

    @GET("/api/v1/terminal/history")
    suspend fun getHistory(@Query("sessionId") sessionId: String?): List<TerminalOutput>
}
```

---

## 4. Web Client Implementation

The React Web client UI has been fully implemented with:

1. **Terminal View (`TerminalView.tsx`)**:
   - Monospace font styling mimicking high-end terminal emulators.
   - Command header with `$ <command>`, duration badge, timestamp, and status pill.
   - Standard output display formatted with proper terminal whitespace.
   - Standard error highlighted in structured rose alert box.
   - Process termination indicator: `Process exited with code 0` (or non-zero).
   - Copy output button with instant feedback.
   - Interactive prompt with history cycling (`ArrowUp` / `ArrowDown`).
   - Quick command shortcuts (`pytest`, `git status`, `git diff`, `python -m harness.main`).
   - Active command execution spinner with `Stop` button for cancellation.

2. **Decoupled Mock Service (`frontend/src/services/terminalApi.ts`)**:
   - `MockTerminalApiService` enforces client-side safety simulation matching the Python backend blocklist.
   - Provides realistic test suite simulations for `pytest` (42 passed, 0 failed), `git status`, and custom commands.
   - Easy toggle to point to live `TerminalApiService` when backend endpoints are ready.
