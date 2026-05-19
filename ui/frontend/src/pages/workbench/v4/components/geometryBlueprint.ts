import { V4_PALETTE } from "@/theme/industrial_minimalist";

export interface GeometryBlueprintPart {
  id: string;
  labelZh: string;
  labelEn: string;
  count: number;
  color: string;
}

export const GEOMETRY_BLUEPRINT_SUMMARY = {
  partCount: 17,
  instanceCount: 2,
  toleranceMm: 2.0,
  estimatedCellsM: 18.76,
} as const;

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

export function hasAuthoredCadParts(partLikeCount: number | null | undefined): boolean {
  return (partLikeCount ?? 0) >= 2;
}
