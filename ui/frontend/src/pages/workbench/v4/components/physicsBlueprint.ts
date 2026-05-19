import { V4_CFD_COLORMAP, V4_PALETTE } from "@/theme/industrial_minimalist";

export interface PhysicsBlueprintTab {
  id: "recommended" | "custom" | "time" | "gravity";
  label: string;
}

export interface PhysicsBlueprintModel {
  name: string;
  family: string;
  note: string;
  recommended?: boolean;
  color: string;
}

export interface PhysicsBlueprintMaterial {
  name: string;
  rho: string;
  mu: string;
}

export const PHYSICS_BLUEPRINT_TABS: PhysicsBlueprintTab[] = [
  { id: "recommended", label: "推荐物理模型" },
  { id: "custom", label: "自定义物理模型" },
  { id: "time", label: "时间格式" },
  { id: "gravity", label: "重力(g)=9.8" },
];

export const PHYSICS_BLUEPRINT_SUMMARY = {
  modelCount: 5,
  materialCount: 5,
  caseType: "稳态流动",
  estimatedCellsM: 28.6,
  recommendedModel: "SST k-ω",
  gravity: 9.8,
} as const;

export const PHYSICS_BLUEPRINT_VELOCITY_RANGE = {
  min: 0,
  max: 40,
} as const;

export const PHYSICS_BLUEPRINT_VELOCITY_RANGE_TUPLE: [number, number] = [
  PHYSICS_BLUEPRINT_VELOCITY_RANGE.min,
  PHYSICS_BLUEPRINT_VELOCITY_RANGE.max,
];

export const PHYSICS_BLUEPRINT_COLORMAP = V4_CFD_COLORMAP;

export const PHYSICS_BLUEPRINT_MODELS: PhysicsBlueprintModel[] = [
  {
    name: "SST k-ω",
    family: "RANS",
    note: "近壁稳定",
    recommended: true,
    color: V4_PALETTE.active,
  },
  {
    name: "Spalart-Allmaras",
    family: "RANS",
    note: "外流快速",
    color: V4_PALETTE.brand,
  },
  {
    name: "k-ε",
    family: "RANS",
    note: "稳健基线",
    color: V4_PALETTE.warn,
  },
  {
    name: "Laminar",
    family: "DNS-lite",
    note: "低 Re",
    color: V4_PALETTE.textSecondary,
  },
  {
    name: "Energy off",
    family: "Thermal",
    note: "等温",
    color: V4_PALETTE.healthy,
  },
];

export const PHYSICS_BLUEPRINT_MATERIALS: PhysicsBlueprintMaterial[] = [
  { name: "空气", rho: "1.225", mu: "1.8e-5" },
  { name: "钛合金", rho: "4506", mu: "—" },
  { name: "钢", rho: "7850", mu: "—" },
  { name: "Inconel", rho: "8190", mu: "—" },
  { name: "隔热层", rho: "2600", mu: "—" },
];
