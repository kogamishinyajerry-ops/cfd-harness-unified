// Persists Step 3 dialog state across step navigation (Codex round-8
// P1, 2026-04-30). TaskPanel remounts the active step's body on every
// step change, so anything held in Step3SetupBC's local useState
// disappears the moment the engineer clicks Step 1/2/4/5 in the
// StepTree. With envelope mode now unconditional (round-2 P1), losing
// `envelope` + `pickedFaceIdForQuestion` + `activeFaceQuestionId`
// means a partially-answered uncertain dialog gets wiped by an
// accidental click — the engineer has to re-pick faces and re-type
// labels from scratch. Lifting these three pieces of state into a
// shell-scoped provider survives the unmount.
//
// Scope: state is keyed implicitly by caseId via the provider remount
// path — when the engineer navigates to a different case, the whole
// StepPanelShell tree re-renders with a new caseId, and the useEffect
// below resets the state. Other transient UI state (rejection,
// networkError, annotations) stays local in Step3SetupBC: it's either
// re-fetchable on remount (annotations) or only meaningful immediately
// after a click (rejection/networkError).

import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import type { AIActionEnvelope } from "./types";

interface Step3StateContextValue {
  envelope: AIActionEnvelope | null;
  setEnvelope: (next: AIActionEnvelope | null) => void;
  pickedFaceIdForQuestion: Record<string, string>;
  setPickedFaceIdForQuestion: React.Dispatch<
    React.SetStateAction<Record<string, string>>
  >;
  activeFaceQuestionId: string | null;
  setActiveFaceQuestionId: (next: string | null) => void;
}

const Step3StateContext = createContext<Step3StateContextValue | null>(null);

export function Step3StateProvider({
  caseId,
  children,
}: {
  caseId: string;
  children: ReactNode;
}) {
  const [envelope, setEnvelope] = useState<AIActionEnvelope | null>(null);
  const [pickedFaceIdForQuestion, setPickedFaceIdForQuestion] = useState<
    Record<string, string>
  >({});
  const [activeFaceQuestionId, setActiveFaceQuestionId] = useState<
    string | null
  >(null);

  // Reset when the engineer navigates to a different case_id. The
  // workbench URL is /workbench/case/:caseId so a case switch keeps
  // StepPanelShell mounted but flips the param; without this reset
  // the previous case's envelope would leak into the new case.
  useEffect(() => {
    setEnvelope(null);
    setPickedFaceIdForQuestion({});
    setActiveFaceQuestionId(null);
  }, [caseId]);

  const value = useMemo(
    () => ({
      envelope,
      setEnvelope,
      pickedFaceIdForQuestion,
      setPickedFaceIdForQuestion,
      activeFaceQuestionId,
      setActiveFaceQuestionId,
    }),
    [envelope, pickedFaceIdForQuestion, activeFaceQuestionId],
  );
  return (
    <Step3StateContext.Provider value={value}>
      {children}
    </Step3StateContext.Provider>
  );
}

export function useStep3State(): Step3StateContextValue {
  const ctx = useContext(Step3StateContext);
  if (ctx === null) {
    throw new Error(
      "useStep3State must be used inside a <Step3StateProvider>",
    );
  }
  return ctx;
}
