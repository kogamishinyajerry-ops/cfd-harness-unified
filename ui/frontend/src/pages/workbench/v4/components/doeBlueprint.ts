import { V4_CFD_COLORMAP, V4_PALETTE } from "@/theme/industrial_minimalist";

export interface DoeBlueprintSample {
  id: string;
  variableLabel: string;
  pressurePa: number;
  temperatureC: number;
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

export const DOE_BLUEPRINT_KPIS = {
  sampleCount: 28,
  completedCount: 28,
  runningCount: 0,
  queuedCount: 0,
  bestPressurePa: 212.6,
  bestTemperatureC: 94.1,
  estimatedComputeTime: "18 h 42 m",
  elapsedComputeTime: "16 h 08 m",
  remainingComputeTime: "2 h 34 m",
} as const;

export const DOE_BLUEPRINT_VISIBLE_SAMPLES: DoeBlueprintSample[] = [
  {
    id: "V-07",
    variableLabel: "进风口面积 +20%",
    pressurePa: 298.7,
    temperatureC: 98.8,
    seed: 3,
  },
  {
    id: "V-08",
    variableLabel: "进风口面积 +40%",
    pressurePa: 262.1,
    temperatureC: 96.3,
    seed: 7,
  },
  {
    id: "V-09",
    variableLabel: "风道角度 +5°",
    pressurePa: 231.4,
    temperatureC: 95.7,
    seed: 11,
  },
  {
    id: "V-10",
    variableLabel: "风道角度 +10°",
    pressurePa: 218.9,
    temperatureC: 94.9,
    seed: 13,
  },
  {
    id: "V-11",
    variableLabel: "风扇转速 +10%",
    pressurePa: 247.5,
    temperatureC: 93.6,
    seed: 17,
  },
  {
    id: "V-12",
    variableLabel: "风扇转速 +20%",
    pressurePa: DOE_BLUEPRINT_KPIS.bestPressurePa,
    temperatureC: DOE_BLUEPRINT_KPIS.bestTemperatureC,
    optimal: true,
    seed: 19,
  },
  {
    id: "V-13",
    variableLabel: "散热片间距 -10%",
    pressurePa: 226.3,
    temperatureC: 95.4,
    seed: 23,
  },
  {
    id: "V-14",
    variableLabel: "网格等级（中→细）",
    pressurePa: 214.8,
    temperatureC: 94.0,
    seed: 29,
  },
];

export const DOE_BLUEPRINT_SCATTER_POINTS = [
  ...DOE_BLUEPRINT_VISIBLE_SAMPLES,
  {
    id: "V-15",
    variableLabel: "出口面积 +10%",
    pressurePa: 195.4,
    temperatureC: 96.8,
    seed: 31,
  },
  {
    id: "V-16",
    variableLabel: "局部细化",
    pressurePa: 360.0,
    temperatureC: 93.0,
    seed: 37,
  },
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
    title: "推荐 3 个新方案",
    facts: [
      { label: "基于当前结果", value: "预计更优", tone: "healthy" },
      { label: "建议方向", value: "局部细化" },
    ],
    cta: "查看推荐",
    ctaTone: "active",
    footer: "仅展示候选方向，不自动触发新求解",
  },
  {
    title: "发现最优点",
    facts: [
      { label: "方案", value: "V-12", tone: "healthy" },
      { label: "压降", value: "212.6 Pa", tone: "healthy" },
      { label: "最高温度", value: "94.1 °C", tone: "healthy" },
    ],
    cta: "查看详情",
    footer: "建议开展局部细化验证",
  },
  {
    title: "生成对比报告",
    facts: [
      { label: "图表", value: "函数与结论" },
      { label: "设计数", value: "28" },
    ],
    cta: "生成报告",
    ctaTone: "active",
    footer: "对比最优方案与基线设计",
  },
  {
    title: "导出模板",
    facts: [
      { label: "对象", value: "探索设置" },
      { label: "复用", value: "新项目" },
    ],
    cta: "导出模板",
    ctaTone: "active",
    footer: "导出当前探索设置与最优方案导出为模板",
  },
];
