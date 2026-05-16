/**
 * V71-UI-V3 · PipelineStripV3 · 5-step pipeline tab strip
 * Per Image 01/02/03/04/05/07/08: chevron-separated step pills, status dots
 * (filled=passes / half=active / empty=pending), sand-coral underline on
 * active step.
 */
import type { StepId } from "../WorkbenchShellV3";

const STEPS: { id: StepId; label: string }[] = [
  { id: 1, label: "Import" },
  { id: 2, label: "Mesh" },
  { id: 3, label: "Setup BC" },
  { id: 4, label: "Solve" },
  { id: 5, label: "Results" },
];

interface PipelineStripV3Props {
  activeStep: StepId;
  onSetStep: (s: StepId) => void;
  caseId: string | null;
}

export function PipelineStripV3({
  activeStep,
  onSetStep,
  caseId,
}: PipelineStripV3Props) {
  return (
    <div
      data-testid="pipeline-strip-v3"
      data-v71-ui-shell="true"
      className="h-11 flex items-center px-4 border-b border-v3-border"
    >
      {STEPS.map((s, idx) => {
        const isActive = s.id === activeStep;
        const isPassed = s.id < activeStep && caseId !== null;
        const dotColor = isActive
          ? "bg-v3-accent"
          : isPassed
          ? "bg-v3-inlet"
          : "bg-v3-textTertiary/40";
        return (
          <span key={s.id} className="flex items-center">
            <button
              type="button"
              onClick={() => onSetStep(s.id)}
              data-testid={`pipeline-step-${s.id}`}
              data-state={isActive ? "active" : isPassed ? "passed" : "pending"}
              className={`relative flex items-center gap-2 px-2 py-1 text-[14px] ${
                isActive
                  ? "text-v3-textPrimary"
                  : "text-v3-textSecondary hover:text-v3-textPrimary"
              }`}
            >
              <span className="font-mono text-[11px] text-v3-textTertiary">
                {s.id}
              </span>
              <span>{s.label}</span>
              <span
                aria-hidden
                className={`inline-block w-2 h-2 rounded-full ${dotColor}`}
              />
              {isActive && (
                <span
                  aria-hidden
                  className="absolute left-2 right-2 -bottom-[1px] h-[2px] bg-v3-accent"
                />
              )}
            </button>
            {idx < STEPS.length - 1 && (
              <span className="mx-2 text-v3-textTertiary text-[14px]">›</span>
            )}
          </span>
        );
      })}
    </div>
  );
}
