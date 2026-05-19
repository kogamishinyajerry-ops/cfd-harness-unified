/**
 * V88.5 · V8.D Solver-config state machine + run-readiness signal
 *
 * Per .planning/blueprints/v8/INDEX.md Contract V8.D:
 *   - State machine: clean → dirty → saving → saved/error → dirty
 *   - Exposes `configReady` boolean that V7.A Run button gates on
 *     (via shell-level shared state · V7.A does NOT import this hook
 *     directly · reverse-stop #25)
 *   - Wraps existing `api.postRawDict()` (no new endpoint · V132 = 9)
 *   - V87.4 schema-drift carry: 422 / 409 responses surface as
 *     structured `error` state · NOT crash · NOT state corruption
 *   - V130 invariant: NO useEffect that fires commit · `confirmCommit`
 *     is only called from the V8.C diff confirm-button user-click path
 *
 * The hook accepts `postImpl` override so unit tests can drive
 * transitions deterministically without a real network.
 */

import { useCallback, useEffect, useReducer, useRef } from "react";

import { api } from "@/api/client";
import { ApiError } from "@/api/client";
import type {
  RawDictPostBody,
  RawDictPostResponse,
} from "@/types/case_dicts";

import {
  validateControlDictFields,
  parseControlDictFields,
  serializeControlDictFields,
} from "../components/solver_config_validator";
import type {
  ControlDictField,
  ValidationError,
} from "../components/solver_config_validator";

export type SolverConfigState =
  | "clean"
  | "dirty"
  | "saving"
  | "saved"
  | "error";

export interface SolverConfigStateV8 {
  state: SolverConfigState;
  fields: Partial<Record<ControlDictField, string>>;
  baseline: Partial<Record<ControlDictField, string>>;
  etag: string | null;
  baseContent: string;
  validationErrors: ValidationError[];
  errorMessage: string | null;
  /**
   * Computed: true iff state ∈ {clean, saved} AND validationErrors is
   * empty. Read by WorkbenchShellV3 → passed to V7.A Run button (NOT
   * imported by V7.A directly · reverse-stop #25).
   */
  configReady: boolean;

  setField: (field: ControlDictField, value: string) => void;
  /** Computed-only transition · NO fetch · used by V8.A "Review changes". */
  reviewChanges: () => void;
  /**
   * The ONE path that fires POST /dicts · invoked from V8.C "Confirm
   * commit" user-click. V130 invariant: NO useEffect calls this.
   */
  confirmCommit: () => Promise<void>;
  /** Returns to baseline · state → clean. */
  discard: () => void;
  /** Recoverable error transition · error → dirty (user retries). */
  dismissError: () => void;
  /** Hydrate baseline + etag from a fresh GET /dicts response. */
  hydrate: (input: {
    content: string;
    etag: string | null;
  }) => void;
}

interface ReducerState {
  state: SolverConfigState;
  fields: Partial<Record<ControlDictField, string>>;
  baseline: Partial<Record<ControlDictField, string>>;
  etag: string | null;
  baseContent: string;
  errorMessage: string | null;
}

type Action =
  | { type: "hydrate"; fields: Partial<Record<ControlDictField, string>>; etag: string | null; baseContent: string }
  | { type: "setField"; field: ControlDictField; value: string }
  | { type: "review" }
  | { type: "saving" }
  | { type: "saved"; etag: string; baseContent: string }
  | { type: "error"; message: string }
  | { type: "discard" }
  | { type: "dismissError" };

const INITIAL: ReducerState = {
  state: "clean",
  fields: {},
  baseline: {},
  etag: null,
  baseContent: "",
  errorMessage: null,
};

/** Shallow-equal check between two partial field maps. */
function fieldsEqual(
  a: Partial<Record<ControlDictField, string>>,
  b: Partial<Record<ControlDictField, string>>,
): boolean {
  const keys: ControlDictField[] = [
    "application",
    "endTime",
    "deltaT",
    "writeInterval",
    "writeFormat",
  ];
  return keys.every((k) => (a[k] ?? "") === (b[k] ?? ""));
}

function reducer(state: ReducerState, action: Action): ReducerState {
  switch (action.type) {
    case "hydrate":
      return {
        state: "clean",
        fields: { ...action.fields },
        baseline: { ...action.fields },
        etag: action.etag,
        baseContent: action.baseContent,
        errorMessage: null,
      };

    case "setField": {
      const nextFields = { ...state.fields, [action.field]: action.value };
      const isDirty = !fieldsEqual(nextFields, state.baseline);
      // From error → setField → dirty (user editing past the error).
      if (state.state === "error") {
        return {
          ...state,
          fields: nextFields,
          state: isDirty ? "dirty" : "clean",
          errorMessage: null,
        };
      }
      return {
        ...state,
        fields: nextFields,
        state: isDirty ? "dirty" : "clean",
      };
    }

    case "review":
      // Computed-only — does not change state. Validation happens via
      // the selector on `state.fields`. Including for symmetry with the
      // public API · no-op transition.
      return state;

    case "saving":
      // Caller guarantees state was "dirty" (validation passed). We
      // also tolerate "error" → "saving" for retry-after-fix.
      return { ...state, state: "saving", errorMessage: null };

    case "saved":
      return {
        ...state,
        state: "saved",
        baseline: { ...state.fields },
        etag: action.etag,
        baseContent: action.baseContent,
        errorMessage: null,
      };

    case "error":
      return { ...state, state: "error", errorMessage: action.message };

    case "discard":
      return {
        ...state,
        state: "clean",
        fields: { ...state.baseline },
        errorMessage: null,
      };

    case "dismissError":
      // error → dirty (so user can retry · or hit discard to clean).
      // Validation surface re-renders on next setField anyway.
      return { ...state, state: "dirty", errorMessage: null };

    default:
      return state;
  }
}

