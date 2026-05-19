# Blueprints v4 · Top-Tier Full-Pipeline AI CFD Demo Showcase

> **Authored**: 2026-05-17 (V80 strategic pivot · post V79 close)
> **Predecessor**: `.planning/blueprints/v3/INDEX.md` (8-image visual SSOT · V70 → V79)
> **Status**: ACCEPTED — V80.1 substrate landing this blueprint
> **Relationship to V3**: V4 EXTENDS V3 · does NOT replace · V3's 8-image visual contracts remain SSOT for the workbench surface
> **Anti-fraud rule**: any V80+ implementation arc that touches demo showcase surface must reference this V4 INDEX by section in its DEC + commit message

## 0 · Why V4 exists

V3 blueprint (2026-05-16) locked the **workbench's structural visual contract**: 4-panel grid, 5-step pipeline, viewport mode router, single sand-coral accent, V130/V132 invariants.

V67-C through V79 (15 arcs) delivered that workbench. By V79 close: 16-pillar 100/100, 76 visual baselines validated, vtk.js 3D viewport with camera presets, SSE live residual streaming, audit-package E2E verified, a11y compliant, cross-browser config ready.

**What V3 did NOT specify**: how a FRESH engineer experiences the project for the first time. The workbench is excellent for an engineer who already knows what they're doing; V4's mission is to make it READABLE in 30 seconds to someone who doesn't.

V4 is the **demo showcase layer** on top of the V3 workbench. It does not change V3's structural contracts.

## 1 · The 30-second narrative

V4's North Star is a 30-second walk-through that a fresh engineer can experience on `/workbench/v3?demo=1`:

| t (s) | Frame | What's on screen | V3 substrate | V4 demo overlay |
|---|---|---|---|---|
| 0-2 | Empty workbench | V3 Image 01 (empty shell) | persistent 4-panel grid | demo banner top-center: "30s tour available · [Start tour]" |
| 2-5 | Demo banner clicked | V3 Image 02 selecting lid_driven_cavity, navigating to Step 1 | left-panel case browser | tour-step-1 callout · arrow pointing at active case |
| 5-10 | Step 1 Import | V3 Image 02 (geometry view) | vtk canvas with imported geometry | tour-step-2 callout · "This case has a watertight geometry — Inspector confirms" |
| 10-15 | Step 2 Mesh | V3 Image 03 (mesh wireframe + Console) | mesh wireframe + bottom panel | tour-step-3 callout · "Mesh quality table on the right · AI advisor flags 0.7% high-skewness cells" |
| 15-20 | Step 3 Physics | V3 Image 04 (BC color coding + MaterialCard) | BC patches in dusty palette | tour-step-4 callout · "Color-coded patches · INLET green · WALL red · SYMMETRY amber" |
| 20-25 | Step 4 Solver | V3 Image 05 (residuals chart + console) | residuals + SSE live stream + SolverStateBadge | tour-step-5 callout · "Real-time residual streaming from backend SSE · solver converges at iter ~170" |
| 25-30 | Step 5 Postprocess | V3 Image 07 (Ghia comparison + TrustGate PASS) | gold-vs-actual comparator + TrustGate verdict | tour-step-6 callout · "Verified against Ghia 1982 · within ±5% band · audit package downloadable" |
| 30+ | Tour complete | Workbench in normal state | unchanged | dismiss banner appears bottom · "Tour complete · explore freely" |

**Critical constraint**: the tour does NOT auto-run the solver. The user clicks through. The "real-time residuals" in t=20-25 use the V77+V78 SSE substrate that's already wired — but the tour exposes them as a narrative beat, not as an auto-executed step.

V130 invariant compliance: at no point does the demo make the AI "run" anything. The AI advisor commentary (V80.3) is curated text describing what's already happening on screen.

## 2 · The 4 NEW visual contracts (V4 binding)

V3 had 8 visual contracts. V4 adds 4 NEW contracts, anchored to the 4 V80 sub-DECs:

### Contract V4.A · Demo banner (V80.2)

**Locks**: the **non-aggressive opt-in pattern**. The banner is a peer to V3 Image 01's empty-shell layout; it does NOT take over the page.

**Don't drift on**:
- Top-of-page strip · ~36px tall · sand-coral border-bottom 1px · NEUTRAL background (no fill highlight)
- Text: `30-second tour available · ` followed by `[Start tour ›]` text-link styled (NOT button-styled · no rounded fill · just sand-coral underline)
- Right edge: `× dismiss` text-link in text-tertiary
- Banner is dismissable PERMANENTLY per browser via localStorage key `v80-demo-banner-dismissed=1`
- When dismissed, the page reverts to the canonical V3 Image 01 empty-shell
- When started, banner becomes a thin progress indicator with `step N of 6 · [Next ›] · [Skip tour]` controls

