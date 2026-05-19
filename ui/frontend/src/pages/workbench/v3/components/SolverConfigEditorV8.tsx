/**
 * V88.2 · V8.A SolverConfigEditorV8 · USER-edit form for OpenFOAM controlDict
 *
 * Per .planning/blueprints/v8/INDEX.md Contract V8.A:
 *   - Surfaces in Engineer Control Rail / Right Panel Inspector tab —
 *     NOT in sandbox / cinematic / bridge (V83.2 + V83.4 + V85.X + V87 carries)
 *   - Hidden behaviorally when readOnlyMode=true (?demo=1 / ?demo=2 / ?bridge=1)
 *   - USER-click only · NO useEffect auto-write · NO timer-based auto-commit
 *   - "Review changes" surfaces V8.C diff preview · DISABLED on clean / errors
 *   - "Discard" returns to baseline · only visible when dirty
 *   - V130 invariant lexically enforced via denylist tests (no "auto-save",
 *     "auto-commit", "AI applies", "automatic" verbiage)
 *
 * Component is pure presentational — parent (WorkbenchShellV3) supplies
 * state + handlers via the V8.D `useSolverConfigStateV8` hook.
 *
 * V88 reverse-stops enforced:
 *   #20 V8.A behavioral disable in read-only modes
 *   #23 Edits MUST go through V8.C diff preview before commit
 *   #24 Validation errors MUST surface pre-commit
 */

import { useState } from "react";

import { SolverConfigDiffV8 } from "./SolverConfigDiffV8";
import {
  KNOWN_SOLVERS,
  ALLOWED_WRITE_FORMATS,
} from "./solver_config_validator";
import type {
  ControlDictField,
  ValidationError,
} from "./solver_config_validator";

export type SolverConfigEditorState =
  | "clean"
  | "dirty"
  | "saving"
  | "saved"
  | "error";

interface SolverConfigEditorV8Props {
  caseId: string | null;
  /** Hidden behaviorally when true (sandbox/cinematic/bridge modes). */
  readOnlyMode?: boolean;
  /** Editor state · fields + baseline + validation surfaced from V8.D. */
  fields: Partial<Record<ControlDictField, string>>;
  baseline: Partial<Record<ControlDictField, string>>;
  state: SolverConfigEditorState;
  validationErrors: ValidationError[];
  errorMessage: string | null;
  onFieldChange: (field: ControlDictField, value: string) => void;
  onConfirmCommit: () => void;
  onDiscard: () => void;
  /** V89.2 injection harness · forces V8.C diff open without a user click.
   *  Dev/test only · production never receives this prop because the
   *  shell's injection reader is env-gated (reverse-stop #28). */
  forceDiffOpen?: boolean;
}

const FIELD_HINTS: Record<ControlDictField, string> = {
  application: "OpenFOAM solver (e.g. icoFoam, simpleFoam)",
  endTime: "simulation end time (seconds)",
  deltaT: "timestep (seconds) · must be ≤ endTime",
  writeInterval: "write cadence (seconds) · must be ≤ endTime",
  writeFormat: "ascii (readable) or binary (smaller)",
};

const FIELD_ORDER: ControlDictField[] = [
  "application",
  "endTime",
  "deltaT",
  "writeInterval",
  "writeFormat",
];

