/**
 * V4 · MainCanvas · 8-mode switcher · Phase C real viewport wiring.
 *
 * Geometry / Mesh / Boundary modes now wrap the real vtk.js viewport
 * (ViewportV4) layered over the SVG IndustrialBoxScene fallback. The
 * viewport mounts only when a glb probe confirms availability, so
 * curated cases without imported geometry (LDC, tutorials) still
 * show the stylised SVG scene rather than a 404 spinner.
 *
 * Other modes (import / physics / solver / post / doe) remain pure
 * SVG — adding a 3D viewport there carries no information without
 * volume rendering or contour plots, which are later arcs.
 *
 * Camera preset state is lifted here so the Top-right preset chips
 * stay mounted across modes and drive a single source-of-truth into
 * whichever mode is currently rendering a viewport.
 */
import { useState } from "react";

import { ModeRendererBoundary } from "./modes/ModeRendererBoundary";
import { ModeRendererDoe } from "./modes/ModeRendererDoe";
import { ModeRendererGeometry } from "./modes/ModeRendererGeometry";
import { ModeRendererImport } from "./modes/ModeRendererImport";
import { ModeRendererMesh } from "./modes/ModeRendererMesh";
import { ModeRendererPhysics } from "./modes/ModeRendererPhysics";
import { ModeRendererPost } from "./modes/ModeRendererPost";
import { ModeRendererSolver } from "./modes/ModeRendererSolver";
import type { V4CameraPreset } from "./ViewportV4";
import type { V4PipelineStepId } from "@/theme/industrial_minimalist";

interface MainCanvasV4Props {
  activeStep: V4PipelineStepId;
  caseId?: string;
}

const PRESET_LABEL: Record<V4CameraPreset, string> = {
  front: "前",
  top: "顶",
  iso: "轴侧",
};

const PRESET_TITLE: Record<V4CameraPreset, string> = {
  front: "正视图",
  top: "俯视图",
  iso: "轴侧视图",
};

function renderForStep(
  step: V4PipelineStepId,
  caseId: string | undefined,
  cameraPreset: V4CameraPreset,
) {
  switch (step) {
    case "import":
      return <ModeRendererImport />;
    case "geometry":
      return (
        <ModeRendererGeometry caseId={caseId} cameraPreset={cameraPreset} />
      );
    case "mesh":
      return <ModeRendererMesh caseId={caseId} cameraPreset={cameraPreset} />;
    case "physics":
      return (
        <ModeRendererPhysics caseId={caseId} cameraPreset={cameraPreset} />
      );
    case "boundary":
      return (
        <ModeRendererBoundary caseId={caseId} cameraPreset={cameraPreset} />
      );
    case "solver":
      return <ModeRendererSolver caseId={caseId} cameraPreset={cameraPreset} />;
    case "post":
      return <ModeRendererPost caseId={caseId} cameraPreset={cameraPreset} />;
    case "doe":
      return <ModeRendererDoe />;
  }
}

export function MainCanvasV4({ activeStep, caseId }: MainCanvasV4Props) {
  const [cameraPreset, setCameraPreset] = useState<V4CameraPreset>("iso");

  return (
    <section
      className="relative flex min-h-0 flex-1 flex-col overflow-hidden bg-v4-canvas"
      data-testid="maincanvas-v4"
      data-active-step={activeStep}
      data-case-id={caseId ?? "__none__"}
      data-camera-preset={cameraPreset}
    >
      {renderForStep(activeStep, caseId, cameraPreset)}

      {/* Camera preset overlay · top-right · stable across modes */}
      <div
        className="pointer-events-auto absolute right-3 top-3 flex gap-1 rounded border border-v4-border bg-v4-surfaceRaised/95 px-1 py-0.5 text-[10px] text-v4-textSecondary"
        data-testid="maincanvas-v4-camera-presets"
      >
        {(Object.keys(PRESET_LABEL) as V4CameraPreset[]).map((p) => {
          const isActive = p === cameraPreset;
          return (
            <button
              key={p}
              type="button"
              onClick={() => setCameraPreset(p)}
              className={[
                "rounded px-1.5 py-0.5 transition-colors",
                isActive
                  ? "bg-v4-canvas text-v4-textPrimary"
                  : "hover:text-v4-textPrimary",
              ].join(" ")}
              title={PRESET_TITLE[p]}
              data-testid={`maincanvas-v4-camera-preset-${p}`}
              data-active={isActive ? "true" : "false"}
            >
              {PRESET_LABEL[p]}
            </button>
          );
        })}
      </div>
    </section>
  );
}