**Implementation task home**: V80.2 — `DemoBannerV4` React component · `/workbench/v3?demo=1` query parameter or localStorage flag activates the tour

**Acceptance test** (e2e v3-a11y-audit absorbs this):
- `[data-testid='demo-banner']` exists when `?demo=1` query present
- Banner has tabIndex + visible focus ring on `[data-testid='demo-banner-start']` link
- Dismissing the banner sets localStorage AND removes the banner from DOM
- The tour CANNOT take over the page (no `position:fixed` modal · no scroll lock · no full-screen overlay)

### Contract V4.B · AI advisor depth panel (V80.3)

**Locks**: the **V130 invariant rendered as substrate**. The advisor doesn't just say "info / warn / error" — it explains WHY in 3 distinct commentary kinds keyed to (case_id, step).

**Don't drift on**:
- Right Panel Advisor tab (V3 Image 06 base) gains 3 NEW commentary kinds (each appears when the case + step matches):
  - `advisor-commentary-mesh-quality` (appears on Step 2): mesh skewness / aspect ratio reasoning · cites V-row + reference textbook
  - `advisor-commentary-convergence` (appears on Step 4 when SolverStateBadge state=converged): convergence diagnostics · cites residual decay pattern
  - `advisor-commentary-result-interpretation` (appears on Step 5): result verdict explanation · cites gold reference + tolerance band
- Each commentary card uses the V3 Image 06 advisor-finding paragraph form · NOT bullet list · NOT button list
- Each commentary's body text is HUMAN-CURATED in `ui/frontend/src/data/advisor_commentary.ts` · NOT runtime LLM-generated · keyed by `(case_id, step) → string`
- Footer phrase preserved verbatim: `N advisor rules fired · 0 actions taken · all suggestions advisory · V132 locked`
- V132 reverse-stop: zero buttons with `auto-execute` / `Apply` / `Run` semantics

**Implementation task home**: V80.3 — `AdvisorCommentaryV4` component + commentary data module

**Acceptance test**:
- For lid_driven_cavity at step=2: `[data-testid='advisor-commentary-mesh-quality']` exists with body text matching the curated snippet
- For lid_driven_cavity at step=4 when state=converged: `-convergence` card exists
- For lid_driven_cavity at step=5: `-result-interpretation` card exists
- ZERO elements with `data-auto-execute=true` exist
- vitest unit test asserts the data module exports the canonical (case, step) → snippet map

### Contract V4.C · Gold-vs-actual comparator (V80.4)

**Locks**: the **scientifically credible verdict surface**. V3 Image 07 had a single chart titled "u(y) along x = 0.5 · Ghia 1982 vs. computed"; V4 makes that chart REAL with overlaid curves not abstract placeholders.

**Don't drift on**:
- SVG-based · NO canvas / NO chart library dependency (must work offline · LLM-offline 4Q gate)
- Two curves overlaid in single coordinate space:
  - Computed: solid line · sand-coral `#b78b65` · stroke-width 1.8
  - Reference (Ghia 1982): open circles · stroke `#9a9aa0` · NO fill · circle radius 4
