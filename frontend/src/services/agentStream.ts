/**
 * AI Coding Harness — Agent Event Stream Transport Layer
 *
 * Implements pluggable transport strategies:
 * - Mock Simulation (default for local development & demonstration)
 * - HTTP Polling (fallback)
 * - Server-Sent Events (SSE - recommended for real-time one-way telemetry)
 * - WebSockets (prepared contract without early premature socket binding)
 *
 * The UI consumes the unified IAgentEventStream interface; transports can be swapped
 * with zero UI code changes.
 */

import {
  AgentEvent,
  AgentStep,
  AgentTask,
  IAgentEventStream,
  StreamTransportType,
} from '../types/agentContract';

/**
 * Server-Sent Events (SSE) Stream Client
 */
export class SSEAgentStream implements IAgentEventStream {
  readonly transport: StreamTransportType = 'sse';
  private baseUrl: string;

  constructor(baseUrl: string = '/api/v1/agent') {
    this.baseUrl = baseUrl;
  }

  subscribe(
    taskId: string,
    onEvent: (event: AgentEvent) => void,
    onError?: (err: Error) => void
  ): () => void {
    const url = `${this.baseUrl}/stream?taskId=${encodeURIComponent(taskId)}`;
    const eventSource = new EventSource(url);

    eventSource.onmessage = (messageEvent) => {
      try {
        const data: AgentEvent = JSON.parse(messageEvent.data);
        onEvent(data);
      } catch (err) {
        console.error('Failed to parse SSE agent event', err);
      }
    };

    eventSource.onerror = (e) => {
      onError?.(new Error('SSE connection error'));
    };

    return () => {
      eventSource.close();
    };
  }

  async getTask(taskId: string): Promise<AgentTask> {
    const res = await fetch(`${this.baseUrl}/tasks/${taskId}`);
    if (!res.ok) throw new Error(`Failed to fetch task: ${res.statusText}`);
    return res.json();
  }

  async getSteps(taskId: string): Promise<AgentStep[]> {
    const res = await fetch(`${this.baseUrl}/tasks/${taskId}/steps`);
    if (!res.ok) throw new Error(`Failed to fetch steps: ${res.statusText}`);
    return res.json();
  }
}

/**
 * HTTP Polling Stream Client
 */
export class PollingAgentStream implements IAgentEventStream {
  readonly transport: StreamTransportType = 'polling';
  private baseUrl: string;
  private intervalMs: number;

  constructor(baseUrl: string = '/api/v1/agent', intervalMs: number = 1000) {
    this.baseUrl = baseUrl;
    this.intervalMs = intervalMs;
  }

  subscribe(
    taskId: string,
    onEvent: (event: AgentEvent) => void,
    onError?: (err: Error) => void
  ): () => void {
    let active = true;
    let lastTimestamp = '';

    const poll = async () => {
      if (!active) return;
      try {
        const query = lastTimestamp ? `?since=${encodeURIComponent(lastTimestamp)}` : '';
        const res = await fetch(`${this.baseUrl}/tasks/${taskId}/events${query}`);
        if (res.ok) {
          const events: AgentEvent[] = await res.json();
          for (const ev of events) {
            lastTimestamp = ev.timestamp;
            onEvent(ev);
          }
        }
      } catch (err) {
        onError?.(err instanceof Error ? err : new Error(String(err)));
      }

      if (active) {
        setTimeout(poll, this.intervalMs);
      }
    };

    poll();

    return () => {
      active = false;
    };
  }

  async getTask(taskId: string): Promise<AgentTask> {
    const res = await fetch(`${this.baseUrl}/tasks/${taskId}`);
    if (!res.ok) throw new Error(`Failed to fetch task: ${res.statusText}`);
    return res.json();
  }

  async getSteps(taskId: string): Promise<AgentStep[]> {
    const res = await fetch(`${this.baseUrl}/tasks/${taskId}/steps`);
    if (!res.ok) throw new Error(`Failed to fetch steps: ${res.statusText}`);
    return res.json();
  }
}

/**
 * WebSocket Stream Client (Prepared Architecture)
 * Adheres to the prompt constraint: Do NOT implement WebSockets unless the backend is ready.
 */
