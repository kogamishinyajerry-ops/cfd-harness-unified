/**
 * V89.2 · V8 state-injection harness · dev/test-only
 *
 * Per .planning/decisions/2026-05-17_v89_charter_dec.md §6 reverse-stops #28-#29:
 *   - ACTIVE only when `import.meta.env.DEV` OR `import.meta.env.MODE === 'test'`
 *   - Production builds discard the URL param silently
 *   - MUST NOT enable AI auto-write · MUST NOT fire any mutating fetch ·
 *     injected `error` state shows banner WITHOUT having issued a POST
 *
 * Usage:
 *   /workbench/v3/case/lid_driven_cavity?step=4&btab=open&_v89_inject=dirty
 *   /workbench/v3/case/lid_driven_cavity?step=4&btab=open&_v89_inject=diff_open
 *   /workbench/v3/case/lid_driven_cavity?step=4&btab=open&_v89_inject=error
 *
 * Output is consumed by WorkbenchShellV3 to override the `solverConfig`
 * slice passed to BottomPanelV3 → SolverConfigEditorV8. Pure presentational
 * state · no fetch · no state-machine transitions · no manifest writes.
 *
 * V130 invariant preserved: injection only affects what the user SEES,
 * not what the system DOES. The `error` injection shows a 409-style
 * banner but does NOT have a prior POST in the network log.
 */

import type {
  ControlDictField,
  ValidationError,
} from "./solver_config_validator";
import type { SolverConfigEditorState } from "./SolverConfigEditorV8";

export type InjectionKey = "dirty" | "diff_open" | "error";

export interface InjectedSlice {
  state: SolverConfigEditorState;
  fields: Partial<Record<ControlDictField, string>>;
  baseline: Partial<Record<ControlDictField, string>>;
  validationErrors: ValidationError[];
  errorMessage: string | null;
  /** Force the V8.C diff preview open without requiring a user click. */
  forceDiffOpen: boolean;
  /** Inject identifier for inspection via data-attribute. */
  injectionKey: InjectionKey;
}

/**
 * Canonical baseline that the injected slices treat as "on-disk" content.
 * Matches the V88 baseline test harness for consistency.
 */
const CANONICAL_BASELINE: Partial<Record<ControlDictField, string>> = {
  application: "icoFoam",
  endTime: "10.0",
  deltaT: "0.005",
  writeInterval: "0.5",
  writeFormat: "ascii",
};

/**
 * Build the dirty-state slice: endTime edited from 10.0 → 20.0.
 * No validation errors · Review-changes button enabled · diff closed.
 */
function buildDirtySlice(): InjectedSlice {
  return {
    state: "dirty",
    fields: { ...CANONICAL_BASELINE, endTime: "20.0" },
    baseline: CANONICAL_BASELINE,
    validationErrors: [],
    errorMessage: null,
    forceDiffOpen: false,
    injectionKey: "dirty",
  };
}

/**
 * Build the diff-open slice: same dirty fields + diff modal pre-opened.
 * V8.A's local showDiff state is overridden via `forceDiffOpen`.
 */
function buildDiffOpenSlice(): InjectedSlice {
  return {
    state: "dirty",
    fields: { ...CANONICAL_BASELINE, endTime: "20.0" },
    baseline: CANONICAL_BASELINE,
    validationErrors: [],
    errorMessage: null,
    forceDiffOpen: true,
    injectionKey: "diff_open",
  };
}

/**
 * Build the error-state slice: synthetic 409 ETag-mismatch error
 * displayed without an actual POST having fired. Diff stays closed so
 * the error banner is visible at the editor level.
 */
function buildErrorSlice(): InjectedSlice {
  return {
    state: "error",
    fields: { ...CANONICAL_BASELINE, endTime: "20.0" },
    baseline: CANONICAL_BASELINE,
    validationErrors: [],
    errorMessage:
      "file changed on disk · refresh and merge before retry (409 ETag mismatch)",
    forceDiffOpen: false,
    injectionKey: "error",
  };
}

/**
 * Env-gated injection reader.
 *
 * @param key - The injection key from URL param `_v89_inject`
 * @param envMode - Optional override for tests. When undefined, reads
 *   `import.meta.env.MODE` directly. Tests can pass "production" to
 *   verify production builds discard injection.
 * @returns The injected slice OR null when injection is inactive
 */
export function readInjectionState(
  key: string | null | undefined,
  envMode?: string,
): InjectedSlice | null {
  // Production builds DISCARD the param silently · V130 invariant
  // preserved · the injection harness is a dev/test affordance only.
  //
  // When caller passes explicit `envMode`, that is the authoritative
  // gate (used by contract tests to verify production semantics).
  // When caller omits `envMode`, fall back to `import.meta.env` which
  // is bundler-injected.
  let isDev: boolean;
  if (envMode !== undefined) {
    isDev = envMode === "development" || envMode === "test";
  } else {
    const mode = (import.meta.env as { MODE?: string })?.MODE;
    isDev =
      Boolean((import.meta.env as { DEV?: boolean })?.DEV) ||
      mode === "development" ||
      mode === "test";
  }
  if (!isDev) return null;
  if (!key) return null;

  switch (key) {
    case "dirty":
      return buildDirtySlice();
    case "diff_open":
      return buildDiffOpenSlice();
    case "error":
      return buildErrorSlice();
    default:
      // Unknown injection key · ignored (forward-compat · don't crash
      // production-mode dev builds that may see stale URLs)
      return null;
  }
}
