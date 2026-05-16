/**
 * V71.1 · WorkbenchShellV3 smoke + V130/V132 contract test
 *
 * Asserts:
 *   1. Shell mounts with all 4 panels + pipeline strip + viewport toolbar
 *   2. Activity bar renders 6 workbench-level entries
 *   3. Pipeline strip exposes 5 steps; clicking advances ?step= param
 *   4. Viewport toolbar exposes 6 modes; switching is engineer-controlled
 *   5. Right panel exposes 3 tabs (Inspector / Advisor / TruthChain)
 *   6. Advisor tab carries advisory-only badge + NO apply/submit/execute
 *      buttons (V130/V132 contract)
 *   7. Bottom panel collapses + expands · 4 tabs (Console/Residuals/Forces/Log)
 */
import { describe, expect, it, beforeEach, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { WorkbenchShellV3 } from "../WorkbenchShellV3";

function renderShell(initial: string = "/workbench/v3/case/lid_driven_cavity") {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[initial]}>
        <Routes>
          <Route
            path="/workbench/v3/case/:caseId"
            element={<WorkbenchShellV3 />}
          />
          <Route path="/workbench/v3" element={<WorkbenchShellV3 />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  // Stub completeness endpoint so TruthChain tab has data when probed.
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo) => {
      const url = typeof input === "string" ? input : input.toString();
      if (url.includes("/completeness")) {
        return new Response(
          JSON.stringify({
            case_id: "lid_driven_cavity",
            case_kind: "whitelist",
            ready_for_archive: true,
            blocked_by_critical: 0,
            percentage: 100,
            llm_offline: true,
            last_action: "audit-passed",
            validation: "audit-passing",
          }),
          { status: 200, headers: { "content-type": "application/json" } },
        );
      }
      if (url.includes("/ai-review") || url.includes("/ai-diagnose")) {
        return new Response("upstream offline", { status: 503 });
      }
      return new Response("{}", { status: 200 });
    }),
  );
});

describe("WorkbenchShellV3 · panel structure", () => {
  it("mounts all 4 persistent panels + topbar + bottom collapsed bar", () => {
    renderShell();
    expect(screen.getByTestId("workbench-shell-v3")).toBeInTheDocument();
    expect(screen.getByTestId("workbench-left-panel")).toBeInTheDocument();
    expect(screen.getByTestId("workbench-center")).toBeInTheDocument();
    expect(screen.getByTestId("workbench-right-panel")).toBeInTheDocument();
    // Bottom panel starts collapsed at Step 1
    expect(
      screen.getByTestId("bottom-panel-collapsed"),
    ).toBeInTheDocument();
  });

  it("carries data-v71-ui-shell tag for visual baseline contract", () => {
    renderShell();
    const shell = screen.getByTestId("workbench-shell-v3");
    expect(shell.getAttribute("data-v71-ui-shell")).toBe("true");
  });
});

describe("WorkbenchShellV3 · pipeline + viewport", () => {
  it("exposes 5 pipeline steps", () => {
    renderShell();
    for (let i = 1; i <= 5; i++) {
      expect(
        screen.getByTestId(`pipeline-step-${i}`),
      ).toBeInTheDocument();
    }
  });

  it("exposes 6 viewport modes", () => {
    renderShell();
    for (const mode of [
      "geometry",
      "mesh",
      "bc",
      "field",
      "residuals",
      "report",
    ]) {
      expect(
        screen.getByTestId(`viewport-mode-${mode}`),
      ).toBeInTheDocument();
    }
  });

  it("advances ?step= when pipeline step clicked", async () => {
    const user = userEvent.setup();
    renderShell();
    const step4 = screen.getByTestId("pipeline-step-4");
    await user.click(step4);
    // Bottom panel auto-expands at Step 4+
    expect(
      screen.getByTestId("bottom-panel-expanded"),
    ).toBeInTheDocument();
  });
});

