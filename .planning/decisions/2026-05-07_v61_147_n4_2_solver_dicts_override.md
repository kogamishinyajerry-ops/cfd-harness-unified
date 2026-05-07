---
decision_id: DEC-V61-147
title: N4.2 · Solver dict override schema + diff-against-defaults computation
status: Accepted
parent_dec: V61-145
phase: N4
notion_sync_status: pending
---

# DEC-V61-147 · N4.2 Solver Dict Override

## Status

**Accepted 2026-05-07** — V133 sub-DEC slim 6-field. Medium-risk per
N4 charter; Opus confidence high — schema + pure diff function, no
disk write, no V132 mutator. No Codex pre-merge mandate.

## Decision

Land the structured override + diff layer for solver dicts:

- `SolverDictsOverride` Pydantic schema covering most-commonly-tuned
  knobs (linear-solver tolerance/family/relTol per field;
  n_non_orthogonal_correctors; divSchemes default; residualControl
  thresholds)
- `diff_against_defaults()` pure function comparing
  (N3.4-derived solver, N3.5-derived tolerance template) baseline
  against engineer's override; emits sorted list of DiffEntry records

## What this sub-DEC does NOT add (and why)

- **No new V132 mutator route.** The actual rendering of fvSchemes /
  fvSolution / controlDict on disk continues to flow through the
  existing solver_profiles YAML + `bc_setup.py:_atomic_commit_dicts`
  path. N4.2 ships only the structured override schema + diff
  computation; the route + writer integration that translates
  `(SolverDictsOverride, regime, material, tolerance_template)` into
  on-disk dicts is deferred to N4.3 / N4.5 (which DO add their own
  mutators on top of this schema).
- **No frontend dict editor panel.** The visual editor with diff
  display lands in the unified Step 3 Physics setup workbench shell
  (N4.3 onwards). Schema lands first so the panel design has a
  stable wire shape to render against.

This staging matches the N3 pattern (N3.1+N3.2 schemas first,
N3.3 wired the panel + route).

## Wire shape

```python
DivSchemeDefault = Literal[
    "upwind", "linear", "linearUpwind", "limitedLinear", "limitedLinearV",
]

LinearSolverFamily = Literal["PCG", "PBiCGStab", "smoothSolver", "GAMG"]

class LinearSolverOverride(BaseModel):  # extra=forbid
    family: LinearSolverFamily | None
    tolerance: float | None       # > 0
    rel_tol: float | None         # [0, 1)

class SolverDictsOverride(BaseModel):  # extra=forbid
    linear_solvers: dict[str, LinearSolverOverride]  # field-name keys (alnum)
    n_non_orthogonal_correctors: int | None  # 0..5
    div_scheme_default: DivSchemeDefault | None
    residual_control: dict[str, float] | None  # field → > 0 threshold
    authored_at: str
```

## diff_against_defaults

Inputs:
- `solver: SolverName` (from N3.4 derivation)
- `regime: RegimeKind` (for human-readable reason strings)
- `tolerance_template: ToleranceTemplate` (from N3.5)
- `override: SolverDictsOverride`

Output: `list[DiffEntry]` sorted by `path` for stable rendering.

`DiffEntry` is a frozen dataclass with `path` (canonical dotted path),
`baseline` (what the derived defaults would emit), `override` (what
the engineer set), `reason` (human-readable why-it-changed string).

When a linear-solver field name doesn't fit the standard tier mapping
(exoticTransport-style names), `baseline` is None and the diff entry
still surfaces the override for engineer audit.

## Tier-mapping convention

Standard OpenFOAM field names are tier-keyed:

| field | tier (from ToleranceTemplate) |
|---|---|
| U / UFinal | momentum |
| p / pFinal | pressure |
| k / kFinal / omega / omegaFinal / epsilon / epsilonFinal | turbulence |
| T / TFinal | energy |

Other field names: `_baseline_tolerance_for_field` returns None.
This is a deliberate choice — the diff renderer surfaces the override
without claiming a misleading baseline.

## V132 contract

This module **has no mutation surface**. It returns dataclasses; no
disk write. No registry entry needed. The caller (future N4.3 /
N4.5 routes) is responsible for wiring the override into the actual
dict-write path AND for adding their own V132 entries when those
routes land.

## Files touched

Backend (NEW):
- `ui/backend/schemas/solver_dicts.py` — schemas
- `ui/backend/services/case_solve/dict_diff.py` — diff computation

Tests (NEW):
- `ui/backend/tests/test_solver_dicts_override.py` (21 cases —
  field validators including bound checks, literal enforcement,
  charset, residual-threshold positivity, empty-override produces
  empty diff, single + multiple overrides, stable sort, baseline
  varies with tolerance tier, exotic field names yield None
  baseline, frozen DiffEntry)

## Verification

- 21 N4.2 tests green
- 14 V132 contract tests still green (this sub-DEC adds no mutator)
- Diff stable-sorted by path so test assertions don't flake on dict
  iteration order
- Baseline varies correctly with tolerance template tier (lab_quality
  → tighter baseline; same override produces different diff)

## Out of scope

- Route layer + writer integration (POST /api/cases/{id}/solver-dicts)
  — N4.3 (wires URF panel + commit route) or N4.5 (controlDict
  timing + commit route) will add that mutator
- Per-corrector residualControl (P-only / P-final-only) — N4-extend
- Custom limited-* gradient + div schemes (limitedLinear 0.5 /
  limitedCubic / Minmod) — N4-extend
- URF (relaxation factors) — N4.3
- controlDict timing — N4.5
- Frontend solver dict editor panel + diff display — N4.3 (workbench
  shell)
