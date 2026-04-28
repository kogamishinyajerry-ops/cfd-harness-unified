// Step 1 Import wired-body tests (M-PANELS spec_v2 §E Step 4).

import { describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { ApiError } from "@/api/client";

const apiMock = vi.hoisted(() => ({
  getCase: vi.fn(),
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

import { Step1Import } from "../steps/Step1Import";

function renderStep(props: {
  caseId?: string;
  onStepComplete?: () => void;
  onStepError?: (msg: string) => void;
  registerAiAction?: (action: (() => Promise<void>) | null) => void;
}) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <Step1Import
          caseId={props.caseId ?? "abc"}
          onStepComplete={props.onStepComplete ?? (() => {})}
          onStepError={props.onStepError ?? (() => {})}
          registerAiAction={props.registerAiAction ?? (() => {})}
        />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

const FAKE_CASE = {
  case_id: "imported_2026-04-28T00-00-00Z_demo",
  name: "Demo imported case",
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
};

describe("Step1Import · wired body", () => {
  it("fetches the case + renders the summary on success", async () => {
    apiMock.getCase.mockResolvedValueOnce(FAKE_CASE);
    renderStep({ caseId: FAKE_CASE.case_id });

    await waitFor(() => {
      expect(screen.getByTestId("step1-import-summary")).toBeInTheDocument();
    });
    expect(apiMock.getCase).toHaveBeenCalledWith(FAKE_CASE.case_id);
    expect(screen.getByTestId("step1-import-summary")).toHaveTextContent(
      FAKE_CASE.name,
    );
    expect(screen.getByTestId("step1-import-summary")).toHaveTextContent(
      FAKE_CASE.geometry_type,
    );
  });

  it("calls onStepComplete once the case query resolves", async () => {
    apiMock.getCase.mockResolvedValueOnce(FAKE_CASE);
    const onStepComplete = vi.fn();
    renderStep({ caseId: FAKE_CASE.case_id, onStepComplete });

    await waitFor(() => {
      expect(onStepComplete).toHaveBeenCalled();
    });
  });

  it("renders an error banner + calls onStepError when the case query rejects", async () => {
    apiMock.getCase.mockRejectedValueOnce(
      new ApiError(404, "not found"),
    );
    const onStepError = vi.fn();
    renderStep({ caseId: "missing", onStepError });

    await waitFor(() => {
      expect(screen.getByTestId("step1-import-error")).toBeInTheDocument();
    });
    expect(onStepError).toHaveBeenCalledWith(expect.stringMatching(/^404/));
  });

  it("renders the Re-upload link pointing at /workbench/import", async () => {
    apiMock.getCase.mockResolvedValueOnce(FAKE_CASE);
    renderStep({ caseId: FAKE_CASE.case_id });

    await waitFor(() => {
      expect(
        screen.getByTestId("step1-import-reupload-link"),
      ).toBeInTheDocument();
    });
    expect(
      screen.getByTestId("step1-import-reupload-link"),
    ).toHaveAttribute("href", "/workbench/import");
  });
});
