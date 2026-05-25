/**
 * V4 · Viewport · vtk.js shell · per UI-SPEC §3 · Phase C real 3D viewport.
 *
 * Thin React shell around the existing imperative ``viewport_kernel`` so
 * V3-era chrome (rounded border + "Geometry preview" header + Reset
 * Camera button + status footer) is dropped. V4 is a full-bleed canvas
 * inside MainCanvasV4 with **no decorative frame**: the dark v4-canvas
 * background extends edge-to-edge. Loading / error / empty states render
 * compact corner badges so the SVG scaffold fallback can layer over them
 * without competing for the same vertical space.
 *
 * Phase C-R2 adds pickMode passthrough — when ``pickMode=true`` the
 * component fetches /face-index for the case and installs the same
 * cell-picker + hover-preselect + coplanar-sibling-expansion pipeline
 * V3's Viewport.tsx wires (DEC-V61-098). Result fires through
 * ``onFacePick`` as a stable face_id (plus all sibling face_ids in the
 * highlighted region). This is the surface the V4 边界 mode uses to
 * link clicks-on-bc-glb to real patches from workbench-basics.
 *
 * Hot-reload safety: dispose() runs in the useEffect cleanup. Camera
 * preset prop change re-fires setCameraPreset on the existing kernel
 * without recreating it.
 */
import { useEffect, useRef, useState } from "react";

import { api } from "@/api/client";
import { GlbLoadError, loadGlbFromUrl } from "@/visualization/glb_loader";
import {
  createKernel,
  type PickResult,
  type ViewportKernel,
} from "@/visualization/viewport_kernel";
import { WebGLUnavailableError } from "@/visualization/webgl_support";
import { V4_PALETTE } from "@/theme/industrial_minimalist";

import type { FaceIndexDocument } from "@/pages/workbench/step_panel_shell/types";

export type V4CameraPreset = "front" | "top" | "iso";

export interface V4FacePickEvent {
  faceId: string | null;
  faceIds: string[];
  patchName: string;
  cellId: number;
  worldPosition: [number, number, number];
}

/** Screen-space annotation contract · ViewportV4 owns the projection
 *  and renders the leader-line + label card itself when this prop is
 *  set (R5). Replaces the static top-right card that earlier rounds
 *  placed in mode renderers. */
export interface V4ViewportAnnotation {
  /** Patch id (== glTF primitive.name). Required for centroid fallback. */
  patchName: string;
  /** Face id from the last click pick, if any. Surfaces as a sub-line. */
  faceId?: string | null;
  /** Primary label (typically patch.label_zh). */
  label: string;
  /** Short role label rendered as a tag (e.g. "入口"). */
  roleLabel?: string;
  /** Role color · used for the swatch, leader, and card border. */
  color: string;
  /** Exact pick world position (preferred anchor when present · falls
   *  back to actor bounds centroid otherwise). */
  worldPos?: [number, number, number] | null;
}

