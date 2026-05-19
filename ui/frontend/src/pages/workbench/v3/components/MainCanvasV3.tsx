/**
 * V71-UI-V3 / V76 · MainCanvasV3 · viewport router
 *
 * V71 used SVG placeholders for every mode. V76 wires real WebGL vtk.js
 * for geometry + mesh modes (Pillar 15 · 3D Visualization Fidelity) and
 * keeps the substrate placeholders for bc / field / residuals / report
 * (those are 2D / chart surfaces, not 3D scenes).
 */
import type { StepId, ViewportMode } from "../WorkbenchShellV3";
import { GeometryPlaceholder } from "./canvas/GeometryPlaceholder";
import { BCPlaceholder } from "./canvas/BCPlaceholder";
import { ResidualsChartV3 } from "./canvas/ResidualsChartV3";
import { ReportComparisonV3 } from "./canvas/ReportComparisonV3";
import { EmptyCanvasV3 } from "./canvas/EmptyCanvasV3";
import { VtkCanvasV3 } from "./canvas/VtkCanvasV3";

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
      return <VtkCanvasV3 caseId={caseId} mode="geometry" />;
    case "mesh":
      return <VtkCanvasV3 caseId={caseId} mode="mesh" />;
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
