// Workbench basics · Stage 2 MVP types.
// Mirrors `ui/backend/schemas/workbench_basics.py`. Source data lives in
// `knowledge/workbench_basics/<case_id>.yaml`.

export type PatchRole =
  | "wall"
  | "moving_wall"
  | "inlet"
  | "outlet"
  | "symmetry"
  | "cyclic"
  | "empty"
  | "airfoil"
  | "periodic";

export type PatchLocation =
  | "top"
  | "bottom"
  | "left"
  | "right"
  | "front_back"
  | "inlet"
  | "outlet"
  | "airfoil_upper"
  | "airfoil_lower"
  | "cylinder_surface"
  | "step_face"
  | (string & {});

export interface BBox {
  x_min: number;
  x_max: number;
  y_min: number;
  y_max: number;
  z_min?: number;
  z_max?: number;
}

export interface CharacteristicLength {
  name: string;
  value: number;
  unit: string;
  description_zh?: string;
}

export interface Geometry {
  shape: string; // "rectangle" | "airfoil" | "cylinder" | "step" | ...
  bbox: BBox;
  characteristic_length: CharacteristicLength;
}

export interface Patch {
  id: string;
  role: PatchRole;
  location: PatchLocation;
  label_zh: string;
  label_en: string;
  description_zh?: string;
}

export interface BoundaryConditionPatch {
  type: string;
  value?: number | number[] | string;
  display_zh?: string;
}

export interface BoundaryCondition {
  field: string;
  quantity: string;
  units: string;
  description_zh?: string;
  per_patch: Record<string, BoundaryConditionPatch>;
}

export interface MaterialProperty {
  symbol: string;
  name: string;
  value: number;
  unit: string;
  note_zh?: string;
}

export interface Material {
  id: string;
  label_zh: string;
  label_en: string;
  properties: MaterialProperty[];
}

export interface DerivedQuantity {
  symbol: string;
  name: string;
  value: number;
  formula: string;
  note_zh?: string;
}

export interface Solver {
  name: string;
  family: string;
  steady_state: boolean;
  // Optional: a derived case with no readable turbulence metadata cannot
  // claim laminar-vs-turbulent (DEC-V61-206). null/undefined ⇒ "待识别".
  laminar?: boolean | null;
  display_zh: string;
  reasoning_zh: string;
}

export interface WorkbenchBasicsHints {
  geometry_zh?: string;
  driver_zh?: string;
  physical_intuition_zh?: string;
}

export interface WorkbenchBasics {
  case_id: string;
  display_name: string;
  display_name_zh?: string;
  canonical_ref?: string;
  // "authored" = hand-curated knowledge yaml; "derived" = mirrored from a
  // real imported OpenFOAM case on disk (DEC-V61-206). Absent ⇒ treat as
  // authored (older payloads). The UI labels derived data "派生自算例".
  provenance?: "authored" | "derived";
  dimension: number;
  // Optional: derived imported cases have no <CaseFrame> shape category
  // (the V4 workbench renders the real GLB viewport instead).
  geometry?: Geometry;
  patches: Patch[];
  boundary_conditions: BoundaryCondition[];
  materials: Material[];
  derived: DerivedQuantity[];
  solver?: Solver;
  hints?: WorkbenchBasicsHints;
  schema_drift_warning?: string;
}
