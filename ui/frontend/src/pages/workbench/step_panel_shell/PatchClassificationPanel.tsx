// DEC-V61-108 Phase B · per-patch BC classification override panel.
//
// Renders below Step 3's setup-bc surface. Lists every patch in
// polyMesh/boundary with two columns:
//   - "Auto"     → what bc_setup_from_stl_patches._classify_patch emits
//                  WITHOUT the override layer (heuristic baseline)
//   - "Override" → what the engineer has saved in
//                  ``system/patch_classification.yaml``
//
// Each row has a dropdown to set/clear the override. When the engineer
// has picked a face in the Viewport AND the picked face's patch can
// be resolved via FaceIndexDocument, that row highlights so the user
// sees "this is the patch you just clicked".
//
// Phase A (backend) shipped the GET/PUT/DELETE store with fd-based
// race-free I/O. Phase B (this file) is the first surface that lets
// the engineer actually use it; without this the override sidecar
// only ever populates from out-of-band scripts, which defeats the
// "human can freely select+edit" half of the workbench charter.

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { api, ApiError } from "@/api/client";
import type {
  BCClassValue,
  FaceIndexDocument,
  PatchClassificationState,
} from "./types";

const BC_CLASS_OPTIONS: BCClassValue[] = [
  "velocity_inlet",
  "pressure_outlet",
  "no_slip_wall",
  "symmetry",
];

const BC_CLASS_LABEL: Record<BCClassValue, string> = {
  velocity_inlet: "Velocity inlet",
  pressure_outlet: "Pressure outlet",
  no_slip_wall: "No-slip wall",
  symmetry: "Symmetry",
};

interface PatchClassificationPanelProps {
  caseId: string;
  /** The face_id the engineer just picked in the Viewport, or null
   *  when no pick is active. Used to derive the highlighted patch row
   *  via the cached FaceIndexDocument lookup. */
  pickedFaceId: string | null;
}

/** Codex R1 P3 closure: pull the structured ``failing_check`` /
 *  ``detail`` payload out of an ``ApiError`` if present, otherwise
 *  fall back to the bare error message. Used by both the initial
 *  GET path and the per-row save path so error UX is consistent.
 */
function formatApiErrorDetail(e: unknown): string {
  if (e instanceof ApiError && e.detail && typeof e.detail === "object") {
    const detail = e.detail as { failing_check?: string; detail?: string };
    if (detail.failing_check) {
      return `${detail.failing_check}${detail.detail ? `: ${detail.detail}` : ""}`;
    }
  }
  if (e instanceof Error) return e.message;
  return String(e);
}

