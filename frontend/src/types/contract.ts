/**
 * AI Coding Harness — Shared Cross-Platform Conceptual Contract
 *
 * This contract defines the core repository and editor schemas shared across:
 * 1. Web / Desktop Web (React + TypeScript)
 * 2. macOS (Swift / SwiftUI via Codable)
 * 3. Android (Kotlin / Jetpack Compose via kotlinx.serialization)
 *
 * CRITICAL ARCHITECTURAL RULE:
 * The clients are strictly interfaces to the backend Harness API.
 * Repository intelligence, AST parsing, indexing, and agent logic live in the backend.
 * Do NOT duplicate repository or agent logic inside client code.
 */

// ============================================================================
// 1. Repository Node & Tree Structure
// ============================================================================

export type RepositoryNodeType = 'file' | 'directory';

export interface RepositoryNode {
  /** Unique identifier or normalized relative path */
  id: string;
  /** Display name (e.g. 'session.py' or 'auth') */
  name: string;
  /** Full relative path from repository root (e.g. 'src/auth/session.py') */
  path: string;
  /** Node type: file or directory */
  type: RepositoryNodeType;
  /** Size in bytes (for files) */
  size?: number;
  /** Language identifier (e.g. 'python', 'typescript', 'markdown') */
  language?: string;
  /** Last modification timestamp in ISO 8601 format */
  lastModified?: string;
  /** Child nodes if type is 'directory' */
  children?: RepositoryNode[];
}

export interface RepositoryTree {
  /** Root directory path */
  rootPath: string;
  /** Repository name */
  repositoryName: string;
  /** Active git branch */
  branch: string;
  /** Hierarchical list of root nodes */
  nodes: RepositoryNode[];
  /** Total count of files in the repository */
  totalFiles: number;
  /** Total count of directories in the repository */
  totalDirectories: number;
}

// ============================================================================
// 2. Repository File
// ============================================================================

export interface RepositoryFile {
  /** Unique identifier or path */
  id: string;
  /** Full relative path from repository root (e.g. 'src/auth/session.py') */
  path: string;
  /** File name (e.g. 'session.py') */
  name: string;
  /** Complete text content of the file */
  content: string;
  /** Programming language identifier for syntax highlighting */
  language: string;
  /** File size in bytes */
  size: number;
  /** Encoding format (typically 'utf-8') */
  encoding: string;
  /** Whether the file is read-only */
  isReadOnly?: boolean;
  /** Total number of lines in the file */
  lineCount?: number;
  /** ISO 8601 timestamp of last modification */
  lastModified?: string;
}

// ============================================================================
// 3. File Change (Save / Edit / Create Payload)
// ============================================================================

export type FileChangeType = 'edit' | 'create' | 'delete';

export interface FileChange {
  /** Target relative path in the repository */
  path: string;
  /** New content to persist */
  content: string;
  /** Original content prior to edits (used for conflict detection) */
  originalContent?: string;
  /** Operation type */
  changeType: FileChangeType;
  /** Client timestamp of change in ISO 8601 */
  timestamp: string;
}

// ============================================================================
// 4. Editor State (Client Session Management)
// ============================================================================

export interface EditorCursorPosition {
  line: number;
  column: number;
}

export interface EditorState {
  /** List of currently open files (tabs) */
  openFiles: RepositoryFile[];
  /** Path of the active file being edited, or null if none */
  activeFilePath: string | null;
  /** Set/list of paths that have unsaved in-memory changes */
  modifiedFilePaths: string[];
  /** Current cursor position in active editor */
  cursorPosition?: EditorCursorPosition;
  /** Read-only mode override */
  isReadOnly?: boolean;
}
