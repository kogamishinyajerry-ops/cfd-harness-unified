/**
 * V68-A.4 · Viewport mode dispatcher
 *
 * Surfaces the 6 canonical viewport modes per Blueprint v3 §4:
 *   - geometry        (default for Step 1 Import)
 *   - mesh-wireframe  (default for Step 2 Mesh)
 *   - bc-faces        (default for Step 3 SetupBC)
 *   - field-slice     (default for Step 4 SolveRun · mid-run preview)
 *   - residuals       (default for Step 4 SolveRun · convergence chart)
 *   - report-grid     (default for Step 5 ResultsView)
 *
 * The current mode is exposed via `data-viewport-mode` on a wrapper div so
 * Playwright e2e tests can assert mode-state without scraping the vtk.js
 * canvas. Mode changes are deterministic + side-effect-free here; the
 * actual render switch is wired in V68-A.5 (consumer side).
 */
import { useMemo, useState, type ReactNode } from "react";

export type ViewportMode =
  | "geometry"
  | "mesh-wireframe"
  | "bc-faces"
  | "field-slice"
  | "residuals"
  | "report-grid";

export const VIEWPORT_MODES: readonly ViewportMode[] = [
  "geometry",
  "mesh-wireframe",
  "bc-faces",
  "field-slice",
  "residuals",
  "report-grid",
] as const;

const STEP_DEFAULT_MODE: Record<string, ViewportMode> = {
  "1": "geometry",
  "2": "mesh-wireframe",
  "3": "bc-faces",
  "4": "residuals",
  "5": "report-grid",
};

export function defaultModeForStep(stepId: string | number | null | undefined): ViewportMode {
  const key = String(stepId ?? "1");
  return STEP_DEFAULT_MODE[key] ?? "geometry";
}

const MODE_LABEL: Record<ViewportMode, string> = {
  geometry: "Geometry",
  "mesh-wireframe": "Mesh",
  "bc-faces": "BC",
  "field-slice": "Field",
  residuals: "Residuals",
  "report-grid": "Report",
};

interface ViewportModeDispatcherProps {
  /** Current 5-step pipeline step (1..5) · drives default mode. */
  stepId?: string | number | null;
  /** User-override mode (e.g. inspecting mesh while on Step 4). */
  overrideMode?: ViewportMode | null;
  /** Render children inside the data-viewport-mode wrapper. */
  children?: ReactNode;
  testIdPrefix?: string;
}

export function ViewportModeDispatcher({
  stepId,
  overrideMode,
  children,
  testIdPrefix,
}: ViewportModeDispatcherProps) {
  const stepDefault = useMemo(() => defaultModeForStep(stepId), [stepId]);
  const [userMode, setUserMode] = useState<ViewportMode | null>(null);
  const effective = overrideMode ?? userMode ?? stepDefault;
  const prefix = testIdPrefix ?? "viewport-mode";

  return (
    <div
      data-testid={`${prefix}-dispatcher`}
      data-viewport-mode={effective}
      data-viewport-step={String(stepId ?? "")}
      className="relative flex h-full flex-col"
    >
      <div
        data-testid={`${prefix}-toolbar`}
        className="flex items-center gap-1 border-b border-surface-800 bg-surface-950/60 px-2 py-1 text-[10px]"
      >
        {VIEWPORT_MODES.map((m) => (
          <button
            key={m}
            type="button"
            data-testid={`${prefix}-button-${m}`}
            data-active={m === effective ? "true" : "false"}
            onClick={() => setUserMode(m === effective ? null : m)}
            className={`rounded px-1.5 py-0.5 transition ${
              m === effective
                ? "bg-emerald-900/40 text-emerald-300"
                : "text-surface-400 hover:bg-surface-800"
            }`}
          >
            {MODE_LABEL[m]}
          </button>
        ))}
      </div>
      <div className="min-h-0 flex-1">{children}</div>
    </div>
  );
}
