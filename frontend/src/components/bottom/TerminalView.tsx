import React, { useState, useRef, useEffect } from 'react';
import {
  Terminal as TerminalIcon,
  Trash2,
  Play,
  CheckCircle2,
  AlertCircle,
  Copy,
  Check,
  StopCircle,
  Loader2,
  Shield,
} from 'lucide-react';
import { TerminalOutput } from '../../types/terminalContract';

interface TerminalViewProps {
  history: TerminalOutput[];
  onRunCommand: (command: string) => void;
  onClear: () => void;
  isExecuting?: boolean;
  onCancelCommand?: () => void;
}

export const TerminalView: React.FC<TerminalViewProps> = ({
  history,
  onRunCommand,
  onClear,
  isExecuting = false,
  onCancelCommand,
}) => {
  const [cmdInput, setCmdInput] = useState<string>('');
  const [historyIndex, setHistoryIndex] = useState<number>(-1);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Auto-scroll to bottom on new output or state change
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [history, isExecuting]);

  // Extract commands history for ArrowUp / ArrowDown navigation
  const previousCommands = history
    .map((h) => h.command)
    .filter((c, i, arr) => arr.indexOf(c) === i);

  const handleSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!cmdInput.trim() || isExecuting) return;

    onRunCommand(cmdInput.trim());
    setCmdInput('');
    setHistoryIndex(-1);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'ArrowUp') {
      e.preventDefault();
      if (previousCommands.length === 0) return;
      const nextIndex =
        historyIndex === -1
          ? previousCommands.length - 1
          : Math.max(0, historyIndex - 1);
      setHistoryIndex(nextIndex);
      setCmdInput(previousCommands[nextIndex]);
    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      if (historyIndex === -1) return;
      if (historyIndex >= previousCommands.length - 1) {
        setHistoryIndex(-1);
        setCmdInput('');
      } else {
        const nextIndex = historyIndex + 1;
        setHistoryIndex(nextIndex);
        setCmdInput(previousCommands[nextIndex]);
      }
    }
  };

  const handleCopy = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 1800);
  };

  const sampleCommands = [
    'pytest',
    'git status',
    'git diff',
    'python -m harness.main',
  ];

  return (
    <div className="h-full flex flex-col bg-[#0b0e14] font-mono text-xs select-text">
      {/* 1. Terminal Header Toolbar */}
      <div className="h-7 px-3 bg-harness-surface/70 border-b border-harness-border/50 flex items-center justify-between text-[11px] text-gray-400 select-none">
        <div className="flex items-center space-x-2">
          <TerminalIcon className="w-3.5 h-3.5 text-sky-400" />
          <span className="font-semibold text-gray-300">zsh — controlled-shell</span>
          <div className="flex items-center space-x-1 text-[10px] text-emerald-400/90 bg-emerald-500/10 px-1.5 py-0.2 rounded border border-emerald-500/20">
            <Shield className="w-2.5 h-2.5" />
            <span>sandboxed</span>
          </div>
        </div>

        {/* Quick shortcut commands */}
        <div className="flex items-center space-x-2">
          <span className="text-[10px] text-gray-600">Quick:</span>
          {sampleCommands.map((sc, idx) => (
            <button
              key={idx}
              disabled={isExecuting}
              onClick={() => onRunCommand(sc)}
              className="text-[10px] text-gray-400 hover:text-sky-300 disabled:opacity-40 transition font-mono"
            >
              ${sc}
            </button>
          ))}

          <span className="text-gray-700">|</span>

          {/* Clear Button */}
          <button
            onClick={onClear}
            className="p-1 text-gray-400 hover:text-white transition"
            title="Clear Terminal Output"
          >
            <Trash2 className="w-3 h-3" />
          </button>
        </div>
      </div>

      {/* 2. Output Log Feed */}
      <div className="flex-1 overflow-y-auto p-3.5 space-y-4">
        {history.map((item) => {
          const isRunning = item.status === 'running';
          const isSuccess = item.status === 'success';
          const isFailed = item.status === 'failed';

          return (
            <div key={item.id} className="space-y-1.5 group">
              {/* Command Line Header */}
              <div className="flex items-center justify-between text-[11px] select-none">
                <div className="flex items-center space-x-2 font-semibold">
                  <span className="text-emerald-400">$</span>
                  <span className="text-gray-100">{item.command}</span>
                </div>

                <div className="flex items-center space-x-2 text-[10px]">
                  {/* Duration */}
                  {item.durationSeconds > 0 && (
                    <span className="text-gray-500 font-mono">
                      {item.durationSeconds}s
                    </span>
                  )}

                  {/* Status Badge */}
                  {isRunning ? (
                    <span className="flex items-center space-x-1 text-sky-400 bg-sky-500/10 px-1.5 py-0.5 rounded border border-sky-500/30 animate-pulse">
                      <Loader2 className="w-2.5 h-2.5 animate-spin" />
                      <span>RUNNING</span>
                    </span>
                  ) : isSuccess ? (
                    <span className="flex items-center space-x-1 text-emerald-400 bg-emerald-500/10 px-1.5 py-0.5 rounded border border-emerald-500/30">
                      <CheckCircle2 className="w-2.5 h-2.5" />
                      <span>SUCCESS</span>
                    </span>
                  ) : (
                    <span className="flex items-center space-x-1 text-rose-400 bg-rose-500/10 px-1.5 py-0.5 rounded border border-rose-500/30">
                      <AlertCircle className="w-2.5 h-2.5" />
                      <span>FAILED</span>
                    </span>
                  )}

                  {/* Copy Output Button */}
                  <button
                    onClick={() => handleCopy(item.stdout || item.stderr, item.id)}
                    className="p-0.5 text-gray-500 hover:text-gray-200 rounded opacity-0 group-hover:opacity-100 transition"
                    title="Copy command output"
                  >
                    {copiedId === item.id ? (
                      <Check className="w-3 h-3 text-emerald-400" />
                    ) : (
                      <Copy className="w-3 h-3" />
                    )}
                  </button>
                </div>
              </div>

              {/* Stdout Output Stream */}
              {item.stdout && (
                <pre className="text-gray-300 whitespace-pre-wrap leading-relaxed text-[11.5px] pl-3 py-1 font-mono">
                  {item.stdout}
                </pre>
              )}

              {/* Stderr Output Stream */}
              {item.stderr && (
                <pre className="text-rose-400 whitespace-pre-wrap leading-relaxed text-[11.5px] pl-3 py-1 font-mono bg-rose-950/20 rounded border border-rose-500/30">
                  {item.stderr}
                </pre>
              )}

              {/* Exit Code Summary */}
              {!isRunning && item.exitCode !== null && (
                <div
                  className={`text-[11px] pl-3 font-mono select-none pt-0.5 ${
                    item.exitCode === 0 ? 'text-gray-500' : 'text-rose-400 font-semibold'
                  }`}
                >
                  Process exited with code {item.exitCode}
                </div>
              )}

              {/* Running State Spinner */}
              {isRunning && (
                <div className="pl-3 py-1 text-[11px] text-sky-400 flex items-center space-x-2 select-none">
                  <Loader2 className="w-3 h-3 animate-spin" />
                  <span>Executing in controlled backend sandbox...</span>
                </div>
              )}
            </div>
          );
        })}

        <div ref={bottomRef} />
      </div>

      {/* 3. Interactive Input Prompt */}
      <form
        onSubmit={handleSubmit}
        className="h-9 border-t border-harness-border/50 bg-[#0e121a] px-3 flex items-center space-x-2 select-none"
      >
        <span className="text-emerald-400 font-bold select-none">$</span>
        <input
          ref={inputRef}
          type="text"
          value={cmdInput}
          onChange={(e) => setCmdInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isExecuting}
          placeholder={
            isExecuting
              ? 'Command running in sandbox...'
              : "Run controlled bash command (e.g., 'pytest', 'git status', 'python -m harness.main')..."
          }
          className="flex-1 bg-transparent text-gray-200 text-xs focus:outline-none font-mono disabled:opacity-50 select-text"
        />

        {isExecuting ? (
          <button
            type="button"
            onClick={onCancelCommand}
            className="flex items-center space-x-1 px-2 py-0.5 bg-rose-600/30 hover:bg-rose-600/50 text-rose-200 border border-rose-500/40 rounded text-[11px] font-medium transition select-none"
            title="Cancel command (SIGINT)"
          >
            <StopCircle className="w-3 h-3 fill-rose-300" />
            <span>Stop</span>
          </button>
        ) : (
          <button
            type="submit"
            disabled={!cmdInput.trim()}
            className="text-gray-400 hover:text-sky-300 disabled:opacity-30 p-1 rounded transition select-none"
            title="Execute (Enter)"
          >
            <Play className="w-3.5 h-3.5" />
          </button>
        )}
      </form>
    </div>
  );
};
