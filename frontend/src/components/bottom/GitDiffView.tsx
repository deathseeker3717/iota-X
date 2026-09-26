import React, { useState } from 'react';
import {
  GitBranch,
  GitCommit as GitCommitIcon,
  RotateCw,
  FileCode,
  FilePlus,
  FileMinus,
  FileEdit,
  HelpCircle,
  Check,
  Copy,
  ExternalLink,
  History,
  Layers,
} from 'lucide-react';
import {
  GitChange,
  GitCommit,
  GitDiff,
  GitStatus,
} from '../../types/gitContract';

interface GitDiffViewProps {
  status?: GitStatus | null;
  changes?: GitChange[];
  commits?: GitCommit[];
  activeDiff?: GitDiff | null;
  selectedFile?: string | null;
  selectedCommit?: GitCommit | null;
  commitDetails?: string | null;
  isLoading?: boolean;
  isRefreshing?: boolean;
  onRefresh?: () => void;
  onSelectFile?: (file: string) => void;
  onSelectCommit?: (commit: GitCommit) => void;
  onClearCommit?: () => void;
  onOpenFile?: (path: string) => void;
}

type FilterCategory = 'all' | 'modified' | 'added' | 'deleted' | 'untracked';
type ViewMode = 'changes' | 'history';

export const GitDiffView: React.FC<GitDiffViewProps> = ({
  status,
  changes = [],
  commits = [],
  activeDiff,
  selectedFile,
  selectedCommit,
  commitDetails,
  isLoading = false,
  isRefreshing = false,
  onRefresh,
  onSelectFile,
  onSelectCommit,
  onClearCommit,
  onOpenFile,
}) => {
  const [viewMode, setViewMode] = useState<ViewMode>('changes');
  const [filterCategory, setFilterCategory] = useState<FilterCategory>('all');
  const [copied, setCopied] = useState(false);

  // Group changes by status
  const modifiedFiles = changes.filter((c) => c.status === 'modified');
  const addedFiles = changes.filter((c) => c.status === 'added');
  const deletedFiles = changes.filter((c) => c.status === 'deleted');
  const untrackedFiles = changes.filter((c) => c.status === 'untracked');

  // Filter list based on selected category tab
  const displayedChanges =
    filterCategory === 'all'
      ? changes
      : filterCategory === 'modified'
      ? modifiedFiles
      : filterCategory === 'added'
      ? addedFiles
      : filterCategory === 'deleted'
      ? deletedFiles
      : untrackedFiles;

  const activeChange =
    changes.find((c) => c.file === selectedFile) ||
    displayedChanges[0] ||
    changes[0] ||
    null;

  const totalAdditions = changes.reduce((acc, c) => acc + (c.additions || 0), 0);
  const totalDeletions = changes.reduce((acc, c) => acc + (c.deletions || 0), 0);

  const handleCopyDiff = () => {
    const textToCopy = selectedCommit
      ? commitDetails || ''
      : activeDiff?.diffText || activeChange?.diff || '';
    if (textToCopy) {
      navigator.clipboard.writeText(textToCopy);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'added':
        return <span className="text-[10px] bg-emerald-500/20 text-emerald-300 px-1 py-0.5 rounded font-mono font-bold">A</span>;
      case 'deleted':
        return <span className="text-[10px] bg-rose-500/20 text-rose-300 px-1 py-0.5 rounded font-mono font-bold">D</span>;
      case 'modified':
        return <span className="text-[10px] bg-amber-500/20 text-amber-300 px-1 py-0.5 rounded font-mono font-bold">M</span>;
      case 'untracked':
        return <span className="text-[10px] bg-gray-500/20 text-gray-300 px-1 py-0.5 rounded font-mono font-bold">U</span>;
      default:
        return null;
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'added':
        return <FilePlus className="w-3.5 h-3.5 text-emerald-400 shrink-0" />;
      case 'deleted':
        return <FileMinus className="w-3.5 h-3.5 text-rose-400 shrink-0" />;
      case 'modified':
        return <FileEdit className="w-3.5 h-3.5 text-amber-400 shrink-0" />;
      case 'untracked':
        return <HelpCircle className="w-3.5 h-3.5 text-gray-400 shrink-0" />;
      default:
        return <FileCode className="w-3.5 h-3.5 text-sky-400 shrink-0" />;
    }
  };

  return (
    <div className="h-full flex flex-col bg-harness-bg select-text">
      {/* 1. Global Git Top Toolbar */}
      <div className="h-9 px-3 bg-harness-surface/90 border-b border-harness-border/70 flex items-center justify-between text-xs select-none">
        {/* Left: Branch & View Switcher */}
        <div className="flex items-center space-x-3">
          <div className="flex items-center space-x-1.5 px-2 py-0.5 bg-sky-500/10 border border-sky-500/30 rounded text-sky-300 font-mono text-[11px]">
            <GitBranch className="w-3.5 h-3.5 text-sky-400" />
            <span className="font-semibold">{status?.branch || 'context-observability'}</span>
            {status?.ahead ? (
              <span className="text-emerald-400 text-[10px] font-bold">↑{status.ahead}</span>
            ) : null}
            {status?.behind ? (
              <span className="text-amber-400 text-[10px] font-bold">↓{status.behind}</span>
            ) : null}
          </div>

          <div className="flex items-center space-x-1 bg-harness-panel/60 p-0.5 rounded">
            <button
              onClick={() => {
                setViewMode('changes');
                onClearCommit?.();
              }}
              className={`flex items-center space-x-1 px-2 py-0.5 rounded text-[11px] font-medium transition ${
                viewMode === 'changes'
                  ? 'bg-sky-500 text-white shadow-sm'
                  : 'text-gray-400 hover:text-gray-200'
              }`}
            >
              <Layers className="w-3 h-3" />
              <span>Working Changes ({changes.length})</span>
            </button>
            <button
              onClick={() => setViewMode('history')}
              className={`flex items-center space-x-1 px-2 py-0.5 rounded text-[11px] font-medium transition ${
                viewMode === 'history'
                  ? 'bg-sky-500 text-white shadow-sm'
                  : 'text-gray-400 hover:text-gray-200'
              }`}
            >
              <History className="w-3 h-3" />
              <span>Commit History ({commits.length})</span>
            </button>
          </div>
        </div>

        {/* Right: Additions/Deletions & Refresh */}
        <div className="flex items-center space-x-3 text-[11px]">
          <div className="flex items-center space-x-2 font-mono">
            <span className="text-emerald-400 font-medium">+{totalAdditions}</span>
            <span className="text-rose-400 font-medium">-{totalDeletions}</span>
          </div>

          <button
            onClick={onRefresh}
            disabled={isLoading || isRefreshing}
            className="flex items-center space-x-1 px-2 py-1 bg-harness-panel hover:bg-harness-panel/80 text-gray-300 hover:text-white rounded border border-harness-border/60 transition disabled:opacity-50"
            title="Refresh Git Status (git_status)"
          >
            <RotateCw
              className={`w-3.5 h-3.5 text-sky-400 ${
                isRefreshing || isLoading ? 'animate-spin' : ''
              }`}
            />
            <span className="text-[11px]">Refresh</span>
          </button>
        </div>
      </div>

      {/* 2. Main Content Split: Sidebar List + Right Diff Viewer */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Sidebar */}
        <div className="w-72 border-r border-harness-border/70 bg-harness-surface flex flex-col select-none shrink-0">
          {viewMode === 'changes' ? (
            <>
              {/* Category Filter Badges */}
              <div className="p-2 border-b border-harness-border/50 flex flex-wrap gap-1 bg-harness-surface/50">
                <button
                  onClick={() => setFilterCategory('all')}
                  className={`px-2 py-0.5 rounded text-[10px] font-medium transition ${
                    filterCategory === 'all'
                      ? 'bg-sky-500/20 text-sky-300 border border-sky-500/40'
                      : 'text-gray-400 hover:bg-harness-panel hover:text-gray-200'
                  }`}
                >
                  All ({changes.length})
                </button>
                <button
                  onClick={() => setFilterCategory('modified')}
                  className={`px-2 py-0.5 rounded text-[10px] font-medium transition ${
                    filterCategory === 'modified'
                      ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                      : 'text-gray-400 hover:bg-harness-panel hover:text-gray-200'
                  }`}
                >
                  Modified ({modifiedFiles.length})
                </button>
                <button
                  onClick={() => setFilterCategory('added')}
                  className={`px-2 py-0.5 rounded text-[10px] font-medium transition ${
                    filterCategory === 'added'
                      ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
                      : 'text-gray-400 hover:bg-harness-panel hover:text-gray-200'
                  }`}
                >
                  Added ({addedFiles.length})
                </button>
                <button
                  onClick={() => setFilterCategory('deleted')}
                  className={`px-2 py-0.5 rounded text-[10px] font-medium transition ${
                    filterCategory === 'deleted'
                      ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40'
                      : 'text-gray-400 hover:bg-harness-panel hover:text-gray-200'
                  }`}
                >
                  Deleted ({deletedFiles.length})
                </button>
                {untrackedFiles.length > 0 && (
                  <button
                    onClick={() => setFilterCategory('untracked')}
                    className={`px-2 py-0.5 rounded text-[10px] font-medium transition ${
                      filterCategory === 'untracked'
                        ? 'bg-gray-500/20 text-gray-200 border border-gray-500/40'
                        : 'text-gray-400 hover:bg-harness-panel hover:text-gray-200'
                    }`}
                  >
                    Untracked ({untrackedFiles.length})
                  </button>
                )}
              </div>

              {/* Changed Files List */}
              <div className="flex-1 overflow-y-auto py-1">
                {displayedChanges.length === 0 ? (
                  <div className="p-4 text-center text-xs text-gray-500">
                    No {filterCategory !== 'all' ? filterCategory : ''} changes found.
                  </div>
                ) : (
                  displayedChanges.map((change) => {
                    const isSelected = change.file === activeChange?.file;
                    return (
                      <div
                        key={change.file}
                        onClick={() => onSelectFile?.(change.file)}
                        className={`flex items-center justify-between px-3 py-2 cursor-pointer text-xs transition ${
                          isSelected
                            ? 'bg-sky-500/20 text-sky-200 border-l-2 border-sky-400'
                            : 'text-gray-300 hover:bg-harness-panel/50 hover:text-white'
                        }`}
                      >
                        <div className="flex items-center space-x-2 truncate pr-2">
                          {getStatusIcon(change.status)}
                          <span className="truncate font-mono text-[11px]">{change.file}</span>
                        </div>
                        <div className="flex items-center space-x-1.5 shrink-0">
                          {change.staged && (
                            <span className="text-[9px] bg-emerald-500/10 text-emerald-400 px-1 rounded border border-emerald-500/30">
                              staged
                            </span>
                          )}
                          {getStatusBadge(change.status)}
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </>
          ) : (
            /* Commit History Mode */
            <div className="flex-1 overflow-y-auto py-1">
              <div className="px-3 py-1.5 text-[10px] uppercase font-bold text-gray-500 tracking-wider">
                Recent Commits (git_log)
              </div>
              {commits.map((commit) => {
                const isSelected = selectedCommit?.hash === commit.hash;
                return (
                  <div
                    key={commit.hash}
                    onClick={() => onSelectCommit?.(commit)}
                    className={`px-3 py-2 border-b border-harness-border/30 cursor-pointer text-xs transition ${
                      isSelected
                        ? 'bg-sky-500/20 text-sky-200 border-l-2 border-sky-400'
                        : 'text-gray-300 hover:bg-harness-panel/50 hover:text-white'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-mono text-[10px] text-sky-400 font-semibold flex items-center space-x-1">
                        <GitCommitIcon className="w-3 h-3" />
                        <span>{commit.shortHash}</span>
                      </span>
                      <span className="text-[10px] text-gray-500">{commit.date}</span>
                    </div>
                    <div className="text-xs font-medium text-gray-200 line-clamp-2 leading-snug">
                      {commit.message}
                    </div>
                    <div className="text-[10px] text-gray-400 mt-1 truncate">
                      {commit.author}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Right Area: Unified Diff Viewer or Commit Details */}
        <div className="flex-1 flex flex-col overflow-hidden bg-[#0d1117]">
          {selectedCommit ? (
            /* Commit Details Viewer (git_show) */
            <>
              <div className="h-8 px-3 bg-harness-surface/60 border-b border-harness-border/50 flex items-center justify-between text-xs select-none">
                <div className="flex items-center space-x-2 font-mono text-gray-200">
                  <GitCommitIcon className="w-3.5 h-3.5 text-sky-400" />
                  <span className="text-gray-400">Commit:</span>
                  <span className="font-semibold text-sky-300">{selectedCommit.shortHash}</span>
                  <span className="text-gray-500">— {selectedCommit.message}</span>
                </div>
                <div className="flex items-center space-x-2">
                  <button
                    onClick={handleCopyDiff}
                    className="flex items-center space-x-1 text-xs text-gray-400 hover:text-gray-200 transition"
                    title="Copy Commit Details"
                  >
                    {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                    <span>{copied ? 'Copied' : 'Copy'}</span>
                  </button>
                  <button
                    onClick={onClearCommit}
                    className="text-xs text-sky-400 hover:text-sky-300 transition"
                  >
                    Back to Working Diff
                  </button>
                </div>
              </div>

              <div className="flex-1 overflow-auto p-4 font-mono text-xs leading-relaxed">
                <pre className="text-gray-300 whitespace-pre-wrap">
                  {commitDetails || 'Loading commit details...'}
                </pre>
              </div>
            </>
          ) : activeChange ? (
            /* Working Diff Viewer (git_diff) */
            <>
              <div className="h-8 px-3 bg-harness-surface/60 border-b border-harness-border/50 flex items-center justify-between text-xs select-none">
                <div className="flex items-center space-x-2 font-mono text-gray-200">
                  {getStatusBadge(activeChange.status)}
                  <span className="font-semibold text-sky-300">{activeChange.file}</span>
                  <span className="text-[10px] text-gray-400">
                    (+{activeChange.additions} -{activeChange.deletions})
                  </span>
                </div>
                <div className="flex items-center space-x-3">
                  <button
                    onClick={handleCopyDiff}
                    className="flex items-center space-x-1 text-xs text-gray-400 hover:text-gray-200 transition"
                    title="Copy Unified Diff"
                  >
                    {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                    <span>{copied ? 'Copied' : 'Copy Diff'}</span>
                  </button>
                  <button
                    onClick={() => onOpenFile?.(activeChange.file)}
                    className="flex items-center space-x-1 text-xs text-sky-400 hover:text-sky-300 transition"
                  >
                    <ExternalLink className="w-3.5 h-3.5" />
                    <span>Open in Editor</span>
                  </button>
                </div>
              </div>

              {/* Diff Content */}
              <div className="flex-1 overflow-auto p-3 font-mono text-xs leading-relaxed">
                {(activeDiff?.diffText || activeChange.diff || 'No diff content available.')
                  .split('\n')
                  .map((line, idx) => {
                    let bgStyle = 'bg-transparent text-gray-300';
                    let indicator = ' ';

                    if (line.startsWith('+') && !line.startsWith('+++')) {
                      bgStyle = 'bg-emerald-950/40 text-emerald-300';
                      indicator = '+';
                    } else if (line.startsWith('-') && !line.startsWith('---')) {
                      bgStyle = 'bg-rose-950/40 text-rose-300';
                      indicator = '-';
                    } else if (line.startsWith('@@')) {
                      bgStyle = 'bg-sky-950/40 text-sky-400 font-bold';
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
                        <span className="flex-1">{line}</span>
                      </div>
                    );
                  })}
              </div>
            </>
          ) : (
            <div className="h-full flex items-center justify-center text-gray-500 text-xs">
              No changes detected in working repository. Repository is clean.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
