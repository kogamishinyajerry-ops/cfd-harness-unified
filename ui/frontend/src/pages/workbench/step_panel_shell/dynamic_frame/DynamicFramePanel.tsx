// DEC-V61-202-SUB-M30-CYCLE1 · rail.primary slot renderer.
//
// Mounted ABOVE existing TaskPanel content (additive layer per user
// 2026-05-22 Q1=B). Renders the frame.rail_primary card with severity-
// driven tone, deep-link to the targeted manifest field, and a
// debuggable provenance disclosure for "why is this showing?"
//
// Failure modes (degrade gracefully):
//   - query loading → minimal skeleton
//   - query error → silent (the static step body still renders below)
//   - feature flag off (?dynamic_frame=1 not set) → not rendered

import { useState } from "react";

import type { RailPrimary } from "@/types/workbench_frame";

interface DynamicFramePanelProps {
  rail: RailPrimary;
}

const KIND_TONE: Record<
  RailPrimary["kind"],
  { pill: string; dot: string; label: string }
> = {
  problem_fix: {
    pill: "bg-rose-900/40 border-rose-700/60 text-rose-200",
    dot: "bg-rose-400",
    label: "需修复",
  },
  info_gap: {
    pill: "bg-amber-900/40 border-amber-700/60 text-amber-200",
    dot: "bg-amber-400",
    label: "待补充",
  },
  step_default: {
    pill: "bg-emerald-900/40 border-emerald-700/60 text-emerald-200",
    dot: "bg-emerald-400",
    label: "就绪",
  },
};

export function DynamicFramePanel({ rail }: DynamicFramePanelProps) {
  const [showProvenance, setShowProvenance] = useState(false);
  const tone = KIND_TONE[rail.kind] ?? KIND_TONE.step_default;

  return (
    <section
      data-testid="dynamic-frame-panel"
      data-kind={rail.kind}
      className="mx-3 mt-3 rounded-md border border-surface-700 bg-surface-900/80 p-3"
    >
      <header className="flex items-center justify-between gap-2">
        <span
          className={`inline-flex items-center gap-1 rounded-sm border px-1.5 py-0.5 text-[10px] uppercase tracking-wider ${tone.pill}`}
        >
          <span className={`h-1.5 w-1.5 rounded-full ${tone.dot}`} />
          {tone.label}
        </span>
        {rail.field_path && (
          <code className="truncate font-mono text-[10px] text-surface-500">
            {rail.field_path}
          </code>
        )}
      </header>

      <h3 className="mt-2 text-[13px] font-medium text-surface-100">
        {rail.title}
      </h3>

      {rail.body_text && (
        <p className="mt-1 text-[12px] leading-snug text-surface-300">
          {rail.body_text}
        </p>
      )}

      {rail.cta_label && (
        <button
          type="button"
          data-testid="dynamic-frame-cta"
          className="mt-3 rounded-sm border border-sky-700/60 bg-sky-900/40 px-2 py-1 text-[11px] text-sky-200 hover:bg-sky-900/60"
        >
          {rail.cta_label}
        </button>
      )}

      {/* Provenance disclosure — dev-mode style; collapsed by default */}
      <button
        type="button"
        onClick={() => setShowProvenance((v) => !v)}
        className="mt-2 text-[10px] text-surface-500 hover:text-surface-300"
        aria-expanded={showProvenance}
      >
        {showProvenance ? "▾ 为什么显示这个" : "▸ 为什么显示这个"}
      </button>
      {showProvenance && (
        <ul className="mt-1 list-disc pl-4 text-[10px] text-surface-500">
          {rail.provenance.map((p, i) => (
            <li key={i} className="font-mono">
              {p}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
