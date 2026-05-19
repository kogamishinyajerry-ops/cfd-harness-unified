# V7 Blueprint · Live Solver Trigger · ACTIVE 2026-05-17

> **Predecessor**: V6 blueprint (`.planning/blueprints/v6/INDEX.md`) · landed V85 · Real-Artifact Bridge LIVE
> **Charter**: `.planning/decisions/2026-05-17_v86_charter_dec.md` (B281)
> **Streak**: 9th consecutive arc target with NO scoring framework changes (V78+V79+V80+V81+V82+V83+V84+V85+V86)
> **Mandate pivot**: 22nd mandate dropped "AI CFD demo展示" framing in favor of "全流程CFD能力" — first non-verbatim re-issue since V80 · signals pivot from showcase to actual capability

## 0 · What V7 is + isn't

**V7 IS**:
- A **USER-triggered live OpenFOAM solver run** from the v3 workbench Engineer Control Rail
- A **frontend wiring arc** that closes the 6-arc live-solver-hookup structural debt without backend changes (existing `POST /api/import/{case_id}/solve-stream` endpoint is reused per DEC-V61-088 surface scan disposition (a) extend)
- A **post-run hand-off** that feeds the resulting real `run_id` into V6 Bridge artifact loader · audit-package auto-build on completion · run_id surfaces in TopBar provenance
- A **cancellable state machine** with explicit prerequisite gating (mesh ready · BC setup) — no runaway runs · user retains stop control at all times

**V7 IS NOT**:
- A new MUTATING_ROUTE · V132 count stays at 9 (existing `/solve-stream` endpoint reused)
- An AI-triggered solver path · V130 invariant intact · Run button is USER-click only · no AI auto-trigger · no timer-based auto-execute · no programmatic invocation outside user click event
- A sandbox / cinematic / bridge surface affordance · V7.A surfaces in Engineer Control Rail ONLY · sandbox + cinematic + bridge stay read-only per V83.2 + V83.4 + V85.X carries
- A V82.4 curated SSE generator replacement · curated path stays operational alongside real-SSE wiring · curated default for demo flows · real opt-in via user click
- A new pillar / subscore / threshold / scorer-script (V86 charter §6 reverse-stops · 9th arc no-scoring-change target)
- An auth-boundary change · existing endpoint already enforces case-dir resolution + BC validation + container availability checks · no new security review needed (Codex v2.2 1-sync-trigger NOT hit)

## 1 · The narrative (V7 extends the V4+V5+V6 timeline)

V4 = static knowledge layer. V5 = interactive curated demo. V6 = real-data bridge (read-only view of pre-existing artifacts). **V7 = USER triggers a live solver run, watches it stream, hands off the resulting real run_id back into V6 bridge for review.**

| Mode | URL trigger | What user sees | Source of truth |
|---|---|---|---|
| Default (curated) | `/workbench/v3/case/{id}` | Curated step labels (V4) · curated sandbox banners (V5) | sandbox_step_states.ts + V4 commentary |
| Cinematic | `+ ?demo=1&cinema=1` | 12s auto-tour through curated state | V4 + V5.C |
| Sandbox | `+ ?demo=2` | Click-through curated state | V5.A |
| Failure-mode | `+ ?failmode=1` | 3 curated failure cards | V5.B |
| Bridge | `+ ?bridge=1` | Step banners from REAL pre-run artifact | V6.A bridge reader |
| **Live (NEW · V7)** | **engineer-rail Run button click** | **REAL solver run streaming live · residuals chart updates per iter · LIVE pill in TopBar · prerequisite-gated state machine · cancel-button available** | **V7.A button → POST /api/import/{id}/solve-stream → V7.B state → V7.C SSE → V7.D post-run handoff** |

## 2 · The 4 V7 contracts

### V7.A · Run Solver Button (component)

`src/pages/workbench/v3/components/RunSolverButtonV7.tsx`:

```tsx
interface RunSolverButtonV7Props {
  caseId: string | null;
  /** Prerequisite gate · button disabled when any are false. */
  meshReady: boolean;
  bcSetup: boolean;
  /** State machine slice (from useSolverRunStateV7). */
  runState: SolverRunState;
  /** USER-click handler — kicks off POST /solve-stream. */
  onRequestRun: () => void;
  /** USER-click handler — cancels in-flight run. */
  onCancelRun: () => void;
}
```

- Surfaces in Engineer Control Rail · NOT in sandbox/cinematic/bridge
- Disabled when `meshReady=false` OR `bcSetup=false` OR `runState !== "idle"`
- When `runState === "running"`, button label flips to "Cancel run"
- `data-testid="run-solver-v7"` + `data-prerequisites-met="true|false"` + `data-run-state="..."` for inspection
- Contract tests assert:
  - V130: only `<button onClick={...}>` affordance — no `useEffect` auto-trigger, no timer, no programmatic invocation
  - Denylist test for "auto-run" / "automatic" / "AI runs" in description text
  - Disabled when prerequisites unmet (no run attempt possible)