export function SolverConfigEditorV8({
  caseId,
  readOnlyMode = false,
  fields,
  baseline,
  state,
  validationErrors,
  errorMessage,
  onFieldChange,
  onConfirmCommit,
  onDiscard,
  forceDiffOpen,
}: SolverConfigEditorV8Props) {
  const [showDiff, setShowDiff] = useState(false);

  // Reverse-stop #20: hidden in read-only modes (sandbox/cinematic/bridge).
  // We render a placeholder for inspection rather than null so e2e tests
  // can assert the structural disable without DOM rebuild.
  if (readOnlyMode) {
    return (
      <div
        data-testid="solver-config-editor-v8"
        data-readonly-mode="true"
        data-config-state="readonly"
        className="text-[10px] font-mono text-v3-textTertiary opacity-50"
      >
        solver config editor unavailable in read-only modes
      </div>
    );
  }

  const caseUnset = caseId == null;
  const isDirty = state === "dirty" || state === "error";
  const hasErrors = validationErrors.length > 0;
  const reviewDisabled = caseUnset || !isDirty || hasErrors;
  const isSaving = state === "saving";

  // Reverse-stop #23: "Review changes" gate · diff opens BEFORE commit.
  // The Confirm in the diff is the ONE path that fires onConfirmCommit.
  const handleReview = () => {
    if (reviewDisabled) return;
    setShowDiff(true);
  };

  const handleConfirm = () => {
    onConfirmCommit();
    // Diff stays mounted while saving so user sees the saving label · we
    // close it on saved or error-dismiss via the next render.
  };

  const handleCancelDiff = () => {
    setShowDiff(false);
  };

  // Auto-close diff on saved (no longer dirty · no fields changed).
  // This is data-driven · not a useEffect auto-fire. Pure render.
  // V89.2: when `forceDiffOpen` is true (dev/test injection harness),
  // the diff renders without requiring a user click. The injection
  // reader is env-gated in the shell · production never sets this true.
  const diffOpen = (showDiff || Boolean(forceDiffOpen)) && state !== "saved";

  return (
    <section
      data-testid="solver-config-editor-v8"
      data-case-id={caseId ?? "__none__"}
      data-config-state={state}
      data-validation-status={hasErrors ? "invalid" : "valid"}
      data-readonly-mode="false"
      className="flex flex-col gap-3 border border-v3-border rounded p-3 bg-v3-panel"
      aria-label="Solver configuration editor"
    >
      <header className="flex items-center justify-between">
        <h3 className="text-[11px] font-mono uppercase tracking-[0.08em] text-v3-textSecondary">
          Solver configuration · system/controlDict
        </h3>
        <span
          data-testid="solver-config-editor-v8-state-pill"
          className={
            state === "dirty"
              ? "text-[10px] font-mono text-v3-accent uppercase tracking-[0.06em]"
              : state === "error"
              ? "text-[10px] font-mono text-v3-danger uppercase tracking-[0.06em]"
              : "text-[10px] font-mono text-v3-textTertiary uppercase tracking-[0.06em]"
          }
        >
          {state}
        </span>
      </header>

      <form
        className="flex flex-col gap-2"
        onSubmit={(e) => {
          // Defensive: even if user hits Enter, we ONLY open the diff —
          // never auto-fire commit (reverse-stop #23).
          e.preventDefault();
          handleReview();
        }}
      >
        {FIELD_ORDER.map((field) => {
          const fieldError = validationErrors.find((e) => e.field === field);
          const value = fields[field] ?? "";
          const isSelect =
            field === "application" || field === "writeFormat";
          const options =
            field === "application"
              ? KNOWN_SOLVERS
              : field === "writeFormat"
              ? ALLOWED_WRITE_FORMATS
              : [];
          return (
            <label
              key={field}
              data-testid={`solver-config-editor-v8-field-${field}`}
              className="flex flex-col gap-0.5"
            >
              <span className="text-[10px] font-mono text-v3-textSecondary uppercase tracking-[0.06em]">
                {field}
              </span>
              {isSelect ? (
                <select
                  data-testid={`solver-config-editor-v8-input-${field}`}
                  value={value}
                  onChange={(e) => onFieldChange(field, e.target.value)}
                  disabled={caseUnset || isSaving}
                  className="px-2 py-1 text-[11px] font-mono border border-v3-border rounded bg-v3-panel text-v3-textPrimary focus:outline focus:outline-2 focus:outline-v3-borderFocus disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <option value="">(select)</option>
                  {options.map((opt) => (
                    <option key={opt} value={opt}>
                      {opt}
                    </option>
                  ))}
                </select>
              ) : (
                <input
                  type="text"
                  inputMode={
                    field === "endTime" ||
                    field === "deltaT" ||
                    field === "writeInterval"
                      ? "decimal"
                      : "text"
                  }
                  data-testid={`solver-config-editor-v8-input-${field}`}
                  value={value}
                  onChange={(e) => onFieldChange(field, e.target.value)}
                  disabled={caseUnset || isSaving}
                  className="px-2 py-1 text-[11px] font-mono border border-v3-border rounded bg-v3-panel text-v3-textPrimary focus:outline focus:outline-2 focus:outline-v3-borderFocus disabled:opacity-50 disabled:cursor-not-allowed"
                />
              )}
              <span className="text-[9px] font-mono text-v3-textTertiary">
                {FIELD_HINTS[field]}
              </span>
              {fieldError && (
                <span
                  data-testid={`solver-config-editor-v8-fielderror-${field}`}
                  className="text-[9px] font-mono text-v3-danger"
                >
                  {fieldError.message}
                </span>
              )}
            </label>
          );
        })}
      </form>

      <footer className="flex items-center justify-end gap-2">
        {isDirty && (
          <button
            type="button"
            data-testid="solver-config-editor-v8-discard"
            onClick={onDiscard}
            disabled={isSaving}
            className="px-3 py-1 text-[11px] font-mono uppercase tracking-[0.08em] border border-v3-border rounded text-v3-textSecondary hover:text-v3-textPrimary disabled:opacity-50 disabled:cursor-not-allowed focus:outline focus:outline-2 focus:outline-v3-borderFocus"
          >
            Discard
          </button>
        )}
        <button
          type="button"
          data-testid="solver-config-editor-v8-review"
          onClick={handleReview}
          disabled={reviewDisabled}
          aria-label="Open diff preview for review before commit"
          className="px-3 py-1 text-[11px] font-mono uppercase tracking-[0.08em] border border-v3-accent rounded text-v3-accent hover:bg-v3-accent/10 disabled:opacity-50 disabled:cursor-not-allowed focus:outline focus:outline-2 focus:outline-v3-borderFocus"
        >
          Review changes
        </button>
      </footer>

      {state === "error" && errorMessage && !diffOpen && (
        <p
          data-testid="solver-config-editor-v8-error-banner"
          className="text-[10px] font-mono text-v3-danger"
        >
          {errorMessage}
        </p>
      )}

      {diffOpen && (
        <SolverConfigDiffV8
          current={baseline}
          pending={fields}
          validationErrors={validationErrors}
          isSaving={isSaving}
          errorMessage={state === "error" ? errorMessage : null}
          onConfirm={handleConfirm}
          onCancel={handleCancelDiff}
        />
      )}
    </section>
  );
}
