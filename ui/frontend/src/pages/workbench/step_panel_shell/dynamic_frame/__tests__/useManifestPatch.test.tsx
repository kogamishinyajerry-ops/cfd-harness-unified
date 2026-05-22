// DEC-V61-202-SUB-M30-CYCLE2 · useManifestPatch mutation tests.

import { describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

const apiMock = vi.hoisted(() => ({
  patchCaseManifest: vi.fn(),
}));
vi.mock("@/api/client", async () => {
  const actual = await vi.importActual<typeof import("@/api/client")>(
    "@/api/client",
  );
  return {
    ...actual,
    api: { ...actual.api, patchCaseManifest: apiMock.patchCaseManifest },
  };
});

import { useManifestPatch } from "../useManifestPatch";
import type { ManifestPatchResponse } from "@/types/manifest_patch";

function TestHarness({
  caseId,
  onSuccess,
}: {
  caseId: string;
  onSuccess?: (r: ManifestPatchResponse) => void;
}) {
  const m = useManifestPatch({ caseId, onSuccess });
  return (
    <button
      type="button"
      data-testid="trigger"
      onClick={() =>
        m.mutate({
          field_path: "vof_contract.phases",
          value: ["water", "air"],
          expected_state_sha: "a".repeat(64),
        })
      }
    >
      {m.isPending ? "pending" : "go"}
    </button>
  );
}

function renderHarness(onSuccess?: (r: ManifestPatchResponse) => void) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return {
    ...render(
      <QueryClientProvider client={qc}>
        <TestHarness caseId="test_case" onSuccess={onSuccess} />
      </QueryClientProvider>,
    ),
    qc,
  };
}

describe("useManifestPatch", () => {
  it("calls api.patchCaseManifest with the right request shape", async () => {
    apiMock.patchCaseManifest.mockResolvedValueOnce({
      success: true,
      applied_path: "vof_contract.phases",
      new_state_sha: "b".repeat(64),
      case_kind: "imported_user",
      validation_errors: [],
    });
    renderHarness();
    await userEvent.click(screen.getByTestId("trigger"));
    await waitFor(() => {
      expect(apiMock.patchCaseManifest).toHaveBeenCalledWith("test_case", {
        field_path: "vof_contract.phases",
        value: ["water", "air"],
        expected_state_sha: "a".repeat(64),
      });
    });
  });

  it("invalidates workbench-frame query on success", async () => {
    apiMock.patchCaseManifest.mockResolvedValueOnce({
      success: true,
      applied_path: "vof_contract.phases",
      new_state_sha: "b".repeat(64),
      case_kind: "imported_user",
      validation_errors: [],
    });
    const { qc } = renderHarness();
    const invalidateSpy = vi.spyOn(qc, "invalidateQueries");
    await userEvent.click(screen.getByTestId("trigger"));
    await waitFor(() => {
      expect(invalidateSpy).toHaveBeenCalledWith({
        queryKey: ["workbench-frame", "test_case"],
      });
    });
  });

  it("calls onSuccess callback with the response", async () => {
    const response: ManifestPatchResponse = {
      success: true,
      applied_path: "vof_contract.phases",
      new_state_sha: "b".repeat(64),
      case_kind: "imported_user",
      validation_errors: [],
    };
    apiMock.patchCaseManifest.mockResolvedValueOnce(response);
    const onSuccess = vi.fn();
    renderHarness(onSuccess);
    await userEvent.click(screen.getByTestId("trigger"));
    await waitFor(() => {
      expect(onSuccess).toHaveBeenCalledWith(response);
    });
  });
});