### V7.B · Run State Machine (hook)

`src/pages/workbench/v3/hooks/useSolverRunStateV7.ts`:

```ts
export type SolverRunState =
  | "idle"
  | "starting"     // POST in flight
  | "running"      // SSE open, receiving events
  | "done"         // SSE closed cleanly, exit_code=0
  | "failed"       // SSE closed with error event OR HTTP error
  | "cancelled";   // user clicked cancel

export interface SolverRunStateV7 {
  state: SolverRunState;
  runId: string | null;          // assigned when starting → running
  startedAt: string | null;
  endedAt: string | null;
  errorMessage: string | null;
  request: (caseId: string) => Promise<void>;
  cancel: () => void;
}
```

- Pure state-machine hook · no fetch yet (V7.C wires the actual SSE)
- Transitions:
  - `idle` → `starting` (on `request()`)
  - `starting` → `running` (on first SSE event received)
  - `starting` → `failed` (on HTTP 4xx/5xx)
  - `running` → `done` (on SSE close with `success=true`)
  - `running` → `failed` (on SSE error event OR `success=false`)
  - `running` → `cancelled` (on `cancel()` · AbortController-driven)
  - any → `idle` (on user dismiss)
- Contract tests cover all transitions + idempotency (`request()` while already running = no-op + warning)

### V7.C · Live Residual Bridge (integration)

Wires real SSE into v3 `ResidualsChartV3` + adds LIVE pill to TopBar.

- Reuses existing `src/hooks/useSseResidualStream.ts` (V77.5 hook · already battle-tested)
- New prop `liveRunId?: string | null` on `ResidualsChartV3`:
  - When set + `runState === "running"`: subscribes to real SSE via `useSseResidualStream(`/api/import/${caseId}/solve-stream`)`
  - When null OR `runState === "idle|done|failed|cancelled"`: falls back to V82.4 curated 4-layer realism generator (default · demo mode preserved)
- TopBar gains `LIVE` pill via `data-testid="topbar-live-pill"` when `runState === "running"` · sand-coral accent color matching existing v3 palette
- Contract tests:
  - Curated generator continues to function when no real SSE active (regression)
  - When real SSE active, chart receives real residual events (mock SSE)
  - LIVE pill mounts iff `runState === "running"`
  - Cancel transitions chart back to curated path within 200ms (no orphaned SSE)

### V7.D · Post-Run Hand-off (integration)

When `runState` transitions `running → done`:

- The just-completed `run_id` becomes available via `useSolverRunStateV7().runId`
- `WorkbenchShellV3` reads `runId` and passes it to V6 `BridgeModeShowcase` + `DemoSandboxV5` via the existing `bridgeArtifact` prop pipeline
- Fetches artifact via `GET /api/cases/{case_id}/run-history/{run_id}` (existing V6.A consumer pattern)
- Audit-package auto-build is best-effort: a fire-and-forget `POST /api/cases/{case_id}/runs/{run_id}/audit-package/build` request (existing endpoint per `audit_package.py:140`) — counted in V132=9 baseline
- TopBar provenance line extends with the just-completed run_id when V6.D `BridgeModeShowcase` is active
- Contract tests:
  - V7.D fires only on `running → done` (not on `failed` or `cancelled`)
  - Audit-package request is fire-and-forget · run state does not block on its completion
  - V6 bridge receives the new `run_id` and renders with `data-source="bridge"` + LIVE badge

## 3 · Reverse-stops (V7 contracts MUST honor)

1. **USER-click only**: Run button MUST be a `<button onClick={...}>` affordance · NO `useEffect` auto-trigger · NO timer-based invocation · NO programmatic invocation outside user click events
2. **Engineer Control Rail only**: V7.A surfaces in Engineer Control Rail · sandbox / cinematic / bridge stay read-only (V83.2 + V83.4 + V85.X carries)
3. **Cancellable**: Run state MUST be cancellable from UI · AbortController-backed · no runaway runs
4. **Prerequisite-gated**: Button disabled when `meshReady=false` OR `bcSetup=false` · no run attempt possible until prereqs satisfied
5. **V130 denylist**: V7.A description text + V7.B state-machine method docs MUST NOT contain "auto-run" / "AI runs" / "automatic" / equivalent · lexical denylist test enforced
6. **V132 = 9**: No new MUTATING_ROUTE · existing `/solve-stream` + `/audit-package/build` endpoints reused (both already counted)
7. **Curated path operational**: V82.4 4-layer realism SSE generator MUST continue to serve demo + bridge flows when no live run active · regression test covers this
8. **V6 bridge READ-ONLY preserved**: V7.D post-run hand-off SURFACES the new run_id but bridge mode itself reads-only (V85.X carry) · no auto-re-trigger from bridge surfaces
9. **State machine transitions reversible to idle**: All terminal states (`done` / `failed` / `cancelled`) MUST allow user to dismiss back to `idle` for next run
10. **Audit-package best-effort**: V7.D's `audit-package/build` call MUST be fire-and-forget · run state does not block on its completion · failure does not propagate as run state regression

