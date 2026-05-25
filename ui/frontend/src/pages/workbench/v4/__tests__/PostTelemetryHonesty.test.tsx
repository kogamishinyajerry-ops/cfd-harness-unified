/**
 * DEC-V61-205 (M5 C4) · the Post right-column telemetry must be honest:
 *   • the radial gauge renders the REAL convergence value/worst-equation
 *     passed to it (no hardcoded 65% "通过率"),
 *   • the three profile mini-charts, lacking a real per-quantity profile
 *     source, render an explicit "示意" (illustrative) badge and DO NOT show
 *     a confident run-style value — never silent fake data.
 * Pure render tests (no fetch / no vtk).
 */
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import {
  ConvergenceGauge,
  PostMiniProfileChart,
} from "../components/modes/ModeRendererPost";
import { POST_BLUEPRINT_MINI_CHARTS } from "../components/postBlueprint";

describe("Post telemetry honesty (M5 C4 de-fake)", () => {
  it("gauge renders the real value + worst-equation label it is given", () => {
    render(<ConvergenceGauge value={42} worst="p" achieved={false} />);
    const gauge = screen.getByTestId("v4-post-gauge");
    expect(gauge.getAttribute("data-achieved")).toBe("false");
    expect(gauge.textContent).toContain("42");
    expect(gauge.textContent).toContain("p");
    expect(gauge.textContent).toContain("收敛度");
    // The old fabricated "通过率" framing must be gone.
    expect(gauge.textContent).not.toContain("通过率");
    // 42% < 75 ⇒ honest "进展中", not "已收敛".
    expect(gauge.textContent).toContain("进展中");
  });

  it("gauge reports 已收敛 only when convergence is actually achieved", () => {
    render(<ConvergenceGauge value={100} worst="p" achieved />);
    expect(screen.getByTestId("v4-post-gauge").textContent).toContain("已收敛");
  });

  it("illustrative mini-charts carry the 示意 badge and hide the confident value", () => {
    const chart = POST_BLUEPRINT_MINI_CHARTS[0];
    render(<PostMiniProfileChart chart={chart} illustrative />);
    const el = screen.getByTestId(`v4-post-mini-chart-${chart.id}`);
    expect(el.getAttribute("data-illustrative")).toBe("true");
    expect(el.textContent).toContain("示意");
    // The fabricated terminal sample (e.g. "248.6 Pa") must NOT be shown as if
    // it were a measured run value.
    expect(el.textContent).not.toContain("248.6");
    expect(el.textContent).not.toContain(chart.samples[chart.samples.length - 1].toString());
  });

  it("a non-illustrative mini-chart would show its value (guards the flag)", () => {
    const chart = POST_BLUEPRINT_MINI_CHARTS[0];
    render(<PostMiniProfileChart chart={chart} />);
    const el = screen.getByTestId(`v4-post-mini-chart-${chart.id}`);
    expect(el.getAttribute("data-illustrative")).toBe("false");
    expect(el.textContent).not.toContain("示意");
  });
});
