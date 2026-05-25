// DEC-V61-204 · M4 cycle 3 · useReportBundle hook tests.

import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

const apiMock = vi.hoisted(() => ({ reportBundle: vi.fn() }));
vi.mock("@/api/client", async () => {
  const actual = await vi.importActual<typeof import("@/api/client")>(
    "@/api/client",
  );
  return {
    ...actual,
    api: { ...actual.api, reportBundle: apiMock.reportBundle },
  };
});

import { useReportBundle } from "../useReportBundle";
import type { ReportBundle } from "@/types/case_solve";

const BUNDLE: ReportBundle = {
  final_time: 100,
  cell_count: 100,
  slab_cell_count: 10,
  plane_axes: ["x", "y"],
  summary_text: "t",
  cache_version: "v1",
  case_kind: "channel",
  artifacts: {
    contour_streamlines: "/a.png",
    pressure: "/b.png",
    vorticity: "/c.png",
    centerline: "/d.png",
  },
};

function Probe({ caseId }: { caseId: string | null | undefined }) {
  const { data, error } = useReportBundle(caseId);
  return (
    <div>
      <span data-testid="kind">{data?.case_kind ?? "—"}</span>
      <span data-testid="err">{error ? "err" : "—"}</span>
    </div>
  );
}

function renderProbe(caseId: string | null | undefined) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={qc}>
      <Probe caseId={caseId} />
    </QueryClientProvider>,
  );
}

describe("useReportBundle", () => {
  beforeEach(() => vi.clearAllMocks());

  it("fetches the bundle for a real caseId", async () => {
    apiMock.reportBundle.mockResolvedValueOnce(BUNDLE);
    renderProbe("c");
    await waitFor(() =>
      expect(screen.getByTestId("kind").textContent).toBe("channel"),
    );
    expect(apiMock.reportBundle).toHaveBeenCalledWith("c");
  });

  it("is disabled (no request) when caseId is null", () => {
    renderProbe(null);
    expect(apiMock.reportBundle).not.toHaveBeenCalled();
  });

  it("surfaces the error when the fetch rejects", async () => {
    apiMock.reportBundle.mockRejectedValueOnce(new Error("boom"));
    renderProbe("c");
    await waitFor(() =>
      expect(screen.getByTestId("err").textContent).toBe("err"),
    );
  });
});
