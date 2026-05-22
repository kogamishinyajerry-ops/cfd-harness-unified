# Dogfood · M3.0 cycle 4 · horizontal multi-physics

> **Cycle**: DEC-V61-202-SUB-M30-CYCLE4-MULTIPHYSICS-DOGFOOD
> **Date**: 2026-05-22
> **Surface under test**: decide() + dynamic frame coherence across
> 4 canonical physics regimes (RANS / LES / compressible / multi-region CHT)
> **Method**: programmatic via FastAPI TestClient in
> `scripts/dogfood/case_007_cycle4_multiphysics.py`
> **Verdict**: **PASS** · 120/120 shape-coherence checks

## Context

Cycles 1-3 dogfooded a single physics regime (case_007 KCS ship VOF).
Cycle 4 broadens horizontal coverage: every regime an engineer might
construct should produce a coherent dynamic frame, never a crash.

Per Anthropic agent canon §6 (real-usage eval > benchmark), each
regime is treated as a canonical eval case. The script does NOT
exhaustively cover every physics knob — that's M3.* depth, not M3.0
horizontal breadth. The bar is shape coherence: every (regime, step)
must produce HTTP 200 + a populated rail_primary + a valid topbar_cta
+ a list-typed bottom_cards + a non-empty manifest_state_sha.

## Regimes covered

| # | Regime | Solver | Realistic gaps staged |
|---|---|---|---|
| 1 | RANS steady incompressible (flat plate) | `simpleFoam` | none — clean PASS baseline |
| 2 | LES transient incompressible (channel) | `pisoFoam` | `physics.sub_grid_model` absent + bc.U inlet WARN |
| 3 | Compressible (supersonic wedge) | `rhoCentralFoam` | mesh non-orthogonality WARN + outlet T type_mismatch FAIL |
| 4 | Multi-region CHT (conjugate heat) | `chtMultiRegionFoam` | flat bc_audit finding for missing solid-fluid coupling |

## Trace (per-regime, per-step)

```
RANS-flatplate:
  step=1  rail.kind=step_default     'Step 1 · 几何就绪'        topbar=next_step    cards=1
  step=2  rail.kind=step_default     'Step 2 · 网格就绪'        topbar=next_step    cards=1
  step=3  rail.kind=info_gap         'Fill: physics.solver'     topbar=step_default cards=1
  step=4  rail.kind=info_gap         'Fill: bc.patches'         topbar=step_default cards=1
  step=5  rail.kind=step_default     'Step 5 · 准备求解'        topbar=submit_solve cards=1

LES-channel:
  step=1  rail.kind=step_default     'Step 1 · 几何就绪'        topbar=next_step    cards=1
  step=2  rail.kind=step_default     'Step 2 · 网格就绪'        topbar=next_step    cards=1
  step=3  rail.kind=info_gap         'Fill: physics.solver'     topbar=step_default cards=2
  step=4  rail.kind=info_gap         'Fill: bc.patches'         topbar=step_default cards=1
  step=5  rail.kind=step_default     'Step 5 · 准备求解'        topbar=submit_solve cards=1

Compressible-wedge:
  step=1  rail.kind=step_default     'Step 1 · 几何就绪'        topbar=next_step    cards=1
  step=2  rail.kind=step_default     'Step 2 · 网格就绪'        topbar=next_step    cards=1
  step=3  rail.kind=info_gap         'Fill: physics.solver'     topbar=step_default cards=2
  step=4  rail.kind=problem_fix      'bc_audit.json FAIL'       topbar=re_audit     cards=3
  step=5  rail.kind=step_default     'Step 5 · 准备求解'        topbar=submit_solve cards=1

CHT-multiregion:
  step=1  rail.kind=step_default     'Step 1 · 几何就绪'        topbar=next_step    cards=1
  step=2  rail.kind=step_default     'Step 2 · 网格就绪'        topbar=next_step    cards=1
  step=3  rail.kind=info_gap         'Fill: physics.solver'     topbar=step_default cards=2
  step=4  rail.kind=info_gap         'Fill: bc.patches'         topbar=step_default cards=2
  step=5  rail.kind=step_default     'Step 5 · 准备求解'        topbar=submit_solve cards=1
```

## Verdict matrix

| Regime / Step | 1 | 2 | 3 | 4 | 5 | Total |
|---|---|---|---|---|---|---|
| RANS-flatplate | 6/6 | 6/6 | 6/6 | 6/6 | 6/6 | **30/30** |
| LES-channel | 6/6 | 6/6 | 6/6 | 6/6 | 6/6 | **30/30** |
| Compressible-wedge | 6/6 | 6/6 | 6/6 | 6/6 | 6/6 | **30/30** |
| CHT-multiregion | 6/6 | 6/6 | 6/6 | 6/6 | 6/6 | **30/30** |
| **All** | **24/24** | **24/24** | **24/24** | **24/24** | **24/24** | **120/120** |

6 checks per (regime, step) tuple: HTTP 200 + rail.kind valid + rail.title
non-empty + bottom_cards is list + topbar.kind valid + manifest_state_sha
non-empty hex.

## Observations (for cycle 7 beginner test, NOT cycle 4 fixes)

This dogfood verifies decide() does not crash. It also surfaces a
real M3.0-level UX observation worth flagging here for cycle 7 to
empirically test:

**Schema divergence between manifests and case_completeness gaps.**

All four regimes — including the regime where the manifest *correctly*
declares `solver: simpleFoam` at top level — hit Step 3 with
`info_gap: 'Fill: physics.solver'`. The case_completeness analyzer
wants the solver declared at `physics.solver` (nested), not the
top-level `solver` key the dogfood manifests use. Similarly Step 4
wants `bc.patches`, while the manifests carry `bc_contract.<patch>`.

This is a real product-side concern for the ≤30-minute litmus test:
when an engineer copies their existing OpenFOAM manifest into the
workbench, the workbench may surface gaps the engineer believes are
already filled, with no clear "this is a schema disagreement, not a
real gap" signal. Cycle 7 (real-engineer test) will quantify whether
this confuses beginners or whether the corrective workflow is obvious.

**Cycle 4 explicitly does NOT fix this.** It's not in scope per the
DEC's "out of scope (cycle 5+): schema alignment between manifest
keys and completeness gap field_paths". Logging here so cycle 7 has
the head-start signal.

## Reproduction

```bash
cd /Users/Zhuanz/Desktop/cfd-audit-merge
PYTHONPATH=. .venv/bin/python scripts/dogfood/case_007_cycle4_multiphysics.py
```

## Confidence

`confidence: high` — synthetic but shape-realistic fixtures (cross-
referenced against `ui/backend/audit/cases/*/artifacts/` real cases).
The horizontal coverage check is conservative: it asks "does decide()
crash on this regime?" and "does it return a populated frame?", not
"is the advice physically optimal?". The latter requires V130 advisor
work and is M3.2+ depth.
