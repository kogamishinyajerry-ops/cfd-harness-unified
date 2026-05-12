# Case 012 · HVAC Ceiling Supply Diffuser · buoyantSimpleFoam (Industrial Reference)

> **NOT a gold-standard case.** Tier-3 parametric commercial-office HVAC
> topology with ASHRAE 55 / IEA Annex 20 design-table predictions as
> band reference. This is the **first buoyantSimpleFoam re-deployment
> outside APU bay** — same numerics root (case_002a · Pattern 6
> compressible-buoyant-RANS), different industrial topology.
>
> Established 2026-05-09 as Phase 1 #2 of the industrial-extension
> batch (case_011-020). Closes Phase 1 alongside case_011.
>
> **Sibling threads**: case_002a (APU bay buoyantSimpleFoam — direct
> inheritance source), case_011 (plate-fin compact HX — Phase 1 #1).

## What this entry is

Phase 1 #2 industrial-extension case. **No NEW numerics root** — Codex
brief explicitly stated buoyantSimpleFoam single-region inheritance
from case_002a; expected V3-V13 + S1-S13 already covered. Engineering
question is the topological transfer to a commercial-office HVAC room
served by a 4-way ceiling diffuser.

## What this entry is for

1. **Pattern 6 evidence**: numerics-class inheritance (compressible-
   buoyant-RANS) extending from APU confined-bay buoyant to commercial-
   office room buoyant. Demonstrates that the same solver + thermophysics
   + URF chain works across two topology classes once geometry-side
   surgery (single fluid region; no multi-region) is preserved.
2. **D7 advisor-gap surfacer**: first project D7 (face-orientation
   defect) injection. No LANDED advisor for face-normal defects. Surfaces
   as A4 advisor candidate for post-case_012 retro.
3. **9th D1 cross-topology PASS for A2 _run_shared**: 0.35 mm gap between
   diffuser_face_plate and ceiling. PASS confirms `_run_shared` runs
   cleanly across one more topology; per V25 placeholder semantics, does
   NOT field-validate gap distance. Apply [QUESTIONABLE 2026-05-08]
   marker until A2-v2 sub-DEC lands.
4. **HVAC engineering KPIs**: ADPI / throw-distance T_50 / dumping-
   criterion dT/dz are HVAC-industry-recognizable post-processors.
   Extracted as artifact candidates for main-project workbench.

## Pointer

| field | value |
|---|---|
| Sandbox path | `~/Desktop/case_012_hvac_supply_diffuser/` |
| README | `~/Desktop/case_012_hvac_supply_diffuser/README.md` |
| Final REPORT | `~/Desktop/case_012_hvac_supply_diffuser/evidence/v1/REPORT.md` |
| SSOT YAML | `~/Desktop/case_012_hvac_supply_diffuser/config/case.yaml` |
| CAD generator | `scripts/build_cad.py` (Codex 248-LOC, deterministic) |
| Pipeline scripts | `scripts/00..05_*` |
| Solver runner | `scripts/03_run_solver.sh` |

## Engineering brief (from Codex case_012_codex_response.md)

| field | value |
|---|---|
| Component | 4-way ceiling diffuser commercial office (B_HVAC_DIFFUSER_01) |
| Room | 6.0 m × 4.5 m × 3.0 m |
| Supply | T = 289.15 K (16 °C), U = 2.6 m/s, slot 10 mm |
| Return | low-side-wall (pressureOutlet) |
| Heat sources | 4 occupants × 75 W + equipment 200 W = 500 W total |
| Predicted ADPI | ≈ 85 % (target ≥ 80 %) |
| Solver v1 | buoyantSimpleFoam steady, single fluid region, laminar |
| Defects | D1 (0.35 mm slot gap) + D7 (louver_vane_2 rotated 38°) |
| Effort | 8-10 h, ~3 versions |

## Defects

| ID | Description | Verification | Status |
|----|-------------|-------------|--------|
| D1 | 0.35 mm gap diffuser_face_plate ↔ ceiling | `freecadcmd scripts/check_gap.py` (env-var args) | PASS — measured 0.350 mm |
| D7 | louver_vane_2 rotated 38° from intended | `freecadcmd scripts/check_face_normal.py` (env-var args) | PASS — measured 38.000° |

## v1 run results (2026-05-09)

| Metric | v1 result | Target | Verdict |
|--------|-----------|--------|---------|
| Mesh cells (sHM after V52 fix) | 1.16 M | — | OK |
| Solver iterations completed | 133 / 200 (stopped early) | — | partial pseudo-steady |
| ADPI (27-point ASHRAE 55) | **0.0 %** | ≥ 80 % | **FAIL (V53 sealed-room)** |
| occupied-zone U_max | 4.05 m/s | < 0.25 m/s | FAIL (V53) |
| Throw distance T_50 | **0.0 m** (no jet) | ≈ 2.7 m | FAIL (V53) |
| occZone vol-mean T | 295.03 K (21.9 °C) | — | room ≈ isothermal |
| occZone max T | 309.32 K (36.2 °C) | — | local heat-source heating |
| Max dT/dz (occupied zone) | 0.045 K/m | < 2.0 K/m | PASS (incidentally) |

Interpretation: V53 sealed-room signal — buoyancy + sHM-discretized
0.35 mm D1 gap (~6 mm effective opening) drive whole-room circulation
with no forced supply jet. ADPI = 0 % because room is nearly
isothermal (no temperature input from absent supply BC).

## A2 advisor exercise (9th cross-topology PASS)

```
A2_RESULT: patch=diffuser__ceiling_interface matched=True body_owner=ceiling
           bbox_overlap=1.0000 area_diff=0.0000 normal_dot=1.0000
           diagnostic="shared face on 'ceiling' (area=2.7e+07)"
[QUESTIONABLE 2026-05-08] PASS=algorithm-runs-cleanly, NOT field-validation
of 0.35 mm gap. A2-v2 sub-DEC pending (V25).
```

This is the 9th cross-topology PASS (003 + 004 + 005 v1/v2 + 006 + 007 +
008 + 009 + 010 + 012). Strong evidence for `_run_shared` algorithmic
robustness across topology classes (APU bay → CRM-HLS → NREL Phase VI →
RAE M2129 S-duct → ONERA M6 transonic → KCS ship → GLC305 IRT airfoil →
Sandia Flame D combustor → DrivAer fastback → HVAC room).

**Per V25 caveat**: ALL 9 PASSes confirm `_run_shared` finds candidate
faces; NONE field-validate the engineer's gap-distance question. A2-v2
sub-DEC adds `inter_face_gap_mm` field; until it lands, do NOT claim
field-validation.

## Hand-coded vs reused from main project

**Hand-coded in case-local scripts**:
- `scripts/build_cad.py` — Codex 248-LOC parametric CadQuery
  (deterministic via STEP timestamp canonicalization)
- `scripts/01_extract_stl.py` — FreeCAD STEP → per-body STL with mm→m scaling
- `scripts/02_setup_case.py` — single-script consolidated dict writer
  (blockMesh + sHM + thermophys + g + turbulence + 0.orig + topoSet);
  v1 simplification; v2 candidate to split per Codex brief
- `scripts/03_run_solver.sh` — Docker `opencfd/openfoam-default:2312`
  invocation with S4 potentialFoam warm start
- `scripts/04_setup_postprocess.py` — sampleDict for ADPI 27-grid +
  jet centerline + floor stratification probes
- `scripts/05_postprocess.py` — ADPI / throw / dumping computation

**Reused from main project** via PYTHONPATH:
- `ui.backend.services.geometry_ingest.virtual_interface_detector`
  (A2 advisor; LANDED 2026-05-08, V25 [QUESTIONABLE] caveat)

## v1 design decisions

- **Compressible perfectGas + Sutherland** (NOT strict Boussinesq EoS):
  brief specifies "Boussinesq buoyancy regime" (Ra ~ 1e9-1e10 mixed
  convection physics), but buoyantSimpleFoam compressible perfectGas
  naturally handles ρ(T) variation and is well-tested via case_002a.
  Strict Boussinesq EoS would require buoyantBoussinesqSimpleFoam (a
  different solver). This is a defensible v1 simplification.
  v2 candidate: re-run with buoyantBoussinesqSimpleFoam.
- **Laminar v1** (NOT kωSST): APU bay convention per S1
  (`kOmegaSST + zero IC → ω blowup → wall function NaN`). v2 candidate:
  restart kωSST from converged v1 IC.
- **Single-script case writer** (NOT 5 separate scripts per Codex brief):
  v1 tractability simplification. v2 candidate: split into
  03_thermophysical / 04_BCs / 05_fvSchemes / 06_fvSolution.

## What this case does NOT yet have (v1)

- **v1 IS A SEALED-ROOM NATURAL-CONVECTION RUN** (V53). Codex CAD
  generator emitted supply_inlet and return_outlet as 3D solid bodies;
  sHM treated them as walls; no inlet/outlet patches in the mesh.
  Result: only buoyancy-driven recirculation, no forced supply jet.
  v1 ADPI / throw / dumping metrics are reported as natural-convection
  characterization NOT as HVAC-with-supply-jet verdict.
  v1.5 / v2 fix path documented in V53 (createPatch carve OR thin-
  face-geometry CAD emission).
- Verdict against ASHRAE 55 / IEA Annex 20 reference: predicted ADPI
  ≈ 85% but no analytical comparison case; CFD ADPI ± 10 pp band
  CANNOT be evaluated until V53 fix lands.
- kωSST / k-ε turbulence model
- Buoyancy via strict Boussinesq EoS (using compressible perfectGas
  proxy)
- Radiation (negligible at these temperatures, but documented)

## When to update this entry

- Each time a new sandbox version (v2, v3) lands: append to defect /
  KPI tables + V-finding cross-references
- When A2-v2 sub-DEC lands: re-run D1 falsification with field-
  validated gap-distance API; upgrade [QUESTIONABLE] → [VALIDATED]
  if API confirms 0.35 mm
- When A4 face-orientation advisor lands (post-case_012 retro
  candidate): re-run D7 falsification + add cross-topology entry
- When a new industrial case is added in Phase 1: cross-reference here

## References

- DEC-V61-198 — APU bay strategic pivot (parent decision)
- `.planning/methodology/industrial_case_solver_findings.md` — V-series
- `.planning/methodology/solver_convergence_playbook.md` — S1-S21
- `.planning/methodology/knowledge_status_convention.md` — [QUESTIONABLE] grammar
- `.planning/cross_cuts/v_series_2026-05-09_case_012_append.md` — V-series append
- `.planning/methodology/kickoff/case_012_codex_response.md` — Codex deliverables
- `.planning/methodology/kickoff/case_012_validation.md` — kickoff PASS verdict
- `case_002a_apu_bay_buoyant_simple.md` — direct inheritance source
- `case_011_plate_fin_compact_hx.md` — Phase 1 #1 sibling
