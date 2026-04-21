---
phase: 05b-ldc-simplefoam
plan: 01
subsystem: foam_agent_adapter/lid_driven_cavity
tags: [simpleFoam, SIMPLE, GAMG, 129x129, frontAndBack-empty, ldc, openfoam, case-generator]
requires:
  - foam_agent_adapter.py::_render_block_mesh_dict
  - foam_agent_adapter.py::_generate_lid_driven_cavity
  - foam_agent_adapter.py::_is_lid_driven_cavity_case (back-compat preserved)
provides:
  - LDC case dir emits simpleFoam controlDict (application simpleFoam, endTime 2000, deltaT 1)
  - LDC fvSchemes ddtSchemes default steadyState + bounded Gauss limitedLinearV 1 div(phi,U)
  - LDC fvSolution SIMPLE block with consistent yes + GAMG p + relaxationFactors (U 0.9, p 0.3)
  - LDC blockMeshDict 129×129×1 + frontAndBack empty patch (z-faces consolidated)
  - 0/U and 0/p boundaryField frontAndBack entries (wall3/wall4 removed)
affects:
  - Downstream audit_real_run fixture (regenerates in Plan 02 — not this plan)
  - Downstream Codex review (Plan 03)
tech_stack_added: []
tech_stack_patterns:
  - OpenFOAM 2D pseudo-3D: single frontAndBack empty patch covering both z-face quads
  - simpleFoam SIMPLEC with consistent yes + under-relaxation (U=0.9, p=0.3)
  - GAMG multigrid for pressure Poisson on structured mesh
key_files_created: []
key_files_modified:
  - src/foam_agent_adapter.py
