/**
 * AI Coding Harness — Shared Cross-Platform Agent Activity Contract
 *
 * Defines the models and streaming interface for the autonomous agent workflow:
 * - Planning
 * - Repository Research
 * - Code Inspection & Editing
 * - Test Execution & Verification
 * - Failure Analysis & Recovery Loops (1/3, 2/3, 3/3)
 *
 * Clients MUST NOT execute agent logic locally. The backend orchestrator emits
 * structured events consumed uniformly by Web, macOS, and Android.
 */

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

export interface AgentStepArtifact {
  name: string;
  path?: string;
  type: 'file' | 'diff' | 'test_output' | 'plan';
}

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
  artifacts?: AgentStepArtifact[];
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

export type AgentEventType =
  | 'task_received'
  | 'planning'
  | 'researching'
  | 'files_found'
  | 'inspecting'
  | 'editing'
  | 'testing'
  | 'test_failed'
  | 'failure_analysis'
  | 'recovery_attempt'
  | 'correction'
  | 'testing_again'
  | 'verification'
  | 'completed'
  | 'step_started'
  | 'step_progress'
  | 'step_completed'
  | 'tool_call'
  | 'tool_result'
  | 'error';

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

/**
 * Pluggable Stream Transport Interface.
 * Allows switching between HTTP Polling, Server-Sent Events, WebSockets, or Mocks
 * without any UI changes.
 */
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
