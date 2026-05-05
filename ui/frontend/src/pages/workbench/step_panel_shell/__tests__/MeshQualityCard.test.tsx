// DEC-V61-127 · MeshQualityCard unit tests.
//
// Coverage scenarios from DEC §V1 acceptance criteria:
//   1. V122 fallback path (only V122 fields, "checkMesh skipped" badge)
//   2. V126 happy path (Mesh OK pill + green-band gauges + needles)
//   3. V126 failure path (Mesh failed pill + failed_checks list)
//   4. Loading state
//   5. Error state (API 5xx)
//   6. Re-fetch on meshGenSeq bump

import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor, cleanup } from "@testing-library/react";

import { ApiError } from "@/api/client";
import type {
  MeshQualityReportV122,
  MeshQualityReportV126,
} from "../types";

const apiMock = vi.hoisted(() => ({
  getMeshQuality: vi.fn(),
}));
vi.mock("@/api/client", async () => {
  const actual = await vi.importActual<typeof import("@/api/client")>(
    "@/api/client",
  );
  return {
    ...actual,
    api: { ...actual.api, getMeshQuality: apiMock.getMeshQuality },
  };
});

import {
  MeshQualityCard,
  __clearMeshQualityCacheForTests,
  invalidateMeshQualityCache,
} from "../MeshQualityCard";

const baseV122: MeshQualityReportV122 = {
  report_kind: "v122",
  case_id: "ldc",
  polymesh_present: true,
  cell_count: 12500,
  point_count: 8400,
  internal_face_count: 30000,
  boundary_face_count: 2000,
  bounding_box_min: [0, 0, 0],
  bounding_box_max: [1, 1, 1],
  bounding_box_volume: 1.0,
  cells_per_unit_volume: 12500,
  patch_face_counts: { walls: 1500, inlet: 300, outlet: 200 },
  warnings: [],
};

const v126Healthy: MeshQualityReportV126 = {
  ...baseV122,
  report_kind: "v126",
  checkmesh_max_non_orthogonality_deg: 22.5,
  checkmesh_max_skewness: 0.32,
  checkmesh_max_aspect_ratio: 4.5,
  checkmesh_mesh_ok: true,
  checkmesh_n_severe_non_ortho_faces: 0,
  checkmesh_failed_checks: null,
};

const v126Failed: MeshQualityReportV126 = {
  ...baseV122,
  report_kind: "v126",
  checkmesh_max_non_orthogonality_deg: 78.4,
  checkmesh_max_skewness: 4.2,
  checkmesh_max_aspect_ratio: 850.5,
  checkmesh_mesh_ok: false,
  checkmesh_n_severe_non_ortho_faces: 18,
  checkmesh_failed_checks: ["Max skewness = 4.2 > 4 -- SKEWED CELLS DETECTED"],
};

beforeEach(() => {
  apiMock.getMeshQuality.mockReset();
  __clearMeshQualityCacheForTests();
  cleanup();
});

describe("MeshQualityCard · V126 happy path", () => {
  it("renders Mesh OK pill and green-band skewness", async () => {
    apiMock.getMeshQuality.mockResolvedValue(v126Healthy);
    render(<MeshQualityCard caseId="ldc" meshGenSeq={1} />);
    await waitFor(() =>
      expect(screen.getByTestId("mesh-quality-card")).toBeInTheDocument(),
    );
    expect(screen.getByText("Mesh OK")).toBeInTheDocument();
    // Skewness 0.32 → "good" band label.
    const skew = screen.getByTestId("mesh-quality-gauge-max-skewness");
    expect(skew.textContent).toContain("0.32");
    expect(skew.textContent).toContain("good");
    // Per-patch chips render.
    expect(screen.getByTitle(/walls: 1,500 faces/)).toBeInTheDocument();
    // No severe-faces banner when count = 0.
    expect(
      screen.queryByTestId("mesh-quality-severe-faces"),
    ).not.toBeInTheDocument();
  });
});

describe("MeshQualityCard · V126 failed path", () => {
  it("renders Failed pill, severe-faces banner, and failed_checks", async () => {
    apiMock.getMeshQuality.mockResolvedValue(v126Failed);
    render(<MeshQualityCard caseId="ldc" meshGenSeq={1} />);
    await waitFor(() =>
      expect(screen.getByText(/Failed 1 check/)).toBeInTheDocument(),
    );
    // Skewness 4.2 — beyond axis max (1.0), needle clamps but band is "reject".
    const skew = screen.getByTestId("mesh-quality-gauge-max-skewness");
    expect(skew.textContent).toContain("reject");
    // Severe-faces banner present.
    const severe = screen.getByTestId("mesh-quality-severe-faces");
    expect(severe.textContent).toContain("18");
    // Failed-check string surfaced verbatim.
    expect(screen.getByText(/SKEWED CELLS DETECTED/)).toBeInTheDocument();
  });
});

