import React from 'react';
import {
  Terminal,
  ShieldCheck,
  GitBranch,
  Cpu,
  ChevronDown,
  ChevronUp,
  Maximize2,
  Minimize2,
} from 'lucide-react';
import {
  ActiveBottomTab,
  AgentStep,
  GitChange,
  TerminalOutput,
  VerificationResult,
} from '../../types';
import { TerminalView } from './TerminalView';
import { VerificationView } from './VerificationView';
import { GitDiffView } from './GitDiffView';
import { AgentActivityView } from './AgentActivityView';

interface BottomPanelProps {
  activeTab: ActiveBottomTab;
  onSelectTab: (tab: ActiveBottomTab) => void;
  terminalHistory: TerminalOutput[];
  onRunTerminalCommand: (command: string) => void;
  onClearTerminal: () => void;
  verificationResult: VerificationResult;
  isRunningVerification: boolean;
  onRunVerification: () => void;
  onAskAgentToFix?: (msg: string) => void;
  gitChanges: GitChange[];
  selectedGitFile: string | null;
  onSelectGitFile: (file: string) => void;
  agentSteps: AgentStep[];
  isAgentRunning: boolean;
  onOpenFile?: (path: string) => void;
  isMaximized: boolean;
  onToggleMaximize: () => void;
  onToggleCollapse: () => void;
  isCollapsed: boolean;
}

export const BottomPanel: React.FC<BottomPanelProps> = ({
  activeTab,
  onSelectTab,
  terminalHistory,
  onRunTerminalCommand,
  onClearTerminal,
  verificationResult,
  isRunningVerification,
  onRunVerification,
  onAskAgentToFix,
  gitChanges,
  selectedGitFile,
  onSelectGitFile,
  agentSteps,
  isAgentRunning,
  onOpenFile,
  isMaximized,
  onToggleMaximize,
  onToggleCollapse,
  isCollapsed,
}) => {
  return (
    <div className="h-full flex flex-col bg-harness-surface border-t border-harness-border select-none">
      {/* Tab Navigation Header */}
      <div className="h-9 px-2 bg-harness-surface border-b border-harness-border/60 flex items-center justify-between text-xs text-gray-400">
        <div className="flex items-center space-x-1">
          {/* Terminal Tab */}
          <button
            onClick={() => {
              if (isCollapsed) onToggleCollapse();
              onSelectTab('terminal');
            }}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded transition ${
              activeTab === 'terminal' && !isCollapsed
                ? 'text-sky-300 bg-harness-panel font-medium border-b-2 border-sky-400'
                : 'text-gray-400 hover:text-gray-200 hover:bg-harness-panel/50'
            }`}
          >
            <Terminal className="w-3.5 h-3.5 text-sky-400" />
            <span>Terminal</span>
          </button>

          {/* Verification Tab */}
          <button
            onClick={() => {
              if (isCollapsed) onToggleCollapse();
              onSelectTab('tests');
            }}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded transition ${
              activeTab === 'tests' && !isCollapsed
                ? 'text-sky-300 bg-harness-panel font-medium border-b-2 border-sky-400'
                : 'text-gray-400 hover:text-gray-200 hover:bg-harness-panel/50'
            }`}
          >
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
            <span>Tests</span>
            <span className="text-[10px] bg-emerald-500/20 text-emerald-300 px-1.5 py-0.2 rounded font-mono">
              {verificationResult.passedTests}/{verificationResult.totalTests}
            </span>
          </button>

          {/* Git Diff Tab */}
          <button
            onClick={() => {
              if (isCollapsed) onToggleCollapse();
              onSelectTab('git');
            }}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded transition ${
              activeTab === 'git' && !isCollapsed
                ? 'text-sky-300 bg-harness-panel font-medium border-b-2 border-sky-400'
                : 'text-gray-400 hover:text-gray-200 hover:bg-harness-panel/50'
            }`}
          >
            <GitBranch className="w-3.5 h-3.5 text-amber-400" />
            <span>Git Diff</span>
            {gitChanges.length > 0 && (
              <span className="text-[10px] bg-sky-500/20 text-sky-300 px-1.5 py-0.2 rounded font-mono">
                {gitChanges.length}
              </span>
            )}
          </button>

          {/* Agent Activity Tab */}
          <button
            onClick={() => {
              if (isCollapsed) onToggleCollapse();
              onSelectTab('agent');
            }}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded transition ${
              activeTab === 'agent' && !isCollapsed
                ? 'text-sky-300 bg-harness-panel font-medium border-b-2 border-sky-400'
                : 'text-gray-400 hover:text-gray-200 hover:bg-harness-panel/50'
            }`}
          >
            <Cpu className="w-3.5 h-3.5 text-indigo-400" />
            <span>Agent Activity</span>
            {isAgentRunning && (
              <span className="w-2 h-2 rounded-full bg-sky-400 animate-ping" />
            )}
          </button>
        </div>

        {/* Panel controls */}
        <div className="flex items-center space-x-1">
          <button
            onClick={onToggleMaximize}
            className="p-1 hover:text-white rounded transition"
            title={isMaximized ? 'Restore Panel' : 'Maximize Panel'}
          >
            {isMaximized ? (
              <Minimize2 className="w-3.5 h-3.5" />
            ) : (
              <Maximize2 className="w-3.5 h-3.5" />
            )}
          </button>
          <button
            onClick={onToggleCollapse}
            className="p-1 hover:text-white rounded transition"
            title={isCollapsed ? 'Expand Panel' : 'Collapse Panel'}
          >
            {isCollapsed ? (
              <ChevronUp className="w-3.5 h-3.5" />
            ) : (
              <ChevronDown className="w-3.5 h-3.5" />
            )}
          </button>
        </div>
      </div>

      {/* Panel Body */}
      {!isCollapsed && (
        <div className="flex-1 overflow-hidden">
          {activeTab === 'terminal' && (
            <TerminalView
              history={terminalHistory}
              onRunCommand={onRunTerminalCommand}
              onClear={onClearTerminal}
            />
          )}

          {activeTab === 'tests' && (
            <VerificationView
              result={verificationResult}
              isRunning={isRunningVerification}
              onRunVerification={onRunVerification}
              onAskAgentToFix={onAskAgentToFix}
              onOpenFile={onOpenFile}
            />
          )}

          {activeTab === 'git' && (
            <GitDiffView
              changes={gitChanges}
              selectedFile={selectedGitFile}
              onSelectFile={onSelectGitFile}
              onOpenFile={onOpenFile}
            />
          )}

          {activeTab === 'agent' && (
            <AgentActivityView steps={agentSteps} isRunning={isAgentRunning} />
          )}
        </div>
      )}
    </div>
  );
};
