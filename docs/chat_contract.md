# AI Coding Harness — Cross-Platform Chat System & API Contract

## 1. Architectural Overview & Eventual Flow

The AI Chat system is designed as a reusable cross-platform product feature across:
1. **Web / Desktop Web** (React 19 + TypeScript)
2. **macOS Client** (Native Swift / SwiftUI)
3. **Android Client** (Native Kotlin / Jetpack Compose)

The visual presentation conforms to platform-native design conventions (e.g. macOS Sonoma / Sequoia guidelines, Android Material 3, Web IDE dark theme), but all three clients communicate over the **exact same typed Chat API contract**.

### The Execution Flow:
```
┌────────────────────────┐   ┌────────────────────────┐   ┌────────────────────────┐
│      Web Client        │   │     macOS Client       │   │     Android Client     │
│   (React + Monaco)     │   │   (Native SwiftUI)     │   │ (Kotlin + Compose)     │
└───────────┬────────────┘   └───────────┬────────────┘   └───────────┬────────────┘
            │                            │                            │
            └────────────────────────────┼────────────────────────────┘
                                         ▼
                                  POST /chat
                               (or WebSocket WS /chat)
                                         ▼
                             ┌────────────────────────┐
                             │   Harness REST API     │
                             └───────────┬────────────┘
                                         ▼
                             ┌────────────────────────┐
                             │  Central Orchestrator  │
                             │ (TaskContext & Cycle)  │
                             └───────────┬────────────┘
                                         ▼
                             ┌────────────────────────┐
                             │ Specialized AI Agents  │
                             │ (Planner, Coder, Critic│
                             │  Verifier) + Tools     │
                             └───────────┬────────────┘
                                         ▼
                             ┌────────────────────────┐
                             │     Model Gateway      │
                             │ (Gemini, Claude, GPT,  │
                             │  NIM, Local Ollama)    │
                             └────────────────────────┘
```

### Critical Architectural Invariants:
1. **No Model Logic in the Client**: The clients only dispatch user prompts, optional file attachments, and active context (active file, open tabs). Clients never call LLM endpoints directly.
2. **No Hardcoded Model Providers**: Never hardcode NVIDIA NIM, Gemini, or OpenAI credentials or client libraries in the frontend. Model selection and routing happen entirely inside the Python `ModelGateway`.
3. **Decoupled Agent Activity**: Agent execution events (`AgentEvent`) are streamed or returned separately from conversation messages. Chat messages represent human-readable dialogue and code proposals; internal multi-step tool iterations are routed to the **Agent Activity** view.

---

## 2. Cross-Platform Typed Conceptual Interface

### Entities:
- **`ChatMessage`**: A single conversational turn (user prompt or assistant answer with markdown, code blocks, and action proposals).
- **`Conversation`**: A persistent or task-based multi-turn message thread.
- **`ChatRequest`**: The client request payload sent to `POST /chat`.
- **`ChatResponse`**: The server response payload containing the assistant's message and any associated `AgentEvent`s.
- **`AgentEvent`**: Fine-grained telemetry emitted by the Orchestrator (step progress, tool calls, verifications).

---

### A. TypeScript Definitions (Web Client)

