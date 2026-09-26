import React, { useState } from 'react';
import { GitBranch, FileEdit, Plus, Minus, RotateCw, FileCode } from 'lucide-react';
import { GitChange } from '../../types';

interface GitDiffViewProps {
  changes: GitChange[];
  selectedFile: string | null;
  onSelectFile: (file: string) => void;
  onOpenFile?: (path: string) => void;
}

export const GitDiffView: React.FC<GitDiffViewProps> = ({
  changes,
  selectedFile,
  onSelectFile,
  onOpenFile,
}) => {
  const activeChange =
    changes.find((c) => c.file === selectedFile) || changes[0] || null;

  const totalAdditions = changes.reduce((acc, c) => acc + c.additions, 0);
  const totalDeletions = changes.reduce((acc, c) => acc + c.deletions, 0);

  return (
    <div className="h-full flex bg-harness-bg select-text">
      {/* Changed Files Sidebar */}
      <div className="w-64 border-r border-harness-border/70 bg-harness-surface flex flex-col select-none">
        <div className="h-8 px-3 border-b border-harness-border/50 flex items-center justify-between text-xs text-gray-400">
          <div className="flex items-center space-x-1.5 font-bold uppercase tracking-wider text-[10px]">
            <GitBranch className="w-3.5 h-3.5 text-sky-400" />
            <span>Changes ({changes.length})</span>
          </div>
          <div className="flex items-center space-x-2 text-[10px]">
            <span className="text-emerald-400">+{totalAdditions}</span>
            <span className="text-rose-400">-{totalDeletions}</span>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto py-1">
          {changes.map((change) => {
            const isSelected = change.file === activeChange?.file;
            return (
              <div
                key={change.file}
                onClick={() => onSelectFile(change.file)}
                className={`flex items-center justify-between px-3 py-1.5 cursor-pointer text-xs transition ${
                  isSelected
                    ? 'bg-sky-500/20 text-sky-200 border-l-2 border-sky-400'
                    : 'text-gray-300 hover:bg-harness-panel/50 hover:text-white'
                }`}
              >
                <div className="flex items-center space-x-1.5 truncate pr-2">
                  <FileEdit className="w-3.5 h-3.5 text-sky-400 shrink-0" />
                  <span className="truncate">{change.file}</span>
                </div>
                <div className="flex items-center space-x-1.5 text-[10px] shrink-0 font-mono">
                  <span className="text-emerald-400">+{change.additions}</span>
                  <span className="text-rose-400">-{change.deletions}</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Diff Content View */}
      <div className="flex-1 flex flex-col overflow-hidden bg-[#0d1117]">
        {activeChange ? (
          <>
            {/* Diff Header */}
            <div className="h-8 px-3 bg-harness-surface/60 border-b border-harness-border/50 flex items-center justify-between text-xs select-none">
              <div className="flex items-center space-x-2 font-mono text-gray-200">
                <span className="text-gray-400">Viewing diff:</span>
                <span className="font-semibold text-sky-300">{activeChange.file}</span>
              </div>
              <button
                onClick={() => onOpenFile?.(activeChange.file)}
                className="flex items-center space-x-1 text-xs text-sky-400 hover:text-sky-300 transition"
              >
                <FileCode className="w-3.5 h-3.5" />
                <span>Open in Editor</span>
              </button>
            </div>

            {/* Unified Diff Code Lines */}
            <div className="flex-1 overflow-auto p-3 font-mono text-xs leading-relaxed">
              {activeChange.diff.split('\n').map((line, idx) => {
                let bgStyle = 'bg-transparent text-gray-300';
                let indicator = ' ';

                if (line.startsWith('+') && !line.startsWith('+++')) {
                  bgStyle = 'bg-emerald-950/40 text-emerald-300';
                  indicator = '+';
                } else if (line.startsWith('-') && !line.startsWith('---')) {
                  bgStyle = 'bg-rose-950/40 text-rose-300';
                  indicator = '-';
                } else if (line.startsWith('@@')) {
                  bgStyle = 'bg-sky-950/30 text-sky-400 font-bold';
                  indicator = '@';
                }

                return (
                  <div
                    key={idx}
                    className={`flex items-start px-2 py-0.5 rounded-sm whitespace-pre ${bgStyle}`}
                  >
                    <span className="w-5 select-none text-gray-600 text-[10px] shrink-0">
                      {indicator}
                    </span>
                    <span className="flex-1">{line}</span>
                  </div>
                );
              })}
            </div>
          </>
        ) : (
          <div className="h-full flex items-center justify-center text-gray-500 text-xs">
            No changes detected in working repository.
          </div>
        )}
      </div>
    </div>
  );
};
