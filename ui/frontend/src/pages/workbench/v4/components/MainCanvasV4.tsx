/**
 * V4 · MainCanvas · 8-mode switcher · Phase C real viewport wiring.
 *
 * Geometry / Mesh / Boundary modes now wrap the real vtk.js viewport
 * (ViewportV4) layered over the SVG IndustrialBoxScene fallback. The
 * viewport mounts only when a glb probe confirms availability, so
 * curated cases without imported geometry (LDC, tutorials) still
 * show the stylised SVG scene rather than a 404 spinner.
 *
 * Import / Geometry / Mesh / Boundary / Solver / Post can mount the real
 * vtk.js viewport when a page-level blueprint needs CAD or field context.
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
import {
  V4_PALETTE,
  type V4PipelineStepId,
} from "@/theme/industrial_minimalist";
import { CROSS_STEP_BLUEPRINT_DOCK } from "./crossStepBlueprint";
import { ViewportModeToolbarV4 } from "./ViewportModeToolbarV4";

interface MainCanvasV4Props {
  activeStep: V4PipelineStepId;
  viewportMode?: V4PipelineStepId;
  onViewportModeChange?: (mode: V4PipelineStepId) => void;
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
      return <ModeRendererImport caseId={caseId} cameraPreset={cameraPreset} />;
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

function CrossStepResidualDock() {
  return (
    <div
      className="pointer-events-auto absolute bottom-3 left-3 z-20 w-[280px] rounded border border-v4-border bg-v4-surfaceRaised/95 p-2 shadow-lg backdrop-blur"
      data-testid="v4-cross-step-residual-dock"
      data-active-step={CROSS_STEP_BLUEPRINT_DOCK.activeStep}
      data-viewport-mode={CROSS_STEP_BLUEPRINT_DOCK.viewportMode}
      data-content={CROSS_STEP_BLUEPRINT_DOCK.content}
    >
      <div className="flex items-baseline justify-between">
        <span className="text-[10px] uppercase tracking-wider text-v4-textTertiary">
          Residuals dock
        </span>
        <span className="font-mono text-[10px] text-v4-active">
          solver still running
        </span>
      </div>
      <svg
        className="mt-1 h-12 w-full"
        viewBox="0 0 240 48"
        preserveAspectRatio="none"
        aria-hidden
      >
        {[10, 24, 38].map((y) => (
          <line
            key={y}
            x1="0"
            x2="240"
            y1={y}
            y2={y}
            stroke={V4_PALETTE.border}
            strokeWidth="0.6"
          />
        ))}
        <polyline
          points="0,8 32,14 64,17 96,23 128,27 160,32 192,37 240,42"
          fill="none"
          stroke={V4_PALETTE.active}
          strokeWidth="1.8"
          strokeLinecap="round"
        />
        <polyline
          points="0,15 32,18 64,22 96,25 128,30 160,35 192,39 240,44"
          fill="none"
          stroke={V4_PALETTE.brand}
          strokeWidth="1.2"
          strokeLinecap="round"
          opacity="0.75"
        />
      </svg>
      <div className="mt-1 text-[9px] text-v4-textTertiary">
        active step remains Solver · Mesh viewport inspection does not interrupt
      </div>
    </div>
  );
}

export function MainCanvasV4({
  activeStep,
  viewportMode = activeStep,
  onViewportModeChange,
  caseId,
}: MainCanvasV4Props) {
  const [cameraPreset, setCameraPreset] = useState<V4CameraPreset>("iso");
  const cameraPresetPositionClass =
    viewportMode === "import" ? "right-[232px] top-[108px]" : "right-3 top-10";
  const isSolverMeshCrossStep =
    activeStep === "solver" && viewportMode === "mesh";

  return (
    <section
      className="relative flex min-h-0 flex-1 flex-col overflow-hidden bg-v4-canvas"
      data-testid="maincanvas-v4"
      data-active-step={activeStep}
      data-viewport-mode={viewportMode}
      data-cross-step={activeStep !== viewportMode ? "true" : "false"}
      data-case-id={caseId ?? "__none__"}
      data-camera-preset={cameraPreset}
    >
      {onViewportModeChange && (
        <div
          className="shrink-0"
          data-testid="v4-viewport-mode-toolbar-frame"
        >
          <ViewportModeToolbarV4
            activeStep={activeStep}
            viewportMode={viewportMode}
            onViewportModeChange={onViewportModeChange}
          />
        </div>
      )}

      <div
        className="relative min-h-0 flex-1 overflow-hidden"
        data-testid="maincanvas-v4-viewport-slot"
      >
        {renderForStep(viewportMode, caseId, cameraPreset)}

        {isSolverMeshCrossStep && <CrossStepResidualDock />}

        {viewportMode !== "doe" && (
          <div
            className={[
              "pointer-events-auto absolute flex gap-1 rounded border border-v4-border bg-v4-surfaceRaised/95 px-1 py-0.5 text-[10px] text-v4-textSecondary",
              cameraPresetPositionClass,
            ].join(" ")}
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
        )}
      </div>
    </section>
  );
}
