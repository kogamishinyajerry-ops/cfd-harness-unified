// DEC-V61-102 M-RESCUE Phase 2 · Step 4 raw-dict-editor wiring tests.
// Verifies the collapsible <details> section is present, collapsed
// by default, lazily mounts RawDictEditor on expand, and stays
// mounted across collapse cycles (matching the Step 3 pattern).

import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

const apiMock = vi.hoisted(() => ({
  listRawDicts: vi.fn(),
}));
vi.mock("@/api/client", async () => {
  const actual = await vi.importActual<typeof import("@/api/client")>(
    "@/api/client",
  );
  return {
    ...actual,
    api: { ...actual.api, listRawDicts: apiMock.listRawDicts },
  };
});

import { SolveStreamProvider } from "../SolveStreamContext";
import { Step4SolveRun } from "../steps/Step4SolveRun";

function renderStep4(props: { caseId?: string } = {}) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <SolveStreamProvider>
        <Step4SolveRun
          caseId={props.caseId ?? "imported_test"}
          onStepComplete={() => {}}
          onStepError={() => {}}
          registerAiAction={() => {}}
        />
      </SolveStreamProvider>
    </QueryClientProvider>,
  );
}

describe("Step4SolveRun · raw dict editor wiring (DEC-V61-102 Phase 2)", () => {
  it("renders a collapsed raw-dict-editor section by default", () => {
    apiMock.listRawDicts.mockResolvedValue([]);
    renderStep4();
    const details = screen.getByTestId("step4-raw-dict-editor");
    expect(details).toBeInTheDocument();
    // <details> without an `open` attribute is collapsed.
    expect((details as HTMLDetailsElement).open).toBe(false);
  });

  it("does not mount RawDictEditor until the disclosure is expanded", () => {
    apiMock.listRawDicts.mockResolvedValue([]);
    renderStep4();
    expect(screen.queryByText(/Loading dict list/)).toBeNull();
    expect(apiMock.listRawDicts).not.toHaveBeenCalled();
  });

  it("mounts RawDictEditor on first open and triggers the dict list fetch", async () => {
    apiMock.listRawDicts.mockResolvedValue([]);
    renderStep4();
    const details = screen.getByTestId("step4-raw-dict-editor") as HTMLDetailsElement;
    // Synthetic toggle: <details>.open=true and dispatch the toggle event.
    details.open = true;
    fireEvent(details, new Event("toggle"));
    expect(apiMock.listRawDicts).toHaveBeenCalledWith("imported_test");
  });

  it("limits visible paths to the solver-control set (controlDict/fvSchemes/fvSolution)", async () => {
    apiMock.listRawDicts.mockResolvedValue([
      { path: "system/controlDict", exists: true, source: "ai", etag: "1" },
      { path: "system/fvSchemes", exists: true, source: "ai", etag: "2" },
      { path: "system/fvSolution", exists: true, source: "ai", etag: "3" },
      { path: "constant/momentumTransport", exists: true, source: "ai", etag: "4" },
      { path: "constant/physicalProperties", exists: true, source: "ai", etag: "5" },
    ]);
    renderStep4();
    const details = screen.getByTestId("step4-raw-dict-editor") as HTMLDetailsElement;
    details.open = true;
    fireEvent(details, new Event("toggle"));

    // RawDictEditor renders one tab per visible path. The Step 4
    // allowedPaths set explicitly excludes constant/* (BCs are
    // Step 3's territory).
    await screen.findByText("system/controlDict");
    expect(screen.getByText("system/fvSchemes")).toBeInTheDocument();
    expect(screen.getByText("system/fvSolution")).toBeInTheDocument();
    expect(screen.queryByText("constant/momentumTransport")).toBeNull();
    expect(screen.queryByText("constant/physicalProperties")).toBeNull();
  });
});
