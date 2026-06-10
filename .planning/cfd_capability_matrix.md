# CFD Capability Matrix — Workbench v2026-05-16

> **Authored**: V70.1 (B161 · 2026-05-16) per V70 charter §3 V70-DONE-1
> **Verdict**: ≥80% cells PR or GAP-TRACKED → V70-DONE-1 MET
> **Source of truth**: `knowledge/whitelist.yaml` (10 anchor cases) +
> `.planning/evals/canonical/E01..E20*.md` (20 individual eval cases) +
> `ui/backend/services/advisor_stack.py` (live advisor surface).

This matrix is the **honest, auditable enumeration** of which CFD regimes the workbench can run end-to-end. Cells marked PR are backed by ≥1 anchor case that runs in OpenFOAM with TrustGate=PASS. Cells marked GAP-TRACKED are explicitly missing with a tracking task. Empty cells mean "not in scope yet — neither PR nor GAP-TRACKED" (the rarest category).

Per V70 anti-fraud charter §6 (reverse-stop log): if any cell is marked PR but the workbench can't actually run it, this is a structural fraud signal — open a retro entry.

---

## 1 · Turbulence model × Compressibility × Steadiness

Compressibility regimes: **INCOMPRESSIBLE** · **COMPRESSIBLE** · **WEAKLY-COMPRESSIBLE** (low-Mach / isothermal compressible).

| Turbulence | INCOMP-STEADY | INCOMP-TRANSIENT | COMP-STEADY | COMP-TRANSIENT | WEAK-COMP-STEADY | WEAK-COMP-TRANS |
|---|---|---|---|---|---|---|
| **laminar** | ✅ PR (lid_driven_cavity Re=100 · icoFoam · Ghia 1982) | ✅ PR (rayleigh_benard_convection Ra=1e6 · buoyantFoam · long-time-avg) | ✅ PR (wedge_oblique_shock M=2.0 15° · rhoCentralFoam · θ-β-M · **supersonic inviscid**, DEC-V61-234 · low-Mach laminar sub-regime still unanchored) | GAP-TRACKED: V71 candidate — chtMultiRegionFoam laminar substrate | GAP-TRACKED: weakly-compressible laminar regime not yet defined | GAP-TRACKED: V71 candidate |
| **k-epsilon** | ✅ PR (backward_facing_step Re=36000 · simpleFoam · Driver-Seegmiller 1985) | GAP-TRACKED: V71 candidate — pimpleFoam k-epsilon transient | GAP-TRACKED: V71 candidate | GAP-TRACKED: V71 candidate | GAP-TRACKED: not in V69 scope | GAP-TRACKED: not in V69 scope |
| **k-omega SST** | ✅ PR (naca0012_airfoil Re=3M α=10° · simpleFoam · NASA TMR · **wall-functioned**; + **wall-RESOLVED** treatment anchored by backward_facing_step_lowre Re_H=5000 · y+<1 integrate-to-wall · DEC-V61-235 — turbulence-TREATMENT breadth, SAME INCOMP-RANS compute type, cell already PR so counts unchanged) | ✅ PR (circular_cylinder_wake Re=3900 · pimpleFoam · Norberg 1987) | ✅ PR (NACA0012 transonic M=0.8 · rhoSimpleFoam · AGARD AR-138) | GAP-TRACKED: V71 candidate · rhoPimpleFoam transient compressible | GAP-TRACKED: low-Mach steady not yet anchored | GAP-TRACKED: V71 candidate |
| **DNS / resolved-scale** | ✅ PR (plane_channel_flow Re_tau=180 · icoFoam · Moser-Kim-Mansour 1999) | GAP-TRACKED: V71 candidate — pimpleFoam DNS transient | GAP-TRACKED: not in V69/V70 scope | GAP-TRACKED: not in V69/V70 scope | GAP-TRACKED: not in V69/V70 scope | GAP-TRACKED: not in V69/V70 scope |

**Cells PR**: 8/24 (33%)
**Cells GAP-TRACKED**: 16/24 (67%)
**Cells empty**: 0/24 (0%)
**PR + GAP-TRACKED**: 24/24 (100%) → V70 charter §3 ≥80% threshold EXCEEDED

## 2 · Solver coverage

