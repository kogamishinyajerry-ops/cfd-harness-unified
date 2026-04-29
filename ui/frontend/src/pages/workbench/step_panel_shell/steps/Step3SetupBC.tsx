// Step 3 · Setup BC — wired in Phase-1A (DEC-V61-097).
//
// LDC-only scope: the gmsh pipeline produces a mesh of the STL interior,
// which is correct as a flow domain ONLY for closed-cavity geometries
// (the ldc_box demo). For external-flow demos (cylinder, naca0012)
// the mesh is the obstacle interior — useless for CFD; that requires
// a separate blockMesh+sHM pipeline (Phase-2 / Phase-3 milestones).
//
// This component:
// 1. Calls POST /api/import/<id>/setup-bc — splits gmshToFoam's single
//    patch into `lid` + `fixedWalls` and authors icoFoam dicts.
// 2. Surfaces the lid-face count + Re number so the user sees the
//    geometric classification worked.
// 3. Registers the action so the shell's [AI 处理] button is enabled.

import { useCallback, useEffect, useMemo, useState } from "react";

import { api, ApiError } from "@/api/client";
import type {
  CaseSolveRejection,
  SetupBcSummary,
} from "@/types/case_solve";

import { AnnotationPanel } from "../AnnotationPanel";
import { useFacePickOptional } from "../FacePickContext";
import type {
  AnnotationsDocument,
  FaceAnnotation,
  StepTaskPanelProps,
} from "../types";

const REJECTION_HINTS: Record<string, string> = {
  not_an_ldc_cube:
    "This geometry doesn't look like an axis-aligned cube. The Phase-1A demo only supports the ldc_box fixture; cylinder/airfoil need an external-flow pipeline (Phase-2).",
  mesh_missing:
    "Step 2 (mesh) hasn't been run for this case — go back and click [AI 处理] on Step 2 first.",
  case_not_found:
    "This case_id isn't in the imported drafts directory. Re-run Step 1 (import).",
};

