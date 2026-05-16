/**
 * V71-UI-V3 · ViewportToolbarV3 · 36px row with 6 viewport mode selectors
 * Per Image 01/02-08: "Geometry · Mesh · BC · Field · Residuals · Report"
 * separated by "·" dots. Active mode has sand-coral underline. Cross-step
 * hint visible to right when engineer overrode default mode for step.
 */
import type { StepId, ViewportMode } from "../WorkbenchShellV3";

const MODES: { id: ViewportMode; label: string }[] = [
  { id: "geometry", label: "Geometry" },
  { id: "mesh", label: "Mesh" },
  { id: "bc", label: "BC" },
  { id: "field", label: "Field" },
  { id: "residuals", label: "Residuals" },
  { id: "report", label: "Report" },
];

const DEFAULT_FOR_STEP: Record<StepId, ViewportMode> = {
  1: "geometry",
  2: "mesh",
  3: "bc",
  4: "residuals",
  5: "report",
};

interface ViewportToolbarV3Props {
  activeMode: ViewportMode;
  onSetMode: (m: ViewportMode) => void;
  activeStep: StepId;
}

export function ViewportToolbarV3({
  activeMode,
  onSetMode,
  activeStep,
}: ViewportToolbarV3Props) {
  const isCrossStep = activeMode !== DEFAULT_FOR_STEP[activeStep];

  return (
    <div
      data-testid="viewport-toolbar-v3"
      data-v71-ui-shell="true"
      data-viewport-mode={activeMode}
      className="h-9 flex items-center px-4 border-b border-v3-border text-[13px]"
    >
      {MODES.map((m, idx) => {
        const isActive = m.id === activeMode;
        return (
          <span key={m.id} className="flex items-center">
            <button
              type="button"
              onClick={() => onSetMode(m.id)}
              data-testid={`viewport-mode-${m.id}`}
              data-active={isActive ? "true" : "false"}
              aria-pressed={isActive}
              aria-label={`Viewport mode: ${m.label}`}
              className={`relative px-2 py-0.5 motion-safe:transition-colors motion-safe:duration-150 ${
                isActive
                  ? "text-v3-textPrimary"
                  : "text-v3-textSecondary hover:text-v3-textPrimary"
              }`}
            >
              {m.label}
              {isActive && (
                <span
                  aria-hidden
                  className="absolute left-2 right-2 -bottom-[1px] h-[1.5px] bg-v3-accent"
                />
              )}
            </button>
            {idx < MODES.length - 1 && (
              <span className="text-v3-textTertiary mx-1">·</span>
            )}
          </span>
        );
      })}
      <div className="flex-1" />
      {isCrossStep && (
        <span
          data-testid="cross-step-hint"
          className="text-v3-textTertiary text-[11px] mr-3"
        >
          viewing {activeMode} while Step {activeStep} {activeStep === 4 ? "solves" : "active"}
        </span>
      )}
      <div className="flex items-center gap-2 text-v3-textTertiary text-[12px]">
        <span aria-label="fullscreen">⛶</span>
        <span aria-label="reset view">↻</span>
        <span aria-label="lock camera">⌖</span>
      </div>
    </div>
  );
}
