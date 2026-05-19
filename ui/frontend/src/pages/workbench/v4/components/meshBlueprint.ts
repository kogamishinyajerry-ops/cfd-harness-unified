import { V4_PALETTE } from "@/theme/industrial_minimalist";

export interface MeshBlueprintHistogram {
  label: string;
  mean: number;
  unit: string;
  bins: number[];
  color: string;
}

export const MESH_BLUEPRINT_HISTOGRAMS: MeshBlueprintHistogram[] = [
  {
    label: "流体距离",
    mean: 0.84,
    unit: "mm",
    bins: [0.18, 0.28, 0.44, 0.68, 0.94, 0.82, 0.56, 0.34, 0.2],
    color: V4_PALETTE.brand,
  },
  {
    label: "表面距离",
    mean: 0.42,
    unit: "mm",
    bins: [0.78, 0.88, 0.72, 0.48, 0.34, 0.24, 0.18, 0.12, 0.08],
    color: V4_PALETTE.healthy,
  },
  {
    label: "单元质量",
    mean: 0.91,
    unit: "q",
    bins: [0.08, 0.14, 0.2, 0.36, 0.54, 0.72, 0.9, 0.84, 0.62],
    color: V4_PALETTE.healthy,
  },
  {
    label: "歪斜度",
    mean: 0.128,
    unit: "max",
    bins: [0.92, 0.66, 0.38, 0.2, 0.12, 0.08, 0.05, 0.04, 0.03],
    color: V4_PALETTE.warn,
  },
  {
    label: "纵横比",
    mean: 8.6,
    unit: ":1",
    bins: [0.22, 0.36, 0.58, 0.82, 0.74, 0.52, 0.36, 0.22, 0.14],
    color: V4_PALETTE.active,
  },
];

export const MESH_BLUEPRINT_NUMERICS = {
  estimatedCellsM: 18.86,
  maxSkewness: 0.128,
  maxNonOrthogonalityDeg: 67.4,
  timeEstimateMin: 28.6,
} as const;