describe("MeshQualityCard · V122 fallback (container down)", () => {
  it("renders 'checkMesh skipped' pill and dimmed gauges", async () => {
    apiMock.getMeshQuality.mockResolvedValue(baseV122);
    render(<MeshQualityCard caseId="ldc" meshGenSeq={1} />);
    await waitFor(() =>
      expect(screen.getByText("checkMesh skipped")).toBeInTheDocument(),
    );
    // All three gauges show "skipped" in their value cell.
    const skew = screen.getByTestId("mesh-quality-gauge-max-skewness");
    expect(skew.textContent).toContain("skipped");
    const nonOrtho = screen.getByTestId(
      "mesh-quality-gauge-max-non-orthogonality",
    );
    expect(nonOrtho.textContent).toContain("skipped");
    const ar = screen.getByTestId("mesh-quality-gauge-max-aspect-ratio");
    expect(ar.textContent).toContain("skipped");
  });

  it("surfaces V122 warnings in their own list", async () => {
    apiMock.getMeshQuality.mockResolvedValue({
      ...baseV122,
      warnings: [
        {
          severity: "warning" as const,
          code: "cell_count_low",
          message: "12,500 cells; mesh under-refined for k-omega SST",
        },
      ],
    });
    render(<MeshQualityCard caseId="ldc" meshGenSeq={1} />);
    await waitFor(() =>
      expect(screen.getByText(/under-refined/)).toBeInTheDocument(),
    );
    expect(screen.getByText(/cell_count_low/)).toBeInTheDocument();
    expect(screen.getByText(/Has warnings/)).toBeInTheDocument();
  });
});