- ±5% tolerance band: sand-coral fill · opacity 0.08 · drawn behind both curves
- Axes: Inter 11px text-secondary labels · y-axis "u (normalized)" · x-axis "y/H"
- Legend top-right: 2 entries · `▬ computed` + `○ Ghia 1982`
- Data points: 17 (Ghia's canonical lid_driven_cavity u-centerline sampling)
- Worst-point highlight: small dot in dusty-amber `#a89060` on the point with max |Δu| · annotation `max |Δu| = X.X%`
- data-testid: `comparator-gold-actual-{case_id}-{quantity}` (e.g., `comparator-gold-actual-lid_driven_cavity-u_centerline`)

**Implementation task home**: V80.4 — `ComparatorV4` component · mounts in Step 5 viewport view alongside `GoldDeltaPanel`

**Acceptance test**:
- For lid_driven_cavity at step=5 viewport=report: `[data-testid='comparator-gold-actual-lid_driven_cavity-u_centerline']` SVG exists
- SVG has ≥17 circle elements (reference points) + 1 polyline (computed curve)
- max-delta annotation is visible
- Visual baseline added (number 77) for this comparator surface

### Contract V4.D · First-time landing (V80.2 + 4Q gate)

**Locks**: the **fresh-engineer cold-start experience**. When a user lands on `/workbench/v3` with no query params and no localStorage state, they see a polished but quiet first-time hint.

**Don't drift on**:
- V3 Image 01 empty-shell is the BASE state · V4 layer is purely additive
- Tiny text-tertiary footer chip top-right: `New here? · [30s tour]` — NOT a banner · NOT a popup
- Dismissed permanently via the same localStorage key as Contract V4.A
- Activating the tour transitions through `?demo=1` URL state · normal V3 navigation works around it
- The tour does NOT pretend to be the canonical workbench experience — it's an opt-in walk-through

**Implementation task home**: V80.2 — included in `DemoBannerV4` logic

**Acceptance test**:
- Cold visit to `/workbench/v3` shows `[data-testid='first-time-hint']` in TopBar area
- Clicking it sets `?demo=1` and activates the tour
- Dismissing it sets localStorage AND removes the hint
- localStorage state survives reload

## 3 · V79-discipline carry (V80 invariants)

V4 blueprint is bound by the V78+V79+V80 scoring discipline:

| Constraint | Source | V80 enforcement |
|---|---|---|
| Pillar count = 16 | V78 charter §5 | V80 reverse-stop §6.3 |
| NO new subscore | V79 charter | V80 reverse-stop §6.4 |
| NO V78 scorer threshold change | V79 charter | V80 reverse-stop §6.5 |
| NO new `vN_fleet/` directory | V80 charter | V80 reverse-stop §6.6 |
| AI advisor commentary human-curated | V80 charter | V80 reverse-stop §6.7 + V130 invariant |
| Demo mode opt-in only · no aggressive UX | V80 charter | V80 reverse-stop §6.8 |

## 4 · V3 → V4 visual baseline mapping

| Visual contract | V3 baseline # | V4 substrate addition |
|---|---|---|
| V3 Image 01 empty-shell | 23 | V4.A demo banner (when ?demo=1) → baseline 78 |
| V3 Image 02 import step | 24 | V4.D first-time hint → already absorbed in 23/77 surfaces |
| V3 Image 06 advisor tab | 28 | V4.B advisor commentary → baseline 79 (`28-v3-advisor-tab.png` re-snap with commentary visible) |
| V3 Image 07 results | 29 | V4.C comparator → baseline 77 (`77-v4-comparator-gold-actual.png`) |
| — | — | V4.D first-time hint isolated → baseline 80 |

Total post-V80 baseline count: 76 + 4 = **80 visual baselines** · Pillar 4 visualization scorer's V78 threshold (≥76) holds and is exceeded.

## 5 · Honest disclosures

### What V4 is NOT
- **Not a marketing landing page**. V4's "demo" lives INSIDE the workbench, not as a separate marketing site.
- **Not a Joyride/Shepherd-style overlay framework**. V4 ships its own minimal banner + callout component (~150 LOC) — no JS framework dependency beyond what V3 already uses.
- **Not LLM-driven advisor text**. The 3 commentary kinds in V4.B are HUMAN-CURATED snippets in a TypeScript data module. Future arcs could swap to backend-served curated content, but runtime LLM calls would violate the 4Q gate.
- **Not a pillar / subscore / scorer change.** V4 substrate is absorbed by existing V78 scorers. Pillar count stays at 16.
- **Not a replacement for V3.** V3's 8 visual contracts remain SSOT for the workbench surface. V4 extends with 4 demo-specific contracts.

### What V4 does NOT solve (V81+ candidates)
- Cross-browser actual runs (firefox/webkit) — V79.2 config ready
- Backend SSE physically-accurate convergence — V78.1 synthetic
- SSIM at per-screenshot replacement — V79.3 standalone gate
- Performance benchmarking — pillar candidate for V81 IF measurement axis genuinely missing
- Multi-case demo (V4 tour walks lid_driven_cavity ONLY) — V81+ could add tour variants for backward_facing_step / NACA0012

## 6 · The V4 blueprint commitment

V4 is the FIRST blueprint update since V3 (V70 era · 15 arcs ago). The 1-year cadence of blueprint updates is RIGHT for a stable substrate; this is not annual planning, it's "the user mandate explicitly asked for a next-stage blueprint at V80, so V80 delivers one".

V80 sub-DECs land the substrate. V81+ can iterate against V4 the way V71-V79 iterated against V3.

— Blueprints V4 INDEX · 2026-05-17 · LANDED (V80.1)
