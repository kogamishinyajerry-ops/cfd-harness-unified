// Right-rail face-annotation form (DEC-V61-098 spec_v2 §A8).
//
// Renders when the engineer picks a face in the Viewport. The form
// captures `name`, `patch_type`, and a free-text `physics_notes`,
// then dispatches PUT /face-annotations with confidence='user_authoritative'
// and annotated_by='human' — the sticky invariant in the backend
// merge function (§B.1) ensures subsequent AI writes can't overwrite
// the user's choice.

import { useEffect, useState } from "react";

import type { FaceAnnotation } from "./types";

const PATCH_TYPES = ["wall", "patch", "symmetry", "empty", "cyclic"] as const;

interface AnnotationPanelProps {
  /** The face_id that was picked. The form is keyed off this so it
   *  remounts (resets state) when the engineer picks a new face. */
  faceId: string;
  /** Total number of face_ids the save will be applied to (the
   *  visually-highlighted segment). When >1 the panel surfaces a
   *  badge so the engineer knows the BC will fan out across every
   *  triangle of the curved patch — e.g. "Applies to 124 faces"
   *  on a tet-meshed cylinder side (Codex e844a6f review P1).
   *  Defaults to 1 (back-compat for single-face dogfood paths
   *  and tests that synthesize the panel directly). */
  faceIdCount?: number;
  /** Existing annotation for this face_id, if any. Used to seed the
   *  form with the latest persisted values. */
  existing?: FaceAnnotation;
  /** Disabled while a PUT is in flight or the AI is mid-run.
   *  The shell sets this to ``aiInFlight || saveInFlight``. */
  disabled?: boolean;
  /** Fires when the engineer clicks "Save". Caller is responsible for
   *  dispatching the PUT and updating the cache; this component is
   *  presentational. Returns a Promise so the caller can keep the
   *  button disabled while the request is in flight. */
  onSave: (patch: FaceAnnotation) => Promise<void>;
  /** Optional: clear the picked face (e.g. when the engineer dismisses
   *  the panel without saving). The shell typically wires this to
   *  clearing the FacePickContext. */
  onCancel?: () => void;
}

// Placeholder sentinel for "no patch type selected yet" (Codex 86gs
// N1.1 R11 P1#1 close). Distinguishing default-untouched from
// engineer-explicit cannot be done with an onChange touched-flag
// because <select> doesn't fire change when the engineer clicks the
// already-selected option to re-confirm. The placeholder UX makes
// the selection state unambiguous: the dropdown starts on "—",
// and any real option (including "wall") requires an explicit pick.
const PATCH_TYPE_PLACEHOLDER = "" as const;

