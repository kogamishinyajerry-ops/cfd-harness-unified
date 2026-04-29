// Shared face-pick state between the Viewport and the right-rail
// panels (DEC-V61-098 spec_v2 §A6+§A8).
//
// The Viewport (when its pickMode prop is true) publishes pick events
// here via ``setPickedFace``. The Step3SetupBC body subscribes via
// ``usePickedFace`` and renders the AnnotationPanel for the picked
// face_id. After a successful save (or explicit cancel), the panel
// clears the selection so the engineer sees a clean slate before
// picking the next face.

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";

export interface PickedFaceState {
  /** Stable face_id resolved by the Viewport. */
  faceId: string;
  /** World-space click position — used by the AnnotationPanel to
   *  optionally anchor itself near the picked face (Tier-A: just
   *  metadata, no positioning yet). */
  worldPosition: [number, number, number];
}

interface FacePickContextValue {
  picked: PickedFaceState | null;
  setPicked: (next: PickedFaceState | null) => void;
}

const FacePickContext = createContext<FacePickContextValue | null>(null);

export function FacePickProvider({ children }: { children: ReactNode }) {
  const [picked, setPicked] = useState<PickedFaceState | null>(null);
  const value = useMemo(
    () => ({ picked, setPicked }),
    [picked],
  );
  return (
    <FacePickContext.Provider value={value}>
      {children}
    </FacePickContext.Provider>
  );
}

export function useFacePick(): FacePickContextValue {
  const ctx = useContext(FacePickContext);
  if (ctx === null) {
    throw new Error(
      "useFacePick must be used inside a <FacePickProvider>",
    );
  }
  return ctx;
}

/** Returns ``picked`` or null when not inside a provider — used by
 *  components that may render in either mode (e.g., the Viewport in
 *  contexts without a provider, like the standalone import preview).
 */
export function useFacePickOptional(): FacePickContextValue | null {
  return useContext(FacePickContext);
}

/** Convenience hook that returns a handler suitable for the Viewport's
 *  ``onFacePick`` prop — strips the cell/primitive metadata and only
 *  forwards the resolved face_id + world position into the context.
 *  Use it together with ``useFacePickOptional`` so the handler is null
 *  outside a provider (no-op).
 */
export function useFacePickPublisher() {
  const ctx = useFacePickOptional();
  return useCallback(
    (event: {
      faceId: string | null;
      primitiveIndex: number;
      cellId: number;
      worldPosition: [number, number, number];
    }) => {
      if (!ctx || !event.faceId) return;
      ctx.setPicked({
        faceId: event.faceId,
        worldPosition: event.worldPosition,
      });
    },
    [ctx],
  );
}
