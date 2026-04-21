# Phase 5b: LDC simpleFoam migration — Research

**Produced:** 2026-04-21
**Source:** Direct investigation during Phase 5b auto-mode attempt (reverted) + OpenFOAM v10 docs + CFD best-practice literature

## RESEARCH COMPLETE

## Prior Phase 5b attempt (reverted) — findings

### What was tried
1. Kept icoFoam, bumped mesh 20×20 → 129×129. Result: Courant = 6.45 (unstable).
2. Added deltaT 0.005 → 0.0005 + endTime 10 → 3 to restore Courant ≈ 0.65. Result: stable but wrong physics.

### What was found
Real solver output at 129×129 icoFoam after 3s (=30 characteristic times at L/U = 0.1s):

| y_norm | solver u | Ghia u | delta |
|--------|----------|--------|-------|
| 0.0625 | -0.0166 | -0.0372 | 55% off |
| 0.500 | -0.0674 | +0.0253 | WRONG SIGN |
| 0.750 | -0.0979 | +0.333 | WRONG SIGN |
| 1.000 | +0.9356 | +1.0 | near-lid extrapolation |

Profile is monotonically decreasing from lid (~+1.0) down to minimum at y=0.69 (u=-0.1), with no sign flip above the vortex core. That's what a **transient LDC looks like before the primary vortex forms** — not a converged steady state. 30 characteristic times is insufficient for Re=100 icoFoam to reach Ghia's asymptote.

### Root cause
icoFoam is a transient PISO solver. Each timestep advances the solution by `deltaT` wall-clock seconds. Natural damping at Re=100 is slow; published LDC benchmarks simulating to steady state via transient solvers often need 50-100+ characteristic times. At deltaT=0.0005, that's 100000+ timesteps — multi-hour wall time. Not a viable iteration loop.

### Conclusion
**Solver swap is mandatory.** simpleFoam (steady-state SIMPLE) converges to the steady state in <2000 pseudo-iterations; on 129×129 this is typically <1 minute wall time. All subsequent Phase 5b sub-phases that use internal incompressible flow will benefit from the same pattern.

## simpleFoam architecture

### How simpleFoam differs from icoFoam
| Aspect | icoFoam | simpleFoam |
|---|---|---|
| Formulation | Transient Navier-Stokes, ∂u/∂t + u·∇u = -∇p/ρ + ν∇²u | Steady Navier-Stokes, drop ∂u/∂t |
| Coupling | PISO (Pressure Implicit with Splitting of Operators) | SIMPLE (Semi-Implicit Method for Pressure-Linked Equations) |
| Time dimension | Physical seconds | Pseudo-iterations (deltaT=1 convention) |
| Stability constraint | CFL < 1 (physical timestep) | Under-relaxation factors (URF) |
| Convergence | Converges *in time*; stop at steady state | Converges *in iterations*; stop at residualControl |
| fvSchemes::ddtSchemes | `Euler` or `backward` | `steadyState` |

### SIMPLE algorithm inner loop
1. Solve momentum equation with guessed p* → get u*.
2. Compute p' correction from continuity deficit.
3. Correct u and p: u = u* + u'(p'), p = p* + α_p · p'.
4. Apply under-relaxation: U = α_U · U_new + (1-α_U) · U_old.
5. Repeat until max(R_p, R_U) < residualControl tolerance OR iteration count exhausted.

### `consistent yes` option
The SIMPLEC variant (SIMPLE Consistent) — uses a modified p' equation that allows α_p ≈ α_U (no need for aggressive p under-relaxation). Typically ~30% faster convergence. Enable for LDC.

## fvSchemes rationale

### ddtSchemes: `steadyState`
Eliminates the time derivative entirely. Non-negotiable for simpleFoam.

### gradSchemes: `Gauss linear`
Standard cell-center to cell-face gradient. Linear interpolation is 2nd-order on orthogonal meshes. LDC mesh is uniform orthogonal → `corrected` not needed for gradient.