export function AnnotationPanel({
  faceId,
  faceIdCount = 1,
  existing,
  disabled = false,
  onSave,
  onCancel,
}: AnnotationPanelProps) {
  const [name, setName] = useState(existing?.name ?? "");
  // patchType holds the dropdown's current value. Empty string means
  // "no real option selected" — the placeholder is showing. Any
  // PATCH_TYPES value (including "wall") means engineer picked it.
  // Existing values seed the dropdown to that option directly.
  const [patchType, setPatchType] = useState<string>(
    existing?.patch_type ?? PATCH_TYPE_PLACEHOLDER,
  );
  const [physicsNotes, setPhysicsNotes] = useState(
    existing?.physics_notes ?? "",
  );
  const [saveInFlight, setSaveInFlight] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Reset form when the engineer picks a different face.
  useEffect(() => {
    setName(existing?.name ?? "");
    setPatchType(existing?.patch_type ?? PATCH_TYPE_PLACEHOLDER);
    setPhysicsNotes(existing?.physics_notes ?? "");
    setError(null);
    setSaveInFlight(false);
  }, [faceId, existing?.name, existing?.patch_type, existing?.physics_notes]);

  const submit = async () => {
    if (!name.trim()) {
      setError("Please give the face a name (e.g. 'inlet', 'lid').");
      return;
    }
    setError(null);
    setSaveInFlight(true);
    try {
      const isExplicitPick = patchType !== PATCH_TYPE_PLACEHOLDER;
      await onSave({
        face_id: faceId,
        name: name.trim(),
        // Persist patch_type only when the engineer actually picked
        // a real option from the dropdown. Placeholder-still-selected
        // saves leave it undefined so downstream stale-pin recovery
        // in Step3SetupBC can carry stale metadata forward
        // unambiguously, AND so an explicit "wall" pick (which had
        // no way to be expressed in R10's heuristic world) is
        // preserved as engineer-authoritative.
        patch_type: isExplicitPick ? patchType : undefined,
        // R12 marker: positive signal that this patch_type came from
        // an explicit engineer pick (or seeded from a prior explicit
        // save). The stale-pin recovery resume layer keys off this
        // to disambiguate from legacy pre-R11 records where every
        // untouched save persisted patch_type="wall" by default.
        patch_type_explicit: isExplicitPick ? true : undefined,
        physics_notes: physicsNotes.trim() || undefined,
        confidence: "user_authoritative",
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setSaveInFlight(false);
    }
  };

  const isLocked = disabled || saveInFlight;

  return (
    <div
      data-testid="annotation-panel"
      className="space-y-3 rounded-sm border border-surface-800 bg-surface-950/60 p-3 text-[12px]"
    >
      <div className="flex items-center justify-between">
        <h3 className="font-mono text-[10px] uppercase tracking-wider text-surface-400">
          Face annotation
        </h3>
        <span
          className="font-mono text-[10px] text-surface-500"
          data-testid="annotation-panel-face-id"
          title={faceId}
        >
          {faceId.slice(0, 12)}…
        </span>
      </div>
      {faceIdCount > 1 && (
        <div
          data-testid="annotation-panel-multi-face-badge"
          className="rounded-sm border border-amber-700/40 bg-amber-900/20 px-2 py-1 text-[11px] text-amber-200"
        >
          Applies to {faceIdCount} faces (smooth surface segment).
        </div>
      )}

      <label className="block space-y-1">
        <span className="text-[11px] text-surface-300">Name</span>
        <input
          type="text"
          value={name}
          disabled={isLocked}
          onChange={(e) => setName(e.target.value)}
          placeholder="e.g. inlet"
          data-testid="annotation-panel-name"
          className="w-full rounded-sm border border-surface-700 bg-surface-900 px-2 py-1 text-[12px] text-surface-100 placeholder:text-surface-600 focus:border-emerald-500 focus:outline-none disabled:cursor-not-allowed disabled:opacity-50"
        />
      </label>

      <label className="block space-y-1">
        <span className="text-[11px] text-surface-300">Patch type</span>
        <select
          value={patchType}
          disabled={isLocked}
          onChange={(e) => setPatchType(e.target.value)}
          data-testid="annotation-panel-patch-type"
          className="w-full rounded-sm border border-surface-700 bg-surface-900 px-2 py-1 text-[12px] text-surface-100 focus:border-emerald-500 focus:outline-none disabled:cursor-not-allowed disabled:opacity-50"
        >
          <option value={PATCH_TYPE_PLACEHOLDER}>— select patch type —</option>
          {PATCH_TYPES.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
      </label>

      <label className="block space-y-1">
        <span className="text-[11px] text-surface-300">
          Physics notes <span className="text-surface-500">(optional)</span>
        </span>
        <textarea
          value={physicsNotes}
          disabled={isLocked}
          onChange={(e) => setPhysicsNotes(e.target.value)}
          rows={2}
          placeholder="e.g. fixedValue U=(1 0 0)"
          data-testid="annotation-panel-notes"
          className="w-full rounded-sm border border-surface-700 bg-surface-900 px-2 py-1 text-[11px] text-surface-100 placeholder:text-surface-600 focus:border-emerald-500 focus:outline-none disabled:cursor-not-allowed disabled:opacity-50"
        />
      </label>

      {error && (
        <p
          className="rounded-sm border border-rose-500/40 bg-rose-500/10 px-2 py-1 text-[11px] text-rose-200"
          data-testid="annotation-panel-error"
        >
          {error}
        </p>
      )}

      <div className="flex items-center justify-end gap-2 pt-1">
        {onCancel && (
          <button
            type="button"
            onClick={onCancel}
            disabled={isLocked}
            className="rounded-sm border border-surface-700 bg-surface-900/40 px-2 py-1 text-[11px] text-surface-300 transition hover:bg-surface-800 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Cancel
          </button>
        )}
        <button
          type="button"
          onClick={submit}
          disabled={isLocked}
          data-testid="annotation-panel-save"
          className="rounded-sm border border-emerald-500/60 bg-emerald-500/15 px-3 py-1 text-[11px] text-emerald-100 transition hover:bg-emerald-500/25 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {saveInFlight ? "Saving…" : "Save"}
        </button>
      </div>
    </div>
  );
}