export class WebSocketAgentStream implements IAgentEventStream {
  readonly transport: StreamTransportType = 'websocket';
  private wsUrl: string;

  constructor(wsUrl: string = 'ws://localhost:8000/ws/v1/agent/events') {
    this.wsUrl = wsUrl;
  }

  subscribe(
    taskId: string,
    onEvent: (event: AgentEvent) => void,
    onError?: (err: Error) => void
  ): () => void {
    console.warn(
      'WebSocket transport initialized in standby mode. Backend WS endpoint not activated yet.'
    );
    // Prepared connection logic ready for backend activation:
    /*
    const ws = new WebSocket(`${this.wsUrl}?taskId=${encodeURIComponent(taskId)}`);
    ws.onmessage = (e) => onEvent(JSON.parse(e.data));
    ws.onerror = (e) => onError?.(new Error('WebSocket error'));
    return () => ws.close();
    */
    return () => {};
  }

  async getTask(taskId: string): Promise<AgentTask> {
    throw new Error('WebSocket stream uses companion REST endpoint for static snapshots');
  }

  async getSteps(taskId: string): Promise<AgentStep[]> {
    throw new Error('WebSocket stream uses companion REST endpoint for static snapshots');
  }
}

/**
 * Mock Agent Event Stream
 * Powers the Hackathon demonstration with both standard execution and the
 * failure/recovery loop (1/3, 2/3, 3/3).
 */
export class MockAgentEventStream implements IAgentEventStream {
  readonly transport: StreamTransportType = 'mock';

  private initialTask: AgentTask = {
    id: 'task_demo_101',
    title: 'Fix authentication session timeout and token refresh race condition',
    description: 'Autonomous multi-agent workflow solving repository issue #42',
    status: 'inspecting',
    createdAt: new Date().toLocaleTimeString(),
    currentStepIndex: 4,
    totalSteps: 8,
    recoveryAttempt: 0,
    maxRecoveryAttempts: 3,
    steps: [
      {
        id: 'step_1',
        title: 'Task received',
        status: 'completed',
        agentName: 'Orchestrator',
        durationSeconds: 0.1,
        details: 'Received user issue: Session timeout occurs prematurely under high load.',
        subSteps: ['Parsed task requirements', 'Initialized execution state context'],
      },
      {
        id: 'step_2',
        title: 'Planning',
        status: 'completed',
        agentName: 'PlannerAgent',
        durationSeconds: 0.8,
        details: 'Formulated 4-phase execution plan: research, code modification, verification, recovery.',
        subSteps: ['Identified auth & session components', 'Built atomic execution sequence'],
      },
      {
        id: 'step_3',
        title: 'Repository research',
        status: 'completed',
        agentName: 'ResearchAgent',
        durationSeconds: 1.2,
        details: 'Indexed code AST, symbols, and cross-references for token refresh logic.',
        subSteps: ['Queried symbol index for SessionManager', 'Analyzed test coverage in tests/test_auth.py'],
      },
      {
        id: 'step_4',
        title: 'Relevant files found',
        status: 'completed',
        agentName: 'ResearchAgent',
        durationSeconds: 0.3,
        details: 'Located core target files: src/harness/auth.py, src/harness/session.py, tests/test_auth.py',
        relevantFiles: ['src/harness/auth.py', 'src/harness/session.py', 'tests/test_auth.py'],
        subSteps: [
          'src/harness/auth.py (Token generation & validation)',
          'src/harness/session.py (Session timeout threshold)',
          'tests/test_auth.py (Unit test assertions)',
        ],
      },
      {
        id: 'step_5',
        title: 'Inspecting code',
        status: 'in_progress',
        agentName: 'CoderAgent',
        details: 'Analyzing token expiry validation at src/harness/auth.py:45-80.',
        relevantFiles: ['src/harness/auth.py'],
        subSteps: ['Reading AST nodes', 'Tracing concurrency lock in SessionManager'],
      },
      {
        id: 'step_6',
        title: 'Editing',
        status: 'pending',
        agentName: 'CoderAgent',
        details: 'Apply unified diff to update timeout configuration and concurrency lock.',
      },
      {
        id: 'step_7',
        title: 'Running tests',
        status: 'pending',
        agentName: 'TestAgent',
        details: 'Execute pytest suite via Controlled Shell Tool.',
      },
      {
        id: 'step_8',
        title: 'Verification',
        status: 'pending',
        agentName: 'VerificationAgent',
        details: 'Confirm zero regressions, lint conformance, and type correctness.',
      },
    ],
    relevantFiles: ['src/harness/auth.py', 'src/harness/session.py', 'tests/test_auth.py'],
    errors: [],
    iteration: 1,
    maxIterations: 25,
  };

