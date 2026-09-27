/**
 * Chat API Service
 *
 * Implements the cross-platform Chat API contract.
 *
 * Eventual Architecture:
 * Client -> POST /chat -> Harness -> Orchestrator -> Agent -> Model Gateway
 *
 * CRITICAL ARCHITECTURAL CONSTRAINTS:
 * - NO hardcoded model provider (e.g. NVIDIA NIM, OpenAI, Anthropic) in the frontend.
 * - NO model logic on the client.
 * - The backend Harness orchestrates agents and interfaces with the Model Gateway.
 * - Agent events are emitted separately to power the Agent Activity UI.
 */

import {
  ChatMessage,
  ChatRequest,
  ChatResponse,
  Conversation,
} from '../types/chatContract';
import { AgentEvent } from '../types/agentContract';

export interface ChatApiService {
  /** Fetch all conversation sessions */
  getConversations(): Promise<Conversation[]>;

  /** Fetch a specific conversation with full message history */
  getConversation(id: string): Promise<Conversation | null>;

  /** Create a new conversation session for a new task */
  createConversation(title?: string): Promise<Conversation>;

  /** Send a user message and receive AI reasoning, code proposals, and agent events */
  sendMessage(request: ChatRequest): Promise<ChatResponse>;

  /** Regenerate the latest assistant response */
  regenerateMessage(conversationId: string): Promise<ChatResponse>;

  /** Retry a specific failed or cancelled message */
  retryMessage(conversationId: string, messageId: string): Promise<ChatResponse>;
}

// ============================================================================
// Concrete Implementation: MockChatApiService
// Provides realistic multi-agent execution responses adhering to the contract.
// ============================================================================

export class MockChatApiService implements ChatApiService {
  private conversations: Map<string, Conversation> = new Map();

  constructor() {
    // Seed default initial conversation
    const defaultConv: Conversation = {
      id: 'conv_default',
      title: 'Session Authentication & Timeout Fix',
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      messages: [
        {
          id: 'msg_welcome',
          role: 'assistant',
          content: `Welcome to the **AI Coding Harness**.

I can assist with repository understanding, bug fixes, features, and test-driven verification.

### Capabilities:
- **Repository Research**: AST symbol indexing, query-driven context selection
- **Multi-Agent Orchestration**: Planner, Coder, Critic, Verifier
- **Safe Execution**: Sandboxed filesystem and automated pytest verification

Enter a task below (e.g. *"Fix the authentication timeout"*) or start a **New Task**.`,
          timestamp: 'Just now',
          status: 'completed',
        },
      ],
    };
    this.conversations.set(defaultConv.id, defaultConv);
  }

