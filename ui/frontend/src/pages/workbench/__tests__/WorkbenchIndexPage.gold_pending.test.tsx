/**
 * V68-C.3 · WorkbenchIndexPage gold-pending badge tests.
 *
 * Asserts:
 *   1. Catalog renders case_002a with `gold pending` badge + disclaimer
 *   2. Curated whitelist cases render ContractChip (no gold-pending badge)
 *   3. Edit & run link still works for gold-pending cases (engineer can
 *      open them; gold-pending is a trust-gate flag, not a navigation gate)
 */
import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor, cleanup } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import {
  QueryClient,
  QueryClientProvider,
} from "@tanstack/react-query";

import type { CaseIndexEntry } from "@/types/validation";

const apiMock = vi.hoisted(() => ({
  listCases: vi.fn(),
}));
vi.mock("@/api/client", async () => {
  const actual = await vi.importActual<typeof import("@/api/client")>(
    "@/api/client",
  );
  return {
    ...actual,
    api: { ...actual.api, listCases: apiMock.listCases },
  };
});

import { WorkbenchIndexPage } from "../WorkbenchIndexPage";

function renderPage() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return render(
    <MemoryRouter>
      <QueryClientProvider client={client}>
        <WorkbenchIndexPage />
      </QueryClientProvider>
    </MemoryRouter>,
  );
}

const APU_BAY: CaseIndexEntry = {
  case_id: "case_002a",
  name: "APU Bay Industrial Ventilation (Gold Pending)",
  flow_type: "INTERNAL",
  geometry_type: "COMPLEX",
  turbulence_model: "k-omega SST",
  has_gold_standard: false,
  has_measurement: false,
  contract_status: "UNKNOWN",
  run_summary: { total: 0, verdict_counts: {} },
  case_kind: "imported_user",
  gold_pending: true,
};

const LDC: CaseIndexEntry = {
  case_id: "lid_driven_cavity",
  name: "Lid-Driven Cavity",
  flow_type: "INTERNAL",
  geometry_type: "SIMPLE_GRID",
  turbulence_model: "laminar",
  has_gold_standard: true,
  has_measurement: true,
  contract_status: "PASS",
  run_summary: { total: 5, verdict_counts: { PASS: 3, FAIL: 2 } },
  case_kind: "whitelist",
  gold_pending: false,
};

beforeEach(() => {
  apiMock.listCases.mockReset();
  cleanup();
});

describe("WorkbenchIndexPage · gold-pending badge", () => {
  it("renders gold pending badge + disclaimer for case_002a", async () => {
    apiMock.listCases.mockResolvedValue([LDC, APU_BAY]);
    renderPage();

    await waitFor(() =>
      expect(screen.getByTestId("case-card-case_002a")).toBeInTheDocument(),
    );
    const card = screen.getByTestId("case-card-case_002a");
    expect(card).toHaveAttribute("data-case-kind", "imported_user");
    expect(card).toHaveAttribute("data-gold-pending", "true");
    expect(
      screen.getByTestId("case-card-gold-pending-badge"),
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("case-card-gold-pending-badge").textContent,
    ).toContain("gold pending");
    expect(
      screen.getByTestId(
        "case-card-gold-pending-disclaimer-case_002a",
      ).textContent,
    ).toMatch(/Gold pending|trust gate stays PENDING/);
  });

  it("renders contract chip (no gold-pending badge) for curated whitelist cases", async () => {
    apiMock.listCases.mockResolvedValue([LDC, APU_BAY]);
    renderPage();

    await waitFor(() =>
      expect(
        screen.getByTestId("case-card-lid_driven_cavity"),
      ).toBeInTheDocument(),
    );
    const ldcCard = screen.getByTestId("case-card-lid_driven_cavity");
    expect(ldcCard).toHaveAttribute("data-case-kind", "whitelist");
    expect(ldcCard).toHaveAttribute("data-gold-pending", "false");
    // ContractChip with PASS text present; gold-pending badge absent on LDC.
    expect(ldcCard.textContent).toContain("PASS");
    expect(
      ldcCard.querySelector('[data-testid="case-card-gold-pending-badge"]'),
    ).toBeNull();
  });

  it("Edit & run link is still emitted for gold-pending case (engineer can open it)", async () => {
    apiMock.listCases.mockResolvedValue([APU_BAY]);
    renderPage();

    await waitFor(() =>
      expect(screen.getByTestId("case-card-case_002a")).toBeInTheDocument(),
    );
    const card = screen.getByTestId("case-card-case_002a");
    const editLinks = card.querySelectorAll("a");
    const hrefs = Array.from(editLinks).map((a) => a.getAttribute("href"));
    expect(hrefs).toContain("/workbench/case/case_002a/edit");
    expect(hrefs).toContain("/workbench/case/case_002a/runs");
  });
});
