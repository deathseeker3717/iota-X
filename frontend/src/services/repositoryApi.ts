/**
 * Repository API Service
 *
 * Provides typed access to the repository filesystem and metadata via the backend Harness API.
 * Adheres strictly to the Cross-Platform Contract (RepositoryTree, RepositoryFile, FileChange).
 * Browser code NEVER directly accesses the local filesystem.
 */

import {
  FileChange,
  RepositoryFile,
  RepositoryNode,
  RepositoryTree,
} from '../types/contract';

export interface RepositoryApiService {
  /** Fetch the hierarchical directory tree of the repository */
  getTree(rootPath?: string): Promise<RepositoryTree>;

  /** Fetch a specific file's content and metadata */
  getFile(path: string): Promise<RepositoryFile>;

  /** Persist edits to a file */
  saveFile(change: FileChange): Promise<{ success: boolean; file: RepositoryFile }>;

  /** Create a new file or directory */
  createNode(path: string, type: 'file' | 'directory', initialContent?: string): Promise<RepositoryNode>;

  /** Delete a file or directory */
  deleteNode(path: string): Promise<boolean>;

  /** Search filenames and paths across the repository */
  searchFiles(query: string): Promise<string[]>;
}

// ============================================================================
// Concrete Implementation: MockRepositoryApiService
// Pre-populated with authentic repository structure and source files.
// ============================================================================

