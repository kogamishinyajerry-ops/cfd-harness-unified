# V8 Blueprint · Solver Configuration Editor · ACTIVE 2026-05-17

> **Predecessor**: V7 blueprint (`.planning/blueprints/v7/INDEX.md`) · landed V86 · substantiated V87 (USER-triggered Live Solver Trigger fully integrated)
> **Charter**: `.planning/decisions/2026-05-17_v88_charter_dec.md` (B294)
> **Streak**: 11th consecutive arc target with NO scoring framework changes (V78+...+V87 = 10 arcs)
> **Mandate**: 24th invocation · 2nd verbatim re-issue of "CFD能力" wording (V86 was 1st) · wording-cohort 2nd-verbatim parallels V80→V83 jump · interpretation = next blueprint LAND in capability axis

## 0 · What V8 is + isn't

**V8 IS**:
- A **USER-edit form** for OpenFOAM solver `controlDict` (application · endTime · deltaT · writeInterval · writeFormat) that surfaces in v3 Engineer Control Rail / Right Panel Inspector tab
- A **deterministic validation surface** that rejects malformed values before the user can commit (negative endTime · invalid solver name · deltaT > endTime · missing required fields)
- An **explicit diff-preview gate** between edit state and on-disk state — user MUST see what changes before committing (no one-click save+commit)
- A **run-readiness signal** (`configReady`) that decouples V8 from V7.A via shell-level shared state — V7.A Run button gates on it without importing V8 internals
- A **frontend wiring arc** reusing existing `POST /api/cases/{case_id}/dicts/{relative_path:path}` endpoint (DEC-V61-088 surface scan disposition (a) extend) · V132 stays at 9

**V8 IS NOT**:
- A new MUTATING_ROUTE · V132 count stays at 9 (existing `/dicts/{path}` POST endpoint reused · already counted in V86 baseline)
- An AI-triggered config editor · V130 invariant intact · all edits + commits are USER-click only · no AI auto-write of dicts · no AI-suggested config presets (V9+ candidate)
- A multi-file batch editor · V8.A edits one dict at a time (controlDict initially) · fvSchemes / fvSolution / etc. = V9+ extension
- A sandbox / cinematic / bridge surface affordance · V8.A surfaces in Engineer-mode only · sandbox + cinematic + bridge stay read-only per V83.2 + V83.4 + V85.X carries
- An in-UI history / undo stack · V8.A relies on existing case-dicts manifest audit trail (every commit records `source=user` + new ETag) · in-UI undo = V9+ candidate
- A new pillar / subscore / threshold / scorer-script (V88 charter §6 reverse-stops · 11th arc no-scoring-change target)
- An auth-boundary change · existing endpoint already enforces case-dir resolution + ETag concurrency + structured 422 validation · no Codex round triggered (v2.2 1-sync-trigger NOT hit)

## 1 · The narrative (V8 extends V4+V5+V6+V7 timeline)

V4 = static knowledge layer. V5 = interactive curated demo. V6 = real-data bridge (read-only artifacts). V7 = USER-triggered live solver run with defaults. **V8 = USER edits solver config before triggering a run, sees diff, validates, commits, then V7 picks up the new config on the next click.**

| Mode | URL trigger | What user sees | Source of truth |
|---|---|---|---|
| Default (curated) | `/workbench/v3/case/{id}` | Curated step labels (V4) + curated sandbox banners (V5) | sandbox_step_states.ts + V4 commentary |
| Cinematic | `+ ?demo=1&cinema=1` | 12s auto-tour through curated state | V4 + V5.C |
| Sandbox | `+ ?demo=2` | Click-through curated state | V5.A |
| Failure-mode | `+ ?failmode=1` | 3 curated failure cards | V5.B |
| Bridge | `+ ?bridge=1` | Step banners from REAL pre-run artifact | V6.A bridge reader |
| Live (V7) | engineer-rail Run button click | REAL solver run streaming live | V7.A button → POST /solve-stream |
| **Config-edit (NEW · V8)** | **engineer-rail Solver-Config editor open** | **USER form fields for controlDict · validation surface · diff preview · commit-after-review affordance · `configReady` signal feeds V7.A gate** | **V8.A form → V8.B validator → V8.C diff → V8.D `configReady` → V7.A Run button enabled** |

