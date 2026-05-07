// DEC-V61-142 (N3.3) · Physics commit wire types.
//
// Mirrors backend ui/backend/schemas/material_contract.py +
// regime_contract.py. NEVER edited manually beyond the comments
// here — schema changes flow backend-first.

export type RegimeKind =
  | "laminar"
  | "RANS-RAS"
  | "RANS-kOmegaSST"
  | "LES-stub";

export interface FluidProperties {
  name: string;
  density: number;
  kinematic_viscosity: number;
  prandtl: number | null;
}

export interface ThermalProperties {
  specific_heat: number;
  thermal_conductivity: number;
}

export interface MaterialContract {
  kind: "preset" | "custom";
  preset_id: string | null;
  fluid: FluidProperties;
  thermal: ThermalProperties | null;
  citation: string | null;
  authored_at: string;
}

export interface ApplicabilityBounds {
  re_min: number | null;
  re_max: number | null;
  mach_max: number | null;
  y_plus_target: number | null;
}

export interface RegimeContract {
  kind: "preset" | "custom";
  preset_id: string | null;
  regime: RegimeKind;
  applicability: ApplicabilityBounds;
  citation: string | null;
  authored_at: string;
}

export interface PhysicsCommitRequest {
  material: MaterialContract;
  regime: RegimeContract;
}

export interface PhysicsCommitResponse {
  case_id: string;
  written_paths: string[];
  dict_texts: Record<string, string>;
  committed_at: string;
}

/** Frontend-only library mirror — keeps the dropdown working without
 *  a separate fetch. Values match the backend library; tests assert
 *  citation parity. */
export interface MaterialPresetView {
  preset_id: string;
  display_name: string;
  citation: string;
  fluid: FluidProperties;
  thermal: ThermalProperties | null;
  notes?: string;
}

export interface RegimePresetView {
  preset_id: string;
  display_name: string;
  citation: string;
  regime: RegimeKind;
  applicability: ApplicabilityBounds;
  notes?: string;
}
