# Case 002b · APU Bay Ventilation · chtMultiRegionSimpleFoam thread (Industrial Reference)

> **NOT a gold-standard case.** No benchmark data, no verdict-pass
> criterion. Industrial reference — proof artifact + V-series source.
>
> **Sibling thread**: `case_002a_apu_bay_buoyant_simple.md` — same
> APU geometry, single-region buoyantSimpleFoam.
>
> Forked from case_002a 2026-05-07 to attempt the v2 plan outlined
> in case_002a's REPORT.md §8.2 (CHT with Ti shells + radiation).
> Runs in parallel sandbox to keep buoyantSimpleFoam optimization
> (case_002a v14+) and CHT exploration independent.

## What this entry is

This case extends case_002a's ventilation problem with **conjugate
heat transfer**: the APU body walls are no longer fixedValue T (a
case_002a v1 simplification) — instead 6 Ti shell regions
(Outer_Surf, Inner_Surf, Plane_Outer_Surf, firewall_front +
firewall_behind, frames + beams aggregated, APU_door) are
extruded as thin solid regions and coupled to the fluid through
`compressible::turbulentTemperatureRadCoupledMixed` BCs.

This unlocks a new **solver-class** in the project's coverage map:
**Conjugate Heat Transfer (CHT)** — the second covered class after
case_002a's "internal flow + buoyancy + forced convection".

## Pointer

| field | value |
|---|---|
| Case path | `~/Desktop/apu-bay-ventilation-cht/` |
| Top-level overview | `~/Desktop/apu-bay-ventilation-cht/docs/decisions_v1.md` |
| v1 report | `~/Desktop/apu-bay-ventilation-cht/reports/report_v1.md` |
| SSOT YAML | `~/Desktop/apu-bay-ventilation-cht/config/case.yaml` |
| Pipeline scripts | `~/Desktop/apu-bay-ventilation-cht/scripts/03..11` (numbered slightly differently from case_002a; multi-region adds 06_5 + 07 + 08 + 09) |
| Templates | `~/Desktop/apu-bay-ventilation-cht/templates/` |
| Solver | `chtMultiRegionSimpleFoam` (ESI OpenFOAM v2312) |

## What's different from case_002a

| Axis | case_002a | case_002b |
|---|---|---|
| Solver | buoyantSimpleFoam | chtMultiRegionSimpleFoam |
| Region count | 1 (fluid) | 7 (1 fluid + 6 Ti solid extrusions) |
| APU body wall T | fixedValue per body (MES data) | retained — kept as boundary heat source on fluid side |
| Skin treatment | zeroGradient T (adiabatic compromise) | full thermal coupling through 2 mm Ti shell regions |
| Radiation | none | viewFactor `ε = 0.7`, far-field `ε = 1` (v1 only; v2 dropped to isolate convergence) |
| Pipeline stages | 11 scripts | 11 scripts + 2.5 (topoSet faceZone) + 3 (extrudeToRegionMesh ×6) |
| Cell count | 943,411 (single region) | 1,272,942 (sum across 7 regions) |
| Status (2026-05-07) | v14 @ iter 813+, healthy | v2 norad @ iter 67+, fluid-side limitTemperature 5%+ clipping |

## v1 → v2 progression (V-series source)

| Version | Key change | Outcome | V-series |
|---|---|---|---|
| v1 | Initial CHT setup with viewFactor radiation `ε=0.7` | Crashed at Time=1; no time directories written; post-processing reported `T = ±1e+300` for solid regions (V-series misinterpretation) | V14 (sentinel misread) |
| v2 norad | Drop radiation, keep multi-region structure | Solver progresses to iter 67+; **fluid-side limitTemperature clamping 3-5% cells per iter** | V15 (V5 pattern crosses solver families) |
| v3 (planned) | Restart radiation from converged v2 IC | TBD | TBD |

This v1 → v2 → v3 layering is the case_002a "v1 simplification then
restore" pattern (laminar → kωSST in case_002a) reapplied: drop
radiation for v2 baseline, restore once flow field is established.

## Per-stage wall time (reference, v2 norad path)

Measured 2026-05-07 on macOS Apple Silicon, Docker
`opencfd/openfoam-default:2312`:

| Stage | Script | Wall time | Output |
|---|---|---|---|
| 3 | `03_validate_inputs.py` | <5 s | input + naming validation |
| 4 | `04_scaffold_case.py` | <5 s | case dir tree |
| 5 | `05_make_fluid_mesh.py` | ~5 min | fluid mesh (sHM, 732k castellated) |
| 6.5 | `06_5_create_facezones.py` | <30 s | topoSet patch → faceZone (9 zones; 6 Frame + beam_3 lost per V10) |
| 7 | `07_extrude_solid_regions.py` | ~2 min | 6 thin solid regions extruded (2 mm × 2 layers) |
| 8 | `08_make_region_dicts.py` | <10 s | thermo + 0/ + system/ + regionProperties for 7 regions |
| 9 (v1) | `09_run_view_factors.py` | ~3 min | viewFactor matrix (14 MB, 7204 coarse faces) — **dropped in v2** |
| 10 | `10_run_solver.py` | ongoing (200+ iter target) | chtMultiRegionSimpleFoam |
| 11 | `11_post.py` | <30 s | per-region T plots |

## Hand-coded vs reused (sediment candidates for main project)

**Hand-coded** in case-local scripts (V-series source material):
- topoSet patch → faceZone workflow (`06_5_create_facezones.py`)
- extrudeToRegionMesh wrapper for thin-shell solid regions
- per-region 0/ + thermophysicalProperties Jinja2 templates (Ti
  material schema)
- region-pair coupled BC writer
  (`compressible::turbulentTemperatureRadCoupledMixed`)
- multi-region solver-launch script
- viewFactor radiation pre-processor wiring

**Reused from main project** via `PYTHONPATH`:
- (same 5 utility modules as case_002a — geometry_ingest,
  case_scaffold, case_bc/writer, mesh_quality, audit_package)

**Likely main-project extractions when next CHT case starts**:
- Multi-region case scaffold (extends `case_scaffold`)
- Region-pair BC writer (extends `case_bc/writer`)
- Solid material library schema (Ti, Al, Cu, steel, ceramics)
- chtMultiRegionFoam solver template family

These are NOT extracted yet (per DEC-V61-198: artifacts are
extracted only when the next industrial case in the same class
is being set up — premature extraction is wasted leverage).

## V-series findings sourced from this case

| ID | Symptom | Root cause | Status |
|---|---|---|---|
| V14 | "T = ±1e+300" reported for solid regions in v1 post-processing | Solver crashed mid-Time=1; no time directories written; sentinel = OpenFOAM default for unread fields. NOT divergence — interpretation bug | **closed** (lesson captured) |
| V15 | v2 norad fluid-side limitTemperature clamping 3-5% cells per iter | V5 (compressible ρ/T runaway) pattern from buoyantSimpleFoam reappears in chtMultiRegionSimpleFoam fluid sub-solver — multi-region wrapping doesn't change fluid-internal numerics | **partial** (mitigated by clamps; root fix = lower URF on h or transient solver) |
| V10 (inherited) | sHM ate 6 Frame patches + beam_3 in level [1,2] | level-1 cell size > Frame thickness | **partial** (case-local accept; main-project advisor pending — see `thin_wall_advisor.py` extraction in this DEC) |

See `industrial_case_solver_findings.md` for full V-series rows.

## Solver-class capability axis

This case fills the **CHT** row in the project's coverage map (per
DEC-V61-198 Pillar 1). Project state advanced from
`{internal+buoyancy}` to `{internal+buoyancy, CHT}` upon V14 + V15
capture (closure not required — partial coverage at "first run
through it" depth counts as covered).

## What this case does NOT yet have

- **Converged steady state**: v2 norad still pseudo-steady at
  iter 67+; matches case_002a v13 pattern. v14-equivalent
  iter-budget extension expected
- **Radiation in converged run**: v1 crashed; v3 planned restart
  from v2 IC
- **Cavity coupling between Inner_Surf ↔ Outer_Surf** (decision A
  in v1: zeroGradient backface; v2 may revisit with effective h /
  R 1D thermal resistance)
- **Frame + beam_3 patches recovered**: blocked by V10; fix lives
  in main project's thin_wall_advisor extraction

## When to update this entry

- **Each new version** (v3, v4, ...): append row to "v1 → v2 → v3
  progression" table + add corresponding V-series entry if a new
  failure mode surfaced
- **When converged**: add §"Converged outcome" with residual
  history + per-region T_min/T_max final-frame
- **When sibling case_002a closes its arc**: cross-reference the
  divergence point ("at v15 case_002a converged; case_002b
  remained pseudo-steady") for narrative coherence

## References

- DEC-V61-198 — APU bay strategic pivot (parent decision)
- `case_002a_apu_bay_buoyant_simple.md` — sibling thread
- `industrial_case_solver_findings.md` — V-series (V14, V15 sourced
  here)
- `solver_convergence_playbook.md` — decision tree (S11 sourced
  here)
- `case_index.md` — multi-case tracker
