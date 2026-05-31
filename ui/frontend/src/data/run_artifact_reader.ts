/**
 * V85.2 · V6.A Bridge Reader · pure data module
 *
 * Maps a real-run artifact (RunDetail-shaped, served by existing
 * GET /api/cases/{case_id}/run-history/{run_id} endpoint) onto a per-step
 * BridgeStepState that DemoSandboxV5 can render in bridge mode.
 *
 * V6 contract V6.A · `.planning/blueprints/v6/INDEX.md`:
 *   - READ-ONLY · zero new MUTATING_ROUTES (consumes existing endpoint)
 *   - Graceful degrade: artifact null → returns null → caller falls back
 *     to curated `getSandboxStepState`
 *   - LLM-offline: pure deterministic mapping · no runtime LLM call
 *   - AI passive-observe: returns observations as banner text only · NO
 *     action recommendations · NO auto-execute affordance
 *
 * V130/V132 invariants:
 *   - No fetch in this module · callers supply the artifact via props
 *   - No mutation of input · returns new objects
 *   - All field reads guarded for missing/optional data (real artifacts
 *     in practice have sparse key_quantities/residuals)
 */

import type { StepId } from "../pages/workbench/v3/WorkbenchShellV3";

/** Subset of RunDetail (ui/backend/schemas/run_history.py) that V6.A reads.
 *  Keeping this narrow makes the contract explicit + lets us evolve the
 *  backend schema without breaking V6 unless the listed fields change. */
export interface BridgeArtifact {
  case_id: string;
  run_id: string;
  started_at: string;
  duration_s: number;
  success: boolean;
  exit_code: number;
  verdict_summary: string;
  failure_category?: string | null;
  task_spec?: Record<string, unknown>;
  key_quantities?: Record<string, unknown>;
  residuals?: Record<string, number>;
}

export interface BridgeStepState {
  source: "real_artifact";
  caseId: string;
  runId: string;
  /** Human-readable banner: short label (≤120 chars) with key real values
   *  interpolated. Mirrors V5 SandboxStepState.banner shape. */
  banner: string;
  /** Whether this step's source artifact reports success at the
   *  pipeline-level (verdict.success). Used by V6.C diff panel to flag
   *  divergence between curated (always success) and real (may fail). */
  artifactSuccess: boolean;
  /** Optional failure category (e.g., "solver_diverged") surfaced only as
   *  passive observation — V130 forbids action affordances here. */
  failureCategory?: string | null;
}

const STEP_LABELS: Record<StepId, string> = {
  1: "Import",
  2: "Mesh",
  3: "Physics",
  4: "Solver",
  5: "Postprocess",
};

function fmtTaskSpec(task: Record<string, unknown> | undefined): string {
  if (!task) return "task spec unavailable";
  const re = task["Re"];
  const flow = task["flow_type"];
  const steady = task["steady_state"];
  const comp = task["compressibility"];
  const parts: string[] = [];
  if (typeof re === "number" && Number.isFinite(re)) {
    // Real artifacts sometimes carry placeholder Re=99999999; surface
    // verbatim so V6.C diff panel can flag obvious placeholders.
    parts.push(`Re=${re}`);
  }
  if (typeof flow === "string") parts.push(flow);
  if (typeof steady === "string") parts.push(steady);
  if (typeof comp === "string") parts.push(comp);
  return parts.length > 0 ? parts.join(" · ") : "task spec sparse";
}

function fmtResiduals(residuals: Record<string, number> | undefined): string {
  if (!residuals || Object.keys(residuals).length === 0) {
    return "residuals not captured";
  }
  // Show up to 3 residual names with their final values (real runs
  // typically log Ux/Uy/p/k/omega). Format keeps the banner ≤ 120 chars.
  const entries = Object.entries(residuals).slice(0, 3);
  return entries
    .map(([k, v]) => `${k}=${v.toExponential(2)}`)
    .join(" · ");
}

