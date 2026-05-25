// DEC-V61-202-SUB-M30-CYCLE2 · TopBar dynamic CTA pill.
//
// Mounted inside the TopBar (or as an inline component within
// StepPanelShell's header region) when ?dynamic_frame=1 is set. Pill
// color follows kind; disabled state shows tooltip with reason.
//
// Cycle 2 wires the CTA presentation; actual step-transition behavior
// (clicking "Next step" → navigate URL to ?step=N+1) is wired by the
// parent that owns search-params state.
//
// DEC-V61-202-SUB-M32-CYCLE2: when the CTA is disabled, the visual
// cue picks up the rail's severity so engineers can tell why they're
// blocked at a glance: rose-grey (critical / must-fix), amber-grey
// (missing field), sky-grey (advisory / optional). Without this,
// disabled CTA was uniform grey regardless of urgency — losing the
// criticality info cycle-1 surfaced on the rail.

import type { FrameSeverity, TopbarCta } from "@/types/workbench_frame";

interface DynamicTopbarCtaProps {
  cta: TopbarCta;
  onClick?: () => void;
  /**
   * DEC-V61-202-SUB-M32-CYCLE2: rail severity drives the disabled
   * CTA's tone. Default "info" (sky-grey) preserves existing visual
   * for legacy mounts that don't pass this prop.
   */
  railSeverity?: FrameSeverity;
  /**
   * DEC-V61-204 (M4 C2): when a mutating CTA (submit_solve) has its
   * action in flight, render a disabled spinner state so the engineer
   * sees the run is running. Defaults to false — legacy mounts
   * (StepPanelShell) that omit it are unchanged.
   */
  busy?: boolean;
  /** Label shown in place of `cta.label` while `busy` (e.g. "求解中…"). */
  busyLabel?: string;
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

// DEC-V61-202-SUB-M32-CYCLE2: per-severity disabled-state classes.
// Pattern: muted version of the rail tone — same hue family,
// reduced saturation, cursor-not-allowed. cycle-1's DynamicFramePanel
// uses the saturated version of the same hues, so the disabled CTA
// reads as "same severity, but blocked".
const DISABLED_CLASS_BY_SEVERITY: Record<FrameSeverity, string> = {
  fail: "border-rose-800/60 bg-rose-950/40 text-rose-500/70 cursor-not-allowed",
  warn: "border-amber-800/60 bg-amber-950/40 text-amber-500/70 cursor-not-allowed",
  info: "border-sky-800/60 bg-sky-950/40 text-sky-500/70 cursor-not-allowed",
};

export function DynamicTopbarCta({
  cta,
  onClick,
  railSeverity,
  busy,
  busyLabel,
}: DynamicTopbarCtaProps) {
  const tone = KIND_TONE[cta.kind] ?? KIND_TONE.step_default;
  // Severity defaults to "info" when caller doesn't pass one — preserves
  // legacy sky-tone visual for mounts that predate this prop.
  const effectiveSeverity: FrameSeverity = railSeverity ?? "info";
  const disabledClass =
    DISABLED_CLASS_BY_SEVERITY[effectiveSeverity] ??
    DISABLED_CLASS_BY_SEVERITY.info;
  const isBusy = busy ?? false;
  // While busy the action is in flight: block interaction (no double-run)
  // but keep the enabled hue dimmed + cursor-wait so it reads "running",
  // not "blocked" (which would re-use the muted severity tones).
  const interactionDisabled = !cta.enabled || isBusy;
  const baseClass = cta.enabled ? tone.enabled : disabledClass;
  const className = isBusy ? `${tone.enabled} cursor-wait opacity-70` : baseClass;

  return (
    <button
      type="button"
      data-testid="dynamic-topbar-cta"
      data-kind={cta.kind}
      data-enabled={cta.enabled}
      data-busy={isBusy}
      data-rail-severity={effectiveSeverity}
      disabled={interactionDisabled}
      onClick={interactionDisabled ? undefined : onClick}
      title={cta.reason ?? undefined}
      aria-label={cta.label}
      aria-disabled={interactionDisabled}
      aria-busy={isBusy}
      className={`rounded-sm border px-2 py-0.5 font-mono text-[11px] uppercase tracking-wider transition ${className}`}
    >
      {isBusy ? (
        <span className="inline-flex items-center gap-1">
          <span
            aria-hidden
            className="inline-block h-2.5 w-2.5 animate-spin rounded-full border border-current border-t-transparent"
          />
          {busyLabel ?? cta.label}
        </span>
      ) : (
        cta.label
      )}
    </button>
  );
}
