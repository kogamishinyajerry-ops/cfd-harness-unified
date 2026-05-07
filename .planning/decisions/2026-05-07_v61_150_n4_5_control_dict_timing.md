---
decision_id: DEC-V61-150
title: N4.5 · controlDict timing schema + read-only timing advisor
status: Accepted
parent_dec: V61-145
phase: N4
notion_sync_status: pending
---

# DEC-V61-150 · N4.5 controlDict Timing

## Status

**Accepted 2026-05-07** — V133 sub-DEC slim 6-field. Low-risk per N4
charter "low | no [Pre-merge Codex]". Pure schema + advisor; no
mutation surface. Closes the N4 phase: charter (N4.0) + 5 sub-DECs
(N4.1-N4.5) all Accepted.

## Decision

Land the structured override schema for `system/controlDict` timing
fields + a read-only advisor that emits info / warning hints when
the override is incoherent with the N3.4-derived solver family
(steady vs transient).

Charter §threat-model row 7: "controlDict timing editor lets
transient endTime be set on steady solver" — advisor surfaces this
as INFO hint, not blocker. V130 advisory-only enforced by
structure: advisor is a pure function returning dataclasses; module
is NOT in `KNOWN_MUTATION_FUNCTIONS`.

## Wire shape

```python
class ControlDictTiming(BaseModel):  # extra=forbid
    end_time: float | None        # > 0
    write_interval: float | None  # > 0, capped at 1e6 (~12 days)
    adjust_time_step: bool | None
    max_co: float | None          # (0, 10]
    delta_t: float | None         # > 0
    authored_at: str
```

## Steady-vs-transient solver families

| family | solvers (per N3.4) |
|---|---|
| steady | simpleFoam · buoyantSimpleFoam |
| transient | icoFoam · pimpleFoam · buoyantPimpleFoam |

## Advisor hints

| condition | severity | target | message |
|---|---|---|---|
| steady solver + adjust_time_step set | info | adjust_time_step | "field will be written but ignored" |
| steady solver + max_co set | info | max_co | "field will be written but ignored" |
| steady solver + delta_t set | info | delta_t | "interpreted as outer-loop increment only" |
| transient + max_co set + adjust=False | info | max_co | "value won't take effect (fixed Δt is used)" |
| transient + adjust=True + max_co unset | warning | max_co | "profile default will be used — confirm matches scheme tolerance" |
| write_interval > end_time | info | write_interval | "case will write only final step; typically unit-mismatch typo" |

Hints sort: warnings before info; alpha by target within each
severity bucket. Both invariants tested.

## V130 / V132 enforcement

- Schema accepts engineer input only — no AI auto-fill path
- Advisor returns `list[TimingHint]` dataclasses; **no disk write,
  no API mutation**
- Test asserts `derive_timing_hints` and `timing_advisor` module are
  absent from `KNOWN_MUTATION_FUNCTIONS` — encoded V130 contract

## V132 contract (no new mutator)

This sub-DEC adds NO mutation route — same staging pattern as
N4.2/N4.3. The actual writer that translates `ControlDictTiming` →
`system/controlDict` lines is deferred to N4-extend / downstream
(unified solver-config commit route consuming
URFOverride + SolverDictsOverride + ControlDictTiming + BCContract
in one round-trip).

## Files touched

Backend (NEW):
- `ui/backend/schemas/control_dict_timing.py` — schema
- `ui/backend/services/case_solve/timing_advisor.py` — pure advisor

Tests (NEW):
- `ui/backend/tests/test_control_dict_timing.py` (19 cases —
  schema validators (positivity, max_co bounds (0,10], write_interval
  sanity cap 1e6, extra-keys-forbidden); empty timing → empty hints;
  coherent transient + steady → empty hints; steady + transient-only
  fields → 3 info hint variants; transient max_co + adjust=False
  → info; transient adjust=True + max_co unset → warning;
  write_interval > end_time → info; sort order warnings-before-info
  + alpha by target; V130 advisory-only contract)

## Verification

- 19 N4.5 tests green
- 116 N4 phase + V132 contract tests green collectively
- 14 V132 contract tests still green (no regression)
- Hints sort invariants pinned (warning < info; alpha within)

## N4 phase close summary

| Sub-DEC | LOC backend | Tests | V132 mutator |
|---|---|---|---|
| N4.0 charter (V61-145) | 0 | 0 | n/a |
| N4.1 BCContract (V61-146) | ~640 | 38 | yes (POST /api/cases/{id}/bc-contract) |
| N4.2 SolverDictsOverride (V61-147) | ~480 | 21 | no |
| N4.3 URF advisor (V61-148) | ~280 | 18 | no |
| N4.4 escape hatch (V61-149) | 0 | 6 | no (reuses V102) |
| N4.5 controlDict timing (V61-150) | ~280 | 19 | no |
| **N4 total** | **~1680** | **102** | **+1** |

N4 charter four-question gate (Blueprint v3 §5):
1. ✅ Q1 LLM-offline reachability — every contract is form-driven,
   schema-validated, no LLM call
2. ✅ Q2 artifacts output — N4.1 writes 0.orig/{U, p}; N4.2-N4.5
   schemas consumed by future writer for system/{fvSchemes,
   fvSolution, controlDict}
3. ✅ Q3 audit explainable — diff against derived defaults (N4.2),
   stability hints (N4.3), timing coherence hints (N4.5) all
   surface as inspectable metadata; manifest tracks source/edited_at
   per dict (existing V102 + V104)
4. ✅ Q4 AI advisory only — 2 advisor modules (urf_advisor,
   timing_advisor) explicitly tested NOT in
   KNOWN_MUTATION_FUNCTIONS; only structured-write routes (BCContract)
   are V132 mutators

## Out of scope

- Unified solver-config commit route (POST consuming all 4 schemas
  + writing all 3 dicts atomically) — N4-extend or downstream
- Frontend timing panel + advisor badge rendering — unified Step 3
  Physics setup workbench shell (UI lands additively post-N4)
- Compressible-regime timing knobs (rho-coupling, sub-iteration)
  — M3-extend
- Custom function-object timing controls — M5-extend
