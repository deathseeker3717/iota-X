/**
 * AI Coding Harness — Shared Cross-Platform Chat Contract
 *
 * Defines the core schemas for the AI Chat system across:
 * 1. Web / Desktop Web (React + TypeScript)
 * 2. macOS (Swift / SwiftUI via Codable)
 * 3. Android (Kotlin / Jetpack Compose via kotlinx.serialization)
 *
 * CRITICAL ARCHITECTURAL CONSTRAINTS:
 * - The clients are strictly UI interfaces to the Harness API.
 * - Do NOT put model logic in the client.
 * - Do NOT hard-code NVIDIA NIM or any provider into the frontend.
 * - The backend Harness handles: Orchestrator -> Agent -> Model Gateway.
 * - The UI supports agent activity separately from conversation messages.
 */

// ============================================================================
// 1. Chat Message & Roles
// ============================================================================

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

// ============================================================================
// 2. Conversation
// ============================================================================

export interface Conversation {
  id: string;
  title: string;
  createdAt: string;
  updatedAt: string;
  messages: ChatMessage[];
  activeTaskId?: string;
  metadata?: Record<string, any>;
}

// ============================================================================
// 3. Chat Request & Response
// ============================================================================

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

// ============================================================================
// 4. Agent Event (Emitted by Orchestrator / Agents during execution)
// ============================================================================

export type AgentEventType =
  | 'step_started'
  | 'step_progress'
  | 'tool_call'
  | 'tool_result'
  | 'step_completed'
  | 'error';

export type AgentRole =
  | 'orchestrator'
  | 'planner'
  | 'coder'
  | 'critic'
  | 'verifier';

export interface AgentEvent {
  id: string;
  type: AgentEventType;
  agentRole: AgentRole;
  title: string;
  details?: string;
  timestamp: string;
  payload?: Record<string, any>;
}
