# V5 Blueprint · Interactive AI-CFD Demo · ACTIVE 2026-05-17

> **Predecessor**: V4 blueprint (`.planning/blueprints/v4/INDEX.md`) · landed V80 · FULLY substantiated by V82 (10/10 case commentary · 4/4 V4 contracts proven · 79 visual baselines)
> **Charter**: `.planning/decisions/2026-05-17_v83_charter_dec.md` (B260)
> **Streak**: 6th consecutive arc with NO scoring framework changes (V78 + V79 + V80 + V81 + V82 + V83)

## 0 · What V5 is + isn't

**V5 IS**:
- An EXTENSION of V4 — V4 contracts (V4.A-V4.D) continue to hold; V5 adds V5.A-V5.D ALONGSIDE
- 4 NEW visual contracts that move the demo from "static showcase of CFD knowledge" to "interactive demonstration of AI-assisted CFD workflow"
- Pure-frontend + curated-state substrate · NO live solver · NO runtime LLM · LLM-offline 4Q gate intact
- Strategic substrate · NOT a new scoring axis (6-arc no-scoring-change discipline carried)

**V5 IS NOT**:
- A replacement for V4 — V4 still measures + governs the static demo surface
- A live OpenFOAM hookup — V5.A sandbox is curated click-through, V5.B failure-mode showcase uses curated narratives, V5.C cinematic uses URL+timer state
- A new pillar / subscore / threshold / scorer-script (V83 charter §3 reverse-stops)
- An aggressive UX takeover — V83 charter §5 reverse-stop #8 prohibits auto-popups, scroll-lock, fixed-position modals · cinematic auto-advance is OPT-IN and PAUSABLE

## 1 · The 30-to-90-second narrative (extends V4's 30s timeline)

V4 narrative was 0..30s (welcome → Step 1 → Step 5 → tour complete). V5 narrative extends this for users who want depth:

| Time | What's on screen (V4 carry + V5 additions) | V5 contract activated |
|---|---|---|
| 0-5 | Welcome banner · "30s tour available" · first-time hint chip | V4.A + V4.D (carry) |
| 5-30 | Step 1 → Step 5 (V4 timeline continues unchanged) | V4.A-C (carry) |
| 30+ | "Tour complete · explore freely OR try sandbox / failure-mode" | V5 entry point |
| 30-60 | **Sandbox mode** · user clicks Step 1 → curated geometry preview → Step 2 → curated mesh preview → ... · feels interactive | V5.A |
| 60-75 | **Failure-mode showcase** · "what happens when X goes wrong" · 3 canonical patterns · AI advisor catches each in real-time | V5.B |
| 75-90 | **Provenance card** · "in this 90 seconds you saw: 3 cases · 9 advisor commentaries · 17 Ghia points · 12 literature citations" | V5.D |
| any | **Cinematic mode toggle** · auto-progress through the tour at fixed pace · pause/resume/back · prefers-reduced-motion respected | V5.C |

V83 charter compliance: tour does NOT auto-advance solver. Sandbox does NOT call mutating backend routes. Cinematic mode does NOT bypass the V80 opt-in pattern.

## 2 · The 4 NEW visual contracts (V5 binding)

### Contract V5.A · Demo Sandbox Mode (V83.2)

**Locks**: the **interactive click-through pattern**. The user opts into `?demo=2` and from that moment on, every click on a pipeline step shows a curated outcome that "feels live" without invoking any backend mutation.

