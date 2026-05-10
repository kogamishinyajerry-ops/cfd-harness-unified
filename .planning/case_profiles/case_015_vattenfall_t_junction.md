# Case 015 · Vattenfall T-Junction Thermal Striping · chtMultiRegionFoam LES (WALE)

> **Phase 3 #1** — first compound numerics root (LES + CHT). Combines
> case_002b CHT inheritance + case_010 LES inheritance into the
> Vattenfall OECD/NEA T-junction benchmark.
>
> **Numerics class**: `incompressible-LES-CHT` (NEW root). Sibling pattern
> in coverage map: case_002b (`steady-CHT`) + case_010 (`incompressible-
> external-LES`). This case demonstrates that LES and CHT compose into
> a single coherent numerics root rather than two adjacent ones.

## What this entry is

This case extends the OECD/NEA Vattenfall T-junction benchmark with a
**wall-modeled LES** treatment (WALE subgrid + nutUSpaldingWallFunction)
coupled to a **multi-region conjugate heat transfer** treatment of the
6 mm SS304 pipe wall. The branch (hot) flow at 36°C / 6.0 kg/s mixes
into the main (cold) flow at 19°C / 9.0 kg/s, producing wall-temperature
striping downstream. Statistics target: mean and RMS T' at 10
thermocouple stations Tx10..Tx100, plus FFT spectrum at one station for
fatigue-spectrum analysis.

The case **also exercises** A2 (`virtual_interface_detector`) on a
pipe-pipe weld topology — the 12th cross-topology algorithm-runs PASS
in the V25 chain — with the 60 µm weld misalignment as defect D5.

## Pointer

| field | value |
|---|---|
| Case path | `~/Desktop/case_015_vattenfall_t_junction/` |
| README | `~/Desktop/case_015_vattenfall_t_junction/README.md` |
| Scripts | `~/Desktop/case_015_vattenfall_t_junction/scripts/00..10` + `build_cad.py` + `a2_falsification_d5.py` |
| OF case | `~/Desktop/case_015_vattenfall_t_junction/case/` |
| Solver | `chtMultiRegionFoam` (transient, ESI OpenFOAM v2312) |
| Turbulence | LES + WALE (cubeRootVol delta) |
| Wall treatment | wall-modeled, nutUSpaldingWallFunction, y+ target 30-100 |

## Codex brief

- Designed by Codex (gpt-5.4 high, CRS, 160k tok single-round emit)
- Validated PASS 2026-05-08 (`case_015_validation.md`)
- Brief at `.planning/methodology/kickoff/case_015_codex_response.md`
- Round count: R1 only · cap=3

## Geometry (verbatim from Codex Deliverable 2)

| field | value |
|---|---|
| main pipe ID / OD | 140 / 152 mm |
| branch pipe ID / OD | 100 / 112 mm |
| wall thickness | 6 mm SS304 |
| upstream length | 1000 mm |
| downstream length | 2000 mm |
| branch length | 470 mm |
| weld misalignment (D5) | 60 µm in +x at branch-to-main toe |
| 10 thermocouple pads | Tx10..Tx100 every 200 mm starting at x=200 mm |

Generated via `scripts/build_cad.py` (CadQuery; verbatim from Codex
Deliverable 2). Output: `inputs/cad_codex_v1.step` (378 040 bytes,
sha256 `cd31e9423598e6cc4ddc95a9e7a89e182c33bd91c76a2d13e9c5c1cf4950e6eb`,
13 bodies = 3 regions + 10 probe pads).

## Operating point

| field | value |
|---|---|
| main_inlet (cold) | T = 292.15 K (19 °C), ṁ = 9.0 kg/s, U_bulk ≈ 0.586 m/s |
| branch_inlet (hot) | T = 309.15 K (36 °C), ṁ = 6.0 kg/s, U_bulk ≈ 0.766 m/s |
| main_outlet | inletOutlet on U, prghPressure 0 on p |
| Conjugate fluid↔solid | `compressible::turbulentTemperatureCoupledBaffleMixed` |
| Outer wall | adiabatic zeroGradient T |
| Water (both fluids) | ρ = 998 kg/m³, μ = 1.0e-3, cp = 4180, Pr = 7.0 |
| SS304 | ρ = 7900, cp = 500, k = 15 W/m·K |

