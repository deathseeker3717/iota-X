import React, { useState } from 'react';
import {
  Copy,
  Check,
  Cpu,
  User,
  FileText,
  RotateCcw,
  AlertCircle,
  ExternalLink,
} from 'lucide-react';
import { ChatMessage } from '../../types/chatContract';
import { ActionCard } from './ActionCard';

interface MessageItemProps {
  message: ChatMessage;
  onOpenFile?: (path: string) => void;
  onRegenerate?: () => void;
  onRetry?: () => void;
  isLatestAssistant?: boolean;
}

export const MessageItem: React.FC<MessageItemProps> = ({
  message,
  onOpenFile,
  onRegenerate,
  onRetry,
  isLatestAssistant = false,
}) => {
  const isUser = message.role === 'user';
  const isFailed = message.status === 'failed';
  const [copiedCodeIndex, setCopiedCodeIndex] = useState<number | null>(null);
  const [copiedMessage, setCopiedMessage] = useState<boolean>(false);

  const handleCopyCode = (text: string, index: number) => {
    navigator.clipboard.writeText(text);
    setCopiedCodeIndex(index);
    setTimeout(() => setCopiedCodeIndex(null), 2000);
  };

  const handleCopyMessage = () => {
    navigator.clipboard.writeText(message.content);
    setCopiedMessage(true);
    setTimeout(() => setCopiedMessage(false), 2000);
  };

  // Markdown formatter supporting headers, lists, blockquotes, and code blocks
  const renderFormattedContent = (content: string) => {
    const parts = content.split(/(```[\s\S]*?```)/g);

    return parts.map((part, idx) => {
      // Code block
      if (part.startsWith('```') && part.endsWith('```')) {
        const lines = part.slice(3, -3).trim().split('\n');
        const lang = lines[0].trim() || 'code';
        const codeText = lines.slice(1).join('\n') || lines[0];

        return (
          <div
            key={idx}
            className="my-2.5 rounded-lg border border-harness-border overflow-hidden bg-harness-bg shadow-xs"
          >
            <div className="flex items-center justify-between px-3 py-1.5 bg-harness-panel/80 border-b border-harness-border/70 text-[11px] font-mono text-gray-400 select-none">
              <span className="font-semibold text-gray-300 capitalize">{lang}</span>
              <button
                onClick={() => handleCopyCode(codeText, idx)}
                className="flex items-center space-x-1 text-gray-400 hover:text-white transition px-1.5 py-0.5 rounded hover:bg-harness-border/50"
                title="Copy code"
              >
                {copiedCodeIndex === idx ? (
                  <>
                    <Check className="w-3 h-3 text-emerald-400" />
                    <span className="text-emerald-400">Copied!</span>
                  </>
                ) : (
                  <>
                    <Copy className="w-3 h-3" />
                    <span>Copy code</span>
                  </>
                )}
              </button>
            </div>
            <pre className="p-3 font-mono text-xs overflow-x-auto text-gray-200 leading-relaxed">
              <code>{codeText}</code>
            </pre>
          </div>
        );
      }

      // Regular text parsing: lines
      const paragraphs = part.split('\n');
      return (
        <div key={idx} className="space-y-1.5">
          {paragraphs.map((p, pIdx) => {
            if (!p.trim()) return <div key={pIdx} className="h-1" />;

            // Header 3
            if (p.startsWith('### ')) {
              return (
                <h4
                  key={pIdx}
                  className="font-bold text-gray-100 text-xs mt-3 mb-1 tracking-tight flex items-center space-x-1"
                >
                  <span>{p.replace('### ', '')}</span>
                </h4>
              );
            }

            // Header 2
            if (p.startsWith('## ')) {
              return (
                <h3 key={pIdx} className="font-bold text-gray-100 text-sm mt-3 mb-1">
                  {p.replace('## ', '')}
                </h3>
              );
            }

            // Bullet list item
            if (p.startsWith('- ') || p.startsWith('* ')) {
              return (
                <div key={pIdx} className="flex items-start space-x-1.5 text-xs text-gray-300 pl-2">
                  <span className="text-sky-400 font-bold">•</span>
                  <span>{formatInline(p.slice(2))}</span>
                </div>
              );
            }

            // Numbered list item
            if (/^\d+\.\s/.test(p)) {
              const num = p.match(/^(\d+\.)\s/)?.[1] || '1.';
              const rest = p.replace(/^\d+\.\s/, '');
              return (
                <div key={pIdx} className="flex items-start space-x-1.5 text-xs text-gray-300 pl-2">
                  <span className="text-sky-400 font-mono text-[11px] shrink-0">{num}</span>
                  <span>{formatInline(rest)}</span>
                </div>
              );
            }

            // Blockquote
            if (p.startsWith('> ')) {
              return (
                <div
                  key={pIdx}
                  className="border-l-2 border-sky-500/60 pl-2.5 py-0.5 text-xs text-gray-400 italic bg-sky-500/5 my-1 rounded-r"
                >
                  {formatInline(p.slice(2))}
                </div>
              );
            }

            return (
              <p key={pIdx} className="text-xs text-gray-200 leading-relaxed">
                {formatInline(p)}
              </p>
            );
          })}
        </div>
      );
    });
  };

  // Inline formatting for **bold**, *italics*, and `code`
  const formatInline = (text: string) => {
    const inlineTokens = text.split(/(`[^`]+`|\*\*[^*]+\*\*|\*[^*]+\*)/g);

    return inlineTokens.map((token, tIdx) => {
      if (token.startsWith('`') && token.endsWith('`')) {
        const snippet = token.slice(1, -1);
        const isFileRef = snippet.includes('.') || snippet.includes('/');

        return (
          <span
            key={tIdx}
            onClick={() => isFileRef && onOpenFile?.(snippet)}
            className={`font-mono text-[11px] px-1.5 py-0.5 rounded bg-harness-panel border border-harness-border/60 ${
              isFileRef
                ? 'text-sky-300 hover:text-sky-200 hover:underline cursor-pointer inline-flex items-center space-x-0.5'
                : 'text-amber-200'
            }`}
          >
            <span>{snippet}</span>
            {isFileRef && <ExternalLink className="w-2.5 h-2.5 ml-0.5 inline opacity-70" />}
          </span>
        );
      }

      if (token.startsWith('**') && token.endsWith('**')) {
        return (
          <strong key={tIdx} className="font-semibold text-gray-100">
            {token.slice(2, -2)}
          </strong>
        );
      }

      if (token.startsWith('*') && token.endsWith('*')) {
        return (
          <em key={tIdx} className="italic text-gray-300">
            {token.slice(1, -1)}
          </em>
        );
      }

      return token;
    });
  };

  return (
    <div
      className={`p-3.5 rounded-xl text-xs transition relative group ${
        isUser
          ? 'bg-harness-panel/50 border border-harness-border/60 ml-4'
          : isFailed
          ? 'bg-rose-950/20 border border-rose-500/40 mr-2 shadow-sm'
          : 'bg-harness-surface border border-harness-border mr-2 shadow-xs'
      }`}
    >
      {/* Sender Header */}
      <div className="flex items-center justify-between mb-2 select-none">
        <div className="flex items-center space-x-2">
          {isUser ? (
            <div className="w-5 h-5 rounded-full bg-emerald-600/30 border border-emerald-500/40 flex items-center justify-center text-emerald-300">
              <User className="w-3 h-3" />
            </div>
          ) : (
            <div className="w-5 h-5 rounded-full bg-sky-600/30 border border-sky-500/40 flex items-center justify-center text-sky-300">
              <Cpu className="w-3 h-3" />
            </div>
          )}
          <span className="font-semibold text-gray-200 text-xs">
            {isUser ? 'You' : 'AI Coding Harness'}
          </span>
        </div>

        <div className="flex items-center space-x-2 text-[10px] text-gray-500">
          <span>{message.timestamp}</span>

          {/* Quick Copy message action */}
          <button
            onClick={handleCopyMessage}
            className="p-1 hover:text-white rounded hover:bg-harness-panel opacity-0 group-hover:opacity-100 transition"
            title="Copy message"
          >
            {copiedMessage ? (
              <Check className="w-3 h-3 text-emerald-400" />
            ) : (
              <Copy className="w-3 h-3" />
            )}
          </button>
        </div>
      </div>

      {/* Attachments preview */}
      {message.attachments && message.attachments.length > 0 && (
        <div className="mb-2.5 flex flex-wrap gap-1.5 select-none">
          {message.attachments.map((att) => (
            <div
              key={att.id}
              className="flex items-center space-x-1 bg-harness-bg border border-harness-border px-2 py-0.5 rounded text-[11px] text-gray-300"
            >
              <FileText className="w-3 h-3 text-sky-400" />
              <span>{att.name}</span>
            </div>
          ))}
        </div>
      )}

      {/* Message Body */}
      <div className="select-text">{renderFormattedContent(message.content)}</div>

      {/* Error / Retry Bar */}
      {isFailed && (
        <div className="mt-3 p-2 bg-rose-900/30 border border-rose-500/40 rounded-lg flex items-center justify-between text-xs text-rose-300">
          <div className="flex items-center space-x-1.5">
            <AlertCircle className="w-3.5 h-3.5 text-rose-400 shrink-0" />
            <span>Generation encountered an error.</span>
          </div>
          {onRetry && (
            <button
              onClick={onRetry}
              className="flex items-center space-x-1 px-2 py-0.5 bg-rose-600 hover:bg-rose-500 text-white rounded text-[11px] font-medium transition"
            >
              <RotateCcw className="w-3 h-3" />
              <span>Retry</span>
            </button>
          )}
        </div>
      )}

      {/* AI Code Actions (if any) */}
      {message.actions && message.actions.length > 0 && (
        <div className="mt-3 space-y-2 select-none">
          {message.actions.map((act) => (
            <ActionCard key={act.id} action={act} onViewFile={onOpenFile} />
          ))}
        </div>
      )}

      {/* Footer Actions for Latest Assistant Message: Regenerate */}
      {!isUser && !isFailed && isLatestAssistant && onRegenerate && (
        <div className="mt-2.5 pt-2 border-t border-harness-border/40 flex items-center justify-end select-none">
          <button
            onClick={onRegenerate}
            className="flex items-center space-x-1 text-[11px] text-gray-400 hover:text-sky-300 hover:bg-harness-panel px-2 py-0.5 rounded transition"
            title="Regenerate response from model"
          >
            <RotateCcw className="w-3 h-3" />
            <span>Regenerate</span>
          </button>
        </div>
      )}
    </div>
  );
};
