---
followup_id: V70-FOLLOWUP-2
title: V70.2 regime-breadth canonical eval anchors 11 V70-planned advisors not yet landed
opened: 2026-05-16
opened_by: V70.2 (B162)
priority: medium
status: open
---

# V70-FOLLOWUP-2 · 11 V70-planned advisors not yet landed in advisor_stack.py

## Context

V70.2 expanded the canonical eval set from 20 → 30 cases (E21..E30) to cover ≥4 turbulence models × ≥3 compressibility regimes × ≥2 steadiness regimes. The new case rule tables reference 11 advisors that don't currently exist in `ui/backend/services/advisor_stack.py` or any `*advisor*.py` module — they're "anchors for future advisor work" rather than current SSOT enforcement.

This mirrors the V69 pattern (6 V66-B planned advisors disclosed in `v69_v66b_planned_advisors_not_landed.md`).

## 11 planned-but-not-landed advisors

| # | Advisor | Anchored by canonical case | Planned purpose |
|---|---|---|---|
| 1 | `bc_type_validator` | E30 · 2D extrusion canonical | Validate BC type compatibility with patch type (empty / symmetry / cyclic / patch) |
| 2 | `compressibility_regime_advisor` | E22 · supersonic · E23 · transonic transient · E26 · low-Mach | Detect Mach regime + recommend solver branch (rho* vs incompressible) |
| 3 | `dimensionality_check` | E30 · 2D extrusion | Confirm 2D handling (1-cell-depth + empty patches) |
| 4 | `mesh_resolution_advisor` | E27 · DNS Re_tau=590 · E28 · LES backstep | DNS/LES grid resolution criteria (Δx+/Δy+/Δz+ bounds) |
| 5 | `region_coupling_validator` | E29 · CHT laminar | Validate fluid-solid interface T-continuity in chtMultiRegionFoam |
| 6 | `separation_resolution_advisor` | E24 · S-A NACA0012 stall α=18° | Warn on separation-regime accuracy gaps (RANS vs hybrid LES) |
| 7 | `shock_capture_quality_advisor` | E22 · rhoCentralFoam supersonic | Validate flux limiter (minMod / vanLeer) for shock-capturing |
| 8 | `statistics_averaging_advisor` | E25 / E27 / E28 / E30 transient | Validate averaging-window length (≥10 flow-through for RANS · ≥20 for DNS/LES) |
| 9 | `symmetry_validator` | E30 · 2D extrusion | Validate symmetry BC matches mirrored solution invariants |
| 10 | `timestep_validator` | E23 · rhoPimpleFoam transonic transient | Validate CFL < 1 for shock-capturing transient |
| 11 | `turbulence_model_advisor` | E21 / E23 / E24 / E25 / E26 / E27 / E28 | Recommend turbulence model + provide context-aware tips |

## Disposition options (V71+ consideration)

**Option A — Author all 11 advisors in V71 (heavy)**: full SSOT closure but ~3-5 sub-DECs of work.

**Option B — Author the high-leverage 4 (`compressibility_regime_advisor` + `turbulence_model_advisor` + `mesh_resolution_advisor` + `statistics_averaging_advisor`)**: covers ≥7 of the 10 new cases. Remaining 7 advisors deferred to V72+ or formally retired.

**Option C — Formally retire low-value advisors (`symmetry_validator` / `dimensionality_check` / `bc_type_validator`) as "implicit in OpenFOAM solver checks; no advisor needed"**: reduces inflated F-NEW count.

Default: **Option B** unless next-arc charter explicitly mandates otherwise.

## Why this is structural honesty, not "lowered bar"

Per V69 close retro §6.2: the alternative paths (hide them with passing dummies / quick advisor stubs) would pollute the SSOT. Disclosure preserves audit integrity. KNOWN_F_NEW_ADVISORS is the V69-established mechanism that V70.2 inherits.

## Evidence

- `ui/backend/tests/test_canonical_advisor_eval.py` · KNOWN_F_NEW_ADVISORS · V70 batch (11 new entries · header comment lists each)
- `.planning/evals/canonical/E21..E30*.md` · rule firings tables reference these advisors
- `ui/backend/services/advisor_stack.py` + `*advisor*.py` modules · grep confirms 11/11 are absent

— V70-FOLLOWUP-2 · 2026-05-16 · B162
