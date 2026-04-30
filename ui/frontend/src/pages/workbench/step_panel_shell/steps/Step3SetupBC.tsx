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

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { api, ApiError } from "@/api/client";
import type { AnnotationsRevisionConflictDetail } from "../types";
import type { CaseSolveRejection } from "@/types/case_solve";

import { AnnotationPanel } from "../AnnotationPanel";
import { DialogPanel } from "../DialogPanel";
import { useFacePickOptional } from "../FacePickContext";
import { useStep3State } from "../Step3StateContext";
import type {
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
  // Legacy `summary` state was set only by the removed
  // triggerSetupLegacy path (api.setupBC). Envelope-mode dispatches
  // populate `envelope.summary` instead, which the confident-success
  // banner below already shows.
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
  // Codex round-2 P1 (2026-04-30): the previous condition
  // `envelopeMode = aiMode !== null` made `?ai_mode=...` opt-in
  // semantics for the M-AI-COPILOT flow. The default URL is plain
  // `/workbench/case/:id?step=3` (no ai_mode), which dispatched the
  // LEGACY api.setupBC path that ignores face_annotations.yaml — so
  // any face the user pinned through the (now-unblocked) Step 3
  // viewport was silently discarded. Envelope mode is the production
  // M-AI-COPILOT contract; ai_mode is now strictly a debug knob to
  // FORCE the envelope into uncertain/blocked states for testing the
  // dialog UI under controlled scenarios. Natural production flow
  // always uses envelope, with no force flags.
  const envelopeMode = true;
  // Codex round-8 P1 (2026-04-30): envelope, pickedFaceIdForQuestion,
  // and activeFaceQuestionId now live in a shell-scoped Step3StateContext
  // so they survive the TaskPanel's remount when the engineer navigates
  // to another step and back. With envelope mode unconditional (round-2
  // P1), losing these on navigation forced the engineer to re-pick faces
  // and re-type labels for any in-progress uncertain dialog. Other
  // transient state (rejection, networkError, annotations) stays local
  // — annotations is re-fetched on remount, and rejection/networkError
  // are only meaningful immediately after a click.
  //
  // Map: question.id → face_id picked specifically for that question.
  // The DialogPanel reads this to gate completeness on face_label
  // questions; the resume handler reads it to assemble the
  // PUT /face-annotations payload.
  //
  // activeFaceQuestionId: explicit "active face question" — engineer
  // picks a question via the DialogPanel button, then the next viewport
  // pick routes to that specific slot.
  const {
    envelope,
    setEnvelope,
    pickedFaceIdForQuestion,
    setPickedFaceIdForQuestion,
    activeFaceQuestionId,
    setActiveFaceQuestionId,
  } = useStep3State();
  const [annotations, setAnnotations] = useState<AnnotationsDocument | null>(
    null,
  );
  const [annotationsLoadError, setAnnotationsLoadError] = useState<
    string | null
  >(null);

  // M9 Step 3 (Codex Step 1 R1 non-blocker #2 closure): clear stale
  // envelope + pick state when the engineer toggles the ai_mode
  // query param mid-session. Without this, an old uncertain envelope
  // could linger after switching to legacy mode (or vice versa),
  // confusing the engineer about which flow is active.
  //
  // M9 Step 3 R1 Finding 1 (MED): a request started under the previous
  // ai_mode could still resolve and stomp the cleared state. We bump
  // a generation token on every aiMode flip; in-flight runEnvelope
  // resolutions ignore themselves when their captured token no longer
  // matches the current one.
  const aiModeGenRef = useRef(0);
  useEffect(() => {
    aiModeGenRef.current += 1;
    setEnvelope(null);
    setPickedFaceIdForQuestion({});
    setActiveFaceQuestionId(null);
    setRejection(null);
    setNetworkError(null);
  }, [aiMode]);

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

  // Resolve which face question gets the next pick:
  //   1. If the engineer explicitly clicked "Select this face" on a
  //      question row, route to that one (activeFaceQuestionId).
  //   2. Otherwise auto-route ONLY when the envelope has exactly one
  //      face question total (single-question dogfood path · Step 1
  //      backwards-compat). Multi-question envelopes always require
  //      explicit slot selection, even after some have been answered —
  //      otherwise the engineer can be surprised by a "silent
  //      second-pick wins" once only one slot remains unresolved.
  const activeFaceQuestion = useMemo<UnresolvedQuestion | null>(() => {
    if (!envelope) return null;
    if (activeFaceQuestionId) {
      const explicit = envelope.unresolved_questions.find(
        (q) => q.id === activeFaceQuestionId && q.needs_face_selection,
      );
      if (explicit) return explicit;
      // Stale id (engineer clicked the button on a question that the
      // re-run dropped) — fall through to single-q auto-route.
    }
    const totalFaceQs = envelope.unresolved_questions.filter(
      (q) => q.needs_face_selection,
    );
    if (totalFaceQs.length === 1 && !pickedFaceIdForQuestion[totalFaceQs[0].id]) {
      return totalFaceQs[0];
    }
    return null;
  }, [envelope, activeFaceQuestionId, pickedFaceIdForQuestion]);

  // Consume picks: if there's an active dialog face question, the pick
  // routes to it (not the AnnotationPanel). Otherwise the
  // AnnotationPanel handles it via the existing flow below.
  //
  // M9 Step 3 R1 Finding 2 (LOW): when an envelope is open with
  // unresolved face questions but no slot is active (multi-q awaiting
  // explicit selection), a bare pick used to leak through into
  // AnnotationPanel — opening a separate mutation surface that
  // bypasses the dialog flow entirely. We now swallow such picks so
  // "explicit slot selection required" stays true at the UX level.
  const envelopeAwaitsFaceSelection = Boolean(
    envelope?.unresolved_questions.some((q) => q.needs_face_selection),
  );
  useEffect(() => {
    if (!facePick?.picked) return;
    if (activeFaceQuestion) {
      setPickedFaceIdForQuestion((prev) => ({
        ...prev,
        [activeFaceQuestion.id]: facePick.picked!.faceId,
      }));
      // After consuming the pick, clear the explicit active-id so the
      // next pick doesn't auto-route back to this same question (the
      // engineer should explicitly pick the next question they want
      // to answer, or use the auto-routing fallback if only one
      // face question exists in the envelope).
      setActiveFaceQuestionId(null);
      facePick.setPicked(null);
      return;
    }
    if (envelopeAwaitsFaceSelection) {
      // Envelope expects face answers via dialog — drop the stray
      // pick rather than surfacing AnnotationPanel.
      facePick.setPicked(null);
    }
  }, [facePick, activeFaceQuestion, envelopeAwaitsFaceSelection]);

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

  // Envelope-mode path (M9 Tier-B AI · M-AI-COPILOT production flow).
  // Codex round-2 (2026-04-30) made envelope the unconditional default;
  // the prior triggerSetupLegacy that called api.setupBC directly has
  // been removed because it ignored face_annotations.yaml and silently
  // discarded user pins on the natural Step 3 click. fold.useForceFlags
  // is true ONLY when the URL has an explicit ?ai_mode=force_*
  // (debug-time UI forcing); production clicks pass useForceFlags=false
  // so the executor returns the natural envelope based on whatever
  // annotations the user has already pinned.
  const runEnvelope = useCallback(
    async (fold: { useForceFlags: boolean }) => {
      setRejection(null);
      setNetworkError(null);
      // Capture the generation token at request start; if the engineer
      // flips ai_mode while this promise is in flight, the post-resolve
      // state writes are dropped (Codex M9 Step 3 R1 Finding 1).
      const generation = aiModeGenRef.current;
      const isStale = () => aiModeGenRef.current !== generation;
      try {
        const result = await api.setupBCWithEnvelope(
          caseId,
          fold.useForceFlags ? envelopeForce : {},
        );
        if (isStale()) return;
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
            if (!isStale()) setAnnotations(fresh);
          } catch {
            // Non-fatal — local state stays where it is, the
            // annotation panel re-fetches on its next 409.
          }
        }
        if (
          !isStale() &&
          result.confidence === "confident" &&
          result.unresolved_questions.length === 0
        ) {
          // Reset dialog state and complete the step. Tier-B note:
          // we don't currently fetch the post-envelope SetupBcSummary
          // (n_lid_faces / Re) — the success surface below renders a
          // simpler "✓ AI processing complete" note in envelope mode.
          // The isStale() re-check covers the case where ai_mode flipped
          // during the nested getFaceAnnotations() await above (Codex
          // M9 Step 3 R2 finding).
          setPickedFaceIdForQuestion({});
          onStepComplete();
        }
      } catch (e) {
        if (isStale()) {
          // Drop late errors from the previous ai_mode — surfacing
          // them now would be misleading to the engineer who already
          // moved on to a different flow.
          return;
        }
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
      // Codex round-4 P2 (2026-04-30): if facesToWrite is non-empty
      // but annotations hasn't loaded yet, the PUT was previously
      // skipped silently. Now that envelope is the default Step 3
      // path, that race silently dropped the user's lid pin →
      // re-running envelope returned the same uncertain question
      // and the user thought they'd answered. Block the resume here
      // with an actionable error so the user retries (annotations
      // are usually loaded within ~50 ms of step entry).
      if (facesToWrite.length > 0 && !annotations) {
        throw new Error(
          "Face annotations not ready yet — please wait a moment and click [继续 AI 处理] again.",
        );
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

  // useForceFlags=true ONLY when an explicit ?ai_mode is set
  // (debug-time forcing of uncertain/blocked envelopes); the natural
  // production click is useForceFlags=false so the executor returns
  // the actual envelope based on existing face_annotations.yaml.
  const triggerSetup = () =>
    runEnvelope({ useForceFlags: aiMode !== null });

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

      {!envelope && !rejection && !networkError && (
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
          activeFaceQuestionId={activeFaceQuestionId}
          onSelectActiveFaceQuestion={setActiveFaceQuestionId}
          onResume={handleDialogResume}
        />
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
