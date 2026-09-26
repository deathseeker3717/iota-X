/**
 * Shared Git Integration Contract Models for Frontend
 *
 * Models:
 * - GitChange: Represents modified, added, deleted, or untracked file
 * - GitStatus: Working tree status, branches, ahead/behind
 * - GitDiff: Unified diff representation
 * - GitCommit: Structured commit log entry
 */

export type GitChangeStatus = 'modified' | 'added' | 'deleted' | 'untracked';

export interface GitChange {
  file: string;
  status: GitChangeStatus;
  staged: boolean;
  additions: number;
  deletions: number;
  oldPath?: string;
  diff?: string;
}

export interface GitStatus {
  branch: string;
  isClean: boolean;
  changes: GitChange[];
  stagedFiles: string[];
  unstagedFiles: string[];
  untrackedFiles: string[];
  ahead: number;
  behind: number;
  rawOutput?: string;
}

export interface GitDiff {
  filePath?: string;
  staged: boolean;
  commit?: string;
  diffText: string;
  additions: number;
  deletions: number;
  changes?: GitChange[];
}

export interface GitCommit {
  hash: string;
  shortHash: string;
  author: string;
  date: string;
  message: string;
  parentHashes?: string[];
}
