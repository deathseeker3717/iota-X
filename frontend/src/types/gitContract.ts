/**
 * AI Coding Harness — Shared Cross-Platform Git Integration Contract
 *
 * Defines models and API interfaces for repository inspection:
 * - git_status: Working directory status (changed, staged, untracked)
 * - git_diff: Unified diffs of modifications
 * - git_log: Commit history logs
 * - git_show: Details or file snapshots of specific commits
 *
 * Clients MUST NOT execute Git commands directly on host machines.
 */

export type GitFileStatus = 'modified' | 'added' | 'deleted' | 'untracked';

export interface GitChange {
  file: string;
  status: GitFileStatus;
  additions: number;
  deletions: number;
  diff?: string;
  staged?: boolean;
  oldPath?: string;
}

export interface GitStatus {
  branch: string;
  isClean: boolean;
  stagedFiles: string[];
  unstagedFiles: string[];
  untrackedFiles: string[];
  changes: GitChange[];
  rawOutput: string;
}

export interface GitDiff {
  file?: string;
  unifiedDiff: string;
  staged: boolean;
  commit?: string;
  additions: number;
  deletions: number;
}

export interface GitCommit {
  hash: string;
  shortHash: string;
  author: string;
  date: string;
  message: string;
  diff?: string;
}

export interface GitDiffOptions {
  staged?: boolean;
  filePath?: string;
  commit?: string;
}

export interface GitLogOptions {
  maxCount?: number;
  filePath?: string;
}

export interface IGitApiService {
  getStatus(): Promise<GitStatus>;
  getDiff(options?: GitDiffOptions): Promise<GitDiff>;
  getLog(options?: GitLogOptions): Promise<GitCommit[]>;
  getShow(commitOrRef?: string, filePath?: string): Promise<string>;
}
