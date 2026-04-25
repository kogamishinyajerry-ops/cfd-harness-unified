// Wizard types · Stage 8a onboarding workbench.
// Mirrors ui/backend/schemas/wizard.py.

export type ParamType = "int" | "float";

export interface TemplateParam {
  key: string;
  label_zh: string;
  label_en: string;
  type: ParamType;
  default: number;
  min?: number | null;
  max?: number | null;
  unit?: string | null;
  help_zh?: string | null;
}

export interface TemplateSummary {
  template_id: string;
  name_zh: string;
  name_en: string;
  description_zh: string;
  geometry_type: string;
  flow_type: string;
  solver: string;
  canonical_ref?: string | null;
  params: TemplateParam[];
}

export interface TemplateListResponse {
  templates: TemplateSummary[];
}

export interface DraftCreateRequest {
  template_id: string;
  case_id: string;
  name_display?: string | null;
  params: Record<string, number>;
}

export interface DraftCreateResponse {
  case_id: string;
  draft_path: string;
  yaml_text: string;
  lint_ok: boolean;
  lint_errors: string[];
  lint_warnings: string[];
}

export interface WizardPreviewResponse {
  yaml_text: string;
}

export type PhaseId = "geometry" | "mesh" | "boundary" | "solver" | "compare";
export type PhaseStatus = "ok" | "fail" | "running";
export type WizardEventType =
  | "phase_start"
  | "log"
  | "metric"
  | "phase_done"
  | "run_done";
// Stage 8b prep (round-3 Q13 audit): forward-compat fields for real
// solver subprocess. Mock script leaves these undefined.
export type LogLevel = "debug" | "info" | "warning" | "error";
export type LogStream = "stdout" | "stderr";

export interface RunPhaseEvent {
  type: WizardEventType;
  phase?: PhaseId | null;
  t: number;
  line?: string | null;
  message?: string | null;
  summary?: string | null;
  status?: PhaseStatus | null;
  metric_key?: string | null;
  metric_value?: number | null;
  // Stage 8b forward-compat
  level?: LogLevel | null;
  stream?: LogStream | null;
  exit_code?: number | null;
}
