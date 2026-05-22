// DEC-V61-202-SUB-M30-CYCLE2 · TopBar dynamic CTA pill.
//
// Mounted inside the TopBar (or as an inline component within
// StepPanelShell's header region) when ?dynamic_frame=1 is set. Pill
// color follows kind; disabled state shows tooltip with reason.
//
// Cycle 2 wires the CTA presentation; actual step-transition behavior
// (clicking "Next step" → navigate URL to ?step=N+1) is wired by the
// parent that owns search-params state.

import type { TopbarCta } from "@/types/workbench_frame";

interface DynamicTopbarCtaProps {
  cta: TopbarCta;
  onClick?: () => void;
}

const KIND_TONE: Record<
  TopbarCta["kind"],
  { enabled: string; label: string }
> = {
  next_step: {
    enabled: "border-sky-700/60 bg-sky-900/40 text-sky-200 hover:bg-sky-900/60",
    label: "下一步",
  },
  re_audit: {
    enabled:
      "border-amber-700/60 bg-amber-900/40 text-amber-200 hover:bg-amber-900/60",
    label: "复检",
  },
  submit_solve: {
    enabled:
      "border-emerald-700/60 bg-emerald-900/40 text-emerald-200 hover:bg-emerald-900/60",
    label: "提交",
  },
  step_default: {
    enabled: "border-sky-700/60 bg-sky-900/40 text-sky-200 hover:bg-sky-900/60",
    label: "下一步",
  },
};

export function DynamicTopbarCta({ cta, onClick }: DynamicTopbarCtaProps) {
  const tone = KIND_TONE[cta.kind] ?? KIND_TONE.step_default;
  const className = cta.enabled
    ? tone.enabled
    : "border-surface-700 bg-surface-900/40 text-surface-500 cursor-not-allowed";

  return (
    <button
      type="button"
      data-testid="dynamic-topbar-cta"
      data-kind={cta.kind}
      data-enabled={cta.enabled}
      disabled={!cta.enabled}
      onClick={cta.enabled ? onClick : undefined}
      title={cta.reason ?? undefined}
      aria-label={cta.label}
      aria-disabled={!cta.enabled}
      className={`rounded-sm border px-2 py-0.5 font-mono text-[11px] uppercase tracking-wider transition ${className}`}
    >
      {cta.label}
    </button>
  );
}
