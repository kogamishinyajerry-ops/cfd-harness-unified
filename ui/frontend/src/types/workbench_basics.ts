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
  laminar: boolean;
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
  dimension: number;
  geometry: Geometry;
  patches: Patch[];
  boundary_conditions: BoundaryCondition[];
  materials: Material[];
  derived: DerivedQuantity[];
  solver?: Solver;
  hints?: WorkbenchBasicsHints;
  schema_drift_warning?: string;
}
