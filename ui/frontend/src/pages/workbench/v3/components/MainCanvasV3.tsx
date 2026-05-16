/**
 * V71-UI-V3 · MainCanvasV3 · placeholder canvas that switches content by
 * (stepId, viewportMode). Per Images 02-08.
 *
 * V71 scope: render canonical placeholders for each (step, mode) combo —
 * NOT a full WebGL 3D viewport. The placeholders show what each surface
 * communicates (e.g., "geometry wireframe" / "residuals chart") at
 * Claude-tier polish without backend dependencies.
 *
 * V72+: replace each placeholder with real renderers (vtk.js / chart libs).
 */
import type { StepId, ViewportMode } from "../WorkbenchShellV3";
import { GeometryPlaceholder } from "./canvas/GeometryPlaceholder";
import { MeshPlaceholder } from "./canvas/MeshPlaceholder";
import { BCPlaceholder } from "./canvas/BCPlaceholder";
import { ResidualsChartV3 } from "./canvas/ResidualsChartV3";
import { ReportComparisonV3 } from "./canvas/ReportComparisonV3";
import { EmptyCanvasV3 } from "./canvas/EmptyCanvasV3";

interface MainCanvasV3Props {
  caseId: string | null;
  stepId: StepId;
  viewportMode: ViewportMode;
}

export function MainCanvasV3({
  caseId,
  stepId,
  viewportMode,
}: MainCanvasV3Props) {
  if (!caseId) {
    return <EmptyCanvasV3 />;
  }
  switch (viewportMode) {
    case "geometry":
      return <GeometryPlaceholder caseId={caseId} />;
    case "mesh":
      return <MeshPlaceholder caseId={caseId} />;
    case "bc":
      return <BCPlaceholder caseId={caseId} />;
    case "field":
      return <GeometryPlaceholder caseId={caseId} variant="field" />;
    case "residuals":
      return <ResidualsChartV3 caseId={caseId} />;
    case "report":
      return <ReportComparisonV3 caseId={caseId} stepId={stepId} />;
    default:
      return <EmptyCanvasV3 />;
  }
}