function fmtDuration(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds <= 0) return "duration unknown";
  if (seconds < 60) return `${seconds.toFixed(1)}s`;
  if (seconds < 3600) return `${(seconds / 60).toFixed(1)}min`;
  return `${(seconds / 3600).toFixed(2)}h`;
}

/**
 * Returns the bridge step state for (artifact, step), or null when no
 * artifact is present. Callers handle null by falling back to the V5
 * curated `getSandboxStepState`.
 *
 * Step mapping rationale:
 *   - Step 1 (Import)     → task_spec (geometry/flow shape)
 *   - Step 2 (Mesh)       → key_quantities cell/y+ if present, else placeholder
 *   - Step 3 (Physics)    → task_spec (Re, steadiness, compressibility)
 *   - Step 4 (Solver)     → residuals + exit_code + duration
 *   - Step 5 (Postprocess)→ success + verdict_summary + failure_category
 */
export function getBridgeStepState(
  artifact: BridgeArtifact | null,
  step: StepId,
): BridgeStepState | null {
  if (artifact == null) return null;

  const stepLabel = STEP_LABELS[step];
  let banner: string;

  switch (step) {
    case 1: {
      const flow = fmtTaskSpec(artifact.task_spec);
      banner = `${stepLabel} · real run ${artifact.run_id} · ${flow}`;
      break;
    }
    case 2: {
      const kq = artifact.key_quantities ?? {};
      const cells = kq["cells"];
      const yp = kq["y_plus_max"];
      const cellsStr =
        typeof cells === "number"
          ? `${cells} cells`
          : "cell count not captured";
      const ypStr = typeof yp === "number" ? `y+ ≤ ${yp.toFixed(2)}` : "y+ not captured";
      banner = `${stepLabel} · ${cellsStr} · ${ypStr}`;
      break;
    }
    case 3: {
      banner = `${stepLabel} · ${fmtTaskSpec(artifact.task_spec)}`;
      break;
    }
    case 4: {
      const res = fmtResiduals(artifact.residuals);
      const exitStr = artifact.exit_code === 0 ? "exit=0" : `exit=${artifact.exit_code}`;
      const durStr = fmtDuration(artifact.duration_s);
      banner = `${stepLabel} · ${res} · ${exitStr} · ${durStr}`;
      break;
    }
    case 5: {
      const verdict = artifact.success ? "PASS" : "FAIL";
      const cat = artifact.failure_category
        ? ` · ${artifact.failure_category}`
        : "";
      // Cap verdict_summary to keep banner readable. Real runs may carry
      // multi-line OpenFOAM log fragments here.
      const summary = artifact.verdict_summary.split("\n")[0].slice(0, 60);
      banner = `${stepLabel} · ${verdict}${cat} · ${summary}`;
      break;
    }
  }

  return {
    source: "real_artifact",
    caseId: artifact.case_id,
    runId: artifact.run_id,
    banner,
    artifactSuccess: artifact.success,
    failureCategory: artifact.failure_category ?? null,
  };
}

/** Whether a case has at least one bridgeable artifact in the local
 *  reports tree. The actual probe runs server-side (via the
 *  /run-history endpoint); this function exists for callers that want
 *  a quick "is bridge mode even possible for this case" check.
 *
 *  V6.A is artifact-shape-aware but NOT filesystem-aware. The list of
 *  cases known to have real artifacts is curated here based on what's
 *  committed under `reports/{case_id}/runs/`. Callers can use this as a
 *  hint when deciding whether to render a "?bridge=1" entry point.
 *
 *  This list is INTENTIONALLY conservative — only cases with at least
 *  one captured run are listed. New cases get added when artifacts
 *  land in reports/. */
export const BRIDGE_KNOWN_CASES: ReadonlyArray<string> = [
  "lid_driven_cavity",
];

export function isBridgeKnownCase(caseId: string | null | undefined): boolean {
  if (caseId == null) return false;
  return BRIDGE_KNOWN_CASES.includes(caseId);
}
