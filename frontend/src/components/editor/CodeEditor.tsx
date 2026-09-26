import React, { useState, useEffect, useRef } from 'react';
import Editor, { OnMount } from '@monaco-editor/react';
import {
  FileCode,
  Save,
  Lock,
  Unlock,
  Check,
  Code2,
} from 'lucide-react';
import { RepositoryFile } from '../../types/contract';

interface CodeEditorProps {
  activeTab: (RepositoryFile & { isModified?: boolean }) | null;
  onChangeContent: (path: string, content: string) => void;
  onSave: () => void;
}

export const CodeEditor: React.FC<CodeEditorProps> = ({
  activeTab,
  onChangeContent,
  onSave,
}) => {
  const [isReadOnly, setIsReadOnly] = useState<boolean>(false);
  const [cursorPos, setCursorPos] = useState<{ line: number; col: number }>({ line: 1, col: 1 });
  const [justSaved, setJustSaved] = useState<boolean>(false);
  const editorRef = useRef<any>(null);

  // Map file extensions to Monaco language identifiers
  const getMonacoLanguage = (path: string, langHint?: string): string => {
    if (langHint && langHint !== 'plaintext') return langHint;
    const ext = path.split('.').pop()?.toLowerCase();
    switch (ext) {
      case 'py':
        return 'python';
      case 'ts':
        return 'typescript';
      case 'tsx':
        return 'typescript';
      case 'js':
        return 'javascript';
      case 'jsx':
        return 'javascript';
      case 'json':
        return 'json';
      case 'html':
        return 'html';
      case 'css':
        return 'css';
      case 'md':
        return 'markdown';
      case 'toml':
        return 'ini';
      case 'yaml':
      case 'yml':
        return 'yaml';
      case 'sh':
      case 'bash':
        return 'shell';
      case 'sql':
        return 'sql';
      default:
        return 'plaintext';
    }
  };

  // Keyboard shortcut listener for Ctrl+S / Cmd+S
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 's') {
        e.preventDefault();
        onSave();
        setJustSaved(true);
        setTimeout(() => setJustSaved(false), 1500);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onSave]);

  const handleEditorMount: OnMount = (editor, monaco) => {
    editorRef.current = editor;

    // Track cursor movements
    editor.onDidChangeCursorPosition((e) => {
      setCursorPos({
        line: e.position.lineNumber,
        col: e.position.column,
      });
    });

    // Add Cmd+S / Ctrl+S action directly in Monaco
    editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS, () => {
      onSave();
      setJustSaved(true);
      setTimeout(() => setJustSaved(false), 1500);
    });
  };

  // Handle empty state
  if (!activeTab) {
    return (
      <div className="h-full flex flex-col items-center justify-center bg-harness-bg text-gray-500 select-none p-6">
        <div className="w-16 h-16 rounded-2xl bg-harness-panel/50 border border-harness-border flex items-center justify-center mb-4 text-sky-400/80 shadow-inner">
          <Code2 className="w-8 h-8" />
        </div>
        <p className="text-sm font-semibold text-gray-300">No File Open</p>
        <p className="text-xs text-gray-500 mt-1 max-w-sm text-center">
          Select a file from the Explorer on the left, or use the AI Assistant to generate code and inspect repository files.
        </p>
        <div className="mt-4 flex items-center space-x-2 text-[11px] text-gray-400 font-mono bg-harness-panel/60 px-3 py-1.5 rounded border border-harness-border/60">
          <span>Shortcuts:</span>
          <span className="bg-harness-bg px-1.5 py-0.5 rounded text-gray-300">⌘S / Ctrl+S to save</span>
        </div>
      </div>
    );
  }

  const pathParts = activeTab.path.split('/');
  const language = getMonacoLanguage(activeTab.path, activeTab.language);

  return (
    <div className="h-full flex flex-col bg-harness-bg">
      {/* Breadcrumb Path & Action Bar */}
      <div className="h-7 px-3 bg-harness-bg/90 border-b border-harness-border/50 flex items-center justify-between text-xs text-gray-400 select-none">
        {/* Breadcrumb */}
        <div className="flex items-center space-x-1.5 truncate">
          <FileCode className="w-3.5 h-3.5 text-sky-400 shrink-0" />
          {pathParts.map((part, idx) => (
            <React.Fragment key={idx}>
              {idx > 0 && <span className="text-gray-600">/</span>}
              <span className={idx === pathParts.length - 1 ? 'text-gray-200 font-medium' : ''}>
                {part}
              </span>
            </React.Fragment>
          ))}
          {activeTab.isModified && (
            <span className="text-sky-400 text-[10px] ml-2 bg-sky-500/15 border border-sky-500/30 px-1.5 py-0.2 rounded font-mono">
              ● Unsaved
            </span>
          )}
        </div>

        {/* Editor Controls */}
        <div className="flex items-center space-x-2">
          {/* Read-only toggle */}
          <button
            onClick={() => setIsReadOnly(!isReadOnly)}
            className={`p-1 rounded transition ${
              isReadOnly
                ? 'text-amber-400 hover:text-amber-300 bg-amber-500/10'
                : 'text-gray-400 hover:text-white'
            }`}
            title={isReadOnly ? 'Read-only mode (Click to edit)' : 'Editable (Click to lock)'}
          >
            {isReadOnly ? <Lock className="w-3.5 h-3.5" /> : <Unlock className="w-3.5 h-3.5" />}
          </button>

          {/* Save Button */}
          <button
            onClick={() => {
              onSave();
              setJustSaved(true);
              setTimeout(() => setJustSaved(false), 1500);
            }}
            className={`flex items-center space-x-1 text-xs px-2.5 py-0.5 rounded transition ${
              justSaved
                ? 'bg-emerald-600/30 text-emerald-300 border border-emerald-500/40'
                : activeTab.isModified
                ? 'bg-sky-600 hover:bg-sky-500 text-white font-medium shadow-xs'
                : 'text-gray-400 hover:text-white hover:bg-harness-panel'
            }`}
            title="Save file (⌘S / Ctrl+S)"
          >
            {justSaved ? (
              <>
                <Check className="w-3 h-3 text-emerald-400" />
                <span>Saved</span>
              </>
            ) : (
              <>
                <Save className="w-3 h-3" />
                <span>Save</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Monaco Code Editor Container */}
      <div className="flex-1 w-full h-full overflow-hidden relative">
        <Editor
          height="100%"
          language={language}
          value={activeTab.content}
          theme="vs-dark"
          onMount={handleEditorMount}
          options={{
            readOnly: isReadOnly,
            fontSize: 13,
            fontFamily: '"JetBrains Mono", Menlo, Monaco, Consolas, monospace',
            fontLigatures: true,
            tabSize: 4,
            insertSpaces: true,
            minimap: {
              enabled: true,
              maxColumn: 80,
              renderCharacters: false,
            },
            scrollBeyondLastLine: false,
            automaticLayout: true,
            lineNumbers: 'on',
            renderWhitespace: 'selection',
            bracketPairColorization: { enabled: true },
            guides: {
              bracketPairs: true,
              indentation: true,
            },
            cursorBlinking: 'smooth',
            smoothScrolling: true,
            padding: { top: 10, bottom: 10 },
            wordWrap: 'off',
            renderLineHighlight: 'all',
          }}
          onChange={(value) => {
            if (value !== undefined) {
              onChangeContent(activeTab.path, value);
            }
          }}
          loading={
            <div className="flex items-center justify-center h-full text-gray-500 text-xs font-mono">
              Loading Code-OSS Monaco editor...
            </div>
          }
        />
      </div>

      {/* Editor Status Bar Footer */}
      <div className="h-6 px-3 bg-harness-surface border-t border-harness-border/60 flex items-center justify-between text-[11px] text-gray-400 font-mono select-none">
        <div className="flex items-center space-x-3">
          <span>Ln {cursorPos.line}, Col {cursorPos.col}</span>
          <span>Spaces: 4</span>
          <span>UTF-8</span>
        </div>
        <div className="flex items-center space-x-3">
          <span className="capitalize">{language}</span>
          <span className="text-gray-500">
            {activeTab.content.split('\n').length} lines
          </span>
        </div>
      </div>
    </div>
  );
};
