/**
 * AI Coding Harness — Shared Cross-Platform Terminal & Shell Contract
 *
 * Defines the core schemas for the Controlled Shell Execution system across:
 * 1. Web / Desktop Web (React + TypeScript)
 * 2. macOS (Swift / SwiftUI via Codable)
 * 3. Android (Kotlin / Jetpack Compose via kotlinx.serialization)
 *
 * CRITICAL ARCHITECTURAL CONSTRAINTS:
 * - Clients MUST NOT execute arbitrary shell commands directly on their host machines.
 * - All terminal invocations route through:
 *   Client -> Terminal API -> Harness Backend -> Controlled Shell Tool -> Repository
 * - The backend Shell Tool enforces security sandboxing, timeouts, and dangerous command blocks.
 */

// ============================================================================
// 1. Command Request
// ============================================================================

export interface CommandRequest {
  /** Shell command to execute (e.g. 'pytest tests', 'git status') */
  command: string;
  /** Working directory relative to sandbox repository root */
  workingDirectory?: string;
  /** Maximum execution duration in seconds before timeout */
  timeoutSeconds?: number;
  /** Optional environment variable overrides */
  environment?: Record<string, string>;
  /** Client session or terminal identifier */
  sessionId?: string;
}

// ============================================================================
// 2. Command Result
// ============================================================================

export type CommandExecutionStatus = 'success' | 'failed' | 'timeout' | 'cancelled';

export interface CommandResult {
  /** Unique execution identifier */
  id: string;
  /** Command that was executed */
  command: string;
  /** Standard output stream */
  stdout: string;
  /** Standard error stream */
  stderr: string;
  /** Process exit status code (0 for success) */
  exitCode: number;
  /** Total execution duration in seconds */
  durationSeconds: number;
  /** Overall execution status */
  status: CommandExecutionStatus;
  /** Flag indicating whether command timed out */
  timedOut?: boolean;
  /** ISO 8601 execution timestamp */
  timestamp: string;
}

// ============================================================================
// 3. Terminal Output (Client UI Model)
// ============================================================================

export type TerminalItemStatus = 'running' | 'success' | 'failed' | 'cancelled';

export interface TerminalOutput {
  /** Unique output block ID */
  id: string;
  /** Full command line string */
  command: string;
  /** Standard output content */
  stdout: string;
  /** Standard error content */
  stderr: string;
  /** Exit code (null while still running) */
  exitCode: number | null;
  /** Elapsed duration in seconds */
  durationSeconds: number;
  /** Current state of the process */
  status: TerminalItemStatus;
  /** Formatted timestamp */
  timestamp: string;
  /** Working directory where command executed */
  cwd?: string;
}