const DEFAULT_REPO_FILES: Record<string, { content: string; language: string }> = {
  'src/harness/tools/filesystem.py': {
    language: 'python',
    content: `"""Filesystem tools for the AI Coding Harness.

Provides safe, sandboxed file operations: listing, reading, writing, and editing files.
"""

from __future__ import annotations

import fnmatch
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

class FilesystemTool:
    """Provides sandboxed filesystem operations."""

    def __init__(self, root_dir: str = ".", enforce_sandbox: bool = True) -> None:
        self.root_dir = Path(root_dir).resolve()
        self.enforce_sandbox = enforce_sandbox

    def list_files(self, directory: str = ".") -> List[str]:
        """List files relative to root directory, ignoring excluded patterns."""
        results = []
        target = (self.root_dir / directory).resolve()
        for root, _, files in os.walk(target):
            for file in files:
                rel = os.path.relpath(os.path.join(root, file), self.root_dir)
                results.append(rel)
        return sorted(results)

    def read_file(self, path: str) -> str:
        """Safely read text file content."""
        full_path = (self.root_dir / path).resolve()
        return full_path.read_text(encoding="utf-8")

    def write_file(self, path: str, content: str) -> bool:
        """Write content to file within sandbox."""
        full_path = (self.root_dir / path).resolve()
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content, encoding="utf-8")
        return True
`,
  },
  'src/harness/tools/search.py': {
    language: 'python',
    content: `"""Repository search tools for finding files, symbols, references, and imports."""

from __future__ import annotations
from typing import Any, Dict, List, Optional

class SearchTool:
    def __init__(self, root_dir: str = ".") -> None:
        self.root_dir = root_dir

    def search_symbol(self, symbol_name: str) -> List[Dict[str, Any]]:
        """Locates symbol definitions across indexed Python modules."""
        return [
            {"symbol": symbol_name, "file": "src/auth/session.py", "line": 97, "kind": "class"}
        ]

    def find_references(self, symbol_name: str) -> List[Dict[str, Any]]:
        """Finds cross-file references to a symbol."""
        return [
            {"file": "tests/test_auth.py", "line": 120, "context": "manager = SessionManager()"}
        ]
`,
  },
  'src/harness/repository/indexer.py': {
    language: 'python',
    content: `"""Repository indexer for the AI Coding Harness.

Builds an inverted index of:
- files
- functions and classes
- imports and dependency graphs
- cross-file symbol references
- full-text token inverted index
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Set

@dataclass
class FileIndexEntry:
    file_path: str
    mtime: float
    size_bytes: int
    content_hash: str
    line_count: int

class RepositoryIndexer:
    def __init__(self, root_dir: str = ".") -> None:
        self.root_dir = root_dir
        self.entries: Dict[str, FileIndexEntry] = {}

    def index_repository(self) -> int:
        """Indexes all supported source files in the repository."""
        return len(self.entries)
`,
  },
  'src/harness/repository/context.py': {
    language: 'python',
    content: `"""Repository context selection for the AI Coding Harness.

Implements query-driven context selection:
Issue / Query -> Repository Search -> Relevant Files -> Relevant Functions/Classes.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List

@dataclass
class RelevantFile:
    file_path: str
    score: float
    rationale: str

class RepositoryContextManager:
    def find_relevant_context(self, query: str) -> List[RelevantFile]:
        return [
            RelevantFile("src/auth/session.py", 0.95, "Contains token timeout logic"),
            RelevantFile("tests/test_auth.py", 0.88, "Auth test suite verification")
        ]
`,
  },
  'src/harness/orchestrator/orchestrator.py': {
    language: 'python',
    content: `"""Central Orchestrator managing specialized agent roles and workflow."""

from dataclasses import dataclass
from typing import Any, Dict

@dataclass
class TaskContext:
    task_id: str
    description: str
    state: str = "INITIALIZED"

class CentralOrchestrator:
    def __init__(self) -> None:
        self.iteration_limit = 10
        self.current_state = "IDLE"

    async def execute_task(self, prompt: str) -> Dict[str, Any]:
        """Runs the autonomous harness cycle: Plan -> Code -> Verify."""
        return {"status": "SUCCESS", "verified": True}
`,
  },
  'src/auth/session.py': {
    language: 'python',
    content: `"""User Session and JWT management."""

import time
from typing import Optional

class SessionManager:
    """Manages active user sessions with configurable timeout."""

    def __init__(self, session_timeout_seconds: int = 300) -> None:
        self.session_timeout_seconds = session_timeout_seconds
        self.active_sessions: dict = {}

    def is_session_valid(self, session_id: str, last_activity: float) -> bool:
        """Verify if session has exceeded expiration limit."""
        elapsed = time.time() - last_activity
        if elapsed > self.session_timeout_seconds:
            return False
        return True

    def refresh_session(self, session_id: str) -> bool:
        """Refresh expiration timestamp for an active session."""
        if session_id in self.active_sessions:
            self.active_sessions[session_id] = time.time()
            return True
        return False
`,
  },
  'tests/test_auth.py': {
    language: 'python',
    content: `"""Tests for session and authentication flows."""

import time
import pytest
from src.auth.session import SessionManager

def test_session_expiration():
    manager = SessionManager(session_timeout_seconds=2)
    now = time.time()
    assert manager.is_session_valid("user_1", now) is True
    assert manager.is_session_valid("user_1", now - 5) is False

def test_session_refresh():
    manager = SessionManager(session_timeout_seconds=60)
    manager.active_sessions["s123"] = time.time() - 30
    assert manager.refresh_session("s123") is True
`,
  },
  'tests/test_filesystem_tool.py': {
    language: 'python',
    content: `"""Unit tests for the sandboxed filesystem tool."""

import pytest
from src.harness.tools.filesystem import FilesystemTool

def test_list_files(tmp_path):
    tool = FilesystemTool(root_dir=str(tmp_path))
    (tmp_path / "hello.py").write_text("print('hello')")
    files = tool.list_files()
    assert "hello.py" in files
`,
  },
  'README.md': {
    language: 'markdown',
    content: `# AI Coding Harness (Hackathon 2026)

Cross-platform autonomous AI coding agent harness.

## Architecture

- **Web Client**: React + TypeScript + Monaco Code-OSS
- **macOS Client**: Native Swift / SwiftUI (planned)
- **Android Client**: Native Kotlin / Jetpack Compose (planned)
- **Shared Backend**: Python AI Coding Harness (Agents + Tools + Repository Intelligence)
`,
  },
  'pyproject.toml': {
    language: 'toml',
    content: `[project]
name = "ai-coding-harness"
version = "0.1.0"
description = "Autonomous AI Coding Harness"
readme = "README.md"
requires-python = ">=3.10"
dependencies = [
    "pyyaml>=6.0.1",
    "python-dotenv>=1.0.0",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
`,
  },
};

export class MockRepositoryApiService implements RepositoryApiService {
  private files: Record<string, { content: string; language: string }> = {
    ...DEFAULT_REPO_FILES,
  };

