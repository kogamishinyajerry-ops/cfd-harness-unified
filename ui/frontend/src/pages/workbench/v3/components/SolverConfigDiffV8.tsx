/**
 * V88.4 · V8.C SolverConfigDiffV8 · Diff preview gate before commit
 *
 * Per .planning/blueprints/v8/INDEX.md Contract V8.C:
 *   - Two-column display: current on-disk vs pending edit
 *   - Changed fields highlighted with sand-coral accent (<2% pixel budget)
 *   - Validation errors rendered inline above Confirm · Confirm DISABLED
 *     when errors present (V88 reverse-stop #23 + #24)
 *   - "Confirm commit" is the ONE user-click that fires the commit · V130
 *     denylist asserts no "auto-commit" / "AI applies" verbiage
 *   - "Cancel" returns to editor without firing any fetch
 *
 * Component is pure presentational — parent supplies handlers.
 * State machine lives in V8.D (useSolverConfigStateV8).
 */

import type {
  ControlDictField,
  ValidationError,
} from "./solver_config_validator";

interface SolverConfigDiffV8Props {
  current: Partial<Record<ControlDictField, string>>;
  pending: Partial<Record<ControlDictField, string>>;
  validationErrors: ValidationError[];
  /** When state is "saving", Confirm button shows in-flight label. */
  isSaving?: boolean;
  /** When state is "error", an inline error banner surfaces with retry hint. */
  errorMessage?: string | null;
  onConfirm: () => void;
  onCancel: () => void;
}

const FIELD_ORDER: ControlDictField[] = [
  "application",
  "endTime",
  "deltaT",
  "writeInterval",
  "writeFormat",
];

export function SolverConfigDiffV8({
  current,
  pending,
  validationErrors,
  isSaving = false,
  errorMessage,
  onConfirm,
  onCancel,
}: SolverConfigDiffV8Props) {
  const changedFields = FIELD_ORDER.filter(
    (f) => (current[f] ?? "") !== (pending[f] ?? ""),
  );
  const hasErrors = validationErrors.length > 0;
  const confirmDisabled = hasErrors || isSaving || changedFields.length === 0;

  // V130: human-curated labels · NO "auto-commit" / "AI applies" verbiage.
  // This component takes a USER click before any POST fires.
  const confirmLabel = isSaving ? "Saving…" : "Confirm commit";

  return (
    <div
      data-testid="solver-config-diff-v8"
      data-changed-fields-count={String(changedFields.length)}
      data-validation-error-count={String(validationErrors.length)}
      data-state-saving={isSaving ? "true" : "false"}
      className="flex flex-col gap-2 border border-v3-border rounded p-3 bg-v3-panel"
    >
      <header className="flex items-center justify-between">
        <h3 className="text-[11px] font-mono uppercase tracking-[0.08em] text-v3-textSecondary">
          Review changes before commit
        </h3>
        <span
          data-testid="solver-config-diff-v8-summary"
          className="text-[10px] font-mono text-v3-textTertiary"
        >
          {changedFields.length} field
          {changedFields.length === 1 ? "" : "s"} changed
        </span>
      </header>

      <table className="w-full text-[11px] font-mono">
        <thead>
          <tr className="text-v3-textTertiary text-left">
            <th className="py-1 pr-2 font-normal">field</th>
            <th className="py-1 pr-2 font-normal">on disk</th>
            <th className="py-1 font-normal">pending</th>
          </tr>
        </thead>
        <tbody>
          {FIELD_ORDER.map((field) => {
            const cur = current[field] ?? "";
            const pen = pending[field] ?? "";
            const changed = cur !== pen;
            return (
              <tr
                key={field}
                data-testid={`solver-config-diff-row-${field}`}
                data-changed={changed ? "true" : "false"}
                className={
                  changed
                    ? "border-t border-v3-border/40"
                    : "border-t border-v3-border/20 opacity-60"
                }
              >
                <td className="py-1 pr-2 text-v3-textSecondary">{field}</td>
                <td className="py-1 pr-2 text-v3-textTertiary">{cur || "—"}</td>
                <td
                  className={
                    changed
                      ? "py-1 text-v3-accent"
                      : "py-1 text-v3-textTertiary"
                  }
                >
                  {pen || "—"}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>

      {hasErrors && (
        <ul
          data-testid="solver-config-diff-v8-errors"
          className="flex flex-col gap-0.5 text-[10px] font-mono text-v3-danger"
        >
          {validationErrors.map((err, idx) => (
            <li
              key={`${err.field}-${err.kind}-${idx}`}
              data-testid={`solver-config-diff-v8-error-${err.field}`}
            >
              <span className="uppercase tracking-[0.06em]">[{err.field}]</span>{" "}
              {err.message}
            </li>
          ))}
        </ul>
      )}

      {errorMessage && (
        <p
          data-testid="solver-config-diff-v8-commit-error"
          className="text-[10px] font-mono text-v3-danger"
        >
          {errorMessage}
        </p>
      )}

      <footer className="flex items-center justify-end gap-2">
        <button
          type="button"
          data-testid="solver-config-diff-v8-cancel"
          onClick={onCancel}
          disabled={isSaving}
          className="px-3 py-1 text-[11px] font-mono uppercase tracking-[0.08em] border border-v3-border rounded text-v3-textSecondary hover:text-v3-textPrimary disabled:opacity-50 disabled:cursor-not-allowed focus:outline focus:outline-2 focus:outline-v3-borderFocus"
        >
          Cancel
        </button>
        <button
          type="button"
          data-testid="solver-config-diff-v8-confirm"
          onClick={onConfirm}
          disabled={confirmDisabled}
          aria-label="Confirm controlDict commit"
          className="px-3 py-1 text-[11px] font-mono uppercase tracking-[0.08em] border border-v3-accent rounded text-v3-accent hover:bg-v3-accent/10 disabled:opacity-50 disabled:cursor-not-allowed focus:outline focus:outline-2 focus:outline-v3-borderFocus"
        >
          {confirmLabel}
        </button>
      </footer>
    </div>
  );
}
