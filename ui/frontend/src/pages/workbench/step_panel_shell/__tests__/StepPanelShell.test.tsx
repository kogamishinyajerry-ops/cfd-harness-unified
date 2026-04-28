// Smoke test for the M-PANELS shell (DEC-V61-096 spec_v2 §E Steps 2 + 4).
// Asserts the shell mounts cleanly + 5 steps render + URL-driven step
// state works. Component-level tests live in this directory's other
// __tests__ files; per-step wireup tests live in step_panel_shell/steps
// alongside the components.

import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

// vtk.js viewport_kernel mock so jsdom doesn't try to load WebGL.
vi.mock("@/visualization/viewport_kernel", () => ({
  createKernel: () => ({
    attachStl: vi.fn(),
    attachGltf: vi.fn(),
    resetCamera: vi.fn(),
    dispose: vi.fn(),
    setBackground: vi.fn(),
  }),
}));

// Step 1 now queries api.getCase via react-query (Step 4 wireup).
// Mock the api module so the shell tests don't block on a network
// fetch and we don't need to add an msw handler for every test.
const apiMock = vi.hoisted(() => ({
  getCase: vi.fn().mockResolvedValue({
    case_id: "abc",
    name: "Test Case",
    reference: null,
    doi: null,
    flow_type: "incompressible",
    geometry_type: "imported",
    compressibility: null,
    steady_state: null,
    solver: null,
    turbulence_model: "laminar",
    parameters: {},
    gold_standard: null,
    preconditions: [],
    contract_status_narrative: null,
  }),
}));
vi.mock("@/api/client", async () => {
  const actual = await vi.importActual<typeof import("@/api/client")>(
    "@/api/client",
  );
  return {
    ...actual,
    api: { ...actual.api, getCase: apiMock.getCase },
  };
});

import { StepPanelShell } from "../../StepPanelShell";

function renderShell(initialPath: string) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[initialPath]}>
        <Routes>
          <Route
            path="/workbench/case/:caseId"
            element={<StepPanelShell />}
          />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
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

  it("renders a real Viewport on Step 1 (format='glb' from /geometry/render)", () => {
    renderShell("/workbench/case/abc?step=1");
    // Step 4 wireup flipped Step 1's viewportConfig from 'none' to
    // 'glb'; the Viewport mounts (mocked kernel) so the placeholder
    // is no longer present on this step.
    expect(screen.queryByTestId("viewport-placeholder")).toBeNull();
  });

  it("still shows the viewport placeholder on Steps 2-5 (not yet wired)", () => {
    renderShell("/workbench/case/abc?step=2");
    expect(screen.getByTestId("viewport-placeholder")).toBeInTheDocument();
  });

  it("falls back to step 1 on out-of-range ?step values", () => {
    renderShell("/workbench/case/abc?step=99");
    expect(screen.getByTestId("step-panel-shell")).toHaveAttribute(
      "data-current-step-id",
      "1",
    );
  });
});
