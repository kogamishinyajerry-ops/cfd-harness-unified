// DEC-V61-202-SUB-M30-CYCLE1 · viewport.overlays slot renderer.
//
// Floats overlay decorations on top of the Viewport element. Cycle 1
// renders as a corner-anchored badge stack — full 3D-coordinate
// overlays (e.g. spatial patch-highlight rings inside the WebGL
// canvas) are deferred to cycle 2 (requires Viewport API surface
// extension).
//
// Failure modes:
//   - empty overlays array → nothing rendered (zero DOM footprint)

import type { ViewportOverlay } from "@/types/workbench_frame";

interface DynamicViewportOverlaysProps {
  overlays: ViewportOverlay[];
}

const SEVERITY_RING: Record<ViewportOverlay["severity"], string> = {
  info: "border-sky-700/60 bg-sky-950/70 text-sky-200",
  warn: "border-amber-700/60 bg-amber-950/70 text-amber-200",
  fail: "border-rose-700/60 bg-rose-950/70 text-rose-200",
};

export function DynamicViewportOverlays({
  overlays,
}: DynamicViewportOverlaysProps) {
  if (overlays.length === 0) return null;

  return (
    <div
      data-testid="dynamic-viewport-overlays"
      className="pointer-events-none absolute right-3 top-3 z-10 flex flex-col gap-1.5"
    >
      {overlays.map((overlay, i) => (
        <div
          key={`${overlay.kind}-${overlay.target ?? ""}-${i}`}
          data-testid="viewport-overlay"
          data-kind={overlay.kind}
          data-severity={overlay.severity}
          className={`pointer-events-auto inline-flex items-center gap-1.5 rounded-sm border px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider ${SEVERITY_RING[overlay.severity]}`}
        >
          <OverlayIcon kind={overlay.kind} />
          <span>{overlay.label ?? overlay.target ?? overlay.kind}</span>
        </div>
      ))}
    </div>
  );
}

function OverlayIcon({ kind }: { kind: ViewportOverlay["kind"] }) {
  switch (kind) {
    case "patch_highlight":
      return <span aria-hidden>◇</span>;
    case "region_highlight":
      return <span aria-hidden>▣</span>;
    case "cell_count_badge":
      return <span aria-hidden>#</span>;
    case "checkmesh_warn":
      return <span aria-hidden>⚠</span>;
    default:
      return null;
  }
}
