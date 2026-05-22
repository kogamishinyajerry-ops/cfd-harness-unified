// DEC-V61-202-SUB-M30-CYCLE1 · WorkbenchFrame TypeScript mirror.
//
// Stay byte-equivalent to ui/backend/schemas/workbench_frame.py. When
// the backend schema changes, update this file in the same commit.

export type RailPrimaryKind = "info_gap" | "problem_fix" | "step_default";

export type OverlayKind =
  | "patch_highlight"
  | "region_highlight"
  | "cell_count_badge"
  | "checkmesh_warn";

export type CardKind = "audit_finding" | "missing_field" | "step_hint";

export type FrameSeverity = "info" | "warn" | "fail";

export interface RailPrimary {
  kind: RailPrimaryKind;
  title: string;
  body_text: string | null;
  field_path: string | null;
  suggested_default: unknown | null;
  cta_label: string | null;
  provenance: string[];
}

export interface ViewportOverlay {
  kind: OverlayKind;
  target: string | null;
  severity: FrameSeverity;
  label: string | null;
}

export interface BottomCard {
  kind: CardKind;
  title: string;
  body_text: string;
  severity: FrameSeverity;
  source_artifact: string | null;
  field_path: string | null;
}

export interface WorkbenchFrame {
  case_id: string;
  step: number;
  rail_primary: RailPrimary;
  viewport_overlays: ViewportOverlay[];
  bottom_cards: BottomCard[];
  state_sha: string;
  decided_at: string;
}
