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
import { MaterialCard } from "../MaterialCard";
import { PatchClassificationPanel } from "../PatchClassificationPanel";
import { RawDictEditor } from "@/components/RawDictEditor";

// DEC-V61-102 M-RESCUE Phase 2 · Step 3 raw-dict footprint. These are
// the OpenFOAM dicts setup_ldc_bc / setup_channel_bc author. 0/* paths
// are intentionally excluded from the allowlist (face_id-coupled —
// editing them silently breaks the patch invariant).
const STEP3_RAW_DICT_PATHS = [
  "system/controlDict",
  "system/fvSchemes",
  "system/fvSolution",
  "constant/momentumTransport",
  "constant/physicalProperties",
] as const;
import { useFacePickOptional } from "../FacePickContext";
import { PowerDisclosure } from "../PowerDisclosure";
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
  // DEC-V61-131 N1.1: confident envelope is advisory-only; this state
  // tracks the engineer's [应用 AI 建议] confirm click which calls the
  // legacy non-envelope api.setupBC to actually mutate the case.
  const [applying, setApplying] = useState(false);
  const [appliedSummary, setAppliedSummary] = useState<string | null>(null);
  const [applyError, setApplyError] = useState<string | null>(null);
  // DEC-V61-102 Phase 2 raw-dict editor mount gate.
  //
  // Codex Phase-2 P2 closure: track whether the disclosure has been
  // opened AT LEAST ONCE rather than whether it is open RIGHT NOW.
  // After the first open, the editor stays mounted so closing the
  // <details> hides it via CSS rather than unmounting the component.
  //
  // Note: cross-step navigation (Step 3 → Step 2 → Step 3) DOES
  // unmount this whole panel and reset rawDictHasOpened. Buffer
  // continuity across that boundary is handled inside RawDictEditor
  // via sessionStorage persistence (Codex round-2 MED closure), so
  // the user's unsaved content survives even when the parent unmounts.
  const [rawDictHasOpened, setRawDictHasOpened] = useState(false);

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
  // Codex f7f6476 round-3 P2: surface a visible banner when a
  // segment fan-out had to skip outlier siblings, instead of a
  // hidden console.warn the user will never see in normal browser
  // use. Cleared on next pick (so the warning is transient — it
  // describes the previous save).
  const [segmentPartialSaveWarning, setSegmentPartialSaveWarning] =
    useState<string | null>(null);

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
  //
  // Codex round-9 P1 (2026-04-30): now that envelope/pickedFaceIdForQuestion/
  // activeFaceQuestionId live in a shell-scoped Step3StateContext, this
  // effect must NOT fire on every Step3SetupBC mount — TaskPanel
  // remounts the body on step navigation, so resetting unconditionally
  // would re-wipe the lifted state and re-introduce the round-8 P1
  // regression. We skip the very first effect run (the natural mount)
  // and only reset on subsequent runs (an actual aiMode change while
  // the component is alive). aiModeGenRef still bumps on a real
  // change so any in-flight envelope from the previous mode gets
  // dropped on resolve.
  const aiModeGenRef = useRef(0);
  const aiModeFirstRunRef = useRef(true);
  useEffect(() => {
    if (aiModeFirstRunRef.current) {
      aiModeFirstRunRef.current = false;
      return;
    }
    aiModeGenRef.current += 1;
    setEnvelope(null);
    setPickedFaceIdForQuestion({});
    setActiveFaceQuestionId(null);
    setRejection(null);
    setNetworkError(null);
  }, [aiMode, setEnvelope, setPickedFaceIdForQuestion, setActiveFaceQuestionId]);

  // Codex round-11 P1 (2026-04-30): with envelope state lifted into
  // shell-scoped Step3StateContext, an in-flight setupBCWithEnvelope()
  // for case A can outlive the Step3SetupBC instance — and when it
  // resolves it would call setEnvelope() through the (still-alive)
  // shell context, stomping case B's freshly-reset state with case
  // A's dialog. From there [继续 AI 处理] would write annotations to
  // the wrong case. Two complementary guards:
  //   1. cancelledRef: flipped true on unmount cleanup, so a request
  //      whose Step3SetupBC instance is gone aborts its post-resolve
  //      writes.
  //   2. currentCaseIdRef: tracks the latest caseId across re-renders
  //      of the SAME instance (React Router updates :caseId in place
  //      without remounting the route element). runEnvelope captures
  //      the requestCaseId at start and compares it to the ref at
  //      resolve time.
  const cancelledRef = useRef(false);
  const currentCaseIdRef = useRef(caseId);
  useEffect(() => {
    currentCaseIdRef.current = caseId;
  }, [caseId]);
  useEffect(() => {
    cancelledRef.current = false;
    return () => {
      cancelledRef.current = true;
    };
  }, []);

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
  // Codex round-3 P2 closure: a new pick supersedes the previous
  // partial-save warning. The banner stays until the next pick OR
  // explicit dismiss, so the engineer has time to see + read it
  // even if the panel itself dismissed.
  useEffect(() => {
    if (facePick?.picked) {
      setSegmentPartialSaveWarning(null);
    }
  }, [facePick?.picked?.faceId]);

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
    // Dogfood feedback 2026-04-30: previously the M9 R1 Finding 2
    // (LOW) closure swallowed bare picks whenever the envelope had
    // any unresolved face question, on the theory that AnnotationPanel
    // would "open a separate mutation surface that bypasses the dialog
    // flow." But that left the engineer with no way to set BCs after
    // the highlight landed — the panel never surfaced.
    //
    // Now both surfaces coexist:
    //   - With NO active dialog question: bare picks surface
    //     AnnotationPanel below, the engineer can free-annotate.
    //   - With an active dialog question (the engineer clicked
    //     "Select this face" on a specific row): picks route into
    //     that question's slot (handled above) — the AnnotationPanel
    //     does NOT surface for that pick.
    // The two paths can't conflict on the same pick because the
    // active-question branch above clears facePick.picked before
    // any AnnotationPanel render observes it.
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
      // Codex e844a6f review P1: when the picked highlight covers
      // multiple face_ids (curved patch on a gmsh tet mesh), fan
      // the annotation out across every face_id in the segment so
      // the saved state matches the visual highlight. For axis-
      // aligned cube faces this collapses to length 1 and the
      // request is identical to the pre-fix shape.
      //
      // Codex rounds 2-4 closure: classify each sibling as "safe
      // to overwrite" or "outlier to preserve":
      //   - Sibling unannotated → always safe (empty slots get
      //     filled by the fan-out, including the partially-
      //     annotated-segment recovery path Codex round-4 raised).
      //   - Sibling annotated identically to the picked face's
      //     pre-edit state → safe (uniform segments fan out
      //     correctly, e.g. all-wall → inlet bulk rename).
      //   - Sibling annotated differently from the picked face's
      //     pre-edit state → outlier, leave intact. The user can
      //     click that sibling individually to edit it.
      // Earlier rounds compared against the new form values
      // (round 2, broke bulk renames) or required strict equality
      // including unannotated mismatches (round 3, broke partial-
      // segment recovery).
      const segmentFaceIds =
        facePick?.picked?.faceIds && facePick.picked.faceIds.length > 0
          ? facePick.picked.faceIds
          : [patch.face_id];
      const annotationByFaceId = new Map<string, FaceAnnotation>();
      for (const f of annotations.faces) {
        annotationByFaceId.set(f.face_id, f);
      }
      const pickedExisting = annotationByFaceId.get(patch.face_id);
      // Codex 86gs N1.1 R12 P2 close: normalize the new-encoding
      // (patch_type=undefined, post-R11 untouched-default save) and
      // legacy-encoding (patch_type="wall", pre-R11 untouched
      // default) as the same semantic state for sibling-comparison
      // purposes. Without this, a multi-face segment that mixed
      // both shapes would misclassify identical siblings as outliers
      // and only update part of the segment after the upgrade.
      const normalizePatchType = (
        v: FaceAnnotation["patch_type"] | undefined,
      ): string | undefined =>
        v === undefined || v === null || v === "wall" ? undefined : v;
      const isSafeSibling = (
        existing: FaceAnnotation | undefined,
      ): boolean => {
        // Unannotated sibling → safe to fill.
        if (existing === undefined) return true;
        // Annotated sibling, but picked face has no prior
        // annotation → user is starting from a blank slate;
        // preserve any pre-existing sibling annotation.
        if (pickedExisting === undefined) return false;
        // Both annotated → safe iff sibling matches picked.
        return (
          existing.name === pickedExisting.name &&
          normalizePatchType(existing.patch_type) ===
            normalizePatchType(pickedExisting.patch_type) &&
          (existing.physics_notes ?? undefined) ===
            (pickedExisting.physics_notes ?? undefined)
        );
      };
      const facesToWrite: FaceAnnotation[] = [];
      const skippedFaceIds: string[] = [];
      for (const fid of segmentFaceIds) {
        const isPrimary = fid === patch.face_id;
        if (isPrimary) {
          facesToWrite.push({ ...patch, face_id: fid });
          continue;
        }
        const existing = annotationByFaceId.get(fid);
        if (!isSafeSibling(existing)) {
          skippedFaceIds.push(fid);
          continue;
        }
        facesToWrite.push({ ...patch, face_id: fid });
      }
      try {
        const updated = await api.putFaceAnnotations(caseId, {
          if_match_revision: annotations.revision,
          faces: facesToWrite,
          annotated_by: "human",
        });
        setAnnotations(updated);
        // Codex round-3 P2 closure: surface a visible banner when
        // a fan-out had to skip outlier siblings, so the engineer
        // sees that the saved BC state diverges from the visual
        // highlight (rather than silently committing a partial
        // write and dismissing the panel). The banner clears on
        // the next pick.
        if (skippedFaceIds.length > 0) {
          setSegmentPartialSaveWarning(
            `Saved annotation to ${facesToWrite.length} of ${
              segmentFaceIds.length
            } face(s) in the highlighted segment. ` +
              `${skippedFaceIds.length} sibling face(s) had different existing annotations and were left unchanged — ` +
              `click each one individually to review or edit.`,
          );
        } else {
          setSegmentPartialSaveWarning(null);
        }
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
      // Capture the generation token + caseId at request start. The
      // post-resolve writes are dropped if either:
      //   - the engineer flipped ai_mode while we were in flight
      //     (Codex M9 Step 3 R1 Finding 1), OR
      //   - the engineer switched cases mid-flight, EITHER by
      //     unmounting Step3SetupBC entirely (cancelledRef) or by
      //     re-rendering the same instance with a new caseId
      //     (currentCaseIdRef differs from requestCaseId; Codex
      //     round-11 P1).
      const generation = aiModeGenRef.current;
      const requestCaseId = caseId;
      const isStale = () =>
        cancelledRef.current ||
        aiModeGenRef.current !== generation ||
        currentCaseIdRef.current !== requestCaseId;
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
          // DEC-V61-131 N1.1: confident envelope is advisory-only —
          // the backend hard-strip removed setup_ldc_bc /
          // setup_channel_bc invocations from envelope mode. The step
          // does NOT auto-complete; the engineer must click
          // [应用 AI 建议] to call legacy api.setupBC and apply.
          // Reset stale dialog state but stay on this step.
          setPickedFaceIdForQuestion({});
          setAppliedSummary(null);
          setApplyError(null);
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
      // DEC-V61-131 N1.1 R7: collect stale_face_ids from any answered
      // question carrying them so the PUT can purge the legacy entry
      // alongside the replacement pick — required for the stale-pin
      // recovery flow to converge (PUT only merges by face_id, so
      // without the explicit removal the stale entry stays on disk
      // and the next classifier run sees the same stale state).
      const facesToWrite: FaceAnnotation[] = [];
      const removeFaceIds: string[] = [];
      // DEC-V61-131 N1.1 R8 P2#2 close (Codex R7): when replacing a
      // stale pin, carry the engineer's previously-entered metadata
      // (patch_type / physics_notes) forward onto the replacement.
      // Without this, a remesh-then-recover cycle silently wipes
      // engineer annotations beyond name/confidence.
      const annotationByFaceId = new Map<string, FaceAnnotation>();
      if (annotations) {
        for (const f of annotations.faces) {
          annotationByFaceId.set(f.face_id, f);
        }
      }
      for (const q of envelope.unresolved_questions) {
        if (!q.needs_face_selection) continue;
        const composed = answers[q.id];
        if (!composed) continue;
        const [faceId, label] = composed.split(":");
        if (!faceId) continue;
        // Codex R8 P2#2 + R9 + R10 + R11 + R12 close: carry forward
        // stale-face metadata onto the replacement only when the
        // replacement face has NO unambiguously explicit value.
        // We use the R12 patch_type_explicit marker plus a
        // legacy-aware fallback to discriminate sources:
        //   * existing.patch_type_explicit === true → post-R12
        //     explicit pick (engineer or AI classifier). Preserve,
        //     including an explicit "wall".
        //   * existing.patch_type set, no marker, value !== "wall"
        //     → legacy pre-R12 explicit pick (the dropdown's
        //     default at write-time WAS "wall", so anything else
        //     could only have come from an explicit selection).
        //     Preserve.
        //   * existing.patch_type === "wall", no marker → legacy
        //     ambiguous (could be untouched default or explicit
        //     wall). Treat as ambiguous; if stale has a meaningful
        //     non-wall role, inherit it (the recovery semantic
        //     "replacement inherits stale's BC role" wins).
        //   * existing.patch_type undefined/null → no opinion yet;
        //     carry stale unconditionally.
        // This is unambiguous post-R12 (marker resolves) and the
        // only residual ambiguity is legacy "wall" vs stale-non-
        // wall — where the recovery semantic favors stale.
        let carryPatchType: FaceAnnotation["patch_type"] | undefined;
        let carryPhysicsNotes: FaceAnnotation["physics_notes"] | undefined;
        if (q.stale_face_ids && q.stale_face_ids.length === 1) {
          const stale = annotationByFaceId.get(q.stale_face_ids[0]);
          const existingReplacement = annotationByFaceId.get(faceId);
          if (stale) {
            const existingPatchType = existingReplacement?.patch_type;
            const existingHasExplicitMarker =
              existingReplacement?.patch_type_explicit === true;
            const existingPatchTypeIsSet =
              existingPatchType !== undefined && existingPatchType !== null;
            const staleHasMeaningfulRole =
              stale.patch_type !== undefined &&
              stale.patch_type !== null &&
              stale.patch_type !== "wall";
            if (!existingPatchTypeIsSet) {
              // No opinion → carry stale freely.
              carryPatchType = stale.patch_type;
            } else if (
              !existingHasExplicitMarker &&
              existingPatchType === "wall" &&
              staleHasMeaningfulRole
            ) {
              // Legacy "wall" + stale has a real role → inherit
              // stale's role. This is the only residual ambiguity
              // from the pre-R12 data shape; we resolve it in
              // favor of the recovery semantic.
              carryPatchType = stale.patch_type;
            }
            // else: explicit marker present, OR legacy non-wall
            // (which was unambiguously explicit pre-R12 because
            // "wall" was the only default), OR stale has no
            // meaningful role → preserve existing as-is.
            if (
              !existingReplacement ||
              existingReplacement.physics_notes === undefined ||
              existingReplacement.physics_notes === null
            ) {
              carryPhysicsNotes = stale.physics_notes;
            }
          }
        }
        const replacement: FaceAnnotation = {
          face_id: faceId,
          name: label || q.id,
          confidence: "user_authoritative",
        };
        if (carryPatchType !== undefined) {
          replacement.patch_type = carryPatchType;
          // The engineer's click on [继续 AI 处理] after the
          // replacement pick implicitly accepts stale's BC role for
          // the replacement face — mark the resulting annotation
          // explicit so a future resume run never treats it as
          // legacy-ambiguous (Codex 86gs N1.1 R12).
          replacement.patch_type_explicit = true;
        }
        if (carryPhysicsNotes !== undefined) {
          replacement.physics_notes = carryPhysicsNotes;
        }
        facesToWrite.push(replacement);
        if (q.stale_face_ids && q.stale_face_ids.length > 0) {
          for (const stale of q.stale_face_ids) {
            removeFaceIds.push(stale);
          }
        }
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
            remove_face_ids:
              removeFaceIds.length > 0 ? removeFaceIds : undefined,
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

  // DEC-V61-131 N1.1: [应用 AI 建议] confirm button. The advisory
  // envelope tells the engineer what AI suggests; this click calls
  // the legacy non-envelope POST /setup-bc to actually write the
  // dicts. Only renders when the envelope is confident. The legacy
  // route auto-dispatches LDC vs channel by classifier so the
  // confident-channel path applies correctly (Codex N1.1 R0 P1).
  //
  // Stale-guard mirrors runEnvelope (Codex N1.1 R0 P2#1): a click
  // that resolves after the engineer switched cases (cancelledRef OR
  // currentCaseIdRef differs) must NOT mutate the new instance's
  // state — which would otherwise mis-mark the new case complete or
  // surface the previous case's apply summary.
  const handleApplySuggestion = useCallback(async () => {
    if (applying) return;
    setApplying(true);
    setApplyError(null);
    setRejection(null);
    setNetworkError(null);
    const requestCaseId = caseId;
    const isStale = () =>
      cancelledRef.current ||
      currentCaseIdRef.current !== requestCaseId;
    try {
      // DEC-V61-131 N1.1 R2 (Codex R1 P1+P2 close): bind apply to
      // the AI advisory's geometry class + annotations revision so
      // a stale-pin channel surfaces as recoverable
      // channel_pin_mismatch and a concurrent annotations edit
      // surfaces as 409 annotations_revision_conflict (instead of
      // applying to a different face set than the engineer accepted).
      const bcKind =
        envelope?.suggested_bc_kind === "channel" ||
        envelope?.suggested_bc_kind === "ldc"
          ? envelope.suggested_bc_kind
          : undefined;
      const ifMatch = envelope?.annotations_revision_consumed;
      const summary = await api.setupBC(caseId, {
        bcKind,
        ifMatchRevision: ifMatch,
      });
      if (isStale()) return;
      const inletPart =
        summary.bc_kind === "channel"
          ? `inlet=${summary.n_inlet_faces ?? "—"} outlet=${
              summary.n_outlet_faces ?? "—"
            }`
          : `lid=${summary.n_lid_faces ?? "—"}`;
      setAppliedSummary(
        `Applied (${summary.bc_kind ?? "ldc"}): ${inletPart} walls=${
          summary.n_wall_faces ?? "—"
        } Re=${summary.reynolds ?? "—"}`,
      );
      onStepComplete();
    } catch (e) {
      if (isStale()) return;
      if (
        e instanceof ApiError &&
        e.detail &&
        typeof e.detail === "object" &&
        "failing_check" in e.detail
      ) {
        const detail = e.detail as CaseSolveRejection & {
          unresolved_questions?: UnresolvedQuestion[];
        };
        // DEC-V61-131 N1.1 R3 P1 close (Codex 86gs R3): on stale-pin
        // or revision-conflict, the right recovery is to RE-RUN the
        // AI envelope from scratch, NOT to synthesize an uncertain
        // envelope from the apply route's classifier questions —
        // those questions can be free_text/needs_face_selection=false
        // (channel_pin_mismatch surface), which means the dialog
        // would reopen as a textarea, handleDialogResume would not
        // persist any face annotation, and the next [继续 AI 处理]
        // re-runs the envelope with unchanged annotations and gets
        // the same rejection — an infinite loop. Re-running envelope
        // returns proper face-selection questions through the
        // classifier's natural uncertain path.
        if (
          detail.failing_check === "channel_pin_mismatch" ||
          detail.failing_check === "annotations_revision_conflict" ||
          detail.failing_check === "ldc_mismatch"
        ) {
          // DEC-V61-131 R20 P2 close (CRS R0 finding): ldc_mismatch is
          // the symmetric guard added in R19 — engineer accepted an LDC
          // advisory but the geometry/classifier now reports
          // confident-channel before apply. The right recovery is
          // identical to channel_pin_mismatch / annotations_revision_conflict:
          // wipe the stale confident-LDC card and re-run the envelope
          // so the engineer gets the new face-selection questions
          // through the classifier's natural uncertain path. Without
          // this entry the frontend renders ldc_mismatch as a terminal
          // banner and the engineer is stuck on a stale card with no
          // path forward except a manual page refresh.
          //
          // DEC-V61-131 R21 P3 close (CRS R20 finding): do NOT call
          // onStepError() on the auto-recovery branch. onStepError
          // flips Step 3 to the persistent 'error' state in
          // StepPanelShell and shows the global AI error banner
          // until some later successful apply clears it. For these
          // three rejection codes the panel auto-refreshes the
          // envelope, so the engineer should see the new
          // dialog/advisory loading, NOT a red failed step. The
          // pre-R21 onStepError call was inherited boilerplate from
          // the non-recovering branch — it was wrong for
          // channel_pin_mismatch and annotations_revision_conflict
          // too, but R20 is what surfaced the inconsistency by
          // adding ldc_mismatch (CRS framing: "this commit newly
          // introduces inconsistent shell state for ldc_mismatch
          // cases"). Removing onStepError from all three keeps the
          // recovery path symmetric and bug-free.
          setEnvelope(null);
          setPickedFaceIdForQuestion({});
          setActiveFaceQuestionId(null);
          // Re-run envelope on a microtask so React processes the
          // state resets above before the new envelope arrives. The
          // refreshed envelope reads the (possibly updated)
          // annotations.yaml and surfaces the right
          // face-selection questions — recoverable without an
          // infinite loop.
          void runEnvelope({ useForceFlags: false });
        } else {
          setRejection(detail);
          onStepError(
            `apply suggestion rejected: ${detail.failing_check}`,
          );
        }
      } else {
        const msg = e instanceof Error ? e.message : String(e);
        setApplyError(msg);
        onStepError(msg);
      }
    } finally {
      if (!cancelledRef.current) setApplying(false);
    }
  }, [
    applying,
    caseId,
    envelope,
    onStepComplete,
    onStepError,
    runEnvelope,
    setActiveFaceQuestionId,
    setEnvelope,
    setPickedFaceIdForQuestion,
  ]);

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

      {/* V68-C.1 · MaterialCard · read-only display of the case's
       *  committed physics state (constant/physicalProperties +
       *  constant/momentumTransport). Surfaces immediately on Step 3
       *  entry so the engineer sees the current state before deciding
       *  whether to re-commit via PhysicsPanel below. */}
      <MaterialCard caseId={caseId} />

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
            className="space-y-2 rounded-sm border border-emerald-700/40 bg-emerald-900/10 p-2"
          >
            <div className="font-mono text-[11px] text-emerald-200">
              {appliedSummary
                ? "✓ Applied"
                : "AI suggests (advisory · click to apply)"}
            </div>
            <p className="text-[10px] text-surface-400">{envelope.summary}</p>
            {envelope.next_step_suggestion && !appliedSummary && (
              <p className="text-[10px] text-surface-500">
                {envelope.next_step_suggestion}
              </p>
            )}
            {appliedSummary ? (
              <p
                data-testid="step3-apply-summary"
                className="text-[10px] text-emerald-300/80"
              >
                {appliedSummary}
              </p>
            ) : (
              <button
                type="button"
                data-testid="step3-apply-suggestion-btn"
                disabled={applying}
                onClick={handleApplySuggestion}
                className="rounded-sm border border-emerald-500/60 bg-emerald-700/40 px-2 py-1 text-[11px] font-mono text-emerald-100 hover:bg-emerald-700/60 disabled:opacity-50"
              >
                {applying ? "应用中..." : "[应用 AI 建议]"}
              </button>
            )}
            {applyError && (
              <p
                data-testid="step3-apply-error"
                className="text-[10px] text-rose-300"
              >
                Apply failed: {applyError}
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

      {segmentPartialSaveWarning && (
        <div
          data-testid="step3-segment-partial-save-warning"
          className="flex items-start justify-between gap-2 rounded-sm border border-amber-700/50 bg-amber-900/15 px-2 py-1 text-[11px] text-amber-200"
        >
          <span>{segmentPartialSaveWarning}</span>
          <button
            type="button"
            onClick={() => setSegmentPartialSaveWarning(null)}
            className="text-[10px] uppercase tracking-wider text-amber-300 hover:text-amber-100"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* DEC-V61-108 Phase B · per-patch BC classification override.
       *  Always mounted on Step 3 (not gated on a pick) so the engineer
       *  can scan all patches at a glance and override any of them.
       *  Picked-face highlighting is purely a hint — the panel works
       *  without a pick. ``key={caseId}`` forces a full remount when
       *  React Router swaps caseId in place — Codex DEC-V61-108
       *  Phase B R1 P1 #2 closure. */}
      {caseId && (
        <PatchClassificationPanel
          key={caseId}
          caseId={caseId}
          pickedFaceId={facePick?.picked?.faceId ?? null}
        />
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
          faceIdCount={facePick.picked.faceIds.length}
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

      {/* DEC-V61-102 M-RESCUE Phase 2 · raw dict editor. Collapsed by
       *  default; lazily mounted on first expand so existing Step 3
       *  tests (which don't wrap in QueryClientProvider) stay green.
       *  Once mounted, stays mounted — collapsing the disclosure hides
       *  it via CSS but preserves unsaved edits (Codex P2 closure). */}
      <details
        data-testid="step3-raw-dict-editor"
        className="mt-3 rounded-sm border border-slate-700/50 bg-slate-900/30"
        onToggle={(e) => {
          if ((e.target as HTMLDetailsElement).open) {
            setRawDictHasOpened(true);
          }
        }}
      >
        <summary className="cursor-pointer px-2 py-1 text-[11px] uppercase tracking-wider text-slate-300 hover:text-slate-100">
          Advanced · edit raw dicts (manual override)
        </summary>
        <div className="px-2 py-2">
          {!caseId ? (
            <p className="text-[11px] text-slate-400">Open a case first.</p>
          ) : rawDictHasOpened ? (
            <RawDictEditor
              caseId={caseId}
              allowedPaths={STEP3_RAW_DICT_PATHS}
            />
          ) : null}
        </div>
      </details>

      <PowerDisclosure
        label="Solver-specific BC overrides"
        summary="Defaults: standard turbulence inlet (k-ω SST), no-slip walls"
        testIdPrefix="step3-bc-adv"
      >
        <p className="text-surface-300">
          Override turbulence intensity, hydraulic diameter, wall function
          model on a per-patch basis. Use the Raw Dict editor above for
          arbitrary keys not surfaced here.
        </p>
        <ul className="ml-3 list-disc text-surface-400">
          <li>Turbulence intensity: 5% (default)</li>
          <li>Hydraulic diameter: auto from patch bbox</li>
          <li>Wall function: nutkWallFunction (default) | nutkRoughWallFunction</li>
        </ul>
      </PowerDisclosure>
    </div>
  );
}
