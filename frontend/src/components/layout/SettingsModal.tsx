import React, { useState } from 'react';
import { X, Sliders, Shield, Cpu, Key, Database } from 'lucide-react';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const SettingsModal: React.FC<SettingsModalProps> = ({ isOpen, onClose }) => {
  const [model, setModel] = useState('gemini-2.5-pro');
  const [apiUrl, setApiUrl] = useState('http://127.0.0.1:8000/api/v1');
  const [enforceSandbox, setEnforceSandbox] = useState(true);
  const [maxSteps, setMaxSteps] = useState(15);
  const [activeTab, setActiveTab] = useState<'general' | 'models' | 'sandbox' | 'observability'>('general');

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-xs select-none">
      <div className="w-[540px] max-w-full bg-harness-surface border border-harness-border rounded-xl shadow-2xl overflow-hidden flex flex-col animate-in fade-in zoom-in-95 duration-150">
        {/* Header */}
        <div className="h-12 px-5 border-b border-harness-border flex items-center justify-between bg-harness-panel/50">
          <div className="flex items-center space-x-2">
            <Sliders className="w-4 h-4 text-sky-400" />
            <span className="font-semibold text-sm text-gray-100">Harness Settings</span>
          </div>
          <button
            onClick={onClose}
            className="p-1 text-gray-400 hover:text-white rounded hover:bg-harness-border/50 transition"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Tab switcher */}
        <div className="flex border-b border-harness-border text-xs px-5 bg-harness-bg/50">
          <button
            onClick={() => setActiveTab('general')}
            className={`py-2 px-3 border-b-2 font-medium transition ${
              activeTab === 'general'
                ? 'border-sky-400 text-sky-300'
                : 'border-transparent text-gray-400 hover:text-gray-200'
            }`}
          >
            General & API
          </button>
          <button
            onClick={() => setActiveTab('models')}
            className={`py-2 px-3 border-b-2 font-medium transition ${
              activeTab === 'models'
                ? 'border-sky-400 text-sky-300'
                : 'border-transparent text-gray-400 hover:text-gray-200'
            }`}
          >
            Model Gateway
          </button>
          <button
            onClick={() => setActiveTab('sandbox')}
            className={`py-2 px-3 border-b-2 font-medium transition ${
              activeTab === 'sandbox'
                ? 'border-sky-400 text-sky-300'
                : 'border-transparent text-gray-400 hover:text-gray-200'
            }`}
          >
            Security & Sandbox
          </button>
        </div>

        {/* Body content */}
        <div className="p-5 space-y-4 text-xs">
          {activeTab === 'general' && (
            <div className="space-y-4">
              <div>
                <label className="block font-medium text-gray-300 mb-1">
                  Shared Harness API Endpoint
                </label>
                <div className="relative">
                  <input
                    type="text"
                    value={apiUrl}
                    onChange={(e) => setApiUrl(e.target.value)}
                    className="w-full bg-harness-bg border border-harness-border rounded-lg px-3 py-2 text-gray-100 font-mono text-xs focus:outline-none focus:border-sky-500"
                  />
                </div>
                <p className="text-[11px] text-gray-500 mt-1">
                  Cross-platform backend consumed by React Web, macOS Swift, and Android clients.
                </p>
              </div>

              <div>
                <label className="block font-medium text-gray-300 mb-1">
                  Max Autonomous Steps per Task
                </label>
                <input
                  type="number"
                  min={1}
                  max={50}
                  value={maxSteps}
                  onChange={(e) => setMaxSteps(Number(e.target.value))}
                  className="w-24 bg-harness-bg border border-harness-border rounded-lg px-3 py-1.5 text-gray-100 text-xs focus:outline-none focus:border-sky-500"
                />
                <p className="text-[11px] text-gray-500 mt-1">
                  Orchestrator halts execution if iteration limit is reached without verification.
                </p>
              </div>
            </div>
          )}

          {activeTab === 'models' && (
            <div className="space-y-4">
              <div>
                <label className="block font-medium text-gray-300 mb-1">
                  Primary Foundation Model
                </label>
                <select
                  value={model}
                  onChange={(e) => setModel(e.target.value)}
                  className="w-full bg-harness-bg border border-harness-border rounded-lg px-3 py-2 text-gray-100 text-xs focus:outline-none focus:border-sky-500"
                >
                  <option value="gemini-2.5-pro">Google Gemini 2.5 Pro (Recommended)</option>
                  <option value="gemini-2.5-flash">Google Gemini 2.5 Flash</option>
                  <option value="claude-3-7-sonnet">Anthropic Claude 3.7 Sonnet</option>
                  <option value="gpt-4o">OpenAI GPT-4o</option>
                  <option value="local-deepseek-r1">Local Ollama / DeepSeek-R1</option>
                </select>
                <p className="text-[11px] text-gray-500 mt-1">
                  Used by Planner, Coder, and Critic agents in the central orchestrator.
                </p>
              </div>

              <div className="p-3 bg-harness-bg/60 border border-harness-border/70 rounded-lg flex items-start space-x-2.5">
                <Key className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                <div>
                  <span className="font-semibold text-gray-300">API Key Management</span>
                  <p className="text-gray-400 mt-0.5 text-[11px]">
                    API keys are securely read from backend environment (.env) and never exposed to the client.
                  </p>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'sandbox' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between p-3 bg-harness-bg rounded-lg border border-harness-border">
                <div className="flex items-start space-x-2.5">
                  <Shield className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                  <div>
                    <span className="font-semibold text-gray-200">Filesystem Sandbox</span>
                    <p className="text-gray-400 text-[11px] mt-0.5">
                      Prevents agents from traversing outside the repository root workspace.
                    </p>
                  </div>
                </div>
                <input
                  type="checkbox"
                  checked={enforceSandbox}
                  onChange={(e) => setEnforceSandbox(e.target.checked)}
                  className="rounded border-gray-600 text-sky-600 focus:ring-sky-500 h-4 w-4 bg-harness-surface"
                />
              </div>

              <div className="p-3 bg-harness-bg/60 border border-harness-border/70 rounded-lg flex items-start space-x-2.5">
                <Database className="w-4 h-4 text-sky-400 shrink-0 mt-0.5" />
                <div>
                  <span className="font-semibold text-gray-300">Tool Protection</span>
                  <p className="text-gray-400 mt-0.5 text-[11px]">
                    Shell tool disallows non-whitelisted interactive commands and destructive deletion without confirmation.
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="h-12 px-5 border-t border-harness-border bg-harness-panel/40 flex items-center justify-end space-x-2">
          <button
            onClick={onClose}
            className="px-3 py-1.5 rounded-lg border border-harness-border hover:bg-harness-border/40 text-gray-300 text-xs font-medium transition"
          >
            Cancel
          </button>
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-lg bg-sky-600 hover:bg-sky-500 text-white text-xs font-medium transition shadow"
          >
            Save Settings
          </button>
        </div>
      </div>
    </div>
  );
};
