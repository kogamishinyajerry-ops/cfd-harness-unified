---
decision_id: DEC-V61-144
title: N3.5 · Tolerance template binding (regime → default residual tier)
status: Accepted
parent_dec: V61-139
phase: N3
notion_sync_status: pending
---

# DEC-V61-144 · N3.5 Tolerance Binding

## Status

**Accepted 2026-05-07** — V133 sub-DEC slim 6-field. Low-risk read-only
addition per N3 charter "low | no [Pre-merge Codex]". Pure derivation
table; no mutation surface; no V132 entry needed.

Closes N3 phase: charter (N3.0) + 5 sub-DECs (N3.1-N3.5) all
Accepted.

## Decision

Introduce three tolerance templates (`lab_quality` / `engineering` /
`fast_survey`) carrying per-equation residual targets, plus a regime
→ default-tier mapping. Engineer overrides in N4.2 (solver dict
editor with diff against derived defaults).

## Templates

| tier | momentum | pressure | turbulence | energy | when to use |
|---|---|---|---|---|---|
| `lab_quality` | 1e-7 | 1e-7 | 1e-7 | 1e-7 | V&V, grid-convergence studies, benchmark reproduction |
| `engineering` | 1e-5 | 1e-5 | 1e-5 | 1e-5 | industrial default; converges to 3-4 sig figs on integrals |
| `fast_survey` | 1e-3 | 1e-3 | 1e-3 | 1e-3 | parameter sweeps / shape morphing — qualitative trend only |

## Regime defaults

| regime | default tier | rationale |
|---|---|---|
| `laminar` | engineering | LDC benchmark cases manually opt-in to `lab_quality` |
| `RANS-RAS` | engineering | industrial common case |
| `RANS-kOmegaSST` | engineering | industrial common case |
| `LES-stub` | lab_quality | LES turbulent statistics are sensitive to residual control |

## Charter §"existing CaseProfile machinery"

The charter referenced "existing CaseProfile machinery"; in fact no
prior structured CaseProfile existed (only ad-hoc tolerance values
buried in solver_profiles YAML files). N3.5 is the FIRST sub-DEC to
introduce a structured tolerance contract; the broader CaseProfile
concept (regime + material + solver + tolerance + run-control bundle)
remains reserved for M3-extend / M4 milestones.

## V132 contract

Module returns dataclasses; **no mutation surface**, no registry entry.
The Step Physics panel will surface the derived template as informational;
N4.2 solver-dict editor consumes it as the default-with-override
starting point.

## Tier ordering invariant (test-enforced)

`lab_quality < engineering < fast_survey` on every residual target
field. Test fails if a future edit accidentally inverts the ordering.

## Files touched

Backend:
- `ui/backend/services/physics/tolerance_binding.py` (NEW)
- `ui/backend/services/physics/__init__.py` — re-exports

Tests:
- `ui/backend/tests/test_tolerance_binding.py` (11 cases — three
  tiers exist, every template carries rationale, residuals strictly
  positive, **tier ordering invariant** asserts tighter→looser
  monotonic, every RegimeKind has default tier, LES defaults to
  lab_quality, RANS+laminar default to engineering, derivation
  composition, defensive KeyError branches)

## Verification

- 11 N3.5 tests green
- 115 N3 phase + V132 contract tests green collectively
- Tier ordering invariant prevents silent residual loosening
- Every RegimeKind has a documented default tier (charter ship-
  blocker pattern)

## Out of scope

- Wire derived tolerance into solver-profile YAML rendering — N4.2
- Custom-tier authoring (engineer types own residual targets) — N4-extend
- Per-equation override (e.g. tighten only U) — N4-extend
- Tolerance writer (translate ToleranceTemplate → fvSolution `tolerance`/
  `relTol` lines) — N4.2
- AI advisor recommending a tier given case history — N6 territory
