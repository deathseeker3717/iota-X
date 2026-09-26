/**
 * Shared Type Definitions for the AI Coding Harness Frontend
 */

// Export the cross-platform conceptual contracts:
export * from './contract';
export * from './chatContract';
export * from './attachmentContract';
export * from './terminalContract';
export * from './gitContract';

import {
  RepositoryNode,
  RepositoryFile,
} from './contract';

import {
  ChatMessage as ContractChatMessage,
  ChatAction,
} from './chatContract';

import { Attachment } from './attachmentContract';

// Backward compatibility aliases mapping to the contract:
export type WorkspaceFile = RepositoryNode;
export type EditorTab = RepositoryFile & { isModified?: boolean };
export type AIAction = ChatAction;
export type UploadedFile = Attachment;
export type ChatMessage = ContractChatMessage & { isStreaming?: boolean };

export interface TestFailure {
  testName: string;
  file: string;
  expected: string;
  received: string;
  trace: string;
}

export interface VerificationResult {
  status: 'verified' | 'failed' | 'in_progress' | 'idle';
  testsPassed: boolean;
  totalTests: number;
  passedTests: number;
  failedTests: number;
  typeCheckPassed: boolean;
  lintPassed: boolean;
  requirementsSatisfied: boolean;
  failures: TestFailure[];
  durationSeconds: number;
}

export interface AgentStep {
  id: string;
  title: string;
  status: 'completed' | 'in_progress' | 'pending' | 'failed' | 'recovering';
  details?: string;
  subSteps?: string[];
}

export type ActiveBottomTab = 'terminal' | 'tests' | 'git' | 'agent';
export type ActiveSideBarTab = 'explorer' | 'search' | 'git' | 'tests';