export function Step3SetupBC({
  caseId,
  onStepComplete,
  onStepError,
  registerAiAction,
}: StepTaskPanelProps) {
  const [summary, setSummary] = useState<SetupBcSummary | null>(null);
  const [rejection, setRejection] = useState<CaseSolveRejection | null>(null);
  const [networkError, setNetworkError] = useState<string | null>(null);

  // M-AI-COPILOT face-annotation state (DEC-V61-098 spec_v2 §A8). The
  // FacePickContext (populated by the Viewport pickMode wiring) is
  // optional — when null we just render the legacy form. When present,
  // a picked face_id surfaces the AnnotationPanel below the BC summary.
  const facePick = useFacePickOptional();
  const [annotations, setAnnotations] = useState<AnnotationsDocument | null>(
    null,
  );
  const [annotationsLoadError, setAnnotationsLoadError] = useState<
    string | null
  >(null);

  // Lazy-load annotations doc once the case_id is known. We don't gate
  // the panel on this because the existing-annotation seed is purely
  // optional UX (the AnnotationPanel handles the no-existing case).
  useEffect(() => {
    if (!caseId) return;
    let cancelled = false;
    api
      .getFaceAnnotations(caseId)
      .then((doc) => {
        if (cancelled) return;
        setAnnotations(doc);
        setAnnotationsLoadError(null);
      })
      .catch((e) => {
        if (cancelled) return;
        const msg = e instanceof Error ? e.message : String(e);
        setAnnotationsLoadError(msg);
      });
    return () => {
      cancelled = true;
    };
  }, [caseId]);

  const existingForPicked = useMemo<FaceAnnotation | undefined>(() => {
    if (!facePick?.picked || !annotations) return undefined;
    return annotations.faces.find(
      (f) => f.face_id === facePick.picked!.faceId,
    );
  }, [facePick?.picked, annotations]);

  const handleSaveAnnotation = useCallback(
    async (patch: FaceAnnotation) => {
      if (!annotations) {
        throw new Error("annotations not loaded yet");
      }
      const updated = await api.putFaceAnnotations(caseId, {
        if_match_revision: annotations.revision,
        faces: [patch],
        annotated_by: "human",
      });
      setAnnotations(updated);
      facePick?.setPicked(null);
    },
    [annotations, caseId, facePick],
  );

  const handleCancelPick = useCallback(() => {
    facePick?.setPicked(null);
  }, [facePick]);

  const triggerSetup = useCallback(async () => {
    setRejection(null);
    setNetworkError(null);
    try {
      const r = await api.setupBC(caseId);
      setSummary(r);
      onStepComplete();
    } catch (e) {
      if (
        e instanceof ApiError &&
        e.detail &&
        typeof e.detail === "object" &&
        "failing_check" in e.detail
      ) {
        const detail = e.detail as CaseSolveRejection;
        setRejection(detail);
        onStepError(`setup-bc rejected: ${detail.failing_check}`);
      } else {
        const msg = e instanceof Error ? e.message : String(e);
        setNetworkError(msg);
        onStepError(msg);
      }
      throw e;
    }
  }, [caseId, onStepComplete, onStepError]);

  useEffect(() => {
    registerAiAction(triggerSetup);
    return () => registerAiAction(null);
  }, [registerAiAction, triggerSetup]);

  return (
    <div className="space-y-3 p-3 text-[12px]" data-testid="step3-setup-bc-body">
      <h2 className="text-sm font-mono uppercase tracking-wider text-surface-200">
        Step 3 · Setup BC
      </h2>
      <p className="text-surface-400">
        Auto-classify boundary patches and write OpenFOAM dicts for
        icoFoam (LDC, Re=100, U_lid=1 m/s).
      </p>

      <div className="rounded-sm border border-amber-700/40 bg-amber-900/10 px-2 py-1 text-[10px] text-amber-200">
        Phase-1A scope: this only works on closed-cavity geometries
        (the <code>ldc_box</code> demo). External-flow demos require
        Phase-2 (blockMesh + sHM).
      </div>

      {!summary && !rejection && !networkError && (
        <p className="rounded-sm border border-surface-800 bg-surface-900/40 px-2 py-1 text-[11px] text-surface-400">
          Click <strong className="text-surface-200">[AI 处理]</strong> below
          to split the mesh into lid + walls and write BC dicts.
        </p>
      )}

      {summary && (
        <div
          data-testid="step3-setup-bc-success"
          className="space-y-2 rounded-sm border border-emerald-700/40 bg-emerald-900/10 p-2"
        >
          <div className="font-mono text-[11px] text-emerald-200">
            ✓ Boundary patches split, dicts written
          </div>
          <ul className="space-y-1 font-mono text-[10px] text-surface-300">
            <li>
              lid faces: <span className="text-emerald-300">{summary.n_lid_faces}</span>{" "}
              ({summary.lid_velocity[0]} {summary.lid_velocity[1]} {summary.lid_velocity[2]}) m/s
            </li>
            <li>
              wall faces: <span className="text-emerald-300">{summary.n_wall_faces}</span>{" "}
              (no-slip)
            </li>
            <li>
              ν: <span className="text-emerald-300">{summary.nu.toExponential(3)}</span>{" "}
              m²/s &nbsp;→&nbsp; Re ={" "}
              <span className="text-emerald-300">{summary.reynolds.toFixed(0)}</span>
            </li>
            <li className="pt-1 text-surface-500">
              {summary.written_files.length} dict files written
            </li>
          </ul>
        </div>
      )}

      {rejection && (
        <div
          data-testid="step3-setup-bc-rejection"
          className="space-y-1 rounded-sm border border-rose-700/50 bg-rose-900/10 p-2 text-[11px]"
        >
          <div className="font-mono text-rose-300">
            ✗ {rejection.failing_check}
          </div>
          <div className="text-rose-200">{rejection.detail}</div>
          {REJECTION_HINTS[rejection.failing_check] && (
            <div className="pt-1 text-[10px] text-rose-300/70">
              {REJECTION_HINTS[rejection.failing_check]}
            </div>
          )}
        </div>
      )}

      {networkError && (
        <div
          data-testid="step3-setup-bc-network-error"
          className="rounded-sm border border-rose-700/50 bg-rose-900/10 px-2 py-1 text-[11px] text-rose-200"
        >
          Network error: {networkError}
        </div>
      )}

      {/* M-AI-COPILOT face annotations (DEC-V61-098 §A8). The panel
       *  surfaces only when the engineer has picked a face in the
       *  Viewport — see ../FacePickContext. The existing form above
       *  remains the LDC dogfood path; this is the collab-first
       *  extension that lets the engineer pin user_authoritative
       *  metadata onto individual boundary faces. */}
      {facePick?.picked && (
        <AnnotationPanel
          faceId={facePick.picked.faceId}
          existing={existingForPicked}
          disabled={!annotations}
          onSave={handleSaveAnnotation}
          onCancel={handleCancelPick}
        />
      )}

      {annotationsLoadError && (
        <p
          data-testid="step3-annotations-load-error"
          className="rounded-sm border border-rose-700/30 bg-rose-900/5 px-2 py-1 text-[10px] text-rose-300/70"
        >
          Could not load existing annotations: {annotationsLoadError}
        </p>
      )}
    </div>
  );
}
