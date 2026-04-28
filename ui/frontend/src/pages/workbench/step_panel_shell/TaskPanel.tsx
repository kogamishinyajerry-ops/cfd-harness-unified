// Right rail · per-step task panel. Renders the active step's body +
// the shared StepNavigation row.

import type { ComponentType } from "react";

import { StepNavigation } from "./StepNavigation";
import type {
  StepDef,
  StepNavigationContract,
  StepTaskPanelProps,
} from "./types";

interface TaskPanelProps {
  step: StepDef;
  caseId: string;
  onStepComplete: () => void;
  onStepError: (message: string) => void;
  registerAiAction: (action: (() => Promise<void>) | null) => void;
  navigation: StepNavigationContract;
}

export function TaskPanel({
  step,
  caseId,
  onStepComplete,
  onStepError,
  registerAiAction,
  navigation,
}: TaskPanelProps) {
  const Body = step.taskPanelComponent as ComponentType<StepTaskPanelProps>;
  return (
    <aside
      aria-label={`Task panel · ${step.longLabel}`}
      data-testid="task-panel"
      data-step-id={step.id}
      className="flex h-full min-h-0 flex-col border-l border-surface-800 bg-surface-950/40"
    >
      <header className="border-b border-surface-800 px-3 py-2">
        <h2 className="text-xs font-mono uppercase tracking-wider text-surface-300">
          {step.longLabel}
        </h2>
      </header>
      <div className="flex-1 overflow-y-auto">
        <Body
          caseId={caseId}
          onStepComplete={onStepComplete}
          onStepError={onStepError}
          registerAiAction={registerAiAction}
        />
      </div>
      <StepNavigation
        {...navigation}
        aiActionDeferredTooltip={step.aiActionDeferredTooltip}
      />
    </aside>
  );
}
