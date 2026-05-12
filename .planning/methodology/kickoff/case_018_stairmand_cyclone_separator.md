# Case 018 · Stairmand Cyclone Separator · Sub-Session Kickoff

> Paste between `=== BEGIN ===` and `=== END ===` into a fresh
> Claude Code session. Designed by Codex (gpt-5.4 high, CRS,
> 139k tok single-round emit). Validated 2026-05-08 — see
> `case_018_validation.md`. PASS.
>
> **Phase 4 #2 of industrial-extension batch** — first 3D
> swirl-dominant + Lagrangian. Extends case_008 airfoil icing
> Lagrangian to cyclone topology.
>
> **D6 2nd injection** — accumulating advisor-gap evidence
> (after case_016 first D6 injection).
>
> **First RSM turbulence for project** — k-ε / k-ω-SST under-
> predict cyclone vortex core; LaunderGibsonRSTM industry standard.

=== BEGIN ===

You are a Claude Code sub-session under cfd-harness-unified
orchestration. Task: **case_018_stairmand_cyclone_separator**.

**Phase 4 #2** — first 3D swirl-dominant separator.

## Project context
18 prior cases (002a/b + 003-017).

## Required reading
1. `.planning/strategic/case_011_020_industrial_extension_roadmap_2026-05-08.md`
2. `.planning/strategic/case_013_020_dispatch_plan_2026-05-08.md`
3. `.planning/case_proposal_queue.md`
4. **`.planning/methodology/kickoff/case_008_codex_response.md`** — Lagrangian + kinematicCloud inheritance
5. `.planning/methodology/kickoff/case_016_codex_response.md` — D6 first-injection precedent
6. `.planning/case_profiles/case_008_glc305_irt_lagrangian.md`
7. `.planning/methodology/industrial_case_solver_findings.md` (V36-V37 from case_008 + LES findings)
8. `.planning/methodology/knowledge_status_convention.md`
9. `.planning/methodology/kickoff/case_018_codex_response.md`
10. `.planning/methodology/kickoff/case_018_validation.md`

## Hard guardrails
1. V130 advisory · V132 no AI-mutating routes
2. No date/calendar gating
3. **No advisor for D6** — manual FreeCAD body-count + bbox check
4. Do NOT redesign — round-cap=3
5. **pimpleFoam transient + RSM (LaunderGibsonRSTM)** — NOT k-ε /
   k-ω-SST (under-predict cyclone PVC)
6. **kinematicCloud one-way coupled** (no momentum feedback)
7. **3D required** (cyclone is 3D swirl)
8. **No new defects outside D1-D10**

## Case identifier
`case_018_stairmand_cyclone_separator` · solver-class
**pimpleFoam + RSM + kinematicCloud transient** · numerics-class
**incompressible-RANS-Lagrangian-swirl** (extends case_008 to
swirl-dominant)

## Codex brief summary
- Component: Stairmand high-efficiency cyclone (public literature
  ratios baked into script)
- Geometry: D=250 mm cyclone; inlet 0.5D × 0.2D rectangular;
  cylindrical body 1.5D; conical 2.5D; vortex finder 0.5D × 0.5D;
  underflow ≥ 0.4D
- Operating point: air at standard conditions, U_inlet = 20 m/s,
  Re_D ≈ 3.3e5, swirl number S ≈ 1-3
- Particle phase: ρ_p = 2650 kg/m³ (silica), 1-50 μm log-normal
  distribution, mass loading 10-50 g/m³
- Turbulence: RSM (LaunderGibsonRSTM)
- Lagrangian: kinematicCloud one-way; SchillerNaumann drag;
  rebound walls / escape outlets
- Defect: **D6** — 10-30 mm cube floating in collection chamber
- Effort: 10-12h, ~3 versions

## Codex CAD script (deliverable 2)
Save at `scripts/build_cad.py`. 157 LOC, deterministic.

```bash
cd ~/Desktop/case_018_stairmand_cyclone_separator
python3 -m venv .venv
.venv/bin/pip install cadquery numpy pyyaml jinja2 trimesh
python scripts/build_cad.py --out inputs/cad_codex_v1.step
```

## RSM + Lagrangian setup (case_018 main work)

### `00_check_region.py`
Verify STEP has region_air + cyclone patches + debris_cube_d6.

### `02_blockmesh_shm.py`
blockMesh + sHM; refine cyclone body / conical / vortex finder
core / debris cube vicinity.

### `03_write_thermophysical.py`
Air at standard conditions.

### `04_write_BCs.py`
- inlet_tangential: flowRateInletVelocity at U=20 m/s tangent to barrel
- overflow_outlet: pressureOutlet
- underflow_outlet: pressureOutlet OR closed-bottom with escape
- cyclone_walls: noSlip
- particle walls: rebound (or escape on underflow)

