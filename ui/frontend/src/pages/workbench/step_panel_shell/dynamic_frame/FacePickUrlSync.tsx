// DEC-V61-202-SUB-M30-CYCLE3 · mirror FacePickContext.picked.patchName
// into the URL search param ?focus_patch=<name>.
//
// Lives inside <FacePickProvider> so it can subscribe to picked.
// Reads + writes the URL via react-router useSearchParams. The
// backend's decide() reads ?focus_patch= from the GET frame request
// and uses it to bias rail.primary + bottom_cards toward problems
// mentioning the patch the engineer is currently looking at.
//
// One-way only (picked → URL). Deep-linking with ?focus_patch=<x>
// directly is supported on the backend side (decide() reads URL),
// but does NOT round-trip back into FacePickContext.picked — the
// Viewport's spatial highlight only updates on an actual pick event.
// See DEC §Risks "deep-link with focus_patch but no Viewport pick"
// for the deliberate cycle-4-deferred trade-off.

import { useEffect, useRef } from "react";
import { useSearchParams } from "react-router-dom";

import { useFacePickOptional } from "../FacePickContext";

interface FacePickUrlSyncProps {
  /** When false, the sync is dormant (no URL writes). Lets the
   *  shell mount the component unconditionally inside FacePickProvider
   *  but only activate when the dynamic-frame feature flag is on. */
  enabled: boolean;
}

export function FacePickUrlSync({ enabled }: FacePickUrlSyncProps) {
  const facePick = useFacePickOptional();
  const [searchParams, setSearchParams] = useSearchParams();
  const picked = facePick?.picked ?? null;
  const patchName = picked?.patchName ?? null;
  // Track whether we've ever observed a pick (i.e., a non-null
  // ``picked`` state). On the initial render we don't yet know
  // whether the engineer will pick anything, so we must leave a
  // deep-linked ?focus_patch=<x> alone. As soon as a real pick fires
  // (picked transitions null → PickedFaceState), the engineer's
  // spatial input becomes authoritative and we mirror picked.patchName
  // into the URL — including the "picked an unnamed face, patchName
  // is null" case where we actively remove ?focus_patch=.
  // See DEC §Risks "deep-link with focus_patch but no Viewport pick".
  const hasObservedPickRef = useRef(false);

  useEffect(() => {
    if (!enabled) return;

    const everPicked = hasObservedPickRef.current || picked !== null;
    if (picked !== null) hasObservedPickRef.current = true;

    if (!everPicked) {
      // No pick has ever happened — URL is authoritative; don't touch.
      return;
    }

    const currentFocusPatch = searchParams.get("focus_patch");
    // No-op when the URL already matches what we'd write — guards
    // against extra router churn (e.g., publisher fired twice with
    // the same patchName in quick succession).
    if (patchName === currentFocusPatch) return;
    if (!patchName && !currentFocusPatch) return;

    const next = new URLSearchParams(searchParams);
    if (patchName) {
      next.set("focus_patch", patchName);
    } else {
      next.delete("focus_patch");
    }
    setSearchParams(next, { replace: true });
  }, [enabled, picked, patchName, searchParams, setSearchParams]);

  return null;
}
