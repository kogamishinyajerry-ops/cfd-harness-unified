# Case 002 · APU Bay Ventilation (Industrial Reference)

> **NOT a gold-standard case.** No benchmark data, no verdict-pass
> criterion. This is an **industrial reference** — proof artifact and
> V-series finding source.
>
> Established by DEC-V61-198 (APU bay strategic pivot, 2026-05-07) as
> the first non-academic case in the project's case fleet.

## What this entry is

The 10 YAML profiles in this directory describe **gold-standard
academic cases**: each has a benchmark (Ghia 1982 LDC, Thomas 2021
NACA, etc.), a verdict-pass tolerance, and a known-good solution
to compare against.

This entry is different. It points at a real industrial case
(`~/Desktop/apu-bay-ventilation/`) that:

- Has **no analytical / experimental / DNS benchmark** — it's a
  one-off engineering question (does the APU bay ventilate at 55°C
  ambient with prescribed wall temperatures?), not a community
  validation case
- Has **no verdict-pass criterion** — there is nothing to compare
  to other than physical sanity (continuity error, residual
  behavior, qualitative flow direction)
- Is **a live, sometimes-edited engineering sandbox** — not a frozen
  fixture. The pointer below is a path; the case is not copied here

## What this entry is for

Three orthogonal uses:

1. **Proof artifact**: when someone asks "can the workbench do
   industrial CFD today," this is the answer. 943,411 cells,
   `buoyantSimpleFoam`, 13-version solver iteration, 11-script
   pipeline, ~3500 LOC. Ran end-to-end in one development day.

2. **V-series finding source**: the V3-V13 progression in this case
   seeded `industrial_case_solver_findings.md` (V-series). Future
   industrial cases append to V-series; this is where the seed came
   from.

3. **Reference architecture**: the SSOT YAML + Jinja2 + 11-script
   pipeline pattern (`case.yaml` → templates → `case/system/*` etc.)
   is the canonical example of "engineer + Claude Code drives an
   industrial case without N2-N5 UI". Future industrial cases
   should follow the same skeleton (with case-specific naming,
   geometry, BC values).

## Pointer

| field | value |
|---|---|
| Case path | `~/Desktop/apu-bay-ventilation/` |
| Top-level overview | `~/Desktop/apu-bay-ventilation/README.md` |
| Final report | `~/Desktop/apu-bay-ventilation/evidence/v13_post_v5_183632/REPORT.md` |
| SSOT YAML | `~/Desktop/apu-bay-ventilation/config/case.yaml` |
| Solver convergence trail | `REPORT.md §4.3` (V3-V13 table) |
| 11-script pipeline | `~/Desktop/apu-bay-ventilation/scripts/01..11` |
| Templates | `~/Desktop/apu-bay-ventilation/templates/` |

## Per-step wall time (reference)

Measured 2026-05-07 on macOS Apple Silicon, Docker
`opencfd/openfoam-default:2312`:

| Step | Script | Wall time | Output |
|---|---|---|---|
| 1 | `01_cad_clean.py` | ~60 s | per-body STL from CATIA STEP (29 bodies) |
| 1b | `01b_optimize_geom.py` | ~10 s | decimated + axially-stretched STL |
| 2 | `02_domain_subtract.py` | ~30 s | combined STL with farfield + interface faces |
| 3 | `03_validate_stl.py` | <5 s | patch existence + naming check |
| 4 | `04_scaffold_case.py` | <5 s | `case/` directory tree |
| 5 | `05_make_dicts.py` | <5 s | all `system/` + `constant/` + `0.orig/` dicts |
| 6 | `06_run_mesh.sh` | ~5 min | sHM 943k cells |
| 7 | `07_check_mesh.py` | <5 s | quality report + advisor suggestions |
| 8 | `08_write_bcs.py` | <5 s | `0/` BC values (filtered for missing patches) |
| 9 | `09_run_solver.sh` | ~7 min | 100 iter buoyantSimpleFoam (single core) |
| 10 | `10_post.py` | ~30 s | ParaView slices + streamlines |
| 11 | `11_audit.py` | <5 s | signed evidence pack |