## 2 · The 4 V8 contracts

### V8.A · SolverConfigEditor (component)

`src/pages/workbench/v3/components/SolverConfigEditorV8.tsx`:

```tsx
interface SolverConfigEditorV8Props {
  caseId: string | null;
  /** Initial controlDict content + ETag (from GET /dicts/system/controlDict). */
  initial: { content: string; etag: string | null } | null;
  /** Edit state slice (from useSolverConfigStateV8). */
  state: SolverConfigState;
  /** USER-edit handler — pure field setter, NO auto-write. */
  onFieldChange: (field: ControlDictField, value: string) => void;
  /** USER-click handler — opens V8.C diff preview gate. */
  onReviewChanges: () => void;
  /** USER-click handler from inside V8.C diff — performs the actual POST. */
  onConfirmCommit: () => void;
  /** USER-click handler — discards pending edits, returns to clean state. */
  onDiscard: () => void;
}

type ControlDictField =
  | "application"      // e.g. "icoFoam" / "simpleFoam"
  | "endTime"          // number > 0
  | "deltaT"           // number > 0, < endTime
  | "writeInterval"    // number > 0
  | "writeFormat";     // "ascii" | "binary"
```

- Surfaces in Engineer Control Rail (adjacent to V7.A Run button) OR Right Panel Inspector tab — NOT in sandbox/cinematic/bridge
- Disabled (hidden behaviorally) when `?demo=1` / `?demo=2` / `?bridge=1` (carry V87 V7.A read-only-mode discipline · reverse-stop 20)
- Fields rendered as controlled inputs · `onFieldChange` updates local edit state only (no fetch)
- "Review changes" button surfaces V8.C diff preview · disabled when no field has changed (state === "clean") OR when validation errors exist
- "Discard" button surfaces only when state === "dirty" · returns to clean baseline
- `data-testid="solver-config-editor-v8"` + `data-config-state="clean|dirty|saving|saved|error"` + `data-validation-status="valid|invalid"` for inspection
- Contract tests assert:
  - V130: only USER-click affordances · NO `useEffect` auto-write · NO timer-based auto-commit · NO programmatic POST outside the `onConfirmCommit` user-click path
  - Mount-time fetch-zero-call assertion: component does NOT issue POST /dicts on mount, only on explicit `onConfirmCommit` user click
  - Denylist test for "auto-save" / "auto-commit" / "AI applies" / "automatic" in description text
  - Disabled / hidden behaviorally in `?demo=1` / `?demo=2` / `?bridge=1`
  - Discard returns state to `clean`

### V8.B · Validation Surface (pure function)

`src/pages/workbench/v3/components/solver_config_validator.ts`:

```ts
export type ValidationKind =
  | "negative"          // numeric field is negative or zero where >0 required
  | "too_large"         // deltaT > endTime, or writeInterval > endTime
  | "invalid_solver"    // application not in known solver allowlist
  | "missing"           // required field empty
  | "non_numeric"       // numeric field has non-parseable value
  | "invalid_format";   // writeFormat not in {"ascii", "binary"}

export interface ValidationError {
  field: ControlDictField;
  kind: ValidationKind;
  message: string;
}

export function validateControlDictFields(
  fields: Partial<Record<ControlDictField, string>>,
): ValidationError[];
```

- Pure deterministic validation · no I/O · no LLM call · no fetch
- Known solver allowlist: `["icoFoam", "simpleFoam", "pisoFoam", "pimpleFoam", "interFoam", "rhoCentralFoam", "buoyantSimpleFoam"]` (initial set · extensible)
- `endTime`, `deltaT`, `writeInterval` parsed via `Number()` · NaN → `non_numeric` · 0 or negative → `negative`
- `deltaT > endTime` → `too_large` on `deltaT` field
- `writeInterval > endTime` → `too_large` on `writeInterval` field
- Empty required field → `missing`
- Returns empty array when all valid
- Contract tests cover ALL edge cases (each kind × each applicable field · valid baseline · multi-error case)
- V87.4 schema-drift discipline carry: validator handles unexpected/extra fields gracefully (ignored · not crashed)

