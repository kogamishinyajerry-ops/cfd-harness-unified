// Right rail · per-step task panel. Renders the active step's body +
// the shared StepNavigation row.
//
// DEC-V61-116: a CompletenessCard pins to the top of the scrollable
// Body, surfacing "距离入库标准还差 N 项" + status pill + missing
// fields list. Independent of the active step — drives the engineer's
// archive-readiness awareness on every step.
//
// DEC-V61-120: an AICoachPanel pins to the BOTTOM of the right rail
// (above StepNavigation), giving the engineer an always-visible chat
// surface to ask the LLM about case completeness. Read-only adviser
// in V120; tool-calling + action-approval lands in V61-121.

import type { ComponentType } from "react";

import { AICoachPanel } from "./AICoachPanel";
import { CompletenessCard } from "./CompletenessCard";
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
      <div className="flex-1 min-h-0 overflow-y-auto">
        {caseId && <CompletenessCard caseId={caseId} />}
        <Body
          caseId={caseId}
          onStepComplete={onStepComplete}
          onStepError={onStepError}
          registerAiAction={registerAiAction}
        />
      </div>
      {caseId && <AICoachPanel key={caseId} caseId={caseId} />}
      <StepNavigation
        {...navigation}
        aiActionDeferredTooltip={step.aiActionDeferredTooltip}
      />
    </aside>
  );
}
