import { V4_PALETTE } from "@/theme/industrial_minimalist";

export interface GeometryBlueprintPart {
  id: string;
  labelZh: string;
  labelEn: string;
  count: number;
  color: string;
}

export interface GeometryBlueprintTab {
  id: "cad" | "model";
  label: string;
}

export interface GeometryBlueprintTool {
  id:
    | "repair"
    | "simplify"
    | "gap"
    | "imprint"
    | "wrap"
    | "extract"
    | "boolean"
    | "measure"
    | "view"
    | "display";
  label: string;
  glyph: string;
}

export interface GeometryBlueprintCallout {
  id: "inlet" | "fan" | "heat" | "shell" | "outlet";
  label: string;
  color: string;
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  labelX: number;
  labelY: number;
}

export interface GeometryBlueprintRightCard {
  title: string;
  confidencePct: number;
  facts: Array<{
    label: string;
    value: string;
    tone?: "healthy" | "warn" | "crit" | "neutral";
  }>;
  footer?: string;
}

export interface GeometryBlueprintScene {
  kind: "exploded-apu-bitmap";
  imageUrl: string;
  sourceBlueprint: string;
}

export const GEOMETRY_BLUEPRINT_SUMMARY = {
  partCount: 17,
  instanceCount: 2,
  gapCount: 2,
  toleranceMm: 2.0,
  estimatedCellsM: 18.76,
} as const;

export const GEOMETRY_BLUEPRINT_SCENE: GeometryBlueprintScene = {
  kind: "exploded-apu-bitmap",
  imageUrl: "/blueprints/v4/geometry-apu-exploded.png",
  sourceBlueprint: "ChatGPT Image 2026年5月18日 22_58_28 (2).png",
} as const;

export const GEOMETRY_BLUEPRINT_TABS: GeometryBlueprintTab[] = [
  { id: "cad", label: "几何与 CAD 准备" },
  { id: "model", label: "模型设置" },
];

export const GEOMETRY_BLUEPRINT_TOOLBAR: GeometryBlueprintTool[] = [
  { id: "repair", label: "修复", glyph: "↔" },
  { id: "simplify", label: "简化", glyph: "◇" },
  { id: "gap", label: "缝隙检查", glyph: "⊕" },
  { id: "imprint", label: "印模", glyph: "▧" },
  { id: "wrap", label: "包裹", glyph: "□" },
  { id: "extract", label: "区域提取", glyph: "⌘" },
  { id: "boolean", label: "布尔", glyph: "⬡" },
  { id: "measure", label: "测量", glyph: "⌁" },
  { id: "view", label: "视图", glyph: "◉" },
  { id: "display", label: "显示", glyph: "▱" },
];

export const GEOMETRY_BLUEPRINT_PARTS: GeometryBlueprintPart[] = [
  {
    id: "inlet-shell",
    labelZh: "进气壳体",
    labelEn: "Inlet shell",
    count: 3,
    color: V4_PALETTE.cadParts.inletShell,
  },
  {
    id: "compressor",
    labelZh: "压气机",
    labelEn: "Compressor",
    count: 4,
    color: V4_PALETTE.cadParts.compressor,
  },
  {
    id: "combustor",
    labelZh: "燃烧室",
    labelEn: "Combustor",
    count: 2,
    color: V4_PALETTE.cadParts.combustor,
  },
  {
    id: "turbine",
    labelZh: "涡轮段",
    labelEn: "Turbine section",
    count: 3,
    color: V4_PALETTE.cadParts.turbine,
  },
  {
    id: "nozzle",
    labelZh: "喷管",
    labelEn: "Nozzle",
    count: 2,
    color: V4_PALETTE.cadParts.nozzle,
  },
  {
    id: "mounts",
    labelZh: "安装支架",
    labelEn: "Mount brackets",
    count: 2,
    color: V4_PALETTE.cadParts.bracket,
  },
  {
    id: "accessory",
    labelZh: "附件箱",
    labelEn: "Accessory box",
    count: 1,
    color: V4_PALETTE.cadParts.gearbox,
  },
];

export const GEOMETRY_BLUEPRINT_CALLOUTS: GeometryBlueprintCallout[] = [
  {
    id: "inlet",
    label: "入口",
    color: V4_PALETTE.active,
    x1: 154,
    y1: 190,
    x2: 96,
    y2: 142,
    labelX: 44,
    labelY: 118,
  },
  {
    id: "fan",
    label: "风扇区",
    color: V4_PALETTE.brand,
    x1: 256,
    y1: 134,
    x2: 232,
    y2: 70,
    labelX: 194,
    labelY: 48,
  },
  {
    id: "heat",
    label: "散热件",
    color: V4_PALETTE.bcTypes.rotor,
    x1: 396,
    y1: 190,
    x2: 440,
    y2: 242,
    labelX: 410,
    labelY: 248,
  },
  {
    id: "shell",
    label: "壳体",
    color: V4_PALETTE.healthy,
    x1: 532,
    y1: 104,
    x2: 590,
    y2: 84,
    labelX: 590,
    labelY: 68,
  },
  {
    id: "outlet",
    label: "出口",
    color: V4_PALETTE.bcTypes.outlet,
    x1: 506,
    y1: 178,
    x2: 584,
    y2: 180,
    labelX: 588,
    labelY: 164,
  },
];

export const GEOMETRY_BLUEPRINT_RIGHT_CARDS: GeometryBlueprintRightCard[] = [
  {
    title: "自动识别零件",
    confidencePct: 94,
    facts: [
      {
        label: "已识别",
        value: `${GEOMETRY_BLUEPRINT_SUMMARY.partCount} 个零件`,
        tone: "healthy",
      },
    ],
    footer: "AI 建议需用户采纳后生效",
  },
  {
    title: "缝隙检查",
    confidencePct: 91,
    facts: [{ label: "检测到", value: "2 处缝隙", tone: "warn" }],
    footer: "建议检查薄壁与装配接缝",
  },
  {
    title: "包裹建议",
    confidencePct: 92,
    facts: [
      {
        label: "建议包裹尺寸",
        value: `${GEOMETRY_BLUEPRINT_SUMMARY.toleranceMm.toFixed(1)} mm`,
      },
    ],
    footer: "用于后续流体域抽取",
  },
  {
    title: "流体域提取",
    confidencePct: 93,
    facts: [{ label: "建议", value: "自动提取流体域" }],
    footer: "先预览，不直接写入 case",
  },
];

export function hasAuthoredCadParts(partLikeCount: number | null | undefined): boolean {
  return (partLikeCount ?? 0) >= 2;
}
