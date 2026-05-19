/**
 * V88.2 · V8.A SolverConfigEditorV8 contract test
 *
 * Asserts the V8.A contract from .planning/blueprints/v8/INDEX.md:
 *   - Hidden behaviorally when readOnlyMode=true (V88 reverse-stop #20)
 *   - USER-edit form · field change calls onFieldChange (NO auto-write)
 *   - "Review changes" disabled when caseUnset / clean / has errors
 *   - "Review changes" click opens V8.C diff preview (no commit)
 *   - "Confirm commit" inside diff calls onConfirmCommit (single user path)
 *   - "Discard" returns dirty → clean via onDiscard
 *   - V130 lexical denylist: NO "auto-save" / "auto-commit" / "AI applies"
 *     / "automatic" verbiage in rendered text
 *   - V130 structural: NO useEffect that fires onConfirmCommit on mount
 *   - exposes data-config-state · data-validation-status · data-case-id
 *
 * Component is pure presentational — state lives in V8.D hook (tested
 * separately). Network mocking handled at hook layer.
 */
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { SolverConfigEditorV8 } from "../components/SolverConfigEditorV8";
import type {
  SolverConfigEditorState,
} from "../components/SolverConfigEditorV8";
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
  caseId?: string | null;
  readOnlyMode?: boolean;
  fields?: Partial<Record<ControlDictField, string>>;
  baseline?: Partial<Record<ControlDictField, string>>;
  state?: SolverConfigEditorState;
  validationErrors?: ValidationError[];
  errorMessage?: string | null;
  onFieldChange?: (field: ControlDictField, value: string) => void;
  onConfirmCommit?: () => void;
  onDiscard?: () => void;
}) {
  const onFieldChange = props.onFieldChange ?? vi.fn();
  const onConfirmCommit = props.onConfirmCommit ?? vi.fn();
  const onDiscard = props.onDiscard ?? vi.fn();
  const caseId =
    "caseId" in props ? props.caseId! : "lid_driven_cavity";
  const utils = render(
    <SolverConfigEditorV8
      caseId={caseId}
      readOnlyMode={props.readOnlyMode ?? false}
      fields={props.fields ?? cleanBaseline}
      baseline={props.baseline ?? cleanBaseline}
      state={props.state ?? "clean"}
      validationErrors={props.validationErrors ?? []}
      errorMessage={props.errorMessage ?? null}
      onFieldChange={onFieldChange}
      onConfirmCommit={onConfirmCommit}
      onDiscard={onDiscard}
    />,
  );
  return { ...utils, onFieldChange, onConfirmCommit, onDiscard };
}