  /** Construct hierarchical tree from flat path list */
  private buildTreeFromFiles(): RepositoryNode[] {
    const rootNodes: RepositoryNode[] = [];
    const dirMap: Record<string, RepositoryNode> = {};

    const getOrCreateDir = (dirPath: string): RepositoryNode => {
      if (dirMap[dirPath]) return dirMap[dirPath];

      const parts = dirPath.split('/');
      const name = parts[parts.length - 1];
      const node: RepositoryNode = {
        id: dirPath,
        name,
        path: dirPath,
        type: 'directory',
        children: [],
      };
      dirMap[dirPath] = node;

      if (parts.length === 1) {
        rootNodes.push(node);
      } else {
        const parentPath = parts.slice(0, -1).join('/');
        const parent = getOrCreateDir(parentPath);
        if (parent.children && !parent.children.some((c) => c.path === node.path)) {
          parent.children.push(node);
        }
      }
      return node;
    };

    const sortedPaths = Object.keys(this.files).sort();

    for (const filePath of sortedPaths) {
      const parts = filePath.split('/');
      const fileName = parts[parts.length - 1];
      const fileData = this.files[filePath];

      const fileNode: RepositoryNode = {
        id: filePath,
        name: fileName,
        path: filePath,
        type: 'file',
        size: fileData.content.length,
        language: fileData.language,
        lastModified: new Date().toISOString(),
      };

      if (parts.length === 1) {
        rootNodes.push(fileNode);
      } else {
        const parentPath = parts.slice(0, -1).join('/');
        const parent = getOrCreateDir(parentPath);
        if (parent.children) {
          parent.children.push(fileNode);
        }
      }
    }

    return rootNodes;
  }

  async getTree(_rootPath?: string): Promise<RepositoryTree> {
    const nodes = this.buildTreeFromFiles();
    const totalFiles = Object.keys(this.files).length;

    // Count directories
    let totalDirs = 0;
    const countDirs = (items: RepositoryNode[]) => {
      for (const item of items) {
        if (item.type === 'directory') {
          totalDirs++;
          if (item.children) countDirs(item.children);
        }
      }
    };
    countDirs(nodes);

    return {
      rootPath: '.',
      repositoryName: 'iota-X',
      branch: 'tools-repository',
      nodes,
      totalFiles,
      totalDirectories: totalDirs,
    };
  }

  async getFile(path: string): Promise<RepositoryFile> {
    const entry = this.files[path];
    if (!entry) {
      // Return safe blank file if not found
      return {
        id: path,
        path,
        name: path.split('/').pop() || path,
        content: `# File ${path}\n# Empty file created.\n`,
        language: this.detectLanguage(path),
        size: 0,
        encoding: 'utf-8',
        lineCount: 2,
        lastModified: new Date().toISOString(),
      };
    }

    const lines = entry.content.split('\n').length;
    return {
      id: path,
      path,
      name: path.split('/').pop() || path,
      content: entry.content,
      language: entry.language,
      size: entry.content.length,
      encoding: 'utf-8',
      lineCount: lines,
      lastModified: new Date().toISOString(),
    };
  }

  async saveFile(change: FileChange): Promise<{ success: boolean; file: RepositoryFile }> {
    const language = this.detectLanguage(change.path);
    this.files[change.path] = {
      content: change.content,
      language,
    };

    const savedFile: RepositoryFile = {
      id: change.path,
      path: change.path,
      name: change.path.split('/').pop() || change.path,
      content: change.content,
      language,
      size: change.content.length,
      encoding: 'utf-8',
      lineCount: change.content.split('\n').length,
      lastModified: change.timestamp || new Date().toISOString(),
    };

    return { success: true, file: savedFile };
  }

  async createNode(
    path: string,
    type: 'file' | 'directory',
    initialContent = ''
  ): Promise<RepositoryNode> {
    const name = path.split('/').pop() || path;

    if (type === 'file') {
      const language = this.detectLanguage(path);
      this.files[path] = { content: initialContent, language };
      return {
        id: path,
        name,
        path,
        type: 'file',
        size: initialContent.length,
        language,
        lastModified: new Date().toISOString(),
      };
    } else {
      // directory
      return {
        id: path,
        name,
        path,
        type: 'directory',
        children: [],
      };
    }
  }

  async deleteNode(path: string): Promise<boolean> {
    if (this.files[path]) {
      delete this.files[path];
      return true;
    }
    // Delete any children under directory
    let found = false;
    for (const key of Object.keys(this.files)) {
      if (key.startsWith(path + '/')) {
        delete this.files[key];
        found = true;
      }
    }
    return found;
  }

  async searchFiles(query: string): Promise<string[]> {
    const q = query.toLowerCase();
    return Object.keys(this.files).filter((path) => path.toLowerCase().includes(q));
  }

  private detectLanguage(fileName: string): string {
    const ext = fileName.split('.').pop()?.toLowerCase() || '';
    const langMap: Record<string, string> = {
      py: 'python',
      ts: 'typescript',
      tsx: 'typescript',
      js: 'javascript',
      jsx: 'javascript',
      json: 'json',
      md: 'markdown',
      toml: 'toml',
      yaml: 'yaml',
      yml: 'yaml',
      sh: 'shell',
      bash: 'shell',
      css: 'css',
      html: 'html',
      sql: 'sql',
    };
    return langMap[ext] || 'plaintext';
  }
}

export const repositoryApi: RepositoryApiService = new MockRepositoryApiService();
