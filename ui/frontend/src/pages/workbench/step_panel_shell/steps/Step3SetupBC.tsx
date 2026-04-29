// Step 3 · Setup BC — wired in Phase-1A (DEC-V61-097), extended in
// M-AI-COPILOT Tier-A (DEC-V61-098) with face-annotation pinning,
// and again in M9 Tier-B AI (this revision) with envelope-mode
// dialog flow.
//
// LDC-only scope: the gmsh pipeline produces a mesh of the STL interior,
// which is correct as a flow domain ONLY for closed-cavity geometries
// (the ldc_box demo). For external-flow demos (cylinder, naca0012)
// the mesh is the obstacle interior — useless for CFD; that requires
// a separate blockMesh+sHM pipeline (Phase-2 / Phase-3 milestones).
//
// Two operating modes:
//   1. Legacy (default): POST /setup-bc returns SetupBcSummary; we show
//      lid/wall counts + Re. This is the LDC dogfood path Phase-1A built.
//   2. Envelope mode (?ai_mode=force_uncertain | force_blocked):
//      POST /setup-bc?envelope=1&force_uncertain=1 returns
//      AIActionEnvelope. When confidence is uncertain/blocked, we
//      render the DialogPanel and the engineer answers questions
//      (often by picking faces in the viewport). [继续 AI 处理] then
//      saves answers as user_authoritative annotations and re-runs
//      envelope mode. Once confident, the step completes.
//
// Tier-B AI fully wires only when the backend ships a real
// arbitrary-STL classifier (deferred); the force_uncertain flag is
// the dogfood substrate for testing the dialog UX in the meantime.

import { useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { api, ApiError } from "@/api/client";
import type { AnnotationsRevisionConflictDetail } from "../types";
import type {
  CaseSolveRejection,
  SetupBcSummary,
} from "@/types/case_solve";

import { AnnotationPanel } from "../AnnotationPanel";
import { DialogPanel } from "../DialogPanel";
import { useFacePickOptional } from "../FacePickContext";
import type {
  AIActionEnvelope,
  AnnotationsDocument,
  FaceAnnotation,
  StepTaskPanelProps,
  UnresolvedQuestion,
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
  const [searchParams] = useSearchParams();
  const aiMode = searchParams.get("ai_mode") ?? null;
  const envelopeForce: { forceUncertain?: boolean; forceBlocked?: boolean } =
    useMemo(() => {
      if (aiMode === "force_uncertain") return { forceUncertain: true };
      if (aiMode === "force_blocked") return { forceBlocked: true };
      return {};
    }, [aiMode]);
  const envelopeMode = aiMode !== null;
  const [envelope, setEnvelope] = useState<AIActionEnvelope | null>(null);
  // Map: question.id → face_id picked specifically for that question.
  // The DialogPanel reads this to gate completeness on face_label
  // questions; the resume handler reads it to assemble the
  // PUT /face-annotations payload.
  const [pickedFaceIdForQuestion, setPickedFaceIdForQuestion] = useState<
    Record<string, string>
  >({});
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

  // First unresolved face-selection question awaiting an answer (used
  // to route the engineer's pick to the right question slot).
  const activeFaceQuestion = useMemo<UnresolvedQuestion | null>(() => {
    if (!envelope) return null;
    return (
      envelope.unresolved_questions.find(
        (q) => q.needs_face_selection && !pickedFaceIdForQuestion[q.id],
      ) ?? null
    );
  }, [envelope, pickedFaceIdForQuestion]);

  // Consume picks: if there's an active dialog face question, the pick
  // routes to it (not the AnnotationPanel). Otherwise the
  // AnnotationPanel handles it via the existing flow below.
  useEffect(() => {
    if (!facePick?.picked || !activeFaceQuestion) return;
    setPickedFaceIdForQuestion((prev) => ({
      ...prev,
      [activeFaceQuestion.id]: facePick.picked!.faceId,
    }));
    facePick.setPicked(null);
  }, [facePick, activeFaceQuestion]);

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
      try {
        const updated = await api.putFaceAnnotations(caseId, {
          if_match_revision: annotations.revision,
          faces: [patch],
          annotated_by: "human",
        });
        setAnnotations(updated);
        facePick?.setPicked(null);
      } catch (e) {
        // Codex Step 7b round 1 HIGH: a 409 revision_conflict
        // (concurrent AI write or second client) used to leave the
        // panel stuck on the stale revision forever — every retry
        // re-sent the same `if_match_revision` and re-failed. We now
        // re-fetch the latest annotations doc on 409 so the user can
        // retry with the bumped revision; the AnnotationPanel keeps
        // its draft inputs intact (it only resets on faceId change).
        // sticky invariant is preserved (annotated_by stays 'human').
        if (
          e instanceof ApiError &&
          e.status === 409 &&
          e.detail &&
          typeof e.detail === "object" &&
          "failing_check" in e.detail
        ) {
          const conflict = e.detail as AnnotationsRevisionConflictDetail;
          try {
            const fresh = await api.getFaceAnnotations(caseId);
            setAnnotations(fresh);
            throw new Error(
              `Revision conflict (was ${conflict.attempted_revision}, ` +
                `latest ${fresh.revision}). Refreshed — please retry.`,
            );
          } catch (refetchErr) {
            // If even the refetch fails, surface a useful error so
            // the AnnotationPanel still tells the user something
            // actionable.
            if (refetchErr instanceof Error) throw refetchErr;
            throw new Error(
              `Revision conflict (was ${conflict.attempted_revision}, ` +
                `latest ${conflict.current_revision}). ` +
                `Refresh failed: ${String(refetchErr)}.`,
            );
          }
        }
        throw e;
      }
    },
    [annotations, caseId, facePick],
  );

  const handleCancelPick = useCallback(() => {
    facePick?.setPicked(null);
  }, [facePick]);

  // Legacy non-envelope path. Used when ?ai_mode is unset.
  const triggerSetupLegacy = useCallback(async () => {
    setRejection(null);
    setNetworkError(null);
    try {
      const r = await api.setupBC(caseId);
      setSummary(r);
      setEnvelope(null);
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

  // Envelope-mode path (M9 Tier-B AI). Used when ?ai_mode=force_uncertain
  // or ?ai_mode=force_blocked is set, and on every [继续 AI 处理]
  // resume click. The fold parameter controls force flags so the
  // resume call doesn't re-force uncertainty after the user answered.
  const runEnvelope = useCallback(
    async (fold: { useForceFlags: boolean }) => {
      setRejection(null);
      setNetworkError(null);
      try {
        const result = await api.setupBCWithEnvelope(
          caseId,
          fold.useForceFlags ? envelopeForce : {},
        );
        setEnvelope(result);
        // Refresh annotations whenever the envelope reports the doc
        // bumped server-side (e.g., the action wrapper merged AI
        // confident classifications).
        if (
          annotations &&
          result.annotations_revision_after !== annotations.revision
        ) {
          try {
            const fresh = await api.getFaceAnnotations(caseId);
            setAnnotations(fresh);
          } catch {
            // Non-fatal — local state stays where it is, the
            // annotation panel re-fetches on its next 409.
          }
        }
        if (
          result.confidence === "confident" &&
          result.unresolved_questions.length === 0
        ) {
          // Reset dialog state and complete the step. Tier-B note:
          // we don't currently fetch the post-envelope SetupBcSummary
          // (n_lid_faces / Re) — the success surface below renders a
          // simpler "✓ AI processing complete" note in envelope mode.
          setPickedFaceIdForQuestion({});
          onStepComplete();
        }
      } catch (e) {
        if (
          e instanceof ApiError &&
          e.detail &&
          typeof e.detail === "object" &&
          "failing_check" in e.detail
        ) {
          const detail = e.detail as CaseSolveRejection;
          setRejection(detail);
          onStepError(`setup-bc envelope rejected: ${detail.failing_check}`);
        } else {
          const msg = e instanceof Error ? e.message : String(e);
          setNetworkError(msg);
          onStepError(msg);
        }
        throw e;
      }
    },
    [caseId, envelopeForce, annotations, onStepComplete, onStepError],
  );

  const handleDialogResume = useCallback(
    async (answers: Record<string, string>) => {
      if (!envelope) return;
      // For face-selection questions: persist the picked face_id with
      // the engineer's label as a user_authoritative annotation. The
      // DialogPanel composes "<face_id>:<label>" when both are
      // present, or just "<face_id>" otherwise. Parse that back here.
      const facesToWrite: FaceAnnotation[] = [];
      for (const q of envelope.unresolved_questions) {
        if (!q.needs_face_selection) continue;
        const composed = answers[q.id];
        if (!composed) continue;
        const [faceId, label] = composed.split(":");
        if (!faceId) continue;
        facesToWrite.push({
          face_id: faceId,
          name: label || q.id,
          confidence: "user_authoritative",
        });
      }
      if (facesToWrite.length > 0 && annotations) {
        try {
          const updated = await api.putFaceAnnotations(caseId, {
            if_match_revision: annotations.revision,
            faces: facesToWrite,
            annotated_by: "human",
          });
          setAnnotations(updated);
        } catch (e) {
          if (e instanceof ApiError && e.status === 409) {
            // Resync and abort the resume; the engineer can click
            // [继续 AI 处理] again. We surface the conflict via the
            // envelope's error_detail to keep the UI on the dialog
            // path.
            try {
              const fresh = await api.getFaceAnnotations(caseId);
              setAnnotations(fresh);
            } catch {
              // best-effort
            }
            throw new Error(
              "Annotations changed mid-dialog. Refreshed — please retry.",
            );
          }
          throw e;
        }
      }
      // Re-run envelope mode WITHOUT force flags. The action wrapper
      // re-reads the (now-updated) face_annotations.yaml and ideally
      // returns confident.
      await runEnvelope({ useForceFlags: false });
    },
    [annotations, caseId, envelope, runEnvelope],
  );

  const triggerSetup = envelopeMode
    ? () => runEnvelope({ useForceFlags: true })
    : triggerSetupLegacy;

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

      {envelopeMode && (
        <div
          data-testid="step3-envelope-mode-banner"
          className="rounded-sm border border-amber-500/40 bg-amber-500/10 px-2 py-1 text-[10px] font-mono text-amber-200"
        >
          AI-COPILOT envelope mode (ai_mode={aiMode}). The dialog panel
          will surface below when the AI returns uncertain or blocked.
        </div>
      )}

      {!summary && !envelope && !rejection && !networkError && (
        <p className="rounded-sm border border-surface-800 bg-surface-900/40 px-2 py-1 text-[11px] text-surface-400">
          Click <strong className="text-surface-200">[AI 处理]</strong> below
          to split the mesh into lid + walls and write BC dicts.
        </p>
      )}

      {envelope &&
        envelope.confidence === "confident" &&
        envelope.unresolved_questions.length === 0 && (
          <div
            data-testid="step3-envelope-success"
            className="rounded-sm border border-emerald-700/40 bg-emerald-900/10 p-2"
          >
            <div className="font-mono text-[11px] text-emerald-200">
              ✓ AI processing complete (envelope mode)
            </div>
            <p className="mt-1 text-[10px] text-surface-400">{envelope.summary}</p>
            {envelope.next_step_suggestion && (
              <p className="mt-1 text-[10px] text-surface-500">
                {envelope.next_step_suggestion}
              </p>
            )}
          </div>
        )}

      {envelope && envelope.unresolved_questions.length > 0 && (
        <DialogPanel
          envelope={envelope}
          pickedFaceIdForQuestion={pickedFaceIdForQuestion}
          onResume={handleDialogResume}
        />
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