### divSchemes: `bounded Gauss limitedLinearV 1` for div(phi,U)
- `bounded` prefix: ensures steady-state convergence (subtracts a continuity-enforced term). Essential for simpleFoam; unbounded central differencing on steady problems oscillates.
- `limitedLinearV 1`: Sweby-family flux limiter, 2nd-order accurate, bounded between 1st-order upwind (limit→0) and central (limit→1). The `V` variant limits by velocity magnitude (more aggressive, better for recirculating flows like LDC).
- Alternative: `bounded Gauss linearUpwind default` — slightly more diffusive but very robust. Use if limitedLinearV produces oscillations near the lid-wall corners.

### divSchemes: `Gauss linear` for div((nuEff*dev2(T(grad(U)))))
Standard laminar/turbulent deviatoric stress term. Unbounded is fine here because it's in the diffusion family, not advection.

### laplacianSchemes: `Gauss linear corrected`
`corrected` is the non-orthogonal correction. On uniform 129×129 mesh, non-orthogonality is 0 → `corrected` is a no-op but harmless. Keep it for generality.

## fvSolution rationale

### p solver: GAMG
GAMG (Generalized Algebraic Multigrid) is typically 3-10× faster than PCG for the pressure Poisson equation on structured meshes. Essential for SIMPLE convergence within reasonable wall time.

### U solver: smoothSolver + GaussSeidel
GaussSeidel is the standard cheap smoother for momentum. 1 sweep per iteration is usual.

### Under-relaxation factors
- Starting point for Re=100 LDC: α_U = 0.9, α_p = 0.3.
- If SIMPLEC enabled (`consistent yes`): α_p can be bumped to 0.7-0.9.
- If divergence observed: reduce α_U to 0.7, α_p to 0.2, retry.

### residualControl
- Target: p 1e-5, U 1e-5.
- Ghia 1982's 5% tolerance on u_centerline maps to roughly residual ~1e-3 → 1e-5 is 2 orders of magnitude stricter, good safety margin.
- If it doesn't converge to 1e-5 within 2000 iterations, relax to 1e-4 as contingency.

## 2D pseudo-3D boundary conditions

OpenFOAM is always 3D internally. To get a 2D solve on a pseudo-3D mesh (thin slab in z), declare the front and back z-faces as `empty` patch type. This tells OpenFOAM to not compute fluxes through those faces.

### Current code state
The existing generator declares `wall4 faces ((4 5 6 7))` as a z-face but types it `wall`. This is wrong for steady 2D — with `wall` type and `noSlip` BC, the flow gets spurious viscous damping through the z-direction.

### Two viable fixes
1. **Consolidate**: remove wall4, keep wall3 (other z-face), consolidate both z-faces into one `frontAndBack` patch of type `empty`. Standard OpenFOAM pattern.
2. **Retain names, retype**: keep both wall3 and wall4 patch names but change patch type to `empty` in blockMeshDict AND change the corresponding BC in 0/U + 0/p to `empty` type.

### Recommendation
Option 1 is cleaner but changes patch names (minor API surface delta). Option 2 preserves patch names at cost of stranger BC structure. **Pick Option 1** — the teaching fixtures don't reference z-face names, and consolidation is the standard pattern any reviewer will expect.

## Post-processing sampling

The existing `_emit_gold_anchored_points_sampledict` call with `physical_points = [(0.5, y, 0.0) for y in y_values]` writes normalized y-coords into physical-coord slots. On a convertToMeters=0.1 mesh, physical y=1.0 m is 10× the domain height (0.1m). This IS a bug, but it's a bug that the fallback extractor `_extract_ldc_centerline` bypasses by re-sampling cell centers + normalizing via `yr / 0.1`.

**Decision**: leave the sampleDict as-is (the fallback path is what actually feeds the comparator). Don't "fix" it in this phase — that's a separate investigation with risk of breaking other cases.

## Expected wall time and iteration count

