/**
 * AI Coding Harness Interaction Hook
 *
 * Integrates Chat, Terminal, Verification, Git, and Agent Activity.
 * Adheres strictly to the Cross-Platform Contract.
 * The UI supports agent activity separately from chat conversations.
 */

import { useCallback, useEffect, useState } from 'react';
import {
  AgentStep,
  GitChange,
  TerminalOutput,
  VerificationResult,
} from '../types';
import { AgentEvent } from '../types/chatContract';
import { useChat } from './useChat';
import { api } from '../services/api';

export function useHarness() {
  // Agent Activity State (populated from backend API and chat AgentEvents)
  const [agentSteps, setAgentSteps] = useState<AgentStep[]>([]);
  const [isAgentRunning, setIsAgentRunning] = useState<boolean>(false);

  // Terminal State
  const [terminalHistory, setTerminalHistory] = useState<TerminalOutput[]>([
    {
      id: 'term_init',
      command: 'pytest tests',
      stdout: `============================= test session starts ==============================
collected 67 items
tests/test_agents.py .....
tests/test_context.py ..
tests/test_tests_tool.py ....
tests/test_tool_registry.py ..

============================== 67 passed in 1.08s ==============================`,
      stderr: '',
      exitCode: 0,
      durationSeconds: 1.08,
      status: 'success',
      timestamp: 'Initial',
    },
  ]);

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
    durationSeconds: 1.08,
  });
  const [isRunningVerification, setIsRunningVerification] = useState<boolean>(false);

  // Git State
  const [gitChanges, setGitChanges] = useState<GitChange[]>([]);
  const [selectedGitFile, setSelectedGitFile] = useState<string | null>(null);

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

  // Initial load from Harness API
  useEffect(() => {
    async function loadInitial() {
      try {
        const changes = await api.getGitChanges();
        setGitChanges(changes);
        if (changes.length > 0) {
          setSelectedGitFile(changes[0].file);
        }

        const steps = await api.getAgentWorkflow();
        setAgentSteps(steps);
      } catch (err) {
        console.error('Failed to load harness state', err);
      }
    }
    loadInitial();
  }, []);

  const runTerminalCommand = useCallback(async (cmd: string) => {
    if (!cmd.trim()) return;

    try {
      const output = await api.runCommand(cmd);
      setTerminalHistory((prev) => [...prev, output]);
    } catch (err) {
      console.error('Failed to execute command', err);
    }
  }, []);

  const clearTerminal = useCallback(() => {
    setTerminalHistory([]);
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

    // Terminal
    terminalHistory,
    runTerminalCommand,
    clearTerminal,

    // Verification
    verificationResult,
    isRunningVerification,
    runVerification,

    // Git
    gitChanges,
    selectedGitFile,
    setSelectedGitFile,
  };
}
