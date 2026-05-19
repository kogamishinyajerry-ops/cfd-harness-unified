/**
 * V87.4 · V7.B SSE schema-drift guard
 *
 * Per V87 charter §3 + V85+V86 retro Open Q (2-arc carry): runtime
 * schema validation at the SSE parse boundary in `useSolverRunStateV7`.
 *
 * Why plain TS type guards instead of Zod:
 *   - No new dependency (CLAUDE.md "Don't introduce new frameworks
 *     unless explicitly requested")
 *   - Schema is small (4 event types · ≤8 distinct fields)
 *   - Each guard is ≤10 LOC · trivial to audit + test
 *   - Same runtime contract: invalid payload → guard returns false →
 *     caller skips dispatch (graceful degrade · V87 reverse-stop #22)
 *
 * Future migration to Zod is safe — interface shapes (StartEvent,
 * ResidualEvent, etc.) form a stable boundary; swap implementation
 * without breaking callers.
 *
 * V87 reverse-stop #22: invalid events MUST degrade gracefully ·
 * NOT crash · NOT corrupt state · NOT propagate error to user.
 */

export interface StartEvent {
  run_id: string;
}

export interface DoneEvent {
  run_id?: string;
  success?: boolean;
}

export interface ErrorEvent {
  message?: string;
}

export interface ResidualEvent {
  iteration: number;
  values: Record<string, number>;
  ts_ms: number;
}

function isRecord(v: unknown): v is Record<string, unknown> {
  return typeof v === "object" && v !== null && !Array.isArray(v);
}

export function isStartEvent(payload: unknown): payload is StartEvent {
  if (!isRecord(payload)) return false;
  return typeof payload["run_id"] === "string" && payload["run_id"].length > 0;
}

export function isDoneEvent(payload: unknown): payload is DoneEvent {
  if (!isRecord(payload)) return false;
  // done payload is permissive · run_id + success are both optional ·
  // failure modes (e.g., success=false) handled by the dispatcher logic
  if ("run_id" in payload && typeof payload["run_id"] !== "string") return false;
  if ("success" in payload && typeof payload["success"] !== "boolean") return false;
  return true;
}

export function isErrorEvent(payload: unknown): payload is ErrorEvent {
  if (!isRecord(payload)) return false;
  if ("message" in payload && typeof payload["message"] !== "string") return false;
  return true;
}

export function isResidualEvent(payload: unknown): payload is ResidualEvent {
  if (!isRecord(payload)) return false;
  if (typeof payload["iteration"] !== "number") return false;
  if (!Number.isFinite(payload["iteration"])) return false;
  if (typeof payload["ts_ms"] !== "number") return false;
  if (!isRecord(payload["values"])) return false;
  // Every entry in values must be finite number (loose-typed mocks
  // sometimes send strings · drop those silently).
  for (const v of Object.values(payload["values"])) {
    if (typeof v !== "number" || !Number.isFinite(v)) return false;
  }
  return true;
}