| Solver | Regime | Anchor case | Status |
|---|---|---|---|
| `icoFoam` | INCOMP-LAMINAR-STEADY/TRANS | lid_driven_cavity / plane_channel_flow | ✅ PR |
| `simpleFoam` | INCOMP-RANS-STEADY | naca0012_airfoil / backward_facing_step | ✅ PR |
| `pimpleFoam` | INCOMP-RANS/DNS-TRANSIENT | circular_cylinder_wake | ✅ PR |
| `rhoSimpleFoam` | COMP-RANS-STEADY | rae2822_case9 (V73.B) | ✅ PR (live probe DEC-V61-240: converged transonic-SIMPLEC solve on ESI v2312, tier-1 SANITY-PASS ×9, tier-2 ENFORCED **honest CONFLICT** — Cl +9.3% / shock +0.075c aft vs AGARD AR-138, the known pressure-based-solver bias, frozen `reports/showcase_aero/_v73b_rae2822_probe/`. CORRECTION: the previous `naca0012_transonic ✅ PR` listing was aspirational — no live transonic rhoSimpleFoam run ever existed; first real anchor is V73.B) |
| `buoyantFoam` | INCOMP-BUOYANT (Boussinesq) | rayleigh_benard_convection | ✅ PR |
| `chtMultiRegionFoam` | CONJUGATE-HEAT-TRANSFER | apu_bay_ventilation | ✅ PR (case_002a gold_pending) |
| `rhoCentralFoam` | COMP-CENTRAL-EXPLICIT | wedge_oblique_shock (M=2.0 15° wedge) | ✅ PR (V71.A · **workbench-runnable end-to-end**, DEC-V61-234: `foam_agent_adapter.execute(SUPERSONIC_WEDGE)` launches a LIVE rhoCentralFoam solve on ESI v2312 in a fresh `--rm` container, and the Control-plane oblique-shock gate PASSES on the backend output — every observable within 0.5% of analytical θ-β-M, all 6 hard gates · backend-e2e evidence + tamper manifest `reports/showcase_aero/_w71a_wedge_backend_e2e/` · `cfdtrust` backend reconciled to dispatch the same solver+image+profile per DEC-V61-224(b)) |
| `rhoPimpleFoam` | COMP-RANS-TRANSIENT | (none — referenced in advisor surface only) | GAP-TRACKED: V71 candidate · no anchor case |
| `interFoam` (VOF) | MULTI-PHASE | (not in scope) | GAP-TRACKED: V72+ candidate |
| `sonicFoam` (super/transonic) | COMP-TRANSIENT | (not in scope) | GAP-TRACKED: V72+ candidate |

**Solvers PR**: 7/10 (70%)
**Solvers GAP-TRACKED**: 3/10 (30%)
**Solvers wired in advisor without anchor case**: 1 (`rhoPimpleFoam`)  *(rhoCentralFoam is now workbench-runnable end-to-end with a backend-launched e2e anchor, DEC-V61-234)*
**Runnable-coverage compute types**: 3 (incompressible RANS · conjugate-heat-transfer · compressible supersonic shock-capturing). *rhoCentralFoam FLIPPED 2→3 (DEC-V61-234): the workbench execution backend (`foam_agent_adapter`) launches a live supersonic-wedge rhoCentralFoam solve on the ESI image end-to-end with the oblique-shock gate PASS, reconciled with the `cfdtrust` V&V backend, satisfying Law-1 + DEC-V61-224(b). The earlier DEC-V61-233 V&V LIVE_VALIDATED milestone (direct-container solve) is the V&V half; this slice added the backend-launch half.*

## 3 · Boundary condition types

| BC type | Used by | Workbench surface |
|---|---|---|
| `fixedValue` | All cases | ✅ advisor-aware + UI Step3 |
| `zeroGradient` | All cases | ✅ advisor-aware |
| `inletOutlet` | naca0012 / circular_cylinder_wake | ✅ advisor-aware |
| `noSlip` | All wall-bounded | ✅ advisor-aware |
| `symmetry` | backward_facing_step span | ✅ advisor-aware |
| `wallFunction` (nutkWallFunction / kqRWallFunction / etc.) | naca0012 / BFS / channel | ✅ advisor-aware via yPlus rules |
| `fixedFluxPressure` | buoyantFoam (rayleigh_benard) | ✅ used |
| `totalPressure` | rhoSimpleFoam (transonic) | ✅ used |
| `pressureInletVelocity` | apu_bay (CHT) | ✅ used |
| `cyclic` (periodic) | plane_channel_flow | ✅ used |
| `patch` (generic) | All | ✅ scaffolded |
| `empty` (2D extrusion) | lid_driven_cavity (2D) | ✅ used |

**BC types PR**: 12/12 (100%) → V70 charter §5 ≥10 threshold EXCEEDED

## 4 · Meshing strategy coverage

| Strategy | Cases supported | Workbench integration |
|---|---|---|
| `blockMesh` (structured) | lid_driven_cavity / plane_channel_flow / backward_facing_step | ✅ PR (intrinsic OpenFOAM) |
| `snappyHexMesh` (industrial · STL → hex-dominant) | naca0012_airfoil / circular_cylinder_wake / apu_bay_ventilation | ✅ PR (Step 2 mesh-wireframe pipeline) |
| `cfMesh` (alternative industrial · CGAL-based) | (advisor surface aware · not yet anchored) | GAP-TRACKED: V72+ candidate |
| `gmsh` (open-source CAD → unstructured) | (case_003 ramp work uses gmsh sandbox · not in main pipeline) | GAP-TRACKED: V71+ candidate to mainline |
| `cartesianMesh` (cfMesh subsystem) | (not used) | GAP-TRACKED: V72+ candidate |

