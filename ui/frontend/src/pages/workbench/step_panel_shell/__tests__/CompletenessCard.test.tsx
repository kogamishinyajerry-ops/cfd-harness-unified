// DEC-V61-116 · CompletenessCard tests.
//
// Coverage: status pill tones (绿/黄/红), expand-on-click, missing-row
// rendering, graceful degradation on API error / loading.

import { describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import type { CaseCompletenessReport } from "@/types/case_completeness";

const apiMock = vi.hoisted(() => ({
  getCaseCompleteness: vi.fn(),
}));
vi.mock("@/api/client", async () => {
  const actual = await vi.importActual<typeof import("@/api/client")>(
    "@/api/client",
  );
  return {
    ...actual,
    api: { ...actual.api, getCaseCompleteness: apiMock.getCaseCompleteness },
  };
});

import { CompletenessCard } from "../CompletenessCard";

function renderCard(caseId = "test_case") {
  // Each test gets a fresh QueryClient so mocks don't leak between cases.
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false, staleTime: 0 } },
  });
  return render(
    <QueryClientProvider client={qc}>
      <CompletenessCard caseId={caseId} />
    </QueryClientProvider>,
  );
}

const READY_REPORT: CaseCompletenessReport = {
  case_id: "lid_driven_cavity",
  case_kind: "whitelist",
  ready_for_archive: true,
  blocked_by_critical: 0,
  present_count: 10,
  total_count: 10,
  percentage: 100.0,
  missing: [],
  notes: [],
};

const WARNING_REPORT: CaseCompletenessReport = {
  case_id: "backward_facing_step",
  case_kind: "whitelist",
  ready_for_archive: true,
  blocked_by_critical: 0,
  present_count: 9,
  total_count: 12,
  percentage: 75.0,
  missing: [
    {
      field_path: "boundary_conditions",
      severity: "warning",
      why: "Adapter-driven geometry uses canonical defaults.",
      suggested_default: null,
    },
  ],
  notes: ["No gold standard linked."],
};

const BLOCKED_REPORT: CaseCompletenessReport = {
  case_id: "imported_X",
  case_kind: "imported_user",
  ready_for_archive: false,
  blocked_by_critical: 2,
  present_count: 1,
  total_count: 3,
  percentage: 33.3,
  missing: [
    {
      field_path: "physics.solver",
      severity: "critical",
      why: "OpenFOAM solver name is required.",
      suggested_default: "simpleFoam",
    },
    {
      field_path: "bc.patches",
      severity: "critical",
      why: "At least one boundary patch must be configured.",
      suggested_default: null,
    },
  ],
  notes: [],
};


describe("CompletenessCard", () => {
  it("renders the green ready pill when archive-ready", async () => {
    apiMock.getCaseCompleteness.mockResolvedValueOnce(READY_REPORT);
    renderCard();
    const pill = await screen.findByTestId("completeness-pill");
    expect(pill).toHaveAttribute("data-tone", "ready");
    expect(pill.textContent).toContain("可入库");
    expect(screen.getByText("已达入库标准")).toBeInTheDocument();
    // 100%
    expect(screen.getByText("100%")).toBeInTheDocument();
  });

  it("renders the amber warning pill when only warnings remain", async () => {
    apiMock.getCaseCompleteness.mockResolvedValueOnce(WARNING_REPORT);
    renderCard();
    const pill = await screen.findByTestId("completeness-pill");
    expect(pill).toHaveAttribute("data-tone", "warning");
    expect(pill.textContent).toContain("可改进");
  });

  it("renders the rose blocked pill when blocked_by_critical > 0", async () => {
    apiMock.getCaseCompleteness.mockResolvedValueOnce(BLOCKED_REPORT);
    renderCard();
    const pill = await screen.findByTestId("completeness-pill");
    expect(pill).toHaveAttribute("data-tone", "blocked");
    expect(pill.textContent).toContain("需修复");
    expect(screen.getByText("还差 2 项")).toBeInTheDocument();
  });

  it("expands to show missing field rows on click", async () => {
    apiMock.getCaseCompleteness.mockResolvedValueOnce(BLOCKED_REPORT);
    renderCard();
    await screen.findByTestId("completeness-pill");
    const summary = screen.getByTestId("completeness-summary");
    await userEvent.click(summary);
    const expanded = await screen.findByTestId("completeness-expanded");
    expect(expanded.textContent).toContain("physics.solver");
    expect(expanded.textContent).toContain("bc.patches");
  });

  it("shows the loading message before data resolves", () => {
    // Never resolve — query stays pending.
    apiMock.getCaseCompleteness.mockReturnValueOnce(new Promise(() => {}));
    renderCard();
    expect(screen.getByText("完整度分析中…")).toBeInTheDocument();
  });

  it("degrades gracefully on API error", async () => {
    apiMock.getCaseCompleteness.mockRejectedValueOnce(new Error("boom"));
    renderCard();
    await waitFor(() =>
      expect(screen.getByText(/完整度分析暂不可用/)).toBeInTheDocument(),
    );
  });
});
