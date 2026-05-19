# V6 Blueprint · Real-Artifact Bridge · ACTIVE 2026-05-17

> **Predecessor**: V5 blueprint (`.planning/blueprints/v5/INDEX.md`) · landed V83 · FULLY substantiated by V84 (4 visual baselines · 8 e2e specs · 2 lint scripts · multi-case sandbox across 10 Gold-Standard cases)
> **Charter**: `.planning/decisions/2026-05-17_v85_charter_dec.md` (B274)
> **Streak**: 8th consecutive arc target with NO scoring framework changes (V78+V79+V80+V81+V82+V83+V84+V85)

## 0 · What V6 is + isn't

**V6 IS**:
- A **bridge** from V4/V5 curated demo surfaces to REAL OpenFOAM run artifacts
- READ-ONLY consumption of existing `reports/{case_id}/runs/*/` artifacts via existing GET endpoints (`/api/cases/{id}` · `/api/audit-packages/{bundle}/manifest.json` · `/api/cases/{id}/solver/stream`)
- A **graceful-degrade** layer · when no run artifact exists for a case, bridge silently falls back to curated state (V5.A behavior preserved)
- A **strategic answer to the 5-arc live-solver-hookup carry** — V85 partially closes it by surfacing pre-existing run data, deferring full live-trigger to V86+
- An **explicit UI mode** distinct from curated · `?bridge=1` query parameter activates · global LIVE DATA pill · per-step LIVE DATA badge · explicit "exit to curated" CTA

**V6 IS NOT**:
- A replacement for V4 or V5 · curated mode remains default · V4 cinematic + V5 sandbox + V5 failure-mode all continue to function unchanged when bridge is off
- An AI-triggered solver execution path · user pre-runs case offline (existing `scripts/smoke/dogfood_loop.py` or manual OpenFOAM invocation) · bridge reads resulting artifacts only
- A new mutating endpoint · V132 MUTATING_ROUTES locked at 9 unchanged
- A new auth surface · bridge consumes existing unauthenticated GET endpoints
- An "AI-driven CFD" pivot · V130 (AI advisor not driver) intact · bridge AI is **passive-observe** only · diff panel surfaces divergences as observations, not as remediation actions
- A new pillar / subscore / threshold / scorer-script (V85 charter §3 reverse-stops · 8th arc no-scoring-change target)

## 1 · The bridge narrative (extends V4 30s + V5 30-90s timeline)

V4 + V5 narratives cover curated demo. V6 extends for users who pre-ran a real case and want to see their data flow through the same demo substrate:

| Mode | URL trigger | What user sees | Source of truth |
|---|---|---|---|
| Default | `/workbench/v3/case/{id}` | Curated step labels (V4) · curated sandbox banners (V5.A) | `sandbox_step_states.ts` + V4 commentary corpus |
| Cinematic | `+ ?demo=1&cinema=1` | 12s auto-tour through curated state | V4 + V5.C |
| Sandbox | `+ ?demo=2` | Click-through curated state (per-case · 10 cases) | V5.A `getSandboxStepState(caseId, step)` |
| Failure-mode | `+ ?failmode=1` | 3 curated failure cards (mesh skewness · under-relaxation · wake) | V5.B `failure_modes.ts` |
| **Bridge (NEW · V6)** | `+ ?bridge=1` | Step banners populated from REAL artifact data · LIVE DATA badge · diff panel vs curated | **V6.A `getBridgeStepState(caseId, step)`** reading from `reports/{case}/runs/*/` via existing GET endpoints |
| Bridge + Sandbox | `+ ?demo=2&bridge=1` | Sandbox click-through showing REAL per-step data instead of curated narrative | V6.A + V5.A precedence: bridge takes over IF artifact present, else curated fallback |

## 2 · The 4 V6 contracts

### V6.A · Bridge Reader (data layer)

Frontend hook `src/data/run_artifact_reader.ts`:

```ts
export interface BridgeStepState {
  source: "real_artifact";
  caseId: string;
  runId: string;          // from reports/{case}/runs/{timestamp}/summary.json
  commitSha?: string;     // from summary.json provenance
  banner: string;         // human-curated template + real values interpolated
  rawArtifact: {
    path: string;
    timestamp: string;
    summary?: object;
    measurement?: object;
    verdict?: object;
  };
}

export async function getBridgeStepState(
  caseId: string,
  step: StepId,
): Promise<BridgeStepState | null>;
```

- Reads from existing endpoints:
  - `GET /api/cases/{caseId}` → case metadata (already wired in `useQuery`)
  - `GET /api/cases/{caseId}/completeness` → step completion state (already wired)
  - `reports/{caseId}/runs/{timestamp}/summary.json` → run-level provenance (via new public-static read)
  - `GET /api/audit-packages/{bundle_id}/manifest.json` → audit metadata (already exists)
- Returns `null` when artifact missing → caller falls back to curated `getSandboxStepState`
- All read paths are GET-only · no POST/PUT/DELETE · V132 invariant safe

### V6.B · Bridge-Mode Sandbox (UI integration)

`DemoSandboxV5` extended with `bridgeActive` prop:

```tsx
interface DemoSandboxV5Props {
  stepId: StepId;
  caseId?: string | null;
  bridgeActive?: boolean;  // NEW V6
}
```

Behavior:
- When `bridgeActive && caseId`: attempts `getBridgeStepState(caseId, step)` first
- If returns non-null: renders REAL state with `data-source="bridge"` + LIVE DATA badge
- If returns null OR `!bridgeActive`: renders curated `getSandboxStepState(caseId, step)` with existing `data-source="curated"` semantics
- Contract tests cover BOTH modes for at least lid_driven_cavity (real artifact present) and a case without artifacts (curated fallback)

### V6.C · Live-vs-Curated Diff Panel (component)

New component `LiveVsCuratedDiffV6`:

```tsx
<LiveVsCuratedDiffV6
  caseId={caseId}
  stepId={stepId}
  curatedBanner={...}
  bridgeBanner={...}
/>
```

Renders:
- Two-column display: curated banner vs real-artifact banner for current step
- If significant divergence (e.g., curated says "skewness 0.32" but real artifact shows skewness 0.42): highlight as `[divergence]` badge with AI advisor observation note
- Observations are **passive** — they describe the difference, they do NOT recommend an action or auto-execute a fix (V130 invariant)
- Hidden when bridge mode is OFF (default state preserved)

### V6.D · Bridge Truth-Gate Disclosure (component)

New component `BridgeModeShowcase`:

```tsx
<BridgeModeShowcase
  active={bridgeActive}
  caseId={caseId}
  runId={runId}
  commitSha={commitSha}
/>
```

