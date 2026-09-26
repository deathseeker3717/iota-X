/**
 * useGit Custom Hook
 *
 * Provides reactive Git state and operations using the centralized Git API.
 */

import { useState, useEffect, useCallback } from 'react';
import {
  GitChange,
  GitCommit,
  GitDiff,
  GitStatus,
} from '../types/gitContract';
import { gitApi, GitApiService } from '../services/gitApi';

export interface UseGitOptions {
  api?: GitApiService;
  autoFetch?: boolean;
}

export interface UseGitReturn {
  status: GitStatus | null;
  changes: GitChange[];
  modifiedFiles: GitChange[];
  addedFiles: GitChange[];
  deletedFiles: GitChange[];
  untrackedFiles: GitChange[];
  commits: GitCommit[];
  activeDiff: GitDiff | null;
  selectedFile: string | null;
  selectedCommit: GitCommit | null;
  commitDetails: string | null;
  isLoading: boolean;
  isRefreshing: boolean;
  error: string | null;
  refreshGit: () => Promise<void>;
  selectFile: (filePath: string) => Promise<void>;
  selectCommit: (commit: GitCommit) => Promise<void>;
  clearSelectedCommit: () => void;
}

export const useGit = (options: UseGitOptions = {}): UseGitReturn => {
  const api = options.api || gitApi;

  const [status, setStatus] = useState<GitStatus | null>(null);
  const [commits, setCommits] = useState<GitCommit[]>([]);
  const [activeDiff, setActiveDiff] = useState<GitDiff | null>(null);
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [selectedCommit, setSelectedCommit] = useState<GitCommit | null>(null);
  const [commitDetails, setCommitDetails] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchStatusAndHistory = useCallback(
    async (isBackground: boolean = false) => {
      if (!isBackground) setIsLoading(true);
      else setIsRefreshing(true);
      setError(null);

      try {
        const [gitStatus, gitLog] = await Promise.all([
          api.getStatus(),
          api.getLog({ maxCount: 15 }),
        ]);

        setStatus(gitStatus);
        setCommits(gitLog);

        // Auto-select first changed file if none selected
        if (!selectedFile && gitStatus.changes.length > 0) {
          const firstFile = gitStatus.changes[0].file;
          setSelectedFile(firstFile);
          const diff = await api.getDiff({ filePath: firstFile });
          setActiveDiff(diff);
        } else if (selectedFile) {
          const diff = await api.getDiff({ filePath: selectedFile });
          setActiveDiff(diff);
        }
      } catch (err: any) {
        setError(err?.message || 'Failed to fetch Git status');
      } finally {
        setIsLoading(false);
        setIsRefreshing(false);
      }
    },
    [api, selectedFile]
  );

  useEffect(() => {
    if (options.autoFetch !== false) {
      fetchStatusAndHistory(false);
    }
  }, [fetchStatusAndHistory, options.autoFetch]);

  const selectFile = useCallback(
    async (filePath: string) => {
      setSelectedFile(filePath);
      setSelectedCommit(null);
      setCommitDetails(null);
      try {
        const diff = await api.getDiff({ filePath });
        setActiveDiff(diff);
      } catch (err: any) {
        setError(err?.message || `Failed to fetch diff for ${filePath}`);
      }
    },
    [api]
  );

  const selectCommit = useCallback(
    async (commit: GitCommit) => {
      setSelectedCommit(commit);
      try {
        const details = await api.getShow({ commitOrRef: commit.hash });
        setCommitDetails(details);
      } catch (err: any) {
        setError(err?.message || `Failed to show commit ${commit.shortHash}`);
      }
    },
    [api]
  );

  const clearSelectedCommit = useCallback(() => {
    setSelectedCommit(null);
    setCommitDetails(null);
  }, []);

  const refreshGit = useCallback(async () => {
    await fetchStatusAndHistory(true);
  }, [fetchStatusAndHistory]);

  const changes = status?.changes || [];
  const modifiedFiles = changes.filter((c) => c.status === 'modified');
  const addedFiles = changes.filter((c) => c.status === 'added');
  const deletedFiles = changes.filter((c) => c.status === 'deleted');
  const untrackedFiles = changes.filter((c) => c.status === 'untracked');

  return {
    status,
    changes,
    modifiedFiles,
    addedFiles,
    deletedFiles,
    untrackedFiles,
    commits,
    activeDiff,
    selectedFile,
    selectedCommit,
    commitDetails,
    isLoading,
    isRefreshing,
    error,
    refreshGit,
    selectFile,
    selectCommit,
    clearSelectedCommit,
  };
};
