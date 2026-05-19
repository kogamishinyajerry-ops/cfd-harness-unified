// Top bar · 6-field information density per Blueprint v3 §4 (V67-C.1).
//
// Six fields visible at all times:
//   1. case (caseId)
//   2. OF truth (openfoam_native | mock | unknown)
//   3. TrustGate (PASS | PASS_WITH_DISCLAIMER | FAIL | PENDING)
//   4. LLM offline (boolean · V130 invariant indicator)
//   5. Audit % (number | null)
//   6. AI = advisor (constant badge · V130 statement)
//
// saveIndicator (legacy field) is preserved alongside caseId (a 7th channel
// kept for backward compat with existing callers; not counted toward
// blueprint §4's "6 fields").
//
// All new fields have sensible defaults so existing call-sites (currently
// passing only caseId / saveIndicator) keep working without changes.

import type { ReactNode } from "react";

interface TopBarProps {
  caseId: string;
  saveIndicator?: "idle" | "saving" | "saved" | "error";
  /** Backend truth source for this case · default "unknown" */
  truthSource?: "openfoam_native" | "mock" | "unknown";
  /** Current TrustGate verdict · default "PENDING" */
  trustGate?: "PASS" | "PASS_WITH_DISCLAIMER" | "FAIL" | "PENDING";
  /** V130 LLM-offline guarantee surface · default true (V130 invariant) */
  llmOffline?: boolean;
  /** Audit coverage percent 0-100 · null when not yet computed */
  auditPct?: number | null;
}

const SAVE_LABEL: Record<NonNullable<TopBarProps["saveIndicator"]>, string> = {
  idle: "ready",
  saving: "saving…",
  saved: "saved",
  error: "save failed",
};

const SAVE_TONE: Record<NonNullable<TopBarProps["saveIndicator"]>, string> = {
  idle: "text-surface-500",
  saving: "text-emerald-300",
  saved: "text-emerald-400",
  error: "text-rose-300",
};

const TRUTH_LABEL: Record<NonNullable<TopBarProps["truthSource"]>, string> = {
  openfoam_native: "OF native",
  mock: "mock",
  unknown: "OF —",
};

const TRUTH_TONE: Record<NonNullable<TopBarProps["truthSource"]>, string> = {
  openfoam_native: "text-emerald-400 border-emerald-700/60",
  mock: "text-amber-300 border-amber-700/60",
  unknown: "text-surface-500 border-surface-700",
};

const TRUST_LABEL: Record<NonNullable<TopBarProps["trustGate"]>, string> = {
  PASS: "Trust: PASS",
  PASS_WITH_DISCLAIMER: "Trust: PASS*",
  FAIL: "Trust: FAIL",
  PENDING: "Trust: —",
};

const TRUST_TONE: Record<NonNullable<TopBarProps["trustGate"]>, string> = {
  PASS: "text-emerald-400 border-emerald-700/60",
  PASS_WITH_DISCLAIMER: "text-amber-300 border-amber-700/60",
  FAIL: "text-rose-300 border-rose-700/60",
  PENDING: "text-surface-500 border-surface-700",
};

function Chip({
  testId,
  className,
  children,
  dataState,
}: {
  testId: string;
  className: string;
  children: ReactNode;
  dataState?: string;
}) {
  return (
    <span
      data-testid={testId}
      data-state={dataState}
      className={`inline-flex items-center rounded border px-1.5 py-0.5 text-[10px] font-mono uppercase tracking-wider ${className}`}
    >
      {children}
    </span>
  );
}

export function TopBar({
  caseId,
  saveIndicator = "idle",
  truthSource = "unknown",
  trustGate = "PENDING",
  llmOffline = true,
  auditPct = null,
}: TopBarProps) {
  const auditLabel =
    auditPct === null || auditPct === undefined
      ? "Audit —"
      : `Audit ${Math.round(auditPct)}%`;
  const auditTone =
    auditPct === null || auditPct === undefined
      ? "text-surface-500 border-surface-700"
      : auditPct >= 80
        ? "text-emerald-400 border-emerald-700/60"
        : auditPct >= 50
          ? "text-amber-300 border-amber-700/60"
          : "text-rose-300 border-rose-700/60";

  return (
    <header
      data-testid="top-bar"
      className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1.5 border-b border-surface-800 bg-surface-950/80 px-3 py-2"
    >
      <div className="flex items-baseline gap-2">
        <span className="text-[10px] font-mono uppercase tracking-wider text-surface-500">
          Workbench
        </span>
        <h1
          className="font-mono text-sm text-surface-100"
          data-testid="top-bar-case-id"
        >
          {caseId}
        </h1>
        <span
          data-testid="save-indicator"
          data-state={saveIndicator}
          className={`text-[11px] ${SAVE_TONE[saveIndicator]}`}
        >
          {SAVE_LABEL[saveIndicator]}
        </span>
      </div>

      <div className="flex flex-wrap items-center gap-1.5">
        <Chip
          testId="top-bar-truth-source"
          dataState={truthSource}
          className={TRUTH_TONE[truthSource]}
        >
          {TRUTH_LABEL[truthSource]}
        </Chip>
        <Chip
          testId="top-bar-trust-gate"
          dataState={trustGate}
          className={TRUST_TONE[trustGate]}
        >
          {TRUST_LABEL[trustGate]}
        </Chip>
        <Chip
          testId="top-bar-llm-offline"
          dataState={llmOffline ? "offline_ok" : "online"}
          className={
            llmOffline
              ? "text-emerald-400 border-emerald-700/60"
              : "text-amber-300 border-amber-700/60"
          }
        >
          {llmOffline ? "LLM offline ✓" : "LLM online"}
        </Chip>
        <Chip
          testId="top-bar-audit-pct"
          dataState={auditPct === null ? "pending" : "computed"}
          className={auditTone}
        >
          {auditLabel}
        </Chip>
        <Chip
          testId="top-bar-ai-advisor"
          dataState="advisor"
          className="text-sky-300 border-sky-700/60"
        >
          AI = advisor
        </Chip>
      </div>
    </header>
  );
}
