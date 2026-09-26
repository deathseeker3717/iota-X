import React, { useState, useRef, useEffect } from 'react';
import { Header } from '../components/layout/Header';
import { FileExplorer } from '../components/explorer/FileExplorer';
import { TabBar } from '../components/editor/TabBar';
import { CodeEditor } from '../components/editor/CodeEditor';
import { ChatPanel } from '../components/chat/ChatPanel';
import { BottomPanel } from '../components/bottom/BottomPanel';
import { useWorkspace } from '../hooks/useWorkspace';
import { useHarness } from '../hooks/useHarness';
import { ActiveBottomTab } from '../types';

export const Workspace: React.FC = () => {
  const {
    fileTree,
    openTabs,
    activeTabId,
    activeTab,
    modifiedFilePaths,
    isLoadingTree,
    refreshTree,
    createNewFile,
    createNewFolder,
    openFile,
    closeTab,
    setActiveTabId,
    updateTabContent,
    saveActiveFile,
  } = useWorkspace();

  const {
    conversations,
    activeConversationId,
    selectConversation,
    startNewTask,
    messages,
    isGenerating,
    sendMessage,
    regenerateLastMessage,
    retryMessage,
    clearChat,
    stopGeneration,
    attachments,
    addAttachments,
    removeAttachment,
    agentSteps,
    isAgentRunning,
    terminalHistory,
    isTerminalExecuting,
    runTerminalCommand,
    cancelTerminalCommand,
    clearTerminal,
    verificationResult,
    isRunningVerification,
    runVerification,
    gitStatus,
    gitChanges,
    gitCommits,
    activeGitDiff,
    selectedGitFile,
    selectedGitCommit,
    gitCommitDetails,
    isGitLoading,
    isGitRefreshing,
    refreshGit,
    selectGitFile,
    selectGitCommit,
    clearGitCommit,
  } = useHarness();

  // Panel sizing & state
  const [activeBottomTab, setActiveBottomTab] = useState<ActiveBottomTab>('terminal');
  const [explorerWidth, setExplorerWidth] = useState<number>(260);
  const [chatWidth, setChatWidth] = useState<number>(380);
  const [bottomHeight, setBottomHeight] = useState<number>(240);
  const [isBottomMaximized, setIsBottomMaximized] = useState<boolean>(false);
  const [isBottomCollapsed, setIsBottomCollapsed] = useState<boolean>(false);

  // Resize dragging references
  const isDraggingExplorer = useRef(false);
  const isDraggingChat = useRef(false);
  const isDraggingBottom = useRef(false);

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (isDraggingExplorer.current) {
        // Minimum 160px, maximum 450px
        const newWidth = Math.max(160, Math.min(e.clientX, 450));
        setExplorerWidth(newWidth);
      }
      if (isDraggingChat.current) {
        // Minimum 280px, maximum 650px
        const newWidth = Math.max(280, Math.min(window.innerWidth - e.clientX, 650));
        setChatWidth(newWidth);
      }
      if (isDraggingBottom.current) {
        // Minimum 100px, maximum 75vh
        const newHeight = Math.max(100, Math.min(window.innerHeight - e.clientY, window.innerHeight * 0.75));
        setBottomHeight(newHeight);
      }
    };

    const handleMouseUp = () => {
      isDraggingExplorer.current = false;
      isDraggingChat.current = false;
      isDraggingBottom.current = false;
      document.body.style.cursor = 'default';
    };

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, []);

  // Quick helper to open a file by relative path from anywhere
  const handleOpenFileByPath = (path: string) => {
    openFile({ path });
  };

  return (
    <div className="flex flex-col h-screen w-screen overflow-hidden bg-harness-bg font-sans">
      {/* 1. Header: AI Coding Harness | Repository | Settings */}
      <Header
        currentRepo="iota-X"
        currentBranch="tools-repository"
        onRunTests={() => {
          setActiveBottomTab('tests');
          setIsBottomCollapsed(false);
          runVerification();
        }}
        isAgentRunning={isAgentRunning}
      />

      {/* 2. Main Workspace Layout */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Column: Explorer */}
        <div
          style={{ width: `${explorerWidth}px` }}
          className="h-full border-r border-harness-border flex flex-col shrink-0 overflow-hidden"
        >
          <FileExplorer
            files={fileTree}
            activeFilePath={activeTabId}
            modifiedFilePaths={modifiedFilePaths}
            onSelectFile={openFile}
            onRefresh={refreshTree}
            onCreateFile={createNewFile}
            onCreateFolder={createNewFolder}
            isLoading={isLoadingTree}
          />
        </div>

        {/* Split Resizer: Explorer <-> Code Editor */}
        <div
          onMouseDown={() => {
            isDraggingExplorer.current = true;
            document.body.style.cursor = 'col-resize';
          }}
          className="w-1 hover:w-1.5 bg-transparent hover:bg-sky-500/50 cursor-col-resize z-20 transition-all select-none"
        />

        {/* Center Column & Bottom Dock: Code Editor and Bottom Panel */}
        <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
          {/* Top: Code Editor */}
          <div
            className={`flex-1 flex flex-col min-h-0 ${
              isBottomMaximized ? 'hidden' : 'block'
            }`}
          >
            <TabBar
              tabs={openTabs}
              activeTabId={activeTabId}
              onSelectTab={setActiveTabId}
              onCloseTab={closeTab}
            />
            <div className="flex-1 overflow-hidden">
              <CodeEditor
                activeTab={activeTab}
                onChangeContent={updateTabContent}
                onSave={saveActiveFile}
              />
            </div>
          </div>

          {/* Split Resizer: Code Editor <-> Bottom Panel */}
          {!isBottomCollapsed && !isBottomMaximized && (
            <div
              onMouseDown={() => {
                isDraggingBottom.current = true;
                document.body.style.cursor = 'row-resize';
              }}
              className="h-1 hover:h-1.5 bg-transparent hover:bg-sky-500/50 cursor-row-resize z-20 transition-all select-none"
            />
          )}

          {/* Bottom Dock: Terminal | Tests | Git Diff | Agent Activity */}
          <div
            style={{
              height: isBottomCollapsed
                ? '36px'
                : isBottomMaximized
                ? '100%'
                : `${bottomHeight}px`,
            }}
            className="shrink-0 transition-all duration-100 overflow-hidden"
          >
            <BottomPanel
              activeTab={activeBottomTab}
              onSelectTab={setActiveBottomTab}
              terminalHistory={terminalHistory}
              onRunTerminalCommand={runTerminalCommand}
              onClearTerminal={clearTerminal}
              isTerminalExecuting={isTerminalExecuting}
              onCancelTerminalCommand={cancelTerminalCommand}
              verificationResult={verificationResult}
              isRunningVerification={isRunningVerification}
              onRunVerification={runVerification}
              onAskAgentToFix={(msg) => sendMessage(msg)}
              gitStatus={gitStatus}
              gitChanges={gitChanges}
              gitCommits={gitCommits}
              activeGitDiff={activeGitDiff}
              selectedGitFile={selectedGitFile}
              selectedGitCommit={selectedGitCommit}
              gitCommitDetails={gitCommitDetails}
              isGitLoading={isGitLoading}
              isGitRefreshing={isGitRefreshing}
              onRefreshGit={refreshGit}
              onSelectGitFile={selectGitFile}
              onSelectGitCommit={selectGitCommit}
              onClearGitCommit={clearGitCommit}
              agentSteps={agentSteps}
              isAgentRunning={isAgentRunning}
              onOpenFile={handleOpenFileByPath}
              isMaximized={isBottomMaximized}
              onToggleMaximize={() => setIsBottomMaximized(!isBottomMaximized)}
              isCollapsed={isBottomCollapsed}
              onToggleCollapse={() => setIsBottomCollapsed(!isBottomCollapsed)}
            />
          </div>
        </div>

        {/* Split Resizer: Code Editor <-> AI Chat */}
        <div
          onMouseDown={() => {
            isDraggingChat.current = true;
            document.body.style.cursor = 'col-resize';
          }}
          className="w-1 hover:w-1.5 bg-transparent hover:bg-sky-500/50 cursor-col-resize z-20 transition-all select-none"
        />

        {/* Right Column: AI Chat */}
        <div
          style={{ width: `${chatWidth}px` }}
          className="h-full border-l border-harness-border flex flex-col shrink-0 overflow-hidden"
        >
          <ChatPanel
            conversations={conversations}
            activeConversationId={activeConversationId}
            onSelectConversation={selectConversation}
            onNewTask={startNewTask}
            messages={messages}
            isGenerating={isGenerating}
            onSendMessage={sendMessage}
            onClearChat={clearChat}
            onStopGeneration={stopGeneration}
            onRegenerate={regenerateLastMessage}
            onRetry={retryMessage}
            attachments={attachments}
            onAddAttachments={addAttachments}
            onRemoveAttachment={removeAttachment}
            onOpenFile={handleOpenFileByPath}
          />
        </div>
      </div>
    </div>
  );
};
