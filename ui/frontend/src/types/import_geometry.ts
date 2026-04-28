// Mirrors ui/backend/schemas/import_geometry.py — kept thin so the wire
// types stay one source-of-truth on the backend.

export type UnitGuess = "m" | "mm" | "in" | "unknown";

export interface PatchInfo {
  name: string;
  face_count: number;
}

export interface IngestReport {
  is_watertight: boolean;
  bbox_min: [number, number, number];
  bbox_max: [number, number, number];
  bbox_extent: [number, number, number];
  unit_guess: UnitGuess;
  solid_count: number;
  face_count: number;
  is_single_shell: boolean;
  patches: PatchInfo[];
  all_default_faces: boolean;
  warnings: string[];
  errors: string[];
}

export interface ImportSTLResponse {
  case_id: string;
  ingest_report: IngestReport;
  edit_url: string;
}

export interface ImportRejectionDetail {
  reason: string;
  failing_check: "stl_parse" | "watertight" | "size_limit" | "unknown" | string;
  ingest_report?: IngestReport | null;
}

// M-PANELS Step 10 · demo-fixtures catalogue. Mirrors the
// DemoFixture pydantic model in ui/backend/routes/demo_fixtures.py.
export interface DemoFixture {
  name: string;
  filename: string;
  title: string;
  description: string;
  size_bytes: number;
  // Phase-1A (DEC-V61-097): closed cavities (ldc_box) walk Steps 1→5
  // end-to-end; external-flow geometries (cylinder, naca0012) stop
  // at Step 2 because the gmsh interior mesh isn't a flow domain.
  full_demo_capable: boolean;
  capability_note: string;
}
