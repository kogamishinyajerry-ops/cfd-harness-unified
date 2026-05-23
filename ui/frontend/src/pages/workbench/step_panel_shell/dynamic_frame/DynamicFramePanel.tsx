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
import { useManifestPatch } from "./useManifestPatch";

interface DynamicFramePanelProps {
  rail: RailPrimary;
  caseId?: string;
  manifestStateSha?: string;
}

// DEC-V61-202-SUB-M31-CYCLE2 Codex R0 P2 fix: explicit allow-list of
// top-level scalar paths that can be edited via the inline text input.
// Each entry is a manifest field_path that the backend PATCH endpoint
// accepts as a top-level scalar string. Adding to this list MUST be
// accompanied by:
//   1. analyzer emitting a no-payload gap for the path
//   2. PATCH endpoint validation accepting the string value
//   3. tests covering the new path
// Cycle 2 ships only `case_family`. M3.1 cycle 3+ extends as new
// scalar gaps land (e.g. engineer-named overrides, future scalar
// metadata fields).
const INLINE_EDITABLE_SCALAR_PATHS: ReadonlySet<string> = new Set([
  "case_family",
]);

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

export function DynamicFramePanel({
  rail,
  caseId,
  manifestStateSha,
}: DynamicFramePanelProps) {
  const [showProvenance, setShowProvenance] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const tone = KIND_TONE[rail.kind] ?? KIND_TONE.step_default;

  // DEC-V61-202-SUB-M30-CYCLE2: wire CTA → PATCH when the rail card
  // targets a specific field_path AND a suggested_default is available
  // AND we have caseId + manifest_state_sha context.
  const patch = useManifestPatch({
    caseId: caseId ?? "",
    onSuccess: (response) => {
      if (!response.success && response.validation_errors.length > 0) {
        setErrorMsg(response.validation_errors[0]);
      } else {
        setErrorMsg(null);
      }
    },
    onError: (err) => {
      setErrorMsg(err instanceof Error ? err.message : String(err));
    },
  });
  const canApply =
    Boolean(caseId) &&
    Boolean(manifestStateSha) &&
    Boolean(rail.field_path) &&
    rail.suggested_default !== null &&
    rail.suggested_default !== undefined;
  const onCtaClick = () => {
    if (!canApply || !rail.field_path || !manifestStateSha) return;
    setErrorMsg(null);
    patch.mutate({
      field_path: rail.field_path,
      value: rail.suggested_default,
      expected_state_sha: manifestStateSha,
    });
  };

  // DEC-V61-202-SUB-M31-CYCLE1: domain-aware form helper. When the
  // rail carries a `suggested_skeleton` (structural dict for fields
  // like `bc.patches` on ship_vof cases), render a secondary CTA
  // alongside the primary "Apply" / "Edit" button. Clicking PATCHes
  // the entire skeleton dict at `field_path`. The two CTAs share the
  // same patch.mutate flow but submit different payloads.
  const canApplySkeleton =
    Boolean(caseId) &&
    Boolean(manifestStateSha) &&
    Boolean(rail.field_path) &&
    rail.suggested_skeleton !== null &&
    rail.suggested_skeleton !== undefined;
  const onSkeletonCtaClick = () => {
    if (!canApplySkeleton || !rail.field_path || !manifestStateSha) return;
    setErrorMsg(null);
    patch.mutate({
      field_path: rail.field_path,
      value: rail.suggested_skeleton,
      expected_state_sha: manifestStateSha,
    });
  };

  // DEC-V61-202-SUB-M31-CYCLE2: inline scalar input. When the rail
  // surfaces a `field_path` with NO `suggested_default` and NO
  // `suggested_skeleton`, the engineer needs a way to type the value
  // themselves. Cycle 1 left the primary `编辑 / Edit` button disabled
  // because no auto-apply payload existed — a non-actionable prompt.
  // This affordance gives any scalar-typed gap a one-shot inline
  // input + Apply button. case_family is the first user-visible surface.
  //
  // Codex R0 P1 fix: gate on `rail.kind === "info_gap"` so
  // `problem_fix` rails (audit findings like `bc_contract.pressure`)
  // stay as view-only diagnostics. They carry field_path for
  // navigation but must not become editable text boxes.
  //
  // Codex R0 P2 fix: explicit allow-list of top-level scalar paths.
  // Cycle 2 ships `case_family` only; other no-payload gaps (e.g.
  // `bc.patches` when no skeleton exists, or bracketed paths like
  // `physics_contract.physics_precondition[0]`) must NOT render the
  // text input — they expect non-string types or reject bracket
  // segments at the PATCH endpoint. Future cycles extend the list as
  // new scalar gaps land.
  const showInlineInput =
    Boolean(caseId) &&
    Boolean(manifestStateSha) &&
    Boolean(rail.field_path) &&
    rail.kind === "info_gap" &&
    INLINE_EDITABLE_SCALAR_PATHS.has(rail.field_path ?? "") &&
    (rail.suggested_default === null || rail.suggested_default === undefined) &&
    (rail.suggested_skeleton === null || rail.suggested_skeleton === undefined);
  const [inlineValue, setInlineValue] = useState("");
  const inlineApplyEnabled = inlineValue.trim().length > 0 && !patch.isPending;
  const onInlineApply = () => {
    if (!showInlineInput || !inlineApplyEnabled || !rail.field_path || !manifestStateSha) return;
    setErrorMsg(null);
    patch.mutate({
      field_path: rail.field_path,
      value: inlineValue.trim(),
      expected_state_sha: manifestStateSha,
    });
  };
  // When inline input is shown, suppress the original disabled primary
  // CTA — same suppression shape as cycle-1's cta_label=null path for
  // skeleton-only gaps. Avoids two dead/duplicate buttons.
  //
  // Codex R1 P2 fix (cycle 2): also suppress when the rail intrinsically
  // has no action available (no suggested_default, no suggested_skeleton,
  // and not in the inline-edit allow-list). This catches fallback
  // states like a `bc.patches` gap with no skeleton (case_family
  // still unknown) where the rail carries cta_label="编辑 / Edit" but
  // no payload — the button is permanently dead because no PATCH
  // context can help. Hide it instead of showing a misleading
  // disabled affordance.
  //
  // Critically: this distinguishes "intrinsically dead" from
  // "missing PATCH context". A rail with `suggested_default` but no
  // caseId still shows the disabled CTA (signal: context is missing
  // but the action IS available). problem_fix rails (audit
  // diagnostics) keep their button — those are intentionally view-only.
  const railHasIntrinsicAction =
    (rail.suggested_default !== null && rail.suggested_default !== undefined) ||
    (rail.suggested_skeleton !== null && rail.suggested_skeleton !== undefined) ||
    (rail.field_path !== null &&
      rail.field_path !== undefined &&
      INLINE_EDITABLE_SCALAR_PATHS.has(rail.field_path));
  const suppressPrimaryCta =
    showInlineInput ||
    (!railHasIntrinsicAction && rail.kind === "info_gap");

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

      {rail.cta_label && !suppressPrimaryCta && (
        <button
          type="button"
          data-testid="dynamic-frame-cta"
          onClick={canApply ? onCtaClick : undefined}
          disabled={!canApply || patch.isPending}
          aria-disabled={!canApply || patch.isPending}
          className={`mt-3 rounded-sm border px-2 py-1 text-[11px] transition ${
            canApply && !patch.isPending
              ? "border-sky-700/60 bg-sky-900/40 text-sky-200 hover:bg-sky-900/60"
              : "border-surface-700 bg-surface-900/40 text-surface-500 cursor-not-allowed"
          }`}
        >
          {patch.isPending ? "应用中…" : rail.cta_label}
        </button>
      )}

      {/* DEC-V61-202-SUB-M31-CYCLE2: inline scalar input. Lets engineers
          type values for scalar gaps (like case_family) directly on the
          rail. Active when the gap has field_path + no auto-apply
          payload + PATCH context. The original "编辑 / Edit" button is
          suppressed above to avoid two dead/duplicate buttons. */}
      {showInlineInput && (
        <div
          data-testid="dynamic-frame-inline-edit"
          className="mt-3 flex items-center gap-2"
        >
          <input
            type="text"
            data-testid="dynamic-frame-inline-input"
            value={inlineValue}
            onChange={(e) => setInlineValue(e.target.value)}
            placeholder={`${rail.field_path}`}
            disabled={patch.isPending}
            className="min-w-0 flex-1 rounded-sm border border-surface-700 bg-surface-900/60 px-2 py-1 text-[11px] text-surface-100 placeholder:text-surface-600 focus:border-sky-700/60 focus:outline-none disabled:cursor-not-allowed disabled:opacity-50"
          />
          <button
            type="button"
            data-testid="dynamic-frame-inline-apply"
            onClick={onInlineApply}
            disabled={!inlineApplyEnabled}
            aria-disabled={!inlineApplyEnabled}
            className={`rounded-sm border px-2 py-1 text-[11px] transition ${
              inlineApplyEnabled
                ? "border-sky-700/60 bg-sky-900/40 text-sky-200 hover:bg-sky-900/60"
                : "border-surface-700 bg-surface-900/40 text-surface-500 cursor-not-allowed"
            }`}
          >
            {patch.isPending ? "应用中…" : "应用 / Apply"}
          </button>
        </div>
      )}

      {/* DEC-V61-202-SUB-M31-CYCLE1: skeleton CTA. Renders only when a
          domain-aware skeleton is available. Amber styling marks it as
          a heavier commit than the scalar Apply (it writes a whole
          nested dict at field_path). Both buttons can coexist when the
          backend offers both a scalar default AND a skeleton. */}
      {canApplySkeleton && (
        <button
          type="button"
          data-testid="dynamic-frame-skeleton-cta"
          onClick={onSkeletonCtaClick}
          disabled={patch.isPending}
          aria-disabled={patch.isPending}
          className={`mt-2 ml-2 rounded-sm border px-2 py-1 text-[11px] transition ${
            !patch.isPending
              ? "border-amber-700/60 bg-amber-900/40 text-amber-200 hover:bg-amber-900/60"
              : "border-surface-700 bg-surface-900/40 text-surface-500 cursor-not-allowed"
          }`}
        >
          {patch.isPending ? "应用中…" : "应用骨架 / Apply skeleton"}
        </button>
      )}

      {errorMsg && (
        <p
          data-testid="dynamic-frame-error"
          className="mt-2 text-[10px] text-rose-300"
        >
          {errorMsg}
        </p>
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
