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
import { ModeRendererBoundary } from "../ModeRendererBoundary";
import { KpiStripV4 } from "../../KpiStripV4";
import { LeftRailV4 } from "../../LeftRailV4";
import { RightPanelV4 } from "../../RightPanelV4";

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
    // temperature: FULLY renderer-scoped neutral state (Codex R0/R1 P1-1 — must
    // claim nothing about the run or physics), not a fake 96.4 °C
    const temp = screen.getByTestId("v4-solver-temperature-panel");
    expect(temp.textContent).toContain("温度时程暂未接入");
    expect(temp.textContent).not.toContain("不可压缩求解无能量方程");
    expect(temp.textContent).not.toContain("当前运行未输出");
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
    const { container } = render(<ModeRendererDoe />);
    const banner = screen.getByTestId("v4-mode-doe-illustrative-banner");
    expect(banner.textContent).toContain("示意");
    expect(banner.textContent).toContain("非真实寻优结果");
    // Codex R2 P2: no concrete "最优解 V-12" winner presented as a real optimum.
    expect(container.textContent).not.toContain("最优解");
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

describe("Boundary step honesty (M5.5 C4)", () => {
  it("no-patches case shows pending states, not fabricated 61/62 + per-type counts", () => {
    const { container } = render(<ModeRendererBoundary caseId={undefined} />, {
      wrapper,
    });
    // the fabricated recognition (61/62) + tree counts (入口×28 …) must be gone
    expect(container.textContent).toContain("待识别");
    expect(container.textContent).not.toContain("61/62");
    expect(container.textContent).not.toContain("61/");
  });

  it("boundary KPI strip with no patches shows honest placeholders, not 28/27/6/1", () => {
    const { container } = render(
      <KpiStripV4 activeStep="boundary" caseId="case-x" />,
      { wrapper },
    );
    // un-derived case → honest 待识别/—, never fabricated inlet 28 / outlet 27
    expect(container.textContent).toContain("待识别");
    expect(container.textContent).not.toContain("28");
    expect(container.textContent).not.toContain("27");
  });

  // Codex C4 P1: the fake also rendered in the shell (left rail + right panel),
  // not only the center renderer / KPI strip. These guard the whole boundary
  // surface against a silent re-fake.
  it("left rail boundary section shows 待识别, not fabricated 61/62 + 入口×28", () => {
    const { container } = render(
      <LeftRailV4 activeStep="boundary" onStepChange={() => {}} caseId="case-x" />,
      { wrapper },
    );
    expect(container.textContent).toContain("待识别");
    expect(container.textContent).not.toContain("61/62");
    expect(container.textContent).not.toContain("入口×28");
  });

  it("right panel boundary with no patches shows a single honest 待识别 card, not AI 识别完成 98.4%", () => {
    const { container } = render(
      <RightPanelV4 activeStep="boundary" caseId="case-x" />,
      { wrapper },
    );
    expect(container.textContent).toContain("待识别");
    expect(container.textContent).not.toContain("98.4");
    expect(container.textContent).not.toContain("识别完成");
  });
});

describe("Boundary step surfaces derived BCs (DEC-V61-206 deriver)", () => {
  // A derived WorkbenchBasics mirroring the turbine cascade — exactly what
  // the manifest→WorkbenchBasics deriver returns for an imported case that
  // has been through setup-bc. Seeded into the query cache so the boundary
  // step renders the REAL patches + BC values instead of 待识别.
  const derivedBasics = {
    case_id: "turbine",
    display_name: "turbine",
    provenance: "derived",
    dimension: 3,
    patches: [
      { id: "inlet", role: "inlet", location: "derived", label_zh: "inlet", label_en: "inlet" },
      { id: "outlet", role: "outlet", location: "derived", label_zh: "outlet", label_en: "outlet" },
      { id: "blade", role: "wall", location: "derived", label_zh: "blade", label_en: "blade" },
    ],
    boundary_conditions: [
      {
        field: "U",
        quantity: "velocity",
        units: "m/s",
        per_patch: {
          inlet: { type: "fixedValue", value: [1, 0, 0], display_zh: "U=(1, 0, 0)" },
          outlet: { type: "zeroGradient", display_zh: "∂U/∂n = 0" },
          blade: { type: "noSlip", display_zh: "U = 0" },
        },
      },
      {
        field: "p",
        quantity: "kinematic_pressure",
        units: "m^2/s^2",
        per_patch: {
          outlet: { type: "fixedValue", value: 0, display_zh: "p = 0" },
        },
      },
    ],
    materials: [],
    derived: [],
  };

  function seededWrapper() {
    const qc = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    qc.setQueryData(["v4-ctx-basics", "turbine"], derivedBasics);
    return ({ children }: { children: ReactNode }) =>
      createElement(QueryClientProvider, { client: qc }, children);
  }

  it("shows the real per-patch U BC values + a 派生自算例 provenance badge, not 待识别", () => {
    const { container } = render(<ModeRendererBoundary caseId="turbine" />, {
      wrapper: seededWrapper(),
    });
    // real patch count, not 待识别
    expect(container.textContent).toContain("边界面 · 3 项");
    // derived provenance is labelled (not hand-authored, not fabricated)
    expect(screen.getByTestId("v4-mode-boundary-provenance").textContent).toContain(
      "派生自算例",
    );
    // the ACTUAL BC values are surfaced — "标注出来你怎么设置的边界条件"
    const bc = screen.getByTestId("v4-mode-boundary-bc-values");
    expect(bc.textContent).toContain("U=(1, 0, 0)");
    expect(bc.textContent).toContain("∂U/∂n = 0");
    expect(bc.textContent).toContain("U = 0");
  });
});
