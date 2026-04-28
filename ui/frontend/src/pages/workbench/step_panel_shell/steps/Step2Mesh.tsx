// Step 2 · Mesh — wired body (DEC-V61-096 spec_v2 §E Step 5).
//
// Surfaces the gmsh+sHM mesh-mode form (beginner / power) and registers
// a mesh-generation action with the shell so the StepNavigation
// [AI 处理] button drives it. On success the polyMesh lands at
// <case>/constant/polyMesh/ and the center-pane Viewport (driven by
// Step 2's viewportConfig) re-fetches /api/cases/<id>/mesh/render.

import { useCallback, useEffect, useState } from "react";

import { api, ApiError } from "@/api/client";
import type {
  MeshMode,
  MeshRejectionDetail,
  MeshSuccessResponse,
} from "@/types/mesh_imported";

import type { StepTaskPanelProps } from "../types";

const REJECTION_HINTS: Record<string, string> = {
  cell_cap_exceeded:
    "Coarsen the geometry or pick a different mesh tier. The 50M-cell hard cap is a resource guard, not a quality threshold.",
  gmsh_diverged:
    "gmsh failed to converge on this geometry. Verify the STL is watertight and free of self-intersections in your CAD.",
  gmshToFoam_failed:
    "The OpenFOAM container could not convert the mesh. Confirm cfd-openfoam is running (docker ps | grep cfd-openfoam).",
  source_not_imported:
    "This case has no triSurface/ STL to mesh — only imported cases can use the gmsh path.",
};

export function Step2Mesh({
  caseId,
  onStepComplete,
  onStepError,
  registerAiAction,
}: StepTaskPanelProps) {
  const [meshMode, setMeshMode] = useState<MeshMode>("beginner");
  const [response, setResponse] = useState<MeshSuccessResponse | null>(null);
  const [rejection, setRejection] = useState<MeshRejectionDetail | null>(null);
  const [networkError, setNetworkError] = useState<string | null>(null);

  // Register the mesh-generation action with the shell. The shell's
  // wrapped onAiProcess sets aiInFlight + captures errors; this body
  // owns the form state + structured rejection panel.
  const triggerMesh = useCallback(async () => {
    setRejection(null);
    setNetworkError(null);
    try {
      const r = await api.meshImported(caseId, meshMode);
      setResponse(r);
      onStepComplete();
    } catch (e) {
      if (
        e instanceof ApiError &&
        e.detail &&
        typeof e.detail === "object"
      ) {
        const detail = e.detail as MeshRejectionDetail;
        setRejection(detail);
        onStepError(`mesh rejected: ${detail.failing_check}`);
      } else {
        const msg = e instanceof Error ? e.message : String(e);
        setNetworkError(msg);
        onStepError(msg);
      }
      // Re-throw so the shell's aiInFlight wrapper sees the failure
      // and surfaces aiErrorMessage in the StatusStrip.
      throw e;
    }
  }, [caseId, meshMode, onStepComplete, onStepError]);

  useEffect(() => {
    registerAiAction(triggerMesh);
    return () => registerAiAction(null);
  }, [registerAiAction, triggerMesh]);

  return (
    <div className="space-y-3 p-3 text-[12px]" data-testid="step2-mesh-body">
      <h2 className="text-sm font-mono uppercase tracking-wider text-surface-200">
        Step 2 · Mesh
      </h2>
      <p className="text-surface-400">
        Generate the polyMesh via gmsh + sHM. Click [AI 处理] in the
        navigation row below to run gmsh on the imported STL — the
        request stays open for ~30–300 s.
      </p>

      <fieldset className="border-0 p-0">
        <legend className="mb-2 block text-[10px] font-mono uppercase tracking-wider text-surface-500">
          Mesh sizing tier
        </legend>
        <div className="flex flex-col gap-2">
          <ModeOption
            value="beginner"
            label="Beginner"
            hint="≈5M-cell sizing target"
            checked={meshMode === "beginner"}
            onChange={() => setMeshMode("beginner")}
          />
          <ModeOption
            value="power"
            label="Power"
            hint="finer · 50M hard cap"
            checked={meshMode === "power"}
            onChange={() => setMeshMode("power")}
          />
        </div>
      </fieldset>

      {response && (
        <div
          data-testid="step2-mesh-success"
          className="rounded-sm border border-emerald-500/30 bg-emerald-500/5 p-2"
        >
          <div className="flex items-baseline justify-between">
            <strong className="text-emerald-300">Mesh generated</strong>
            <code className="font-mono text-[11px] text-surface-500">
              {response.mesh_summary.mesh_mode_used}
            </code>
          </div>
          <dl className="mt-2 grid grid-cols-[max-content_1fr] gap-x-3 gap-y-1 font-mono text-[11px]">
            <dt className="text-surface-500">cells</dt>
            <dd className="text-surface-200">
              {response.mesh_summary.cell_count.toLocaleString()}
            </dd>
            <dt className="text-surface-500">faces</dt>
            <dd className="text-surface-200">
              {response.mesh_summary.face_count.toLocaleString()}
            </dd>
            <dt className="text-surface-500">points</dt>
            <dd className="text-surface-200">
              {response.mesh_summary.point_count.toLocaleString()}
            </dd>
            <dt className="text-surface-500">time</dt>
            <dd className="text-surface-200">
              {response.mesh_summary.generation_time_s.toFixed(2)}s
            </dd>
          </dl>
          {response.mesh_summary.warning && (
            <p className="mt-2 rounded-sm border border-amber-500/40 bg-amber-500/10 px-2 py-1 text-[11px] text-amber-200">
              {response.mesh_summary.warning}
            </p>
          )}
        </div>
      )}

      {rejection && (
        <div
          data-testid="step2-mesh-rejection"
          className="rounded-sm border border-rose-500/40 bg-rose-500/10 p-2"
        >
          <div className="flex items-baseline justify-between">
            <strong className="text-rose-200">Mesh rejected</strong>
            <code className="font-mono text-[11px] text-rose-300">
              {rejection.failing_check}
            </code>
          </div>
          <p className="mt-1 text-rose-200/90">{rejection.reason}</p>
          {REJECTION_HINTS[rejection.failing_check] && (
            <p className="mt-1 text-rose-200/80">
              {REJECTION_HINTS[rejection.failing_check]}
            </p>
          )}
        </div>
      )}

      {networkError && (
        <p
          data-testid="step2-mesh-network-error"
          className="rounded-sm border border-rose-500/40 bg-rose-500/10 px-2 py-1 text-rose-200"
        >
          Network error: {networkError}
        </p>
      )}
    </div>
  );
}

function ModeOption({
  value,
  label,
  hint,
  checked,
  onChange,
}: {
  value: MeshMode;
  label: string;
  hint: string;
  checked: boolean;
  onChange: () => void;
}) {
  return (
    <label
      data-testid={`step2-mesh-mode-${value}`}
      className={`flex cursor-pointer items-baseline gap-2 rounded-sm border px-2 py-1 transition ${
        checked
          ? "border-emerald-500/60 bg-emerald-500/10"
          : "border-surface-800 bg-surface-950/40 hover:border-surface-700"
      }`}
    >
      <input
        type="radio"
        name="step2-mesh-mode"
        value={value}
        checked={checked}
        onChange={onChange}
        className="accent-emerald-400"
      />
      <span className="text-[11px] font-semibold text-surface-100">
        {label}
      </span>
      <span className="text-[11px] text-surface-400">{hint}</span>
    </label>
  );
}
