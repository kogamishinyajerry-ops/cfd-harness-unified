/**
 * V84.5 · per-case sandbox step state · multi-case V5.A extension
 *
 * For each of the 10 Gold-Standard cases, declares the curated outcome
 * shown at each pipeline step in sandbox mode. All text is human-curated
 * (parallels V80 reverse-stop #7 for advisor commentary). No LLM call at
 * runtime · static substrate baked into the bundle.
 */

import type { StepId } from "../pages/workbench/v3/WorkbenchShellV3";

export interface SandboxStepState {
  /** Short label visible in the step transition banner (≤80 chars). */
  banner: string;
  /** Optional 1-line context (≤120 chars) shown below the banner when
   *  the user lingers on the step. NOT used in v0 banner UI · reserved
   *  for V85+ extension. */
  context?: string;
}

const lidDrivenCavity: Record<StepId, SandboxStepState> = {
  1: {
    banner: "Import · 128×128 cartesian geometry · watertight verified",
    context: "Unit square cavity · lid at top moves at U=1",
  },
  2: {
    banner: "Mesh · skewness 0.32 (good) · all 4 walls y+ < 1",
    context: "Cartesian mesh · simpleGrading 2..1..2 wall clustering",
  },
  3: {
    banner: "Physics · INLET (N/A) · LID movingWall · WALLS no-slip",
    context: "Re = 100 · steady incompressible · simpleFoam",
  },
  4: {
    banner: "Solver · simpleFoam · residuals decay (V82.4 4-layer)",
    context: "Watching p · 200 max iters · convergence at ~iter 165",
  },
  5: {
    banner: "Postprocess · 17/17 Ghia points within ±5% · TrustGate PASS",
    context: "max |Δu| = 0.78% · Ghia 1982 reference",
  },
};

const naca0012Airfoil: Record<StepId, SandboxStepState> = {
  1: {
    banner: "Import · NACA 0012 C-mesh · trailing-edge feature captured",
  },
  2: {
    banner: "Mesh · 257×129 C-mesh · y+ < 1 across upper surface",
  },
  3: {
    banner: "Physics · FREESTREAM α=10° · AIRFOIL no-slip · k-ω SST",
  },
  4: {
    banner: "Solver · simpleFoam · Cl convergence to ±0.001 by iter 2000",
  },
  5: {
    banner: "Postprocess · Cl within ±3% of AGARD AR-138 reference",
  },
};

const backwardFacingStep: Record<StepId, SandboxStepState> = {
  1: {
    banner: "Import · backstep geometry · step height h normalized",
  },
  2: {
    banner: "Mesh · ≥40 cells across h · y+ < 1 on lower wall",
  },
  3: {
    banner: "Physics · INLET uniform U · OUTLET zeroGradient · k-ω SST",
  },
  4: {
    banner: "Solver · simpleFoam · reattachment x_r/h stabilizing",
  },
  5: {
    banner: "Postprocess · x_r/h = 6.08 ± 0.05 (Driver-Seegmiller PASS)",
  },
};

const circularCylinderWake: Record<StepId, SandboxStepState> = {
  1: {
    banner: "Import · cylinder diameter D · wake region marked",
  },
  2: {
    banner: "Mesh · O-mesh 80 circ × 25D wake · 120 cells / wavelength",
  },
  3: {
    banner: "Physics · INLET U=1 · CYLINDER no-slip · transient pisoFoam",
  },
  4: {
    banner: "Solver · 5 shedding cycles captured · St stabilizing",
  },
  5: {
    banner: "Postprocess · St = 0.166 (Williamson PASS within ±3%)",
  },
};

const turbulentFlatPlate: Record<StepId, SandboxStepState> = {
  1: { banner: "Import · ZPG flat plate · Re_x = 10⁷ at outlet" },
  2: { banner: "Mesh · 30 prism layers · y+ ≤ 1 wall-resolved" },
  3: { banner: "Physics · INLET turbulent BL · OUTLET zeroGradient" },
  4: { banner: "Solver · simpleFoam · Cf(x=L/2) ±0.5% stable" },
  5: { banner: "Postprocess · log-law slope κ ≈ 0.41 confirmed" },
};

