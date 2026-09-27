# AI Coding Harness — Cross-Platform Agent Activity & Event Stream Contract

## 1. Architectural Principles

The **Agent Activity System** surfaces the core autonomous execution loop of the **AI Coding Harness** to developers. It displays live multi-agent reasoning, repository intelligence, code modifications, test executions, and autonomous failure-recovery loops (1/3, 2/3, 3/3).

### The Unified Streaming Architecture:
```
┌─────────────────────────────────┐   ┌─────────────────────────────────┐   ┌─────────────────────────────────┐
│           Web Client            │   │          macOS Client           │   │         Android Client          │
│     (useAgentWorkflow Hook)     │   │      (SwiftUI AsyncStream)      │   │    (Jetpack Compose Flow)       │
└────────────────┬────────────────┘   └────────────────┬────────────────┘   └────────────────┬────────────────┘
                 │                                     │                                     │
                 └─────────────────────────────────────┼─────────────────────────────────────┘
                                                       ▼
                                            Agent Event Stream Layer
                                     (Pluggable: Polling / SSE / WebSocket)
                                                       ▼
                                            ┌───────────────────────┐
                                            │  Harness Backend API  │
                                            └───────────┬───────────┘
                                                        ▼
                                            ┌───────────────────────┐
                                            │     Orchestrator      │
                                            │(src/harness/          │
                                            │ orchestrator/state.py)│
                                            └───────────┬───────────┘
                                                        ▼
                         ┌──────────────┬───────────────┴──────────────┬──────────────┐
                         ▼              ▼                              ▼              ▼
                  PlannerAgent   ResearchAgent                    CoderAgent    RecoveryAgent
```

### Critical Architectural Constraints:
1. **Zero Client-Side Agent Execution**:
   - Web, macOS (Swift), and Android clients have no local agent logic.
   - The backend Orchestrator coordinates multi-agent lifecycle transitions and emits structured telemetry events.
2. **Pluggable Transport Abstraction**:
   - The client UI interfaces strictly with `IAgentEventStream`.
   - Transports can be swapped between **HTTP Polling**, **Server-Sent Events (SSE)**, or **WebSockets** without rewriting any UI components.
   - WebSockets are defined architecturally but remain inactive until backend socket endpoints are ready.
3. **Identical Contract Across Platforms**:
   - Web, macOS (Swift), and Android (Kotlin) consume identical event formats and data schemas.

---

## 2. Shared Conceptual API Models

```text
AgentTask
AgentStep
AgentStatus
AgentEvent
```

---

## 3. Autonomous Execution Lifecycles

### A. Standard Execution Flow
```text
✓ Task received
✓ Planning
✓ Repository research
✓ Relevant files found
● Inspecting code
○ Editing
○ Running tests
○ Verification
```

### B. Failure & Self-Healing Recovery Loop
When tests fail or assertions trigger regressions, the orchestrator initiates a bounded recovery loop (up to 3 attempts):
```text
✗ Tests failed
→ Failure analysis
→ Recovery attempt 1/3
→ Correction
→ Testing again
✓ Verification (all 67 tests passing)
✓ Task completed
```

---

## 4. Platform Model Definitions

### A. TypeScript / Web Client

