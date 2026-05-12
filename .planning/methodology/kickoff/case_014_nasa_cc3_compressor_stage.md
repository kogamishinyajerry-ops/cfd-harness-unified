# Case 014 · NASA CC3 Compressor Stage · Sub-Session Kickoff

> Paste between `=== BEGIN ===` and `=== END ===` into a fresh
> Claude Code session. Designed by Codex (gpt-5.4 high, CRS,
> 148k tok single-round emit). Validated 2026-05-08 — see
> `case_014_validation.md`. PASS.
>
> **Phase 2 #2 of industrial-extension batch** — gold-standard
> turbomachinery case. Combines case_004 MRF + case_005
> compressible-RANS + case_013 confined-volute lessons into
> NASA CC3 centrifugal compressor stage.
>
> **A2 advisor LANDED 2026-05-08 (commit `a09ae0a`) BUT scope-narrow
> per V25**: D1 (tip-clearance gap +0.30 mm) verification is
> algorithm-runs-cleanly evidence; A2-v2 sub-DEC pending
> (`patches/draft_a2_v2_gap_detection_2026-05-08.md`).
>
> **D8 thin_wall_advisor LANDED + [VALIDATED 6-of-6]** — case_014
> is **8th cross-topology arc data point** (after expected case_010
> 6-of-6 confirmation + case_011 7th + case_014 8th).

=== BEGIN ===

You are a Claude Code sub-session under cfd-harness-unified
orchestration. Task: **case_014_nasa_cc3_compressor_stage**.

**Phase 2 #2** — gold-standard turbomachinery validation.
Establishes turbomachinery industry credibility (gas turbine /
turbocharger / refrigeration / aero engine boost stage).

## Project context
cfd-harness-unified at `/Users/Zhuanz/Desktop/cfd-harness-unified/`.

14 prior cases including case_011-013 industrial-extension
batch dispatched 2026-05-08.

## Required reading
1. `.planning/decisions/2026-05-07_v61_198_apu_bay_strategic_pivot.md`
2. `.planning/strategic/case_011_020_industrial_extension_roadmap_2026-05-08.md`
3. `.planning/strategic/case_013_020_dispatch_plan_2026-05-08.md`
4. `.planning/case_proposal_queue.md`
5. **`.planning/methodology/kickoff/case_004_codex_response.md`** —
   MRF infrastructure inheritance
6. **`.planning/methodology/kickoff/case_005_codex_response.md`** —
   compressible-RANS BC patterns inheritance
7. **`.planning/methodology/kickoff/case_006_codex_response.md`** —
   NASA Tier-1 HTTP 500 caching pattern
8. **`.planning/methodology/kickoff/case_013_codex_response.md`** —
   confined-volute MRF (immediate predecessor)
9. `.planning/methodology/industrial_case_solver_findings.md`
   (V22-V32 inheritance from MRF + compressible cases)
10. `.planning/methodology/knowledge_status_convention.md`
11. `.planning/methodology/kickoff/case_014_codex_response.md`
12. `.planning/methodology/kickoff/case_014_validation.md`

## Hard guardrails
1. V130 advisory-only · V132 no AI-mutating routes
2. No date/calendar gating; OpenFOAM is truth source
3. Use main-project advisors:
   - `from ui.backend.services.geometry_ingest.thin_wall_advisor
     import detect_thin_wall_patches_at_risk` (D8 8th data point)
   - `from ui.backend.services.geometry_ingest.virtual_interface_detector
     import detect_virtual_interfaces, InterfaceSpec` (D1 with
     [QUESTIONABLE] marker)
4. Do NOT redesign — execute Codex brief; revision round-cap=3
5. **Single-region rhoSimpleFoam + MRF cellZone + periodic** —
   NOT chtMultiRegion, NOT full 360° model
6. **No new defects outside D1-D10**
7. **No Ahmed/NACA/Sajben** (Lane B; not relevant)
8. Do NOT add `isSame()` fast-path (V2 lesson)

## Case identifier
`case_014_nasa_cc3_compressor_stage` · solver-class
**rhoSimpleFoam+MRF steady (v1 design point) /
characteristic curve (v2)** · numerics-class
**compressible-RANS-MRF** (NEW root — first true turbomachinery)

## Codex brief summary
- Component: NASA CC3 centrifugal compressor stage (Tier-1 NASA
  archive bake-into-script per case_006 lessons)
- Reference: NASA/TM-2013-216566 / AIAA 2013-3631
- Geometry:
  - 15 main blades + 15 splitter blades
  - R_TE (impeller exit radius) = 215.5 mm
  - Inlet blade height = 64 mm
  - Exit blade height = 17 mm
  - Tip clearance baseline = 0.30 mm (mean approximation; published
    chord-wise 0.1524/0.6096/0.2032 mm)
  - Vaned diffuser
  - One passage modeled (12° wedge equivalent for 30-blade-effective)
  - Periodic boundaries (cyclicAMI)
