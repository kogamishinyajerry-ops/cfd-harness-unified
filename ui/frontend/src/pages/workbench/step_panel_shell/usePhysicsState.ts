/**
 * V68-C.1 · Physics-state hook backing MaterialCard.
 *
 * Dual-mode design honoring V130 (advisor not actor):
 *   - Primary: GET /api/cases/:id/physics — committed dict text from
 *     IMPORTED_DIR. Returns 200 + nullable dict texts.
 *   - Fallback: GET /api/cases/:id — for whitelist cases the route
 *     returns 404 (case not in IMPORTED_DIR). We surface the case's
 *     solver + turbulence_model + parameters from CaseDetail as a
 *     *reference* view so MaterialCard can still render something
 *     meaningful in Step 3 for whitelist dogfood paths. We do NOT
 *     synthesize fake dict text — the parsed-fields readout is
 *     populated from CaseDetail.parameters; the raw-dict pane shows
 *     "(whitelist case · not materialized)".
 *
 * The hook returns a discriminated `PhysicsView` so MaterialCard can
 * branch cleanly without rebuilding the conditional itself.
 */
import { useQuery } from "@tanstack/react-query";

import { api } from "@/api/client";
import type { PhysicsStateResponse } from "@/types/physics";
import type { CaseDetail } from "@/types/validation";

export type PhysicsView =
  | {
      status: "committed";
      caseId: string;
      materialDictText: string | null;
      regimeDictText: string | null;
      // Parsed key fields from the dict text (best-effort regex; null
      // when the dict doesn't carry the field). Always shown alongside
      // the raw text for engineer audit.
      parsed: ParsedPhysics;
    }
  | {
      status: "reference";
      caseId: string;
      caseDetail: CaseDetail;
      parsed: ParsedPhysics;
    }
  | { status: "loading"; caseId: string }
  | { status: "error"; caseId: string; message: string }
  | { status: "no-case"; caseId: null };

export interface ParsedPhysics {
  // physicalProperties / transportProperties parsed surface
  transportModel: string | null; // "Newtonian" | ...
  nu: number | null; // kinematic viscosity m²/s
  rho: number | null; // density kg/m³
  // momentumTransport parsed surface
  simulationType: string | null; // "laminar" | "RAS" | "LES"
  rasModel: string | null; // "kOmegaSST" | "kEpsilon" | ...
  // Whitelist-derived fallback fields
  solver: string | null; // "icoFoam" | "simpleFoam" | ...
  turbulenceModel: string | null; // "laminar" | "k-omega SST" | ...
  reynolds: number | null;
}

const EMPTY_PARSED: ParsedPhysics = {
  transportModel: null,
  nu: null,
  rho: null,
  simulationType: null,
  rasModel: null,
  solver: null,
  turbulenceModel: null,
  reynolds: null,
};

// Parse an OpenFOAM dict text for the canonical material fields.
// Regex-based intentionally — the dicts are line-oriented and writer.py
// emits a stable format. Best-effort: missing fields stay null.
export function parsePhysicalProperties(text: string): Partial<ParsedPhysics> {
  const out: Partial<ParsedPhysics> = {};
  const mTransport = /transportModel\s+([A-Za-z_][\w]*)\s*;/.exec(text);
  if (mTransport) out.transportModel = mTransport[1];
  // Match either:  nu  [0 2 -1 0 0 0 0] 1e-3;   or   nu  1e-3;
  const mNu = /\bnu\b(?:\s+\[[^\]]+\])?\s+([+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)\s*;/.exec(
    text,
  );
  if (mNu) out.nu = Number(mNu[1]);
  const mRho = /\brho\b(?:\s+\[[^\]]+\])?\s+([+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)\s*;/.exec(
    text,
  );
  if (mRho) out.rho = Number(mRho[1]);
  return out;
}

export function parseMomentumTransport(text: string): Partial<ParsedPhysics> {
  const out: Partial<ParsedPhysics> = {};
  const mSim = /simulationType\s+([A-Za-z_][\w]*)\s*;/.exec(text);
  if (mSim) out.simulationType = mSim[1];
  const mRAS = /RASModel\s+([A-Za-z_][\w]*)\s*;/.exec(text);
  if (mRAS) out.rasModel = mRAS[1];
  return out;
}

export function parsePhysicsState(
  state: PhysicsStateResponse,
): ParsedPhysics {
  const out: ParsedPhysics = { ...EMPTY_PARSED };
  if (state.material_dict_text) {
    Object.assign(out, parsePhysicalProperties(state.material_dict_text));
  }
  if (state.regime_dict_text) {
    Object.assign(out, parseMomentumTransport(state.regime_dict_text));
  }
  return out;
}

export function parseCaseDetailReference(detail: CaseDetail): ParsedPhysics {
  const out: ParsedPhysics = { ...EMPTY_PARSED };
  out.solver = detail.solver;
  out.turbulenceModel = detail.turbulence_model;
  const re = detail.parameters?.["Re"];
  if (typeof re === "number") out.reynolds = re;
  // Derive a simulationType hint from turbulence_model so the UI's
  // primary readout still has something to show on whitelist cases.
  const tm = (detail.turbulence_model ?? "").toLowerCase();
  if (tm.includes("laminar")) out.simulationType = "laminar";
  else if (tm.includes("rans") || tm.includes("k-omega") || tm.includes("k-epsilon")) {
    out.simulationType = "RAS";
  } else if (tm.includes("les")) out.simulationType = "LES";
  return out;
}

export function usePhysicsState(caseId: string | null | undefined): PhysicsView {
  const enabled = Boolean(caseId);
  const physicsQuery = useQuery({
    queryKey: ["physics-state", caseId],
    queryFn: () => api.getPhysicsState(caseId!),
    enabled,
    staleTime: 15_000,
    refetchOnWindowFocus: false,
    retry: false,
  });

  // Fallback: only fire when physics returned null (case not imported)
  // — this is the whitelist-case path. Avoids double-fetch when the
  // primary path resolved with committed data.
  const fallbackEnabled = enabled && physicsQuery.data === null;
  const detailQuery = useQuery({
    queryKey: ["case-detail-for-physics", caseId],
    queryFn: () => api.getCase(caseId!),
    enabled: fallbackEnabled,
    staleTime: 30_000,
    refetchOnWindowFocus: false,
    retry: false,
  });

  if (!caseId) return { status: "no-case", caseId: null };

  if (physicsQuery.isLoading) {
    return { status: "loading", caseId };
  }
  if (physicsQuery.isError) {
    const msg =
      physicsQuery.error instanceof Error
        ? physicsQuery.error.message
        : "physics state fetch failed";
    return { status: "error", caseId, message: msg };
  }

  // Primary path resolved with non-null payload → committed view.
  if (physicsQuery.data) {
    return {
      status: "committed",
      caseId,
      materialDictText: physicsQuery.data.material_dict_text,
      regimeDictText: physicsQuery.data.regime_dict_text,
      parsed: parsePhysicsState(physicsQuery.data),
    };
  }

  // physicsQuery.data === null → 404 → fall back to CaseDetail.
  if (detailQuery.isLoading) {
    return { status: "loading", caseId };
  }
  if (detailQuery.isError) {
    const msg =
      detailQuery.error instanceof Error
        ? detailQuery.error.message
        : "case detail fetch failed";
    return { status: "error", caseId, message: msg };
  }
  if (detailQuery.data) {
    return {
      status: "reference",
      caseId,
      caseDetail: detailQuery.data,
      parsed: parseCaseDetailReference(detailQuery.data),
    };
  }

  return { status: "loading", caseId };
}