Defined in [`frontend/src/types/agentContract.ts`](file:///Users/arnavjindal2008/Desktop/AI%20Hack/iota-X/frontend/src/types/agentContract.ts):

```typescript
export type AgentStatus =
  | 'idle'
  | 'task_received'
  | 'planning'
  | 'researching'
  | 'files_found'
  | 'inspecting'
  | 'editing'
  | 'testing'
  | 'failed'
  | 'failure_analysis'
  | 'recovering'
  | 'verifying'
  | 'completed';

export type AgentStepStatus =
  | 'pending'
  | 'in_progress'
  | 'completed'
  | 'failed'
  | 'recovering'
  | 'skipped';

export interface AgentStep {
  id: string;
  title: string;
  status: AgentStepStatus;
  agentName?: string;
  startedAt?: string;
  completedAt?: string;
  durationSeconds?: number;
  details?: string;
  subSteps?: string[];
  error?: string;
  recoveryAttempt?: number;
  maxRecoveryAttempts?: number;
  relevantFiles?: string[];
}

export interface AgentTask {
  id: string;
  title: string;
  description?: string;
  status: AgentStatus;
  createdAt: string;
  completedAt?: string;
  currentStepIndex: number;
  totalSteps: number;
  recoveryAttempt: number;
  maxRecoveryAttempts: number;
  steps: AgentStep[];
  relevantFiles: string[];
  errors: string[];
  iteration: number;
  maxIterations: number;
}

export interface AgentEvent {
  id: string;
  taskId?: string;
  type: AgentEventType;
  status?: AgentStatus;
  agentRole?: string;
  stepId?: string;
  title: string;
  details?: string;
  timestamp: string;
  stepIndex?: number;
  recoveryAttempt?: number;
  maxRecoveryAttempts?: number;
  relevantFiles?: string[];
  payload?: Record<string, any>;
}

export type StreamTransportType = 'polling' | 'sse' | 'websocket' | 'mock';

export interface IAgentEventStream {
  readonly transport: StreamTransportType;
  subscribe(
    taskId: string,
    onEvent: (event: AgentEvent) => void,
    onError?: (err: Error) => void
  ): () => void;
  getTask(taskId: string): Promise<AgentTask>;
  getSteps(taskId: string): Promise<AgentStep[]>;
}
```

---

### B. Swift / macOS Model (SwiftUI)

Native Swift representations conforming to `Codable`, `Identifiable`, and `Sendable`:

```swift
import Foundation

public enum AgentStatus: String, Codable, Sendable {
    case idle
    case taskReceived = "task_received"
    case planning
    case researching
    case filesFound = "files_found"
    case inspecting
    case editing
    case testing
    case failed
    case failureAnalysis = "failure_analysis"
    case recovering
    case verifying
    case completed
}

public enum AgentStepStatus: String, Codable, Sendable {
    case pending
    case inProgress = "in_progress"
    case completed
    case failed
    case recovering
    case skipped
}

public struct AgentStep: Codable, Identifiable, Sendable {
    public let id: String
    public let title: String
    public let status: AgentStepStatus
    public let agentName: String?
    public let durationSeconds: Double?
    public let details: String?
    public let subSteps: [String]?
    public let error: String?
    public let recoveryAttempt: Int?
    public let maxRecoveryAttempts: Int?
    public let relevantFiles: [String]?
}

public struct AgentTask: Codable, Identifiable, Sendable {
    public let id: String
    public let title: String
    public let description: String?
    public let status: AgentStatus
    public let createdAt: String
    public let currentStepIndex: Int
    public let totalSteps: Int
    public let recoveryAttempt: Int
    public let maxRecoveryAttempts: Int
    public let steps: [AgentStep]
    public let relevantFiles: [String]
    public let errors: [String]
}

public struct AgentEvent: Codable, Identifiable, Sendable {
    public let id: String
    public let taskId: String?
    public let type: String
    public let status: AgentStatus?
    public let agentRole: String?
    public let stepId: String?
    public let title: String
    public let details: String?
    public let timestamp: String
    public let recoveryAttempt: Int?
    public let maxRecoveryAttempts: Int?
    public let relevantFiles: [String]?
}

/// Swift Asynchronous Event Stream Protocol
public protocol AgentStreamProtocol: Sendable {
    func eventStream(for taskId: String) -> AsyncThrowingStream<AgentEvent, Error>
    func fetchTask(taskId: String) async throws -> AgentTask
}
```

---

### C. Kotlin / Android Model (Jetpack Compose)

Native Kotlin models utilizing `kotlinx.serialization` and Kotlin Coroutines `Flow`:

```kotlin
package com.harness.agent.model

import kotlinx.serialization.Serializable
import kotlinx.serialization.SerialName
import kotlinx.coroutines.flow.Flow

@Serializable
enum class AgentStatus {
    @SerialName("idle") IDLE,
    @SerialName("task_received") TASK_RECEIVED,
    @SerialName("planning") PLANNING,
    @SerialName("researching") RESEARCHING,
    @SerialName("files_found") FILES_FOUND,
    @SerialName("inspecting") INSPECTING,
    @SerialName("editing") EDITING,
    @SerialName("testing") TESTING,
    @SerialName("failed") FAILED,
    @SerialName("failure_analysis") FAILURE_ANALYSIS,
    @SerialName("recovering") RECOVERING,
    @SerialName("verifying") VERIFYING,
    @SerialName("completed") COMPLETED
}

@Serializable
enum class AgentStepStatus {
    @SerialName("pending") PENDING,
    @SerialName("in_progress") IN_PROGRESS,
    @SerialName("completed") COMPLETED,
    @SerialName("failed") FAILED,
    @SerialName("recovering") RECOVERING,
    @SerialName("skipped") SKIPPED
}

@Serializable
data class AgentStep(
    val id: String,
    val title: String,
    val status: AgentStepStatus,
    val agentName: String? = null,
    val durationSeconds: Double? = null,
    val details: String? = null,
    val subSteps: List<String> = emptyList(),
    val error: String? = null,
    val recoveryAttempt: Int? = null,
    val maxRecoveryAttempts: Int? = null,
    val relevantFiles: List<String> = emptyList()
)

@Serializable
data class AgentTask(
    val id: String,
    val title: String,
    val description: String? = null,
    val status: AgentStatus,
    val createdAt: String,
    val currentStepIndex: Int = 0,
    val totalSteps: Int = 8,
    val recoveryAttempt: Int = 0,
    val maxRecoveryAttempts: Int = 3,
    val steps: List<AgentStep> = emptyList(),
    val relevantFiles: List<String> = emptyList(),
    val errors: List<String> = emptyList()
)

@Serializable
data class AgentEvent(
    val id: String,
    val taskId: String? = null,
    val type: String,
    val status: AgentStatus? = null,
    val agentRole: String? = null,
    val stepId: String? = null,
    val title: String,
    val details: String? = null,
    val timestamp: String,
    val recoveryAttempt: Int? = null,
    val maxRecoveryAttempts: Int? = null,
    val relevantFiles: List<String> = emptyList()
)

interface AgentStreamRepository {
    fun streamEvents(taskId: String): Flow<AgentEvent>
    suspend fun getTask(taskId: String): AgentTask
}
```

---

## 5. Web Client Demonstration Controls

The React web client includes interactive demo triggers specifically built for Hackathon evaluators in [`AgentActivityView.tsx`](file:///Users/arnavjindal2008/Desktop/AI%20Hack/iota-X/frontend/src/components/bottom/AgentActivityView.tsx):
- **"Standard Workflow" button**: Runs through all 8 sequential lifecycle phases (`✓`, `●`, `○`).
- **"Failure & Recovery (1/3)" button**: Demonstrates test suite failure detection (`✗`), root-cause analysis (`→`), autonomous patch formulation (`Recovery attempt 1/3`), corrective editing, re-testing, and verified completion.
- **"Reset" button**: Restores state to inspect fresh cycles.
