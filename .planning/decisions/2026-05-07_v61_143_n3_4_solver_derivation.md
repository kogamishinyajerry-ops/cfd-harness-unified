---
decision_id: DEC-V61-143
title: N3.4 · Solver derivation table (regime × thermal-present → OpenFOAM solver name)
status: Accepted
parent_dec: V61-139
phase: N3
notion_sync_status: pending
---

# DEC-V61-143 · N3.4 Solver Derivation Table

## Status

**Accepted 2026-05-07** — V133 sub-DEC slim 6-field. Low-risk read-only
addition per N3 charter §"low | no [Pre-merge Codex]". Pure derivation
function; no mutation surface.

## Decision

Pure-function mapping `(RegimeContract, MaterialContract.thermal-present?)`
→ `(SolverName, rationale, tested_against_case)`. The Step Physics
panel surfaces the derived solver as informational; engineer sees it
populate when they pick regime + material, and can override in N4
(BC + solver workbench merge).

## Derivation table (8 rows)

| regime | thermal? | solver | regression-fixture |
|---|---|---|---|
| laminar | no | icoFoam | lid_driven_cavity |
| laminar | yes | buoyantPimpleFoam | differential_heated_cavity |
| RANS-RAS | no | simpleFoam | elbow_duct |
| RANS-RAS | yes | buoyantSimpleFoam | differential_heated_cavity |
| RANS-kOmegaSST | no | simpleFoam | straight_pipe |
| RANS-kOmegaSST | yes | buoyantSimpleFoam | differential_heated_cavity |
| LES-stub | no | pimpleFoam | elbow_duct |
| LES-stub | yes | buoyantPimpleFoam | differential_heated_cavity |

Defaults bias towards steady-state RANS (industrial common case).
Engineer running transient overrides in N4. LES-stub picks pimple-
family because LES is inherently transient — engineer must still
hand-edit `momentumTransport` to choose a sub-grid model (N3.3 emitted
a TODO comment).

## Charter ship-blocker invariant

Every row carries a `tested_against_case` regression-fixture ID;
empty value = ship-blocker. Test
`test_every_row_has_a_regression_fixture_id` enforces.

## V132 contract

This module returns a string. **No mutation surface**, no V132 entry
needed. The result is consumed by the Step Physics panel (read-only
display), the future GET endpoint surfacing CaseProfile state (N3.5),
and the N4 solver-dict editor (which will use it as the default-with-
override starting point).

## Defensive branch

`derive_solver` raises `KeyError` when no row matches the (regime,
thermal) tuple — guards against the case where `RegimeKind` grows
in a separate commit without the derivation table being updated.
Test exercises this.

## Files touched

Backend:
- `ui/backend/services/physics/solver_derivation.py` (NEW)
- `ui/backend/services/physics/__init__.py` — re-exports

Tests:
- `ui/backend/tests/test_solver_derivation.py` (14 cases — table
  completeness, every-row-has-fixture invariant, every-row-has-
  rationale invariant, valid solver-name set, all 8 derivation paths,
  defensive KeyError branch)

## Verification

- 14 N3.4 tests green
- Table covers every (RegimeKind × thermal-present) tuple — no orphan
  combos (test asserts set equality)
- Every row's `tested_against_case` non-empty (charter ship-blocker)
- 90+14=104 N3 backend tests collectively green

## Out of scope

- Frontend display of derived solver — N3.5 will surface it via
  CaseProfile binding panel
- N4 solver-dict editor consuming this as default — N4.2
- Steady vs transient toggle override — N4 territory
- Compressible-regime path (Mach > 0.3) — M3-extend
