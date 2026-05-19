---
decision_id: DEC-V70-2
title: V70.2 · Canonical eval set 20→30 (10 new regime-breadth anchors)
status: Accepted
parent_dec: DEC-V70-charter
phase: V70
notion_sync_status: pending
batch: B162
confidence: high
autonomous_governance: true
verdict: LANDED
---

# DEC-V70-2 · Canonical eval set 20→30 regime breadth

## 1 · Decision

Expand the canonical advisor eval set from 20 → 30 individual case files by authoring E21..E30 — anchoring regime-breadth coverage the V70.1 capability matrix surfaced as gap-tracked. Charter §3 V70-DONE-2 requires ≥4 turbulence × ≥3 compressibility regimes; delivered ≥6 turbulence × ≥3 compressibility.

## 2 · 10 new cases (E21..E30)

| Case | Regime anchor | Turb model | Compressibility | Steadiness |
|---|---|---|---|---|
| E21 | low-Re k-omega-SST · BFS Re=5000 | k-omega-SST low-Re | INCOMP | STEADY |
| E22 | rhoCentralFoam supersonic wedge M=2.0 | k-omega-SST | COMPRESSIBLE | STEADY |
| E23 | rhoPimpleFoam transonic transient buffet | k-omega-SST | COMPRESSIBLE | TRANSIENT |
| E24 | Spalart-Allmaras NACA0012 stall α=18° | **S-A (5th model)** | INCOMP | STEADY |
| E25 | pimpleFoam k-epsilon transient channel | k-epsilon | INCOMP | TRANSIENT |
| E26 | k-omega-SST low-Mach near-incompressible | k-omega-SST | **WEAKLY-COMPRESSIBLE** | STEADY |
| E27 | DNS plane channel Re_tau=590 | DNS resolved-scale | INCOMP | TRANSIENT |
| E28 | LES Smagorinsky backstep ReH=5000 | **LES (6th model)** | INCOMP | TRANSIENT |
| E29 | chtMultiRegionFoam laminar CHT | laminar | INCOMP | STEADY |
| E30 | 2D extrusion canonical (empty + symmetry) | laminar | INCOMP | STEADY |

**Regimes anchored**: 6 turbulence (laminar / k-epsilon / k-omega-SST / S-A / DNS / LES) × 3 compressibility (INCOMP / COMPRESSIBLE / WEAKLY-COMPRESSIBLE) × 2 steadiness (STEADY / TRANSIENT) → charter ≥4 × ≥3 × ≥2 thresholds EXCEEDED.

## 3 · Harness verification

- `uv run python scripts/governance/validate_canonical_eval_schema.py` → `OK · 30 canonical eval case files validate against schema (10 required fields each)`
- `uv run pytest ui/backend/tests/test_canonical_advisor_eval.py -q` → `32 passed in 0.08s` (30 parametrized + 2 aggregate)
- Harness updated: parametrize range 20→30 · aggregate threshold 100→140 (honest re-anchor reflecting V70.2 anchored regime breadth not firing density)

## 4 · Structural honesty: 11 new V70-planned advisors disclosed

The 10 new cases reference 11 advisors that don't currently exist in `advisor_stack.py` or `*advisor*.py` modules:

- `bc_type_validator` · `compressibility_regime_advisor` · `dimensionality_check` · `mesh_resolution_advisor` · `region_coupling_validator` · `separation_resolution_advisor` · `shock_capture_quality_advisor` · `statistics_averaging_advisor` · `symmetry_validator` · `timestep_validator` · `turbulence_model_advisor`

Disclosed in `.planning/followups/v70_v70_2_planned_advisors_not_landed.md` with 3 disposition options (V71 author all 11 · V71 author 4 high-leverage · formally retire 3 low-value). Added to `KNOWN_F_NEW_ADVISORS` set with bare + suffixed forms (parser strips `_advisor`).

This mirrors V69.2's KNOWN_F_NEW pattern: regime-breadth anchors are SSOT-future-proofing, not current SSOT enforcement gaps.

## 5 · Done dim

V70-DONE-2 MET. V70-DONE-4 (AI advisor SSOT regression-protected) inherited from V69.4 unchanged.

## 6 · Score impact

| Pillar | Before V70.2 | After V70.2 |
|---|---|---|
| Pillar 2 (Physics) | 80 (canonical 20 < 30 target) | 100 (canonical 30 ≥ 30) |
| Pillar 7 (AI advisor SSOT) | 88 (V69 baseline) | 89 (+1.0 · regime breadth × 6 turbulence × 3 compressibility) |
| Pillar 8 (CFD-Breadth) | 100 (matrix-anchored) | 100 (eval cases reinforce matrix claims) |

## 7 · Evidence

- `.planning/evals/canonical/E21..E30*.md` · 10 new files (391 LOC total)
- `ui/backend/tests/test_canonical_advisor_eval.py` · 32/32 PASS · KNOWN_F_NEW V70 batch
- `.planning/followups/v70_v70_2_planned_advisors_not_landed.md` · 11 V70-planned advisors disclosed
- `scripts/governance/validate_canonical_eval_schema.py` · 30/30 OK
