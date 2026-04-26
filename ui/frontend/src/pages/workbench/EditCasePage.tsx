import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import jsYaml from "js-yaml";

import { api, ApiError } from "@/api/client";
import type { CaseYamlPayload } from "@/types/editor";

// M2 · Workbench Closed-Loop main-line — /workbench/case/:caseId/edit
//
// A param-form-driven editor for an existing whitelist case. Loads YAML via
// case_editor.py (which itself prefers user_drafts over whitelist), parses it
// client-side with js-yaml, surfaces only the `parameters` and numeric
// `boundary_conditions` fields as form inputs, re-serialises on every change,
// and on submit:
//   1. PUT /api/cases/{id}/yaml → writes user_drafts/{id}.yaml
//   2. navigate /workbench/run/:caseId → triggers RealSolverDriver via the
//      wizard SSE route (CFD_HARNESS_WIZARD_SOLVER=real). RealSolverDriver's
//      _task_spec_from_case_id will pick up the user_draft override.
//
// Scope contract (M2 · 2026-04-26): line-A only. No foam_agent_adapter touch,
// no whitelist write, no gold_standards write. The YAML editor full surface
// (CodeMirror at /cases/:caseId/edit) stays as the pro escape hatch for users
// who need to edit boundary_conditions strings or geometry_type.

type LoadedCase = {
  raw: Record<string, unknown>; // full parsed YAML doc
  origin: "draft" | "whitelist";
  draft_path: string | null;
};

const PARAM_KEYS_ORDERED = ["Re", "Ra", "Re_tau", "Ma"] as const;
type ParamKey = (typeof PARAM_KEYS_ORDERED)[number];

function isFiniteNumber(x: unknown): x is number {
  return typeof x === "number" && Number.isFinite(x);
}

function pickNumericBcs(bc: unknown): Record<string, number> {
  if (!bc || typeof bc !== "object") return {};
  const out: Record<string, number> = {};
  for (const [k, v] of Object.entries(bc as Record<string, unknown>)) {
    if (isFiniteNumber(v)) out[k] = v;
  }
  return out;
}

