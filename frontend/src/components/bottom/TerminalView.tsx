import React, { useState, useRef, useEffect } from 'react';
import { Terminal as TerminalIcon, Trash2, Play, CheckCircle2, AlertCircle } from 'lucide-react';
import { TerminalOutput } from '../../types';

interface TerminalViewProps {
  history: TerminalOutput[];
  onRunCommand: (command: string) => void;
  onClear: () => void;
}

export const TerminalView: React.FC<TerminalViewProps> = ({
  history,
  onRunCommand,
  onClear,
}) => {
  const [cmdInput, setCmdInput] = useState<string>('');
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [history]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!cmdInput.trim()) return;
    onRunCommand(cmdInput.trim());
    setCmdInput('');
  };

  const sampleCommands = ['pytest tests', 'git status', 'python -m harness.main'];

  return (
    <div className="h-full flex flex-col bg-[#0b0e14] font-mono text-xs select-text">
      {/* Terminal Toolbar */}
      <div className="h-7 px-3 bg-harness-surface/60 border-b border-harness-border/40 flex items-center justify-between text-[11px] text-gray-400 select-none">
        <div className="flex items-center space-x-2">
          <TerminalIcon className="w-3.5 h-3.5 text-sky-400" />
          <span>zsh — harness-sandbox</span>
        </div>

        <div className="flex items-center space-x-2">
          {sampleCommands.map((sc, idx) => (
            <button
              key={idx}
              onClick={() => onRunCommand(sc)}
              className="text-[10px] text-gray-400 hover:text-sky-300 hover:underline"
            >
              ${sc}
            </button>
          ))}
          <button
            onClick={onClear}
            className="p-1 text-gray-400 hover:text-white transition"
            title="Clear Terminal"
          >
            <Trash2 className="w-3 h-3" />
          </button>
        </div>
      </div>

      {/* Output log */}
      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {history.map((item) => (
          <div key={item.id} className="space-y-1">
            {/* Command Header */}
            <div className="flex items-center justify-between text-gray-400 text-[11px]">
              <div className="flex items-center space-x-1.5 text-sky-300 font-semibold">
                <span className="text-gray-500">$</span>
                <span>{item.command}</span>
              </div>
              <div className="flex items-center space-x-2 text-[10px] text-gray-500">
                <span>{item.durationSeconds}s</span>
                {item.exitCode === 0 ? (
                  <span className="flex items-center space-x-1 text-emerald-400">
                    <CheckCircle2 className="w-3 h-3" />
                    <span>0</span>
                  </span>
                ) : (
                  <span className="flex items-center space-x-1 text-rose-400">
                    <AlertCircle className="w-3 h-3" />
                    <span>{item.exitCode}</span>
                  </span>
                )}
              </div>
            </div>

            {/* Stdout */}
            {item.stdout && (
              <pre className="text-gray-300 whitespace-pre-wrap leading-relaxed text-[11.5px]">
                {item.stdout}
              </pre>
            )}

            {/* Stderr */}
            {item.stderr && (
              <pre className="text-rose-400 whitespace-pre-wrap leading-relaxed text-[11.5px]">
                {item.stderr}
              </pre>
            )}
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      {/* Interactive Command Input Prompt */}
      <form
        onSubmit={handleSubmit}
        className="h-8 border-t border-harness-border/40 bg-harness-bg/60 px-3 flex items-center space-x-2 select-none"
      >
        <span className="text-emerald-400 font-bold">$</span>
        <input
          type="text"
          value={cmdInput}
          onChange={(e) => setCmdInput(e.target.value)}
          placeholder="Run controlled bash command (e.g., 'pytest tests', 'git diff')..."
          className="flex-1 bg-transparent text-gray-200 text-xs focus:outline-none font-mono"
        />
        <button
          type="submit"
          className="text-gray-400 hover:text-sky-300 p-1 rounded transition"
          title="Execute"
        >
          <Play className="w-3 h-3" />
        </button>
      </form>
    </div>
  );
};
