import React from 'react';
import {
  CheckCircle2,
  Clock,
  AlertTriangle,
  RotateCw,
  GitBranch,
  Search,
  Code2,
  ShieldCheck,
  Cpu,
} from 'lucide-react';
import { AgentStep } from '../../types';

interface AgentActivityViewProps {
  steps: AgentStep[];
  isRunning: boolean;
}

export const AgentActivityView: React.FC<AgentActivityViewProps> = ({
  steps,
  isRunning,
}) => {
  const getStepIcon = (status: AgentStep['status']) => {
    switch (status) {
      case 'completed':
        return <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />;
      case 'in_progress':
        return <RotateCw className="w-4 h-4 text-sky-400 animate-spin shrink-0" />;
      case 'recovering':
        return <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />;
      case 'failed':
        return <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />;
      default:
        return <div className="w-3.5 h-3.5 rounded-full border border-gray-600 shrink-0" />;
    }
  };

  return (
    <div className="h-full flex flex-col bg-harness-surface overflow-y-auto select-none p-4">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-harness-border/60">
        <div className="flex items-center space-x-2.5">
          <div className="p-1.5 rounded-md bg-sky-500/10 border border-sky-500/30">
            <Cpu className="w-4 h-4 text-sky-400" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h3 className="font-bold text-gray-100 text-sm">Autonomous Harness Workflow</h3>
              {isRunning && (
                <span className="flex items-center space-x-1 bg-sky-500/20 text-sky-300 border border-sky-500/40 px-2 py-0.5 rounded-full text-[10px] font-bold animate-pulse">
                  <span>Executing Autonomous Cycle</span>
                </span>
              )}
            </div>
            <p className="text-xs text-gray-400 mt-0.5">
              Multi-agent state transitions: Planner → Research → Coder → Verification → Recovery.
            </p>
          </div>
        </div>
      </div>

      {/* Steps Timeline */}
      <div className="py-4 space-y-4 max-w-3xl">
        {steps.map((step, idx) => {
          const isLast = idx === steps.length - 1;
          return (
            <div key={step.id} className="flex items-start space-x-3 relative">
              {/* Vertical connector line */}
              {!isLast && (
                <div
                  className={`absolute left-[7px] top-[22px] w-[2px] h-[calc(100%+8px)] ${
                    step.status === 'completed'
                      ? 'bg-emerald-500/30'
                      : 'bg-harness-border/60'
                  }`}
                />
              )}

              {/* Status Icon */}
              <div className="z-10 bg-harness-surface pt-0.5">
                {getStepIcon(step.status)}
              </div>

              {/* Step Content */}
              <div className="flex-1 pb-1">
                <div className="flex items-center space-x-2">
                  <span
                    className={`font-semibold text-xs ${
                      step.status === 'completed'
                        ? 'text-gray-100'
                        : step.status === 'in_progress'
                        ? 'text-sky-300 font-bold'
                        : 'text-gray-400'
                    }`}
                  >
                    {step.title}
                  </span>
                  {step.status === 'in_progress' && (
                    <span className="text-[10px] text-sky-400 font-mono animate-pulse">
                      ● active
                    </span>
                  )}
                </div>

                {step.details && (
                  <p className="text-xs text-gray-400 mt-1 leading-relaxed">
                    {step.details}
                  </p>
                )}

                {/* Sub-steps pills */}
                {step.subSteps && step.subSteps.length > 0 && (
                  <div className="flex flex-wrap gap-1.5 mt-2">
                    {step.subSteps.map((sub, sIdx) => (
                      <span
                        key={sIdx}
                        className="text-[10.5px] px-2 py-0.5 bg-harness-panel border border-harness-border/60 text-gray-300 rounded font-mono"
                      >
                        ✓ {sub}
                      </span>
                    ))}
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