### V8.C · Diff Preview (component)

`src/pages/workbench/v3/components/SolverConfigDiffV8.tsx`:

```tsx
interface SolverConfigDiffV8Props {
  current: Partial<Record<ControlDictField, string>>;
  pending: Partial<Record<ControlDictField, string>>;
  validationErrors: ValidationError[];
  onConfirm: () => void;
  onCancel: () => void;
}
```

- Two-column display: left = current on-disk values · right = pending edit values
- Changed fields highlighted (sand-coral accent #b78b65 used sparingly per <2% pixel budget)
- Unchanged fields rendered dim/muted · no visual noise
- Validation errors rendered inline above the Confirm button · Confirm button DISABLED when `validationErrors.length > 0`
- "Confirm commit" button is the SINGLE USER-click that fires the POST /dicts → triggers V8.D state transition `dirty → saving → saved` (or `error`)
- "Cancel" returns to V8.A editor without committing
- `data-testid="solver-config-diff-v8"` + `data-changed-fields-count="N"` + `data-validation-error-count="N"` for inspection
- Contract tests assert:
  - V130 denylist for "auto-commit" / "automatic" / "AI applies" verbiage in heading/body
  - Confirm button disabled iff `validationErrors.length > 0`
  - Confirm button click is the ONLY path that fires the commit (no `useEffect` auto-fire)
  - Cancel does NOT fire a POST (no fetch on cancel path)

### V8.D · Run-Readiness Signal (hook)

`src/pages/workbench/v3/hooks/useSolverConfigStateV8.ts`:

```ts
export type SolverConfigState =
  | "clean"     // local edits match on-disk content (no pending changes)
  | "dirty"     // local edits differ from on-disk content
  | "saving"    // POST /dicts in flight
  | "saved"     // POST completed successfully · new ETag in state
  | "error";    // POST failed (4xx / 5xx / 409 ETag conflict)

export interface SolverConfigStateV8 {
  state: SolverConfigState;
  fields: Partial<Record<ControlDictField, string>>;
  baseline: Partial<Record<ControlDictField, string>>;
  etag: string | null;
  validationErrors: ValidationError[];
  errorMessage: string | null;
  /** Computed: true iff state ∈ {clean, saved} AND validationErrors is empty.
   *  V7.A Run button gates on this via shell-level shared state. */
  configReady: boolean;

  setField: (field: ControlDictField, value: string) => void;
  reviewChanges: () => void;          // computed-only transition (no fetch)
  confirmCommit: () => Promise<void>; // fires POST /dicts
  discard: () => void;                // returns to baseline · state → clean
  dismissError: () => void;           // error → dirty (allow retry)
}
```

- Pure state-machine hook · uses `api.postRawDict(caseId, "system/controlDict", body, {expectedEtag})` for the commit
- Transitions:
  - `clean` → `dirty` (on `setField()` where new value !== baseline)
  - `dirty` → `clean` (on `setField()` where value reverts to baseline · OR on `discard()`)
  - `dirty` → `saving` (on `confirmCommit()`)
  - `saving` → `saved` (on POST 2xx · `baseline` updates to new fields · `etag` updates)
  - `saving` → `error` (on POST 4xx/5xx/409)
  - `saved` → `dirty` (on subsequent `setField()`)
  - `error` → `dirty` (on `dismissError()`)
- `configReady` is the load-bearing decoupling primitive: V7.A imports this boolean from WorkbenchShellV3 shell-level shared state · NOT from V8.D directly · per V88 reverse-stop 25
- Contract tests cover all transitions + V8→V7 handoff (configReady computed correctly across state matrix)
- V87.4 schema-drift discipline carry: hook handles 422 validation responses from POST /dicts gracefully (transitions to `error` with structured message · NOT crash)
- V87.4 graceful-degrade carry: 409 ETag conflict surfaces as `error` with hint to refresh + merge (existing endpoint already returns structured detail)

## 3 · Reverse-stops (V8 contracts MUST honor)

1. **USER-click only**: V8.A field edits + V8.C confirm-commit are USER-click only · NO `useEffect` auto-write · NO timer-based auto-commit · NO programmatic POST outside the `onConfirmCommit` user-click path
2. **Diff preview gate mandatory**: V8.A "Review changes" button MUST open V8.C diff preview BEFORE any commit · no shortcut path from V8.A directly to POST (V88 reverse-stop 23)
3. **Validation errors surface pre-commit**: V8.B validation errors MUST be visible in V8.C diff before user clicks Confirm · Confirm DISABLED when errors present (V88 reverse-stop 24 · V130 AI-no-auto-fix carry)
4. **Engineer-mode only**: V8.A surfaces in Engineer Control Rail / Right Panel Inspector — NOT in sandbox / cinematic / bridge (V83.2 + V83.4 + V85.X carries + V87 V7.A read-only-mode discipline reverse-stop 20)
5. **V130 denylist**: V8.A + V8.C description text + state-machine docs MUST NOT contain "auto-save" / "auto-commit" / "AI applies" / "automatic" / equivalent · lexical denylist test enforced
6. **V132 = 9**: No new MUTATING_ROUTE · existing `POST /api/cases/{case_id}/dicts/{relative_path:path}` endpoint reused (already counted)
7. **Steady-state visual baselines**: V8 baselines MUST be steady-state · NO post-click async-mount fragility (V84.6 lesson · 4th arc carry · V88 reverse-stop 26)
8. **Configurable decoupling**: V8.D `configReady` MUST be inspectable via shell-level shared state (WorkbenchShellV3) · V7.A MUST NOT import V8.D directly (V88 reverse-stop 25)
9. **ETag concurrency**: V8.D commit MUST pass `expected_etag` to POST · 409 surfaces as recoverable error (existing endpoint behavior · don't bypass)
10. **Audit trail via manifest**: V8 commits MUST flow through existing case-dicts manifest recording (`source=user` + new ETag) · don't bypass · TrustGate intact
11. **Single dict scope**: V8.A edits ONE dict at a time (controlDict initially) · multi-file batch editor = V9+ candidate
12. **Curated path operational**: Default (curated) + sandbox + cinematic + bridge flows MUST continue unaffected · V8 is additive only

## 4 · 4Q gate (every V8 sub-DEC must answer)

1. **LLM offline runnable?** ✓ V8.A is form UI · V8.B is deterministic pure validation · V8.C is pure diff render · V8.D is local state machine + existing POST · NO LLM call anywhere
2. **Artifacts emitted?** ✓ V8 commits write `system/controlDict` via existing case-dicts endpoint · manifest records source=user with new ETag · subsequent V7-triggered solver runs pick up the new config · audit-package captures the committed dict (already part of existing manifest surface)
3. **TrustGate intact?** ✓ Every V8 commit records to manifest with source=user + new ETag · existing `/audit-packages/{bundle}/manifest.json` continues to expose this · ETag concurrency prevents silent overwrite
4. **AI advisory only?** ✓ V8.A is USER form · V130 denylist enforced on edit + diff + commit affordances · V8.A structural mount-time fetch-zero-call assertion in tests · existing case-dicts endpoint already enforces `source=user` override on every successful POST · no AI-suggested presets in V8 (V9+ candidate · would need separate denylist guardrails)

## 5 · Honest disclosures (what V8 does NOT do)

- ❌ **AI-suggested config presets** — V130 invariant · V8 is USER editor only · AI suggestions = V9+ candidate (would need separate denylist guardrails + curator-in-the-loop discipline)
- ❌ **Multi-file dict batch editor** — V8.A edits ONE dict at a time (controlDict initially) · fvSchemes / fvSolution / blockMeshDict / etc. = V9+ extension
- ❌ **fvSchemes / fvSolution editors** — V8 starts with controlDict only (most user-impactful · time controls + solver name) · other dicts = V9+ extension
- ❌ **In-UI history / undo stack** — V8.A relies on existing case-dicts manifest audit trail · in-UI undo = V9+ candidate
- ❌ **BC editor in UI** — V88 user-selected against this in axis-pick · BC editor = V89+ candidate
- ❌ **Cross-case bulk config edit** — V8 is single-case · multi-case bulk = V9+ candidate
- ❌ **Programmatic config edit from CI / dogfood** — V8 is UI-only · `scripts/smoke/dogfood_loop.py` continues to be the CI/dogfood path
- ❌ **Backend dict schema migration** — V8 trusts existing `RawDictPostBody` schema + existing 422 validation responses · schema migration = backend-arc candidate, not V8

## 6 · Substrate expansion (V4 + V5 + V6 + V7 + V8 coverage map)

| Layer | V4 | V5 | V6 | V7 | V8 |
|---|---|---|---|---|---|
| Static commentary | ✓ | (carry) | (carry) | (carry) | (carry) |
| Cinematic auto-tour | ✓ | (carry) | (carry) | (carry) | (carry) |
| Provenance card | ✓ | + V5.D | replaced by V6.D | + V7.D extends | (carry · V8 commits surface in manifest) |
| Failure-mode showcase | — | ✓ | (carry) | (carry) | (carry) |
| Sandbox click-through | — | ✓ | + bridge | (carry) | (carry · V8 NOT mounted in sandbox) |
| Multi-case curated state | — | ✓ | (carry) | (carry) | (carry) |
| Real-artifact bridge (READ) | — | — | ✓ | + post-run handoff | (carry · V8 commits → next V7 run → bridge surfaces new artifact) |
| Live-vs-curated diff | — | — | ✓ | (carry) | (carry) |
| USER-triggered live solver run | — | — | — | ✓ | (carry · V7.A gates on V8.D `configReady`) |
| Cancellable run state machine | — | — | — | ✓ | (carry) |
| Live residual SSE in v3 chart | — | — | — | ✓ | (carry) |
| Audit-package auto-build on done | — | — | — | ✓ | (carry · captures V8-committed config) |
| **USER-edit solver config form** | — | — | — | — | ✓ NEW V8.A |
| **Deterministic config validation** | — | — | — | — | ✓ NEW V8.B |
| **Diff preview before commit** | — | — | — | — | ✓ NEW V8.C |
| **Run-readiness signal (configReady)** | — | — | — | — | ✓ NEW V8.D |

After V8 lands: the workbench covers the FULL pre-run-edit + execute + post-run-review lifecycle:
1. **Static-knowledge layer** (V4)
2. **Interactive-demonstration layer** (V5)
3. **Real-data bridge (READ)** (V6)
4. **Live execution layer** (V7) — USER triggers a real run with defaults
5. **Pre-run configuration layer** (V8) — USER edits config, validates, sees diff, commits, then triggers run

All five layers under the same 4Q gate, all V130/V132-compliant, all on the same 16-pillar V78 scoring framework.

## 7 · Test substrate target (V88.6 close gate)

- Visual baselines: at least 3 new (87 solver-config-editor-clean-state · 88 solver-config-editor-dirty-with-diff-open · 89 solver-config-editor-validation-error-surfaced) · target 89 total · steady-state baselines (no post-edit async-mount fragility per V84.6 lesson)
- e2e Playwright specs: at least 4 new in `v88-v8-solver-config.spec.ts` (editor hidden in `?demo=2` / `?bridge=1` · field edit + diff preview + commit path · validation error blocks commit · ETag 409 surfaces recoverable error)
- Contract (vitest) tests: at least 25 new (V8.A editor 6 · V8.B validator 10 · V8.C diff 5 · V8.D hook 4)
- Network-mutation guard: confirm V8 emits POST /dicts ONLY on user Confirm-Commit click in V8.C (V130 denylist asserts no `useEffect` auto-fire of mutating fetch · structural mount-time fetch-zero-call assertion)
- V7+V8 integration test: V8.D `configReady=false` → V7.A Run button disabled · V8.D `configReady=true` → V7.A Run button enabled (decoupled via shell-level shared state · V7.A does NOT import V8.D directly)

— V8 Blueprint · 2026-05-17 · LANDED at V88.1
