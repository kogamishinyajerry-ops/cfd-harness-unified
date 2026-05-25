import { V4_CFD_COLORMAP, V4_PALETTE } from "@/theme/industrial_minimalist";
import type { ModeTab } from "./ModeTabStrip";

export interface PostBlueprintMiniChart {
  id: "pressure" | "velocity" | "temperature";
  label: string;
  unit: string;
  color: string;
  samples: number[];
}

export interface PostBlueprintRightCard {
  title: string;
  facts: Array<{
    label: string;
    value: string;
    tone?: "healthy" | "warn" | "crit" | "neutral";
  }>;
  footer?: string;
  cta?: string;
  ctaTone?: "active" | "neutral";
}

export const POST_BLUEPRINT_TABS: ModeTab[] = [
  { id: "pv", label: "逐层 PV" },
  { id: "iso", label: "等值面" },
  { id: "analysis", label: "分析" },
  { id: "video", label: "视频" },
  { id: "render", label: "渲染" },
];

export const POST_BLUEPRINT_KPIS = {
  pressurePa: 248.6,
  massFlowKgS: 3.62,
  temperatureC: 96.4,
  progressPct: 65,
  gainPct: 4.2,
} as const;

// DEC-V61-205 (M5 C3): POST_BLUEPRINT_VERDICT (the hardcoded "通过 · +4.2%"
// PASS) was removed — the Post verdict pill now renders the REAL backend
// gold-vs-measured verdict via useComparisonVerdict, or an honest no-baseline
// state. A truth-chain workbench must not ship a fabricated PASS.

// DEC-V61-205 (M5 C4): these three profile waveforms are ILLUSTRATIVE design
// tokens only — the workbench has no per-quantity profile source for a generic
// imported case. ModeRendererPost renders them with an explicit "示意" badge +
// muted styling (illustrative prop) so they never masquerade as run data. The
// adjacent radial gauge below is now driven by REAL residual convergence
// (useResidualSeries), so POST_BLUEPRINT_RADIAL_GAUGE.valuePct is a retired
// blueprint value kept only for the contract test.
export const POST_BLUEPRINT_MINI_CHARTS: PostBlueprintMiniChart[] = [
  {
    id: "pressure",
    label: "压力剖面",
    unit: "Pa",
    color: V4_CFD_COLORMAP[4],
    samples: [216, 224, 232, 238, 242, 245, 247, 248, 248.2, 248.5, 248.6],
  },
  {
    id: "velocity",
    label: "速度剖面",
    unit: "m/s",
    color: V4_CFD_COLORMAP[1],
    samples: [22.4, 26.1, 30.4, 34.8, 37.5, 39.6, 40.8, 41.6, 42.1, 42.4, 42.6],
  },
  {
    id: "temperature",
    label: "温度剖面",
    unit: "°C",
    color: V4_PALETTE.warn,
    samples: [88.1, 90.2, 91.8, 93.0, 94.0, 94.8, 95.3, 95.8, 96.1, 96.3, 96.4],
  },
];

export const POST_BLUEPRINT_RADIAL_GAUGE = {
  label: "通过率",
  valuePct: 65,
  color: V4_PALETTE.healthy,
} as const;

export const POST_BLUEPRINT_RIGHT_CARDS: PostBlueprintRightCard[] = [
  {
    title: "对比基准 · 通过",
    facts: [
      { label: "压降", value: "248.6 Pa" },
      { label: "流量", value: "3.62 kg/s", tone: "healthy" },
      { label: "温度", value: "96.4 °C" },
    ],
    footer: "基准库 KJ66-Baseline · 自动对比完成",
  },
  {
    title: "增益 +4.2%",
    facts: [
      { label: "流量增益", value: "+4.2 %", tone: "healthy" },
      { label: "温度偏差", value: "+0.8 %" },
      { label: "覆盖率", value: "65 %" },
    ],
    footer: "与基准截面流量对比 · 稳定区间",
  },
  {
    title: "导出 PDF",
    facts: [
      { label: "视图", value: "PV + 曲线" },
      { label: "证据", value: "表面场" },
      { label: "状态", value: "就绪", tone: "healthy" },
    ],
    cta: "导出 PDF",
    ctaTone: "active",
    footer: "报告包包含主视图、剖面曲线、验收摘要",
  },
];
