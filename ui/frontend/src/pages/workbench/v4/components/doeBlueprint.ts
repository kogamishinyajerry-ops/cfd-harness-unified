import { V4_CFD_COLORMAP, V4_PALETTE } from "@/theme/industrial_minimalist";
import type { ModeTab } from "./ModeTabStrip";

export interface DoeBlueprintSample {
  id: string;
  pressurePa: number;
  temperatureC: number;
  volumeM3: number;
  deltaPct: number;
  recommended: boolean;
  seed: number;
}

export interface DoeBlueprintRightCard {
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

export const DOE_BLUEPRINT_TABS: ModeTab[] = [
  { id: "samples", label: "样本网格" },
  { id: "pareto", label: "Pareto" },
  { id: "sensitivity", label: "敏感性" },
  { id: "report", label: "报告" },
];

export const DOE_BLUEPRINT_KPIS = {
  sampleCount: 28,
  bestPressurePa: 212.6,
  bestTemperatureC: 94.1,
  bestVolumeM3: 18.42,
  bestGainPct: 4.2,
} as const;

export const DOE_BLUEPRINT_SAMPLES: DoeBlueprintSample[] = [
  {
    id: "S-01",
    pressurePa: 198.7,
    temperatureC: 96.8,
    volumeM3: 16.84,
    deltaPct: -2.1,
    recommended: false,
    seed: 3,
  },
  {
    id: "S-02",
    pressurePa: 222.1,
    temperatureC: 95.1,
    volumeM3: 17.91,
    deltaPct: 0.8,
    recommended: true,
    seed: 7,
  },
  {
    id: "S-03",
    pressurePa: 231.4,
    temperatureC: 94.7,
    volumeM3: 18.18,
    deltaPct: 2.2,
    recommended: true,
    seed: 11,
  },
  {
    id: "S-04",
    pressurePa: 206.8,
    temperatureC: 95.9,
    volumeM3: 17.22,
    deltaPct: -1.0,
    recommended: false,
    seed: 13,
  },
  {
    id: "S-05",
    pressurePa: DOE_BLUEPRINT_KPIS.bestPressurePa,
    temperatureC: DOE_BLUEPRINT_KPIS.bestTemperatureC,
    volumeM3: DOE_BLUEPRINT_KPIS.bestVolumeM3,
    deltaPct: DOE_BLUEPRINT_KPIS.bestGainPct,
    recommended: true,
    seed: 17,
  },
  {
    id: "S-06",
    pressurePa: 248.6,
    temperatureC: 93.6,
    volumeM3: 17.72,
    deltaPct: 0.9,
    recommended: true,
    seed: 19,
  },
  {
    id: "S-07",
    pressurePa: 196.4,
    temperatureC: 96.2,
    volumeM3: 16.51,
    deltaPct: -2.4,
    recommended: false,
    seed: 23,
  },
  {
    id: "S-08",
    pressurePa: 219.2,
    temperatureC: 95.4,
    volumeM3: 17.88,
    deltaPct: 1.5,
    recommended: true,
    seed: 29,
  },
  {
    id: "S-09",
    pressurePa: 235.7,
    temperatureC: 94.8,
    volumeM3: 18.06,
    deltaPct: 2.8,
    recommended: false,
    seed: 31,
  },
];

export const DOE_BLUEPRINT_VERDICT = {
  selectedId: "S-05",
  label: "推荐设计 · S-05",
  subtitle: "5 个候选进入比对 · 设计探索后端待接入",
} as const;

export const DOE_BLUEPRINT_SCATTER = {
  xLabel: "压降 Pa",
  yLabel: "温度 °C",
  frontierColor: V4_PALETTE.healthy,
  activeColor: V4_PALETTE.active,
  recommendedColor: V4_CFD_COLORMAP[2],
} as const;

export const DOE_BLUEPRINT_RIGHT_CARDS: DoeBlueprintRightCard[] = [
  {
    title: "推荐 5 个设计",
    facts: [
      { label: "候选样本", value: "28" },
      { label: "推荐入围", value: "5", tone: "healthy" },
      { label: "当前选择", value: "S-05", tone: "healthy" },
    ],
    footer: "按压降、出口温度、体积流量综合排序",
  },
  {
    title: "实验比对就绪",
    facts: [
      { label: "最佳压降", value: "212.6 Pa" },
      { label: "最佳温度", value: "94.1 °C" },
      { label: "后端状态", value: "待接入", tone: "warn" },
    ],
    footer: "当前为设计探索预览，不自动触发新求解",
  },
  {
    title: "导出报告",
    facts: [
      { label: "矩阵", value: "3 × 3" },
      { label: "散点图", value: "Pareto" },
      { label: "体积流量", value: "18.42 m³", tone: "healthy" },
    ],
    cta: "导出报告",
    ctaTone: "active",
    footer: "报告包包含样本矩阵、Pareto 图和推荐摘要",
  },
];