- Operating point:
  - N (corrected speed) = 21,789 rpm
  - ṁ_design (corrected) = 4.54 kg/s
  - U_tip = 492 m/s
  - PR_design = 4.0
  - T0_inlet = 293.15 K, P0_inlet = 101.325 kPa
- Working fluid: air ideal gas + Sutherland viscosity
- Turbulence model: k-ω-SST (industry standard for turbomachinery)
- Solver v1: rhoSimpleFoam + MRF design point only
- Solver v2: characteristic curve (5-7 operating points spanning
  choke / design / surge boundaries)
- Defects:
  - **D1**: tip-clearance gap on ONE blade enlarged from 0.30
    nominal to 0.60 mm (+0.30 mm)
  - **D8**: thin LE on ONE blade, 0.70 mm thickness (within 0.6-
    0.8 mm spec)
- Effort: 14-18h (longest in batch), ~3 versions

## Codex CAD script (deliverable 2)
Save at `scripts/build_cad.py`. 271 LOC, deterministic. CadQuery
parametric one-passage model + cyclicAMI patches.

```bash
cd ~/Desktop/case_014_nasa_cc3_compressor_stage
python3 -m venv .venv
.venv/bin/pip install cadquery numpy pyyaml jinja2 trimesh
python scripts/build_cad.py --out inputs/cad_codex_v1.step
```

## Periodic + MRF setup (case_014 main work)

### `00_check_region.py`
Verify STEP has 1 fluid region + cyclicAMI periodic patches.

### `02_blockmesh_shm.py`
blockMesh + sHM with refinement near blade LE/TE, blade tips,
diffuser leading edge. Verify `cyclicAMI` periodic patches mate
correctly.

### `03_write_MRFProperties.py`
```
mrf_zone
{
    cellZone mrf_zone;
    active true;
    nonRotatingPatches (vaneless_space diffuser_vane_0
                       diffuser_vane_0_tip outlet_collector
                       periodic_lower periodic_upper);
    origin (0 0 0);
    axis (0 0 1);
    omega 2281.6;  // 21,789 rpm = 2281.6 rad/s
}
```

### `04_write_thermophysical.py`
Air ideal gas + Sutherland:
- thermoType: hePsiThermo / pureMixture / sensibleEnthalpy /
  janaf / specie / Sutherland
- T0_ref = 273.15 K, μ_ref = 1.716e-5, S = 110.4

### `05_write_BCs.py`
- `inlet_plenum`: `totalPressure 101325 Pa` + `totalTemperature
  293.15 K` (T0_inlet, P0_inlet per CC3 spec)
- `outlet_collector`: v1 = `pressureOutlet` at design back-pressure
  (PR=4.0 → outlet ≈ 405 kPa); v2 = swept for characteristic curve
- `impeller_*` patches (hub, shroud, blade_main_*,
  blade_main_*_tip, blade_splitter_*, blade_splitter_*_tip):
  rotating wall in MRF zone
- diffuser_vane_*, vaneless_space, outlet_collector: stationary
  noSlip
- `periodic_lower` / `periodic_upper`: `cyclicAMI` with
  rotational transform (12° wedge angle)

### `06_write_fvSchemes.py`
Steady compressible turbomachinery:
- ddt: `steadyState`
- divSchemes: `Gauss linearUpwind grad(U)`,
  `Gauss limitedLinear 1` for k, ω, e
- gradSchemes: `Gauss linear`
- laplacianSchemes: `Gauss linear corrected`

### `07_write_fvSolution.py`
- p: GAMG with rtol 1e-5
- U / k / ω / e: smoothSolver / GaussSeidel; rtol 1e-6
- relaxationFactors: U=0.7, p=0.3, e=0.95, k=0.7, ω=0.7

### `08_run_solver_v1.sh`
Design point (PR=4.0 target):
```bash
rhoSimpleFoam 2>&1 | tee log.solver_design
```

### `09_compute_PR_eta_v1.py`
PR = (p0_outlet) / (p0_inlet)
η_isentropic = ((PR^((γ-1)/γ) - 1) / (T0_outlet/T0_inlet - 1))
ṁ_corrected = ṁ × √(T0_inlet/T_ref) / (P0_inlet/P_ref)

### `10_run_solver_v2_characteristic.sh`
Sweep p_outlet from choke (low p_outlet, high ṁ) to surge
(high p_outlet, low ṁ): 5-7 points.

### `11_compute_characteristic_curve.py`
- PR(ṁ) at 5-7 points
- η(ṁ) curve
- Surge margin = (ṁ_design - ṁ_surge) / ṁ_design
- Choke ṁ = lowest p_outlet stable point