**Don't drift on**:
- URL trigger: `?demo=2` activates sandbox · NOT `?demo=1` (that's the V4 tour mode)
- Sandbox status pill in top-right: `SANDBOX MODE · curated state · no real solver` (font-mono · 11px · text-tertiary border)
- Step 1-5 transitions show curated state for `lid_driven_cavity` (canonical demo case)
  - Step 1: geometry preview (bbox + watertight check passes · 0.3s settle)
  - Step 2: mesh quality table (skewness 0.32 healthy band · per-patch chips)
  - Step 3: BC color-coded patches (inlet green · wall red · symmetry amber)
  - Step 4: SSE residual stream auto-starts via existing V78.1 backend (still GET-only, no mutation)
  - Step 5: comparator + advisor commentary + provenance card preview
- Each step transition shows a small banner "Step N · sandbox curated state" for 1s then fades
- Exit sandbox: click "Exit sandbox" link OR navigate away (URL strips `demo=2`)
- data-testid: `sandbox-mode-pill` + `sandbox-step-banner` + `sandbox-exit`

**Implementation home**: V83.2 — `DemoSandboxV5` React component · activated via `?demo=2`

**Acceptance test**:
- `?demo=2` activates sandbox-mode-pill in TopBar
- Step transitions work via pipeline strip clicks · sandbox banner appears + fades
- NO backend POST/PUT/DELETE during the entire sandbox flow (verified by network log assertion in e2e)
- Exit link clears the `demo` query param

### Contract V5.B · Failure-Mode Showcase (V83.3)

**Locks**: the **"AI catches what novice misses" demonstration**. 3 canonical CFD failure patterns are rendered as opt-in "what would AI advisor say" cards. The user reads the symptom + the AI diagnosis side-by-side.

**Don't drift on**:
- Mounted in the AdvisorContent right-panel when `?failmode=1` query is set
- 3 cards · each ~120px tall · stacked vertically
  - **Card 1 · Mesh-driven divergence** · "Skewness 0.94 on the lid · simpleFoam diverges by iter 50 · AI catches via Pillar 2 physics rule + Pope-skewness threshold" · cites OpenFOAM mesh-quality controls
  - **Card 2 · Under-relaxation oscillation** · "p relax = 0.7 (too aggressive) · residuals oscillate ±0.3 decades around 1e-3 · AI catches via convergence shape pattern" · cites Versteeg & Malalasekera §4.5
  - **Card 3 · Under-resolved wake** · "Cylinder wake at Re=100 with 20 cells / shedding wavelength · St measured 0.21 (overshoots reference 0.166 by 27%) · AI catches via FFT plus Williamson reference" · cites Williamson 1989
- Each card has 3 sections: SYMPTOM (red border) · AI DIAGNOSIS (sand-coral border) · FIX SUGGESTION (text-secondary)
- NO auto-execute "apply fix" button (V132 invariant · V80 reverse-stop carried)
- data-testid: `failure-mode-showcase` + `failure-card-{1,2,3}` + `failure-symptom` + `failure-diagnosis` + `failure-fix`

**Implementation home**: V83.3 — `FailureModeShowcaseV5` mounted in AdvisorContent right-panel

**Acceptance test**:
- `?failmode=1` mounts the showcase
- 3 cards present · each with all 3 sections
- NO buttons inside the showcase (V130/V132 enforced structurally)
- Contract test asserts citation text in each card

### Contract V5.C · Cinematic Mode (V83.4)

**Locks**: the **auto-progressing opt-in tour**. Same V4.A tour beats but advances automatically every ~12 seconds (60s ÷ 5 beats = 12s/beat), with pause/resume/back controls. Strictly opt-in via `?demo=1&cinema=1`. Respects `prefers-reduced-motion` (falls back to manual mode silently).

**Don't drift on**:
- URL trigger: BOTH `demo=1` AND `cinema=1` must be present (additive to V4.A trigger)
- Auto-advance timer = 12000ms · resettable
- Controls in banner: `⏸ pause` · `▶ resume` (when paused) · `← back` · `× exit cinematic`
- Pausing freezes the timer; resume restarts the 12000ms countdown from 0
- `prefers-reduced-motion: reduce` MUST disable auto-advance · timer never starts · pause button hidden
- Visual progress indicator: thin sand-coral line under banner showing 0-100% of current beat (CSS transition · disabled if reduced motion)
- data-testid: `cinematic-mode-active` + `cinematic-pause` + `cinematic-resume` + `cinematic-back` + `cinematic-progress`

**Implementation home**: V83.4 — extension to existing `DemoBannerV4`

**Acceptance test**:
- `?demo=1&cinema=1` activates cinematic mode
- Auto-advance after 12s (test uses fake timers + 12100ms advance)
- Pause stops the timer · resume restarts it
- `prefers-reduced-motion` simulation disables auto-advance entirely (no timer state changes)

### Contract V5.D · Demo Run Provenance Card (V83.5)

**Locks**: the **end-of-tour reward** that gives the demo tangible substance. Shown when the tour completes (last beat finishes OR cinematic exit), summarizing what the user just saw.

**Don't drift on**:
- Renders ONCE when tour completes (state transition from tour-step=6 to tour-step=0/null)
- Card position: bottom-right corner · NOT full-screen overlay · NOT a modal
- Sand-coral border 1px · neutral background · ~280px wide · ~180px tall
- Content (V5.D fields):
  - Headline: "Tour complete · here's what you saw"
  - 4 lines of stats (counts derived from observable URL/localStorage state at exit):
    - `Cases shown: 1` (current case_id)
    - `Pipeline steps walked: 5` (max(step) reached during tour)
    - `Advisor commentary cards visible: ≥3` (V4.B mounted at last step seen)
    - `Citation references: ≥12` (count of curated commentary + comparator gold + truthchain refs)
  - Footer: "Try sandbox mode →" link (sets `?demo=2`) · "× close"
- The counts are static lookups from V4 + V5 substrate · NO analytics beacon · NO telemetry sent anywhere
- data-testid: `provenance-card` + `provenance-stats-{cases,steps,commentary,citations}` + `provenance-sandbox-cta` + `provenance-close`

**Implementation home**: V83.5 — `ProvenanceCardV5` component · mounts conditionally after tour-step transitions to 0

**Acceptance test**:
- Tour completion (last beat → exit) renders `provenance-card`
- 4 stats present with non-zero counts
- NO `<form>`, NO `<input>`, NO fetch/XHR calls (network log assertion)
- "Close" link removes the card from DOM

## 3 · V79+V80+V81+V82 discipline carry (V83 invariants)

V5 is bound by 6-arc discipline:

| Constraint | Source | V83 enforcement |
|---|---|---|
| 16-pillar count fixed | V78 charter | UNCHANGED — V5 IS NOT a pillar; V83 doesn't grow scoring |
| 0 subscore additions | V79 charter | UNCHANGED — V5 contracts absorbed by existing V4 + earlier scorers |
| 0 threshold changes | V79 charter | UNCHANGED — same V78 thresholds throughout V83 |
| 0 scorer scripts | V80 charter | UNCHANGED — V5 substrate measured by existing v78_fleet/ |
| Human-curated commentary | V80 charter | V5.B failure-mode narratives are human-curated (same constraint extended) |
| Aggressive demo UX prohibited | V80 charter | V5.A sandbox + V5.C cinematic are STRICTLY opt-in · pause/exit always available |
| `--arc-label` backward compat | V81 charter | UNCHANGED |
| SSE generator stays LLM-offline | V82 charter | V5.A uses existing V82.4 generator unchanged |
| backend route stays GET-only | V82 charter | V5.A explicitly forbidden from POST/PUT/DELETE |

## 4 · Honest disclosures (V5 limits)

- **Sandbox mode is curated, not live**: Step 1-5 transitions show predetermined state for `lid_driven_cavity` only. The user can click through but every outcome is baked in. This is honest — the demo's job is to show CAPABILITY, not to be a production environment.
- **Failure-mode showcase is narrative, not interactive**: the 3 failure patterns can't be "triggered" by the user · they're cards explaining what AI would catch. Interactive failure injection is a multi-arc effort beyond V5.
- **Cinematic mode advances pipeline state only, not solver state**: auto-advance changes `?step=N` and tour-step; it doesn't pretend to actually run a solver. The SSE stream (if visible) is still V78.1 synthetic.
- **Provenance card stats are static lookups**: counts are derived at render time from observable state. The "cases shown" is always 1 in V5 (we don't track multi-case tour traversal). V6+ could extend.
- **No analytics**: provenance card does NOT phone home. Counts are local-only. This is honest about V130 invariant (no telemetry on user behavior).

## 5 · Acceptance + close gate

V83 close requires:
1. 4 V5 contracts have implementing code (V83.2-V83.5)
2. Each contract has ≥1 contract test (vitest) + ≥1 e2e test (Playwright)
3. V78 scorers UNCHANGED report 16-pillar 100/100 × 2 consecutive iters
4. New visual baselines (if any) registered + stable
5. No new MUTATING_ROUTES (V132 invariant)
6. No runtime LLM calls (V130 invariant · 4Q gate intact)

## 6 · The V5 boundary (when does V6 land?)

V5 covers the demo INTERACTIVITY layer. V6 would land when:
- Live solver hookup becomes substantive (depends on backend SSE physically-real → physically-accurate transition)
- Multi-case sandbox traversal becomes a substrate need (currently 1 case is enough proof)
- Interactive failure injection becomes feasible (depends on solver hookup)

Until those substrate moves, V5 holds. V6 is not "always next arc" — it's "when V5 substrate runs out of depth".

— V5 Blueprint · 2026-05-17 · ACTIVE
