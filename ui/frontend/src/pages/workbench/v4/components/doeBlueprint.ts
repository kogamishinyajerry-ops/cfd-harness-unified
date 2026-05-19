import { V4_CFD_COLORMAP, V4_PALETTE } from "@/theme/industrial_minimalist";

export interface DoeBlueprintSample {
  id: string;
  variableLabel: string;
  pressurePa: number;
  temperatureC: number;
  deltaPct: number;
  optimal?: boolean;
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

export interface DoeBlueprintToolbarItem {
  id: "search" | "status" | "view" | "sort" | "settings";
  label: string;
}

export interface DoeBlueprintTreeSection {
  label: string;
  items: Array<{
    label: string;
    value?: string;
    status?: "ok" | "warn" | "active" | "muted";
  }>;
}

export const DOE_BLUEPRINT_TOOLBAR: DoeBlueprintToolbarItem[] = [
  { id: "search", label: "搜索方案" },
  { id: "status", label: "全部状态" },
  { id: "view", label: "视图" },
  { id: "sort", label: "排序：综合评分" },
  { id: "settings", label: "设置" },
];

export const DOE_BLUEPRINT_TASK = {
  sourceImage: "AI CFD workbench Blueprint image 8 · design exploration",
  sourceCompanion:
    ".planning/transitions/2026-05-18_blueprint_read.md#image-8-design-exploration",
  pageTask:
    "设计探索页用 3x3 真实 CAD/场缩略图矩阵承载样点对比，并在下方保留 Pareto scatter",
  thumbnailRenderer: "ViewportV4 + /blueprints/v4/apu-cad-assembly.glb",
  forbiddenThumbnailFallback:
    "IndustrialBoxScene / StreamlineField hand-drawn SVG thumbnail",
} as const;

export const DOE_BLUEPRINT_KPIS = {
  sampleCount: 28,
  completedCount: 28,
  runningCount: 0,
  queuedCount: 0,
  bestPressurePa: 212.6,
  bestTemperatureC: 94.1,
  bestFlowM3S: 18.42,
  elapsedComputeTime: "16 h 08 m",
  remainingComputeTime: "2 h 34 m",
} as const;

export const DOE_BLUEPRINT_VISIBLE_SAMPLES: DoeBlueprintSample[] = [
  {
    id: "V-07",
    variableLabel: "进风口面积 +20%",
    pressurePa: 298.7,
    temperatureC: 98.8,
    deltaPct: 1.1,
    seed: 3,
  },
  {
    id: "V-08",
    variableLabel: "进风口面积 +40%",
    pressurePa: 262.1,
    temperatureC: 96.3,
    deltaPct: 2.4,
    seed: 7,
  },
  {
    id: "V-09",
    variableLabel: "风道角度 +5°",
    pressurePa: 231.4,
    temperatureC: 95.7,
    deltaPct: 3.0,
    seed: 11,
  },
  {
    id: "V-10",
    variableLabel: "风道角度 +10°",
    pressurePa: 218.9,
    temperatureC: 94.9,
    deltaPct: 3.6,
    seed: 13,
  },
  {
    id: "V-11",
    variableLabel: "风扇转速 +10%",
    pressurePa: 247.5,
    temperatureC: 93.6,
    deltaPct: 3.2,
    seed: 17,
  },
  {
    id: "V-12",
    variableLabel: "风扇转速 +20%",
    pressurePa: DOE_BLUEPRINT_KPIS.bestPressurePa,
    temperatureC: DOE_BLUEPRINT_KPIS.bestTemperatureC,
    deltaPct: 4.2,
    optimal: true,
    seed: 19,
  },
  {
    id: "V-13",
    variableLabel: "散热片间距 -10%",
    pressurePa: 226.3,
    temperatureC: 95.4,
    deltaPct: 3.7,
    seed: 23,
  },
  {
    id: "V-14",
    variableLabel: "网格等级（中→细）",
    pressurePa: 214.8,
    temperatureC: 94.0,
    deltaPct: 4.0,
    seed: 29,
  },
  {
    id: "V-15",
    variableLabel: "出口面积 +10%",
    pressurePa: 195.4,
    temperatureC: 96.8,
    deltaPct: 2.9,
    seed: 31,
  },
];

export const DOE_BLUEPRINT_SCATTER_POINTS = [
  ...DOE_BLUEPRINT_VISIBLE_SAMPLES,
];

export const DOE_BLUEPRINT_VERDICT = {
  selectedId: "V-12",
  label: "V-12 最优解",
  subtitle: "压降与最高温度之间取得最佳平衡",
} as const;

export const DOE_BLUEPRINT_SCATTER = {
  xLabel: "压降 Pa",
  yLabel: "温度 °C",
  frontierColor: V4_PALETTE.healthy,
  activeColor: V4_PALETTE.active,
  recommendedColor: V4_CFD_COLORMAP[2],
} as const;

export const DOE_BLUEPRINT_CONFIDENCE = {
  modelPct: 92,
  label: "模型置信度",
} as const;

export const DOE_BLUEPRINT_LEFT_TREE: DoeBlueprintTreeSection[] = [
  {
    label: "参数",
    items: [
      { label: "几何参数", value: "12", status: "muted" },
      { label: "物理参数", value: "8", status: "muted" },
      { label: "数值参数", value: "6", status: "muted" },
    ],
  },
  {
    label: "变量 (16)",
    items: [
      { label: "进风口面积", value: "4", status: "active" },
      { label: "出口面积", value: "2", status: "muted" },
      { label: "风道角度", value: "3", status: "muted" },
      { label: "风扇转速", value: "2", status: "muted" },
      { label: "散热片间距", value: "2", status: "muted" },
    ],
  },
  {
    label: "方案集",
    items: [
      { label: "探索集_01", value: "32", status: "muted" },
      { label: "探索集_02", value: "28", status: "active" },
      { label: "探索集_03", value: "24", status: "muted" },
    ],
  },
  {
    label: "目标函数",
    items: [
      { label: "压降 (Pa)", value: "最小化", status: "muted" },
      { label: "最高温度 (°C)", value: "最小化", status: "muted" },
    ],
  },
  {
    label: "约束",
    items: [
      { label: "最大噪声", value: "< 85 dB(A)", status: "muted" },
      { label: "风扇功耗", value: "< 1.2 kW", status: "muted" },
      { label: "出口温度", value: "< 120 °C", status: "muted" },
    ],
  },
  {
    label: "最优解",
    items: [
      { label: "V-12（探索集_02）", status: "active" },
      { label: "压降", value: "212.6 Pa", status: "ok" },
      { label: "最高温度", value: "94.1 °C", status: "ok" },
    ],
  },
];

export const DOE_BLUEPRINT_RIGHT_CARDS: DoeBlueprintRightCard[] = [
  {
    title: "推荐 5 个设计",
    facts: [
      { label: "基于当前结果", value: "预计更优", tone: "healthy" },
      { label: "建议方向", value: "局部细化" },
    ],
    cta: "查看推荐",
    ctaTone: "active",
    footer: "仅展示候选方向，不自动触发新求解",
  },
  {
    title: "实验比对就绪",
    facts: [
      { label: "方案", value: "V-12", tone: "healthy" },
      { label: "压降", value: "212.6 Pa", tone: "healthy" },
      { label: "最高温度", value: "94.1 °C", tone: "healthy" },
    ],
    cta: "查看比对",
    footer: "9 个样点已进入同一坐标系",
  },
  {
    title: "导出报告",
    facts: [
      { label: "图表", value: "缩略图 + Pareto" },
      { label: "设计数", value: "28" },
    ],
    cta: "生成报告",
    ctaTone: "active",
    footer: "对比最优方案与基线设计",
  },
];
