import { V4_CFD_COLORMAP, V4_PALETTE } from "@/theme/industrial_minimalist";

export interface SolverBlueprintResidualSeries {
  name: "p" | "U" | "T";
  color: string;
  samples: number[];
}

export interface SolverBlueprintRightCard {
  title: string;
  facts: Array<{
    label: string;
    value: string;
    tone?: "healthy" | "warn" | "crit";
  }>;
  footer?: string;
}

export const SOLVER_BLUEPRINT_TASK = {
  sourceImage: ".planning/blueprints/v3/05-solve.png",
  sourceCompanion: ".planning/transitions/2026-05-18_blueprint_read.md#image-1-6",
  pageTask:
    "求解运行页同时呈现真实 CAD/场视口、密集曲线流线、残差/温度 split charts 和 GPU/CPU/MEM telemetry",
  primaryViewport:
    "ViewportV4 geometry.glb + post/surface.vtp + post/streamlines.vtp",
  forbiddenMainSceneFallback:
    "IndustrialBoxScene / StreamlineField hand-drawn SVG scene",
} as const;

export const SOLVER_BLUEPRINT_KPIS = {
  estimatedCellsM: 18.76,
  residualP: 2.3e-5,
  pressurePa: 248.6,
  massFlowKgS: 3.62,
  temperatureC: 96.4,
  progressPct: 65,
  iterCurrent: 1250,
  iterTotal: 2000,
  elapsed: "00:12:14",
} as const;

export const SOLVER_BLUEPRINT_STREAMLINE_COUNT = 72;

export const SOLVER_BLUEPRINT_VELOCITY_RANGE: [number, number] = [0, 40];

export const SOLVER_BLUEPRINT_RESIDUAL_SERIES: SolverBlueprintResidualSeries[] = [
  {
    name: "p",
    color: V4_PALETTE.healthy,
    samples: [
      1.8e-1, 8.6e-2, 3.2e-2, 1.1e-2, 4.9e-3, 1.8e-3, 7.2e-4, 2.9e-4,
      1.1e-4, 5.4e-5, 3.2e-5, SOLVER_BLUEPRINT_KPIS.residualP,
    ],
  },
  {
    name: "U",
    color: V4_CFD_COLORMAP[2],
    samples: [
      2.4e-1, 1.2e-1, 6.4e-2, 2.8e-2, 1.2e-2, 4.8e-3, 1.9e-3, 8.0e-4,
      3.4e-4, 1.6e-4, 7.5e-5, 3.8e-5,
    ],
  },
  {
    name: "T",
    color: V4_CFD_COLORMAP[4],
    samples: [
      1.2e-1, 7.4e-2, 4.6e-2, 2.9e-2, 1.5e-2, 7.4e-3, 3.8e-3, 1.7e-3,
      8.6e-4, 4.2e-4, 1.9e-4, 9.8e-5,
    ],
  },
];

export const SOLVER_BLUEPRINT_TEMPERATURE_HISTORY = [
  74.2, 79.6, 83.1, 86.8, 89.5, 91.7, 93.2, 94.3, 95.1, 95.7, 96.1, 96.4,
] as const;

export const SOLVER_BLUEPRINT_TELEMETRY = {
  gpuPct: 94,
  cpuPct: 71,
  memGb: 48,
  deltaT: "2.5e-4",
} as const;

export const SOLVER_BLUEPRINT_RIGHT_CARDS: SolverBlueprintRightCard[] = [
  {
    title: "收敛趋势良好",
    facts: [
      { label: "残差 p", value: "2.30e-5", tone: "healthy" },
      { label: "趋势", value: "连续下降", tone: "healthy" },
      { label: "进度", value: "65 %" },
    ],
    footer: "基于最近 12 个残差样本 · advisory only",
  },
  {
    title: "通过验证 200 步",
    facts: [
      { label: "窗口", value: "200 iter" },
      { label: "压力", value: "248.6 Pa" },
      { label: "流量", value: "3.62 kg/s" },
    ],
    footer: "未改变求解器状态 · 仅作趋势提示",
  },
  {
    title: "GPU 满载",
    facts: [
      { label: "GPU", value: "94 %", tone: "warn" },
      { label: "CPU", value: "71 %" },
      { label: "MEM", value: "48 GB" },
    ],
    footer: `δt ${SOLVER_BLUEPRINT_TELEMETRY.deltaT} · telemetry preview`,
  },
];
