# Phase 5b: LDC simpleFoam migration + Ghia 1982 match — Context

**Gathered:** 2026-04-21
**Status:** Ready for planning
**Source:** User direct input (auto-mode Phase 5b kickoff, post Phase 5a closure)

<domain>
## Phase Boundary

This is the **first of 8 Phase 5b per-case sub-phases** closing the gap between Phase 5a's real-solver baseline (2 PASS / 8 FAIL) and full audit-grade coverage. Scope is strictly the `lid_driven_cavity` case; the remaining 7 FAIL cases (BFS, turbulent_flat_plate, duct_flow, impinging_jet, naca0012_airfoil, differential_heated_cavity, rayleigh_benard_convection) each get their own sub-phase that will reuse the simpleFoam migration pattern established here.

**What this phase delivers:**
- `lid_driven_cavity` case generator emits a simpleFoam (steady-state SIMPLE) OpenFOAM case dir instead of icoFoam (transient PISO).
- Mesh refinement to 129×129 (matches Ghia 1982).
- Regenerated `audit_real_run` fixture with `comparator_passed: true` at 5% tolerance against Ghia u_centerline.
- All 79 backend pytest cases remain green; no regression on the existing teaching fixtures (reference_pass / under_resolved / wrong_model / grid_convergence).

**What this phase explicitly does NOT deliver:**
- Tuning any other FAIL case (separate sub-phases).
- A generic simpleFoam pattern abstracted across all internal cases — single-case focus only.
- Second-order scheme upgrades or turbulence model work.
- Byte-reproducibility regression tests that actually re-run the solver (still deferred to tests/integration/).
- Any change to `knowledge/gold_standards/lid_driven_cavity.yaml` (三禁区 #3, not in scope).
</domain>

<decisions>
## Implementation Decisions

### Solver choice
- **LOCKED**: simpleFoam (steady-state SIMPLE coupling).
- Rationale: icoFoam is transient; Ghia 1982's reference is the asymptotic steady state. Prior Phase 5b investigation (reverted) confirmed 30 characteristic times (endTime=3s, dt=0.0005s) of icoFoam does NOT reach Ghia's steady state — the solver settles into a transient "dragged-down profile" that monotonically decreases from lid. simpleFoam converges to steady state in minutes with SIMPLE, no CFL stability issue.

### Mesh
- **LOCKED**: 129×129 uniform hex, 1 cell in z (2D pseudo-3D).
- Rationale: Matches Ghia 1982's 129×129 grid exactly, eliminating mesh-induced interpolation error at the 17 gold y-points. Previous baseline was 20×20; Phase 5a attempt bumped to 129×129 with icoFoam (wrong-signed physics); this phase pairs 129×129 with simpleFoam (correct physics).
- `simpleGrading (1 1 1)` — uniform, no near-wall clustering. LDC doesn't need it at Re=100.

### Re and physical dimensions
- **LOCKED**: unchanged from existing generator. Re = task_spec.Re or 100 default. convertToMeters = 0.1 so physical domain 0.1m × 0.1m. U_lid = 1.0 m/s. nu = 0.1/Re. These come from TaskSpec via `_task_spec_from_case_id("lid_driven_cavity")` and should remain parametric.

### fvSchemes for simpleFoam
- **Claude's Discretion** (no project-specific constraint):
  - Gradient: `Gauss linear`.
  - Divergence: `div(phi,U) Gauss limitedLinearV 1` — bounded 2nd order, robust for steady-state LDC at Re=100. `Gauss linear` (unbounded 2nd order) is acceptable alternative but marginally noisier.
  - Laplacian: `Gauss linear corrected`.
  - Interpolation: `linear`.
  - snGrad: `corrected`.

### fvSolution for simpleFoam
- **Claude's Discretion**:
  - `SIMPLE { nNonOrthogonalCorrectors 0; consistent yes; pRefCell 0; pRefValue 0; }`.
  - Solvers: p → GAMG (multigrid, fast for Poisson); U → smoothSolver GaussSeidel.
  - Under-relaxation: p 0.3, U 0.7 (standard SIMPLE starting point).
  - residualControl: p 1e-5, U 1e-5 (target for convergence).

### controlDict
- **Claude's Discretion**:
  - `application simpleFoam`.
  - `startTime 0; endTime 2000;` (2000 SIMPLE iterations max — convergence typically <1000 for LDC Re=100).
  - `deltaT 1` (simpleFoam is pseudo-transient; deltaT is iteration count, not physical time).
  - `writeInterval 2000` (only write final — no intermediate snapshots needed for audit).

### 0/U and 0/p boundary conditions
- **LOCKED (carry forward)**: existing BCs are correct.
  - lid: `fixedValue (1 0 0)` for U, `zeroGradient` for p.
  - Other 4 walls (wall1-4): `noSlip` for U, `zeroGradient` for p.
  - **REMOVE** the `wall5`+`wall6` empty-face BCs used by icoFoam if they exist (simpleFoam with 2D pseudo-3D needs z-faces as `empty` patch type in blockMeshDict, not `wall`).

### blockMeshDict patch changes
- **MANDATORY**: the current `wall4 faces ((4 5 6 7))` is a z-face at z=0.1m declared as `wall` — with simpleFoam in 2D pseudo-3D this must be `empty` patch type OR we keep it `wall` and add matching BC in 0/U. Pick whichever matches the existing `lid_driven_cavity` reference_pass teaching fixture's expectations for z-face treatment.
- **CORRECT PATTERN**: create a single `empty`-type patch `frontAndBack` covering both z=0 and z=0.1 faces, and remove `wall3` (z=0 front) and `wall4` (z=0.1 back) from the current setup. This is standard OpenFOAM 2D pseudo-3D.

### Post-processing / sampleDict
- **LOCKED (carry forward)**: existing gold-anchored `points` sampler at physical (0.5, y, 0.0) is unchanged. The `_extract_ldc_centerline` function already reconciles normalized-vs-physical y via `yr / 0.1` and uses `x_target = 0.05`. Don't touch it.

### Codex review
- **MANDATORY**: per RETRO-V61-001, `src/` edit >5 LOC triggers Codex baseline. This phase WILL edit >5 LOC (entire controlDict + fvSchemes + fvSolution + blockMesh cell count — est. 80-120 LOC total). Codex pre-merge review required if self-estimated pass rate ≤70%; otherwise post-merge acceptable.

### Claude's Discretion
- Exact LOC count of the `_generate_lid_driven_cavity` rewrite.
- Whether to split the generator into a helper (`_render_simple_fvsolution`, `_render_simple_fvschemes`) or keep it inline — inline is fine for single-case scope.
- Whether to commit the failing fixture before the passing fixture (for CI traceability) or just overwrite — just overwrite is acceptable.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Ghia 1982 reference physics
- `knowledge/gold_standards/lid_driven_cavity.yaml` — the 17 y-points + u values the audit fixture is compared against. READ-ONLY (三禁区 #3).

### Phase 5a infrastructure (do not modify)
- `ui/backend/schemas/validation.py::RunCategory` — `audit_real_run` literal is already registered (Phase 5a).
- `ui/backend/services/validation_report.py::_load_run_measurement` — audit fixture loader used by the signed-bundle route.
- `ui/backend/routes/audit_package.py::build_audit_package` — the HMAC-signing endpoint. Expects `run_id="audit_real_run"` to load the fixture.
- `scripts/phase5_audit_run.py` — the driver script. Writes `fixtures/runs/{case_id}/audit_real_run_measurement.yaml`.

### Case generator (THIS phase edits)
- `src/foam_agent_adapter.py::_generate_lid_driven_cavity` — lines ~640-960 (controlDict, fvSchemes, fvSolution, 0/U, 0/p, sampleDict emission). Subject to this phase's rewrite.
- `src/foam_agent_adapter.py::_render_block_mesh_dict` — lines ~6463-6542 (blockMesh emitter). Subject to cell-count and z-face patch-type changes.
- `src/foam_agent_adapter.py::_is_lid_driven_cavity_case` + `_extract_ldc_centerline` — lines ~7178-7427. DO NOT modify — these handle dispatch and profile extraction correctly.

### Audit fixture schema contract
- `ui/backend/tests/test_phase5_byte_repro.py` — schema contract the new fixture must satisfy. MANDATORY keys: run_metadata.run_id=="audit_real_run", category=="audit_real_run", measurement.{value,unit,run_id,commit_sha,measured_at,quantity,extraction_source,solver_success,comparator_passed}.

### Project governance
- `.planning/retrospectives/2026-04-21_v61_counter16_retrospective.md` — RETRO-V61-001 (governance doc defining risky-PR Codex baseline).
- `.planning/decisions/2026-04-21_phase6_td028_q4_bfs_closure.md` — DEC-V61-028 (Phase 5a completion marker).
- `CLAUDE.md` — project-specific instructions for src/ edits and Codex triggers.

### OpenFOAM v10 tutorials (external reference; do not copy verbatim, adapt)
- `/opt/openfoam10/tutorials/incompressible/simpleFoam/` — reference cases. `pitzDaily` is the most commonly-cited simpleFoam tutorial; closest to our use case is `simpleFoam/pitzDaily` but NOT identical (different geometry). No direct LDC tutorial ships with OpenFOAM v10; pattern-match from pitzDaily for fvSchemes/fvSolution structure.

</canonical_refs>

<specifics>
## Specific Ideas

### simpleFoam controlDict target
```
application     simpleFoam;
startFrom       startTime;
startTime       0;
stopAt          endTime;
endTime         2000;
deltaT          1;
writeControl    timeStep;
writeInterval   2000;
purgeWrite      0;
writeFormat     ascii;
writePrecision  6;
writeCompression off;
timeFormat      general;
timePrecision   6;
runTimeModifiable true;
```

### simpleFoam fvSchemes target
```
ddtSchemes      { default steadyState; }
gradSchemes     { default Gauss linear; }
divSchemes      {
    default             none;
    div(phi,U)          bounded Gauss limitedLinearV 1;
    div((nuEff*dev2(T(grad(U))))) Gauss linear;
}
laplacianSchemes { default Gauss linear corrected; }
interpolationSchemes { default linear; }
snGradSchemes   { default corrected; }
wallDist        { method meshWave; }
```

### simpleFoam fvSolution target
```
solvers {
    p {
        solver          GAMG;
        tolerance       1e-06;
        relTol          0.1;
        smoother        GaussSeidel;
    }
    U {
        solver          smoothSolver;
        smoother        GaussSeidel;
        tolerance       1e-05;
        relTol          0.1;
        nSweeps         1;
    }
}
SIMPLE {
    nNonOrthogonalCorrectors 0;
    consistent      yes;
    pRefCell        0;
    pRefValue       0;
    residualControl {
        p    1e-5;
        U    1e-5;
    }
}
relaxationFactors {
    equations { U 0.9; }
    fields    { p 0.3; }
}
```

### blockMeshDict target (frontAndBack empty patch)
```
convertToMeters 0.1;
vertices ( (0 0 0) (1 0 0) (1 1 0) (0 1 0) (0 0 0.1) (1 0 0.1) (1 1 0.1) (0 1 0.1) );
blocks ( hex (0 1 2 3 4 5 6 7) (129 129 1) simpleGrading (1 1 1) );
edges ();
boundary (
    lid { type wall; faces ((3 7 6 2)); }
    fixedWalls { type wall; faces ((0 4 7 3) (1 2 6 5) (0 1 5 4)); }
    frontAndBack { type empty; faces ((0 3 2 1) (4 5 6 7)); }
);
mergePatchPairs ();
```

(Note: consolidating wall1/wall2/wall3 into a single `fixedWalls` patch is a simplification — the adapter currently keeps 4 separate wall patches. Either is acceptable; consolidation reduces BC boilerplate in 0/U and 0/p. **Prefer keeping 4 separate** to minimize delta against the teaching-fixture baseline.)
</specifics>

<deferred>
## Deferred Ideas

- Solver-swap generalization across other cases (BFS uses simpleFoam already but with k-epsilon; impinging_jet needs different approach). Each case gets its own sub-phase.
- Adaptive mesh refinement / mesh quality metrics. Not needed at 129×129 uniform.
- Residual plotting in the UI from the real-solver run. Phase 5a has stub; real wiring is Phase 5c-f territory.
- Automated byte-reproducibility by actually re-running the solver (currently only schema is enforced). Requires CI runner with Docker + OpenFOAM; defer to Phase 5j.
</deferred>

---

*Phase: 05b-ldc-simplefoam*
*Context gathered: 2026-04-21 via direct user input in auto mode*
