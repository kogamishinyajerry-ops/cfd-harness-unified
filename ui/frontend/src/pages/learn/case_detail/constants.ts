// Constants shared across LearnCaseDetailPage tabs.
// Extracted 2026-04-25 from LearnCaseDetailPage.tsx (Stage 1 shell-split,
// per Codex industrial-workbench meeting verdict). Behavior unchanged.

import type { ContractStatus } from "@/types/validation";

// Cases with a curated grid-convergence sweep (4 meshes each). Every
// case in the /learn catalog now has one. If a new case is added,
// author 4 mesh_N fixtures and register its density labels here.
export const GRID_CONVERGENCE_CASES: Record<
  string,
  { meshLabel: string; densities: { id: string; label: string; n: number }[] }
> = {
  lid_driven_cavity: {
    meshLabel: "uniform grid N×N",
    densities: [
      { id: "mesh_20", label: "20²", n: 400 },
      { id: "mesh_40", label: "40²", n: 1600 },
      { id: "mesh_80", label: "80²", n: 6400 },
      { id: "mesh_160", label: "160²", n: 25600 },
    ],
  },
  turbulent_flat_plate: {
    meshLabel: "wall-normal cells",
    densities: [
      { id: "mesh_20", label: "20 y-cells", n: 20 },
      { id: "mesh_40", label: "40 y-cells", n: 40 },
      { id: "mesh_80", label: "80 y-cells + 4:1", n: 80 },
      { id: "mesh_160", label: "160 y-cells", n: 160 },
    ],
  },
  backward_facing_step: {
    meshLabel: "recirculation cells",
    densities: [
      { id: "mesh_20", label: "20 cells", n: 20 },
      { id: "mesh_40", label: "40 cells", n: 40 },
      { id: "mesh_80", label: "80 cells", n: 80 },
      { id: "mesh_160", label: "160 cells", n: 160 },
    ],
  },
  circular_cylinder_wake: {
    meshLabel: "azimuthal cells around cylinder",
    densities: [
      { id: "mesh_20", label: "20 azim", n: 20 },
      { id: "mesh_40", label: "40 azim", n: 40 },
      { id: "mesh_80", label: "80 azim", n: 80 },
      { id: "mesh_160", label: "160 azim", n: 160 },
    ],
  },
  duct_flow: {
    meshLabel: "cross-section cells",
    densities: [
      { id: "mesh_20", label: "20² uniform", n: 400 },
      { id: "mesh_40", label: "40² + 2:1", n: 1600 },
      { id: "mesh_80", label: "80² + 4:1", n: 6400 },
      { id: "mesh_160", label: "160²", n: 25600 },
    ],
  },
  differential_heated_cavity: {
    meshLabel: "square cavity N×N + wall grading",
    densities: [
      { id: "mesh_20", label: "20² uniform", n: 400 },
      { id: "mesh_40", label: "40² + 1.5:1", n: 1600 },
      { id: "mesh_80", label: "80² + 4:1", n: 6400 },
      { id: "mesh_160", label: "160² + 4:1", n: 25600 },
    ],
  },
  plane_channel_flow: {
    // Honest labels: the live adapter path is laminar icoFoam at Re_bulk=5600
    // (see knowledge/gold_standards/plane_channel_flow.yaml physics_contract —
    // contract_status is INCOMPATIBLE_WITH_LITERATURE_DISGUISED_AS_COMPATIBLE
    // because laminar N-S cannot reproduce Kim 1987 Re_τ=180 turbulent DNS).
    // Earlier mesh labels ("WR-LES" / "DNS") implied the solver could switch
    // regimes at higher density — it cannot. Labels now just describe mesh
    // count so the UI does not front-run the solver reality.
    meshLabel: "isotropic cubed cells (laminar icoFoam; aspirational turbulent solver path not yet wired)",
    densities: [
      { id: "mesh_20", label: "20³ cells", n: 8000 },
      { id: "mesh_40", label: "40³ cells", n: 64000 },
      { id: "mesh_80", label: "80³ cells", n: 512000 },
      { id: "mesh_160", label: "160³ cells", n: 4096000 },
    ],
  },
  impinging_jet: {
    meshLabel: "radial cells in stagnation region",
    densities: [
      { id: "mesh_20", label: "20 rad", n: 20 },
      { id: "mesh_40", label: "40 rad + 2:1", n: 40 },
      { id: "mesh_80", label: "80 rad + 4:1", n: 80 },
      { id: "mesh_160", label: "160 rad", n: 160 },
    ],
  },
  naca0012_airfoil: {
    meshLabel: "surface cells per side",
    densities: [
      { id: "mesh_20", label: "20 surf + 8-chord", n: 20 },
      { id: "mesh_40", label: "40 surf + 15-chord", n: 40 },
      { id: "mesh_80", label: "80 surf + 40-chord", n: 80 },
      { id: "mesh_160", label: "160 surf", n: 160 },
    ],
  },
  rayleigh_benard_convection: {
    meshLabel: "square cavity + wall packing",
    densities: [
      { id: "mesh_20", label: "20² uniform", n: 400 },
      { id: "mesh_40", label: "40² + 2:1", n: 1600 },
      { id: "mesh_80", label: "80² + 4:1", n: 6400 },
      { id: "mesh_160", label: "160² + 4:1", n: 25600 },
    ],
  },
};

export const STATUS_TEXT: Record<ContractStatus, string> = {
  PASS: "对齐黄金标准",
  HAZARD: "落入带内，但可能是 silent-pass",
  FAIL: "偏离了 tolerance band",
  UNKNOWN: "尚无可对比的测量值",
};

export const STATUS_CLASS: Record<ContractStatus, string> = {
  PASS: "text-contract-pass",
  HAZARD: "text-contract-hazard",
  FAIL: "text-contract-fail",
  UNKNOWN: "text-surface-400",
};

