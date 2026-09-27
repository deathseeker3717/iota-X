/**
 * AI Coding Harness — Autonomous Agent Workflow Hook
 *
 * Exposes real-time Agent Activity telemetry.
 * Connects to the pluggable IAgentEventStream (Mock, SSE, Polling, WebSocket).
 * UI components consume this hook with zero transport coupling.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import {
  AgentEvent,
  AgentStatus,
  AgentStep,
  AgentTask,
  StreamTransportType,
} from '../types/agentContract';
import {
  agentStreamService,
  MockAgentEventStream,
  PollingAgentStream,
  SSEAgentStream,
  WebSocketAgentStream,
} from '../services/agentStream';

export function useAgentWorkflow() {
  const [task, setTask] = useState<AgentTask | null>(null);
  const [steps, setSteps] = useState<AgentStep[]>([]);
  const [status, setStatus] = useState<AgentStatus>('inspecting');
  const [isRunning, setIsRunning] = useState<boolean>(false);
  const [recoveryAttempt, setRecoveryAttempt] = useState<number>(0);
  const [maxRecoveryAttempts] = useState<number>(3);
  const [activeScenario, setActiveScenario] = useState<'happy' | 'recovery'>('happy');
  const [transportType, setTransportType] = useState<StreamTransportType>('mock');
  const [logs, setLogs] = useState<AgentEvent[]>([]);

  const cancelSimulationRef = useRef<(() => void) | null>(null);

  // Initialize initial state from stream service
  const loadInitial = useCallback(async () => {
    try {
      const initialTask = await agentStreamService.getTask('task_demo_101');
      setTask(initialTask);
      setSteps(initialTask.steps);
      setStatus(initialTask.status);
      setRecoveryAttempt(initialTask.recoveryAttempt);
    } catch (err) {
      console.error('Failed to load initial agent task', err);
    }
  }, []);

  useEffect(() => {
    loadInitial();
  }, [loadInitial]);

  // Handle incoming stream events regardless of transport
  const handleEvent = useCallback((event: AgentEvent) => {
    if (event.status) {
      setStatus(event.status);
    }
    setLogs((prev) => [event, ...prev.slice(0, 49)]);

    if (event.recoveryAttempt !== undefined) {
      setRecoveryAttempt(event.recoveryAttempt);
    }

    setSteps((prevSteps) => {
      const updated = [...prevSteps];

      // If event matches a step directly
      if (event.stepId) {
        const idx = updated.findIndex((s) => s.id === event.stepId);
        if (idx !== -1) {
          if (event.type === 'test_failed') {
            updated[idx] = {
              ...updated[idx],
              status: 'failed',
              error: event.details,
            };
          } else {
            updated[idx] = {
              ...updated[idx],
              status: 'completed',
              details: event.details || updated[idx].details,
            };
          }
        }
      }

      // Check for in-progress step transitions
      if (event.type === 'inspecting') {
        const s = updated.find((x) => x.id === 'step_5');
        if (s) s.status = 'in_progress';
      } else if (event.type === 'editing') {
        const s = updated.find((x) => x.id === 'step_6');
        if (s) s.status = 'in_progress';
      } else if (event.type === 'testing' || event.type === 'testing_again') {
        const s = updated.find((x) => x.id === 'step_7');
        if (s) s.status = 'in_progress';
      } else if (event.type === 'verification') {
        const s = updated.find((x) => x.id === 'step_8');
        if (s) s.status = 'completed';
      }

      // Check for recovery-specific step injection
      if (event.type === 'failure_analysis') {
        if (!updated.some((s) => s.id === 'step_fail_analysis')) {
          updated.push({
            id: 'step_fail_analysis',
            title: 'Failure analysis',
            status: 'completed',
            agentName: 'PlannerAgent',
            details: event.details,
          });
        }
      } else if (event.type === 'recovery_attempt') {
        if (!updated.some((s) => s.id === 'step_rec_1')) {
          updated.push({
            id: 'step_rec_1',
            title: 'Recovery attempt 1/3',
            status: 'recovering',
            agentName: 'RecoveryAgent',
            recoveryAttempt: 1,
            maxRecoveryAttempts: 3,
            details: event.details,
          });
        }
      } else if (event.type === 'correction') {
        if (!updated.some((s) => s.id === 'step_correction')) {
          updated.push({
            id: 'step_correction',
            title: 'Correction applied',
            status: 'completed',
            agentName: 'CoderAgent',
            details: event.details,
            relevantFiles: event.relevantFiles,
          });
        }
      }

      return updated;
    });

    if (event.type === 'completed' || event.type === 'error') {
      setIsRunning(false);
    }
  }, []);

  // Trigger scenario simulation
  const startScenario = useCallback(
    (scenario: 'happy' | 'recovery') => {
      // Cancel any ongoing run
      if (cancelSimulationRef.current) {
        cancelSimulationRef.current();
      }

      setActiveScenario(scenario);
      setIsRunning(true);
      setRecoveryAttempt(0);

      if (scenario === 'happy') {
        // Reset steps to fresh state
        setSteps([
          {
            id: 'step_1',
            title: 'Task received',
            status: 'in_progress',
            agentName: 'Orchestrator',
            details: 'Received user issue: Session timeout occurs prematurely under high load.',
          },
          {
            id: 'step_2',
            title: 'Planning',
            status: 'pending',
            agentName: 'PlannerAgent',
            details: 'Formulate multi-phase execution strategy.',
          },
          {
            id: 'step_3',
            title: 'Repository research',
            status: 'pending',
            agentName: 'ResearchAgent',
            details: 'Scan symbols and references.',
          },
          {
            id: 'step_4',
            title: 'Relevant files found',
            status: 'pending',
            agentName: 'ResearchAgent',
            details: 'Identify candidate files to modify.',
          },
          {
            id: 'step_5',
            title: 'Inspecting code',
            status: 'pending',
            agentName: 'CoderAgent',
            details: 'Analyze token expiry logic.',
          },
          {
            id: 'step_6',
            title: 'Editing',
            status: 'pending',
            agentName: 'CoderAgent',
            details: 'Apply unified diff.',
          },
          {
            id: 'step_7',
            title: 'Running tests',
            status: 'pending',
            agentName: 'TestAgent',
            details: 'Run pytest test suite.',
          },
          {
            id: 'step_8',
            title: 'Verification',
            status: 'pending',
            agentName: 'VerificationAgent',
            details: 'Verify full regression safety.',
          },
        ]);
      } else {
        // Recovery scenario: prepare initial steps
        setSteps([
          {
            id: 'step_1',
            title: 'Task received',
            status: 'completed',
            agentName: 'Orchestrator',
            details: 'Fix authentication timeout.',
          },
          {
            id: 'step_2',
            title: 'Planning',
            status: 'completed',
            agentName: 'PlannerAgent',
            details: 'Plan with failure boundaries.',
          },
          {
            id: 'step_3',
            title: 'Repository research',
            status: 'completed',
            agentName: 'ResearchAgent',
            details: 'Scanned session files.',
          },
          {
            id: 'step_4',
            title: 'Relevant files found',
            status: 'completed',
            agentName: 'ResearchAgent',
            details: 'Found: src/harness/auth.py, tests/test_auth.py',
            relevantFiles: ['src/harness/auth.py', 'tests/test_auth.py'],
          },
          {
            id: 'step_5',
            title: 'Inspecting code',
            status: 'completed',
            agentName: 'CoderAgent',
            details: 'Inspecting src/harness/auth.py.',
          },
          {
            id: 'step_6',
            title: 'Editing',
            status: 'completed',
            agentName: 'CoderAgent',
            details: 'Applied initial edit.',
          },
          {
            id: 'step_7',
            title: 'Running tests',
            status: 'in_progress',
            agentName: 'TestAgent',
            details: 'Executing test suite...',
          },
        ]);
      }

      if (agentStreamService instanceof MockAgentEventStream) {
        cancelSimulationRef.current = agentStreamService.simulateScenario(
          scenario,
          handleEvent,
          () => setIsRunning(false)
        );
      }
    },
    [handleEvent]
  );

  const resetWorkflow = useCallback(() => {
    if (cancelSimulationRef.current) {
      cancelSimulationRef.current();
    }
    setIsRunning(false);
    loadInitial();
  }, [loadInitial]);

  return {
    task,
    steps,
    status,
    isRunning,
    recoveryAttempt,
    maxRecoveryAttempts,
    activeScenario,
    transportType,
    setTransportType,
    startScenario,
    resetWorkflow,
    logs,
  };
}