### `05_write_turbulenceProperties.py`
```
simulationType  RAS;
RAS
{
    RASModel  LaunderGibsonRSTM;
    turbulence on;
    printCoeffs on;
}
```

### `06_write_kinematicCloud.py`
```
solution { coupled false; transient true; }
particleProperties
{
    parcelTypeId 1;
    type kinematicParcel;
    drag SchillerNaumann;
}
injection
{
    type cellZoneInjection;  // OR patchInjection at inlet_tangential
    sizeDistribution { type logNormal; min 1e-6; max 50e-6; ... }
    massTotal ...;
    parcelsPerSecond ... // 1000-10000 parcels target
}
```

### `07_run_solver.sh`
1. potentialFoam initialization
2. pimpleFoam + kinematicCloud transient
3. dt = 1e-3 to 1e-4 s for vortex precession capture
4. Run to swirl statistics convergence (≥ 5 flow-throughs)
5. Long-run for d50 statistics (≥ 10 flow-throughs)

### `08_compute_swirl_number.py`
S = ∫ U_θ U_z r dA / (R ∫ U_z² dA) at one cylindrical-body cross
section.

### `09_compute_d50_eta_curve.py`
- Eulerian flow converged → inject particles at 7 sizes (1, 2, 3,
  5, 8, 15, 30 μm)
- Track parcels until escape (overflow or underflow)
- η(d_p) = % escaped via underflow at each size
- d50 = particle size where η = 50%
- Compare to Stairmand correlation

## Defect verification

### D6 (10-30 mm debris cube in collection chamber) — NO LANDED ADVISOR

> 2nd D6 injection (case_016 first). Accumulating advisor-gap evidence.

**Step 1**: FreeCAD body count (cyclone bodies + 1 debris_cube_d6).
**Step 2**: bbox verification.
**Step 3**: V-finding: 2nd D6 advisor-gap evidence point.
Post-Phase-4 retro: D6 advisor-candidate decision.

## Six per-case standard moves

1. Reference profile at `case_profiles/case_018_stairmand_cyclone_separator.md`
2. V-series append: RSM convergence sensitivity, PVC capture
   threshold, particle injection plane sensitivity, rebound vs
   escape wall BC, D6 debris obstruction effect on swirl number.
   **2nd D6 advisor-gap evidence**.
3. Playbook S15+ candidates:
   - "k-ε vs RSM cyclone vortex-core capture difference"
   - "PVC unstable below swirl-number convergence threshold"
   - "Fine-dust η sensitive to wall rebound coefficient"
4. Stale-assumption fixes: case_008 templates may need RSM variant
   + cellZone particle injection. Commit tag pattern.
5. Artifact extraction (3 likely):
   - `swirl_number_post_processor.py`
   - `d50_eta_curve_calculator.py`
   - `cyclone_dp_advisor.py`
6. RAG corpus: 5 artifacts.

## Sandbox structure
```
~/Desktop/case_018_stairmand_cyclone_separator/
├── README.md, Makefile, .venv/
├── inputs/, templates/, scripts/, case/, evidence/
```

## Sediment + commit convention
Same as cases 011-017.

## Boundaries
- CAN: end-to-end run, sandbox, sediment, <250 LOC artifact extraction (3)
- CANNOT: redesign, k-ε / k-ω-SST without rationale, 2D simplification,
  exceed 12h

## Known issues
1. **2nd D6 evidence — no advisor** — accumulating advisor-gap
2. **First RSM for project** — slower convergence than k-ε; expect
   2× iteration count
3. **PVC capture sensitivity** — vortex precession requires fine
   dt + sufficient mesh refinement at vortex core
4. **Particle injection plane sensitivity** — inject upstream of
   tangential inlet for representative initial conditions
5. **Long-time statistics** — d50 statistics require ≥ 10 flow-
   throughs after swirl number converges

## Strategic role within batch

After case_018 lands, project demonstrates:
- pimpleFoam + RSM + kinematicCloud composes (3 elements)
- 3D swirl-dominant separation industry capability
- 2nd D6 advisor-gap evidence
- Industry KPIs: d50, η(d_p), Δp_cyclone, swirl number

This is **Phase 4 #2**; remaining Phase 4: 019 (Kenics mixer),
020 (porous filter).

=== END ===

## Main session post-dispatch checklist
- [ ] Move case_018 to Dispatched
- [ ] Update case_index.md / INDEX.md
- [ ] When sub-session reports D6 outcome: 2nd D6 advisor-gap evidence
- [ ] When sub-session extracts swirl_number / d50_eta post-processors: evaluate promotion