interface ViewportV4Props {
  glbUrl: string | null | undefined;
  stlUrl?: string | null;
  cameraPreset?: V4CameraPreset;
  onReady?: () => void;
  showGrid?: boolean;
  /** When true, enable cell-level picking on the loaded glb. Requires
   *  ``caseId`` so /face-index can be fetched. Fires ``onFacePick``
   *  on every left-click that hits a cell. Hover (no click) updates
   *  the yellow ghost overlay only. */
  pickMode?: boolean;
  caseId?: string | null;
  onFacePick?: (event: V4FacePickEvent) => void;
  /** Phase C-R3 · legend → viewport reverse highlight. The kernel
   *  matches the glTF primitive.name to ``patch.id`` (bc_glb sets
   *  primitive.name=patch_name) and highlights every cell on the
   *  matching actor. ``null`` clears the named overlay. The kernel
   *  reuses the cyan committed-pick overlay so a click-pick + legend
   *  selection stay coherent (last writer wins).
   */
  highlightedPatchId?: string | null;
  /** R5 · render a screen-space annotation card with a leader line
   *  anchored at the projected patch centroid (or last-pick world
   *  pos). When ``null`` (default) no annotation renders. */
  annotation?: V4ViewportAnnotation | null;
  /** B2.5 · VTP overlay URLs for the Post-mode viewport. Both are
   *  optional and independent · either / both attach when present.
   *   - ``surfaceVtpUrl``  → real per-patch surface with U scalars
   *   - ``streamlinesVtpUrl`` → integrated streamline tracks
   *  The kernel auto-fits the camera after each attach.
   *  Caller controls re-attach via URL change (any change → rebuild). */
  surfaceVtpUrl?: string | null;
  streamlinesVtpUrl?: string | null;
  /** Optional setup/blueprint scalar range. When supplied, the kernel
   *  may use it to render a deterministic contour preview if the
   *  loaded VTP has degenerate U=0 data. Post mode leaves this unset
   *  so scientific result views remain tied to real VTP scalars. */
  surfaceVtpScalarRange?: [number, number];
  /** Fires once the VTP layers report their scalar (U-magnitude)
   *  range so the React side can render a real colorbar. */
  onVtpRangeReady?: (range: [number, number]) => void;
}

type LoadState =
  | { status: "loading" }
  | { status: "ready"; triangleCount?: number }
  | { status: "error"; message: string };

const V4_CANVAS_RGB: [number, number, number] = [
  parseInt(V4_PALETTE.canvas.slice(1, 3), 16) / 255,
  parseInt(V4_PALETTE.canvas.slice(3, 5), 16) / 255,
  parseInt(V4_PALETTE.canvas.slice(5, 7), 16) / 255,
];

/** face_id → list of cellIds where face_ids[i] === face_id. Built once
 *  per primitive so the pick handler (which fires every RAF) is an O(1)
 *  lookup. Mirrors V3 Viewport.tsx#attachSiblingMap. */
type FaceIndexWithSiblings = FaceIndexDocument & {
  primitives: Array<
    FaceIndexDocument["primitives"][number] & {
      _faceIdToCellIds?: Map<string, number[]>;
    }
  >;
};

function attachSiblingMap(doc: FaceIndexDocument): FaceIndexWithSiblings {
  for (const p of doc.primitives) {
    const map = new Map<string, number[]>();
    for (let i = 0; i < p.face_ids.length; i++) {
      const fid = p.face_ids[i];
      const list = map.get(fid);
      if (list) list.push(i);
      else map.set(fid, [i]);
    }
    (p as FaceIndexWithSiblings["primitives"][number])._faceIdToCellIds = map;
  }
  return doc as FaceIndexWithSiblings;
}

function isNonDegenerateScalarRange(range: [number, number]): boolean {
  return (
    Number.isFinite(range[0]) &&
    Number.isFinite(range[1]) &&
    range[1] > range[0]
  );
}