## Defect verification

### D1 (tip-clearance 0.30→0.60 mm on one blade) — A2 advisor LANDED with caveat

> [QUESTIONABLE 2026-05-08]: A2 v1 cannot field-validate
> 0.30 mm gap-difference per V25 placeholder semantics.

**Step 1**: FreeCAD distToShape between blade_main_<i>_tip
and impeller_shroud at multiple angular positions.

**Step 2**: A2 advisor exercise (expected matched=True, 11th
cross-topology PASS).

### D8 (thin LE 0.70 mm on one blade) — thin_wall_advisor LANDED [VALIDATED 6-of-6]

> case_014 = 8th cross-topology arc data point (after expected
> case_010 6-of-6 + case_011 7th).

**Step 1**: FreeCAD bbox-min on blade_main_<i> LE region;
expected 0.70 mm.

**Step 2**: thin_wall_advisor exercise (expected critical
warning at 0.70 mm < min_cells_per_thickness threshold).

## Six per-case standard moves

1. Reference profile at `case_profiles/case_014_nasa_cc3_compressor_stage.md`
2. V-series append: cyclicAMI face-matching tolerance, total-
   total reference state ambiguity, surge-back-pressure ramp
   sensitivity, choke-boundary numerical limit, tip-leakage
   compressible regime grid sensitivity. ALSO: **8th D8
   cross-topology arc**, **11th D1 cross-topology PASS**.
3. Playbook S15+ candidates:
   - "PR off NASA CC3 → check inlet total-state reference"
   - "Surge prediction unstable → reduce p_outlet ramp rate"
   - "Tip-leakage smeared at compressible Mach → refine to ≥ 4
      cells across 0.30 mm baseline gap"
   - "cyclicAMI residual → check periodic face matching tolerance"
4. Stale-assumption fixes: case_004/005 templates may need
   compressor-specific variants. Commit tag pattern.
5. Artifact extraction (4-5 likely):
   - `turbo_characteristic_post_processor.py`
   - `tip_clearance_advisor.py` (specialized vs general A1)
   - `surge_choke_detector.py`
   - `periodic_blade_row_writer.py`
6. RAG corpus: 5 artifacts per `rag_corpus_format.md`

## Sandbox structure
```
~/Desktop/case_014_nasa_cc3_compressor_stage/
├── README.md, Makefile, .venv/
├── inputs/, templates/, scripts/, case/, evidence/
```

## Sediment + commit convention
Same as cases 011-013. `confidence: <high|med|low>` trailer.

## Boundaries
- CAN: end-to-end run, sandbox modify, sediment commits, <250 LOC
  artifact extraction (4-5 likely), advisor-bias fixes
- CANNOT: redesign case, modify other cases, open new DEC arcs,
  full-360° model, k-ε without rationale, multi-region promotion

## Known issues
1. **A2 [QUESTIONABLE]** — D1 algorithm-runs-cleanly NOT field-
   validation
2. **8th D8 cross-topology** — turbomachinery topology data
   point; if consistent with previous 6-of-6, V10/V23 status
   firms further
3. **First true industrial turbomachinery** — periodic blade-row
   + cyclicAMI infrastructure NEW
4. **Tip-leakage compressible regime** — case_013 was incompressible;
   case_014 transonic relative Mach at blade LE may need
   compressible-specific gap mesh resolution
5. **NASA CC3 reference URL** — bake-into-script per case_006
   strategy (HTTP 500 transient possible)

## Strategic role within batch

After case_014 lands, the project demonstrates:
- compressible-RANS + MRF compose into industrial turbomachinery
  (combines case_004 + case_005 + case_013 lessons)
- Periodic blade-row + cyclicAMI infrastructure ready for future
  axial turbomachinery cases
- D1 + D8 sub-mm verification on transonic compressor blade LE
- 8th D8 cross-topology arc data point + 11th D1 cross-topology
  algorithm-PASS
- New industry-recognizable post-processors: PR(ṁ), η(ṁ), surge
  margin, choke ṁ — turbomachinery business credibility

This **closes Phase 2** (cases 013 + 014). Phase 2 close
unblocks Phase 3 (cases 015 LES+CHT + 016 cavity-DES-acoustic).

=== END ===

## Main session post-dispatch checklist
- [ ] Move case_014 to Dispatched
- [ ] Update case_index.md
- [ ] Update INDEX.md
- [ ] When sub-session reports D1 A2: 11th cross-topology PASS
- [ ] When sub-session reports D8: 8th [VALIDATED] arc data point
- [ ] When sub-session extracts turbo post-processors: evaluate
      promotion to main-project shared services
- [ ] After case_014 sediment + case_013 sediment: trigger Phase 2
      close