const planeChannelFlow: Record<StepId, SandboxStepState> = {
  1: { banner: "Import · channel half-height δ · cyclic streamwise" },
  2: { banner: "Mesh · Δx+ ≈ 18 Δz+ ≈ 6 · ≥10 cells in y+ < 10" },
  3: { banner: "Physics · cyclic walls + constant body-force drive" },
  4: { banner: "Solver · Re_τ = 180 · bulk Re ≈ 5600 stable" },
  5: { banner: "Postprocess · Reynolds stresses vs MKM 1999 within ±10%" },
};

const impingingJet: Record<StepId, SandboxStepState> = {
  1: { banner: "Import · jet nozzle + impingement plate · H/D = 2" },
  2: { banner: "Mesh · stagnation y+ < 0.5 · ≥5D radial extent" },
  3: { banner: "Physics · NOZZLE inlet U · PLATE wall heat flux q" },
  4: { banner: "Solver · simpleFoam + energy · Nu_0 ±0.5% stable" },
  5: { banner: "Postprocess · Nu_0 ≈ 88 (Cooper 1993 PASS within ±10%)" },
};

const rayleighBenardConvection: Record<StepId, SandboxStepState> = {
  1: { banner: "Import · Ra = 10⁸ box · AR = 1 · gravity vertical" },
  2: { banner: "Mesh · ≥120 vertical (δ_T resolved) · 96² lateral" },
  3: { banner: "Physics · Boussinesq · hot bottom · cold top · adiabatic sides" },
  4: { banner: "Solver · pimpleFoam Boussinesq · ⟨Nu⟩_t stabilizing" },
  5: { banner: "Postprocess · Nu ≈ 27 (Kerr 1996 PASS within ±10%)" },
};

const differentialHeatedCavity: Record<StepId, SandboxStepState> = {
  1: { banner: "Import · 1×1 box · hot left · cold right · adiabatic h/v" },
  2: { banner: "Mesh · ≥40 cells wall-normal each side · simpleGrading clustering" },
  3: { banner: "Physics · Boussinesq · Ra = 10⁵ · Pr = 0.71" },
  4: { banner: "Solver · buoyantSimpleFoam · Nu_hot stabilizing" },
  5: { banner: "Postprocess · Nu_hot ≈ 4.52 (de Vahl Davis PASS within ±2%)" },
};

const ductFlow: Record<StepId, SandboxStepState> = {
  1: { banner: "Import · square duct · streamwise periodic · 4 walls" },
  2: { banner: "Mesh · y+ < 1 on all 4 walls · wall-resolved · NO wall fn" },
  3: { banner: "Physics · cyclic streamwise · pressure-driven · RSM required" },
  4: { banner: "Solver · simpleFoam + LRR · secondary-flow stabilizing" },
  5: { banner: "Postprocess · 8 corner vortices · ~2% U_bulk peak (Gavrilakis)" },
};

const STATES_BY_CASE: Record<string, Record<StepId, SandboxStepState>> = {
  lid_driven_cavity: lidDrivenCavity,
  naca0012_airfoil: naca0012Airfoil,
  backward_facing_step: backwardFacingStep,
  circular_cylinder_wake: circularCylinderWake,
  turbulent_flat_plate: turbulentFlatPlate,
  plane_channel_flow: planeChannelFlow,
  impinging_jet: impingingJet,
  rayleigh_benard_convection: rayleighBenardConvection,
  differential_heated_cavity: differentialHeatedCavity,
  duct_flow: ductFlow,
};

const FALLBACK: Record<StepId, SandboxStepState> = {
  1: { banner: "Import · case geometry preview" },
  2: { banner: "Mesh · curated quality preview" },
  3: { banner: "Physics · curated BC patches" },
  4: { banner: "Solver · synthetic residual stream (V82.4)" },
  5: { banner: "Postprocess · comparator + advisor + provenance" },
};

export function getSandboxStepState(
  caseId: string | null,
  step: StepId,
): SandboxStepState {
  if (caseId && STATES_BY_CASE[caseId]) {
    return STATES_BY_CASE[caseId][step];
  }
  return FALLBACK[step];
}

export const SANDBOX_CURATED_CASES: ReadonlyArray<string> = Object.keys(
  STATES_BY_CASE,
);
