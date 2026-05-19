import {
  V4_PIPELINE_STEPS,
  type V4PipelineStepId,
} from "@/theme/industrial_minimalist";

import {
  V4_VIEWPORT_MODES,
  viewportModeEnglishLabel,
} from "./crossStepBlueprint";

interface ViewportModeToolbarV4Props {
  activeStep: V4PipelineStepId;
  viewportMode: V4PipelineStepId;
  onViewportModeChange: (mode: V4PipelineStepId) => void;
}

function stepLabel(step: V4PipelineStepId): string {
  return V4_PIPELINE_STEPS.find((item) => item.id === step)?.label ?? step;
}

export function ViewportModeToolbarV4({
  activeStep,
  viewportMode,
  onViewportModeChange,
}: ViewportModeToolbarV4Props) {
  const isCrossStep = activeStep !== viewportMode;
  const isSolverCrossStep = activeStep === "solver";
  const hint = isCrossStep
    ? isSolverCrossStep
      ? `viewing ${viewportModeEnglishLabel(viewportMode)} while ${stepLabel(activeStep)} solves`
      : `viewing ${viewportModeEnglishLabel(viewportMode)} while pipeline stays on ${stepLabel(activeStep)}`
    : "视图跟随当前 pipeline";

  return (
    <div
      className="flex h-8 w-full items-center gap-2 overflow-hidden border-b border-v4-border bg-v4-surfaceRaised/95 px-3 text-[10px] text-v4-textSecondary"
      data-testid="v4-viewport-mode-toolbar"
      data-active-step={activeStep}
      data-viewport-mode={viewportMode}
      data-cross-step={isCrossStep ? "true" : "false"}
    >
      <span className="shrink-0 text-v4-textTertiary">视图层</span>
      <div className="flex items-center gap-0.5">
        {V4_VIEWPORT_MODES.map((mode) => {
          const isActive = mode.id === viewportMode;
          return (
            <button
              key={mode.id}
              type="button"
              onClick={() => onViewportModeChange(mode.id)}
              className={[
                "rounded px-1.5 py-0.5 transition-colors",
                isActive
                  ? "bg-v4-canvas text-v4-textPrimary"
                  : "text-v4-textSecondary hover:text-v4-textPrimary",
              ].join(" ")}
              title={mode.description}
              data-testid={`v4-viewport-mode-${mode.id}`}
              data-active={isActive ? "true" : "false"}
            >
              {mode.label}
            </button>
          );
        })}
      </div>
      <span
        className={[
          "hidden min-w-0 truncate border-l border-v4-border pl-2 font-mono sm:inline",
          isCrossStep ? "text-v4-active" : "text-v4-textTertiary",
        ].join(" ")}
        data-testid={isCrossStep ? "v4-cross-step-hint" : "v4-viewport-mode-hint"}
      >
        {hint}
      </span>
      <span className="shrink-0 border-l border-v4-border pl-2 text-v4-textTertiary">
        仅切换视图
      </span>
    </div>
  );
}
