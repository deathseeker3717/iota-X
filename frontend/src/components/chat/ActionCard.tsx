import React, { useState } from 'react';
import {
  FileEdit,
  Check,
  X,
  ChevronDown,
  ChevronUp,
  FileCode,
} from 'lucide-react';
import { AIAction } from '../../types';

interface ActionCardProps {
  action: AIAction;
  onViewFile?: (file: string) => void;
}

export const ActionCard: React.FC<ActionCardProps> = ({ action, onViewFile }) => {
  const [status, setStatus] = useState<AIAction['status']>(action.status);
  const [showDiff, setShowDiff] = useState<boolean>(false);

  return (
    <div className="my-2 border border-sky-500/30 bg-sky-950/20 rounded-lg overflow-hidden text-xs">
      {/* Header bar */}
      <div className="px-3 py-2 bg-sky-950/40 border-b border-sky-500/20 flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <FileEdit className="w-3.5 h-3.5 text-sky-400" />
          <span className="font-semibold text-sky-300 uppercase text-[10px] tracking-wider">
            AI Code Action
          </span>
          {action.file && (
            <button
              onClick={() => onViewFile?.(action.file!)}
              className="text-gray-300 hover:text-white font-mono flex items-center space-x-1 underline decoration-sky-500/40"
            >
              <span>{action.file}</span>
            </button>
          )}
        </div>

        {/* State Badge */}
        <div>
          {status === 'accepted' && (
            <span className="bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 px-2 py-0.5 rounded text-[10px] font-medium">
              Applied
            </span>
          )}
          {status === 'rejected' && (
            <span className="bg-rose-500/20 text-rose-300 border border-rose-500/40 px-2 py-0.5 rounded text-[10px] font-medium">
              Rejected
            </span>
          )}
        </div>
      </div>

      {/* Content description */}
      <div className="p-3">
        <p className="text-gray-200 text-xs mb-2 leading-relaxed">{action.summary}</p>

        {/* Diff preview toggle */}
        {action.diff && (
          <div className="mt-2">
            <button
              onClick={() => setShowDiff(!showDiff)}
              className="flex items-center space-x-1 text-sky-400 hover:text-sky-300 text-xs transition"
            >
              <span>{showDiff ? 'Hide Diff' : 'View Diff'}</span>
              {showDiff ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
            </button>

            {showDiff && (
              <pre className="mt-2 p-2 bg-black/50 border border-harness-border rounded font-mono text-[11px] overflow-x-auto text-gray-300 whitespace-pre">
                {action.diff.split('\n').map((line, idx) => {
                  let lineStyle = 'text-gray-400';
                  if (line.startsWith('+') && !line.startsWith('+++')) lineStyle = 'text-emerald-400 bg-emerald-950/30';
                  if (line.startsWith('-') && !line.startsWith('---')) lineStyle = 'text-rose-400 bg-rose-950/30';
                  if (line.startsWith('@@')) lineStyle = 'text-sky-400';

                  return (
                    <div key={idx} className={lineStyle}>
                      {line}
                    </div>
                  );
                })}
              </pre>
            )}
          </div>
        )}

        {/* Action button controls */}
        {status === 'pending' && (
          <div className="mt-3 flex items-center space-x-2 pt-2 border-t border-sky-500/20">
            <button
              onClick={() => setStatus('accepted')}
              className="flex items-center space-x-1.5 px-3 py-1 bg-emerald-600 hover:bg-emerald-500 text-white rounded text-xs font-medium transition active:scale-95 shadow-sm"
            >
              <Check className="w-3.5 h-3.5" />
              <span>Accept & Apply</span>
            </button>
            <button
              onClick={() => setStatus('rejected')}
              className="flex items-center space-x-1.5 px-3 py-1 bg-harness-panel hover:bg-rose-950/50 text-gray-300 hover:text-rose-300 border border-harness-border hover:border-rose-500/40 rounded text-xs font-medium transition"
            >
              <X className="w-3.5 h-3.5" />
              <span>Reject</span>
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