interface UseSolverConfigStateV8Options {
  caseId: string | null;
  relativePath?: string;
  /** Test override for `api.postRawDict`. */
  postImpl?: (
    caseId: string,
    relativePath: string,
    body: RawDictPostBody,
  ) => Promise<RawDictPostResponse>;
  /**
   * Optional: when supplied, hook auto-hydrates from this on mount /
   * caseId change. When null, caller is responsible for invoking
   * `hydrate()` directly (e.g. WorkbenchShellV3 already has a GET
   * /dicts query and passes the result in).
   */
  initial?: { content: string; etag: string | null } | null;
}

export function useSolverConfigStateV8(
  options: UseSolverConfigStateV8Options,
): SolverConfigStateV8 {
  const {
    caseId,
    relativePath = "system/controlDict",
    postImpl,
    initial,
  } = options;

  const [reducerState, dispatch] = useReducer(reducer, INITIAL);
  const stateRef = useRef(reducerState);
  stateRef.current = reducerState;

  // Hydration is data-flow — NOT V130-affecting auto-write. We read
  // existing on-disk content (GET) and seed baseline · no POST.
  useEffect(() => {
    if (initial == null) return;
    const parsed = parseControlDictFields(initial.content);
    dispatch({
      type: "hydrate",
      fields: parsed,
      etag: initial.etag,
      baseContent: initial.content,
    });
  }, [initial?.content, initial?.etag]);

  const hydrate = useCallback(
    (input: { content: string; etag: string | null }) => {
      const parsed = parseControlDictFields(input.content);
      dispatch({
        type: "hydrate",
        fields: parsed,
        etag: input.etag,
        baseContent: input.content,
      });
    },
    [],
  );

  const setField = useCallback(
    (field: ControlDictField, value: string) => {
      dispatch({ type: "setField", field, value });
    },
    [],
  );

  const reviewChanges = useCallback(() => {
    dispatch({ type: "review" });
  }, []);

  const discard = useCallback(() => {
    dispatch({ type: "discard" });
  }, []);

  const dismissError = useCallback(() => {
    dispatch({ type: "dismissError" });
  }, []);

  const confirmCommit = useCallback(async () => {
    const snapshot = stateRef.current;
    if (caseId == null) {
      dispatch({ type: "error", message: "no case selected" });
      return;
    }
    // Defense-in-depth: caller (V8.C) gates Confirm on no errors, but
    // re-check here so a stray programmatic call can't slip past.
    const errs = validateControlDictFields(snapshot.fields);
    if (errs.length > 0) {
      dispatch({
        type: "error",
        message: `validation failed: ${errs.map((e) => e.message).join("; ")}`,
      });
      return;
    }

    dispatch({ type: "saving" });

    const nextContent = serializeControlDictFields(
      snapshot.fields,
      snapshot.baseContent,
    );
    const body: RawDictPostBody = {
      content: nextContent,
      ...(snapshot.etag != null ? { expected_etag: snapshot.etag } : {}),
    };

    const fn = postImpl ?? api.postRawDict;
    try {
      const resp = await fn(caseId, relativePath, body);
      dispatch({
        type: "saved",
        etag: resp.new_etag,
        baseContent: nextContent,
      });
    } catch (err) {
      let message = "commit failed";
      if (err instanceof ApiError) {
        if (err.status === 409) {
          message =
            "file changed on disk · refresh and merge before retry (409 ETag mismatch)";
        } else if (err.status === 422) {
          message = `backend validation rejected: ${err.message}`;
        } else {
          message = err.message;
        }
      } else if (err instanceof Error) {
        message = err.message;
      }
      dispatch({ type: "error", message });
    }
  }, [caseId, relativePath, postImpl]);

  const validationErrors = validateControlDictFields(reducerState.fields);
  const configReady =
    (reducerState.state === "clean" || reducerState.state === "saved") &&
    validationErrors.length === 0 &&
    // Require at least one field populated · empty baseline (no dict on
    // disk) → not ready until user edits + commits.
    Object.values(reducerState.fields).some((v) => v != null && v !== "");

  return {
    state: reducerState.state,
    fields: reducerState.fields,
    baseline: reducerState.baseline,
    etag: reducerState.etag,
    baseContent: reducerState.baseContent,
    validationErrors,
    errorMessage: reducerState.errorMessage,
    configReady,
    setField,
    reviewChanges,
    confirmCommit,
    discard,
    dismissError,
    hydrate,
  };
}