export function EditCasePage() {
  const { caseId = "" } = useParams<{ caseId: string }>();
  const navigate = useNavigate();
  const qc = useQueryClient();

  const sourceQuery = useQuery({
    queryKey: ["caseYaml", caseId],
    queryFn: () => api.getCaseYaml(caseId),
    enabled: Boolean(caseId),
  });

  // Local form state — initialised once on first successful load, then
  // diverges from the server until the user hits Save / Reset.
  const [paramOverrides, setParamOverrides] = useState<Partial<Record<ParamKey, number>>>({});
  const [bcOverrides, setBcOverrides] = useState<Record<string, number>>({});
  const [errorMsg, setErrorMsg] = useState<string>("");

  const loaded: LoadedCase | null = useMemo(() => {
    if (!sourceQuery.data) return null;
    try {
      const raw = jsYaml.load(sourceQuery.data.yaml_text);
      if (!raw || typeof raw !== "object" || Array.isArray(raw)) {
        return null;
      }
      return {
        raw: raw as Record<string, unknown>,
        origin: sourceQuery.data.origin === "draft" ? "draft" : "whitelist",
        draft_path: sourceQuery.data.draft_path,
      };
    } catch {
      return null;
    }
  }, [sourceQuery.data]);

  // First-load: prime the form state from the parsed YAML.
  useEffect(() => {
    if (!loaded) return;
    const params = (loaded.raw.parameters ?? {}) as Record<string, unknown>;
    const seedParams: Partial<Record<ParamKey, number>> = {};
    for (const k of PARAM_KEYS_ORDERED) {
      if (isFiniteNumber(params[k])) seedParams[k] = params[k];
    }
    setParamOverrides(seedParams);
    setBcOverrides(pickNumericBcs(loaded.raw.boundary_conditions));
    // Only seed once per loaded source.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sourceQuery.data?.yaml_text]);

  // Reconstruct the YAML doc with the form's overrides merged in. This is
  // what we PUT to the server and what we render in the preview block —
  // single source of truth so the user never sees drift between preview
  // and what /workbench/run actually receives.
  const renderedYaml = useMemo(() => {
    if (!loaded) return "";
    const merged: Record<string, unknown> = {
      ...loaded.raw,
      parameters: {
        ...((loaded.raw.parameters as Record<string, unknown>) ?? {}),
        ...Object.fromEntries(
          Object.entries(paramOverrides).filter(([, v]) => isFiniteNumber(v)),
        ),
      },
      boundary_conditions: {
        ...((loaded.raw.boundary_conditions as Record<string, unknown>) ?? {}),
        ...bcOverrides,
      },
    };
    return jsYaml.dump(merged, { indent: 2, lineWidth: 100, sortKeys: false });
  }, [loaded, paramOverrides, bcOverrides]);

  const saveAndRunMutation = useMutation({
    mutationFn: async () => {
      const payload: CaseYamlPayload = {
        case_id: caseId,
        yaml_text: renderedYaml,
        origin: "draft",
        draft_path: null,
      };
      const result = await api.putCaseYaml(payload);
      if (!result.saved) {
        throw new Error(
          `server rejected draft: ${result.lint.errors.join("; ") || "(no error message)"}`,
        );
      }
      return result;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["caseYaml", caseId] });
      navigate(`/workbench/run/${encodeURIComponent(caseId)}`);
    },
    onError: (err) => {
      setErrorMsg(err instanceof ApiError ? `${err.status}: ${err.message}` : String(err));
    },
  });

  const revertMutation = useMutation({
    mutationFn: () => api.revertCaseYaml(caseId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["caseYaml", caseId] });
      setErrorMsg("");
    },
    onError: (err) => {
      setErrorMsg(err instanceof ApiError ? `${err.status}: ${err.message}` : String(err));
    },
  });

  if (!caseId) {
    return (
      <Section>
        <p className="text-sm text-contract-fail">missing :caseId path param</p>
      </Section>
    );
  }
  if (sourceQuery.isLoading) {
    return <Section><p className="text-surface-300">Loading {caseId}…</p></Section>;
  }
  if (sourceQuery.isError || !sourceQuery.data) {
    const msg =
      sourceQuery.error instanceof ApiError
        ? `${sourceQuery.error.status}: ${sourceQuery.error.message}`
        : String(sourceQuery.error);
    return (
      <Section>
        <p className="text-sm text-contract-fail">Failed to load case YAML: {msg}</p>
      </Section>
    );
  }
  if (sourceQuery.data.origin === "missing") {
    return (
      <Section>
        <p className="text-sm text-contract-fail">
          Case <code>{caseId}</code> not found in whitelist or user_drafts.
        </p>
      </Section>
    );
  }
  if (!loaded) {
    return (
      <Section>
        <p className="text-sm text-contract-fail">
          YAML for <code>{caseId}</code> failed to parse client-side.
          Open the pro editor at{" "}
          <Link to={`/cases/${caseId}/edit`} className="underline">
            /cases/{caseId}/edit
          </Link>{" "}
          to inspect.
        </p>
      </Section>
    );
  }

  const params = (loaded.raw.parameters ?? {}) as Record<string, unknown>;
  const declaredParams = PARAM_KEYS_ORDERED.filter((k) => k in params);
  const numericBcKeys = Object.keys(pickNumericBcs(loaded.raw.boundary_conditions));

  return (
    <Section>
      <header className="mb-6">
        <div className="text-[11px] uppercase tracking-wider text-surface-500">
          <Link to="/learn" className="hover:text-surface-300">Learn</Link>
          <span className="mx-1.5">/</span>
          <Link to={`/learn/cases/${caseId}`} className="hover:text-surface-300">{caseId}</Link>
          <span className="mx-1.5">/</span>
          <span>edit (workbench)</span>
        </div>
        <h1 className="mt-1 text-2xl font-semibold text-surface-100">
          Edit · {String(loaded.raw.name ?? caseId)}
        </h1>
        <p className="mt-1 text-[12px] text-surface-400">
          Tweak numeric parameters and run against the real OpenFOAM solver.
          Changes save to <code>ui/backend/user_drafts/{caseId}.yaml</code> —
          never to <code>knowledge/whitelist.yaml</code>.
        </p>
      </header>

      <OriginBadge origin={loaded.origin} draftPath={loaded.draft_path} />

      <div className="mt-6 grid grid-cols-[minmax(280px,1fr)_minmax(320px,1.4fr)] gap-6">
        {/* --- Form column --- */}
        <div className="space-y-5">
          {declaredParams.length === 0 && numericBcKeys.length === 0 && (
            <p className="text-xs text-surface-500">
              This case has no numeric parameters or boundary conditions exposed
              to the simplified editor. Use the{" "}
              <Link to={`/cases/${caseId}/edit`} className="underline">pro YAML editor</Link>.
            </p>
          )}

          {declaredParams.length > 0 && (
            <fieldset className="rounded-md border border-surface-800 p-4">
              <legend className="px-2 text-[11px] uppercase tracking-wider text-surface-400">
                Parameters
              </legend>
              <div className="space-y-3">
                {declaredParams.map((k) => (
                  <NumberField
                    key={k}
                    label={k}
                    value={paramOverrides[k] ?? null}
                    onChange={(v) =>
                      setParamOverrides((prev) => ({ ...prev, [k]: v ?? undefined }))
                    }
                    hint={paramHint(k)}
                  />
                ))}
              </div>
            </fieldset>
          )}

          {numericBcKeys.length > 0 && (
            <fieldset className="rounded-md border border-surface-800 p-4">
              <legend className="px-2 text-[11px] uppercase tracking-wider text-surface-400">
                Boundary conditions (numeric only)
              </legend>
              <div className="space-y-3">
                {numericBcKeys.map((k) => (
                  <NumberField
                    key={k}
                    label={k}
                    value={bcOverrides[k] ?? null}
                    onChange={(v) =>
                      setBcOverrides((prev) => {
                        if (v === null) {
                          const { [k]: _ignored, ...rest } = prev;
                          return rest;
                        }
                        return { ...prev, [k]: v };
                      })
                    }
                  />
                ))}
              </div>
            </fieldset>
          )}

          <div className="flex flex-wrap items-center gap-3 pt-2">
            <button
              type="button"
              onClick={() => saveAndRunMutation.mutate()}
              disabled={saveAndRunMutation.isPending}
              className="rounded-sm bg-contract-pass/80 px-4 py-1.5 text-sm font-medium text-surface-950 transition hover:bg-contract-pass disabled:opacity-50"
            >
              {saveAndRunMutation.isPending ? "Saving…" : "Save & run with these params"}
            </button>
            {loaded.origin === "draft" && (
              <button
                type="button"
                onClick={() => revertMutation.mutate()}
                disabled={revertMutation.isPending}
                className="rounded-sm border border-surface-700 px-3 py-1.5 text-xs text-surface-300 transition hover:bg-surface-800"
              >
                Revert to whitelist
              </button>
            )}
            <Link
              to={`/cases/${caseId}/edit`}
              className="text-xs text-surface-400 underline hover:text-surface-200"
            >
              Pro YAML editor →
            </Link>
          </div>

          {errorMsg && (
            <p className="rounded-sm border border-contract-fail/40 bg-contract-fail/10 p-3 text-xs text-contract-fail">
              {errorMsg}
            </p>
          )}
        </div>

        {/* --- Preview column --- */}
        <div className="space-y-2">
          <div className="flex items-baseline justify-between">
            <h3 className="text-[11px] uppercase tracking-wider text-surface-400">
              YAML preview (byte-exact draft body)
            </h3>
            <span className="font-mono text-[10px] text-surface-500">
              {renderedYaml.length} chars
            </span>
          </div>
          <pre className="max-h-[60vh] overflow-auto rounded-md border border-surface-800 bg-surface-950/60 p-3 text-[11px] leading-relaxed text-surface-200">
            {renderedYaml}
          </pre>
          <p className="text-[10px] text-surface-500">
            This is the exact body that will land at{" "}
            <code>ui/backend/user_drafts/{caseId}.yaml</code> on save.
            <code>RealSolverDriver</code> picks it up before falling back to{" "}
            <code>knowledge/whitelist.yaml</code>.
          </p>
        </div>
      </div>
    </Section>
  );
}