| Metric | Value | Source |
|---|---|---|
| Cells (129×129) | 16641 2D + 1 z layer | direct |
| SIMPLE iterations to converge at Re=100 | ~500-800 | published simpleFoam benchmarks |
| Wall time per SIMPLE iteration on cfd-openfoam arm64 | ~50-100 ms | Phase 5a observed baseline |
| Total expected wall time | ~30-90 seconds | derived |
| Phase 5a icoFoam 20×20 baseline | 8 seconds | reports/phase5_audit/*_raw.json |

## Risks and mitigations

### R1: simpleFoam diverges (residuals blow up)
- Mitigation: start with conservative URFs (α_U=0.7, α_p=0.2), pilot-run, then tighten.
- Fallback: if still diverges, fall back to `bounded Gauss linearUpwind` for divSchemes.

### R2: Converges to wrong attractor (alternate stable solution)
- For Re=100 LDC, no known multiple steady states — single symmetric primary vortex is unique.
- Mitigation: seed with `internalField uniform (0 0 0)` and let SIMPLE converge from rest. Matches Ghia's initial condition.

### R3: Ghia tolerance still missed at 129×129
- Possible if simpleFoam converged solution has residual ~1e-5 but physical accuracy limited by 2nd-order spatial discretization + uniform mesh.
- Mitigation: run once, measure deviation. If <5% on all 17 points, PASS. If close (5-10%), tighten schemes to 4th-order or use limitedLinearV with limit=1.5. If far (>20%), indicates a deeper bug — escalate.

### R4: Regression on existing teaching fixtures
- `ui/backend/tests/fixtures/runs/lid_driven_cavity/reference_pass_measurement.yaml` has hand-curated u_centerline values matching Ghia's shape — these stay unchanged.
- `mesh_20/40/80/160` grid_convergence fixtures were synthesized in Phase 5a Phase 3 — they are NOT tied to actual solver output. They stay unchanged.
- `real_incident` fixture from §5d Part-2 — ties to commit b8be73a measurement; stays unchanged.
- `under_resolved` + `wrong_model` — hand-curated teaching fixtures; stay unchanged.
- ONLY `audit_real_run_measurement.yaml` changes (this is the Phase 5a file). Byte-repro test (`test_phase5_byte_repro.py`) checks schema, not exact values, so it's unaffected by numeric deltas.

### R5: Wall time blowup
- If SIMPLE doesn't converge within 2000 iterations, audit run takes >5 min per attempt. Iteration loop gets slow.
- Mitigation: set endTime=500 for initial pilot; if converges, bump to 2000 for final. Early feedback on whether SIMPLE is stable.

## Validation Architecture

The existing real-solver pipeline already has sufficient validation infrastructure. No new test files needed beyond what Phase 5a shipped:

### Dimension 1: pytest schema coverage (existing)
- `test_phase5_byte_repro.py` — 12 parametrized tests enforce audit fixture schema contract.
- `test_audit_package_route.py` — 20 tests including `TestAuditRealRunWiring` class covering the LDC-specific route.

### Dimension 2: solver end-to-end coverage (existing driver)
- `scripts/phase5_audit_run.py lid_driven_cavity` — runs FoamAgentExecutor → writes audit fixture → returns PASS/FAIL.

### Dimension 3: HMAC-signed bundle coverage (existing route)
- `POST /api/cases/lid_driven_cavity/runs/audit_real_run/audit-package/build` returns manifest with `measurement.comparator_verdict == "PASS"` when fixture passes.

### Dimension 4: Byte-repro schema enforcement
- Already covered by `test_phase5_byte_repro.py`. No new test needed.

### Dimension 5: No regression on teaching fixtures
- Full backend pytest run must still show 79/79.

### Dimension 6: Frontend tsc clean
- `cd ui/frontend && npx tsc --noEmit` must exit 0. No frontend changes expected from this phase, so this is just a no-regression check.

### Dimension 7: Codex governance (post-edit)
- Any `src/foam_agent_adapter.py` diff >5 LOC triggers Codex review. This phase WILL trigger it (est. 80-120 LOC diff on controlDict + fvSchemes + fvSolution + blockMesh).

### Dimension 8: Numerical verification (new measurement)
- The 5 previously-deviating y-points must all be within ±5% of Ghia values:
  - y=0.0625: target ±0.00186 of -0.03717
  - y=0.1250: target ±0.00210 of -0.04192
  - y=0.5000: target ±0.00126 of +0.02526
  - y=0.7500: target ±0.01665 of +0.33304
  - y=1.0000: target ±0.05000 of +1.00000
- PASS verdict from the audit driver is the canonical binary answer; individual-point analysis is diagnostic only.

---

*Research complete — ready for planning*