export function PatchClassificationPanel({
  caseId,
  pickedFaceId,
}: PatchClassificationPanelProps) {
  const [state, setState] = useState<PatchClassificationState | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [faceIndex, setFaceIndex] = useState<FaceIndexDocument | null>(null);
  // Per-row save error (keyed by patch_name). Cleared when the row
  // dispatches a new save successfully or the engineer clears the
  // override. This keeps errors local to the row so a 422 on patch A
  // doesn't visually disrupt patch B's edit.
  const [rowError, setRowError] = useState<Record<string, string>>({});
  const [savingPatch, setSavingPatch] = useState<string | null>(null);

  // Codex R2 P1+P3 closure: split the single stateGenRef from R1 into
  // two independent tokens because conflating them dropped legitimate
  // updates:
  //   - ``caseGenRef``: bumped only on caseId change. Used by the
  //     case-scoped fetches (initial GET, getFaceIndex). A save
  //     dispatch must NOT invalidate an in-flight face-index GET —
  //     that's the R2 P3 bug.
  //   - ``committedSeqRef``: tracks the highest save-seq we've already
  //     applied to ``state``. handleChange captures its mySeq at
  //     issue; on success it commits iff ``mySeq > committedSeq``,
  //     then advances committedSeq. Failed saves do NOT advance
  //     committedSeq — so an older save that succeeds after a newer
  //     save fails still lands. That's the R2 P1 bug.
  //   - ``saveSeqRef``: bumped on every save dispatch to mint mySeq.
  //
  // Codex R1 P1 #2 closure (defense in depth): the parent already
  // mounts the panel as <PatchClassificationPanel key={caseId} ... />
  // so a caseId switch fully remounts. The caseId-change effect
  // below is belt-and-braces in case a future refactor drops the
  // key prop.
  const caseGenRef = useRef(0);
  const saveSeqRef = useRef(0);
  const committedSeqRef = useRef(0);
  const cancelledRef = useRef(false);
  useEffect(() => {
    cancelledRef.current = false;
    return () => {
      cancelledRef.current = true;
    };
  }, []);

  // Codex R1 P1 #2 closure: proactively wipe case-scoped local state
  // the moment caseId changes, BEFORE the new fetches resolve. With
  // the parent's key prop in place this effect runs on mount only.
  useEffect(() => {
    caseGenRef.current += 1;
    // Reset save sequence counters too — the new case starts from
    // a clean slate so a stale in-flight save (which also failed
    // the caseGen guard) can't slip through on seq comparison.
    saveSeqRef.current = 0;
    committedSeqRef.current = 0;
    setState(null);
    setLoadError(null);
    setFaceIndex(null);
    setRowError({});
    setSavingPatch(null);
  }, [caseId]);

  // Fetch state on mount + whenever the case changes. The captured
  // ``caseGen`` lets us drop late responses from a previous case.
  // The ``committedSeqRef > 0`` guard prevents a slow initial GET
  // from clobbering a save's authoritative response that arrived
  // first (PUT/DELETE responses are full merged state, so they
  // strictly dominate the initial snapshot).
  useEffect(() => {
    if (!caseId) return;
    const myCaseGen = caseGenRef.current;
    const isStale = () =>
      cancelledRef.current || caseGenRef.current !== myCaseGen;
    api
      .getPatchClassification(caseId)
      .then((doc) => {
        if (isStale()) return;
        if (committedSeqRef.current > 0) return;
        setState(doc);
        setLoadError(null);
      })
      .catch((e) => {
        if (isStale()) return;
        setLoadError(formatApiErrorDetail(e));
      });
  }, [caseId]);

  // FaceIndex is only needed to resolve picked-face → patch. Fetch
  // lazily — if the mesh hasn't been built yet GET /face-index 404s,
  // and we just degrade to "no highlight on pick".
  //
  // Codex R2 P3 closure: guarded by caseGenRef ONLY, never by the
  // save sequence. A user save in flight must not strand the picked-
  // face highlight feature.
  useEffect(() => {
    if (!caseId) return;
    const myCaseGen = caseGenRef.current;
    const isStale = () =>
      cancelledRef.current || caseGenRef.current !== myCaseGen;
    api
      .getFaceIndex(caseId)
      .then((doc) => {
        if (!isStale()) setFaceIndex(doc);
      })
      .catch(() => {
        // Non-fatal — picked-face highlight just won't activate.
        if (!isStale()) setFaceIndex(null);
      });
  }, [caseId]);

  // Resolve picked face_id → patch_name using FaceIndex primitives.
  // Returns null when no pick is active OR the face_id isn't found
  // (e.g. stale pick from a different mesh revision).
  const pickedPatchName = useMemo<string | null>(() => {
    if (!pickedFaceId || !faceIndex) return null;
    for (const prim of faceIndex.primitives) {
      if (prim.face_ids.includes(pickedFaceId)) return prim.patch_name;
    }
    return null;
  }, [pickedFaceId, faceIndex]);

  const handleChange = useCallback(
    async (patchName: string, nextValue: string) => {
      // Mint a per-dispatch sequence + capture the case generation.
      // The save commits iff (a) the case hasn't changed under us
      // AND (b) no newer save has already been applied (Codex R2 P1
      // closure). Failed saves leave committedSeq alone so an older
      // save that succeeds later can still land.
      saveSeqRef.current += 1;
      const mySeq = saveSeqRef.current;
      const myCaseGen = caseGenRef.current;
      const isCancelled = () =>
        cancelledRef.current || caseGenRef.current !== myCaseGen;

      setSavingPatch(patchName);
      setRowError((prev) => {
        if (!(patchName in prev)) return prev;
        const { [patchName]: _drop, ...rest } = prev;
        return rest;
      });
      try {
        let next: PatchClassificationState;
        if (nextValue === "") {
          next = await api.deletePatchClassification(caseId, patchName);
        } else {
          next = await api.putPatchClassification(caseId, {
            patch_name: patchName,
            bc_class: nextValue as BCClassValue,
          });
        }
        if (isCancelled()) return;
        if (mySeq <= committedSeqRef.current) return;
        committedSeqRef.current = mySeq;
        setState(next);
      } catch (e) {
        if (isCancelled()) return;
        setRowError((prev) => ({ ...prev, [patchName]: formatApiErrorDetail(e) }));
      } finally {
        if (!isCancelled()) setSavingPatch(null);
      }
    },
    [caseId],
  );

  if (loadError) {
    return (
      <div
        data-testid="patch-classification-load-error"
        className="rounded-sm border border-rose-700/40 bg-rose-900/10 px-2 py-1 text-[11px] text-rose-200"
      >
        Could not load patch classification: {loadError}
      </div>
    );
  }

  if (!state) {
    return (
      <div
        data-testid="patch-classification-loading"
        className="rounded-sm border border-surface-800 bg-surface-900/40 px-2 py-1 text-[11px] text-surface-400"
      >
        Loading patch classification…
      </div>
    );
  }

  if (state.available_patches.length === 0) {
    return (
      <div
        data-testid="patch-classification-no-mesh"
        className="rounded-sm border border-surface-800 bg-surface-900/40 px-2 py-1 text-[11px] text-surface-400"
      >
        No mesh patches detected yet — run Step 2 (mesh) first, then
        come back to assign per-patch BC classifications.
      </div>
    );
  }

  return (
    <section
      data-testid="patch-classification-panel"
      className="space-y-2 rounded-sm border border-surface-800 bg-surface-950/60 p-3 text-[12px]"
    >
      <header className="flex items-baseline justify-between">
        <h3 className="font-mono text-[10px] uppercase tracking-wider text-surface-400">
          Patch classification ({state.available_patches.length})
        </h3>
        <span className="font-mono text-[10px] text-surface-500">
          schema v{state.schema_version}
        </span>
      </header>
      <p className="text-[10px] text-surface-500">
        Override the heuristic per patch. The setup-bc mapper reads
        from here BEFORE running its name-based classifier — useful
        when patch names don't match the inlet/outlet/wall convention.
      </p>
      <table
        className="w-full border-separate border-spacing-y-1 text-left text-[11px]"
      >
        <thead className="text-[10px] uppercase tracking-wider text-surface-500">
          <tr>
            <th className="px-1 py-1">Patch</th>
            <th className="px-1 py-1">Auto</th>
            <th className="px-1 py-1">Override</th>
          </tr>
        </thead>
        <tbody>
          {state.available_patches.map((name) => {
            const auto = state.auto_classifications[name] ?? "";
            const override = state.overrides[name] ?? "";
            const isPicked = pickedPatchName === name;
            const err = rowError[name];
            return (
              <tr
                key={name}
                data-testid={`patch-row-${name}`}
                data-picked={isPicked ? "true" : undefined}
                className={
                  isPicked
                    ? "bg-amber-500/10 ring-1 ring-amber-500/40"
                    : "bg-surface-900/40"
                }
              >
                <td className="px-1 py-1 align-top font-mono text-surface-200">
                  {name}
                </td>
                <td className="px-1 py-1 align-top font-mono text-surface-400">
                  {auto || "—"}
                </td>
                <td className="px-1 py-1 align-top">
                  <select
                    aria-label={`Override for ${name}`}
                    data-testid={`override-select-${name}`}
                    value={override}
                    disabled={savingPatch === name}
                    onChange={(e) => handleChange(name, e.target.value)}
                    className="w-full rounded-sm border border-surface-700 bg-surface-900 px-1 py-1 text-[11px] text-surface-100 focus:border-emerald-500 focus:outline-none disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    <option value="">— inherit auto —</option>
                    {BC_CLASS_OPTIONS.map((cls) => (
                      <option key={cls} value={cls}>
                        {BC_CLASS_LABEL[cls]}
                      </option>
                    ))}
                  </select>
                  {err && (
                    <div
                      data-testid={`override-error-${name}`}
                      className="mt-1 rounded-sm border border-rose-500/40 bg-rose-500/10 px-1 py-0.5 text-[10px] text-rose-200"
                    >
                      {err}
                    </div>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </section>
  );
}
