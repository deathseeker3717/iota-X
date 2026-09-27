import React, { useState, useMemo } from 'react';
import {
  ChevronDown,
  ChevronRight,
  FileCode,
  FileText,
  Folder,
  FolderOpen,
  Search,
  RotateCw,
  FilePlus,
  FolderPlus,
  X,
  FileJson,
  FileCheck2,
} from 'lucide-react';
import { RepositoryNode } from '../../types/contract';

interface FileExplorerProps {
  files: RepositoryNode[];
  activeFilePath: string | null;
  modifiedFilePaths?: string[];
  onSelectFile: (node: { path: string }) => void;
  onRefresh?: () => void;
  onCreateFile?: (path: string) => void;
  onCreateFolder?: (path: string) => void;
  isLoading?: boolean;
}

export const FileExplorer: React.FC<FileExplorerProps> = ({
  files,
  activeFilePath,
  modifiedFilePaths = [],
  onSelectFile,
  onRefresh,
  onCreateFile,
  onCreateFolder,
  isLoading = false,
}) => {
  // Folder expansion map: tracks expanded state for each directory path
  const [expandedFolders, setExpandedFolders] = useState<Record<string, boolean>>({
    src: true,
    'src/auth': true,
    'src/harness': true,
    'src/harness/tools': true,
    'src/harness/repository': true,
    'src/harness/orchestrator': true,
    tests: true,
  });

  // Search filter query
  const [searchQuery, setSearchQuery] = useState<string>('');

  // New item modal dialog state
  const [showNewDialog, setShowNewDialog] = useState<'file' | 'folder' | null>(null);
  const [newItemPath, setNewItemPath] = useState<string>('');

  // Toggle single folder
  const toggleFolder = (path: string) => {
    setExpandedFolders((prev) => ({
      ...prev,
      [path]: !prev[path],
    }));
  };

  // Expand all / Collapse all toggle
  const toggleExpandAll = () => {
    const allExpanded = Object.values(expandedFolders).some((v) => v);
    if (allExpanded) {
      setExpandedFolders({});
    } else {
      const allDirs: Record<string, boolean> = {};
      const collectDirs = (nodes: RepositoryNode[]) => {
        for (const n of nodes) {
          if (n.type === 'directory') {
            allDirs[n.path] = true;
            if (n.children) collectDirs(n.children);
          }
        }
      };
      collectDirs(files);
      setExpandedFolders(allDirs);
    }
  };

  // Distinct language / type icons
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
    if (fileName.endsWith('.sh') || fileName.endsWith('.bash')) {
      return <FileCode className="w-3.5 h-3.5 text-emerald-400 shrink-0" />;
    }
    if (fileName.endsWith('.sql')) {
      return <FileText className="w-3.5 h-3.5 text-pink-400 shrink-0" />;
    }
    return <FileText className="w-3.5 h-3.5 text-gray-400 shrink-0" />;
  };

  // Filter tree recursively based on query
  const filteredFiles = useMemo(() => {
    if (!searchQuery.trim()) return files;

    const q = searchQuery.toLowerCase().trim();

    const filterNode = (node: RepositoryNode): RepositoryNode | null => {
      const nameMatches = node.name.toLowerCase().includes(q);
      const pathMatches = node.path.toLowerCase().includes(q);

      if (node.type === 'file') {
        return nameMatches || pathMatches ? node : null;
      }

      // Directory
      const matchedChildren: RepositoryNode[] = [];
      if (node.children) {
        for (const child of node.children) {
          const filteredChild = filterNode(child);
          if (filteredChild) {
            matchedChildren.push(filteredChild);
          }
        }
      }

      if (nameMatches || pathMatches || matchedChildren.length > 0) {
        return {
          ...node,
          children: matchedChildren,
        };
      }
      return null;
    };

    const results: RepositoryNode[] = [];
    for (const node of files) {
      const filtered = filterNode(node);
      if (filtered) results.push(filtered);
    }
    return results;
  }, [files, searchQuery]);

  // When searching, auto-expand matching directories
  React.useEffect(() => {
    if (searchQuery.trim()) {
      const autoExpanded: Record<string, boolean> = {};
      const expandMatched = (nodes: RepositoryNode[]) => {
        for (const n of nodes) {
          if (n.type === 'directory') {
            autoExpanded[n.path] = true;
            if (n.children) expandMatched(n.children);
          }
        }
      };
      expandMatched(filteredFiles);
      setExpandedFolders((prev) => ({ ...prev, ...autoExpanded }));
    }
  }, [searchQuery, filteredFiles]);

  // Handle new file/folder creation
  const handleCreateSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newItemPath.trim()) return;

    if (showNewDialog === 'file' && onCreateFile) {
      onCreateFile(newItemPath.trim());
    } else if (showNewDialog === 'folder' && onCreateFolder) {
      onCreateFolder(newItemPath.trim());
    }

    setNewItemPath('');
    setShowNewDialog(null);
  };

  // Recursive tree node renderer
  const renderTree = (items: RepositoryNode[], depth = 0) => {
    return items.map((item) => {
      const isFolder = item.type === 'directory';
      const isExpanded = expandedFolders[item.path] ?? false;
      const isActive = activeFilePath === item.path;
      const isModified = modifiedFilePaths.includes(item.path);

      return (
        <div key={item.id} className="text-xs">
          <div
            onClick={() => {
              if (isFolder) {
                toggleFolder(item.path);
              } else {
                onSelectFile(item);
              }
            }}
            style={{ paddingLeft: `${depth * 14 + 10}px` }}
            className={`flex items-center py-1 cursor-pointer transition select-none group pr-2.5 ${
              isActive
                ? 'bg-sky-500/20 text-sky-200 border-l-2 border-sky-400 font-medium'
                : 'text-gray-300 hover:bg-harness-panel/50 hover:text-white'
            }`}
          >
            {/* Expand / Collapse Chevron */}
            {isFolder ? (
              <span className="mr-1 text-gray-400">
                {isExpanded ? (
                  <ChevronDown className="w-3.5 h-3.5" />
                ) : (
                  <ChevronRight className="w-3.5 h-3.5" />
                )}
              </span>
            ) : (
              <span className="w-3.5 mr-1" />
            )}

            {/* Folder / File Icon */}
            {isFolder ? (
              isExpanded ? (
                <FolderOpen className="w-4 h-4 text-sky-400 mr-1.5 shrink-0" />
              ) : (
                <Folder className="w-4 h-4 text-sky-400 mr-1.5 shrink-0" />
              )
            ) : (
              <span className="mr-1.5 shrink-0">{getFileIcon(item.name)}</span>
            )}

            {/* File or Folder Name */}
            <span className="truncate flex-1">{item.name}</span>

            {/* Unsaved changes dot indicator */}
            {isModified && (
              <span
                className="w-1.5 h-1.5 rounded-full bg-sky-400 ml-1.5 shrink-0"
                title="Unsaved changes"
              />
            )}
          </div>

          {/* Nested Children */}
          {isFolder && isExpanded && item.children && item.children.length > 0 && (
            <div>{renderTree(item.children, depth + 1)}</div>
          )}

          {isFolder && isExpanded && (!item.children || item.children.length === 0) && (
            <div
              style={{ paddingLeft: `${(depth + 1) * 14 + 14}px` }}
              className="py-1 text-[11px] text-gray-500 italic select-none"
            >
              (empty)
            </div>
          )}
        </div>
      );
    });
  };

  return (
    <div className="h-full flex flex-col bg-harness-surface select-none">
      {/* Title Bar */}
      <div className="h-9 px-3 flex items-center justify-between border-b border-harness-border/60">
        <span className="text-[11px] font-bold uppercase tracking-wider text-gray-400">
          Explorer
        </span>
        <div className="flex items-center space-x-1 text-gray-400">
          <button
            onClick={() => setShowNewDialog('file')}
            className="p-1 hover:text-white hover:bg-harness-panel rounded transition"
            title="New File"
          >
            <FilePlus className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={() => setShowNewDialog('folder')}
            className="p-1 hover:text-white hover:bg-harness-panel rounded transition"
            title="New Folder"
          >
            <FolderPlus className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={toggleExpandAll}
            className="p-1 hover:text-white hover:bg-harness-panel rounded transition"
            title="Expand / Collapse All"
          >
            <RotateCw className="w-3.5 h-3.5" />
          </button>
          {onRefresh && (
            <button
              onClick={onRefresh}
              className={`p-1 hover:text-white hover:bg-harness-panel rounded transition ${
                isLoading ? 'animate-spin text-sky-400' : ''
              }`}
              title="Refresh Repository Tree"
            >
              <RotateCw className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* New File / Folder Input Form */}
      {showNewDialog && (
        <form
          onSubmit={handleCreateSubmit}
          className="p-2 border-b border-harness-border/60 bg-harness-panel/50 flex items-center space-x-1.5"
        >
          {showNewDialog === 'file' ? (
            <FilePlus className="w-3.5 h-3.5 text-sky-400 shrink-0" />
          ) : (
            <FolderPlus className="w-3.5 h-3.5 text-amber-400 shrink-0" />
          )}
          <input
            autoFocus
            type="text"
            placeholder={
              showNewDialog === 'file' ? 'path/to/file.py' : 'path/to/new_dir'
            }
            value={newItemPath}
            onChange={(e) => setNewItemPath(e.target.value)}
            className="flex-1 bg-harness-bg border border-harness-border px-2 py-0.5 rounded text-xs text-gray-100 placeholder-gray-500 focus:outline-none focus:border-sky-500"
          />
          <button
            type="submit"
            className="px-2 py-0.5 bg-sky-600 hover:bg-sky-500 text-white rounded text-[11px] font-medium"
          >
            Create
          </button>
          <button
            type="button"
            onClick={() => {
              setShowNewDialog(null);
              setNewItemPath('');
            }}
            className="p-0.5 text-gray-400 hover:text-white rounded"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </form>
      )}

      {/* Search Input Filter */}
      <div className="p-2 border-b border-harness-border/40">
        <div className="relative">
          <Search className="w-3.5 h-3.5 absolute left-2 top-2 text-gray-500" />
          <input
            type="text"
            placeholder="Search files in repository..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-7 pr-6 py-1 bg-harness-bg border border-harness-border/80 rounded text-xs text-gray-200 placeholder-gray-500 focus:outline-none focus:border-sky-500"
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery('')}
              className="absolute right-1.5 top-1.5 text-gray-500 hover:text-gray-300 p-0.5"
            >
              <X className="w-3 h-3" />
            </button>
          )}
        </div>
      </div>

      {/* Tree Content */}
      <div className="flex-1 overflow-y-auto py-1">
        {isLoading && files.length === 0 ? (
          <div className="p-4 text-center text-xs text-gray-500 italic">
            Loading repository tree...
          </div>
        ) : filteredFiles.length === 0 ? (
          <div className="p-4 text-center text-xs text-gray-500">
            {searchQuery ? (
              <>
                <p>No matching files found.</p>
                <button
                  onClick={() => setSearchQuery('')}
                  className="mt-1 text-sky-400 hover:underline"
                >
                  Clear search
                </button>
              </>
            ) : (
              <p>Repository is empty.</p>
            )}
          </div>
        ) : (
          renderTree(filteredFiles)
        )}
      </div>

      {/* Repository Status Summary Footer */}
      <div className="h-6 px-3 border-t border-harness-border/40 bg-harness-bg/60 flex items-center justify-between text-[10px] text-gray-500 font-mono">
        <div className="flex items-center space-x-1">
          <FileCheck2 className="w-3 h-3 text-emerald-400" />
          <span>Synced with Harness</span>
        </div>
        <span>{files.length} items</span>
      </div>
    </div>
  );
};
