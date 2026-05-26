/**
 * DEC-V61-206 (M5.5 C2) · the construction-step renderers must not present
 * fabricated numbers as if they were real computed results. Tier-1 de-fakes:
 *   • Physics: no hardcoded "Re 8.4e5 · Pr 0.71"; velocity legend shows a
 *     numeric |U| range only when a REAL VTP scalar range is given, else
 *     "范围待求解".
 *   • Mesh: no fabricated "18.86M · skew 0.128" — an unmeshed case shows
 *     "尚无网格指标".
 *   • Solver: no fabricated "iter 1250/2000 · 00:12:14" or "96.4 °C" temperature
 *     history; an un-run case shows "未开始" + an honest temperature no-data
 *     state (incompressible solvers carry no energy equation).
 * Renders with caseId=null take the empty-state path (no vtk mount).
 */
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createElement, type ReactNode } from "react";

import {
  ModeRendererPhysics,
  PhysicsVelocityLegend,
} from "../ModeRendererPhysics";
import { ModeRendererMesh } from "../ModeRendererMesh";
import { ModeRendererSolver } from "../ModeRendererSolver";
import { ModeRendererDoe } from "../ModeRendererDoe";
import { KpiStripV4 } from "../../KpiStripV4";

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return createElement(QueryClientProvider, { client: qc }, children);
}

describe("Physics step honesty (M5.5 C2)", () => {
  it("velocity legend is explicitly illustrative (pre-solve) — no fabricated m/s range", () => {
    // Codex R0 P1-2: the Physics viewport contour is a blueprint-scaled preview
    // (kernel overrides the VTP range), so the legend must NOT show a numeric
    // m/s value as if measured — it carries a 示意 badge instead.
    render(<PhysicsVelocityLegend />);
    const legend = screen.getByTestId("v4-physics-velocity-legend");
    expect(legend.textContent).toContain("示意");
    expect(legend.textContent).not.toContain("m/s");
    expect(legend.textContent).not.toContain("40");
  });

  it("does not render the fabricated Re/Pr dimensionless claim", () => {
    render(<ModeRendererPhysics caseId={null} />, { wrapper });
    expect(screen.queryByText(/Re 8\.4e5/)).toBeNull();
    expect(screen.queryByText(/Pr 0\.71/)).toBeNull();
  });
});

describe("Mesh step honesty (M5.5 C2)", () => {
  it("an unmeshed case shows 尚无网格指标, not a fabricated cell-count", () => {
    const { container } = render(<ModeRendererMesh caseId={undefined} />, {
      wrapper,
    });
    expect(container.textContent).toContain("尚无网格指标");
    expect(container.textContent).not.toContain("18.86");
    expect(container.textContent).not.toContain("skew 0.128");
  });
});

describe("Solver step honesty (M5.5 C2)", () => {
  it("an un-run case shows 未开始 + honest temperature state, no fabricated KPIs", () => {
    const { container } = render(<ModeRendererSolver caseId={null} />, {
      wrapper,
    });
    // iter overlay: real (0) → 未开始, not the fabricated 1250/2000 · 00:12:14
    expect(container.textContent).toContain("未开始");
    expect(container.textContent).not.toContain("1250");
    expect(container.textContent).not.toContain("00:12:14");
    // temperature: NEUTRAL no-data state (Codex R0 P1-1 — must not claim "no
    // energy equation", which is false for thermal solvers), not a fake 96.4 °C
    const temp = screen.getByTestId("v4-solver-temperature-panel");
    expect(temp.textContent).toContain("暂无温度数据");
    expect(temp.textContent).not.toContain("不可压缩求解无能量方程");
    expect(temp.textContent).not.toContain("96.4");
    // the fake temperature chart component is gone
    expect(screen.queryByTestId("v4-solver-temperature-chart")).toBeNull();
  });

  it("solver KPI strip reports real run-truth, not fabricated domain KPIs", () => {
    const { container } = render(
      <KpiStripV4 activeStep="solver" caseId={null} />,
      { wrapper },
    );
    // no case/run → an honest pending placeholder (等待算例 / 待求解), never the
    // fabricated 18.76M / 248.6 Pa / 3.62 kg/s / 96.4 °C domain KPIs.
    expect(container.textContent).toMatch(/等待算例|待求解/);
    expect(container.textContent).not.toContain("18.76");
    expect(container.textContent).not.toContain("248.6");
    expect(container.textContent).not.toContain("出口温度");
    expect(container.textContent).not.toContain("质量流量");
  });
});

describe("DOE step honesty (M5.5 C3)", () => {
  it("shows a prominent illustrative banner — the fabricated optima are not presented as truth", () => {
    render(<ModeRendererDoe />);
    const banner = screen.getByTestId("v4-mode-doe-illustrative-banner");
    expect(banner.textContent).toContain("示意");
    expect(banner.textContent).toContain("非真实寻优结果");
  });

  it("DOE KPI strip shows an honest placeholder, not fabricated optima", () => {
    const { container } = render(
      <KpiStripV4 activeStep="doe" caseId="case-x" />,
      { wrapper },
    );
    // no fabricated 212.6 Pa / 94.1 °C / 18h42m "V-12 winner" presented as truth
    expect(container.textContent).toContain("示意");
    expect(container.textContent).not.toContain("212.6");
    expect(container.textContent).not.toContain("18h42m");
    expect(container.textContent).not.toContain("V-12");
  });
});
