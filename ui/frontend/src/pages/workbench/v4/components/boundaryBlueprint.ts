import { V4_PALETTE } from "@/theme/industrial_minimalist";

export interface BoundaryBlueprintType {
  id: "inlet" | "outlet" | "hot-wall" | "rotor-zone" | "wall";
  labelZh: string;
  labelEn: string;
  count: number;
  color: string;
}

export interface BoundaryBlueprintTreeCount {
  id: BoundaryBlueprintType["id"] | "unidentified";
  labelZh: string;
  count: number;
  status: "ok" | "warn";
}

export const BOUNDARY_BLUEPRINT_KPIS = {
  inletCount: 28,
  outletCount: 27,
  wallCount: 6,
  rotorCount: 1,
} as const;

export const BOUNDARY_BLUEPRINT_RECOGNITION = {
  recognized: 61,
  total: 62,
  unknown: 1,
} as const;

export const BOUNDARY_BLUEPRINT_TYPES: BoundaryBlueprintType[] = [
  {
    id: "inlet",
    labelZh: "入口",
    labelEn: "Inlet",
    count: BOUNDARY_BLUEPRINT_KPIS.inletCount,
    color: V4_PALETTE.bcTypes.inlet,
  },
  {
    id: "outlet",
    labelZh: "出口",
    labelEn: "Outlet",
    count: BOUNDARY_BLUEPRINT_KPIS.outletCount,
    color: V4_PALETTE.bcTypes.outlet,
  },
  {
    id: "hot-wall",
    labelZh: "热壁面",
    labelEn: "Hot wall",
    count: 1,
    color: V4_PALETTE.crit,
  },
  {
    id: "rotor-zone",
    labelZh: "转子域",
    labelEn: "Rotor zone",
    count: BOUNDARY_BLUEPRINT_KPIS.rotorCount,
    color: V4_PALETTE.bcTypes.rotor,
  },
  {
    id: "wall",
    labelZh: "壁面",
    labelEn: "Wall",
    count: 4,
    color: V4_PALETTE.textSecondary,
  },
];

export const BOUNDARY_BLUEPRINT_TREE_COUNTS: BoundaryBlueprintTreeCount[] = [
  ...BOUNDARY_BLUEPRINT_TYPES.map((type) => ({
    id: type.id,
    labelZh: type.labelZh,
    count: type.count,
    status: "ok" as const,
  })),
  {
    id: "unidentified",
    labelZh: "未识别",
    count: BOUNDARY_BLUEPRINT_RECOGNITION.unknown,
    status: "warn",
  },
];
