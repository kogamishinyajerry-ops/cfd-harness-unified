import { GEOMETRY_REAL_CAD_ASSEMBLY } from "./geometryBlueprint";

export interface ImportBlueprintSource {
  id: string;
  name: string;
  kind: "STEP" | "STL" | "CSV" | "JSON";
  size: string;
  status: "accepted" | "review" | "blocked";
  detail: string;
}

export interface ImportBlueprintCheck {
  label: string;
  value: string;
  status: "PASS" | "REVIEW" | "BLOCKED";
  detail: string;
}

export interface ImportBlueprintCard {
  title: string;
  facts: Array<{
    label: string;
    value: string;
    tone?: "healthy" | "warn" | "crit" | "neutral";
  }>;
  footer?: string;
  cta?: string;
  secondaryCta?: string;
  ctaTone?: "active" | "neutral";
}

export const IMPORT_BLUEPRINT_TASK = {
  sourceImage: ".planning/blueprints/v3/02-import.png",
  pageTask: "把外部 CAD / 网格源文件转成可审计的 case 摄入清单",
  v4Interpretation:
    "导入页不是空上传入口，而是来源文件、单位、拓扑、分件语义和人工采纳 gate 的高密度工作台。",
  primaryPreview: GEOMETRY_REAL_CAD_ASSEMBLY,
} as const;

export const IMPORT_BLUEPRINT_SOURCES: ImportBlueprintSource[] = [
  {
    id: "catia-step",
    name: "0507_APU.step",
    kind: "STEP",
    size: "42.8 MB",
    status: "accepted",
    detail: "CATIA export · 28 authored parts",
  },
  {
    id: "binary-stl",
    name: "individual_binary/*.stl",
    kind: "STL",
    size: "31.4 MB",
    status: "accepted",
    detail: "surface panels · patch names preserved",
  },
  {
    id: "material-map",
    name: "material_map.csv",
    kind: "CSV",
    size: "18 KB",
    status: "review",
    detail: "2 unmapped accessories need user label",
  },
  {
    id: "unit-sidecar",
    name: "units_sidecar.json",
    kind: "JSON",
    size: "6 KB",
    status: "accepted",
    detail: "mm source · solver scale 0.001 m",
  },
];

export const IMPORT_BLUEPRINT_CHECKS: ImportBlueprintCheck[] = [
  {
    label: "文件类型",
    value: "STEP / STL / CSV / JSON",
    status: "PASS",
    detail: "允许的工程输入格式",
  },
  {
    label: "单位与比例",
    value: "mm -> m",
    status: "PASS",
    detail: "比例因子 0.001 已记录",
  },
  {
    label: "拓扑水密性",
    value: "27/28 parts",
    status: "REVIEW",
    detail: "附件小面需要人工确认",
  },
  {
    label: "分件语义",
    value: "28 parts",
    status: "PASS",
    detail: "保留源 CAD 分件名",
  },
  {
    label: "TrustGate",
    value: "manual accept",
    status: "REVIEW",
    detail: "建议不会自动写入 case",
  },
];

export const IMPORT_BLUEPRINT_KPIS = {
  fileCount: IMPORT_BLUEPRINT_SOURCES.length,
  acceptedCount: IMPORT_BLUEPRINT_SOURCES.filter((s) => s.status === "accepted")
    .length,
  reviewCount: IMPORT_BLUEPRINT_SOURCES.filter((s) => s.status === "review")
    .length,
  partCount: GEOMETRY_REAL_CAD_ASSEMBLY.partCount,
  sourceScale: "0.001",
} as const;

export const IMPORT_BLUEPRINT_RIGHT_CARDS: ImportBlueprintCard[] = [
  {
    title: "来源完整度",
    facts: [
      { label: "文件", value: `${IMPORT_BLUEPRINT_KPIS.fileCount} 项` },
      {
        label: "已接受",
        value: `${IMPORT_BLUEPRINT_KPIS.acceptedCount} 项`,
        tone: "healthy",
      },
      {
        label: "待确认",
        value: `${IMPORT_BLUEPRINT_KPIS.reviewCount} 项`,
        tone: "warn",
      },
    ],
    footer: "导入建议仅进入 staging，人工采纳后才写 case",
    cta: "查看证据",
    ctaTone: "active",
  },
  {
    title: "单位与比例",
    facts: [
      { label: "源单位", value: "mm" },
      { label: "solver 单位", value: "m" },
      { label: "scale", value: IMPORT_BLUEPRINT_KPIS.sourceScale },
    ],
    footer: "scale 来源写入 provenance ledger",
    cta: "检查单位",
  },
  {
    title: "分件命名",
    facts: [
      { label: "CAD parts", value: `${IMPORT_BLUEPRINT_KPIS.partCount}` },
      { label: "patch names", value: "preserved", tone: "healthy" },
      { label: "未映射", value: "2", tone: "warn" },
    ],
    footer: "保持 CATIA / STAR-CCM 来源可追溯",
    cta: "人工标注",
  },
];
