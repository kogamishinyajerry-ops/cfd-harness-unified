// Regression: Codex round-8 P1 (2026-04-30). Step 3 dialog state must
// survive the TaskPanel remount that happens whenever the engineer
// navigates to another step. The provider sits at shell scope and
// only resets on caseId change.

import { describe, expect, it } from "vitest";
import { render, screen, act } from "@testing-library/react";
import { useState } from "react";

import {
  Step3StateProvider,
  useStep3State,
} from "../Step3StateContext";

function StateInspector({ label }: { label: string }) {
  const { envelope, pickedFaceIdForQuestion, activeFaceQuestionId } =
    useStep3State();
  return (
    <ul data-testid={`inspector-${label}`}>
      <li data-testid={`envelope-${label}`}>
        {envelope ? envelope.summary : "null"}
      </li>
      <li data-testid={`picks-${label}`}>
        {Object.entries(pickedFaceIdForQuestion)
          .map(([k, v]) => `${k}=${v}`)
          .join(",") || "empty"}
      </li>
      <li data-testid={`active-${label}`}>
        {activeFaceQuestionId ?? "null"}
      </li>
    </ul>
  );
}

function StateMutator() {
  const {
    setEnvelope,
    setPickedFaceIdForQuestion,
    setActiveFaceQuestionId,
  } = useStep3State();
  return (
    <button
      type="button"
      data-testid="mutate"
      onClick={() => {
        setEnvelope({
          confidence: "uncertain",
          summary: "test-summary",
          annotations_revision_consumed: 1,
          annotations_revision_after: 1,
          unresolved_questions: [],
          next_step_suggestion: null,
          error_detail: null,
        });
        setPickedFaceIdForQuestion((prev) => ({
          ...prev,
          q1: "fid_lid",
        }));
        setActiveFaceQuestionId("q1");
      }}
    >
      mutate
    </button>
  );
}

// Mimics TaskPanel's behaviour: a parent that mounts/unmounts the
// inspector based on a "current step" toggle. The provider stays
// mounted at the parent above this; we want to prove that values
// written before the unmount survive after the remount.
function RemountHarness({ caseId }: { caseId: string }) {
  const [showStep3, setShowStep3] = useState(true);
  return (
    <Step3StateProvider caseId={caseId}>
      <button
        type="button"
        data-testid="toggle"
        onClick={() => setShowStep3((prev) => !prev)}
      >
        toggle
      </button>
      {showStep3 ? (
        <>
          <StateMutator />
          <StateInspector label="step3" />
        </>
      ) : (
        <span data-testid="step-other">on a different step</span>
      )}
    </Step3StateProvider>
  );
}

describe("Step3StateContext", () => {
  it("survives child unmount/remount (the navigate-away regression)", () => {
    render(<RemountHarness caseId="abc" />);

    // Set state.
    act(() => {
      screen.getByTestId("mutate").click();
    });
    expect(screen.getByTestId("envelope-step3")).toHaveTextContent(
      "test-summary",
    );
    expect(screen.getByTestId("picks-step3")).toHaveTextContent(
      "q1=fid_lid",
    );
    expect(screen.getByTestId("active-step3")).toHaveTextContent("q1");

    // Navigate away (unmounts Step3 children).
    act(() => {
      screen.getByTestId("toggle").click();
    });
    expect(screen.getByTestId("step-other")).toBeInTheDocument();
    expect(screen.queryByTestId("inspector-step3")).toBeNull();

    // Navigate back (remounts).
    act(() => {
      screen.getByTestId("toggle").click();
    });

    // State must still be present — pre-fix it would all be reset.
    expect(screen.getByTestId("envelope-step3")).toHaveTextContent(
      "test-summary",
    );
    expect(screen.getByTestId("picks-step3")).toHaveTextContent(
      "q1=fid_lid",
    );
    expect(screen.getByTestId("active-step3")).toHaveTextContent("q1");
  });

  it("resets when caseId changes", () => {
    const { rerender } = render(<RemountHarness caseId="abc" />);
    act(() => {
      screen.getByTestId("mutate").click();
    });
    expect(screen.getByTestId("envelope-step3")).toHaveTextContent(
      "test-summary",
    );

    // Switching to a different case must wipe the previous case's state.
    rerender(<RemountHarness caseId="xyz" />);
    expect(screen.getByTestId("envelope-step3")).toHaveTextContent("null");
    expect(screen.getByTestId("picks-step3")).toHaveTextContent("empty");
    expect(screen.getByTestId("active-step3")).toHaveTextContent("null");
  });
});
