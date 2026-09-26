import React from 'react';
import {
  Files,
  Search,
  GitBranch,
  ShieldCheck,
  Cpu,
  Sliders,
} from 'lucide-react';
import { ActiveSideBarTab } from '../../types';

interface ActivityBarProps {
  activeTab: ActiveSideBarTab;
  onSelectTab: (tab: ActiveSideBarTab) => void;
  gitChangesCount: number;
  isAgentRunning: boolean;
}

export const ActivityBar: React.FC<ActivityBarProps> = ({
  activeTab,
  onSelectTab,
  gitChangesCount,
  isAgentRunning,
}) => {
  return (
    <div className="w-12 bg-harness-bg border-r border-harness-border flex flex-col items-center py-2 justify-between select-none">
      {/* Top primary icons */}
      <div className="flex flex-col space-y-2">
        {/* Explorer */}
        <button
          onClick={() => onSelectTab('explorer')}
          className={`p-2.5 rounded-md relative transition ${
            activeTab === 'explorer'
              ? 'text-sky-400 bg-harness-panel/80'
              : 'text-gray-400 hover:text-gray-200 hover:bg-harness-panel/40'
          }`}
          title="Explorer"
        >
          <Files className="w-5 h-5" />
          {activeTab === 'explorer' && (
            <div className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 bg-sky-400 rounded-r" />
          )}
        </button>

        {/* Search */}
        <button
          onClick={() => onSelectTab('search')}
          className={`p-2.5 rounded-md relative transition ${
            activeTab === 'search'
              ? 'text-sky-400 bg-harness-panel/80'
              : 'text-gray-400 hover:text-gray-200 hover:bg-harness-panel/40'
          }`}
          title="Repository Search"
        >
          <Search className="w-5 h-5" />
          {activeTab === 'search' && (
            <div className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 bg-sky-400 rounded-r" />
          )}
        </button>

        {/* Source Control */}
        <button
          onClick={() => onSelectTab('git')}
          className={`p-2.5 rounded-md relative transition ${
            activeTab === 'git'
              ? 'text-sky-400 bg-harness-panel/80'
              : 'text-gray-400 hover:text-gray-200 hover:bg-harness-panel/40'
          }`}
          title="Source Control"
        >
          <GitBranch className="w-5 h-5" />
          {gitChangesCount > 0 && (
            <span className="absolute top-1 right-1 bg-sky-500 text-white font-mono text-[9px] w-4 h-4 rounded-full flex items-center justify-center font-bold">
              {gitChangesCount}
            </span>
          )}
          {activeTab === 'git' && (
            <div className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 bg-sky-400 rounded-r" />
          )}
        </button>

        {/* Tests / Verification */}
        <button
          onClick={() => onSelectTab('tests')}
          className={`p-2.5 rounded-md relative transition ${
            activeTab === 'tests'
              ? 'text-sky-400 bg-harness-panel/80'
              : 'text-gray-400 hover:text-gray-200 hover:bg-harness-panel/40'
          }`}
          title="Testing & Verification"
        >
          <ShieldCheck className="w-5 h-5" />
          {activeTab === 'tests' && (
            <div className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 bg-sky-400 rounded-r" />
          )}
        </button>
      </div>

      {/* Bottom secondary icons */}
      <div className="flex flex-col space-y-2">
        <button
          className="p-2.5 rounded-md text-gray-400 hover:text-gray-200 hover:bg-harness-panel/40 transition"
          title="Preferences"
        >
          <Sliders className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};