Defined in [`frontend/src/types/chatContract.ts`](file:///Users/arnavjindal2008/Desktop/AI%20Hack/iota-X/frontend/src/types/chatContract.ts):

```typescript
export type MessageRole = 'user' | 'assistant' | 'system';
export type MessageStatus = 'pending' | 'streaming' | 'completed' | 'failed';

export interface ChatAttachment {
  id: string;
  name: string;
  size: number;
  type: string;
  content?: string;
  url?: string;
}

export interface ChatAction {
  id: string;
  type: 'file_edit' | 'file_create' | 'command_run' | 'test_run';
  file?: string;
  summary: string;
  diff?: string;
  status: 'pending' | 'accepted' | 'rejected' | 'applied';
}

export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  timestamp: string;
  status?: MessageStatus;
  error?: string;
  actions?: ChatAction[];
  referencedFiles?: string[];
  attachments?: ChatAttachment[];
}

export interface Conversation {
  id: string;
  title: string;
  createdAt: string;
  updatedAt: string;
  messages: ChatMessage[];
  activeTaskId?: string;
  metadata?: Record<string, any>;
}

export interface ChatRequestContext {
  activeFilePath?: string | null;
  openFiles?: string[];
  gitBranch?: string;
  repositoryName?: string;
}

export interface ChatRequest {
  conversationId: string;
  message: string;
  attachments?: ChatAttachment[];
  context?: ChatRequestContext;
}

export interface ChatResponse {
  conversationId: string;
  message: ChatMessage;
  agentEvents?: AgentEvent[];
  finished: boolean;
}

export type AgentEventType =
  | 'step_started'
  | 'step_progress'
  | 'tool_call'
  | 'tool_result'
  | 'step_completed'
  | 'error';

export type AgentRole = 'orchestrator' | 'planner' | 'coder' | 'critic' | 'verifier';

export interface AgentEvent {
  id: string;
  type: AgentEventType;
  agentRole: AgentRole;
  title: string;
  details?: string;
  timestamp: string;
  payload?: Record<string, any>;
}
```

---

### B. Swift Native Definitions (macOS Client)

```swift
import Foundation

// MARK: - 1. Message & Roles
public enum MessageRole: String, Codable, Sendable {
    case user
    case assistant
    case system
}

public enum MessageStatus: String, Codable, Sendable {
    case pending
    case streaming
    case completed
    case failed
}

public struct ChatAttachment: Codable, Identifiable, Sendable {
    public let id: String
    public let name: String
    public let size: Int
    public let type: String
    public let content: String?
    public let url: String?
}

public struct ChatAction: Codable, Identifiable, Sendable {
    public let id: String
    public let type: String // file_edit, file_create, command_run, test_run
    public let file: String?
    public let summary: String
    public let diff: String?
    public var status: String // pending, accepted, rejected, applied
}

public struct ChatMessage: Codable, Identifiable, Sendable {
    public let id: String
    public let role: MessageRole
    public let content: String
    public let timestamp: String
    public var status: MessageStatus?
    public var error: String?
    public var actions: [ChatAction]?
    public var referencedFiles: [String]?
    public var attachments: [ChatAttachment]?
}

// MARK: - 2. Conversation
public struct Conversation: Codable, Identifiable, Sendable {
    public let id: String
    public var title: String
    public let createdAt: String
    public var updatedAt: String
    public var messages: [ChatMessage]
    public var activeTaskId: String?
}

// MARK: - 3. Chat Request & Response
public struct ChatRequestContext: Codable, Sendable {
    public let activeFilePath: String?
    public let openFiles: [String]?
    public let gitBranch: String?
    public let repositoryName: String?
}

public struct ChatRequest: Codable, Sendable {
    public let conversationId: String
    public let message: String
    public let attachments: [ChatAttachment]?
    public let context: ChatRequestContext?
}

public struct ChatResponse: Codable, Sendable {
    public let conversationId: String
    public let message: ChatMessage
    public let agentEvents: [AgentEvent]?
    public let finished: Bool
}

// MARK: - 4. Agent Event
public enum AgentEventType: String, Codable, Sendable {
    case step_started
    case step_progress
    case tool_call
    case tool_result
    case step_completed
    case error
}

public enum AgentRole: String, Codable, Sendable {
    case orchestrator
    case planner
    case coder
    case critic
    case verifier
}

public struct AgentEvent: Codable, Identifiable, Sendable {
    public let id: String
    public let type: AgentEventType
    public let agentRole: AgentRole
    public let title: String
    public let details: String?
    public let timestamp: String
}
```

---

### C. Kotlin Native Definitions (Android Client)

```kotlin
package ai.codingharness.client.model.chat

import kotlinx.serialization.Serializable

// 1. Roles & Messages
@Serializable
enum class MessageRole { user, assistant, system }

@Serializable
enum class MessageStatus { pending, streaming, completed, failed }

@Serializable
data class ChatAttachment(
    val id: String,
    val name: String,
    val size: Long,
    val type: String,
    val content: String? = null,
    val url: String? = null
)

@Serializable
data class ChatAction(
    val id: String,
    val type: String,
    val file: String? = null,
    val summary: String,
    val diff: String? = null,
    val status: String
)

@Serializable
data class ChatMessage(
    val id: String,
    val role: MessageRole,
    val content: String,
    val timestamp: String,
    val status: MessageStatus = MessageStatus.completed,
    val error: String? = null,
    val actions: List<ChatAction>? = null,
    val referencedFiles: List<String>? = null,
    val attachments: List<ChatAttachment>? = null
)

// 2. Conversation
@Serializable
data class Conversation(
    val id: String,
    var title: String,
    val createdAt: String,
    var updatedAt: String,
    val messages: List<ChatMessage>,
    val activeTaskId: String? = null
)

// 3. Request & Response
@Serializable
data class ChatRequestContext(
    val activeFilePath: String? = null,
    val openFiles: List<String>? = null,
    val gitBranch: String? = null,
    val repositoryName: String? = null
)

@Serializable
data class ChatRequest(
    val conversationId: String,
    val message: String,
    val attachments: List<ChatAttachment>? = null,
    val context: ChatRequestContext? = null
)

@Serializable
data class ChatResponse(
    val conversationId: String,
    val message: ChatMessage,
    val agentEvents: List<AgentEvent>? = null,
    val finished: Boolean
)

// 4. Agent Event
@Serializable
enum class AgentEventType {
    step_started, step_progress, tool_call, tool_result, step_completed, error
}

@Serializable
enum class AgentRole {
    orchestrator, planner, coder, critic, verifier
}

@Serializable
data class AgentEvent(
    val id: String,
    val type: AgentEventType,
    val agentRole: AgentRole,
    val title: String,
    val details: String? = null,
    val timestamp: String
)
```

---

## 3. macOS Native Chat Architecture Preparation

```
SwiftUI View Hierarchy
│  ├── NavigationSplitView
│  │   ├── Sidebar (Task History / Conversation sessions)
│  │   └── Inspector Panel (Chat Conversation UI)
│  │       ├── Header: Task Title + "New Task" toolbar button
│  │       ├── ScrollViewReader + LazyVStack (Message bubbles)
│  │       │   ├── User Bubble (Accent styled)
│  │       │   └── Assistant Bubble (Markdown text + Code block + Copy button)
│  │       ├── Bottom Bar: Regenerate / Retry buttons
│  │       └── Message Composer: TextEditor + Attachment button + Send
│
▼
ChatAPIClient (URLSession async/await)
│  ├── POST /chat -> ChatResponse
│  └── WebSocket /events -> AsyncThrowingStream<AgentEvent, Error>
│
▼
Harness API -> Python Orchestrator
```

### macOS Native Feel:
- Uses SF Symbols (`sparkles`, `arrow.clockwise`, `doc.on.clipboard`, `plus.bubble`).
- Native keyboard shortcuts (`⌘N` for New Task, `⌘↩` to Send, `⌘R` to Regenerate).
- Uses native `AttributedString(markdown:)` for rendering markdown.

---

## 4. Android Native Chat Architecture Preparation

```
Jetpack Compose Hierarchy
│  ├── Scaffold (TopAppBar with Conversation Title & New Task action)
│  ├── ModalNavigationDrawer (Task History sessions)
│  ├── LazyColumn (Chat Message Feed)
│  │   ├── UserMessageItem (Surface card)
│  │   └── AssistantMessageItem (Markdown card + Syntax highlight + Copy)
│  ├── AnimatedVisibility (Loading indicator / reasoning step)
│  └── Bottom Bar: OutlinedTextField + IconButton(Attachment) + IconButton(Send)
│
▼
ChatRepository (Ktor / Retrofit + Kotlinx Serialization)
│  ├── fun sendMessage(request: ChatRequest): Flow<ChatResponse>
│  └── fun observeAgentEvents(): Flow<AgentEvent>
│
▼
Harness API -> Python Orchestrator
```

### Android Native Feel:
- Conforms to Material 3 dynamic color theming.
- Haptic feedback on message sent and code copied.
- Native photo/file picker integration for attachments.
