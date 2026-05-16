---
decision_id: DEC-V71-2
title: V71.2 · Step views polish · V71.G/H/I LANDED · Step 1/2/3 surfaces fully wired
status: Accepted
parent_dec: DEC-V71-charter
phase: V71
notion_sync_status: pending
predecessor: DEC-V71-1
batch: B171
confidence: high
autonomous_governance: true
verdict: LANDED
v_row_landed: V71.2 (Done dimension #2 of 9)
substrate: V71.1 LANDED B170 commit 9df67ab · iter-1 weighted=91.04
---

# DEC-V71-2 · Step views polish · V71.G/H/I

## 1 · Decision

Land V71.2 — enrich the Step 1/2/3 inspector + viewport surfaces against blueprint Images 02/03/04. Three new primitives:

- **V71.G**: `<QualityRow>` (mesh quality table with semantic pass/warn dot)
- **V71.H**: BCPlaceholder palette tokenization + `data-bc-type` attribution
- **V71.I**: `<MaterialCard>` + `<MaterialRow>` (inline-expandable read-only)

All three primitives are **display-only** (V130 invariant preserved). Expanding a material row reveals a `<p>` element with derivation text — never an `<input>`, `<button>`, or `<textarea>`.

## 2 · Scope

| Tag | Component | File | Purpose |
|-----|-----------|------|---------|
| V71.G | `<QualityRow>` | `InspectorContent.tsx` | Mesh-quality table with verdict dot |
| V71.H | `BC_PALETTE` const + `<g data-bc-type>` | `canvas/BCPlaceholder.tsx` | Tokenized BC viewport |
| V71.I | `<MaterialCard>` + `<MaterialRow>` | `InspectorContent.tsx` | Inline-expandable materials |

## 3 · V130 compliance

`<MaterialRow>` row-click toggles a `<p data-testid="...-derive">` with derivation text. That text is **read-only guidance** (e.g., "U_lid·H/ν = 1·1/0.01 = 100 (laminar regime)"). Zero new mutating buttons, zero new POST/PUT/DELETE endpoints. The v3 contract test (V71.4 will harden it) continues asserting no apply/submit/execute buttons exist anywhere in the Advisor surface.

## 4 · Tests

`npx vitest run` → **417 pass** (was 414 · +3 V71.2 tests). New tests:

1. `Step 2 inspector renders mesh-quality rows with verdict dots (V71.G)` — asserts ≥4 `mesh-quality-row` testids with `data-quality-verdict` attribute · at least one pass/warn verdict present
2. `Step 3 BC viewport renders all 4 BC types via dusty palette (V71.H)` — asserts 4 `bc-patch-{inlet|outlet|walls|symmetry}` testids render
3. `Step 3 MaterialCard rows expand inline on click (V71.I · read-only)` — asserts material-nu row toggles `data-open` true/false on click · derivation element is `<P>` (read-only) not `<INPUT>`

`npx tsc --noEmit` → **PASS**.

## 5 · Goal-backward map

Charter Done dim #2 ("Step 1/2/3 surfaces wired to shell — Step 1 geometry viewport + Inspector metadata · Step 2 mesh wireframe + Inspector quality table + bottom Console · Step 3 BC color-coded patches + MaterialCard inline two-column") → **LANDED**.

Bottom Console at Step 2 is **available on-demand** (engineer clicks `▴` toggle in collapsed bar to expand). The default-collapsed-at-Step-1-3 behavior is per V71.E spec (Image 03 shows BottomPanel collapsed at Step 2).

## 6 · Risks

- Mesh quality verdict thresholds are case-specific (cavity always pass; BFS shows warn on aspect ratio 842 which is a real concern for SST k-ω but acceptable for k-ε). The verdict logic is **hand-tuned** based on case_id; V72+ should wire `/api/cases/:id/mesh-quality` for real-time scoring.
- BC patch data-bc-type currently uses the BFS-shaped representative geometry; for non-BFS cases the patches render as conceptual labels. V71.6 visual baselines lock the BFS reference.

## 7 · Surface-scan trailer

**Surface-scan: clean.** Step 2 mesh quality previously used inline ad-hoc rows (no extraction); V71.G consolidates them into a reusable primitive. The Step 3 MaterialCard previously was inline JSX; V71.I extracts to component + adds interactivity. No pre-existing implementation found via grep for `mesh-quality-row`, `MaterialCard`, `BC_PALETTE`.

## 8 · Counter

Counter +1 (V71 = autonomous_governance: true). Cumulative arc counter for V71: **3** (charter + V71.1 + V71.2).

## 9 · Next

V71.3 — wire `<ResidualsChartV3>` to mounted /api stub + flesh out BottomPanel streaming (currently static SVG · need SSE buffer integration once API substrate stabilizes).

---

**Co-Authored-By**: Claude Opus 4.7 (1M context)
