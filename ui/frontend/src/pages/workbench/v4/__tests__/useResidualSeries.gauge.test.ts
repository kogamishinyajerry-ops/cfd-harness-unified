/**
 * V4 R6 · Convergence-gauge contract test.
 *
 * Locks the gauge formula:
 *   gauge_pct = 100 × clamp(−log10(worst_residual) / −log10(target_floor), 0, 1)
 *
 * Worst = max across all series · last sample · positive finite only.
 * Threshold matches OpenFOAM steady-state convergence semantics (all
 * equations must drop below the target floor).
 */
import { describe, expect, it } from "vitest";

import { convergenceGaugeFromSeries } from "../hooks/useResidualSeries";
import type { ResidualSeriesPayload } from "@/types/residual_series";

function payload(
  series: Record<string, Array<{ x: number; y: number }>>,
  target_floor = 1e-6,
): ResidualSeriesPayload {
  const sample_count = Math.max(
    0,
    ...Object.values(series).map((arr) => arr.length),
  );
  return {
    case_id: "test",
    source: sample_count > 0 ? "runs" : "empty",
    series,
    sample_count,
    latest_run_id: null,
    target_floor,
    achieved: Object.values(series).every(
      (arr) => arr.length > 0 && arr[arr.length - 1].y <= target_floor,
    ),
    note: "",
  };
}

describe("convergenceGaugeFromSeries", () => {
  it("returns 0 when payload is null", () => {
    const g = convergenceGaugeFromSeries(null);
    expect(g.value).toBe(0);
    expect(g.worst).toBe(null);
    expect(g.achieved).toBe(false);
  });

  it("returns 0 when sample_count is zero", () => {
    const g = convergenceGaugeFromSeries(payload({}));
    expect(g.value).toBe(0);
  });

  it("100% when worst residual sits at the target floor", () => {
    const g = convergenceGaugeFromSeries(
      payload({
        Ux: [{ x: 1, y: 1e-6 }],
        Uy: [{ x: 1, y: 1e-6 }],
        p: [{ x: 1, y: 1e-6 }],
      }),
    );
    expect(g.value).toBeCloseTo(100, 1);
    expect(g.achieved).toBe(true);
  });

  it("~50% at the typical 1e-3 convergence threshold (half of target)", () => {
    const g = convergenceGaugeFromSeries(
      payload({
        Ux: [{ x: 1, y: 1e-3 }],
      }),
    );
    expect(g.value).toBeCloseTo(50, 1);
    expect(g.worst).toBe("Ux");
    expect(g.achieved).toBe(false);
  });

  it("0% when residual is 1.0 (diverged/not started)", () => {
    const g = convergenceGaugeFromSeries(
      payload({
        Ux: [{ x: 1, y: 1.0 }],
      }),
    );
    expect(g.value).toBe(0);
  });

  it("worst = max residual across series (bottleneck rule)", () => {
    const g = convergenceGaugeFromSeries(
      payload({
        Ux: [{ x: 1, y: 1e-6 }], // fully converged
        Uy: [{ x: 1, y: 1e-6 }],
        p: [{ x: 1, y: 1e-3 }], // bottleneck
      }),
    );
    expect(g.worst).toBe("p");
    // p dominates → gauge ≈ 50%
    expect(g.value).toBeCloseTo(50, 1);
    expect(g.achieved).toBe(false);
  });

  it("uses LAST sample of each series (history aware)", () => {
    const g = convergenceGaugeFromSeries(
      payload({
        Ux: [
          { x: 1, y: 1e-2 }, // older sample · ignored
          { x: 2, y: 1e-6 }, // latest · controls gauge
        ],
      }),
    );
    expect(g.value).toBeCloseTo(100, 1);
  });

  it("clamps above 100% (residual below floor)", () => {
    const g = convergenceGaugeFromSeries(
      payload({
        Ux: [{ x: 1, y: 1e-12 }],
      }),
    );
    expect(g.value).toBeLessThanOrEqual(100);
  });

  it("clamps at 0% (residual above 1.0)", () => {
    const g = convergenceGaugeFromSeries(
      payload({
        Ux: [{ x: 1, y: 100 }],
      }),
    );
    expect(g.value).toBe(0);
  });

  it("skips non-positive / non-finite samples", () => {
    const g = convergenceGaugeFromSeries(
      payload({
        Ux: [{ x: 1, y: 0 }], // dropped
        Uy: [{ x: 1, y: -1e-6 }], // dropped
        p: [{ x: 1, y: 1e-4 }], // only one counted
      }),
    );
    expect(g.worst).toBe("p");
    expect(g.value).toBeCloseTo((-Math.log10(1e-4) / 6) * 100, 1);
  });

  it("custom target_floor scales the denominator", () => {
    // Tighter target (1e-9) → 1e-3 is only 1/3 of the way.
    const g = convergenceGaugeFromSeries(
      payload({ Ux: [{ x: 1, y: 1e-3 }] }, /* target_floor */ 1e-9),
    );
    // gauge = (-log10(1e-3) / -log10(1e-9)) × 100 = 3/9 × 100 ≈ 33.3
    expect(g.value).toBeCloseTo(33.3, 1);
  });
});
