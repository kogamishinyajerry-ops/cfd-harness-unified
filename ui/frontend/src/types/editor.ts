// Mirrors ui/backend/schemas/editor.py

export type CaseYamlOrigin = "draft" | "whitelist" | "missing";

export interface CaseYamlPayload {
  case_id: string;
  yaml_text: string;
  origin: CaseYamlOrigin;
  draft_path: string | null;
}

export interface CaseYamlLintResult {
  ok: boolean;
  errors: string[];
  warnings: string[];
}

export interface CaseYamlSaveResult {
  case_id: string;
  saved: boolean;
  draft_path: string | null;
  lint: CaseYamlLintResult;
}
