---
decision_id: V61-211
title: Solver-block extractor (case dir → SolverBlockSnapshot) — sub-DEC
status: Accepted
parent_dec: V61-207
phase: P2 (Blueprint v4)
notion_sync_status: pending (Accepted at landing — session-end sync)
---

# DEC-V61-211 · Solver-block extractor for case-behavioral eval (Stage-2 2b extension)

## Context

Stage-2 2b spike (`ffaba27`) proved the case-level behavioral eval pattern
works on one real case (case_021 / E02 NASA TMR flat plate) by feeding
`parts_manifest.yaml` directly to `assemble_stack`. The extension survey
([this session, 2026-05-28]) found that all 13 manifest-bearing profiles
produce **identical** `{face_orientation, inlet_outlet}` / 0-findings output —
parts_manifest alone does not discriminate cases.

The case-discrimination signal lives in the `assemble_stack` kwargs the spike
deferred: `solver_block_snapshot`, `shm_dict`, `thermo_dict`, `step_path`,
`thin_wall_inputs`, etc. **No production code constructs any of these from a
case dir** — they exist only as hand-built test fixtures in
`test_advisor_stack.py` and as wire-payload parses in `ai_review.py`. That
is the missing rung for the 2b extension.

## Decision

Build a `case_extractors` sub-package under `ui/backend/services/`, starting
with **one** extractor: `solver_block_extractor.extract(case_dir) →
SolverBlockSnapshot | None`. Use it in a new cross-case behavioral eval and
in the existing spike to demonstrate case-specific advisor dispatch.

### Scope (v0.1 · this DEC)

- **In**: `solver` (from `system/controlDict.application`),
  `adjust_time_step` (from `controlDict.adjustTimeStep`), `delta_t` (from
  `controlDict.deltaT`). Three line-anchored regexes. Honest no-result
  when keys absent. Pure function, stdlib-only imports.
- **Out (deferred to v0.2 / future sub-DEC)**: `preconditioners` (requires
  parsing `fvSolution.solvers.<field>` block contents, including OpenFOAM
  regex-pattern keys like `"(U|k|omega)"` — meaningful complexity,
  meaningful Codex surface).
- **Out (separate sub-DECs)**: `shm_dict`, `thermo_dict`, `step_path`,
  `thin_wall_inputs`, `parts_manifest` extractors. Each is its own arc.

### Scope-locking rationale (anti-feature-creep)

A general OpenFOAM-dict parser is real engineering (regex keys, `#include`,
macros, embedded code, nested lists). v0.1 deliberately avoids the
preconditioners block parser to keep this DEC's surface tight: 3 regexes
that match one key each, on the line they appear, ignoring comments. The
extractor's docstring records exactly what it does NOT support, so a future
caller cannot assume more than is there. v0.2's preconditioners extractor
is a follow-on sub-DEC after v0.1 lands.

### Why solver_block first (and not shm/thermo)

- **Universal**: every OF case has `system/controlDict`; 26 profiles in
  `.planning/case_profiles/*_dicts/` qualify (vs 13 with parts_manifest).
- **Real differentiation, even at v0.1 scope**: 5 distinct solver names
  across the 26 profiles; the **5** density-based ones (rhoSimpleFoam ×2:
  case_006 ×2 — rhoPimpleFoam ×2: case_016, case_031 — rhoCentralFoam ×1:
  case_030) hit `check_solver_block`'s V27 density-based dispatch path that
  incompressible cases skip — case-class discrimination from a 3-regex
  extractor.  *(Recount applied 2026-05-28 mid-implementation: initial DEC
  draft said "4 density-based"; the test
  `test_density_based_subset_is_exactly_5_profiles` failed because the
  actual count is 5 — case_031 rhoPimpleFoam was omitted from the head-count.
  Corrected to 5 in both DEC and test; this footnote pins the correction so
  the discrepancy is auditable.)*
- **Smallest extractor with universal applicability**: thermo_dict only
  differentiates the 4 CHT/APU profiles; step needs CAD that most profiles
  lack; shm_dict needs `snappyHexMeshDict` parsing (larger surface).

### Codex review

This is **correctness-critical shared code** (the extractor's output is
fed to advisor logic that produces findings consumed by the eval — a
buggy extractor would either fail the eval or entrench wrong expectations,
both verdict-relevant). Codex review required (cap=3) before commit lands
in `origin/main`. Local commit allowed under L2. Report archived to
`reports/codex_tool_reports/dec211_*`.

## Architectural placement

- New sub-package: `ui/backend/services/case_extractors/__init__.py` (exports)
  + `solver_block_extractor.py` (impl).
- **Import-linter (ADR-001) scope**: `ui/backend/*` is **out of contract
  scope per ADR-001 §3.2** (the `.importlinter` `root_package` is `src`).
  No contract impact.
- Imports: stdlib (`pathlib`, `re`, `dataclasses`) + the existing
  `solver_block_advisor.SolverBlockSnapshot` for return type. Zero
  third-party deps.

## Four-question gate

| Question | Answer |
|---|---|
| LLM-offline runnable? | ✅ pure function, stdlib only |
| Clear artifacts? | the extracted `SolverBlockSnapshot`; pytest |
| TrustGate/audit explains trust? | the extractor is THE input to behavioral adjudication; the eval IS the trust mechanism |
| AI advisory-only, no mutating route? | ✅ read-only, no writes, no route, no mutation |

## Acceptance (sub-DEC passes when)

1. `ui/backend/services/case_extractors/solver_block_extractor.py` exists,
   imports cleanly, exports `extract(case_dir: Path) → SolverBlockSnapshot | None`.
2. `tests/test_solver_block_extractor.py` parametrizes over all 26
   `.planning/case_profiles/*_dicts/` profiles, asserts every profile
   yields a non-None snapshot, asserts the extracted `solver` field
   matches a baseline mapping (5 distinct solvers across the 26).
3. `tests/test_advisor_stack_real_case_behavioral_spike.py` extended:
   feeds the extractor's output to `assemble_stack(parts_manifest=...,
   solver_block_snapshot=...)` for case_021 (incompressible) and case_030
   (rhoCentralFoam) and asserts the dispatched-advisor sets **differ** —
   the live case-discrimination proof.
4. Codex relay APPROVE or APPROVE_WITH_COMMENTS-with-inline-fixes on the
   extractor module (cap=3); local commit allowed before review per L2,
   reconcile post-review.
5. No regression in the broader test sweep (full v9 + canonical +
   advisor_stack passes alongside the new tests).

## Status

Accepted (cfd-chief-engineer, L2, 2026-05-28) — under user-approved
"α′ extension sub-DEC" route, this session.

## Out of scope (do NOT do under this DEC; record as follow-on)

- Preconditioners block parser (v0.2 of this extractor — separate sub-DEC).
- shm_dict / thermo_dict / step extractors (separate sub-DECs each).
- Wiring the extractor into production routes (`ai_review.py` /
  `ai_diagnose.py`) — that's a route-side decision under a different DEC
  (does production want to discover top-level `parts_manifest.yaml` AND
  read `system/` dicts directly, vs continuing the `inputs/` convention?).
- Extending behavioral assertions to FULL E-case firing sets (needs all
  extractors landed first).

— cfd-chief-engineer, 2026-05-28