## LES configuration

| field | value |
|---|---|
| simulationType | LES |
| LESModel | WALE |
| delta | cubeRootVol (deltaCoeff 1) |
| ddt | backward |
| div(phi,U) | linearUpwindV grad(U) |
| dt | 1e-4 s (CFL ≤ 1) |
| y+ target | 30-100 (wall-modeled, NOT wall-resolved DNS) |
| settling | min 5 flow-throughs (≈ 25 s physical) |
| statistics | min 10 flow-throughs after settling for FFT |

## Per-stage wall time (reference)

Measured 2026-05-10 on macOS Apple Silicon, Docker
`opencfd/openfoam-default:2312`:

| Stage | Script | Wall time | Output |
|---|---|---|---|
| 1 | `build_cad.py` | < 5 s | inputs/cad_codex_v1.step (378 KB) |
| 2 | `00_check_regions.py` | < 5 s | 13 bodies confirmed |
| 3 | `01_extract_surfaces.py` | < 10 s | 13 STL files in case/constant/triSurface/ |
| 4 | `02_scaffold_case.py` | < 5 s | 40 case files (system + constant + 0.orig) |
| 5 | `05_run_mesh.sh STAGE=bg` | < 10 s | blockMesh: 43 524 cells |
| 6 | `05_run_mesh.sh STAGE=features` | < 30 s | extendedFeatureEdgeMesh × 3 |
| 7 | `05_run_mesh.sh STAGE=snappy` | ~5-15 min | sHM final mesh (target: 1-3M cells with 2 prism layers) |
| 8 | `05_run_mesh.sh STAGE=split` | ~30 s | per-region polyMesh × 3 |
| 9 | `09_run_solver.sh STAGE=potential` | ~1 min | potentialFoam init per fluid region |
| 10 | `09_run_solver.sh STAGE=solver` | **N flow-throughs × ~5 s each → ≥ 75 s phys = HOURS-DAYS wall** | chtMultiRegionFoam transient; production statistics out of single-session scope |
| 11 | `10_compute_wall_T_statistics.py` | < 30 s | wall-T mean + RMS + FFT JSON |

> **Single-session honesty**: full LES + CHT at production statistics
> (≥ 15 flow-throughs with dt = 1e-4 on a 1-3M cell mesh) is **hours to
> days** of wall-clock compute. This sub-session delivers the full
> scaffold + mesh + solver-runs-cleanly proof-of-concept; long-time
> statistics are explicitly out of scope per the boundaries clause
> ("CANNOT exceed 15h"). Post-processor reports
> `[QUESTIONABLE 2026-05-10]` if duration < 5 flow-throughs.

## Hand-coded vs reused

**Hand-coded** in case-local scripts (V-series source material):
- LES + chtMultiRegion fvSchemes pairing
  (`02_scaffold_case.py::emit_fvSchemes_LES`)
- Multi-region conjugate baffle coupling for two fluid + one solid region
  (`emit_T_fluid` / `emit_T_solid`)
- top-level controlDict with per-region function objects (probes +
  fieldAverage targeting region_main_fluid only)
- wall-T striping post-processor (`10_compute_wall_T_statistics.py`)
- A2 weld-toe planar-slab approximation
  (`a2_falsification_d5.py::build_main_outer_wall_at_toe` /
   `build_branch_outer_wall_at_toe`)

**Reused from main project** via `PYTHONPATH`:
- `ui/backend/services/geometry_ingest/virtual_interface_detector` (A2 v1)

