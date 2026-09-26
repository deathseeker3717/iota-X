import React, { useRef, useEffect } from 'react';
import { X, FileCode, FileText, FileJson } from 'lucide-react';
import { RepositoryFile } from '../../types/contract';

interface TabItem extends RepositoryFile {
  isModified?: boolean;
}

interface TabBarProps {
  tabs: TabItem[];
  activeTabId: string | null;
  onSelectTab: (path: string) => void;
  onCloseTab: (path: string) => void;
}

export const TabBar: React.FC<TabBarProps> = ({
  tabs,
  activeTabId,
  onSelectTab,
  onCloseTab,
}) => {
  const scrollContainerRef = useRef<HTMLDivElement>(null);

  // Auto-scroll active tab into view
  useEffect(() => {
    if (activeTabId && scrollContainerRef.current) {
      const activeEl = scrollContainerRef.current.querySelector(
        `[data-tab-id="${CSS.escape(activeTabId)}"]`
      ) as HTMLElement | null;
      if (activeEl) {
        activeEl.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'nearest' });
      }
    }
  }, [activeTabId]);

  const getFileIcon = (fileName: string) => {
    if (fileName.endsWith('.py')) {
      return <FileCode className="w-3.5 h-3.5 text-yellow-400 shrink-0" />;
    }
    if (fileName.endsWith('.ts') || fileName.endsWith('.tsx')) {
      return <FileCode className="w-3.5 h-3.5 text-sky-400 shrink-0" />;
    }
    if (fileName.endsWith('.js') || fileName.endsWith('.jsx')) {
      return <FileCode className="w-3.5 h-3.5 text-amber-300 shrink-0" />;
    }
    if (fileName.endsWith('.json')) {
      return <FileJson className="w-3.5 h-3.5 text-amber-400 shrink-0" />;
    }
    if (fileName.endsWith('.toml') || fileName.endsWith('.yaml') || fileName.endsWith('.yml')) {
      return <FileText className="w-3.5 h-3.5 text-purple-400 shrink-0" />;
    }
    if (fileName.endsWith('.md')) {
      return <FileText className="w-3.5 h-3.5 text-blue-400 shrink-0" />;
    }
    return <FileText className="w-3.5 h-3.5 text-gray-400 shrink-0" />;
  };

  return (
    <div
      ref={scrollContainerRef}
      className="h-9 bg-harness-surface border-b border-harness-border flex items-center overflow-x-auto select-none no-scrollbar"
    >
      {tabs.length === 0 ? (
        <div className="px-3 text-xs text-gray-500 italic">No open editors</div>
      ) : (
        tabs.map((tab) => {
          const isActive = tab.path === activeTabId;
          return (
            <div
              key={tab.path}
              data-tab-id={tab.path}
              onClick={() => onSelectTab(tab.path)}
              className={`group h-full flex items-center space-x-2 px-3 border-r border-harness-border/70 cursor-pointer text-xs transition shrink-0 max-w-[220px] min-w-[120px] relative ${
                isActive
                  ? 'bg-harness-bg text-gray-100 font-medium'
                  : 'bg-harness-surface/70 text-gray-400 hover:bg-harness-panel/50 hover:text-gray-300'
              }`}
            >
              {/* Active Tab Accent Line */}
              {isActive && (
                <div className="absolute top-0 left-0 right-0 h-0.5 bg-sky-400" />
              )}

              {/* Language Icon */}
              {getFileIcon(tab.name)}

              {/* Tab Title */}
              <span className="truncate flex-1" title={tab.path}>
                {tab.name}
              </span>

              {/* Modified dot vs Close button:
                  When modified: shows bullet dot, changes to close X on hover.
                  When clean: close button appears on hover. */}
              {tab.isModified ? (
                <div className="relative flex items-center justify-center w-4 h-4">
                  <span className="w-2 h-2 rounded-full bg-sky-400 group-hover:hidden transition" />
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onCloseTab(tab.path);
                    }}
                    className="hidden group-hover:flex items-center justify-center p-0.5 rounded hover:bg-harness-border text-gray-300 hover:text-white transition"
                    title="Close (Unsaved changes)"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </div>
              ) : (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onCloseTab(tab.path);
                  }}
                  className="p-0.5 rounded hover:bg-harness-border text-gray-400 hover:text-white transition opacity-0 group-hover:opacity-100"
                  title="Close Tab"
                >
                  <X className="w-3 h-3" />
                </button>
              )}
            </div>
          );
        })
      )}
    </div>
  );
};