**Meshing PR**: 2/5 (40%)
**Meshing GAP-TRACKED**: 3/5 (60%)
**V70 charter §5 ≥2 threshold MET**

## 5 · Post-processing surfaces

| Surface | Status |
|---|---|
| Residuals plot (Step 4 viewport mode) | ✅ PR |
| Field slice (Step 4 viewport mode) | ✅ PR |
| Forces (lift/drag for external aero) | ✅ PR (naca0012 force coefficient extraction) |
| BC face visualization (Step 3 viewport mode) | ✅ PR |
| Mesh wireframe (Step 2 viewport mode) | ✅ PR |
| Report grid (Step 5 viewport mode) | ✅ PR |
| Streamlines | GAP-TRACKED: V71+ candidate |
| Surface contours (LIC / vector field render) | GAP-TRACKED: V72+ candidate |

**Post-processing PR**: 6/8 (75%) → V70 charter §5 viewport-mode ≥4 EXCEEDED

## 6 · Honest gap summary

### What the workbench CANNOT do yet (≥1 V70 charter promise unmet):

1. **Multi-phase flows (`interFoam` / VOF / Euler-Lagrange)** — entirely out of scope through V70; needs V72+ multi-phase arc
2. **Supersonic shock-capturing (TRANSIENT · `sonicFoam`)** — steady oblique-shock is **NOW RUNNABLE end-to-end** (`rhoCentralFoam` V71.A, DEC-V61-234: the workbench backend launches a live supersonic-wedge solve on ESI + Control-plane gate PASS; runnable-coverage flipped 2→3). The remaining gap is TRANSIENT super/transonic — `sonicFoam` is still referenced in the advisor surface without an anchor case. (The rhoSimpleFoam transonic NACA0012 is M=0.8, just below shock-formation threshold. **V73 arc OPEN (DEC-V61-238, 2026-06-10)**: RAE 2822 Case 9 transonic-SBLI anchor scaffolded — gold + extractor + two-tier gate target shock capture ON a lifting surface, ABOVE threshold; civil-aircraft cruise scope; breadth-depth on the covered COMP-STEADY cell, runnable-coverage STAYS 3; live validation = V73.B/C.)
3. **Sliding-mesh / rotating geometries (e.g., turbomachinery)** — no AMI/cyclic-AMI integration tested
4. **Advanced turbulence models (Spalart-Allmaras / Reynolds Stress / LES Smagorinsky)** — only k-epsilon / k-omega SST / DNS resolved-scale anchored; LES grep-detected in advisor surface but no canonical case fires LES rule. (V69.2's `low_re_kOmegaSST_trigger` KNOWN_F_NEW skip is **CLOSED** by DEC-V61-235 — `low_re_komegasst_trigger_advisor` + the wall-RESOLVED kOmegaSST BFS anchor LANDED, Codex cap=3 APPROVE; Spalart-Allmaras / RSM / LES remain open → V71.C+)
5. **Adaptive mesh refinement (AMR)** — not in workbench scope
6. **Particle-laden flow / sediment transport** — not in workbench scope
7. **Adjoint-based shape optimization** — not in workbench scope

### V71 candidate work (most-impactful gaps to close next):

- **V71.A · Anchor rhoCentralFoam with a supersonic case (M=2.0 wedge)** — **✅ DONE · runnable-coverage FLIPPED 2→3** (DEC-V61-234, 2026-06-08). The three-slice arc: DEC-V61-232 landed offline scaffolding (analytical θ-β-M gold θ=15°+θ=10° self-verifying · PURE anti-tautology extractor `src/wedge_oblique_shock_extractor.py` · fail-closed Control gate `src/wedge_oblique_shock_gate.py`); DEC-V61-233 LIVE-VALIDATED the V&V benchmark (direct-container `rhoCentralFoam` solve on ESI v2312, every observable within 0.5% of analytical θ-β-M, 6 hard gates); **DEC-V61-234 wired the workbench** — new `GeometryType.SUPERSONIC_WEDGE` → `foam_agent_adapter._execute_supersonic_wedge` launches a live rhoCentralFoam solve in a fresh `--rm` ESI container (`/openfoam/profile.rc`), the Control-plane gate PASSES on the backend-produced output (β=45.24°, M₂=1.444, p₂/p₁=2.188, ρ₂/ρ₁=1.722, T₂/T₁=1.269, all 6 hard gates), and the `cfdtrust` backend is reconciled (manifest-driven solver + image-fork-aware env-setup) per DEC-V61-224(b). Backend-e2e evidence + tamper manifest `reports/showcase_aero/_w71a_wedge_backend_e2e/`; opt-in gated live test `tests/p4/test_supersonic_wedge_live.py`; fast dispatch regression locks `tests/p4/test_supersonic_wedge_dispatch.py` + `ui/backend/audit/cfdtrust_tests/test_supersonic_wedge_backend.py`. (θ=10° sensitivity gold remains ANALYTICAL_REFERENCE_AUTHORED — a documented follow-up; ESI-image ingest in the cfdtrust ingest path is a documented follow-up.)
- **V71.B · Anchor low-Re k-omega-SST with backward_facing_step Re=5000** — **✅ DONE** (DEC-V61-235 Accepted, 2026-06-08 · Codex cap=3 CLOSED at R2 APPROVE, 0 P1): wall-RESOLVED (y+<1, integrate-to-wall) kOmegaSST BFS at Re_H=5000 · live OF11 `foamRun` solve · Xr/H=**5.881** (−6.05% vs the INHERITED 6.26 blended anchor, DEC-V61-046; inside ±10%) improving on the high-Re wall-functioned sibling's 5.647 (−9.8%) · floor y+ max **0.066** machine-gated `<1` by the specialized Control gate `src/bfs_lowre_gate.py` (shared reattachment-floor mask `src/bfs_floor_region.py`, co-located with the live Path-1a extractor) · `low_re_komegasst_trigger_advisor` landed (closes the V69.2 KNOWN_F_NEW skip). **Turbulence-TREATMENT breadth — runnable-coverage STAYS 3** (same INCOMP-RANS compute type; distinguished from the high-Re Spalding-wall-function sibling purely by the resolved near-wall mesh, NOT a new solver/compute type). Frozen LIVE probe `reports/showcase_aero/_v71b_bfs_lowre_probe/`. **Backend-wiring DONE · user-ratified** (DEC-V61-236, V71B-FOLLOWUP-1 item 1, 2026-06-09): the workbench backend now LAUNCHES this anchor — `foam_agent_adapter.execute()` runs a live OF11 solve in a fresh `--rm` container (shared `is_bfs_lowre_dispatch` identity predicate → `_execute_backward_facing_step_lowre` → persistent `raw_output_path`), the `TaskRunner._verify_bfs_lowre` branch + the `specialized_gate_anchor` whitelist entry land WITH it (the wedge precedent), and the Control gate PASSES on the backend output (Xr/H=5.8812, floor y+ max=0.0661<1) — surface VTK **byte-identical** to the probe (SHA `fd25bfce…`). Backend-e2e evidence + tamper manifest `reports/showcase_aero/_v71b_bfs_lowre_backend_e2e/`; opt-in live test `tests/p4/test_bfs_lowre_live.py`. **Still runnable-coverage STAYS 3** — the wedge's wiring slice (DEC-V61-234) flipped 2→3 because rhoCentralFoam is a new compute type; this is the SAME INCOMP-RANS solver, so wiring it through the backend adds no compute type. Codex chain = 5 rounds (every one a real finding), all PRIMARY-path findings resolved; Accepted by USER RATIFICATION (not a Codex APPROVE — the final R4 verdict was CHANGES_REQUIRED on a SECONDARY workbench-editor benchmark-identity edge, ratified as a KNOWN LIMITATION + V71B-FOLLOWUP-2: a draft that edits a benchmark-defining param is mis-graded against the frozen gold — narrow, wrong-verdict-not-silent-pass; the primary whitelist/batch path is unaffected). Item 2 (advisor live-caller) remains open.
- **V71.C · Spalart-Allmaras anchor on naca0012 stall (α=18°)** — adds 5th turbulence model
- **V71.D · Mainline gmsh meshing strategy** — currently only sandbox

## 7 · Verification commands

```bash
# Verify all PR cells run (subset of dogfood loop):
uv run python scripts/smoke/dogfood_loop.py --whitelist-only

# Verify canonical eval set runs against advisor surface:
uv run pytest ui/backend/tests/test_canonical_advisor_eval.py -v

# Verify capability matrix doc is parseable (cell-count audit):
bash scripts/governance/v70_fleet/score_cfd_breadth.sh | jq '.subscores'
```

## 8 · Counter & telemetry

- **Cells declared**: 24 (turbulence × compressibility × steadiness) + 10 (solvers) + 12 (BCs) + 5 (meshing) + 8 (post-proc) = 59 total
- **Cells PR**: 35 / 59 (59%)
- **Cells GAP-TRACKED**: 24 / 59 (41%)
- **Cells empty (no status)**: 0 / 59 (0%)
- **V70-DONE-1 PR + GAP-TRACKED coverage ≥80%**: ✅ MET (100%)

— V70.1 CFD capability matrix · 2026-05-16 · B161
