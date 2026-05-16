// V73.3 · MultiCaseRibbonV3 unit tests · Pillar 10 + Pillar 12 wiring.
//
// Assertions:
//   - Mounts at Step 5 with real-data wire (`/api/cases` live-api)
//   - Renders current case chip + 4 reference chips when ≥4 whitelist
//     references exist beyond the current
//   - Falls back to offline hint when /api/cases errors (graceful_offline_paths
//     subscore for Pillar 12)
//   - Carries data-source attribute for backend-wiring telemetry
//   - Surfaces no mutating buttons (V130/V132 contract still holds)

import type { ReactElement } from "react";
import { describe, expect, it, beforeEach, vi } from "vitest";
import { render as rtlRender, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { MultiCaseRibbonV3 } from "../components/MultiCaseRibbonV3";

const CASE_ID = "lid_driven_cavity";

const CASES_LIVE = [
  { case_id: CASE_ID, name: "Lid Driven Cavity", case_kind: "whitelist", contract_status: "audit-passing" },
  { case_id: "backward_facing_step", name: "Backward Facing Step", case_kind: "whitelist", contract_status: "audit-passing" },
  { case_id: "circular_cylinder_wake", name: "Cylinder Wake", case_kind: "whitelist", contract_status: "audit-passing" },
  { case_id: "naca0012_airfoil", name: "NACA 0012", case_kind: "whitelist", contract_status: "audit-passing" },
  { case_id: "turbulent_flat_plate", name: "Turbulent Flat Plate", case_kind: "whitelist", contract_status: "audit-passing" },
  // imported user case should NOT appear as reference (only whitelist refs)
  { case_id: "my_imported_case", name: "My Case", case_kind: "imported_user", contract_status: "PENDING" },
];

function render(ui: ReactElement) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return rtlRender(
    <QueryClientProvider client={client}>{ui}</QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo) => {
      const url = typeof input === "string" ? input : input.toString();
      if (url.endsWith("/api/cases")) {
        return new Response(JSON.stringify(CASES_LIVE), {
          status: 200,
          headers: { "content-type": "application/json" },
        });
      }
      return new Response("{}", { status: 200 });
    }),
  );
});

describe("V73.3 · MultiCaseRibbonV3 · real-data wire", () => {
  it("mounts ribbon · current chip + 4 reference chips · live-api source", async () => {
    render(<MultiCaseRibbonV3 caseId={CASE_ID} />);
    await waitFor(() =>
      expect(screen.getByTestId("multi-case-ribbon")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("multi-case-ribbon")).toHaveAttribute(
      "data-source",
      "live",
    );
    // 1 current + exactly 4 reference chips (the 5th whitelist is excluded by slice)
    expect(screen.getByTestId("multi-case-chip-current")).toBeInTheDocument();
    expect(screen.getAllByTestId("multi-case-chip")).toHaveLength(4);
  });

  it("imported_user cases are NOT shown as references", async () => {
    render(<MultiCaseRibbonV3 caseId={CASE_ID} />);
    await waitFor(() =>
      expect(screen.getByTestId("multi-case-ribbon")).toBeInTheDocument(),
    );
    const refs = screen.getAllByTestId("multi-case-chip");
    refs.forEach((chip) => {
      expect(chip.getAttribute("data-case-id")).not.toBe("my_imported_case");
    });
  });

  it("current chip carries v3-accent border (data-active=true)", async () => {
    render(<MultiCaseRibbonV3 caseId={CASE_ID} />);
    await waitFor(() =>
      expect(screen.getByTestId("multi-case-chip-current")).toBeInTheDocument(),
    );
    const current = screen.getByTestId("multi-case-chip-current");
    expect(current).toHaveAttribute("data-active", "true");
    expect(current.className).toContain("border-v3-accent");
  });

  it("falls back to offline hint when /api/cases errors · graceful degradation", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response("upstream offline", { status: 503 })),
    );
    render(<MultiCaseRibbonV3 caseId={CASE_ID} />);
    await waitFor(
      () =>
        expect(
          screen.getByTestId("multi-case-ribbon-offline-hint"),
        ).toBeInTheDocument(),
      { timeout: 4_000 },
    );
    expect(
      screen.getByTestId("multi-case-ribbon-offline-hint"),
    ).toHaveAttribute("data-source", "fallback");
  });

  it("no mutating buttons exist on the ribbon (V130/V132)", async () => {
    render(<MultiCaseRibbonV3 caseId={CASE_ID} />);
    await waitFor(() =>
      expect(screen.getByTestId("multi-case-ribbon")).toBeInTheDocument(),
    );
    expect(screen.queryByRole("button", { name: /apply|submit|execute|run/i })).toBeNull();
  });
});
