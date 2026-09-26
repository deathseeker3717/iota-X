import React, { useRef, useEffect, useState } from 'react';
import {
  Send,
  Square,
  RotateCcw,
  Sparkles,
  Bot,
  Zap,
  Plus,
  History,
  ChevronDown,
} from 'lucide-react';
import {
  ChatMessage,
  Conversation,
} from '../../types/chatContract';
import { Attachment } from '../../types/attachmentContract';
import { MessageItem } from './MessageItem';
import { FileAttachment } from './FileAttachment';

interface ChatPanelProps {
  conversations?: Conversation[];
  activeConversationId?: string;
  onSelectConversation?: (id: string) => void;
  onNewTask?: () => void;
  messages: ChatMessage[];
  isGenerating: boolean;
  onSendMessage: (text: string) => void;
  onClearChat: () => void;
  onStopGeneration: () => void;
  onRegenerate?: () => void;
  onRetry?: (messageId: string) => void;
  attachments: Attachment[];
  onAddAttachments: (files: FileList | File[]) => void;
  onRemoveAttachment: (id: string) => void;
  onOpenFile?: (path: string) => void;
}

export const ChatPanel: React.FC<ChatPanelProps> = ({
  conversations = [],
  activeConversationId,
  onSelectConversation,
  onNewTask,
  messages,
  isGenerating,
  onSendMessage,
  onClearChat,
  onStopGeneration,
  onRegenerate,
  onRetry,
  attachments,
  onAddAttachments,
  onRemoveAttachment,
  onOpenFile,
}) => {
  const [inputText, setInputText] = useState<string>('');
  const [showHistoryMenu, setShowHistoryMenu] = useState<boolean>(false);
  const [isDragOver, setIsDragOver] = useState<boolean>(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isGenerating]);

  const handleSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!inputText.trim() && attachments.length === 0) return;
    if (isGenerating) return;

    onSendMessage(inputText);
    setInputText('');
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const sampleTasks = [
    'Fix the authentication timeout',
    'Run full pytest verification suite',
    'Find everything related to authentication',
  ];

  // Find index of the latest assistant message to attach regenerate button
  const latestAssistantIndex = messages.map((m) => m.role).lastIndexOf('assistant');

  const activeConv = conversations.find((c) => c.id === activeConversationId);

  return (
    <div className="h-full flex flex-col bg-harness-surface select-none">
      {/* 1. Chat Header Bar with New Task and History dropdown */}
      <div className="h-9 px-3 flex items-center justify-between border-b border-harness-border/60 bg-harness-surface z-10">
        <div className="flex items-center space-x-2">
          <Sparkles className="w-3.5 h-3.5 text-sky-400" />
          <span className="text-[11px] font-bold uppercase tracking-wider text-gray-400">
            AI Assistant
          </span>
        </div>

        {/* Action Controls */}
        <div className="flex items-center space-x-1.5">
          {/* New Task Button */}
          {onNewTask && (
            <button
              onClick={onNewTask}
              className="flex items-center space-x-1 px-2 py-0.5 bg-sky-600/20 hover:bg-sky-600/30 text-sky-300 border border-sky-500/30 rounded text-[11px] font-medium transition active:scale-95"
              title="Start a fresh task session"
            >
              <Plus className="w-3 h-3" />
              <span>New Task</span>
            </button>
          )}

          {/* Conversation History Dropdown */}
          {conversations.length > 0 && onSelectConversation && (
            <div className="relative">
              <button
                onClick={() => setShowHistoryMenu(!showHistoryMenu)}
                className="flex items-center space-x-1 p-1 hover:text-white rounded hover:bg-harness-panel text-gray-400 transition"
                title="Task History"
              >
                <History className="w-3.5 h-3.5" />
                <ChevronDown className="w-3 h-3" />
              </button>

              {showHistoryMenu && (
                <div className="absolute right-0 top-8 w-60 bg-harness-surface border border-harness-border rounded-lg shadow-xl py-1 z-30 text-xs">
                  <div className="px-3 py-1.5 text-[10px] font-bold uppercase tracking-wider text-gray-500 border-b border-harness-border/60">
                    Recent Tasks
                  </div>
                  {conversations.map((conv) => (
                    <button
                      key={conv.id}
                      onClick={() => {
                        onSelectConversation(conv.id);
                        setShowHistoryMenu(false);
                      }}
                      className={`w-full text-left px-3 py-1.5 flex flex-col hover:bg-harness-panel transition ${
                        conv.id === activeConversationId
                          ? 'bg-sky-500/15 text-sky-200 font-medium'
                          : 'text-gray-300'
                      }`}
                    >
                      <span className="truncate">{conv.title}</span>
                      <span className="text-[10px] text-gray-500 font-mono">
                        {conv.messages.length} messages
                      </span>
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* 2. Messages Feed */}
      <div className="flex-1 overflow-y-auto p-3 space-y-3.5 select-text">
        {messages.map((msg, idx) => (
          <MessageItem
            key={msg.id}
            message={msg}
            onOpenFile={onOpenFile}
            onRegenerate={idx === latestAssistantIndex ? onRegenerate : undefined}
            onRetry={onRetry ? () => onRetry(msg.id) : undefined}
            isLatestAssistant={idx === latestAssistantIndex}
          />
        ))}

        {/* Loading State: Autonomous Orchestrator Progress */}
        {isGenerating && (
          <div className="p-3 bg-harness-surface border border-sky-500/30 rounded-xl mr-4 flex items-center justify-between text-xs text-sky-300 shadow-sm animate-pulse">
            <div className="flex items-center space-x-2.5">
              <Bot className="w-4 h-4 text-sky-400" />
              <span>Orchestrator reasoning & executing task tools...</span>
            </div>
            <button
              onClick={onStopGeneration}
              className="flex items-center space-x-1 px-2 py-0.5 bg-rose-600/30 hover:bg-rose-600/50 text-rose-200 border border-rose-500/40 rounded text-[11px] font-medium transition"
              title="Stop Generation"
            >
              <Square className="w-2.5 h-2.5 fill-rose-300" />
              <span>Stop</span>
            </button>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* 3. Quick Prompt Suggestions */}
      {messages.length <= 1 && (
        <div className="px-3 pb-2 flex flex-wrap gap-1.5 select-none">
          {sampleTasks.map((task, idx) => (
            <button
              key={idx}
              onClick={() => onSendMessage(task)}
              className="text-[11px] px-2.5 py-1 bg-harness-panel hover:bg-harness-border/70 border border-harness-border text-gray-300 rounded-full transition text-left flex items-center space-x-1"
            >
              <Zap className="w-3 h-3 text-amber-400" />
              <span>{task}</span>
            </button>
          ))}
        </div>
      )}

      {/* 4. Message Composer */}
      <div className="p-3 border-t border-harness-border/60 bg-harness-surface select-none">
        <form
          onSubmit={handleSubmit}
          onDragOver={(e) => {
            e.preventDefault();
            setIsDragOver(true);
          }}
          onDragLeave={(e) => {
            e.preventDefault();
            setIsDragOver(false);
          }}
          onDrop={(e) => {
            e.preventDefault();
            setIsDragOver(false);
            if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
              onAddAttachments(e.dataTransfer.files);
            }
          }}
          className={`relative flex flex-col bg-harness-bg border rounded-xl focus-within:border-sky-500 transition shadow-inner ${
            isDragOver ? 'border-sky-400 bg-sky-950/20' : 'border-harness-border'
          }`}
        >
          <textarea
            ref={textareaRef}
            rows={2}
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask AI Coding Harness to plan, code, or verify... (Enter to send, Shift+Enter for new line)"
            className="w-full p-2.5 bg-transparent text-xs text-gray-100 placeholder-gray-500 focus:outline-none resize-none leading-relaxed select-text"
          />

          <div className="flex items-center justify-between px-2.5 pb-2">
            {/* Attachment Button & File Chips */}
            <FileAttachment
              attachments={attachments}
              onAddFiles={onAddAttachments}
              onRemoveFile={onRemoveAttachment}
              isDragActive={isDragOver}
            />

            <div className="flex items-center space-x-1.5">
              {isGenerating ? (
                <button
                  type="button"
                  onClick={onStopGeneration}
                  className="flex items-center space-x-1 px-2.5 py-1 bg-rose-600/30 hover:bg-rose-600/50 text-rose-200 border border-rose-500/40 rounded-lg text-xs font-medium transition"
                  title="Stop Generation"
                >
                  <Square className="w-3 h-3 fill-rose-300" />
                  <span>Stop</span>
                </button>
              ) : (
                <button
                  type="submit"
                  disabled={!inputText.trim() && attachments.length === 0}
                  className="flex items-center space-x-1 px-3 py-1.5 bg-sky-600 hover:bg-sky-500 disabled:opacity-40 disabled:hover:bg-sky-600 text-white rounded-lg text-xs font-medium transition active:scale-95 shadow"
                >
                  <span>Send</span>
                  <Send className="w-3 h-3" />
                </button>
              )}
            </div>
          </div>
        </form>
      </div>
    </div>
  );
};