  private listeners = new Set<(event: AgentEvent) => void>();

  subscribe(
    taskId: string,
    onEvent: (event: AgentEvent) => void,
    onError?: (err: Error) => void
  ): () => void {
    this.listeners.add(onEvent);
    return () => {
      this.listeners.delete(onEvent);
    };
  }

  async getTask(taskId: string): Promise<AgentTask> {
    return JSON.parse(JSON.stringify(this.initialTask));
  }

  async getSteps(taskId: string): Promise<AgentStep[]> {
    return JSON.parse(JSON.stringify(this.initialTask.steps));
  }

  /**
   * Run a live scenario simulation:
   * 'happy' -> All 8 steps succeed cleanly.
   * 'recovery' -> Demonstrates test failure, failure analysis, recovery attempt 1/3, correction, and re-testing.
   */
  simulateScenario(
    scenario: 'happy' | 'recovery',
    onEvent: (event: AgentEvent) => void,
    onFinish?: () => void
  ): () => void {
    let isCancelled = false;
    const timeouts: ReturnType<typeof setTimeout>[] = [];

    const schedule = (delay: number, fn: () => void) => {
      const t = setTimeout(() => {
        if (!isCancelled) fn();
      }, delay);
      timeouts.push(t);
    };

    if (scenario === 'happy') {
      // Step 1: Task received
      schedule(200, () => {
        onEvent({
          id: `ev_${Date.now()}_1`,
          taskId: 'task_demo_101',
          type: 'task_received',
          status: 'task_received',
          stepId: 'step_1',
          title: 'Task received',
          details: 'Autonomous harness received task specification from prompt.',
          timestamp: new Date().toLocaleTimeString(),
          stepIndex: 0,
        });
      });

      // Step 2: Planning
      schedule(1000, () => {
        onEvent({
          id: `ev_${Date.now()}_2`,
          taskId: 'task_demo_101',
          type: 'planning',
          status: 'planning',
          stepId: 'step_2',
          title: 'Planning',
          details: 'PlannerAgent generated 4-step execution strategy with dependencies.',
          timestamp: new Date().toLocaleTimeString(),
          stepIndex: 1,
        });
      });

      // Step 3: Repository research
      schedule(2000, () => {
        onEvent({
          id: `ev_${Date.now()}_3`,
          taskId: 'task_demo_101',
          type: 'researching',
          status: 'researching',
          stepId: 'step_3',
          title: 'Repository research',
          details: 'ResearchAgent scanning repository index, symbol graph, and references.',
          timestamp: new Date().toLocaleTimeString(),
          stepIndex: 2,
        });
      });

      // Step 4: Relevant files found
      schedule(3000, () => {
        onEvent({
          id: `ev_${Date.now()}_4`,
          taskId: 'task_demo_101',
          type: 'files_found',
          status: 'files_found',
          stepId: 'step_4',
          title: 'Relevant files found',
          details: 'Found: src/harness/auth.py, src/harness/session.py, tests/test_auth.py',
          relevantFiles: ['src/harness/auth.py', 'src/harness/session.py', 'tests/test_auth.py'],
          timestamp: new Date().toLocaleTimeString(),
          stepIndex: 3,
        });
      });

      // Step 5: Inspecting code
      schedule(4200, () => {
        onEvent({
          id: `ev_${Date.now()}_5`,
          taskId: 'task_demo_101',
          type: 'inspecting',
          status: 'inspecting',
          stepId: 'step_5',
          title: 'Inspecting code',
          details: 'Analyzing token expiry validation at src/harness/auth.py:45-80.',
          relevantFiles: ['src/harness/auth.py'],
          timestamp: new Date().toLocaleTimeString(),
          stepIndex: 4,
        });
      });

      // Step 6: Editing
      schedule(5500, () => {
        onEvent({
          id: `ev_${Date.now()}_6`,
          taskId: 'task_demo_101',
          type: 'editing',
          status: 'editing',
          stepId: 'step_6',
          title: 'Editing',
          details: 'Applying unified diff with concurrency lock on refresh_session().',
          relevantFiles: ['src/harness/session.py'],
          timestamp: new Date().toLocaleTimeString(),
          stepIndex: 5,
        });
      });

      // Step 7: Running tests
      schedule(6800, () => {
        onEvent({
          id: `ev_${Date.now()}_7`,
          taskId: 'task_demo_101',
          type: 'testing',
          status: 'testing',
          stepId: 'step_7',
          title: 'Running tests',
          details: 'Invoking pytest tests/test_auth.py via Controlled Shell Tool.',
          timestamp: new Date().toLocaleTimeString(),
          stepIndex: 6,
        });
      });

      // Step 8: Verification
      schedule(8200, () => {
        onEvent({
          id: `ev_${Date.now()}_8`,
          taskId: 'task_demo_101',
          type: 'verification',
          status: 'verifying',
          stepId: 'step_8',
          title: 'Verification',
          details: 'All 67 tests passing. Lint and typechecks passed.',
          timestamp: new Date().toLocaleTimeString(),
          stepIndex: 7,
        });
      });

      schedule(9500, () => {
        onEvent({
          id: `ev_${Date.now()}_9`,
          taskId: 'task_demo_101',
          type: 'completed',
          status: 'completed',
          title: 'Task completed',
          details: 'Autonomous cycle verified and completed successfully.',
          timestamp: new Date().toLocaleTimeString(),
        });
        onFinish?.();
      });
    } else {
      // 'recovery' scenario:
      // Steps 1-6 succeed, Step 7 fails, followed by recovery loop 1/3, correction, and testing again!

      schedule(200, () => {
        onEvent({
          id: `ev_rec_${Date.now()}_1`,
          taskId: 'task_demo_101',
          type: 'task_received',
          status: 'task_received',
          stepId: 'step_1',
          title: 'Task received',
          details: 'Received user task: Fix authentication session timeout.',
          timestamp: new Date().toLocaleTimeString(),
          stepIndex: 0,
        });
      });

      schedule(1000, () => {
        onEvent({
          id: `ev_rec_${Date.now()}_2`,
          taskId: 'task_demo_101',
          type: 'planning',
          status: 'planning',
          stepId: 'step_2',
          title: 'Planning',
          details: 'Created plan with failure detection boundaries.',
          timestamp: new Date().toLocaleTimeString(),
          stepIndex: 1,
        });
      });

      schedule(2000, () => {
        onEvent({
          id: `ev_rec_${Date.now()}_3`,
          taskId: 'task_demo_101',
          type: 'researching',
          status: 'researching',
          stepId: 'step_3',
          title: 'Repository research',
          details: 'Identified dependencies across session and auth modules.',
          timestamp: new Date().toLocaleTimeString(),
          stepIndex: 2,
        });
      });

      schedule(2900, () => {
        onEvent({
          id: `ev_rec_${Date.now()}_4`,
          taskId: 'task_demo_101',
          type: 'files_found',
          status: 'files_found',
          stepId: 'step_4',
          title: 'Relevant files found',
          details: 'Found: src/harness/auth.py, tests/test_auth.py',
          relevantFiles: ['src/harness/auth.py', 'tests/test_auth.py'],
          timestamp: new Date().toLocaleTimeString(),
          stepIndex: 3,
        });
      });

      schedule(3800, () => {
        onEvent({
          id: `ev_rec_${Date.now()}_5`,
          taskId: 'task_demo_101',
          type: 'inspecting',
          status: 'inspecting',
          stepId: 'step_5',
          title: 'Inspecting code',
          details: 'Analyzing timeout handler at src/harness/auth.py:52.',
          relevantFiles: ['src/harness/auth.py'],
          timestamp: new Date().toLocaleTimeString(),
          stepIndex: 4,
        });
      });

      schedule(4800, () => {
        onEvent({
          id: `ev_rec_${Date.now()}_6`,
          taskId: 'task_demo_101',
          type: 'editing',
          status: 'editing',
          stepId: 'step_6',
          title: 'Editing',
          details: 'Initial modification applied to src/harness/auth.py.',
          timestamp: new Date().toLocaleTimeString(),
          stepIndex: 5,
        });
      });

      // Step 7: Tests failed!
      schedule(6000, () => {
        onEvent({
          id: `ev_rec_${Date.now()}_7`,
          taskId: 'task_demo_101',
          type: 'test_failed',
          status: 'failed',
          stepId: 'step_7',
          title: 'Tests failed',
          details: 'AssertionError: Expected timeout 60.0s but got 30.0s in test_session_expiry()',
          timestamp: new Date().toLocaleTimeString(),
          stepIndex: 6,
          payload: {
            error: 'AssertionError: Expected timeout 60.0s but got 30.0s',
            file: 'tests/test_auth.py:64',
          },
        });
      });

      // Step 8: Failure analysis
      schedule(7500, () => {
        onEvent({
          id: `ev_rec_${Date.now()}_8`,
          taskId: 'task_demo_101',
          type: 'failure_analysis',
          status: 'failure_analysis',
          title: 'Failure analysis',
          details: 'Analyzing traceback: Default timeout constant in session.py overrides auth parameter.',
          timestamp: new Date().toLocaleTimeString(),
          payload: {
            rootCause: 'Default timeout constant in session.py was not updated alongside auth.py',
          },
        });
      });

      // Step 9: Recovery attempt 1/3
      schedule(9000, () => {
        onEvent({
          id: `ev_rec_${Date.now()}_9`,
          taskId: 'task_demo_101',
          type: 'recovery_attempt',
          status: 'recovering',
          title: 'Recovery attempt 1/3',
          details: 'Formulating corrective action: Patch src/harness/session.py DEFAULT_TIMEOUT.',
          recoveryAttempt: 1,
          maxRecoveryAttempts: 3,
          timestamp: new Date().toLocaleTimeString(),
        });
      });

      // Step 10: Correction
      schedule(10500, () => {
        onEvent({
          id: `ev_rec_${Date.now()}_10`,
          taskId: 'task_demo_101',
          type: 'correction',
          status: 'editing',
          title: 'Correction',
          details: 'Applied corrective diff to src/harness/session.py (DEFAULT_TIMEOUT = 60.0).',
          relevantFiles: ['src/harness/session.py'],
          timestamp: new Date().toLocaleTimeString(),
        });
      });

      // Step 11: Testing again
      schedule(12000, () => {
        onEvent({
          id: `ev_rec_${Date.now()}_11`,
          taskId: 'task_demo_101',
          type: 'testing_again',
          status: 'testing',
          title: 'Testing again',
          details: 'Re-running pytest tests/test_auth.py via Controlled Shell Tool.',
          timestamp: new Date().toLocaleTimeString(),
        });
      });

      // Step 12: Verification passed
      schedule(13500, () => {
        onEvent({
          id: `ev_rec_${Date.now()}_12`,
          taskId: 'task_demo_101',
          type: 'verification',
          status: 'verifying',
          title: 'Verification',
          details: 'All tests passed (1 passed in 0.08s). 0 failures. Recovery 1/3 succeeded!',
          timestamp: new Date().toLocaleTimeString(),
        });
      });

      schedule(14800, () => {
        onEvent({
          id: `ev_rec_${Date.now()}_13`,
          taskId: 'task_demo_101',
          type: 'completed',
          status: 'completed',
          title: 'Task completed',
          details: 'Autonomous recovery loop completed with verified solution.',
          timestamp: new Date().toLocaleTimeString(),
        });
        onFinish?.();
      });
    }

    return () => {
      isCancelled = true;
      timeouts.forEach(clearTimeout);
    };
  }
}

export const agentStreamService = new MockAgentEventStream();