export function ViewportV4({
  glbUrl,
  cameraPreset = "iso",
  onReady,
  showGrid = true,
  pickMode = false,
  caseId,
  onFacePick,
  highlightedPatchId = null,
  annotation = null,
  surfaceVtpUrl = null,
  streamlinesVtpUrl = null,
  surfaceVtpScalarRange,
  onVtpRangeReady,
}: ViewportV4Props) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const kernelRef = useRef<ViewportKernel | null>(null);
  const faceIndexRef = useRef<FaceIndexWithSiblings | null>(null);
  const onFacePickRef = useRef<typeof onFacePick>(onFacePick);
  useEffect(() => {
    onFacePickRef.current = onFacePick;
  }, [onFacePick]);
  const [loadState, setLoadState] = useState<LoadState>({ status: "loading" });
  // Track face-index fetch separately from glb load so a 404 on
  // /face-index doesn't surface as a viewport error — it just degrades
  // pickMode to no-op. R4 closure of Codex P-1 finding "silent pick
  // degrade": now we render a soft 'face-index 缺失' badge instead of
  // silently swallowing.
  const [pickStatus, setPickStatus] = useState<
    "idle" | "loading" | "ready" | "unavailable"
  >("idle");
  /** Projected screen anchor for the annotation. Re-projects on every
   *  RAF tick while annotation is set so camera moves track. */
  const [annotationAnchor, setAnnotationAnchor] = useState<{
    x: number;
    y: number;
    behind: boolean;
    offscreen: boolean;
  } | null>(null);
  const [containerSize, setContainerSize] = useState<{
    w: number;
    h: number;
  } | null>(null);

  // Mount + load. Re-fires only on glbUrl change.
  //
  // M5 C2 bug #3 fix · the kernel also mounts in "VTP-base" mode when
  // there is no GLB but a post overlay URL is present (imported cases
  // carry STL → no GLB, yet foamToVTK surface/streamline overlays should
  // still render). In that mode we mount an empty kernel and mark it
  // `ready` so the VTP attach effects below fire; the first attachVtp
  // auto-fits the camera to the VTP bounds, so the overlay becomes the
  // base actor. glbUrl never transitions null↔string mid-life here — the
  // Post renderer waits for the GLB probe to settle before deciding —
  // so the `[glbUrl]` dep stays correct.
  useEffect(() => {
    const hasVtp = Boolean(surfaceVtpUrl || streamlinesVtpUrl);
    if (!glbUrl && !hasVtp) return;
    const container = containerRef.current;
    if (!container) return;

    let kernel: ViewportKernel;
    try {
      kernel = createKernel(container, { background: V4_CANVAS_RGB });
    } catch (err) {
      // No usable WebGL context → degrade gracefully instead of crashing the
      // React tree with vtk.js's opaque Proxy(null) TypeError.
      const msg =
        err instanceof WebGLUnavailableError
          ? "WebGL 不可用 · 3D 视口已降级"
          : (err as Error)?.message ?? "viewport init failed";
      setLoadState({ status: "error", message: msg });
      return;
    }
    kernelRef.current = kernel;

    const controller = new AbortController();
    let cancelled = false;
    setLoadState({ status: "loading" });

    if (!glbUrl) {
      // VTP-base mode · no GLB to load. Mount the empty kernel and mark
      // ready so the surface/streamline attach effects run; the kernel
      // auto-fits the camera on the first VTP attach.
      kernel.setCameraPreset(cameraPreset);
      setLoadState({ status: "ready" });
      onReady?.();
    } else {
      loadGlbFromUrl(glbUrl, controller.signal)
        .then(({ importer }) => {
          if (cancelled) {
            importer.delete();
            return;
          }
          kernel.attachGltf(importer);
          kernel.setCameraPreset(cameraPreset);
          setLoadState({ status: "ready" });
          onReady?.();
        })
        .catch((err: unknown) => {
          if ((err as { name?: string })?.name === "AbortError" || cancelled) return;
          const msg =
            err instanceof GlbLoadError
              ? `${err.kind}: ${err.message}`
              : (err as Error).message ?? "unknown error";
          setLoadState({ status: "error", message: msg });
        });
    }

    return () => {
      cancelled = true;
      controller.abort();
      kernelRef.current?.dispose();
      kernelRef.current = null;
      faceIndexRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [glbUrl]);

  // Camera preset prop sync.
  useEffect(() => {
    if (loadState.status !== "ready") return;
    kernelRef.current?.setCameraPreset(cameraPreset);
  }, [cameraPreset, loadState.status]);

  // B2.5 · attach surface VTP when URL becomes available + kernel ready.
  // Detach + re-attach on URL change so cached attachments don't leak.
  useEffect(() => {
    if (loadState.status !== "ready" || !surfaceVtpUrl) return;
    const kernel = kernelRef.current;
    if (!kernel) return;
    let cancelled = false;
    let handle: Awaited<ReturnType<typeof kernel.attachVtp>> | null = null;
    kernel
      .attachVtp(surfaceVtpUrl, "surface", surfaceVtpScalarRange)
      .then((h) => {
        if (cancelled) {
          kernel.detachVtp(h);
          return;
        }
        handle = h;
        if (isNonDegenerateScalarRange(h.scalarRange)) {
          onVtpRangeReady?.(h.scalarRange);
        }
      })
      .catch(() => {
        // Surface VTP load failed (404 / network / parse). Silently
        // skip the overlay — the base glb is still rendered, and the
        // residual chart in the right panel still pins truth.
      });
    return () => {
      cancelled = true;
      if (handle) {
        try {
          kernel.detachVtp(handle);
        } catch {
          // see kernel comments
        }
      }
    };
  }, [surfaceVtpUrl, surfaceVtpScalarRange, loadState.status, onVtpRangeReady]);

  // B2.5 · attach streamlines VTP — same pattern as surface.
  useEffect(() => {
    if (loadState.status !== "ready" || !streamlinesVtpUrl) return;
    const kernel = kernelRef.current;
    if (!kernel) return;
    let cancelled = false;
    let handle: Awaited<ReturnType<typeof kernel.attachVtp>> | null = null;
    kernel
      .attachVtp(streamlinesVtpUrl, "streamlines")
      .then((h) => {
        if (cancelled) {
          kernel.detachVtp(h);
          return;
        }
        handle = h;
        if (isNonDegenerateScalarRange(h.scalarRange)) {
          onVtpRangeReady?.(h.scalarRange);
        }
      })
      .catch(() => {
        // Streamlines not available yet · skip overlay silently.
      });
    return () => {
      cancelled = true;
      if (handle) {
        try {
          kernel.detachVtp(handle);
        } catch {
          // see above
        }
      }
    };
  }, [streamlinesVtpUrl, loadState.status, onVtpRangeReady]);

  // Phase C-R3 · highlightedPatchId prop sync. Idempotent — clear
  // overlay when null, otherwise call the kernel's named-patch
  // highlight. The kernel handles "patch name not found" gracefully
  // (returns 0 cells and clears) so we don't need to validate the
  // patch_id against the actorPatchNames map from the React layer.
  useEffect(() => {
    if (loadState.status !== "ready") return;
    kernelRef.current?.highlightPatchByName?.(highlightedPatchId, "pick");
  }, [highlightedPatchId, loadState.status]);

  // R5 · screen-space annotation projection loop. Runs only when an
  // annotation prop is present AND the kernel is ready. RAF polling
  // is the simplest reliable trigger — vtk.js renderer doesn't expose
  // a "camera moved" event we can hook portably, and the per-frame
  // cost (one matrix-multiply via vtkCoordinate) is trivial. The loop
  // also re-reads the container size each tick so a window resize
  // doesn't desync the leader line.
  useEffect(() => {
    if (!annotation || loadState.status !== "ready") {
      setAnnotationAnchor(null);
      return;
    }
    let raf = 0;
    let cancelled = false;
    const tick = () => {
      if (cancelled) return;
      const kernel = kernelRef.current;
      const container = containerRef.current;
      if (!kernel || !container) {
        raf = requestAnimationFrame(tick);
        return;
      }
      const rect = container.getBoundingClientRect();
      setContainerSize((prev) =>
        prev?.w === rect.width && prev?.h === rect.height
          ? prev
          : { w: rect.width, h: rect.height },
      );
      const world =
        annotation.worldPos ??
        kernel.getPatchCentroid?.(annotation.patchName) ??
        null;
      if (!world) {
        setAnnotationAnchor((prev) => (prev === null ? prev : null));
      } else {
        const screen = kernel.worldToScreen?.(world);
        // R5.1 (Codex finding) · epsilon guard against per-frame React
        // re-renders. The RAF loop runs ~60Hz; without this guard, a
        // static camera still produces 60 setState calls/sec because
        // each setState writes a fresh object reference. Compare with
        // 0.5 CSS px tolerance — sub-pixel jitter never affects the
        // overlay visually and only the resulting commit cost matters.
        const EPS = 0.5;
        setAnnotationAnchor((prev) => {
          if (!screen) return prev === null ? prev : null;
          if (
            prev &&
            Math.abs(prev.x - screen.x) < EPS &&
            Math.abs(prev.y - screen.y) < EPS &&
            prev.behind === screen.behind &&
            prev.offscreen === screen.offscreen
          ) {
            return prev;
          }
          return screen;
        });
      }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => {
      cancelled = true;
      cancelAnimationFrame(raf);
    };
  }, [annotation, loadState.status]);

  // Pick-mode wiring. Mirrors V3 Viewport.tsx pickMode effect — fetches
  // /face-index lazily on first activation, installs setPickHandler +
  // setHoverHandler with coplanar-sibling expansion + multi-face_id
  // collection. Re-runs only when pickMode/caseId/load-status change.
  useEffect(() => {
    if (!pickMode || !caseId) {
      const k = kernelRef.current;
      k?.setPickHandler?.(null);
      k?.setHoverHandler?.(null);
      k?.clearPickHighlight?.();
      k?.clearHoverHighlight?.();
      setPickStatus("idle");
      return;
    }
    if (loadState.status !== "ready") return;
    const kernel = kernelRef.current;
    if (!kernel?.setPickHandler) return;
    let disposed = false;
    setPickStatus(faceIndexRef.current ? "ready" : "loading");

    const resolvePrimitive = (
      patchName: string,
    ): FaceIndexWithSiblings["primitives"][number] | null => {
      const idx = faceIndexRef.current;
      if (!idx) return null;
      return (
        (patchName
          ? idx.primitives.find((p) => p.patch_name === patchName)
          : idx.primitives[0]) ??
        idx.primitives[0] ??
        null
      );
    };

    const expandSiblings = (result: PickResult, faceId: string | null): number[] => {
      const k = kernelRef.current;
      if (k?.getCoplanarSiblings) {
        const coplanar = k.getCoplanarSiblings(result.actor, result.cellId);
        if (coplanar.length > 1) return coplanar;
      }
      if (faceId !== null) {
        const primitive = resolvePrimitive(result.patchName);
        const sibs = primitive?._faceIdToCellIds?.get(faceId);
        if (sibs && sibs.length > 0) return sibs;
      }
      return [result.cellId];
    };

    const collectFaceIds = (
      primitive: FaceIndexWithSiblings["primitives"][number],
      sibs: number[],
      primary: string | null,
    ): string[] => {
      if (sibs.length <= 1) return primary !== null ? [primary] : [];
      const seen = new Set<string>();
      const out: string[] = [];
      if (primary !== null) {
        seen.add(primary);
        out.push(primary);
      }
      for (const cid of sibs) {
        if (cid < 0 || cid >= primitive.face_ids.length) continue;
        const fid = primitive.face_ids[cid];
        if (!fid || seen.has(fid)) continue;
        seen.add(fid);
        out.push(fid);
      }
      return out;
    };

    const handleKernelPick = (result: PickResult) => {
      const primitive = resolvePrimitive(result.patchName);
      if (!primitive) return;
      const faceId =
        result.cellId < primitive.face_ids.length
          ? primitive.face_ids[result.cellId]
          : null;
      const sibs = expandSiblings(result, faceId);
      if (sibs.length > 0) {
        kernelRef.current?.setPickHighlightCells?.(result.actor, sibs);
      } else {
        kernelRef.current?.clearPickHighlight?.();
      }
      const faceIds = collectFaceIds(primitive, sibs, faceId);
      onFacePickRef.current?.({
        faceId,
        faceIds,
        patchName: result.patchName,
        cellId: result.cellId,
        worldPosition: result.worldPosition,
      });
    };

    const handleKernelHover = (result: PickResult) => {
      const primitive = resolvePrimitive(result.patchName);
      if (!primitive) {
        kernelRef.current?.clearHoverHighlight?.();
        return;
      }
      const faceId =
        result.cellId < primitive.face_ids.length
          ? primitive.face_ids[result.cellId]
          : null;
      const sibs = expandSiblings(result, faceId);
      if (sibs.length > 0) {
        kernelRef.current?.setHoverHighlightCells?.(result.actor, sibs);
      } else {
        kernelRef.current?.clearHoverHighlight?.();
      }
    };

    if (faceIndexRef.current) {
      kernel.setPickHandler(handleKernelPick);
      kernel.setHoverHandler?.(handleKernelHover);
      setPickStatus("ready");
    } else {
      api
        .getFaceIndex(caseId)
        .then((doc) => {
          if (disposed) return;
          faceIndexRef.current = attachSiblingMap(doc);
          kernelRef.current?.setPickHandler?.(handleKernelPick);
          kernelRef.current?.setHoverHandler?.(handleKernelHover);
          setPickStatus("ready");
        })
        .catch(() => {
          // Surface the failure as a soft 'unavailable' status (R4
          // Codex P-1 closure). Clicks won't fire onFacePick, but
          // the user sees a badge instead of wondering why nothing
          // happens. The viewport itself stays interactive.
          if (!disposed) setPickStatus("unavailable");
        });
    }

    return () => {
      disposed = true;
      kernelRef.current?.setPickHandler?.(null);
      kernelRef.current?.setHoverHandler?.(null);
    };
  }, [pickMode, caseId, loadState.status]);

  // M5 C2 bug #3 (Codex R1 P1): render the container whenever there is
  // something to show — a GLB OR a post VTP overlay. The earlier
  // `if (!glbUrl) return null` short-circuited BEFORE the container div
  // existed, so the VTP-base mount effect found no containerRef and never
  // created the kernel. Mirror the mount-effect gate exactly.
  if (!glbUrl && !surfaceVtpUrl && !streamlinesVtpUrl) return null;

  return (
    <div
      className="relative h-full w-full"
      data-testid="viewport-v4"
      data-state={loadState.status}
      data-pick-mode={pickMode ? "true" : "false"}
    >
      <div
        ref={containerRef}
        data-testid="viewport-v4-canvas"
        className="absolute inset-0"
        style={{ backgroundColor: V4_PALETTE.canvas }}
      />
      {showGrid && (
        <svg
          className="pointer-events-none absolute inset-0 h-full w-full"
          aria-hidden
        >
          <defs>
            <pattern
              id="v4-viewport-grid"
              width="48"
              height="48"
              patternUnits="userSpaceOnUse"
            >
              <path
                d="M 48 0 L 0 0 0 48"
                fill="none"
                stroke={V4_PALETTE.border}
                strokeWidth="0.5"
                opacity="0.35"
              />
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#v4-viewport-grid)" />
        </svg>
      )}
      {loadState.status === "loading" && (
        <div
          className="pointer-events-none absolute left-3 top-3 rounded border border-v4-border bg-v4-surfaceRaised/90 px-2 py-0.5 font-mono text-[10px] text-v4-textSecondary"
          data-testid="viewport-v4-loading"
        >
          加载几何…
        </div>
      )}
      {loadState.status === "ready" && pickMode && (
        <div
          className={[
            "pointer-events-none absolute left-3 top-3 rounded border bg-v4-surfaceRaised/90 px-2 py-0.5 font-mono text-[10px]",
            pickStatus === "unavailable"
              ? "border-v4-warn/60 text-v4-warn"
              : pickStatus === "loading"
                ? "border-v4-border text-v4-textTertiary"
                : "border-v4-active/50 text-v4-active",
          ].join(" ")}
          data-testid="viewport-v4-pick-status"
          data-pick-status={pickStatus}
        >
          {pickStatus === "unavailable" && "拾选已降级 · face-index 缺失"}
          {pickStatus === "loading" && "拾选加载中…"}
          {pickStatus === "ready" && "拾选模式 · 点击面"}
          {pickStatus === "idle" && "拾选模式"}
        </div>
      )}
      {loadState.status === "error" && (
        <div
          className="pointer-events-none absolute left-3 top-3 rounded border border-v4-crit/60 bg-v4-surfaceRaised/95 px-2 py-0.5 font-mono text-[10px] text-v4-crit"
          data-testid="viewport-v4-error"
          title={loadState.message}
        >
          视口加载失败
        </div>
      )}
      {annotation && annotationAnchor && containerSize && (
        <AnnotationLayer
          annotation={annotation}
          anchor={annotationAnchor}
          container={containerSize}
        />
      )}
    </div>
  );
}

interface AnnotationLayerProps {
  annotation: V4ViewportAnnotation;
  anchor: { x: number; y: number; behind: boolean; offscreen: boolean };
  container: { w: number; h: number };
}

/** R5 · Screen-space annotation overlay · positions a label card off
 *  the projected patch centroid and draws a dashed leader line from
 *  the anchor (3D patch on screen) to the card edge.
 *
 *  R5.1 split:
 *   - `behind=true`     · projection is meaningless. Clamp card to a
 *                         corner, no leader, "↗ patch 在视口外" microcopy.
 *   - `offscreen=true`  · projection valid but off the viewport box.
 *                         Clamp the leader endpoint to the nearest edge
 *                         so the user still sees "the patch is over
 *                         there" with a real direction.
 *   - both false        · normal case, leader to projected anchor.
 */
function AnnotationLayer({ annotation, anchor, container }: AnnotationLayerProps) {
  const CARD_W = 200;
  const CARD_H = annotation.faceId ? 70 : 52;
  const OFFSET_X = 110;
  const OFFSET_Y = -60;
  const PAD = 8;

  // Visible anchor used for drawing — clamped into the container box
  // when the real anchor is offscreen so the leader has a useful
  // endpoint. When `behind`, both anchor coords are meaningless so
  // we anchor the card to top-right corner without a leader.
  const drawnAnchorX = anchor.behind
    ? container.w - PAD
    : Math.max(0, Math.min(container.w, anchor.x));
  const drawnAnchorY = anchor.behind
    ? PAD
    : Math.max(0, Math.min(container.h, anchor.y));

  let cardLeft = drawnAnchorX + OFFSET_X - CARD_W / 2;
  let cardTop = drawnAnchorY + OFFSET_Y - CARD_H / 2;
  if (cardLeft + CARD_W + PAD > container.w) {
    cardLeft = drawnAnchorX - OFFSET_X - CARD_W / 2;
  }
  if (cardTop < PAD) cardTop = drawnAnchorY + Math.abs(OFFSET_Y) - CARD_H / 2;
  cardLeft = Math.max(PAD, Math.min(container.w - CARD_W - PAD, cardLeft));
  cardTop = Math.max(PAD, Math.min(container.h - CARD_H - PAD, cardTop));

  // Pick the card edge nearest to the anchor for the leader endpoint.
  const cardCenterX = cardLeft + CARD_W / 2;
  const cardCenterY = cardTop + CARD_H / 2;
  const dx = drawnAnchorX - cardCenterX;
  const dy = drawnAnchorY - cardCenterY;
  let endX: number;
  let endY: number;
  if (Math.abs(dx) * CARD_H > Math.abs(dy) * CARD_W) {
    endX = dx > 0 ? cardLeft + CARD_W : cardLeft;
    endY = cardCenterY + (dy / Math.abs(dx || 1)) * (CARD_W / 2);
  } else {
    endY = dy > 0 ? cardTop + CARD_H : cardTop;
    endX = cardCenterX + (dx / Math.abs(dy || 1)) * (CARD_H / 2);
  }
  const midX = (drawnAnchorX + endX) / 2;
  const midY = (drawnAnchorY + endY) / 2 - 12;

  // Drawing flags:
  //   • behind   → no leader, anchor marker omitted, edge microcopy
  //   • offscreen→ leader to clamped edge anchor with chevron marker
  //                indicating direction toward off-frame patch
  //   • normal   → leader to anchor + double-circle marker
  const showLeader = !anchor.behind;
  const showAnchorRing = !anchor.behind && !anchor.offscreen;

  return (
    <div
      className="pointer-events-none absolute inset-0"
      data-testid="viewport-v4-annotation"
      aria-hidden
    >
      <svg
        className="absolute inset-0 h-full w-full"
        viewBox={`0 0 ${container.w} ${container.h}`}
        preserveAspectRatio="none"
      >
        {showLeader && (
          <path
            d={`M ${drawnAnchorX} ${drawnAnchorY} Q ${midX} ${midY} ${endX} ${endY}`}
            fill="none"
            stroke={annotation.color}
            strokeWidth="1.2"
            strokeDasharray="3 2"
            opacity="0.85"
          />
        )}
        {showAnchorRing && (
          <>
            <circle
              cx={drawnAnchorX}
              cy={drawnAnchorY}
              r="3"
              fill={annotation.color}
              opacity="0.95"
            />
            <circle
              cx={drawnAnchorX}
              cy={drawnAnchorY}
              r="6"
              fill="none"
              stroke={annotation.color}
              strokeWidth="0.8"
              opacity="0.5"
            />
          </>
        )}
        {anchor.offscreen && !anchor.behind && (
          <circle
            cx={drawnAnchorX}
            cy={drawnAnchorY}
            r="4"
            fill="none"
            stroke={annotation.color}
            strokeWidth="1.5"
            opacity="0.9"
          />
        )}
      </svg>
      <div
        className="absolute flex flex-col gap-1 rounded border bg-v4-surfaceRaised/95 px-3 py-2 shadow-lg"
        style={{
          left: cardLeft,
          top: cardTop,
          width: CARD_W,
          borderColor: annotation.color + "99",
        }}
        data-testid="viewport-v4-annotation-card"
        data-behind={anchor.behind ? "true" : "false"}
        data-offscreen={anchor.offscreen ? "true" : "false"}
      >
        <div className="flex items-center gap-2">
          <span
            aria-hidden
            className="h-2.5 w-2.5 shrink-0 rounded-sm"
            style={{ backgroundColor: annotation.color }}
          />
          <span className="flex-1 truncate text-[12px] font-medium text-v4-textPrimary">
            {annotation.label}
          </span>
          {annotation.roleLabel && (
            <span className="font-mono text-[9px] text-v4-textTertiary">
              {annotation.roleLabel}
            </span>
          )}
        </div>
        <div
          className="truncate font-mono text-[10px] text-v4-textTertiary"
          title={annotation.patchName}
        >
          {annotation.patchName}
        </div>
        {annotation.faceId && (
          <div className="border-t border-v4-border pt-1 font-mono text-[10px] text-v4-textSecondary">
            face_id ·{" "}
            <span className="text-v4-textPrimary">{annotation.faceId}</span>
          </div>
        )}
        {anchor.behind && (
          <div className="font-mono text-[9px] text-v4-warn">
            ↗ patch 在相机背后
          </div>
        )}
        {anchor.offscreen && !anchor.behind && (
          <div className="font-mono text-[9px] text-v4-warn">
            ↗ patch 在视口外
          </div>
        )}
      </div>
    </div>
  );
}
