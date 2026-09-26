import React, { useState, useMemo } from 'react';
import {
  GitBranch,
  GitCommit as GitCommitIcon,
  RotateCw,
  Plus,
  Minus,
  FileEdit,
  FilePlus,
  FileMinus,
  FileQuestion,
  FileCode,
  Copy,
  Check,
  History,
  Layers,
  CheckCircle2,
} from 'lucide-react';
import {
  GitChange,
  GitCommit,
  GitFileStatus,
  GitStatus,
} from '../../types/gitContract';

interface GitDiffViewProps {
  status: GitStatus | null;
  changes: GitChange[];
  selectedFile: string | null;
  onSelectFile: (file: string) => void;
  commits?: GitCommit[];
  selectedCommit?: GitCommit | null;
  selectedCommitDiff?: string;
  onSelectCommit?: (hash: string) => void;
  isLoading?: boolean;
  onRefresh?: () => void;
  onOpenFile?: (path: string) => void;
}

type GitViewMode = 'changes' | 'history';
type FilterStatus = 'all' | GitFileStatus;

export const GitDiffView: React.FC<GitDiffViewProps> = ({
  status,
  changes,
  selectedFile,
  onSelectFile,
  commits = [],
  selectedCommit,
  selectedCommitDiff = '',
  onSelectCommit,
  isLoading = false,
  onRefresh,
  onOpenFile,
}) => {
  const [viewMode, setViewMode] = useState<GitViewMode>('changes');
  const [filter, setFilter] = useState<FilterStatus>('all');
  const [copied, setCopied] = useState<boolean>(false);

  // Filtered changes by status
  const filteredChanges = useMemo(() => {
    if (filter === 'all') return changes;
    return changes.filter((c) => c.status === filter);
  }, [changes, filter]);

  // Active selected change
  const activeChange = useMemo(() => {
    return changes.find((c) => c.file === selectedFile) || changes[0] || null;
  }, [changes, selectedFile]);

  // Counts by status
  const counts = useMemo(() => {
    return {
      all: changes.length,
      modified: changes.filter((c) => c.status === 'modified').length,
      added: changes.filter((c) => c.status === 'added').length,
      deleted: changes.filter((c) => c.status === 'deleted').length,
      untracked: changes.filter((c) => c.status === 'untracked').length,
    };
  }, [changes]);

  const totalAdditions = changes.reduce((acc, c) => acc + c.additions, 0);
  const totalDeletions = changes.reduce((acc, c) => acc + c.deletions, 0);

  const handleCopyDiff = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const renderStatusBadge = (fileStatus: GitFileStatus) => {
    switch (fileStatus) {
      case 'added':
        return (
          <span className="px-1.5 py-0.5 text-[9px] font-bold rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 flex items-center space-x-0.5">
            <Plus className="w-2.5 h-2.5" />
            <span>A</span>
          </span>
        );
      case 'modified':
        return (
          <span className="px-1.5 py-0.5 text-[9px] font-bold rounded bg-amber-500/20 text-amber-300 border border-amber-500/30 flex items-center space-x-0.5">
            <FileEdit className="w-2.5 h-2.5" />
            <span>M</span>
          </span>
        );
      case 'deleted':
        return (
          <span className="px-1.5 py-0.5 text-[9px] font-bold rounded bg-rose-500/20 text-rose-300 border border-rose-500/30 flex items-center space-x-0.5">
            <Minus className="w-2.5 h-2.5" />
            <span>D</span>
          </span>
        );
      case 'untracked':
        return (
          <span className="px-1.5 py-0.5 text-[9px] font-bold rounded bg-purple-500/20 text-purple-300 border border-purple-500/30 flex items-center space-x-0.5">
            <FileQuestion className="w-2.5 h-2.5" />
            <span>U</span>
          </span>
        );
    }
  };

  return (
    <div className="h-full flex flex-col bg-harness-bg select-text">
      {/* Git Sub-Bar Header */}
      <div className="h-9 px-3 bg-harness-surface/90 border-b border-harness-border/70 flex items-center justify-between text-xs select-none">
        <div className="flex items-center space-x-2">
          {/* Mode Selector */}
          <div className="flex items-center bg-harness-bg p-0.5 rounded-md border border-harness-border/50 text-[11px]">
            <button
              onClick={() => setViewMode('changes')}
              className={`flex items-center space-x-1.5 px-2.5 py-1 rounded transition ${
                viewMode === 'changes'
                  ? 'bg-sky-500/20 text-sky-300 font-semibold shadow-sm'
                  : 'text-gray-400 hover:text-gray-200'
              }`}
            >
              <Layers className="w-3 h-3" />
              <span>Working Tree ({changes.length})</span>
            </button>
            <button
              onClick={() => {
                setViewMode('history');
                if (!selectedCommit && commits.length > 0 && onSelectCommit) {
                  onSelectCommit(commits[0].hash);
                }
              }}
              className={`flex items-center space-x-1.5 px-2.5 py-1 rounded transition ${
                viewMode === 'history'
                  ? 'bg-sky-500/20 text-sky-300 font-semibold shadow-sm'
                  : 'text-gray-400 hover:text-gray-200'
              }`}
            >
              <History className="w-3 h-3" />
              <span>Commits ({commits.length})</span>
            </button>
          </div>

          {/* Current Branch Pill */}
          <div className="flex items-center space-x-1 px-2.5 py-1 rounded bg-harness-panel/70 border border-harness-border/40 text-[11px] text-gray-300">
            <GitBranch className="w-3 h-3 text-sky-400" />
            <span className="font-mono text-gray-200 font-medium">
              {status?.branch || 'HEAD'}
            </span>
          </div>

          {/* Staged info */}
          {status && status.stagedFiles.length > 0 && (
            <span className="px-2 py-0.5 text-[10px] font-mono rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              {status.stagedFiles.length} staged
            </span>
          )}
        </div>

        {/* Right Stats & Refresh */}
        <div className="flex items-center space-x-3">
          <div className="flex items-center space-x-2 text-xs font-mono">
            <span className="text-emerald-400 font-semibold">+{totalAdditions}</span>
            <span className="text-rose-400 font-semibold">-{totalDeletions}</span>
          </div>
          <button
            onClick={onRefresh}
            disabled={isLoading}
            className={`flex items-center space-x-1 px-2.5 py-1 rounded bg-harness-panel hover:bg-harness-border/60 text-gray-300 hover:text-white transition border border-harness-border/60 ${
              isLoading ? 'opacity-60 cursor-not-allowed' : ''
            }`}
            title="Refresh Git status from backend"
          >
            <RotateCw className={`w-3 h-3 ${isLoading ? 'animate-spin text-sky-400' : ''}`} />
            <span className="text-[11px]">Refresh</span>
          </button>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Side: Changes or Commit List */}
        <div className="w-72 border-r border-harness-border/70 bg-harness-surface flex flex-col select-none shrink-0">
          {viewMode === 'changes' ? (
            <>
              {/* Category Filter Pills */}
              <div className="p-2 border-b border-harness-border/50 flex flex-wrap gap-1 text-[10px]">
                <button
                  onClick={() => setFilter('all')}
                  className={`px-2 py-0.5 rounded transition ${
                    filter === 'all'
                      ? 'bg-sky-500/20 text-sky-300 font-semibold'
                      : 'text-gray-400 hover:bg-harness-panel'
                  }`}
                >
                  All ({counts.all})
                </button>
                <button
                  onClick={() => setFilter('modified')}
                  className={`px-2 py-0.5 rounded transition ${
                    filter === 'modified'
                      ? 'bg-amber-500/20 text-amber-300 font-semibold'
                      : 'text-gray-400 hover:bg-harness-panel'
                  }`}
                >
                  Modified ({counts.modified})
                </button>
                <button
                  onClick={() => setFilter('added')}
                  className={`px-2 py-0.5 rounded transition ${
                    filter === 'added'
                      ? 'bg-emerald-500/20 text-emerald-300 font-semibold'
                      : 'text-gray-400 hover:bg-harness-panel'
                  }`}
                >
                  Added ({counts.added})
                </button>
                <button
                  onClick={() => setFilter('deleted')}
                  className={`px-2 py-0.5 rounded transition ${
                    filter === 'deleted'
                      ? 'bg-rose-500/20 text-rose-300 font-semibold'
                      : 'text-gray-400 hover:bg-harness-panel'
                  }`}
                >
                  Deleted ({counts.deleted})
                </button>
                <button
                  onClick={() => setFilter('untracked')}
                  className={`px-2 py-0.5 rounded transition ${
                    filter === 'untracked'
                      ? 'bg-purple-500/20 text-purple-300 font-semibold'
                      : 'text-gray-400 hover:bg-harness-panel'
                  }`}
                >
                  Untracked ({counts.untracked})
                </button>
              </div>

              {/* Changes List */}
              <div className="flex-1 overflow-y-auto py-1">
                {filteredChanges.length === 0 ? (
                  <div className="p-4 text-center text-gray-500 text-xs">
                    No {filter !== 'all' ? filter : ''} changes found.
                  </div>
                ) : (
                  filteredChanges.map((change) => {
                    const isSelected = change.file === activeChange?.file;
                    return (
                      <div
                        key={change.file}
                        onClick={() => onSelectFile(change.file)}
                        className={`flex items-center justify-between px-3 py-2 cursor-pointer text-xs transition border-b border-harness-border/20 ${
                          isSelected
                            ? 'bg-sky-500/20 text-sky-200 border-l-2 border-l-sky-400 font-medium'
                            : 'text-gray-300 hover:bg-harness-panel/50 hover:text-white'
                        }`}
                      >
                        <div className="flex items-center space-x-2 truncate pr-2">
                          {renderStatusBadge(change.status)}
                          <span className="truncate font-mono text-[11px]">{change.file}</span>
                        </div>
                        <div className="flex items-center space-x-1.5 text-[10px] shrink-0 font-mono">
                          {change.additions > 0 && (
                            <span className="text-emerald-400">+{change.additions}</span>
                          )}
                          {change.deletions > 0 && (
                            <span className="text-rose-400">-{change.deletions}</span>
                          )}
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </>
          ) : (
            /* Commit History List */
            <div className="flex-1 overflow-y-auto py-1">
              {commits.length === 0 ? (
                <div className="p-4 text-center text-gray-500 text-xs">
                  No commit history available.
                </div>
              ) : (
                commits.map((commit) => {
                  const isSelected =
                    selectedCommit?.hash === commit.hash ||
                    selectedCommit?.shortHash === commit.shortHash;
                  return (
                    <div
                      key={commit.hash}
                      onClick={() => onSelectCommit?.(commit.hash)}
                      className={`p-2.5 cursor-pointer text-xs transition border-b border-harness-border/30 ${
                        isSelected
                          ? 'bg-sky-500/20 text-sky-200 border-l-2 border-l-sky-400'
                          : 'text-gray-300 hover:bg-harness-panel/50 hover:text-white'
                      }`}
                    >
                      <div className="flex items-center justify-between mb-1">
                        <div className="flex items-center space-x-1.5">
                          <GitCommitIcon className="w-3 h-3 text-sky-400 shrink-0" />
                          <span className="font-mono text-[11px] font-semibold text-sky-300">
                            {commit.shortHash}
                          </span>
                        </div>
                        <span className="text-[10px] text-gray-500">{commit.date}</span>
                      </div>
                      <div className="text-[11px] text-gray-200 line-clamp-1 font-medium">
                        {commit.message}
                      </div>
                      <div className="text-[10px] text-gray-400 mt-0.5 truncate">
                        {commit.author}
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          )}
        </div>

        {/* Right Side: Diff Viewer */}
        <div className="flex-1 flex flex-col overflow-hidden bg-[#0d1117]">
          {viewMode === 'changes' ? (
            activeChange ? (
              <>
                {/* Diff Viewer Header */}
                <div className="h-9 px-3 bg-harness-surface/60 border-b border-harness-border/50 flex items-center justify-between text-xs select-none">
                  <div className="flex items-center space-x-2 font-mono text-gray-200">
                    {renderStatusBadge(activeChange.status)}
                    <span className="text-gray-400">Viewing diff:</span>
                    <span className="font-semibold text-sky-300">{activeChange.file}</span>
                    <span className="text-[10px] text-gray-500 ml-2">
                      (+{activeChange.additions} -{activeChange.deletions})
                    </span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <button
                      onClick={() => handleCopyDiff(activeChange.diff || '')}
                      className="flex items-center space-x-1 px-2 py-1 text-[11px] rounded bg-harness-panel/60 hover:bg-harness-panel text-gray-300 hover:text-white transition border border-harness-border/40"
                      title="Copy diff to clipboard"
                    >
                      {copied ? (
                        <>
                          <Check className="w-3 h-3 text-emerald-400" />
                          <span className="text-emerald-400">Copied</span>
                        </>
                      ) : (
                        <>
                          <Copy className="w-3 h-3 text-gray-400" />
                          <span>Copy Diff</span>
                        </>
                      )}
                    </button>
                    {activeChange.status !== 'deleted' && (
                      <button
                        onClick={() => onOpenFile?.(activeChange.file)}
                        className="flex items-center space-x-1 px-2 py-1 text-[11px] rounded bg-sky-500/20 hover:bg-sky-500/30 text-sky-300 transition border border-sky-500/30"
                      >
                        <FileCode className="w-3 h-3" />
                        <span>Open in Editor</span>
                      </button>
                    )}
                  </div>
                </div>

                {/* Diff Lines Body */}
                <div className="flex-1 overflow-auto p-3 font-mono text-xs leading-relaxed">
                  {(activeChange.diff || 'No diff available').split('\n').map((line, idx) => {
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
                        <span className="w-6 select-none text-gray-600 text-[10px] shrink-0 font-mono">
                          {indicator}
                        </span>
                        <span className="flex-1 font-mono">{line}</span>
                      </div>
                    );
                  })}
                </div>
              </>
            ) : (
              <div className="h-full flex flex-col items-center justify-center text-gray-400 space-y-2 select-none">
                <CheckCircle2 className="w-8 h-8 text-emerald-400/80" />
                <span className="text-sm font-medium text-gray-300">Working tree clean</span>
                <span className="text-xs text-gray-500">No uncommitted changes in repository</span>
              </div>
            )
          ) : (
            /* Commit Inspection View */
            selectedCommit ? (
              <>
                {/* Commit Header */}
                <div className="p-3 bg-harness-surface/60 border-b border-harness-border/50 text-xs">
                  <div className="flex items-center justify-between mb-1">
                    <div className="flex items-center space-x-2">
                      <GitCommitIcon className="w-4 h-4 text-sky-400" />
                      <span className="font-mono text-sm font-bold text-sky-300">
                        {selectedCommit.shortHash}
                      </span>
                      <span className="font-mono text-xs text-gray-500">
                        ({selectedCommit.hash})
                      </span>
                    </div>
                    <span className="text-xs text-gray-400">{selectedCommit.date}</span>
                  </div>
                  <h4 className="text-sm font-semibold text-gray-100 mt-1">
                    {selectedCommit.message}
                  </h4>
                  <div className="text-xs text-gray-400 mt-1">
                    Author: <span className="text-gray-300">{selectedCommit.author}</span>
                  </div>
                </div>

                {/* Commit Unified Diff */}
                <div className="flex-1 overflow-auto p-3 font-mono text-xs leading-relaxed">
                  {(selectedCommitDiff || selectedCommit.diff || 'No commit details').split('\n').map((line, idx) => {
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
                        <span className="w-6 select-none text-gray-600 text-[10px] shrink-0 font-mono">
                          {indicator}
                        </span>
                        <span className="flex-1 font-mono">{line}</span>
                      </div>
                    );
                  })}
                </div>
              </>
            ) : (
              <div className="h-full flex items-center justify-center text-gray-500 text-xs">
                Select a commit from the history list to inspect its diff.
              </div>
            )
          )}
        </div>
      </div>
    </div>
  );
};
