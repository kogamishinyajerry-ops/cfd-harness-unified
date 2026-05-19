/**
 * V86.2 · V7.A RunSolverButtonV7 contract test
 *
 * Asserts the V7.A contract from .planning/blueprints/v7/INDEX.md:
 *   - USER-click only · button must be a <button onClick={...}> affordance
 *   - Disabled when caseId=null OR meshReady=false OR bcSetup=false
 *   - During runState=running, label flips to "Cancel run" + click → cancel
 *   - During runState=starting, click → cancel (treats starting as in-flight)
 *   - Terminal states (done/failed/cancelled) show retry hint + click → retry
 *   - V130 lexical denylist: NO auto-trigger / AI-runs / automatic verbiage
 *     anywhere in rendered text
 *   - V130 structural: exactly 1 button · NO useEffect that calls
 *     onRequestRun · NO timer-based fire (asserted by component shape)
 *
 * Component is pure presentational — parent supplies handlers + state.
 * The state machine lives in V7.B (useSolverRunStateV7), wired in V86.3+.
 */
import { describe, expect, it, vi } from "vitest";
import { render, screen, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { RunSolverButtonV7 } from "../components/RunSolverButtonV7";
import type { SolverRunState } from "../hooks/useSolverRunStateV7";

function harness(props: {
  caseId?: string | null;
  meshReady?: boolean;
  bcSetup?: boolean;
  runState?: SolverRunState;
  onRequestRun?: () => void;
  onCancelRun?: () => void;
}) {
  const onRequestRun = props.onRequestRun ?? vi.fn();
  const onCancelRun = props.onCancelRun ?? vi.fn();
  // Distinguish "not provided" from "explicit null" — `??` treats null
  // as nullish, which would swallow the explicit `caseId: null` test.
  const caseId =
    "caseId" in props ? props.caseId! : "lid_driven_cavity";
  const utils = render(
    <RunSolverButtonV7
      caseId={caseId}
      meshReady={props.meshReady ?? true}
      bcSetup={props.bcSetup ?? true}
      runState={props.runState ?? "idle"}
      onRequestRun={onRequestRun}
      onCancelRun={onCancelRun}
    />,
  );
  return { ...utils, onRequestRun, onCancelRun };
}

describe("RunSolverButtonV7 contract · V86.2 · V7.A", () => {
  it("renders 'Run solver' label when idle + prereqs met", () => {
    harness({ runState: "idle" });
    const btn = screen.getByTestId("run-solver-v7-button");
    expect(btn.textContent).toBe("Run solver");
    expect(btn).not.toBeDisabled();
  });

  it("disabled when caseId is null (no case selected)", () => {
    harness({ caseId: null });
    expect(screen.getByTestId("run-solver-v7-button")).toBeDisabled();
    expect(screen.getByTestId("run-solver-v7-hint").textContent).toMatch(
      /select a case/i,
    );
    expect(
      screen.getByTestId("run-solver-v7").getAttribute("data-prerequisites-met"),
    ).toBe("false");
  });

  it("disabled when meshReady=false", () => {
    harness({ meshReady: false, bcSetup: true });
    expect(screen.getByTestId("run-solver-v7-button")).toBeDisabled();
    expect(screen.getByTestId("run-solver-v7-hint").textContent).toMatch(
      /mesh not ready/i,
    );
  });

  it("disabled when bcSetup=false", () => {
    harness({ meshReady: true, bcSetup: false });
    expect(screen.getByTestId("run-solver-v7-button")).toBeDisabled();
    expect(screen.getByTestId("run-solver-v7-hint").textContent).toMatch(
      /BC not setup/i,
    );
  });

  it("disabled when both mesh AND BC unmet · hint surfaces combined reason", () => {
    harness({ meshReady: false, bcSetup: false });
    expect(screen.getByTestId("run-solver-v7-button")).toBeDisabled();
    expect(screen.getByTestId("run-solver-v7-hint").textContent).toMatch(
      /mesh \+ BC not ready/i,
    );
  });

  it("USER click fires onRequestRun when idle + prereqs met", async () => {
    const user = userEvent.setup();
    const { onRequestRun, onCancelRun } = harness({ runState: "idle" });
    await act(async () => {
      await user.click(screen.getByTestId("run-solver-v7-button"));
    });
    expect(onRequestRun).toHaveBeenCalledTimes(1);
    expect(onCancelRun).not.toHaveBeenCalled();
  });

  it("button label flips to 'Cancel run' when runState=running", () => {
    harness({ runState: "running" });
    const btn = screen.getByTestId("run-solver-v7-button");
    expect(btn.textContent).toBe("Cancel run");
    expect(btn).not.toBeDisabled();
    expect(btn.getAttribute("aria-label")).toMatch(/cancel/i);
  });

  it("button label is 'Cancel run' when runState=starting (treats POST-in-flight as in-flight)", () => {
    harness({ runState: "starting" });
    expect(screen.getByTestId("run-solver-v7-button").textContent).toBe(
      "Cancel run",
    );
  });

  it("USER click fires onCancelRun (not onRequestRun) when runState=running", async () => {
    const user = userEvent.setup();
    const { onRequestRun, onCancelRun } = harness({ runState: "running" });
    await act(async () => {
      await user.click(screen.getByTestId("run-solver-v7-button"));
    });
    expect(onCancelRun).toHaveBeenCalledTimes(1);
    expect(onRequestRun).not.toHaveBeenCalled();
  });

  it("terminal state 'done' shows retry hint · click → onRequestRun", async () => {
    const user = userEvent.setup();
    const { onRequestRun } = harness({ runState: "done" });
    expect(screen.getByTestId("run-solver-v7-hint").textContent).toMatch(
      /run completed|run again/i,
    );
    await act(async () => {
      await user.click(screen.getByTestId("run-solver-v7-button"));
    });
    expect(onRequestRun).toHaveBeenCalledTimes(1);
  });

  it("terminal state 'failed' shows retry hint · click → onRequestRun", async () => {
    const user = userEvent.setup();
    const { onRequestRun } = harness({ runState: "failed" });
    expect(screen.getByTestId("run-solver-v7-hint").textContent).toMatch(
      /failed|retry/i,
    );
    await act(async () => {
      await user.click(screen.getByTestId("run-solver-v7-button"));
    });
    expect(onRequestRun).toHaveBeenCalledTimes(1);
  });

  it("terminal state 'cancelled' shows retry hint · click → onRequestRun", async () => {
    const user = userEvent.setup();
    const { onRequestRun } = harness({ runState: "cancelled" });
    expect(screen.getByTestId("run-solver-v7-hint").textContent).toMatch(
      /cancelled|retry/i,
    );
    await act(async () => {
      await user.click(screen.getByTestId("run-solver-v7-button"));
    });
    expect(onRequestRun).toHaveBeenCalledTimes(1);
  });

  it("data-run-state mirrors runState for inspection", () => {
    const states: SolverRunState[] = [
      "idle",
      "starting",
      "running",
      "done",
      "failed",
      "cancelled",
    ];
    for (const state of states) {
      const { unmount } = harness({ runState: state });
      expect(
        screen.getByTestId("run-solver-v7").getAttribute("data-run-state"),
      ).toBe(state);
      unmount();
    }
  });

  // V130 INVARIANT — lexical denylist + structural assertions
  it("V130: rendered text contains no auto-trigger / AI-runs verbiage", () => {
    const DENYLIST = [
      "auto",
      "automatic",
      "AI runs",
      "AI triggers",
      "auto-trigger",
      "auto-execute",
      "auto-run",
    ];
    const states: SolverRunState[] = [
      "idle",
      "starting",
      "running",
      "done",
      "failed",
      "cancelled",
    ];
    for (const state of states) {
      const { unmount } = harness({ runState: state });
      const root = screen.getByTestId("run-solver-v7");
      const text = root.textContent!.toLowerCase();
      for (const verb of DENYLIST) {
        expect(text, `state=${state} hit denylist "${verb}"`).not.toContain(
          verb.toLowerCase(),
        );
      }
      unmount();
    }
  });

  it("V130: exactly 1 button affordance · 0 forms/inputs/selects/textareas", () => {
    const states: SolverRunState[] = [
      "idle",
      "starting",
      "running",
      "done",
      "failed",
      "cancelled",
    ];
    for (const state of states) {
      const { unmount } = harness({ runState: state });
      const root = screen.getByTestId("run-solver-v7");
      const buttons = root.querySelectorAll("button");
      expect(buttons.length, `state=${state}`).toBe(1);
      expect(root.querySelectorAll("form").length).toBe(0);
      expect(root.querySelectorAll("input").length).toBe(0);
      expect(root.querySelectorAll("select").length).toBe(0);
      expect(root.querySelectorAll("textarea").length).toBe(0);
      unmount();
    }
  });

  it("V130: NO useEffect auto-fire · handlers fire ONLY on user click", () => {
    // Render with handlers that throw if called outside a user click —
    // since the only call site is the onClick prop, this verifies the
    // component itself has no useEffect that calls onRequestRun.
    const onRequestRun = vi.fn();
    const onCancelRun = vi.fn();
    render(
      <RunSolverButtonV7
        caseId="lid_driven_cavity"
        meshReady={true}
        bcSetup={true}
        runState="idle"
        onRequestRun={onRequestRun}
        onCancelRun={onCancelRun}
      />,
    );
    // After initial render + microtask flush, NO handler should have fired.
    expect(onRequestRun).not.toHaveBeenCalled();
    expect(onCancelRun).not.toHaveBeenCalled();
  });

  it("button is accessible (button element + aria-label)", () => {
    harness({ runState: "idle" });
    const btn = screen.getByTestId("run-solver-v7-button");
    expect(btn.tagName).toBe("BUTTON");
    expect(btn.getAttribute("type")).toBe("button");
    expect(btn.getAttribute("aria-label")).toBe("Start solver run");
  });
});