Renders (when `active=true`):
- Global pill (top, distinct from `sandbox-mode-pill`): "LIVE DATA · advisor in passive mode · no AI mutation"
- Provenance line: `case_id · run_id · commit SHA · checksum · audit-package URL` (from real artifact)
- Explicit "× exit to curated" link (clears `?bridge` query param · sets URL to default curated mode)
- Visual distinction from `sandbox-mode-pill`: different position (left vs right) or different color accent (still within #b78b65 palette discipline · sand-coral OK)

## 3 · Reverse-stops (V6 contracts MUST honor)

1. **Bridge mode READ-ONLY**: zero new MUTATING_ROUTES · count locked at 9 · V132 invariant
2. **Bridge data sourcing from existing artifacts**: NO AI-triggered solver execution · user pre-runs case offline · V130 invariant
3. **Bridge mode opt-in**: `?bridge=1` query parameter required · default = curated · no automatic activation
4. **AI in bridge mode is passive-observe**: diff panel surfaces divergences as observations · no auto-execute · no remediation buttons · no advisory side effects beyond UI text
5. **Bridge UI visually distinct from curated**: LIVE DATA pill + per-step badge mandatory · no ambiguity about which mode is active
6. **Graceful degrade**: missing artifact → fall back to curated · NO crash · NO error toast · NO AI auto-trigger to generate missing data
7. **Run artifact provenance from source**: `run_id` · `commit SHA` · `checksum` · `audit-package URL` MUST come from the run artifact, NOT synthesized in frontend
8. **Curated mode unchanged**: V4 + V5 surfaces continue to function identically when bridge is off · zero curated-mode regression

## 4 · 4Q gate (every V6 sub-DEC must answer)

1. **LLM offline runnable?** ✓ Bridge reads static artifacts · no runtime LLM call · diff panel observations are deterministic comparisons (numerical thresholds)
2. **Artifacts emitted?** ✓ Bridge mode SURFACES real artifacts as the primary value · this is the entire point of V6
3. **TrustGate intact?** ✓ Zero new MUTATING_ROUTES · diff panel marks divergences without acting · truth-gate makes mode explicit at every surface
4. **AI advisory only?** ✓ Bridge mode AI is passive-observe only · no auto-execute · no remediation · curated AI advisory paths unchanged

## 5 · Honest disclosures (what V6 does NOT do)

- ❌ **Live-trigger solver from UI** — bridge reads pre-existing artifacts only · live-trigger remains V86+ candidate (likely a separate dedicated arc · multi-week commitment · auth-boundary risk)
- ❌ **Cross-case artifact comparison** — V6 surfaces one case at a time · cross-case diff is V7+ candidate
- ❌ **Time-series of multiple runs for same case** — V6 picks the most-recent run · multi-run timeline is V7+ candidate
- ❌ **Bridge cinematic mode** — `?bridge=1&cinema=1` not in V6 scope · cinematic was V5.C · bridge cinematic = V86 candidate
- ❌ **Bridge for failure-mode showcase** — V5.B failure-mode is curated · live-failure detection from real artifacts is V86+ candidate
- ❌ **Bridge provenance card** — V5.D provenance card is tour-completion specific · bridge has its own truth-gate (V6.D) instead
- ❌ **Backend artifact validation** — V6 trusts existing `summary.json`/`measurement.yaml`/`verdict.json` schema · schema validation is V86 candidate

## 6 · Substrate expansion (V4 + V5 + V6 coverage map)

| Layer | V4 | V5 | V6 |
|---|---|---|---|
| Static commentary corpus | ✓ (`advisor_commentary.ts`) | (carry) | (carry) |
| Cinematic auto-tour | ✓ (DemoBannerV4) | (carry) | (carry) |
| Provenance card | ✓ (V4.D ProvenanceCardV4) | + V5.D (post-tour) | replaced by V6.D for bridge mode |
| Failure-mode showcase | — | ✓ (V5.B FailureModeShowcaseV5) | (curated · carry) |
| Sandbox click-through | — | ✓ (V5.A DemoSandboxV5) | + bridge-mode integration (V6.B) |
| Multi-case curated state | — | ✓ (V5 substrate · V84.5 multi-case sandbox) | (carry) |
| **Real-artifact bridge** | — | — | ✓ NEW V6 |
| **Live-vs-curated diff** | — | — | ✓ NEW V6 |

After V6 lands: the demo showcase covers (a) static-knowledge layer (V4), (b) interactive-demonstration layer (V5), AND (c) real-data bridge layer (V6) — all under the same 4Q gate, all LLM-offline-runnable, all V130/V132-compliant.

## 7 · Test substrate target (V85.6 close gate)

- Visual baselines: at least 4 new (84 bridge pill · 85 LIVE DATA badge · 86 diff panel · 87 bridge truth-gate provenance line) · target 87 total
- e2e specs: at least 6 new in `v85-v6-bridge.spec.ts` (bridge activation · curated→bridge toggle · graceful degrade when artifact missing · diff panel divergence detection · bridge exit CTA · multi-case bridge for lid_driven_cavity)
- Contract (vitest) tests: at least 15 new (V6.A reader · V6.B sandbox extension · V6.C diff · V6.D truth-gate · network-mutation guard for bridge flow)
- Network-mutation guard: bridge flow MUST emit zero POST/PUT/DELETE (parallel to V84.2 sandbox network guard)

— V6 Blueprint · 2026-05-17 · LANDED at V85.1
