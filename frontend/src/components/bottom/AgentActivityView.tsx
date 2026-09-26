import React from 'react';
import {
  Check,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  RotateCw,
  Cpu,
  ArrowRight,
  Circle,
  Play,
  RotateCcw,
  FileCode,
  Layers,
  Activity,
  Radio,
} from 'lucide-react';
import { AgentStep, AgentStatus } from '../../types/agentContract';
import { useAgentWorkflow } from '../../hooks/useAgentWorkflow';

interface AgentActivityViewProps {
  onOpenFile?: (path: string) => void;
}

export const AgentActivityView: React.FC<AgentActivityViewProps> = ({ onOpenFile }) => {
  const {
    task,
    steps,
    status,
    isRunning,
    recoveryAttempt,
    maxRecoveryAttempts,
    startScenario,
    resetWorkflow,
    transportType,
    setTransportType,
  } = useAgentWorkflow();

  const renderStatusSymbol = (step: AgentStep) => {
    // Failure handling
    if (step.status === 'failed' || step.title.toLowerCase().includes('fail')) {
      return (
        <div className="w-5 h-5 rounded-full bg-rose-500/20 border border-rose-500/40 flex items-center justify-center text-rose-400 shrink-0 font-bold text-xs shadow-sm shadow-rose-950/50">
          ✗
        </div>
      );
    }

    // Recovery loop steps (Failure analysis, Recovery attempt 1/3, Correction, Testing again)
    if (
      step.status === 'recovering' ||
      step.title.toLowerCase().includes('recovery') ||
      step.title.toLowerCase().includes('analysis') ||
      step.title.toLowerCase().includes('correction') ||
      step.title.toLowerCase().includes('testing again')
    ) {
      return (
        <div className="w-5 h-5 rounded-full bg-amber-500/20 border border-amber-500/50 flex items-center justify-center text-amber-300 shrink-0 font-bold text-xs shadow-sm shadow-amber-950/50">
          →
        </div>
      );
    }

    // Completed
    if (step.status === 'completed') {
      return (
        <div className="w-5 h-5 rounded-full bg-emerald-500/20 border border-emerald-500/40 flex items-center justify-center text-emerald-400 shrink-0 font-bold text-xs shadow-sm shadow-emerald-950/50">
          ✓
        </div>
      );
    }

    // In Progress
    if (step.status === 'in_progress') {
      return (
        <div className="w-5 h-5 rounded-full bg-sky-500/30 border border-sky-400 flex items-center justify-center text-sky-300 shrink-0 font-bold text-xs animate-pulse shadow-sm shadow-sky-950/50">
          ●
        </div>
      );
    }

    // Pending / Unstarted
    return (
      <div className="w-5 h-5 rounded-full bg-harness-panel/40 border border-gray-600 flex items-center justify-center text-gray-500 shrink-0 font-mono text-[10px]">
        ○
      </div>
    );
  };

  const getStatusBadge = (agentStatus: AgentStatus) => {
    switch (agentStatus) {
      case 'completed':
        return (
          <span className="px-2.5 py-1 text-xs font-semibold rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 flex items-center space-x-1.5">
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>✓ Completed</span>
          </span>
        );
      case 'failed':
        return (
          <span className="px-2.5 py-1 text-xs font-semibold rounded-full bg-rose-500/20 text-rose-300 border border-rose-500/30 flex items-center space-x-1.5 animate-pulse">
            <XCircle className="w-3.5 h-3.5" />
            <span>✗ Tests Failed</span>
          </span>
        );
      case 'recovering':
      case 'failure_analysis':
        return (
          <span className="px-2.5 py-1 text-xs font-semibold rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/30 flex items-center space-x-1.5 animate-pulse">
            <AlertTriangle className="w-3.5 h-3.5" />
            <span>→ Recovery Attempt {recoveryAttempt || 1}/{maxRecoveryAttempts}</span>
          </span>
        );
      default:
        return (
          <span className="px-2.5 py-1 text-xs font-semibold rounded-full bg-sky-500/20 text-sky-300 border border-sky-500/30 flex items-center space-x-1.5">
            <RotateCw className="w-3.5 h-3.5 animate-spin" />
            <span className="uppercase">● {agentStatus.replace('_', ' ')}</span>
          </span>
        );
    }
  };

  return (
    <div className="h-full flex flex-col bg-harness-surface overflow-hidden select-text">
      {/* Top Header & Simulation Controls */}
      <div className="p-3 bg-harness-surface/90 border-b border-harness-border/70 flex flex-wrap items-center justify-between gap-3 select-none">
        <div className="flex items-center space-x-3">
          <div className="p-1.5 rounded-md bg-sky-500/10 border border-sky-500/30">
            <Cpu className="w-4 h-4 text-sky-400" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h3 className="font-bold text-gray-100 text-xs tracking-wide">
                AUTONOMOUS HARNESS TELEMETRY
              </h3>
              {getStatusBadge(status)}
            </div>
            <p className="text-[11px] text-gray-400 mt-0.5 truncate max-w-lg">
              {task?.title || 'Active multi-agent reasoning and execution cycle'}
            </p>
          </div>
        </div>

        {/* Demo Action Buttons & Transport Selector */}
        <div className="flex items-center space-x-2">
          {/* Transport Indicator */}
          <div className="flex items-center space-x-1 px-2 py-1 rounded bg-harness-bg border border-harness-border/60 text-[10px] text-gray-400">
            <Radio className="w-3 h-3 text-emerald-400 animate-pulse" />
            <span>Stream:</span>
            <span className="text-gray-200 font-mono uppercase font-semibold">
              {transportType}
            </span>
          </div>

          {/* Scenario Trigger: Standard */}
          <button
            onClick={() => startScenario('happy')}
            disabled={isRunning}
            className={`flex items-center space-x-1.5 px-2.5 py-1.5 rounded bg-sky-600/30 hover:bg-sky-600/50 text-sky-200 border border-sky-500/40 text-xs font-medium transition ${
              isRunning ? 'opacity-50 cursor-not-allowed' : ''
            }`}
            title="Demonstrate the standard 8-phase execution workflow"
          >
            <Play className="w-3 h-3 text-sky-300" />
            <span>Standard Workflow</span>
          </button>

          {/* Scenario Trigger: Failure & Recovery Loop */}
          <button
            onClick={() => startScenario('recovery')}
            disabled={isRunning}
            className={`flex items-center space-x-1.5 px-2.5 py-1.5 rounded bg-amber-600/30 hover:bg-amber-600/50 text-amber-200 border border-amber-500/40 text-xs font-medium transition ${
              isRunning ? 'opacity-50 cursor-not-allowed' : ''
            }`}
            title="Demonstrate test failure detection, root cause analysis, and autonomous recovery attempt 1/3"
          >
            <AlertTriangle className="w-3 h-3 text-amber-300" />
            <span>Failure & Recovery (1/3)</span>
          </button>

          {/* Reset button */}
          <button
            onClick={resetWorkflow}
            className="p-1.5 rounded bg-harness-panel hover:bg-harness-border text-gray-400 hover:text-white border border-harness-border/60 transition"
            title="Reset Workflow State"
          >
            <RotateCcw className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Main Timeline View */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {steps.map((step, idx) => {
          const isLast = idx === steps.length - 1;
          const isFailed = step.status === 'failed' || step.title.toLowerCase().includes('fail');
          const isRecovery =
            step.status === 'recovering' ||
            step.title.toLowerCase().includes('recovery') ||
            step.title.toLowerCase().includes('analysis') ||
            step.title.toLowerCase().includes('correction') ||
            step.title.toLowerCase().includes('testing again');

          let borderColor = 'border-harness-border/50';
          let bgColor = 'bg-harness-panel/40';

          if (isFailed) {
            borderColor = 'border-rose-500/40';
            bgColor = 'bg-rose-950/20';
          } else if (isRecovery) {
            borderColor = 'border-amber-500/40';
            bgColor = 'bg-amber-950/20';
          } else if (step.status === 'in_progress') {
            borderColor = 'border-sky-500/50';
            bgColor = 'bg-sky-950/20';
          } else if (step.status === 'completed') {
            borderColor = 'border-emerald-500/30';
            bgColor = 'bg-harness-panel/30';
          }

          return (
            <div key={step.id} className="flex items-start space-x-3 relative">
              {/* Connector line */}
              {!isLast && (
                <div
                  className={`absolute left-[9px] top-[24px] w-[2px] h-[calc(100%+12px)] ${
                    step.status === 'completed'
                      ? 'bg-emerald-500/30'
                      : isFailed
                      ? 'bg-rose-500/30'
                      : isRecovery
                      ? 'bg-amber-500/30'
                      : 'bg-harness-border/60'
                  }`}
                />
              )}

              {/* Status Symbol: ✓ / ● / ○ / ✗ / → */}
              <div className="z-10 bg-harness-surface pt-1">{renderStatusSymbol(step)}</div>

              {/* Step Card */}
              <div className={`flex-1 p-3 rounded-lg border ${borderColor} ${bgColor} transition`}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <span
                      className={`text-xs font-bold tracking-wide ${
                        isFailed
                          ? 'text-rose-300'
                          : isRecovery
                          ? 'text-amber-300'
                          : step.status === 'completed'
                          ? 'text-gray-100'
                          : step.status === 'in_progress'
                          ? 'text-sky-300'
                          : 'text-gray-400'
                      }`}
                    >
                      {step.title}
                    </span>

                    {step.agentName && (
                      <span className="px-2 py-0.5 text-[9.5px] font-mono rounded bg-harness-bg/80 border border-harness-border/60 text-gray-300">
                        {step.agentName}
                      </span>
                    )}

                    {step.status === 'in_progress' && (
                      <span className="text-[10px] text-sky-400 font-mono animate-pulse">
                        ● running
                      </span>
                    )}
                  </div>

                  {step.durationSeconds !== undefined && (
                    <span className="text-[10px] font-mono text-gray-400">
                      {step.durationSeconds.toFixed(1)}s
                    </span>
                  )}
                </div>

                {/* Details narrative */}
                {step.details && (
                  <p className="text-xs text-gray-300 mt-1.5 leading-relaxed font-sans">
                    {step.details}
                  </p>
                )}

                {/* Failure Error Callout */}
                {step.error && (
                  <div className="mt-2.5 p-2.5 rounded bg-rose-950/40 border border-rose-500/40 text-rose-300 font-mono text-xs">
                    <div className="flex items-center space-x-1.5 font-bold mb-1">
                      <XCircle className="w-3.5 h-3.5 text-rose-400 shrink-0" />
                      <span>Test Suite Assertion Failure</span>
                    </div>
                    <pre className="text-[11px] whitespace-pre-wrap text-rose-200">
                      {step.error}
                    </pre>
                  </div>
                )}

                {/* Sub-steps / checklist */}
                {step.subSteps && step.subSteps.length > 0 && (
                  <div className="flex flex-wrap gap-1.5 mt-2.5">
                    {step.subSteps.map((sub, sIdx) => (
                      <span
                        key={sIdx}
                        className="text-[10.5px] px-2 py-0.5 bg-harness-bg/60 border border-harness-border/50 text-gray-300 rounded font-mono flex items-center space-x-1"
                      >
                        <Check className="w-2.5 h-2.5 text-emerald-400" />
                        <span>{sub}</span>
                      </span>
                    ))}
                  </div>
                )}

                {/* Relevant Files found (clickable to open in Monaco editor) */}
                {step.relevantFiles && step.relevantFiles.length > 0 && (
                  <div className="mt-2.5 flex items-center space-x-1.5 text-xs text-gray-400">
                    <span className="text-[10px] uppercase font-bold text-gray-400">
                      Target files:
                    </span>
                    <div className="flex flex-wrap gap-1.5">
                      {step.relevantFiles.map((file, fIdx) => (
                        <button
                          key={fIdx}
                          onClick={() => onOpenFile?.(file)}
                          className="flex items-center space-x-1 px-2 py-0.5 text-[10.5px] font-mono rounded bg-sky-500/10 hover:bg-sky-500/20 text-sky-300 border border-sky-500/30 transition"
                        >
                          <FileCode className="w-3 h-3 text-sky-400" />
                          <span>{file}</span>
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