describe("MeshQualityCard · loading + error", () => {
  it("renders loading state during fetch", () => {
    let resolveFn: (r: MeshQualityReportV126) => void = () => {};
    apiMock.getMeshQuality.mockReturnValue(
      new Promise<MeshQualityReportV126>((resolve) => {
        resolveFn = resolve;
      }),
    );
    render(<MeshQualityCard caseId="ldc" meshGenSeq={1} />);
    expect(screen.getByTestId("mesh-quality-loading")).toBeInTheDocument();
    resolveFn(v126Healthy);
  });

  it("renders error state for non-404 ApiError", async () => {
    apiMock.getMeshQuality.mockRejectedValue(
      new ApiError(502, "checkmesh_exit_nonzero", { failing_check: "x" }),
    );
    render(<MeshQualityCard caseId="ldc" meshGenSeq={1} />);
    await waitFor(() =>
      expect(screen.getByTestId("mesh-quality-error")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("mesh-quality-error").textContent).toContain(
      "502",
    );
  });

  it("hides card on 404 (case not yet meshed)", async () => {
    apiMock.getMeshQuality.mockRejectedValue(
      new ApiError(404, "polymesh_not_ready", {}),
    );
    render(<MeshQualityCard caseId="ldc" meshGenSeq={1} />);
    // Wait for the rejection to settle, then assert the card is gone.
    await waitFor(() =>
      expect(apiMock.getMeshQuality).toHaveBeenCalled(),
    );
    expect(screen.queryByTestId("mesh-quality-card")).not.toBeInTheDocument();
  });
});

describe("MeshQualityCard · re-fetch on meshGenSeq bump", () => {
  it("meshGenSeq bump alone does NOT bypass cache (R3 contract: explicit invalidate required)", async () => {
    // R3 contract change: cache is keyed on caseId alone, so meshGenSeq
    // bumping without explicit invalidate hits the cache. Step2Mesh's
    // triggerMesh and the module-level regenerate_mesh listener are
    // responsible for invalidating BEFORE bumping the seq.
    apiMock.getMeshQuality.mockResolvedValue(v126Healthy);
    const { rerender } = render(
      <MeshQualityCard caseId="ldc" meshGenSeq={1} />,
    );
    await waitFor(() =>
      expect(apiMock.getMeshQuality).toHaveBeenCalledTimes(1),
    );
    rerender(<MeshQualityCard caseId="ldc" meshGenSeq={2} />);
    // Cache hit — same caseId. No second fetch.
    expect(apiMock.getMeshQuality).toHaveBeenCalledTimes(1);
    // Now invalidate (as Step2Mesh's triggerMesh would) + bump seq.
    invalidateMeshQualityCache("ldc");
    rerender(<MeshQualityCard caseId="ldc" meshGenSeq={3} />);
    await waitFor(() =>
      expect(apiMock.getMeshQuality).toHaveBeenCalledTimes(2),
    );
    // Each call passes runCheckmesh=true.
    expect(apiMock.getMeshQuality).toHaveBeenCalledWith("ldc", {
      runCheckmesh: true,
    });
  });

  it("R3 P1: cache hit on remount with same caseId skips fetch (Step 2 ↔ 3/4 nav)", async () => {
    // First mount: fetch once, populate cache.
    apiMock.getMeshQuality.mockResolvedValue(v126Healthy);
    const { unmount } = render(
      <MeshQualityCard caseId="ldc" meshGenSeq={1} />,
    );
    await waitFor(() =>
      expect(apiMock.getMeshQuality).toHaveBeenCalledTimes(1),
    );
    unmount();
    // R3 P1: a Step 2 ↔ Step 3 ↔ Step 2 navigation remounts Step2Mesh
    // with meshGenSeq=0 (local state reset). The cache must still
    // hit on caseId alone, not block on the gen counter.
    render(<MeshQualityCard caseId="ldc" meshGenSeq={0} />);
    expect(screen.getByText("Mesh OK")).toBeInTheDocument();
    expect(apiMock.getMeshQuality).toHaveBeenCalledTimes(1);
  });

  it("R3 P1: invalidateMeshQualityCache forces refetch on next mount", async () => {
    apiMock.getMeshQuality.mockResolvedValue(v126Healthy);
    const { unmount } = render(
      <MeshQualityCard caseId="ldc" meshGenSeq={1} />,
    );
    await waitFor(() =>
      expect(apiMock.getMeshQuality).toHaveBeenCalledTimes(1),
    );
    unmount();
    // Simulate a fresh mesh (manual or AI-driven) busting the cache.
    invalidateMeshQualityCache("ldc");
    render(<MeshQualityCard caseId="ldc" meshGenSeq={1} />);
    await waitFor(() =>
      expect(apiMock.getMeshQuality).toHaveBeenCalledTimes(2),
    );
  });

  it("R3 P1: AI-coach proposal-applied event busts cache for that caseId", async () => {
    apiMock.getMeshQuality.mockResolvedValue(v126Healthy);
    const { unmount } = render(
      <MeshQualityCard caseId="ldc" meshGenSeq={1} />,
    );
    await waitFor(() =>
      expect(apiMock.getMeshQuality).toHaveBeenCalledTimes(1),
    );
    unmount();
    // Module-level listener: AI applies regenerate_mesh while
    // Step2Mesh is unmounted (engineer is on Step 3/4).
    window.dispatchEvent(
      new CustomEvent("ai-coach:proposal-applied", {
        detail: { caseId: "ldc", tool: "regenerate_mesh" },
      }),
    );
    // Coming back to Step 2 should re-fetch, not show the stale entry.
    render(<MeshQualityCard caseId="ldc" meshGenSeq={1} />);
    await waitFor(() =>
      expect(apiMock.getMeshQuality).toHaveBeenCalledTimes(2),
    );
  });

  it("R4 P2: mesh:mutated event busts cache for that caseId", async () => {
    // The api client dispatches mesh:mutated on success of any
    // polyMesh-mutating route (meshImported, setupBC,
    // setupBCWithEnvelope). The module-level listener must invalidate
    // the cache so the next remount re-fetches.
    apiMock.getMeshQuality.mockResolvedValue(v126Healthy);
    const { unmount } = render(
      <MeshQualityCard caseId="ldc" meshGenSeq={1} />,
    );
    await waitFor(() =>
      expect(apiMock.getMeshQuality).toHaveBeenCalledTimes(1),
    );
    unmount();
    // Step 3 BC setup runs in the background (rewrites
    // constant/polyMesh/boundary). The api client dispatches
    // mesh:mutated, which busts the cache.
    window.dispatchEvent(
      new CustomEvent("mesh:mutated", {
        detail: { caseId: "ldc" },
      }),
    );
    render(<MeshQualityCard caseId="ldc" meshGenSeq={1} />);
    await waitFor(() =>
      expect(apiMock.getMeshQuality).toHaveBeenCalledTimes(2),
    );
  });

  it("R4 P2: mesh:mutated event for a different caseId does NOT bust this cache", async () => {
    apiMock.getMeshQuality.mockResolvedValue(v126Healthy);
    const { unmount } = render(
      <MeshQualityCard caseId="ldc" meshGenSeq={1} />,
    );
    await waitFor(() =>
      expect(apiMock.getMeshQuality).toHaveBeenCalledTimes(1),
    );
    unmount();
    window.dispatchEvent(
      new CustomEvent("mesh:mutated", {
        detail: { caseId: "other-case" },
      }),
    );
    render(<MeshQualityCard caseId="ldc" meshGenSeq={1} />);
    // No re-fetch — cache for "ldc" still valid.
    expect(apiMock.getMeshQuality).toHaveBeenCalledTimes(1);
  });

  it("R3 P2: graceful-degradation responses are NOT cached", async () => {
    // V126 with all checkmesh_* null = container unavailable.
    const v126Skipped: MeshQualityReportV126 = {
      ...v126Healthy,
      checkmesh_max_non_orthogonality_deg: null,
      checkmesh_max_skewness: null,
      checkmesh_max_aspect_ratio: null,
      checkmesh_mesh_ok: null,
      checkmesh_n_severe_non_ortho_faces: null,
      checkmesh_failed_checks: null,
    };
    apiMock.getMeshQuality.mockResolvedValue(v126Skipped);
    const { unmount } = render(
      <MeshQualityCard caseId="ldc" meshGenSeq={1} />,
    );
    await waitFor(() =>
      expect(apiMock.getMeshQuality).toHaveBeenCalledTimes(1),
    );
    unmount();
    // Operator starts the container; next remount must re-fetch
    // (not hit the stale "skipped" entry).
    render(<MeshQualityCard caseId="ldc" meshGenSeq={1} />);
    await waitFor(() =>
      expect(apiMock.getMeshQuality).toHaveBeenCalledTimes(2),
    );
  });
});
