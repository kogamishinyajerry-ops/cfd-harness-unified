/**
 * V88.3 · V8.B Solver-config validation surface · pure deterministic
 *
 * Per .planning/blueprints/v8/INDEX.md Contract V8.B:
 *   - Pure validation logic · no I/O · no LLM · no fetch
 *   - Rejects malformed values before commit (negative endTime · invalid
 *     solver name · deltaT > endTime · missing required · non-numeric)
 *   - Returns structured `ValidationError[]` so the UI can render inline
 *     per-field guidance
 *   - V88 reverse-stop #24: validation errors MUST surface pre-commit ·
 *     V8.C Confirm button gates on `validationErrors.length === 0`
 *   - V87.4 schema-drift carry: ignores unexpected/extra fields gracefully
 *     (does NOT crash · just doesn't validate them)
 *
 * No external deps · no React · runs in <1ms per call.
 */

export type ControlDictField =
  | "application"
  | "endTime"
  | "deltaT"
  | "writeInterval"
  | "writeFormat";

export type ValidationKind =
  | "negative"
  | "too_large"
  | "invalid_solver"
  | "missing"
  | "non_numeric"
  | "invalid_format";

export interface ValidationError {
  field: ControlDictField;
  kind: ValidationKind;
  message: string;
}

/**
 * Initial OpenFOAM solver allowlist · extensible in future arcs.
 * Source: covers incompressible (ico/simple/piso/pimple) + multiphase
 * (interFoam) + compressible (rhoCentralFoam) + buoyant (buoyantSimpleFoam).
 */
export const KNOWN_SOLVERS: readonly string[] = [
  "icoFoam",
  "simpleFoam",
  "pisoFoam",
  "pimpleFoam",
  "interFoam",
  "rhoCentralFoam",
  "buoyantSimpleFoam",
];

export const ALLOWED_WRITE_FORMATS: readonly string[] = ["ascii", "binary"];

/** Numeric fields that must parse as a positive number. */
const NUMERIC_FIELDS: ControlDictField[] = [
  "endTime",
  "deltaT",
  "writeInterval",
];

/** All fields are required for a complete controlDict edit. */
const REQUIRED_FIELDS: ControlDictField[] = [
  "application",
  "endTime",
  "deltaT",
  "writeInterval",
  "writeFormat",
];

function isBlank(value: string | undefined): boolean {
  return value === undefined || value.trim() === "";
}

/**
 * Parse `value` as a finite positive number. Returns NaN if non-parseable
 * or non-finite (Infinity / -Infinity).
 */
function parseNumeric(value: string): number {
  const trimmed = value.trim();
  if (trimmed === "") return NaN;
  const n = Number(trimmed);
  if (!Number.isFinite(n)) return NaN;
  return n;
}

/**
 * Validate a partial controlDict-field map. Returns the list of issues
 * (empty = ready to commit). Caller is V8.D (state machine · gates
 * `configReady`) + V8.C (diff · gates Confirm button).
 */
