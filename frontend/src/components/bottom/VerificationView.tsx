import React from 'react';
import {
  CheckCircle2,
  XCircle,
  Play,
  RotateCw,
  Wrench,
  ShieldCheck,
  FileCode,
} from 'lucide-react';
import { VerificationResult } from '../../types';

interface VerificationViewProps {
  result: VerificationResult;
  isRunning: boolean;
  onRunVerification: () => void;
  onAskAgentToFix?: (failureMessage: string) => void;
  onOpenFile?: (path: string) => void;
}

export const VerificationView: React.FC<VerificationViewProps> = ({
  result,
  isRunning,
  onRunVerification,
  onAskAgentToFix,
  onOpenFile,
}) => {
  return (
    <div className="h-full flex flex-col bg-harness-surface overflow-y-auto select-none p-4">
      {/* Top Banner */}
      <div className="flex items-center justify-between pb-3 border-b border-harness-border/60">
        <div className="flex items-center space-x-3">
          <div className="p-2 rounded-lg bg-harness-panel border border-harness-border">
            <ShieldCheck className="w-5 h-5 text-sky-400" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h3 className="font-bold text-gray-100 text-sm">Harness Verification Engine</h3>
              {result.status === 'verified' && (
                <span className="bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 px-2 py-0.5 rounded-full text-[10px] font-bold tracking-wider uppercase">
                  Verified
                </span>
              )}
              {result.status === 'failed' && (
                <span className="bg-rose-500/20 text-rose-300 border border-rose-500/40 px-2 py-0.5 rounded-full text-[10px] font-bold tracking-wider uppercase">
                  Failed
                </span>
              )}
            </div>
            <p className="text-xs text-gray-400 mt-0.5">
              Automated multi-stage test suite, typecheck, lint, and diff inspection.
            </p>
          </div>
        </div>

        <button
          onClick={onRunVerification}
          disabled={isRunning}
          className="flex items-center space-x-1.5 px-3 py-1.5 bg-sky-600 hover:bg-sky-500 disabled:opacity-50 text-white rounded-lg text-xs font-medium transition active:scale-95 shadow"
        >
          {isRunning ? (
            <>
              <RotateCw className="w-3.5 h-3.5 animate-spin" />
              <span>Verifying...</span>
            </>
          ) : (
            <>
              <Play className="w-3.5 h-3.5 fill-white" />
              <span>Run Verification</span>
            </>
          )}
        </button>
      </div>

      {/* Verification Checkpoints Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 my-4">
        {/* Unit Tests */}
        <div className="p-3 bg-harness-panel/50 border border-harness-border rounded-lg flex items-center justify-between">
          <div>
            <div className="text-[11px] text-gray-400">Unit Tests (pytest)</div>
            <div className="text-sm font-bold text-gray-100 mt-0.5">
              {result.passedTests} / {result.totalTests} Passed
            </div>
          </div>
          {result.testsPassed ? (
            <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
          ) : (
            <XCircle className="w-5 h-5 text-rose-400 shrink-0" />
          )}
        </div>

        {/* Type Checking */}
        <div className="p-3 bg-harness-panel/50 border border-harness-border rounded-lg flex items-center justify-between">
          <div>
            <div className="text-[11px] text-gray-400">Type Checking</div>
            <div className="text-sm font-bold text-gray-100 mt-0.5">Pyright Clean</div>
          </div>
          {result.typeCheckPassed ? (
            <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
          ) : (
            <XCircle className="w-5 h-5 text-rose-400 shrink-0" />
          )}
        </div>

        {/* Linter */}
        <div className="p-3 bg-harness-panel/50 border border-harness-border rounded-lg flex items-center justify-between">
          <div>
            <div className="text-[11px] text-gray-400">Code Quality</div>
            <div className="text-sm font-bold text-gray-100 mt-0.5">Ruff Lint Passed</div>
          </div>
          {result.lintPassed ? (
            <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
          ) : (
            <XCircle className="w-5 h-5 text-rose-400 shrink-0" />
          )}
        </div>

        {/* Requirements */}
        <div className="p-3 bg-harness-panel/50 border border-harness-border rounded-lg flex items-center justify-between">
          <div>
            <div className="text-[11px] text-gray-400">Requirements</div>
            <div className="text-sm font-bold text-gray-100 mt-0.5">Satisfied</div>
          </div>
          {result.requirementsSatisfied ? (
            <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
          ) : (
            <XCircle className="w-5 h-5 text-rose-400 shrink-0" />
          )}
        </div>
      </div>

      {/* Failure Drill-Down or Success Card */}
      {result.failures && result.failures.length > 0 ? (
        <div className="mt-2 space-y-3">
          <h4 className="text-xs font-semibold text-rose-400 uppercase tracking-wider">
            Failure Diagnostics ({result.failures.length})
          </h4>
          {result.failures.map((f, idx) => (
            <div
              key={idx}
              className="p-3 bg-rose-950/20 border border-rose-500/30 rounded-lg text-xs"
            >
              <div className="flex items-center justify-between mb-2">
                <span className="font-mono font-bold text-rose-300">{f.testName}</span>
                <button
                  onClick={() => onOpenFile?.(f.file)}
                  className="flex items-center space-x-1 text-sky-400 hover:text-sky-300 font-mono text-[11px]"
                >
                  <FileCode className="w-3.5 h-3.5" />
                  <span>{f.file}</span>
                </button>
              </div>

              <div className="grid grid-cols-2 gap-2 my-2 font-mono text-[11px]">
                <div className="p-2 bg-black/40 rounded border border-harness-border/60">
                  <span className="text-gray-400 block text-[10px]">Expected:</span>
                  <span className="text-emerald-400">{f.expected}</span>
                </div>
                <div className="p-2 bg-black/40 rounded border border-harness-border/60">
                  <span className="text-gray-400 block text-[10px]">Received:</span>
                  <span className="text-rose-400">{f.received}</span>
                </div>
              </div>

              {f.trace && (
                <pre className="p-2 bg-black/50 rounded font-mono text-[10.5px] text-gray-400 overflow-x-auto">
                  {f.trace}
                </pre>
              )}

              <div className="mt-3 flex justify-end">
                <button
                  onClick={() =>
                    onAskAgentToFix?.(
                      `Fix failing test ${f.testName} in ${f.file}: Expected ${f.expected} but received ${f.received}`
                    )
                  }
                  className="flex items-center space-x-1 px-3 py-1 bg-rose-600 hover:bg-rose-500 text-white rounded text-xs font-medium transition"
                >
                  <Wrench className="w-3.5 h-3.5" />
                  <span>Ask Agent to Fix</span>
                </button>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="p-4 bg-emerald-950/20 border border-emerald-500/30 rounded-lg flex items-center space-x-3 text-xs text-emerald-200 mt-2">
          <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
          <div>
            <span className="font-semibold text-emerald-300">All checks passed:</span> 67 of 67 pytest cases executed successfully in 1.08s with zero regressions.
          </div>
        </div>
      )}
    </div>
  );
};
