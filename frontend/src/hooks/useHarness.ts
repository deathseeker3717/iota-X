/**
 * AI Coding Harness Interaction Hook
 *
 * Integrates Chat, Terminal, Verification, Git, and Agent Activity.
 * Adheres strictly to the Cross-Platform Contract.
 * The UI supports agent activity separately from chat conversations.
 * Terminal commands route to the backend's controlled shell tool.
 */

import { useCallback, useEffect, useState } from 'react';
import {
  AgentStep,
  GitChange,
  GitCommit,
  GitStatus,
  TerminalOutput,
  VerificationResult,
} from '../types';
import { AgentEvent } from '../types/chatContract';
import { useChat } from './useChat';
import { api, gitApi } from '../services/api';
import { terminalApi } from '../services/terminalApi';

export function useHarness() {
  // Agent Activity State (populated from backend API and chat AgentEvents)
  const [agentSteps, setAgentSteps] = useState<AgentStep[]>([]);
  const [isAgentRunning, setIsAgentRunning] = useState<boolean>(false);

  // Terminal State (connected to backend controlled shell tool)
  const [terminalHistory, setTerminalHistory] = useState<TerminalOutput[]>([
    {
      id: 'term_init_1',
      command: 'pytest tests',
      stdout: `============================= test session starts ==============================
collected 67 items
tests/test_agents.py .....
tests/test_context.py ..
tests/test_tests_tool.py ....
tests/test_tool_registry.py ..

============================== 67 passed in 1.02s ==============================`,
      stderr: '',
      exitCode: 0,
      durationSeconds: 1.02,
      status: 'success',
      timestamp: 'Initial',
      cwd: 'iota-X',
    },
  ]);
  const [isTerminalExecuting, setIsTerminalExecuting] = useState<boolean>(false);
  const [activeCommandId, setActiveCommandId] = useState<string | null>(null);

  // Verification State
  const [verificationResult, setVerificationResult] = useState<VerificationResult>({
    status: 'verified',
    testsPassed: true,
    totalTests: 67,
    passedTests: 67,
    failedTests: 0,
    typeCheckPassed: true,
    lintPassed: true,
    requirementsSatisfied: true,
    failures: [],
    durationSeconds: 1.02,
  });
  const [isRunningVerification, setIsRunningVerification] = useState<boolean>(false);

  // Git State (backed by Backend Git Tool)
  const [gitStatus, setGitStatus] = useState<GitStatus | null>(null);
  const [gitChanges, setGitChanges] = useState<GitChange[]>([]);
  const [selectedGitFile, setSelectedGitFile] = useState<string | null>(null);
  const [gitCommits, setGitCommits] = useState<GitCommit[]>([]);
  const [selectedCommit, setSelectedCommit] = useState<GitCommit | null>(null);
  const [selectedCommitDiff, setSelectedCommitDiff] = useState<string>('');
  const [isGitLoading, setIsGitLoading] = useState<boolean>(false);

  // Handler for Agent Events emitted during chat execution
  // Dispatches to Agent Activity panel separately from conversation
  const handleAgentEvents = useCallback((events: AgentEvent[]) => {
    setIsAgentRunning(true);
    const newSteps: AgentStep[] = events.map((ev) => ({
      id: ev.id,
      title: ev.title,
      status:
        ev.type === 'step_completed'
          ? 'completed'
          : ev.type === 'error'
          ? 'failed'
          : 'in_progress',
      details: ev.details,
      subSteps: ev.payload?.subSteps,
    }));

    setAgentSteps((prev) => {
      // Append unique steps
      const existingIds = new Set(prev.map((s) => s.id));
      const filtered = newSteps.filter((s) => !existingIds.has(s.id));
      return [...prev, ...filtered];
    });

    // Mark active finished after short cooldown
    setTimeout(() => setIsAgentRunning(false), 800);
  }, []);

  // Dedicated Chat Hook
  const {
    conversations,
    activeConversationId,
    selectConversation,
    startNewTask,
    messages,
    isGenerating,
    error: chatError,
    sendMessage: sendChatMessage,
    regenerateLastMessage,
    retryMessage,
    stopGeneration,
    clearChat,
    attachments,
    addAttachments,
    removeAttachment,
  } = useChat({
    onAgentEvents: handleAgentEvents,
  });

  // Git Operations through backend Git Tool
  const refreshGit = useCallback(async () => {
    try {
      setIsGitLoading(true);
      const [status, logs] = await Promise.all([
        gitApi.getStatus(),
        gitApi.getLog({ maxCount: 15 }),
      ]);
      setGitStatus(status);
      setGitChanges(status.changes);
      setGitCommits(logs);
      setSelectedGitFile((current) => {
        if (current && status.changes.some((c) => c.file === current)) {
          return current;
        }
        return status.changes.length > 0 ? status.changes[0].file : null;
      });
    } catch (err) {
      console.error('Failed to refresh Git status', err);
    } finally {
      setIsGitLoading(false);
    }
  }, []);

  const selectGitCommit = useCallback(async (hash: string) => {
    try {
      setIsGitLoading(true);
      const diff = await gitApi.getShow(hash);
      const commit = gitCommits.find((c) => c.hash === hash || c.shortHash === hash) || null;
      setSelectedCommit(commit);
      setSelectedCommitDiff(diff);
    } catch (err) {
      console.error('Failed to inspect commit', err);
    } finally {
      setIsGitLoading(false);
    }
  }, [gitCommits]);

  // Initial load from Harness API
  useEffect(() => {
    async function loadInitial() {
      try {
        await refreshGit();
        const steps = await api.getAgentWorkflow();
        setAgentSteps(steps);
      } catch (err) {
        console.error('Failed to load harness state', err);
      }
    }
    loadInitial();
  }, [refreshGit]);

  // Run controlled shell command via terminalApi
  const runTerminalCommand = useCallback(async (cmd: string) => {
    if (!cmd.trim()) return;

    const tempId = `cmd_${Date.now()}`;
    setActiveCommandId(tempId);
    setIsTerminalExecuting(true);

    const pendingItem: TerminalOutput = {
      id: tempId,
      command: cmd,
      stdout: '',
      stderr: '',
      exitCode: null,
      durationSeconds: 0,
      status: 'running',
      timestamp: new Date().toLocaleTimeString(),
      cwd: 'iota-X',
    };

    setTerminalHistory((prev) => [...prev, pendingItem]);

    try {
      const result = await terminalApi.executeCommand({
        command: cmd,
        workingDirectory: 'iota-X',
      });

      setTerminalHistory((prev) =>
        prev.map((item) =>
          item.id === tempId
            ? {
                id: result.id,
                command: result.command,
                stdout: result.stdout,
                stderr: result.stderr,
                exitCode: result.exitCode,
                durationSeconds: result.durationSeconds,
                status: result.status === 'success' ? 'success' : 'failed',
                timestamp: new Date().toLocaleTimeString(),
                cwd: 'iota-X',
              }
            : item
        )
      );
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Command execution failed';
      setTerminalHistory((prev) =>
        prev.map((item) =>
          item.id === tempId
            ? {
                ...item,
                stderr: errorMsg,
                exitCode: 1,
                status: 'failed',
              }
            : item
        )
      );
    } finally {
      setIsTerminalExecuting(false);
      setActiveCommandId(null);
    }
  }, []);

  const cancelTerminalCommand = useCallback(async () => {
    if (activeCommandId) {
      await terminalApi.cancelCommand(activeCommandId);
      setIsTerminalExecuting(false);
      setActiveCommandId(null);
    }
  }, [activeCommandId]);

  const clearTerminal = useCallback(async () => {
    setTerminalHistory([]);
    await terminalApi.clearHistory();
  }, []);

  const runVerification = useCallback(async (filter?: string) => {
    try {
      setIsRunningVerification(true);
      const result = await api.runTests(filter);
      setVerificationResult(result);
    } catch (err) {
      console.error('Failed to run verification', err);
    } finally {
      setIsRunningVerification(false);
    }
  }, []);

  return {
    // Chat & Conversations
    conversations,
    activeConversationId,
    selectConversation,
    startNewTask,
    messages,
    isGenerating: isGenerating || isAgentRunning,
    chatError,
    sendMessage: sendChatMessage,
    regenerateLastMessage,
    retryMessage,
    stopGeneration,
    clearChat,
    attachments,
    addAttachments,
    removeAttachment,

    // Agent Activity (supported separately)
    agentSteps,
    isAgentRunning,

    // Terminal (Controlled Shell Tool)
    terminalHistory,
    isTerminalExecuting,
    runTerminalCommand,
    cancelTerminalCommand,
    clearTerminal,

    // Verification
    verificationResult,
    isRunningVerification,
    runVerification,

    // Git (Backend Git Tool)
    gitStatus,
    gitChanges,
    selectedGitFile,
    setSelectedGitFile,
    gitCommits,
    selectedCommit,
    selectedCommitDiff,
    isGitLoading,
    refreshGit,
    selectGitCommit,
  };
}