## 4 · 4Q gate (every V7 sub-DEC must answer)

1. **LLM offline runnable?** ✓ V7 contracts are all pure UI wiring · no LLM call · state machine is deterministic · SSE consumption uses existing battle-tested hook
2. **Artifacts emitted?** ✓ V7 IS the live-artifact-producing path · real solver run writes canonical `reports/{case_id}/runs/{run_id}/` artifacts · V7.D wires them into V6 bridge
3. **TrustGate intact?** ✓ Audit-package auto-build on `done` transition (V7.D) · run_id in TopBar provenance · existing audit-package GET endpoints surface manifest + bundle
4. **AI advisory only?** ✓ Run button is USER-clicked · V7.A contract tests assert no auto-trigger · V130 invariant lexically enforced via denylist · `foam_agent_adapter.py` AI-trigger path unchanged (V7 doesn't touch it)

## 5 · Honest disclosures (what V7 does NOT do)

- ❌ **AI-triggered solver path** — `foam_agent_adapter.py` AI-trigger remains unchanged · V7.A is the USER-click affordance · two paths coexist
- ❌ **Legacy step-panel-shell SolveStreamContext migration** — disposition (c) was rejected · legacy path continues parallel · V87+ candidate
- ❌ **Cross-case parallel runs** — V7.B state machine is single-case · multiple-case parallel runs = V8+ candidate
- ❌ **Queue / scheduling** — V7 fires a single run on click · no queue · no scheduled retry · V8+ candidate
- ❌ **Run history surface in TopBar** — V7.D surfaces the just-completed run_id, not the full history · multi-run timeline = V8+ candidate
- ❌ **Programmatic runs from CI / dogfood** — V7 is UI-only · `scripts/smoke/dogfood_loop.py` continues to be the CI/dogfood path
- ❌ **Configurable solver flags from UI** — V7 uses default solver settings (icoFoam / simpleFoam via case-dir) · solver-flag editor = V8+ candidate
- ❌ **Backend artifact schema validation** — V7.D trusts existing `RunDetail` schema · V86+ schema-drift Zod guard remains a V85+ deferred Open Q

## 6 · Substrate expansion (V4 + V5 + V6 + V7 coverage map)

| Layer | V4 | V5 | V6 | V7 |
|---|---|---|---|---|
| Static commentary | ✓ | (carry) | (carry) | (carry) |
| Cinematic auto-tour | ✓ | (carry) | (carry) | (carry) |
| Provenance card | ✓ | + V5.D | replaced by V6.D for bridge | (carry · V7.D extends provenance line) |
| Failure-mode showcase | — | ✓ | (curated · carry) | (carry · live failure surfaces via V7.B `failed` state) |
| Sandbox click-through | — | ✓ | + bridge integration | (carry) |
| Multi-case curated state | — | ✓ | (carry) | (carry) |
| Real-artifact bridge (READ) | — | — | ✓ | + post-run handoff (V7.D feeds new run_id) |
| Live-vs-curated diff | — | — | ✓ | (carry · now also catches live-vs-curated divergence in real time) |
| **USER-triggered live solver run** | — | — | — | ✓ NEW V7 |
| **Cancellable run state machine** | — | — | — | ✓ NEW V7 |
| **Live residual SSE in v3 chart** | — | — | — | ✓ NEW V7 |
| **Audit-package auto-build on done** | — | — | — | ✓ NEW V7 |

After V7 lands: the workbench covers the FULL lifecycle:
1. **Static-knowledge layer** (V4) — what canonical CFD knowledge looks like
2. **Interactive-demonstration layer** (V5) — click through curated narratives
3. **Real-data bridge layer (READ)** (V6) — view real run artifacts
4. **Live execution layer (V7)** — USER triggers a real run, watches it stream, hands off to bridge

All four layers under the same 4Q gate, all V130/V132-compliant, all on the same 16-pillar V78 scoring framework.

## 7 · Test substrate target (V86.6 close gate)

- Visual baselines: at least 2 new (84 run-solver-button-disabled · 85 run-solver-button-running-with-LIVE-pill) · target 85 total · steady-state baselines (no post-click async-mount fragility per V84.6 lesson)
- e2e Playwright specs: at least 4 new in `v86-v7-live-solver.spec.ts` (button disabled when prereqs unmet · button enabled + click triggers POST · cancel mid-run · post-run handoff into bridge)
- Contract (vitest) tests: at least 20 new (V7.A button 6 · V7.B state machine 8 · V7.C SSE bridge 4 · V7.D handoff 4)
- Network-mutation guard: confirm V7 emits POSTs ONLY on user click (V130 denylist asserts no `useEffect` auto-fire of mutating fetch)

— V7 Blueprint · 2026-05-17 · LANDED at V86.1
