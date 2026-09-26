import React, { useState } from 'react';
import {
  GitBranch,
  Play,
  CheckCircle2,
  FolderGit2,
  Cpu,
  Settings,
  ChevronDown,
} from 'lucide-react';
import { SettingsModal } from './SettingsModal';

interface HeaderProps {
  currentRepo: string;
  currentBranch: string;
  onRepoChange?: () => void;
  onRunTests: () => void;
  isAgentRunning: boolean;
}

export const Header: React.FC<HeaderProps> = ({
  currentRepo,
  currentBranch,
  onRepoChange,
  onRunTests,
  isAgentRunning,
}) => {
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isRepoMenuOpen, setIsRepoMenuOpen] = useState(false);

  const availableRepos = [
    { name: 'iota-X (ai-coding-harness)', branch: 'main' },
    { name: 'deathseeker3717/iota-X', branch: 'tools-repository' },
    { name: 'demo-microservice', branch: 'feat/auth' },
  ];

  return (
    <>
      <header className="h-12 border-b border-harness-border bg-harness-surface flex items-center justify-between px-4 text-sm select-none z-30">
        {/* Left: AI Coding Harness */}
        <div className="flex items-center space-x-2 font-semibold text-gray-100 tracking-wide min-w-[200px]">
          <div className="w-6 h-6 rounded-md bg-gradient-to-tr from-sky-500 to-indigo-600 flex items-center justify-center text-white shadow-sm">
            <Cpu className="w-3.5 h-3.5" />
          </div>
          <span className="font-bold text-gray-100 text-sm tracking-tight">AI Coding Harness</span>
        </div>

        {/* Center: Repository */}
        <div className="relative flex items-center justify-center">
          <div className="flex items-center space-x-1.5">
            <span className="text-xs text-gray-400 font-medium">Repository:</span>
            <button
              onClick={() => setIsRepoMenuOpen(!isRepoMenuOpen)}
              className="flex items-center space-x-2 bg-harness-bg/90 hover:bg-harness-panel border border-harness-border px-3 py-1 rounded-md text-xs text-gray-200 transition focus:outline-none focus:border-sky-500 shadow-xs"
              title="Switch or view repository"
            >
              <FolderGit2 className="w-3.5 h-3.5 text-sky-400" />
              <span className="font-medium text-gray-100">{currentRepo}</span>
              <span className="text-gray-500">|</span>
              <div className="flex items-center space-x-1 text-emerald-400 font-mono text-[11px]">
                <GitBranch className="w-3 h-3" />
                <span>{currentBranch}</span>
              </div>
              <ChevronDown className="w-3 h-3 text-gray-400 ml-0.5" />
            </button>
          </div>

          {/* Repo dropdown menu */}
          {isRepoMenuOpen && (
            <div className="absolute top-10 left-1/2 -translate-x-1/2 w-64 bg-harness-surface border border-harness-border rounded-lg shadow-xl py-1 z-40 text-xs">
              <div className="px-3 py-1.5 text-[10px] font-bold uppercase tracking-wider text-gray-500 border-b border-harness-border/60">
                Active Repositories
              </div>
              {availableRepos.map((repo, idx) => (
                <button
                  key={idx}
                  onClick={() => {
                    if (onRepoChange) onRepoChange();
                    setIsRepoMenuOpen(false);
                  }}
                  className="w-full text-left px-3 py-2 hover:bg-harness-panel flex items-center justify-between text-gray-300 hover:text-white transition"
                >
                  <span className="truncate">{repo.name}</span>
                  <span className="text-[10px] text-gray-500 font-mono">{repo.branch}</span>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Right: Settings & Action Buttons */}
        <div className="flex items-center space-x-3 min-w-[200px] justify-end">
          {/* Autonomous Status indicator */}
          <div className="flex items-center space-x-1.5 bg-harness-panel/70 border border-harness-border px-2.5 py-1 rounded-full text-xs">
            {isAgentRunning ? (
              <>
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-sky-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-sky-500"></span>
                </span>
                <span className="text-sky-300 font-medium">Harness Active</span>
              </>
            ) : (
              <>
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                <span className="text-gray-300 font-medium">Ready</span>
              </>
            )}
          </div>

          {/* Run Tests / Verify trigger */}
          <button
            onClick={onRunTests}
            className="flex items-center space-x-1.5 px-3 py-1 bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-300 border border-emerald-500/30 rounded-md text-xs font-medium transition active:scale-95"
            title="Execute Pytest Test Suite"
          >
            <Play className="w-3 h-3 fill-emerald-300" />
            <span>Verify (pytest)</span>
          </button>

          {/* Settings button */}
          <button
            onClick={() => setIsSettingsOpen(true)}
            className="flex items-center space-x-1 px-2.5 py-1 bg-harness-bg hover:bg-harness-panel text-gray-300 hover:text-white border border-harness-border rounded-md text-xs font-medium transition"
            title="Open Harness Settings"
          >
            <Settings className="w-3.5 h-3.5 text-gray-400" />
            <span>Settings</span>
          </button>
        </div>
      </header>

      {/* Settings Dialog Modal */}
      <SettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
      />
    </>
  );
};
