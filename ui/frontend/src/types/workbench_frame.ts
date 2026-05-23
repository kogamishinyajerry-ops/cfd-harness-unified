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
  /**
   * DEC-V61-202-SUB-M31-CYCLE1: domain-aware form helper. Optional
   * structural dict skeleton for fields too complex for a scalar
   * `suggested_default` (e.g. `bc.patches` on ship_vof). When non-null,
   * the rail renders a secondary "Apply skeleton" CTA; clicking it
   * PATCHes the full dict at `field_path`. Backend may emit both
   * `suggested_default` (scalar) AND `suggested_skeleton` (dict) on
   * the same rail — they are independent affordances.
   */
  suggested_skeleton: Record<string, unknown> | null;
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

// DEC-V61-202-SUB-M30-CYCLE2 · 4th driver slot.
export type TopbarCtaKind =
  | "next_step"
  | "re_audit"
  | "submit_solve"
  | "step_default";

export interface TopbarCta {
  kind: TopbarCtaKind;
  label: string;
  target_step: number | null;
  enabled: boolean;
  reason: string | null;
}

export interface WorkbenchFrame {
  case_id: string;
  step: number;
  rail_primary: RailPrimary;
  viewport_overlays: ViewportOverlay[];
  bottom_cards: BottomCard[];
  topbar_cta: TopbarCta;
  state_sha: string;
  manifest_state_sha: string;
  decided_at: string;
}