  async getConversations(): Promise<Conversation[]> {
    return Array.from(this.conversations.values()).sort(
      (a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime()
    );
  }

  async getConversation(id: string): Promise<Conversation | null> {
    return this.conversations.get(id) || null;
  }

  async createConversation(title = 'New Task'): Promise<Conversation> {
    const newConv: Conversation = {
      id: `conv_${Date.now()}`,
      title,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      messages: [
        {
          id: `msg_welcome_${Date.now()}`,
          role: 'assistant',
          content: `Started **${title}**. What repository task or issue would you like me to tackle?`,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          status: 'completed',
        },
      ],
    };
    this.conversations.set(newConv.id, newConv);
    return newConv;
  }

  async sendMessage(request: ChatRequest): Promise<ChatResponse> {
    let conv = this.conversations.get(request.conversationId);
    if (!conv) {
      conv = await this.createConversation('Task');
      request.conversationId = conv.id;
    }

    // Add user message to conversation history
    const userMsg: ChatMessage = {
      id: `msg_user_${Date.now()}`,
      role: 'user',
      content: request.message,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      status: 'completed',
      attachments: request.attachments,
    };
    conv.messages.push(userMsg);
    conv.updatedAt = new Date().toISOString();

    // Auto-update conversation title on first user message if default
    if (conv.messages.filter((m) => m.role === 'user').length === 1) {
      conv.title = request.message.slice(0, 42) + (request.message.length > 42 ? '...' : '');
    }

    // Simulate backend response latency
    await new Promise((r) => setTimeout(r, 650));

    // Generate response text & agent events based on prompt
    const { responseContent, actions, referencedFiles, events } = this.generateResponse(
      request.message
    );

    const assistantMsg: ChatMessage = {
      id: `msg_assistant_${Date.now()}`,
      role: 'assistant',
      content: responseContent,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      status: 'completed',
      actions,
      referencedFiles,
    };

    conv.messages.push(assistantMsg);

    return {
      conversationId: conv.id,
      message: assistantMsg,
      agentEvents: events,
      finished: true,
    };
  }

  async regenerateMessage(conversationId: string): Promise<ChatResponse> {
    const conv = this.conversations.get(conversationId);
    if (!conv || conv.messages.length === 0) {
      throw new Error('No messages to regenerate in this conversation.');
    }

    // Pop the last assistant message if present
    if (conv.messages[conv.messages.length - 1].role === 'assistant') {
      conv.messages.pop();
    }

    // Find the last user message
    const lastUserMsg = [...conv.messages].reverse().find((m) => m.role === 'user');
    const prompt = lastUserMsg ? lastUserMsg.content : 'Continue previous task';

    await new Promise((r) => setTimeout(r, 600));

    const { responseContent, actions, referencedFiles, events } = this.generateResponse(prompt);

    const regeneratedMsg: ChatMessage = {
      id: `msg_assistant_regen_${Date.now()}`,
      role: 'assistant',
      content: responseContent,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      status: 'completed',
      actions,
      referencedFiles,
    };

    conv.messages.push(regeneratedMsg);
    conv.updatedAt = new Date().toISOString();

    return {
      conversationId: conv.id,
      message: regeneratedMsg,
      agentEvents: events,
      finished: true,
    };
  }

  async retryMessage(conversationId: string, _messageId: string): Promise<ChatResponse> {
    return this.regenerateMessage(conversationId);
  }

  /**
   * Generates realistic structured responses matching the Harness behavior
   */
  private generateResponse(prompt: string): {
    responseContent: string;
    actions: any[];
    referencedFiles: string[];
    events: AgentEvent[];
  } {
    const lower = prompt.toLowerCase();

    if (lower.includes('auth') || lower.includes('timeout') || lower.includes('session')) {
      const responseContent = `I'll inspect the authentication flow first.

### 1. Repository Intelligence Inspection
Using \`RepositoryContextManager\` and AST symbol indexing, I analyzed the authentication and session modules:
- \`src/auth/session.py\` (Class: \`SessionManager\`)
- \`tests/test_auth.py\` (Test: \`test_session_expiration\`)

### 2. Diagnosis & Root Cause
In \`SessionManager\`, the session expiration logic checked elapsed time against an overly strict or hardcoded threshold. Additionally, there was no safe \`refresh_session\` mechanism to extend active user sessions.

### 3. Proposed Fix
\`\`\`python
# src/auth/session.py
import time
from typing import Optional

class SessionManager:
    """Manages active user sessions with configurable timeout."""

    def __init__(self, session_timeout_seconds: int = 300) -> None:
        self.session_timeout_seconds = session_timeout_seconds
        self.active_sessions: dict = {}

    def is_session_valid(self, session_id: str, last_activity: float) -> bool:
        """Verify if session has exceeded expiration limit."""
        elapsed = time.time() - last_activity
        if elapsed > self.session_timeout_seconds:
            return False
        return True

    def refresh_session(self, session_id: str) -> bool:
        """Refresh expiration timestamp for an active session."""
        if session_id in self.active_sessions:
            self.active_sessions[session_id] = time.time()
            return True
        return False
\`\`\`

### 4. Verification
Executed test verification suite:
\`pytest tests/test_auth.py\`: **2 passed in 0.04s (100% verified)**.`;

      const actions = [
        {
          id: `act_${Date.now()}`,
          type: 'file_edit' as const,
          file: 'src/auth/session.py',
          summary: 'Parameterize session timeout and implement refresh_session()',
          diff: `--- a/src/auth/session.py\n+++ b/src/auth/session.py\n@@ -10,3 +10,8 @@\n-        self.session_timeout_seconds = 5\n+        self.session_timeout_seconds = session_timeout_seconds\n+    def refresh_session(self, session_id: str) -> bool:\n+        if session_id in self.active_sessions:\n+            self.active_sessions[session_id] = time.time()\n+            return True\n+        return False`,
          status: 'pending' as const,
        },
      ];

      const events: AgentEvent[] = [
        {
          id: `ev_${Date.now()}_1`,
          type: 'step_started',
          agentRole: 'orchestrator',
          title: 'Task initiated: Authentication timeout inspection',
          timestamp: new Date().toISOString(),
        },
        {
          id: `ev_${Date.now()}_2`,
          type: 'tool_call',
          agentRole: 'planner',
          title: 'RepositoryContextManager.find_relevant_context("authentication timeout")',
          details: 'Located src/auth/session.py (score: 0.95) and tests/test_auth.py (score: 0.88)',
          timestamp: new Date().toISOString(),
        },
        {
          id: `ev_${Date.now()}_3`,
          type: 'tool_call',
          agentRole: 'coder',
          title: 'FilesystemTool.edit_file("src/auth/session.py")',
          details: 'Updated session expiration check and added refresh_session()',
          timestamp: new Date().toISOString(),
        },
        {
          id: `ev_${Date.now()}_4`,
          type: 'step_completed',
          agentRole: 'verifier',
          title: 'TestsTool.run_tests("tests/test_auth.py")',
          details: 'All 2 unit tests passed cleanly in 0.04s',
          timestamp: new Date().toISOString(),
        },
      ];

      return {
        responseContent,
        actions,
        referencedFiles: ['src/auth/session.py', 'tests/test_auth.py'],
        events,
      };
    }

    if (lower.includes('test') || lower.includes('verify') || lower.includes('pytest')) {
      const responseContent = `I have executed the repository test verification suite.

### Verification Results
\`\`\`bash
============================= test session starts ==============================
platform darwin -- Python 3.14.2, pytest-9.1.1, pluggy-1.6.0
rootdir: /workspace/ai-coding-harness
collected 67 items

tests/test_agents.py .....                                               [  7%]
tests/test_context.py ..                                                 [ 10%]
tests/test_context_manager.py ..........                                 [ 25%]
tests/test_filesystem_tool.py ......                                     [ 34%]
tests/test_git_tool.py ...                                               [ 38%]
tests/test_indexer.py ...                                                [ 43%]
tests/test_mapper.py ...                                                 [ 47%]
tests/test_model_gateway.py ....                                         [ 53%]
tests/test_observability.py .....                                        [ 61%]
tests/test_orchestrator.py .....                                         [ 68%]
tests/test_orchestrator_integration.py .                                 [ 70%]
tests/test_search_tool.py .....                                          [ 77%]
tests/test_shell_tool.py .......                                         [ 88%]
tests/test_symbols.py ..                                                 [ 91%]
tests/test_tests_tool.py ....                                            [ 97%]
tests/test_tool_registry.py ..                                           [100%]

============================== 67 passed in 1.02s ==============================
\`\`\`

All 67 tests in the harness regression suite are passing cleanly.`;

      const events: AgentEvent[] = [
        {
          id: `ev_${Date.now()}`,
          type: 'step_completed',
          agentRole: 'verifier',
          title: 'Full pytest regression suite executed',
          details: '67 passed in 1.02s',
          timestamp: new Date().toISOString(),
        },
      ];

      return {
        responseContent,
        actions: [],
        referencedFiles: ['pyproject.toml', 'tests/test_orchestrator.py'],
        events,
      };
    }

    // Default response
    const responseContent = `I have received your request: **"${prompt}"**.

### Plan:
1. **Repository Search**: Scan indexed codebase files for relevant symbols and dependencies.
2. **Analysis**: Check AST symbol definitions and import graphs.
3. **Execution**: Formulate minimal code changes and apply verification.

Would you like me to inspect a specific file or run the test suite?`;

    const defaultEvents: AgentEvent[] = [
      {
        id: `ev_${Date.now()}`,
        type: 'step_started',
        agentRole: 'orchestrator',
        title: `Task initiated: ${prompt.slice(0, 30)}`,
        timestamp: new Date().toISOString(),
      },
    ];

    return {
      responseContent,
      actions: [],
      referencedFiles: [],
      events: defaultEvents,
    };
  }
}

export const chatApi: ChatApiService = new MockChatApiService();
