/**
 * AI Chat State Management Hook
 *
 * Implements the cross-platform chat lifecycle:
 * - Conversation management & New Task creation
 * - Multi-turn user & assistant message exchange
 * - Markdown, code blocks, retry & regenerate operations
 * - Decoupled AgentEvent propagation (agent activity supported separately)
 */

import { useCallback, useEffect, useState } from 'react';
import {
  AgentEvent,
  ChatMessage,
  ChatRequestContext,
  Conversation,
} from '../types/chatContract';
import { Attachment } from '../types/attachmentContract';
import { chatApi } from '../services/chatApi';
import { uploadApi } from '../services/uploadApi';

interface UseChatProps {
  onAgentEvents?: (events: AgentEvent[]) => void;
  context?: ChatRequestContext;
}

export function useChat({ onAgentEvents, context }: UseChatProps = {}) {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<string>('conv_default');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isGenerating, setIsGenerating] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [attachments, setAttachments] = useState<Attachment[]>([]);

  // Load conversation list and active conversation on mount
  useEffect(() => {
    async function loadConversations() {
      try {
        const list = await chatApi.getConversations();
        setConversations(list);
        if (list.length > 0) {
          const current = list[0];
          setActiveConversationId(current.id);
          setMessages(current.messages);
        }
      } catch (err) {
        console.error('Failed to load conversations:', err);
      }
    }
    loadConversations();
  }, []);

  // Switch active conversation
  const selectConversation = useCallback(async (id: string) => {
    try {
      const conv = await chatApi.getConversation(id);
      if (conv) {
        setActiveConversationId(conv.id);
        setMessages(conv.messages);
        setError(null);
      }
    } catch (err) {
      console.error(`Failed to load conversation ${id}:`, err);
    }
  }, []);

  // Create New Task
  const startNewTask = useCallback(async (title = 'New Task') => {
    try {
      setIsGenerating(false);
      setError(null);
      const newConv = await chatApi.createConversation(title);
      setConversations((prev) => [newConv, ...prev.filter((c) => c.id !== newConv.id)]);
      setActiveConversationId(newConv.id);
      setMessages(newConv.messages);
      setAttachments([]);
    } catch (err) {
      console.error('Failed to start new task:', err);
    }
  }, []);

  // Send message
  const sendMessage = useCallback(
    async (text: string) => {
      if (!text.trim() && attachments.length === 0) return;
      if (isGenerating) return;

      const currentConvId = activeConversationId || 'conv_default';

      // Optimistic user message insertion
      const userMessage: ChatMessage = {
        id: `msg_user_${Date.now()}`,
        role: 'user',
        content: text,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        status: 'completed',
        attachments: [...attachments],
      };

      setMessages((prev) => [...prev, userMessage]);
      setAttachments([]);
      setIsGenerating(true);
      setError(null);

      try {
        const response = await chatApi.sendMessage({
          conversationId: currentConvId,
          message: text,
          attachments: userMessage.attachments,
          context,
        });

        // Append assistant message
        setMessages((prev) => [...prev, response.message]);

        // Propagate agent events separately to update agent activity UI
        if (response.agentEvents && response.agentEvents.length > 0 && onAgentEvents) {
          onAgentEvents(response.agentEvents);
        }

        // Update conversations list title/updatedAt
        const updatedList = await chatApi.getConversations();
        setConversations(updatedList);
      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : 'Failed to generate response';
        setError(errorMsg);
        setMessages((prev) => [
          ...prev,
          {
            id: `msg_err_${Date.now()}`,
            role: 'assistant',
            content: `**Error**: ${errorMsg}. Please try again.`,
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            status: 'failed',
            error: errorMsg,
          },
        ]);
      } finally {
        setIsGenerating(false);
      }
    },
    [activeConversationId, attachments, context, isGenerating, onAgentEvents]
  );

  // Regenerate latest response
  const regenerateLastMessage = useCallback(async () => {
    if (isGenerating || !activeConversationId) return;

    setIsGenerating(true);
    setError(null);

    // Remove last assistant message from display
    setMessages((prev) => {
      if (prev.length > 0 && prev[prev.length - 1].role === 'assistant') {
        return prev.slice(0, -1);
      }
      return prev;
    });

    try {
      const response = await chatApi.regenerateMessage(activeConversationId);
      setMessages((prev) => [...prev, response.message]);

      if (response.agentEvents && response.agentEvents.length > 0 && onAgentEvents) {
        onAgentEvents(response.agentEvents);
      }
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Regeneration failed';
      setError(errorMsg);
    } finally {
      setIsGenerating(false);
    }
  }, [activeConversationId, isGenerating, onAgentEvents]);

  // Retry message
  const retryMessage = useCallback(
    async (messageId: string) => {
      if (isGenerating || !activeConversationId) return;
      setIsGenerating(true);
      setError(null);

      try {
        const response = await chatApi.retryMessage(activeConversationId, messageId);
        setMessages((prev) => {
          const filtered = prev.filter((m) => m.id !== messageId);
          return [...filtered, response.message];
        });

        if (response.agentEvents && response.agentEvents.length > 0 && onAgentEvents) {
          onAgentEvents(response.agentEvents);
        }
      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : 'Retry failed';
        setError(errorMsg);
      } finally {
        setIsGenerating(false);
      }
    },
    [activeConversationId, isGenerating, onAgentEvents]
  );

  // Stop Generation
  const stopGeneration = useCallback(() => {
    setIsGenerating(false);
  }, []);

  // Clear Chat / Messages
  const clearChat = useCallback(() => {
    setMessages([]);
  }, []);

  // Attachments Handling via uploadApi
  const addAttachments = useCallback(async (files: FileList | File[]) => {
    const fileList = Array.from(files);

    for (const f of fileList) {
      const tempId = `att_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`;
      const initialItem: Attachment = {
        id: tempId,
        name: f.name,
        size: f.size,
        type: f.type || 'text/plain',
        status: 'uploading',
        progress: 10,
      };

      setAttachments((prev) => [...prev, initialItem]);

      try {
        const result = await uploadApi.uploadFile({
          file: f,
          filename: f.name,
          mimeType: f.type || 'text/plain',
          size: f.size,
          onProgress: (pct) => {
            setAttachments((prev) =>
              prev.map((item) => (item.id === tempId ? { ...item, progress: pct } : item))
            );
          },
        });

        if (result.success) {
          setAttachments((prev) =>
            prev.map((item) => (item.id === tempId ? result.attachment : item))
          );
        } else {
          setAttachments((prev) =>
            prev.map((item) =>
              item.id === tempId
                ? { ...item, status: 'error', error: result.error || 'Upload failed' }
                : item
            )
          );
        }
      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : 'Upload failed';
        setAttachments((prev) =>
          prev.map((item) =>
            item.id === tempId ? { ...item, status: 'error', error: errorMsg } : item
          )
        );
      }
    }
  }, []);

  const removeAttachment = useCallback(async (id: string) => {
    setAttachments((prev) => prev.filter((a) => a.id !== id));
    try {
      await uploadApi.deleteAttachment(id);
    } catch {
      // ignore
    }
  }, []);

  return {
    conversations,
    activeConversationId,
    selectConversation,
    startNewTask,
    messages,
    isGenerating,
    error,
    sendMessage,
    regenerateLastMessage,
    retryMessage,
    stopGeneration,
    clearChat,
    attachments,
    addAttachments,
    removeAttachment,
  };
}