describe("WorkbenchShellV3 · right panel 3 tabs", () => {
  it("renders Inspector / Advisor / TruthChain tabs", () => {
    renderShell();
    expect(screen.getByTestId("right-tab-inspector")).toBeInTheDocument();
    expect(screen.getByTestId("right-tab-advisor")).toBeInTheDocument();
    expect(screen.getByTestId("right-tab-truthchain")).toBeInTheDocument();
  });

  it("Advisor tab carries advisory-only badge + zero mutating buttons", async () => {
    const user = userEvent.setup();
    renderShell();
    await user.click(screen.getByTestId("right-tab-advisor"));
    expect(
      screen.getByTestId("advisor-advisory-badge"),
    ).toBeInTheDocument();
    // V130/V132 HARD CONTRACT: no mutation controls
    expect(screen.queryByRole("button", { name: /apply/i })).toBeNull();
    expect(screen.queryByRole("button", { name: /submit/i })).toBeNull();
    expect(screen.queryByRole("button", { name: /execute/i })).toBeNull();
    expect(screen.queryByRole("button", { name: /auto-fix/i })).toBeNull();
    expect(screen.queryByRole("button", { name: /应用/ })).toBeNull();
    expect(screen.queryByRole("button", { name: /提交/ })).toBeNull();
    expect(screen.queryByRole("button", { name: /执行/ })).toBeNull();
  });
});

describe("WorkbenchShellV3 · bottom panel", () => {
  it("expands + renders 4 tabs after toggle", async () => {
    const user = userEvent.setup();
    renderShell();
    // Collapsed by default at Step 1
    const collapsedToggle = within(
      screen.getByTestId("bottom-panel-collapsed"),
    ).getByTestId("bottom-panel-toggle");
    await user.click(collapsedToggle);
    expect(
      screen.getByTestId("bottom-panel-expanded"),
    ).toBeInTheDocument();
    expect(screen.getByTestId("bottom-tab-console")).toBeInTheDocument();
    expect(screen.getByTestId("bottom-tab-residuals")).toBeInTheDocument();
    expect(screen.getByTestId("bottom-tab-forces")).toBeInTheDocument();
    expect(screen.getByTestId("bottom-tab-log")).toBeInTheDocument();
  });
});

describe("WorkbenchShellV3 · V71.2 step surfaces", () => {
  it("Step 2 inspector renders mesh-quality rows with verdict dots (V71.G)", async () => {
    const user = userEvent.setup();
    renderShell();
    await user.click(screen.getByTestId("pipeline-step-2"));
    const rows = screen.getAllByTestId("mesh-quality-row");
    expect(rows.length).toBeGreaterThanOrEqual(4);
    // At least one row carries a non-N/A verdict
    const verdicts = rows.map((r) => r.getAttribute("data-quality-verdict"));
    expect(verdicts.some((v) => v === "pass" || v === "warn")).toBe(true);
  });

  it("Step 3 BC viewport renders all 4 BC types via dusty palette (V71.H)", async () => {
    const user = userEvent.setup();
    renderShell();
    await user.click(screen.getByTestId("pipeline-step-3"));
    expect(screen.getByTestId("bc-patch-inlet")).toBeInTheDocument();
    expect(screen.getByTestId("bc-patch-outlet")).toBeInTheDocument();
    expect(screen.getByTestId("bc-patch-walls")).toBeInTheDocument();
    expect(screen.getByTestId("bc-patch-symmetry")).toBeInTheDocument();
  });

  it("Step 3 MaterialCard rows expand inline on click (V71.I · read-only)", async () => {
    const user = userEvent.setup();
    renderShell();
    await user.click(screen.getByTestId("pipeline-step-3"));
    expect(screen.getByTestId("material-card")).toBeInTheDocument();
    const nuRow = screen.getByTestId("material-nu");
    expect(nuRow.getAttribute("data-open")).toBe("false");
    await user.click(nuRow);
    expect(nuRow.getAttribute("data-open")).toBe("true");
    expect(screen.getByTestId("material-nu-derive")).toBeInTheDocument();
    // V130: the expanded panel is read-only · no input/textarea/edit button
    const derive = screen.getByTestId("material-nu-derive");
    expect(derive.tagName).toBe("P");
  });
});

describe("WorkbenchShellV3 · activity bar", () => {
  it("renders 6 activity-bar entries", () => {
    renderShell();
    for (const key of [
      "workbench",
      "catalog",
      "runs",
      "benchmarks",
      "tutorial",
      "settings",
    ]) {
      expect(
        screen.getByTestId(`activity-${key}`),
      ).toBeInTheDocument();
    }
  });
});