Total: **~14 min** wall clock for the full v13 baseline (excluding
solver-version iteration time, which was the dominant cost during
development).

## What was hand-coded vs reused from main project

**Hand-coded in case-local scripts** (the V-series source material):
- CATIA STEP `Import.insert()` name-preserving loader (V1)
- Virtual interface face detector (shared / endcap modes; V2)
- Geometry surgery (decimate-by-tier + axial stretch; V8)
- 11-script pipeline orchestration (Makefile + shell)
- SSOT YAML + Jinja2 templates for all OpenFOAM dicts
- Mass-conservation pre-flight in `05_make_dicts.py` (V12)
- `0.orig/` ↔ `0/` workflow enforcement (V9)
- 13-version solver convergence iteration (V3-V13)

**Reused from main project** via `PYTHONPATH`:
- `ui.backend.services.geometry_ingest.stl_loader` — STL parsing
- `ui.backend.services.geometry_ingest.patch_detector` — patch type
  classification
- `ui.backend.services.case_scaffold` — case directory creation
- `ui.backend.services.case_bc.writer` — BC field rendering
- `ui.backend.services.mesh_quality` — checkMesh log parsing +
  advisor suggestions
- `src.audit_package` — evidence-pack signing

## Mapping to V-series and 5-artifact extraction

The hand-coded portions above map to V-series findings + the
5-artifact extraction in DEC-V61-198:

| Hand-coded item | V-series | Artifact extraction (DEC-V61-198) |
|---|---|---|
| `Import.insert()` STEP loader | V1 | A1 — `cad_ingest_freecad.py` |
| Interface face detector | V2 | A2 — `virtual_interface_detector.py` |
| Geometry surgery | V8 | A3 — `geometry_surgery.py` |
| Mass conservation pre-flight | V12 | A4 — extends `case_bc/writer.py` |
| Solver convergence playbook | V3-V13 | A5 — `solver_convergence_playbook.md` |

Once A1-A5 are landed in main project, future industrial cases will
be able to use these capabilities directly (instead of re-hand-coding
in case-local scripts), reducing per-case overhead.

## What this case does NOT yet have

- **Verdict comparison**: no benchmark, no automated verdict-pass.
  Future industrial cases may have benchmarks (e.g. wind tunnel data
  for an intake diffuser) — those should still be V-series-source,
  not gold-standard, unless they are community-recognized validation
  cases
- **Conjugate heat transfer**: V1 baseline uses `buoyantSimpleFoam`
  with `fixedValue T` on APU body walls (not real solid conduction).
  V2 plan: `chtMultiRegionSimpleFoam` with titanium thermal
  properties — outlined in REPORT.md §8.2
- **Radiation**: 600-870K APU walls + 328K freestream → radiation is
  30-50% of heat transfer. Not modeled in V1
- **Turbulence**: V1 uses laminar (RANS kωSST blew up per V3); V2
  plan to restart kωSST from converged V1 IC

## When to update this entry

- **Each time `~/Desktop/apu-bay-ventilation/` runs a new
  development version** (V14, V15, ...): append to the V3-V13 row
  in REPORT.md and add corresponding V-series entry if a new failure
  mode surfaced
- **When a new industrial case is added** (`case_003_<name>`):
  cross-reference here as a sibling industrial reference
- **When an A1-A5 artifact lands in main project**: update the
  mapping table to note "extracted, see `<path-to-extracted-module>`"

## References

- DEC-V61-198 — APU bay strategic pivot (parent decision)
- `.planning/methodology/industrial_case_solver_findings.md` — V-series
- `.planning/methodology/solver_convergence_playbook.md` — decision tree
- `.planning/methodology/workbench_persona_findings.md` — F-series
  (companion, persona-facing surface)