export function validateControlDictFields(
  fields: Partial<Record<ControlDictField, string>>,
): ValidationError[] {
  const errors: ValidationError[] = [];

  // Missing required fields surface first so user fixes them before
  // we start asserting numeric / allowlist constraints on empties.
  for (const field of REQUIRED_FIELDS) {
    if (isBlank(fields[field])) {
      errors.push({
        field,
        kind: "missing",
        message: `${field} is required`,
      });
    }
  }

  // application: must be in allowlist (only when non-blank · avoid
  // double-reporting alongside "missing").
  if (!isBlank(fields.application)) {
    const app = fields.application!.trim();
    if (!KNOWN_SOLVERS.includes(app)) {
      errors.push({
        field: "application",
        kind: "invalid_solver",
        message: `unknown solver "${app}" · known: ${KNOWN_SOLVERS.join(", ")}`,
      });
    }
  }

  // writeFormat: must be in {"ascii","binary"} when non-blank.
  if (!isBlank(fields.writeFormat)) {
    const fmt = fields.writeFormat!.trim();
    if (!ALLOWED_WRITE_FORMATS.includes(fmt)) {
      errors.push({
        field: "writeFormat",
        kind: "invalid_format",
        message: `writeFormat must be one of: ${ALLOWED_WRITE_FORMATS.join(", ")}`,
      });
    }
  }

  // Numeric fields: parse → check finite → check positive.
  const parsedNumeric: Partial<Record<ControlDictField, number>> = {};
  for (const field of NUMERIC_FIELDS) {
    const raw = fields[field];
    if (isBlank(raw)) continue; // already reported via "missing"
    const n = parseNumeric(raw!);
    if (Number.isNaN(n)) {
      errors.push({
        field,
        kind: "non_numeric",
        message: `${field} must be a finite number`,
      });
      continue;
    }
    if (n <= 0) {
      errors.push({
        field,
        kind: "negative",
        message: `${field} must be > 0`,
      });
      continue;
    }
    parsedNumeric[field] = n;
  }

  // Cross-field: deltaT > endTime → too_large on deltaT.
  if (
    parsedNumeric.deltaT !== undefined &&
    parsedNumeric.endTime !== undefined &&
    parsedNumeric.deltaT > parsedNumeric.endTime
  ) {
    errors.push({
      field: "deltaT",
      kind: "too_large",
      message: `deltaT (${parsedNumeric.deltaT}) must be ≤ endTime (${parsedNumeric.endTime})`,
    });
  }

  // Cross-field: writeInterval > endTime → too_large on writeInterval.
  if (
    parsedNumeric.writeInterval !== undefined &&
    parsedNumeric.endTime !== undefined &&
    parsedNumeric.writeInterval > parsedNumeric.endTime
  ) {
    errors.push({
      field: "writeInterval",
      kind: "too_large",
      message: `writeInterval (${parsedNumeric.writeInterval}) must be ≤ endTime (${parsedNumeric.endTime})`,
    });
  }

  return errors;
}

/**
 * Parse a controlDict source-text blob into a field map. Best-effort:
 * matches OpenFOAM-style `key value;` lines (lenient whitespace). Returns
 * an empty map when the file is empty or non-conforming so the editor
 * doesn't crash on an unfamiliar shape — the user can still fill in
 * fields and commit.
 */
export function parseControlDictFields(
  content: string,
): Partial<Record<ControlDictField, string>> {
  const fields: Partial<Record<ControlDictField, string>> = {};
  if (typeof content !== "string" || content.length === 0) return fields;

  // Match `key value;` (key is alpha · value can include letters/digits/
  // dot/dash/underscore · no semicolons in value). Comments + braces
  // ignored — controlDict is flat key/value.
  const lineRe =
    /^\s*(application|endTime|deltaT|writeInterval|writeFormat)\s+([^;]+?)\s*;\s*$/gm;
  let match: RegExpExecArray | null;
  while ((match = lineRe.exec(content)) !== null) {
    const key = match[1] as ControlDictField;
    const value = match[2].trim();
    fields[key] = value;
  }
  return fields;
}

/**
 * Serialise field map back to controlDict source-text. Used by V8.D
 * commit path so we preserve the OpenFOAM header + only patch the
 * known keys. If `baseContent` is supplied, replace key lines in-place;
 * else emit a minimal block.
 */
export function serializeControlDictFields(
  fields: Partial<Record<ControlDictField, string>>,
  baseContent?: string,
): string {
  if (baseContent && baseContent.length > 0) {
    let next = baseContent;
    for (const field of REQUIRED_FIELDS) {
      const value = fields[field];
      if (value === undefined) continue;
      const fieldRe = new RegExp(
        `^(\\s*${field}\\s+)[^;]+?(\\s*;\\s*)$`,
        "m",
      );
      if (fieldRe.test(next)) {
        next = next.replace(fieldRe, `$1${value}$2`);
      } else {
        // Append before the trailing closing block, or at end-of-file
        // when no obvious anchor exists.
        next = `${next.replace(/\s*$/, "")}\n${field}    ${value};\n`;
      }
    }
    return next;
  }

  // Minimal emission · only used when baseContent is empty (defensive
  // path · normal flow always has baseContent from GET /dicts).
  const lines: string[] = [];
  for (const field of REQUIRED_FIELDS) {
    const value = fields[field];
    if (value === undefined) continue;
    lines.push(`${field}    ${value};`);
  }
  return lines.join("\n") + "\n";
}
