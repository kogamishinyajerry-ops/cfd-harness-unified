// DEC-V61-116 · governance-aware completeness card.
//
// Mounted at the top of TaskPanel's scrollable Body. Surfaces the
// engineer's distance-to-archive view: a status pill (绿/黄/红), a
// percentage, and an expandable list of missing fields with severity
// + reason copy.
//
// Tier-A scope: read-only. The "去补全 →" deep-link buttons are
// disabled placeholders — clicking through to step+field is V61-117
// (StepTree refactor) work. Clicking the summary bar toggles the
// expanded list locally; no global state.
//
// Failure modes (degrade gracefully, never break the workbench):
//   - 404 (case_id unknown to backend): show "（完整度分析暂不可用）"
//   - network / 500: same fallback
//   - empty data (ready_for_archive=true, missing=[]): show "✓ 已达入库标准"

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { api } from "@/api/client";
import type {
  CaseCompletenessReport,
  CompletenessSeverity,
  MissingField,
} from "@/types/case_completeness";

interface CompletenessCardProps {
  caseId: string;
}

const SEVERITY_DOT: Record<CompletenessSeverity, string> = {
  critical: "bg-rose-500",
  warning: "bg-amber-400",
  info: "bg-sky-400",
};

const SEVERITY_LABEL: Record<CompletenessSeverity, string> = {
  critical: "必填",
  warning: "建议",
  info: "可选",
};

export function CompletenessCard({ caseId }: CompletenessCardProps) {
  const [expanded, setExpanded] = useState(false);
  const query = useQuery<CaseCompletenessReport>({
    queryKey: ["case-completeness", caseId],
    queryFn: () => api.getCaseCompleteness(caseId),
    enabled: Boolean(caseId),
    staleTime: 30_000,
    retry: false,
  });

  if (query.isLoading) {
    return (
      <Frame>
        <p className="text-[11px] text-surface-500">完整度分析中…</p>
      </Frame>
    );
  }

  if (query.isError || !query.data) {
    return (
      <Frame>
        <p className="text-[11px] text-surface-500">
          （完整度分析暂不可用）
        </p>
      </Frame>
    );
  }

  const r = query.data;
  const tone = pickTone(r);

  return (
    <Frame>
      {/* Summary bar — clickable header */}
      <button
        type="button"
        data-testid="completeness-summary"
        onClick={() => setExpanded((prev) => !prev)}
        className="flex w-full items-center justify-between gap-2 text-left"
        aria-expanded={expanded}
      >
        <div className="flex min-w-0 items-center gap-2">
          <span
            className={`inline-flex shrink-0 items-center gap-1 rounded-sm border px-1.5 py-0.5 text-[10px] uppercase tracking-wider ${tone.pillClass}`}
            data-testid="completeness-pill"
            data-tone={tone.tone}
          >
            <span className={`h-1.5 w-1.5 rounded-full ${tone.dotClass}`} />
            {tone.label}
          </span>
          <span className="truncate text-[12px] text-surface-200">
            {r.ready_for_archive
              ? "已达入库标准"
              : `还差 ${r.blocked_by_critical || r.missing.length} 项`}
          </span>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <span className="font-mono text-[11px] text-surface-400">
            {r.percentage.toFixed(0)}%
          </span>
          <span aria-hidden className="text-[10px] text-surface-500">
            {expanded ? "▾" : "▸"}
          </span>
        </div>
      </button>

      {/* Progress bar */}
      <div className="mt-2 h-1 w-full overflow-hidden rounded-sm bg-surface-800">
        <div
          className={`h-full transition-[width] duration-300 ${tone.barClass}`}
          style={{ width: `${Math.min(100, Math.max(0, r.percentage))}%` }}
          aria-hidden
        />
      </div>

      {/* Expanded list */}
      {expanded && (
        <div className="mt-3 space-y-2" data-testid="completeness-expanded">
          {r.missing.length === 0 ? (
            <p className="text-[11px] text-surface-500">
              ✓ 当前阶段没有未完成项。
            </p>
          ) : (
            <ul className="space-y-1.5">
              {r.missing.map((m, i) => (
                <MissingRow key={`${m.field_path}:${i}`} m={m} />
              ))}
            </ul>
          )}
          {r.notes.length > 0 && (
            <ul className="border-t border-surface-800 pt-2 space-y-1">
              {r.notes.map((n, i) => (
                <li key={i} className="text-[10px] leading-snug text-surface-500">
                  · {n}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </Frame>
  );
}

function Frame({ children }: { children: React.ReactNode }) {
  // Pinned card at the top of TaskPanel body. border-b separates from
  // the step's own body content that scrolls below.
  return (
    <section
      data-testid="completeness-card"
      className="border-b border-surface-800 bg-surface-950/30 px-3 py-2.5"
    >
      {children}
    </section>
  );
}

function MissingRow({ m }: { m: MissingField }) {
  return (
    <li className="flex items-start gap-2 text-[11px]">
      <span
        className={`mt-1 inline-block h-1.5 w-1.5 shrink-0 rounded-full ${SEVERITY_DOT[m.severity]}`}
        title={SEVERITY_LABEL[m.severity]}
        aria-label={SEVERITY_LABEL[m.severity]}
      />
      <div className="min-w-0 flex-1">
        <code className="block font-mono text-[10px] text-surface-300">
          {m.field_path}
        </code>
        <p className="mt-0.5 leading-snug text-surface-500">{m.why}</p>
      </div>
      {/* Tier-A: disabled placeholder. V61-117 will wire click-through
          to step+field highlight. */}
      <button
        type="button"
        disabled
        title="点击跳转待 V61-117 (StepTree 子节点) 上线后启用"
        className="shrink-0 cursor-not-allowed rounded-sm border border-surface-800 bg-surface-900/40 px-1.5 py-0.5 text-[10px] text-surface-600"
      >
        去补全 →
      </button>
    </li>
  );
}

interface Tone {
  tone: "ready" | "warning" | "blocked";
  label: string;
  pillClass: string;
  dotClass: string;
  barClass: string;
}

function pickTone(r: CaseCompletenessReport): Tone {
  if (r.blocked_by_critical > 0) {
    return {
      tone: "blocked",
      label: "需修复",
      pillClass: "border-rose-600/40 bg-rose-600/10 text-rose-300",
      dotClass: "bg-rose-500",
      barClass: "bg-rose-500/70",
    };
  }
  if (r.missing.length > 0 || !r.ready_for_archive) {
    return {
      tone: "warning",
      label: "可改进",
      pillClass: "border-amber-500/40 bg-amber-500/10 text-amber-200",
      dotClass: "bg-amber-400",
      barClass: "bg-amber-400/70",
    };
  }
  return {
    tone: "ready",
    label: "可入库",
    pillClass: "border-emerald-500/40 bg-emerald-500/10 text-emerald-200",
    dotClass: "bg-emerald-400",
    barClass: "bg-emerald-400/70",
  };
}
