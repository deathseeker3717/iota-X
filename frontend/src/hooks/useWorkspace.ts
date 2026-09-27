/**
 * Workspace and Editor State Management Hook
 *
 * Implements the required architecture:
 * Repository API -> Explorer -> File selection -> Editor
 *
 * Utilizes the Cross-Platform Contract:
 * - RepositoryTree
 * - RepositoryFile
 * - FileChange
 * - EditorState
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  EditorState,
  FileChange,
  RepositoryFile,
  RepositoryNode,
  RepositoryTree,
} from '../types/contract';
import { repositoryApi } from '../services/repositoryApi';

export function useWorkspace() {
  // 1. Repository Tree State
  const [repositoryTree, setRepositoryTree] = useState<RepositoryTree | null>(null);
  const [isLoadingTree, setIsLoadingTree] = useState<boolean>(true);
  const [treeError, setTreeError] = useState<string | null>(null);

  // 2. Editor Session State (matching cross-platform EditorState)
  const [openFiles, setOpenFiles] = useState<RepositoryFile[]>([]);
  const [activeFilePath, setActiveFilePath] = useState<string | null>(null);
  const [modifiedFilePaths, setModifiedFilePaths] = useState<string[]>([]);
  const [isLoadingFile, setIsLoadingFile] = useState<boolean>(false);

  // Load Repository Tree on mount
  const refreshTree = useCallback(async () => {
    try {
      setIsLoadingTree(true);
      setTreeError(null);
      const tree = await repositoryApi.getTree();
      setRepositoryTree(tree);
      return tree;
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to fetch repository tree';
      setTreeError(msg);
      console.error('Failed to load repository tree:', err);
      return null;
    } finally {
      setIsLoadingTree(false);
    }
  }, []);

  // Initial mount: load tree and open default file
  useEffect(() => {
    async function init() {
      const tree = await refreshTree();
      if (tree && tree.nodes.length > 0) {
        // Open default session.py file via Repository API
        const defaultPath = 'src/auth/session.py';
        try {
          const file = await repositoryApi.getFile(defaultPath);
          setOpenFiles([file]);
          setActiveFilePath(defaultPath);
        } catch {
          // Fallback if not found: find first file in tree
          const findFirstFile = (nodes: RepositoryNode[]): string | null => {
            for (const n of nodes) {
              if (n.type === 'file') return n.path;
              if (n.children) {
                const sub = findFirstFile(n.children);
                if (sub) return sub;
              }
            }
            return null;
          };
          const first = findFirstFile(tree.nodes);
          if (first) {
            const file = await repositoryApi.getFile(first);
            setOpenFiles([file]);
            setActiveFilePath(first);
          }
        }
      }
    }
    init();
  }, [refreshTree]);

  // File selection: Explorer -> File selection -> Editor
  const selectFile = useCallback(
    async (path: string) => {
      // If already open, just switch active tab
      const existing = openFiles.find((f) => f.path === path);
      if (existing) {
        setActiveFilePath(path);
        return;
      }

      // Fetch file from backend Repository API
      try {
        setIsLoadingFile(true);
        const file = await repositoryApi.getFile(path);
        setOpenFiles((prev) => [...prev, file]);
        setActiveFilePath(file.path);
      } catch (err) {
        console.error(`Failed to load file content for ${path}:`, err);
      } finally {
        setIsLoadingFile(false);
      }
    },
    [openFiles]
  );

  // Close tab
  const closeTab = useCallback(
    (path: string) => {
      setOpenFiles((prev) => {
        const next = prev.filter((f) => f.path !== path);
        // If closing active file, switch to previous or last tab
        if (activeFilePath === path) {
          const remainingIndex = prev.findIndex((f) => f.path === path);
          if (next.length > 0) {
            const newIndex = Math.max(0, remainingIndex - 1);
            setActiveFilePath(next[newIndex].path);
          } else {
            setActiveFilePath(null);
          }
        }
        return next;
      });

      // Clear modified status if tab is closed
      setModifiedFilePaths((prev) => prev.filter((p) => p !== path));
    },
    [activeFilePath]
  );

  // In-memory content updates during editing
  const updateTabContent = useCallback((path: string, newContent: string) => {
    setOpenFiles((prev) =>
      prev.map((f) => (f.path === path ? { ...f, content: newContent } : f))
    );

    setModifiedFilePaths((prev) => (prev.includes(path) ? prev : [...prev, path]));
  }, []);

  // Save active file or specific path to backend Repository API
  const saveFile = useCallback(
    async (targetPath?: string) => {
      const path = targetPath || activeFilePath;
      if (!path) return false;

      const file = openFiles.find((f) => f.path === path);
      if (!file) return false;

      const change: FileChange = {
        path: file.path,
        content: file.content,
        changeType: 'edit',
        timestamp: new Date().toISOString(),
      };

      try {
        const res = await repositoryApi.saveFile(change);
        if (res.success) {
          // Remove from modified list
          setModifiedFilePaths((prev) => prev.filter((p) => p !== path));
          // Update file metadata
          setOpenFiles((prev) =>
            prev.map((f) => (f.path === path ? { ...f, lastModified: res.file.lastModified } : f))
          );
          return true;
        }
        return false;
      } catch (err) {
        console.error(`Failed to save file ${path}:`, err);
        return false;
      }
    },
    [activeFilePath, openFiles]
  );

  // Create new file
  const createNewFile = useCallback(
    async (path: string, initialContent = '') => {
      try {
        await repositoryApi.createNode(path, 'file', initialContent);
        await refreshTree();
        await selectFile(path);
        return true;
      } catch (err) {
        console.error('Failed to create file:', err);
        return false;
      }
    },
    [refreshTree, selectFile]
  );

  // Create new folder
  const createNewFolder = useCallback(
    async (path: string) => {
      try {
        await repositoryApi.createNode(path, 'directory');
        await refreshTree();
        return true;
      } catch (err) {
        console.error('Failed to create folder:', err);
        return false;
      }
    },
    [refreshTree]
  );

  // Currently active file object
  const activeFile = useMemo(() => {
    return openFiles.find((f) => f.path === activeFilePath) || null;
  }, [openFiles, activeFilePath]);

  // Combined EditorState representation
  const editorState: EditorState = useMemo(
    () => ({
      openFiles,
      activeFilePath,
      modifiedFilePaths,
    }),
    [openFiles, activeFilePath, modifiedFilePaths]
  );

  return {
    // Tree & Explorer
    repositoryTree,
    isLoadingTree,
    treeError,
    refreshTree,
    createNewFile,
    createNewFolder,

    // Editor & Tabs
    editorState,
    openFiles,
    activeFilePath,
    activeFile,
    modifiedFilePaths,
    isLoadingFile,
    selectFile,
    closeTab,
    updateTabContent,
    saveFile,

    // Compatibility aliases for existing components:
    fileTree: repositoryTree ? repositoryTree.nodes : [],
    openTabs: openFiles.map((f) => ({
      ...f,
      isModified: modifiedFilePaths.includes(f.path),
    })),
    activeTabId: activeFilePath,
    activeTab: activeFile
      ? {
          ...activeFile,
          isModified: modifiedFilePaths.includes(activeFile.path),
        }
      : null,
    openFile: (node: { path: string; [key: string]: any }) => selectFile(node.path),
    setActiveTabId: (id: string) => selectFile(id),
    saveActiveFile: () => saveFile(),
  };
}