describe("SolverConfigEditorV8 contract · V88.2 · V8.A", () => {
  it("renders form with all 5 controlDict fields", () => {
    harness({ state: "clean" });
    for (const field of [
      "application",
      "endTime",
      "deltaT",
      "writeInterval",
      "writeFormat",
    ]) {
      expect(
        screen.getByTestId(`solver-config-editor-v8-input-${field}`),
      ).toBeTruthy();
    }
  });

  it("readOnlyMode=true hides the editor form (reverse-stop #20)", () => {
    harness({ readOnlyMode: true });
    const root = screen.getByTestId("solver-config-editor-v8");
    expect(root.getAttribute("data-readonly-mode")).toBe("true");
    // No editable input present
    expect(
      screen.queryByTestId("solver-config-editor-v8-input-application"),
    ).toBeNull();
    expect(
      screen.queryByTestId("solver-config-editor-v8-review"),
    ).toBeNull();
  });

  it("field change fires onFieldChange handler (no auto-write)", async () => {
    const user = userEvent.setup();
    const { onFieldChange, onConfirmCommit } = harness({ state: "clean" });
    const endTime = screen.getByTestId("solver-config-editor-v8-input-endTime");
    await user.clear(endTime);
    await user.type(endTime, "2");
    expect(onFieldChange).toHaveBeenCalled();
    // Crucially, no auto-commit fired during typing
    expect(onConfirmCommit).not.toHaveBeenCalled();
  });

  it("Review-changes button DISABLED when state is clean", () => {
    harness({ state: "clean" });
    const review = screen.getByTestId("solver-config-editor-v8-review");
    expect(review).toBeDisabled();
  });

  it("Review-changes button DISABLED when caseId is null", () => {
    harness({ caseId: null, state: "dirty" });
    const review = screen.getByTestId("solver-config-editor-v8-review");
    expect(review).toBeDisabled();
  });

  it("Review-changes button DISABLED when validation errors present", () => {
    harness({
      state: "dirty",
      fields: { ...cleanBaseline, endTime: "-1" },
      validationErrors: [
        {
          field: "endTime",
          kind: "negative",
          message: "endTime must be > 0",
        },
      ],
    });
    const review = screen.getByTestId("solver-config-editor-v8-review");
    expect(review).toBeDisabled();
  });

  it("Review-changes click opens V8.C diff preview (no commit fired)", async () => {
    const user = userEvent.setup();
    const { onConfirmCommit } = harness({
      state: "dirty",
      fields: { ...cleanBaseline, endTime: "20.0" },
    });
    await user.click(screen.getByTestId("solver-config-editor-v8-review"));
    // Diff appears
    expect(screen.getByTestId("solver-config-diff-v8")).toBeTruthy();
    // No commit yet
    expect(onConfirmCommit).not.toHaveBeenCalled();
  });

  it("Confirm-commit inside diff fires onConfirmCommit (single user path)", async () => {
    const user = userEvent.setup();
    const { onConfirmCommit } = harness({
      state: "dirty",
      fields: { ...cleanBaseline, endTime: "20.0" },
    });
    await user.click(screen.getByTestId("solver-config-editor-v8-review"));
    await user.click(screen.getByTestId("solver-config-diff-v8-confirm"));
    expect(onConfirmCommit).toHaveBeenCalledTimes(1);
  });

  it("Cancel inside diff hides diff, NO commit fired", async () => {
    const user = userEvent.setup();
    const { onConfirmCommit } = harness({
      state: "dirty",
      fields: { ...cleanBaseline, endTime: "20.0" },
    });
    await user.click(screen.getByTestId("solver-config-editor-v8-review"));
    await user.click(screen.getByTestId("solver-config-diff-v8-cancel"));
    expect(screen.queryByTestId("solver-config-diff-v8")).toBeNull();
    expect(onConfirmCommit).not.toHaveBeenCalled();
  });

  it("Discard button only visible when dirty + fires onDiscard", async () => {
    const user = userEvent.setup();
    const { onDiscard, rerender } = harness({ state: "clean" });
    expect(
      screen.queryByTestId("solver-config-editor-v8-discard"),
    ).toBeNull();

    rerender(
      <SolverConfigEditorV8
        caseId="lid_driven_cavity"
        readOnlyMode={false}
        fields={{ ...cleanBaseline, endTime: "20.0" }}
        baseline={cleanBaseline}
        state="dirty"
        validationErrors={[]}
        errorMessage={null}
        onFieldChange={vi.fn()}
        onConfirmCommit={vi.fn()}
        onDiscard={onDiscard}
      />,
    );
    await user.click(screen.getByTestId("solver-config-editor-v8-discard"));
    expect(onDiscard).toHaveBeenCalledTimes(1);
  });

  it("surfaces field-level error inline next to bad field", () => {
    harness({
      state: "dirty",
      fields: { ...cleanBaseline, application: "noSuchFoam" },
      validationErrors: [
        {
          field: "application",
          kind: "invalid_solver",
          message: 'unknown solver "noSuchFoam"',
        },
      ],
    });
    const inline = screen.getByTestId(
      "solver-config-editor-v8-fielderror-application",
    );
    expect(inline.textContent).toContain("noSuchFoam");
  });

  it("V130 denylist: NO 'auto-save' / 'auto-commit' / 'AI applies' / 'automatic' verbiage", () => {
    const { container } = harness({
      state: "dirty",
      fields: { ...cleanBaseline, endTime: "20.0" },
    });
    const text = (container.textContent ?? "").toLowerCase();
    expect(text).not.toContain("auto-save");
    expect(text).not.toContain("auto-commit");
    expect(text).not.toContain("ai applies");
    expect(text).not.toContain("automatic");
  });

  it("exposes data attributes for inspection (state · validation · case)", () => {
    harness({
      state: "dirty",
      fields: { ...cleanBaseline, endTime: "20.0" },
      validationErrors: [
        {
          field: "endTime",
          kind: "negative",
          message: "endTime must be > 0",
        },
      ],
    });
    const root = screen.getByTestId("solver-config-editor-v8");
    expect(root.getAttribute("data-config-state")).toBe("dirty");
    expect(root.getAttribute("data-validation-status")).toBe("invalid");
    expect(root.getAttribute("data-case-id")).toBe("lid_driven_cavity");
    expect(root.getAttribute("data-readonly-mode")).toBe("false");
  });

  it("error-banner surfaces commit-time errorMessage when state=error and diff closed", () => {
    harness({
      state: "error",
      fields: { ...cleanBaseline, endTime: "20.0" },
      errorMessage: "409 etag mismatch · refresh and merge",
    });
    const banner = screen.getByTestId("solver-config-editor-v8-error-banner");
    expect(banner.textContent).toContain("409");
  });

  it("V130 structural: NO useEffect auto-fires onConfirmCommit on mount", () => {
    // Component is pure presentational; mount should not trigger any
    // confirmation. We verify by mounting + asserting handler counts.
    const onConfirmCommit = vi.fn();
    harness({ state: "clean", onConfirmCommit });
    expect(onConfirmCommit).not.toHaveBeenCalled();
  });
});
