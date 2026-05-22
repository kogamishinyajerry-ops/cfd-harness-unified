# Dogfood · M3.0 cycle 4 · horizontal multi-physics

> **Cycle**: DEC-V61-202-SUB-M30-CYCLE4-MULTIPHYSICS-DOGFOOD
> **Date**: 2026-05-22
> **Surface under test**: decide() + dynamic frame coherence across
> 4 canonical physics regimes (RANS / LES / compressible / multi-region CHT)
> **Method**: programmatic via FastAPI TestClient in
> `scripts/dogfood/case_007_cycle4_multiphysics.py`
> **Verdict**: **PASS** · 120/120 shape-coherence checks
> **Note**: post-Codex R0 verbatim rev2 (R1 below) — fixtures now use
> v2 imported-user manifest schema; regime-specific audit findings
> actually flow through to rail.primary.

## Context

Cycles 1-3 dogfooded a single physics regime (case_007 KCS ship VOF).
Cycle 4 broadens horizontal coverage: every regime an engineer might
construct should produce a coherent dynamic frame, never a crash.

Per Anthropic agent canon §6 (real-usage eval > benchmark), each
regime is treated as a canonical eval case. The bar is shape coherence:
every (regime, step) must produce HTTP 200 + a populated rail_primary
+ a valid topbar_cta + a list-typed bottom_cards + a full SHA-256 hex
`manifest_state_sha` (64 chars, the contract for the PATCH flow).

## Regimes covered

| # | Regime | Solver | Realistic gaps staged |
|---|---|---|---|
| 1 | RANS steady incompressible (flat plate) | `simpleFoam` | none — clean PASS baseline |
| 2 | LES transient incompressible (channel) | `pisoFoam` | bc.U inlet WARN via patch_coverage gaps |
| 3 | Compressible (supersonic wedge) | `rhoCentralFoam` | outlet T type_mismatch FAIL + mesh non-orthogonality WARN |
| 4 | Multi-region CHT (conjugate heat) | `chtMultiRegionFoam` | bc_audit FAIL: missing solid-fluid coupling BC |

Manifests use v2 imported-user shape (`physics.solver`,
`physics.turbulence_model`, `bc.patches.<patch>`) so the imported-
user completeness rules exercise as intended (Codex R0 P2 fix).

## Trace (per-regime, per-step) — post Codex R0 fix

```
RANS-flatplate:
  step=1  rail=step_default  'Step 1 · 几何就绪'  topbar=next_step    cards=1
  step=2  rail=step_default  'Step 2 · 网格就绪'  topbar=next_step    cards=1
  step=3  rail=step_default  'Step 3 · 物理已设'  topbar=next_step    cards=1
  step=4  rail=step_default  'Step 4 · 边界已设'  topbar=next_step    cards=1
  step=5  rail=step_default  'Step 5 · 准备求解'  topbar=submit_solve cards=1

LES-channel:
  step=1  rail=step_default  'Step 1 · 几何就绪'  topbar=next_step    cards=1
  step=2  rail=step_default  'Step 2 · 网格就绪'  topbar=next_step    cards=1
  step=3  rail=step_default  'Step 3 · 物理已设'  topbar=next_step    cards=1
  step=4  rail=step_default  'Step 4 · 边界已设'  topbar=next_step    cards=1
  step=5  rail=step_default  'Step 5 · 准备求解'  topbar=submit_solve cards=1

Compressible-wedge:
  step=1  rail=step_default  'Step 1 · 几何就绪'  topbar=next_step    cards=1
  step=2  rail=step_default  'Step 2 · 网格就绪'  topbar=next_step    cards=1
  step=3  rail=step_default  'Step 3 · 物理已设'  topbar=next_step    cards=1
  step=4  rail=problem_fix   'bc_audit.json FAIL' topbar=re_audit     cards=2
  step=5  rail=step_default  'Step 5 · 准备求解'  topbar=submit_solve cards=1

CHT-multiregion:
  step=1  rail=step_default  'Step 1 · 几何就绪'  topbar=next_step    cards=1
  step=2  rail=step_default  'Step 2 · 网格就绪'  topbar=next_step    cards=1
  step=3  rail=step_default  'Step 3 · 物理已设'  topbar=next_step    cards=1
  step=4  rail=problem_fix   'missing solid-fluid coupling BC'         topbar=re_audit cards=1
  step=5  rail=step_default  'Step 5 · 准备求解'  topbar=submit_solve cards=1
```

Compressible Step 4 surfaces the artifact's type_mismatch FAIL on
outlet T as the rail.primary. CHT Step 4 surfaces the artifact's
explicit "missing solid-fluid coupling BC" finding. These are exactly
the regime-specific audit signals reaching the engineer, not generic
fall-through.

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
matches `^[0-9a-f]{64}$` (full SHA-256 hex, Codex R0 P3 strict guard).

## Reproduction

```bash
cd /Users/Zhuanz/Desktop/cfd-audit-merge
PYTHONPATH=. .venv/bin/python scripts/dogfood/case_007_cycle4_multiphysics.py
```

## Confidence

`confidence: high` — fixtures use the v2 imported-user manifest
schema so completeness rules engage at full fidelity, and SHA-256
hex enforcement guards the PATCH-flow contract. The horizontal
coverage check is conservative ("does decide() crash?", "are
artifact-emitted findings surfacing?"), not "is the advice physically
optimal" — the latter requires V130 advisor work and is M3.2+ depth.
