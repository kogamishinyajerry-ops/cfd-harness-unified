// Shared [AI 处理] / [上一步] / [下一步] button row consumed by the
// TaskPanel for every step. Per Addendum 3 §3.b the [下一步] button
// NEVER auto-fires on AI 处理 success — engineer always advances
// manually.

import type { StepNavigationContract } from "./types";

interface StepNavigationProps extends StepNavigationContract {
  /** Tooltip when [AI 处理] is disabled because the step's wireup is
   *  deferred to a later milestone. */
  aiActionDeferredTooltip?: string;
}

const BTN_BASE =
  "rounded-sm border px-3 py-1 text-[11px] font-mono uppercase tracking-wider transition disabled:cursor-not-allowed disabled:opacity-50";

const BTN_NEUTRAL =
  "border-surface-700 bg-surface-900/40 text-surface-200 hover:bg-surface-800";

const BTN_PRIMARY =
  "border-emerald-500/40 bg-emerald-500/10 text-emerald-200 hover:bg-emerald-500/20";

export function StepNavigation({
  onAiProcess,
  onPrevious,
  onNext,
  canAdvance,
  canRetreat,
  aiInFlight,
  aiErrorMessage,
  aiActionDeferredTooltip,
}: StepNavigationProps) {
  const aiDisabled = onAiProcess === null || aiInFlight;
  const aiTitle =
    onAiProcess === null
      ? aiActionDeferredTooltip ?? "AI 处理 wires up in a later milestone"
      : aiInFlight
      ? "AI 处理 in progress…"
      : undefined;

  return (
    <div
      data-testid="step-navigation"
      className="flex flex-col gap-2 border-t border-surface-800 px-3 py-2"
    >
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          data-testid="ai-process-button"
          disabled={aiDisabled}
          title={aiTitle}
          onClick={() => {
            if (!aiDisabled && onAiProcess) {
              void onAiProcess();
            }
          }}
          className={`${BTN_BASE} ${BTN_PRIMARY}`}
        >
          {aiInFlight ? "AI 处理…" : "AI 处理"}
        </button>
        <button
          type="button"
          data-testid="previous-button"
          disabled={!canRetreat || aiInFlight}
          onClick={onPrevious}
          className={`${BTN_BASE} ${BTN_NEUTRAL}`}
        >
          ← 上一步
        </button>
        <button
          type="button"
          data-testid="next-button"
          disabled={!canAdvance || aiInFlight}
          onClick={onNext}
          className={`${BTN_BASE} ${BTN_NEUTRAL}`}
        >
          下一步 →
        </button>
      </div>
      {aiErrorMessage && (
        <p
          data-testid="ai-error"
          className="rounded-sm border border-rose-500/40 bg-rose-500/10 px-2 py-1 text-[11px] text-rose-200"
        >
          AI 处理 error: {aiErrorMessage}
        </p>
      )}
    </div>
  );
}
