// Smoke test for the M-PANELS skeleton (DEC-V61-096 spec_v2 §E Step 2).
// Asserts the shell mounts cleanly + 5 steps render + URL-driven step
// state works. Wire-up tests for Step 1 / Step 2 / etc. land in their
// own test files in spec_v2 §E Steps 3-5.

import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";

// Viewport delegates to viewport_kernel, which the existing
// Viewport.test.tsx mocks to avoid loading vtk.js under jsdom. The
// skeleton ships format='none' on every step so the Viewport never
// actually mounts in this test — we still mock the kernel so the
// production code-path stays import-clean.
vi.mock("@/visualization/viewport_kernel", () => ({
  createKernel: () => ({
    attachStl: vi.fn(),
    attachGltf: vi.fn(),
    resetCamera: vi.fn(),
    dispose: vi.fn(),
    setBackground: vi.fn(),
  }),
}));

import { StepPanelShell } from "../../StepPanelShell";

function renderShell(initialPath: string) {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <Routes>
        <Route
          path="/workbench/case/:caseId"
          element={<StepPanelShell />}
        />
      </Routes>
    </MemoryRouter>,
  );
}

describe("StepPanelShell · skeleton (M-PANELS Step 2)", () => {
  it("mounts at /workbench/case/:caseId with step 1 active by default", () => {
    renderShell("/workbench/case/abc");

    const shell = screen.getByTestId("step-panel-shell");
    expect(shell).toBeInTheDocument();
    expect(shell).toHaveAttribute("data-current-step-id", "1");
  });

  it("shows the case_id in the top bar", () => {
    renderShell("/workbench/case/imported_2026-04-28T00-00-00Z_demo");
    expect(
      screen.getByTestId("top-bar-case-id"),
    ).toHaveTextContent("imported_2026-04-28T00-00-00Z_demo");
  });

  it("renders all 5 step rows in the step tree", () => {
    renderShell("/workbench/case/abc");
    for (const id of [1, 2, 3, 4, 5]) {
      expect(screen.getByTestId(`step-tree-row-${id}`)).toBeInTheDocument();
    }
  });

  it("highlights the active step via data-step-status='active'", () => {
    renderShell("/workbench/case/abc?step=3");
    const shell = screen.getByTestId("step-panel-shell");
    expect(shell).toHaveAttribute("data-current-step-id", "3");
    expect(screen.getByTestId("step-tree-row-3")).toHaveAttribute(
      "data-step-status",
      "active",
    );
    expect(screen.getByTestId("step-tree-row-1")).not.toHaveAttribute(
      "data-step-status",
      "active",
    );
  });

  it("navigates between steps via URL on step-tree click", async () => {
    const user = userEvent.setup();
    renderShell("/workbench/case/abc");

    expect(screen.getByTestId("step-panel-shell")).toHaveAttribute(
      "data-current-step-id",
      "1",
    );
    await user.click(screen.getByTestId("step-tree-row-2"));
    expect(screen.getByTestId("step-panel-shell")).toHaveAttribute(
      "data-current-step-id",
      "2",
    );
  });

  it("[下一步] button advances; [上一步] retreats", async () => {
    const user = userEvent.setup();
    renderShell("/workbench/case/abc?step=2");

    await user.click(screen.getByTestId("next-button"));
    expect(screen.getByTestId("step-panel-shell")).toHaveAttribute(
      "data-current-step-id",
      "3",
    );
    await user.click(screen.getByTestId("previous-button"));
    expect(screen.getByTestId("step-panel-shell")).toHaveAttribute(
      "data-current-step-id",
      "2",
    );
  });

  it("[上一步] is disabled at step 1; [下一步] is disabled at step 5", () => {
    const { unmount } = renderShell("/workbench/case/abc?step=1");
    expect(screen.getByTestId("previous-button")).toBeDisabled();
    expect(screen.getByTestId("next-button")).not.toBeDisabled();
    unmount();

    renderShell("/workbench/case/abc?step=5");
    expect(screen.getByTestId("previous-button")).not.toBeDisabled();
    expect(screen.getByTestId("next-button")).toBeDisabled();
  });

  it("[AI 处理] is disabled in skeleton (no step is wired in Tier-A yet)", () => {
    renderShell("/workbench/case/abc?step=2");
    const aiButton = screen.getByTestId("ai-process-button");
    expect(aiButton).toBeDisabled();
    expect(aiButton).toHaveAttribute("title");
  });

  it("renders the viewport placeholder while every step ships format='none'", () => {
    renderShell("/workbench/case/abc?step=1");
    expect(
      screen.getByTestId("viewport-placeholder"),
    ).toBeInTheDocument();
  });

  it("falls back to step 1 on out-of-range ?step values", () => {
    renderShell("/workbench/case/abc?step=99");
    expect(screen.getByTestId("step-panel-shell")).toHaveAttribute(
      "data-current-step-id",
      "1",
    );
  });
});