**Reused from prior sandboxes via convention**:
- 011 `scripts/05_run_mesh.sh` Docker wrapper pattern (+ STAGE env var)
- 011 `_lib.py` path conventions
- 002b `regionProperties` ordering convention (fluid before solid)

**Likely main-project extractions when next LES + CHT case starts**:
- `wall_temperature_striping_post_processor.py`
  (mean + RMS T' + FFT spectrum at thermocouple-array probes)
- LES + CHT joint controlDict template family (top-level function
  objects per fluid region)
- `T_spectrum_extractor.py` (FFT-only, isolatable)

These are **NOT extracted yet** (per DEC-V61-198: artifacts are
extracted only when the next industrial case in the same class is
being set up — premature extraction is wasted leverage). Promotion
candidate review goes in the case_016 (compressible-DES = 006 + 010,
second compound numerics root) kickoff.

## V-series findings sourced from this case

| ID | Symptom | Root cause | Status |
|---|---|---|---|
| V47 | snappyHexMesh `minMedialAxisAngle` vs `minMedianAxisAngle` typo silently breaks layer addition (chtMR LES/CHT first-encounter) | Layer addition was skipped in case_011 steady CHT (no wall prism layers needed for laminar low-Re HX); case_015 is first chtMR variant requiring wall-prism resolution for LES y+ targeting | **partial** (case_015 first appearance · high-confidence fix) |
| V48 | chtMR top-level controlDict function objects require explicit `region` keyword for cross-region targeting | chtMR dispatches FOs per-region; without explicit region, FO registers in alphabetically-first dispatched region | **partial** (case_015 first appearance) |
| V49 | Wall-modeled LES at conjugate fluid-solid baffle requires the `compressible::` triplet on nut + alphat + k for energy-equation coupling | chtMR uses heRhoThermo internally even for liquid water; non-compressible wall-function on alphat produces silent 10-30% wall heat-flux error | **partial** (case_015 first appearance) |
| V50 | A2 advisor `_run_shared` cross-topology PASS on pipe-pipe weld-toe — **12th** cross-topology algorithm-runs PASS in V25 chain | Same placeholder semantic as V19/V21/V25 — algorithm runs cleanly but does not field-validate the 60 µm offset as a defect | **partial · still [QUESTIONABLE]** |

V47/V48/V49 statuses: **partial** (one-case appearance). All three
require a second LES+CHT case (e.g. case_016 compressible-DES if it
shares the function-object dispatch + wall-function compatibility
pattern) to upgrade to **confirmed** per
`knowledge_status_convention.md`. V50 inherits the still-open V25
[QUESTIONABLE] status — only A2-v2 land + injection test resolves it.

## Defect catalog

| ID | Defect | Topology | Advisor | Verification | Status |
|---|---|---|---|---|---|
| D5 | 60 µm pipe-pipe weld misalignment at T-junction toe | cylindrical adjacency, planar-slab approx | A2 v1 (`virtual_interface_detector`) | `python scripts/a2_falsification_d5.py` → `evidence/v1/a2_d5.json` | **[QUESTIONABLE 2026-05-08]** — algorithm-runs-cleanly PASS only; A2-v2 sub-DEC pending for true field-validation |

## Solver-class capability axis

Case_015 fills the **incompressible-LES-CHT** root in the project's
coverage map (per the strategic memo's 4×N coverage matrix): first
**compound numerics root** combining LES (case_010) + CHT (case_002b)
into a single coherent solver-class. Sibling planned root: case_016
(compressible-DES = case_006 + case_010, second compound).

## Strategic role

After case_015 + case_016 land, project demonstrates:
- LES and CHT compose into a single numerics root (validates the
  numerics-class-combination methodology)
- T-spectrum + RMS T' post-processors enable thermal-fatigue analysis
  (nuclear primary loop, steam plant industry KPIs)
- 12th cross-topology A2 algorithm-PASS (still [QUESTIONABLE] per V25)

Phase 3 closes after case_016 (second compound root) lands.
