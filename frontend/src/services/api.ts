/**
 * Harness API Client Interface
 *
 * Defines the contract between the frontend and the AI Coding Harness backend.
 * Provides seamless switching between mock service and live backend endpoints.
 */

import {
  AgentStep,
  ChatMessage,
  GitChange,
  TerminalOutput,
  VerificationResult,
  WorkspaceFile,
} from '../types';

export interface HarnessApiService {
  // Repository & Files
  getRepositoryTree(): Promise<WorkspaceFile[]>;
  getFileContent(path: string): Promise<string>;
  saveFileContent(path: string, content: string): Promise<boolean>;

  // Chat & AI Agents
  sendMessage(
    message: string,
    history: ChatMessage[],
    onChunk?: (chunk: string) => void
  ): Promise<ChatMessage>;

  // Shell Execution
  runCommand(command: string): Promise<TerminalOutput>;

  // Git Subsystem
  getGitChanges(): Promise<GitChange[]>;
  getGitDiff(file?: string): Promise<string>;

  // Verification & Testing
  runTests(filter?: string): Promise<VerificationResult>;

  // Autonomous Agent Status
  getAgentWorkflow(): Promise<AgentStep[]>;
}

// Current implementation uses MockApi by default, can be toggled via VITE_USE_REAL_API env
import { mockApiService } from './mockApi';

export const api: HarnessApiService = mockApiService;

// Export specialized modular services adhering to cross-platform contracts:
export { repositoryApi } from './repositoryApi';
export { chatApi } from './chatApi';
export { uploadApi } from './uploadApi';