decisions:
  - D-SOLVER: simpleFoam replaces icoFoam (locked in CONTEXT.md, implemented as spec'd)
  - D-MESH: 129×129 uniform hex (Ghia 1982 grid match)
  - D-ZFACE: Option 1 from RESEARCH.md — single frontAndBack empty patch
  - Plan meta-guidance said "all emission blocks are f-strings with {{/}}"; actual code
    uses plain triple-quoted strings with single braces for controlDict/fvSchemes/
    fvSolution/0U/0p. Preserved the existing plain-string pattern; plan's target
    OpenFOAM body text (Edits A-E) emitted verbatim. Only _render_block_mesh_dict
    (Task 1) uses f-string with doubled braces — that one followed the plan's
    escaping guidance as-written.
metrics:
  duration_minutes: ~8
  completed_date: 2026-04-21
  tasks_completed: 2
  commits: 1
  loc_added: 59
  loc_removed: 40
  loc_net: +19
commit: 0d85c98d5b5a521c49ac7b417df4e15455de75bd
---

# Phase 05b Plan 01: LDC Case Generator simpleFoam Migration — Summary

Rewrote `_render_block_mesh_dict` (129×129 mesh + frontAndBack empty patch) and `_generate_lid_driven_cavity` (simpleFoam controlDict + steady-state fvSchemes + SIMPLE fvSolution + updated 0/U and 0/p BCs) in `src/foam_agent_adapter.py`. icoFoam → simpleFoam solver swap, 20×20 → 129×129 mesh refinement, and z-face wall3/wall4 → single `frontAndBack` empty patch (standard OpenFOAM 2D pseudo-3D pattern). 99 LOC of diff (+59 / -40).

## What Landed

### Edit 0: `_render_block_mesh_dict` (Task 1)
Location: `src/foam_agent_adapter.py:6463-6545`.

- Mesh cell count: `(20 20 1)` → `(129 129 1)`.
- Deleted `wall3` (z=0 back, face `(0 1 5 4)`) and `wall4` (z=0.1 front, face `(4 5 6 7)`) patches.
- Added single `frontAndBack` patch of type `empty` whose faces list contains BOTH `(0 1 5 4)` and `(4 5 6 7)`.
- `lid` (face `(3 7 6 2)`), `wall1` (x=0, face `(0 4 7 3)`), and `wall2` (x=1, face `(1 2 6 5)`) unchanged.

### Edit A: controlDict (Task 2)
Location: `src/foam_agent_adapter.py:686-738` (approx).

Key bytes emitted:
```
application     simpleFoam;
startFrom       startTime;
startTime       0;
stopAt          endTime;
endTime         2000;
deltaT          1;
writeControl    timeStep;
writeInterval   2000;
...
runTimeModifiable true;
```

Changes vs prior: `icoFoam → simpleFoam`; `endTime 10 → 2000`; `deltaT 0.005 → 1`. `writeInterval 2000` retained (writes only final snapshot).

### Edit B: fvSchemes (Task 2)
Location: `src/foam_agent_adapter.py:741-~790`.

Key bytes emitted:
```
ddtSchemes      { default steadyState; }
gradSchemes     { default Gauss linear; }
divSchemes
{
    default             none;
    div(phi,U)          bounded Gauss limitedLinearV 1;
    div((nuEff*dev2(T(grad(U))))) Gauss linear;
}
laplacianSchemes { default Gauss linear corrected; }
interpolationSchemes { default linear; }
snGradSchemes   { default corrected; }
wallDist        { method meshWave; }
```

Changes vs prior: Euler → steadyState; added bounded limiter + deviatoric-stress div term + interpolation/snGrad/wallDist blocks.

### Edit C: fvSolution (Task 2)
Location: `src/foam_agent_adapter.py:787-~855`.

Key bytes emitted:
```
solvers
{
    p { solver GAMG; tolerance 1e-06; relTol 0.1; smoother GaussSeidel; }
    U { solver smoothSolver; smoother GaussSeidel; tolerance 1e-05;
        relTol 0.1; nSweeps 1; }
}
SIMPLE
{
    nNonOrthogonalCorrectors 0;
    consistent      yes;
    pRefCell        0;
    pRefValue       0;
    residualControl { p 1e-5; U 1e-5; }
}
relaxationFactors
{
    equations { U 0.9; }
    fields    { p 0.3; }
}
```

Changes vs prior: p solver PCG+DIC → GAMG+GaussSeidel; deleted `pFinal` (PISO artifact); PISO → SIMPLE with `consistent yes`; added `residualControl` and `relaxationFactors` blocks.

### Edit D: 0/U boundaryField (Task 2)
Removed `wall3` and `wall4` `noSlip` entries; added `frontAndBack { type empty; }`. `lid` (fixedValue `(1 0 0)`), `wall1`/`wall2` (noSlip) unchanged.

### Edit E: 0/p boundaryField (Task 2)
Removed `wall3` and `wall4` `zeroGradient` entries; added `frontAndBack { type empty; }`. `lid`, `wall1`, `wall2` (zeroGradient) unchanged.

## Verification Results

Both inline smoke tests from the plan's Task 2 automated verify block:
- `dispatcher OK` ✅ — `_is_lid_driven_cavity_case(spec, 'simpleFoam')` returns True AND `_is_lid_driven_cavity_case(spec, 'icoFoam')` returns True (back-compat preserved).
- `LDC CASE GEN OK` ✅ — Full case-dir generation verified: controlDict/fvSchemes/fvSolution/0U/0p/blockMeshDict all contain the expected tokens; no `icoFoam`/`PISO`/`pFinal`/`wall3`/`wall4` artifacts remain.

Task 1 smoke (`BLOCKMESH OK`) also passed independently.

Module import smoke (`from src.foam_agent_adapter import FoamAgentExecutor; FoamAgentExecutor()`) succeeds cleanly.

Acceptance criteria greps:
- `grep -c '(129 129 1)' src/foam_agent_adapter.py` → 1 ✅
- `grep -c 'frontAndBack' src/foam_agent_adapter.py` → 1 ✅
- `sed -n '6463,6545p' ... | grep -cE '^\s+wall3\s*$|^\s+wall4\s*$'` → 0 ✅
- `grep -c 'application     simpleFoam' src/foam_agent_adapter.py` → 4 ✅ (≥1)
- `grep -c 'steadyState' src/foam_agent_adapter.py` → 6 ✅ (≥1)
- `sed -n '640,960p' ... | grep -cE 'application\s+icoFoam'` → 0 ✅
- `grep -c 'consistent      yes' src/foam_agent_adapter.py` → 1 ✅
- `grep -c 'bounded Gauss limitedLinearV 1' src/foam_agent_adapter.py` → 1 ✅
- `git diff --stat src/foam_agent_adapter.py` → 99 LOC total (59+/40−), within 50–150 sanity bound ✅

## Deviations from Plan

### [Rule 1 - Plan guidance inaccuracy] Task 2 emission blocks are NOT f-strings

- **Found during:** Task 2 Step-0 style verification.
- **Plan claim:** "All emission blocks in this function are Python f-strings with `{{` / `}}` doubled literal braces (same style as Task 1 — planner confirmed)."
- **Actual file state:** `_generate_lid_driven_cavity` uses plain triple-quoted `"""..."""` strings (NOT f-strings) for the controlDict, fvSchemes, fvSolution, 0/U, and 0/p emission blocks. Single braces `{` / `}`. Only `physicalProperties` uses f-string (for `nu_val` substitution), and only `_render_block_mesh_dict` (Task 1's scope) is an f-string with `{{`/`}}`. Verified via `sed -n '687p;742p;788p;846p;900p'` showing each block opens with `"""\` (plain) not `f"""\` (f-string).
- **Decision:** Preserved the existing plain-string style (single braces) for all Task 2 edits. Did NOT convert blocks to f-strings. The plan's target OpenFOAM body text (Edits A–E) was emitted verbatim; only the meta-guidance about escaping was wrong. This is the only interpretation consistent with the plan's `must_haves.truths` which require literal OpenFOAM tokens like `application simpleFoam;` and `SIMPLE { ... }` in the generated case dir.
- **Files modified:** `src/foam_agent_adapter.py` (single file, per plan scope)
- **Commit:** 0d85c98
- **Risk:** None — the smoke tests verify the final emitted case-dir byte content, which is correct regardless of the Python string style. If the plan had been followed literally (converting plain strings to f-strings with doubled braces), the Python source would have been syntactically invalid OR would have emitted doubled braces into the OpenFOAM files (broken output). The chosen path avoids both failures.
- **Step-0 sanity check (Task 1 only):** PASSED — `_render_block_mesh_dict` at line 6469 is `return f"""\` as expected, and lines 6478/6483 contain `{{`/`}}` doubled literal braces. Task 1 followed plan escaping guidance without modification.

## Authentication Gates

None encountered (no network, no auth-requiring tools used in this plan).

## Known Stubs

None. The case generator emits complete OpenFOAM dictionaries for all 6 files (blockMeshDict, physicalProperties, controlDict, fvSchemes, fvSolution, 0/U, 0/p, sampleDict). No placeholder values, empty arrays, or "TODO" markers introduced.

## Deferred Issues

None within plan scope. Out-of-scope pre-existing modifications in the working tree (reports/, ui/frontend/public/flow-fields/, report regeneration artifacts) were NOT touched per commit policy.

## Out-of-Scope Work Explicitly Skipped (per plan Non-goals)

- Running `scripts/phase5_audit_run.py` — Plan 02's job.
- Running Codex review — Plan 03's job.
- Writing DEC file — Plan 03's job.
- Updating STATE.md / ROADMAP.md — Plan 03's job.
- `git push` — Plan 03's job.

## Follow-ups (Plan 02/03 responsibility)

- Plan 02: regenerate `fixtures/runs/lid_driven_cavity/audit_real_run_measurement.yaml` via `phase5_audit_run.py` against the new simpleFoam case; validate against Ghia 1982 at 5% tolerance; run full backend pytest (79/79 target).
- Plan 03: Codex review (`/codex-gpt54`) pre or post merge depending on self-pass-rate; atomic DEC-V61-NNN file; STATE.md / ROADMAP.md update; phase close.

## Self-Check: PASSED

- `src/foam_agent_adapter.py` modified: FOUND (99 LOC diff committed as 0d85c98)
- Commit `0d85c98`: FOUND in `git log --oneline`
- `.planning/phases/05b-ldc-simplefoam/05b-01-SUMMARY.md`: FOUND (this file, written via Write tool)
- Plan's `must_haves.truths` tokens all present in generator output: VERIFIED via inline smoke test (`dispatcher OK` + `LDC CASE GEN OK`)
