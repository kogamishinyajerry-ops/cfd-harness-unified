// DEC-V61-204 · M4 cycle 3 · ReportFiguresPanel state tests.
// The graceful-fallback cases (matplotlib-absent / no-run) are the
// charter's explicit requirement: "never a crash".

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

import { ApiError } from "@/api/client";
import { ReportFiguresPanel } from "../ReportFiguresPanel";
import type { ReportBundle } from "@/types/case_solve";

const BUNDLE: ReportBundle = {
  final_time: 100,
  cell_count: 89745,
  slab_cell_count: 4096,
  plane_axes: ["x", "y"],
  summary_text: "t",
  cache_version: "abcd1234ef",
  case_kind: "lid_driven_cavity",
  artifacts: {
    contour_streamlines: "/api/cases/c/report/contour_streamlines.png?v=1",
    pressure: "/api/cases/c/report/pressure.png?v=1",
    vorticity: "/api/cases/c/report/vorticity.png?v=1",
    centerline: "/api/cases/c/report/centerline.png?v=1",
  },
};

function renderPanel(caseId: string | null = "c") {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={qc}>
      <ReportFiguresPanel caseId={caseId} />
    </QueryClientProvider>,
  );
}

describe("ReportFiguresPanel", () => {
  beforeEach(() => vi.clearAllMocks());

  it("renders 4 provenance-labelled figures with canonical backend URLs on success", async () => {
    apiMock.reportBundle.mockResolvedValueOnce(BUNDLE);
    renderPanel();
    await waitFor(() =>
      expect(screen.getByTestId("v4-report-figures")).toBeInTheDocument(),
    );
    for (const name of [
      "contour_streamlines",
      "pressure",
      "vorticity",
      "centerline",
    ]) {
      expect(screen.getByTestId(`v4-report-fig-${name}`)).toBeInTheDocument();
    }
    // provenance: cell count + cache version surfaced
    const panel = screen.getByTestId("v4-report-figures");
    expect(panel.textContent).toContain("89,745");
    expect(panel.textContent).toContain("abcd1234");
    // figure uses the canonical backend artifact URL (no rewrite)
    const img = screen.getByAltText("|U| + 流线") as HTMLImageElement;
    expect(img.src).toContain("/report/contour_streamlines.png");
  });

  it("derives vorticity/centerline captions from plane_axes (Codex R0 P2)", async () => {
    // non-x/y slab: captions must reflect the actual plane, not hardcoded x-y
    apiMock.reportBundle.mockResolvedValueOnce({
      ...BUNDLE,
      plane_axes: ["x", "z"],
    });
    renderPanel();
    await waitFor(() =>
      expect(screen.getByTestId("v4-report-figures")).toBeInTheDocument(),
    );
    expect(
      screen.getByTestId("v4-report-fig-vorticity").textContent,
    ).toContain("∂Uz/∂x");
    expect(
      screen.getByTestId("v4-report-fig-centerline").textContent,
    ).toContain("U_x(z)");
  });

  it("matplotlib-absent (500 + 'matplotlib') → 'unavailable on this build', not a crash", async () => {
    apiMock.reportBundle.mockRejectedValueOnce(
      new ApiError(500, "matplotlib is required for report rendering"),
    );
    renderPanel();
    await waitFor(() =>
      expect(screen.getByTestId("v4-report-unavailable")).toBeInTheDocument(),
    );
    expect(screen.queryByTestId("v4-report-figures")).not.toBeInTheDocument();
  });

  it("409 (solver hasn't run) → friendly empty state", async () => {
    apiMock.reportBundle.mockRejectedValueOnce(
      new ApiError(409, "solver has not run"),
    );
    renderPanel();
    await waitFor(() =>
      expect(screen.getByTestId("v4-report-empty")).toBeInTheDocument(),
    );
  });

  it("404 (case not built / no results yet) → friendly empty state, not an error", async () => {
    apiMock.reportBundle.mockRejectedValueOnce(
      new ApiError(404, "case 'lid_driven_cavity' not found"),
    );
    renderPanel();
    await waitFor(() =>
      expect(screen.getByTestId("v4-report-empty")).toBeInTheDocument(),
    );
    expect(screen.queryByTestId("v4-report-error")).not.toBeInTheDocument();
  });

  it("generic 500 (non-matplotlib) → error state with HTTP status", async () => {
    apiMock.reportBundle.mockRejectedValueOnce(
      new ApiError(500, "internal field malformed"),
    );
    renderPanel();
    await waitFor(() =>
      expect(screen.getByTestId("v4-report-error").textContent).toContain(
        "HTTP 500",
      ),
    );
  });

  it("503 → results service unavailable", async () => {
    apiMock.reportBundle.mockRejectedValueOnce(
      new ApiError(503, "container down"),
    );
    renderPanel();
    await waitFor(() =>
      expect(screen.getByTestId("v4-report-error").textContent).toContain("503"),
    );
  });

  it("renders nothing + makes no request when no case is selected", () => {
    const { container } = renderPanel(null);
    expect(container).toBeEmptyDOMElement();
    expect(apiMock.reportBundle).not.toHaveBeenCalled();
  });
});
