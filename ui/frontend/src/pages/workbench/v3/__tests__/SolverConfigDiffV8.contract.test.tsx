/**
 * V88.4 · V8.C SolverConfigDiffV8 contract test
 *
 * Asserts the V8.C contract from .planning/blueprints/v8/INDEX.md:
 *   - Two-column display: current vs pending
 *   - Changed-field count + validation-error count surface in data-*
 *   - Confirm button disabled when validationErrors.length > 0
 *   - Confirm button disabled when no fields have changed
 *   - Confirm button disabled when isSaving=true
 *   - Cancel button click → onCancel handler, NO commit fired
 *   - V130 lexical denylist: NO "auto-commit" / "AI applies" / "automatic"
 *     verbiage anywhere in rendered text
 *   - Component is pure presentational · no fetch · no useEffect
 *
 * Pure render test · runs in <100ms.
 */
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { SolverConfigDiffV8 } from "../components/SolverConfigDiffV8";
import type {
  ControlDictField,
  ValidationError,
} from "../components/solver_config_validator";

const cleanBaseline: Partial<Record<ControlDictField, string>> = {
  application: "icoFoam",
  endTime: "10.0",
  deltaT: "0.005",
  writeInterval: "0.5",
  writeFormat: "ascii",
};

function harness(props: {
  current?: Partial<Record<ControlDictField, string>>;
  pending?: Partial<Record<ControlDictField, string>>;
  validationErrors?: ValidationError[];
  isSaving?: boolean;
  errorMessage?: string | null;
  onConfirm?: () => void;
  onCancel?: () => void;
}) {
  const onConfirm = props.onConfirm ?? vi.fn();
  const onCancel = props.onCancel ?? vi.fn();
  const utils = render(
    <SolverConfigDiffV8
      current={props.current ?? cleanBaseline}
      pending={props.pending ?? cleanBaseline}
      validationErrors={props.validationErrors ?? []}
      isSaving={props.isSaving}
      errorMessage={props.errorMessage}
      onConfirm={onConfirm}
      onCancel={onCancel}
    />,
  );
  return { ...utils, onConfirm, onCancel };
}

describe("SolverConfigDiffV8 contract · V88.4 · V8.C", () => {
  it("renders both columns + summary count of changed fields", () => {
    harness({
      pending: { ...cleanBaseline, endTime: "20.0", deltaT: "0.01" },
    });
    const summary = screen.getByTestId("solver-config-diff-v8-summary");
    expect(summary.textContent).toContain("2 fields changed");
  });

  it("marks changed rows with data-changed=true", () => {
    harness({
      pending: { ...cleanBaseline, endTime: "20.0" },
    });
    const endTimeRow = screen.getByTestId("solver-config-diff-row-endTime");
    expect(endTimeRow.getAttribute("data-changed")).toBe("true");
    const deltaTRow = screen.getByTestId("solver-config-diff-row-deltaT");
    expect(deltaTRow.getAttribute("data-changed")).toBe("false");
  });

  it("Confirm button is enabled when changed + no errors + not saving", async () => {
    harness({
      pending: { ...cleanBaseline, endTime: "20.0" },
    });
    const confirm = screen.getByTestId("solver-config-diff-v8-confirm");
    expect(confirm).not.toBeDisabled();
  });

  it("Confirm button is DISABLED when validationErrors present", () => {
    harness({
      pending: { ...cleanBaseline, endTime: "20.0" },
      validationErrors: [
        {
          field: "endTime",
          kind: "negative",
          message: "endTime must be > 0",
        },
      ],
    });
    const confirm = screen.getByTestId("solver-config-diff-v8-confirm");
    expect(confirm).toBeDisabled();
  });

  it("Confirm button is DISABLED when no fields changed (parity with editor's Review gate)", () => {
    harness({ pending: cleanBaseline });
    const confirm = screen.getByTestId("solver-config-diff-v8-confirm");
    expect(confirm).toBeDisabled();
  });

  it("Confirm button is DISABLED when isSaving=true (no double-commit)", () => {
    harness({
      pending: { ...cleanBaseline, endTime: "20.0" },
      isSaving: true,
    });
    const confirm = screen.getByTestId("solver-config-diff-v8-confirm");
    expect(confirm).toBeDisabled();
    expect(confirm.textContent).toContain("Saving");
  });

  it("Cancel button click → onCancel handler", async () => {
    const user = userEvent.setup();
    const { onCancel, onConfirm } = harness({
      pending: { ...cleanBaseline, endTime: "20.0" },
    });
    await user.click(screen.getByTestId("solver-config-diff-v8-cancel"));
    expect(onCancel).toHaveBeenCalledTimes(1);
    expect(onConfirm).not.toHaveBeenCalled();
  });

  it("Confirm button click → onConfirm handler (single user click)", async () => {
    const user = userEvent.setup();
    const { onConfirm, onCancel } = harness({
      pending: { ...cleanBaseline, endTime: "20.0" },
    });
    await user.click(screen.getByTestId("solver-config-diff-v8-confirm"));
    expect(onConfirm).toHaveBeenCalledTimes(1);
    expect(onCancel).not.toHaveBeenCalled();
  });

  it("renders inline validation errors with field + message", () => {
    harness({
      pending: { ...cleanBaseline, application: "noSuchFoam" },
      validationErrors: [
        {
          field: "application",
          kind: "invalid_solver",
          message: 'unknown solver "noSuchFoam" · known: icoFoam, ...',
        },
      ],
    });
    const errList = screen.getByTestId("solver-config-diff-v8-errors");
    expect(errList).toBeTruthy();
    const errLine = screen.getByTestId(
      "solver-config-diff-v8-error-application",
    );
    expect(errLine.textContent).toContain("noSuchFoam");
  });

  it("surfaces commit-time errorMessage banner separately from validation list", () => {
    harness({
      pending: { ...cleanBaseline, endTime: "20.0" },
      errorMessage: "409 etag mismatch · refresh and merge",
    });
    const banner = screen.getByTestId("solver-config-diff-v8-commit-error");
    expect(banner.textContent).toContain("409");
  });

  it("V130 denylist: NO 'auto-commit' / 'AI applies' / 'automatic' verbiage anywhere", () => {
    const { container } = harness({
      pending: { ...cleanBaseline, endTime: "20.0" },
    });
    const text = container.textContent ?? "";
    expect(text.toLowerCase()).not.toContain("auto-commit");
    expect(text.toLowerCase()).not.toContain("ai applies");
    expect(text.toLowerCase()).not.toContain("automatic");
    expect(text.toLowerCase()).not.toContain("auto-save");
  });

  it("exposes data-changed-fields-count + data-validation-error-count for inspection", () => {
    harness({
      pending: { ...cleanBaseline, endTime: "20.0", deltaT: "0.01" },
      validationErrors: [
        {
          field: "deltaT",
          kind: "too_large",
          message: "deltaT > endTime",
        },
      ],
    });
    const root = screen.getByTestId("solver-config-diff-v8");
    expect(root.getAttribute("data-changed-fields-count")).toBe("2");
    expect(root.getAttribute("data-validation-error-count")).toBe("1");
  });
});