// ---------- Helpers --------------------------------------------------------

function Section({ children }: { children: React.ReactNode }) {
  return <section className="mx-auto max-w-6xl px-8 py-8">{children}</section>;
}

function OriginBadge({
  origin,
  draftPath,
}: {
  origin: "draft" | "whitelist";
  draftPath: string | null;
}) {
  if (origin === "draft") {
    return (
      <div className="rounded-sm border border-amber-500/40 bg-amber-500/10 p-3 text-[12px] text-amber-300">
        <strong>Draft active</strong> — loaded from{" "}
        <code className="font-mono text-[11px]">{draftPath ?? "user_drafts/"}</code>.
        Click <strong>Revert to whitelist</strong> below to drop the draft and start over.
      </div>
    );
  }
  return (
    <div className="rounded-sm border border-surface-700 bg-surface-900/40 p-3 text-[12px] text-surface-300">
      <strong>Whitelist baseline</strong> — no user draft yet. Save below will create one.
    </div>
  );
}

function NumberField({
  label,
  value,
  onChange,
  hint,
}: {
  label: string;
  value: number | null;
  onChange: (v: number | null) => void;
  hint?: string;
}) {
  const [text, setText] = useState<string>(value === null ? "" : String(value));
  // Keep local text in sync if external state resets (e.g. revert).
  useEffect(() => {
    setText(value === null ? "" : String(value));
  }, [value]);
  return (
    <label className="block">
      <span className="block text-[11px] font-mono uppercase tracking-wider text-surface-400">
        {label}
      </span>
      <input
        type="text"
        inputMode="decimal"
        value={text}
        onChange={(ev) => {
          const raw = ev.target.value;
          setText(raw);
          if (raw.trim() === "") {
            onChange(null);
            return;
          }
          const n = Number(raw);
          if (Number.isFinite(n)) onChange(n);
        }}
        className="mt-1 w-full rounded-sm border border-surface-700 bg-surface-900 px-2 py-1 font-mono text-[13px] text-surface-100 outline-none focus:border-surface-500"
      />
      {hint && <span className="mt-1 block text-[10px] text-surface-500">{hint}</span>}
    </label>
  );
}

function paramHint(k: string): string | undefined {
  switch (k) {
    case "Re":
      return "Reynolds number — sets ν = U·L/Re for incompressible flow.";
    case "Ra":
      return "Rayleigh number — buoyancy-driven scale.";
    case "Re_tau":
      return "Friction Reynolds number — wall-bounded turbulent scale.";
    case "Ma":
      return "Mach number — compressibility regime.";
    default:
      return undefined;
  }
}
