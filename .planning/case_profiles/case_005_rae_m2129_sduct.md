# Case 005 · RAE M2129 S-Duct Intake Diffuser · rhoSimpleFoam thread (Industrial Reference)

> **NOT a gold-standard case.** No benchmark data, no verdict-pass
> criterion. **Industrial reference** — proof artifact + V-series finding source.
>
> Established by DEC-V61-198 (APU bay strategic pivot, 2026-05-07)
> as the **first compressible case** in the project's case fleet.
> Fills the **internal compressible diffuser (subsonic-transonic)**
> row of the solver-class coverage map. Per Pattern 6 (V-finding
> inheritance by numerics class), case_005 is the **root for
> compressible-RANS**: inherits NO V3-V13/V15 (compressible-buoyant-RANS),
> NO V-findings from case_003 (incompressible-RANS), NO V-findings
> from case_004 (incompressible-RANS-MRF).
>
> **Companion**: this is a single-thread case (one solver class,
> one CAD source, one numerics root). No sibling threads at v1.

## What this entry is

A real industrial-flavored CFD case with a Tier-1 reference geometry (NASA Glenn `WWW/wind/valid/sduct/sduct02/`, AGARD AR-303/AR-270 RAE M2129) regenerated parametrically by Codex's CAD design (per the case-design protocol at `.planning/methodology/codex_case_design_protocol.md`). The case-thread sandbox at `~/Desktop/case_005_rae_m2129_sduct/` ran v1 end-to-end and surfaced 3 new V-series findings (V16, V17, V18) plus the **first industrial falsification of the LANDED A3 advisor** (`geometry_surgery.decimate_to_tier`).

## What this entry is for

Three orthogonal uses (parallel to case_002a):

1. **Proof artifact**: workbench can drive an industrial compressible-RANS S-duct diffuser through CAD → mesh → solver end-to-end without crashing, on a 52k-cell mesh in 144 s wall clock, hand-coded compressible BC writer + thermo writer + DC60 post-processor (none of which existed in the main project before case_005).

2. **V-series finding source**: V16 (STEP roundtrip fragmentation of `cq.Compound`-of-Faces export), V17 (A3 advisor lacks redundancy/overlay-detection logic — toy-case bias is in scope, not parameter values), V18 (compressible-RANS pseudo-steady mass-flow imbalance under SIMPLE + totalPressure inlet + low-resolution mesh), **V19** (A2 advisor lacks sub-mm gap-as-defect detection — V2-pattern shared-interface only). All four documented in `industrial_case_solver_findings.md`.

3. **A3 advisor first industrial falsification**: PARTIAL verdict (Q1 PASS, Q2 PASS, Q3 FAIL). A3 works as a pure decimator with reasonable tier presets; toy-case bias is in *advisor scope* (no upstream classification step), not in *threshold values*. See `~/Desktop/case_005_rae_m2129_sduct/evidence/v1_a3_falsification.json`.

4. **A2 advisor first industrial falsification (correction)**: kickoff prompt called A2 "pending"; verification against codebase (commit a09ae0a) showed A2 IS LANDED. case_005 v1 then surfaced V19 — A2 has perfect V2-pattern shared-interface detection but no sub-mm gap-as-defect API for D1-class signatures. v1 PARTIAL verdict (Q1 PASS, Q2 EXPECTED_FAIL_BY_DESIGN, Q3 SCOPE_GAP_CONFIRMED). See `~/Desktop/case_005_rae_m2129_sduct/evidence/v1_a2_falsification.json`.

5. **V21 disambiguation (v2 work, 2026-05-08 later)**: case_005 sub-session re-ran A2 D1 via the public API `detect_virtual_interfaces`+`_run_shared` (case_003's invocation path) instead of v1's `faces_match_shared` lower-level helper. Result: matched=True for both spec orderings, symmetric, **consistent with case_003 + case_004**. **V21 hypothesis (a) confirmed**: v1 used the wrong code path. **V22's "curved-geometry-specific" hypothesis refuted**: flange-ring axial-end faces ARE axis-aligned planar (normal·x=±1.0). **New finding V25**: `_run_shared` returns matched=True with HARDCODED PLACEHOLDER result fields (`bbox_overlap_fraction=1.0`, `area_diff_fraction=0.0` are literals on lines 200-201, not measurements) — so the 0.35 mm gap is INVISIBLE in the output. All three cases (003, 004, 005 v2) return the same placeholder output for D1. **V19 superseded by V25**, **V21 closed**. v2 falsification evidence at `~/Desktop/case_005_rae_m2129_sduct/evidence/v2_a2_run_shared.json`. **Implication for case_003 + case_004**: their A2 PASS reports confirm only that `find_face_facing_target` runs cleanly + finds candidate faces; they do NOT field-validate A2 as gap-defect detector, because A2 has no API surface for that signal. Main session re-interpretation recommended.

## Pointer

| field | value |
|---|---|
| Case path | `~/Desktop/case_005_rae_m2129_sduct/` |
| Top-level overview | `~/Desktop/case_005_rae_m2129_sduct/README.md` |
| Final report (v1) | `~/Desktop/case_005_rae_m2129_sduct/evidence/v1_final/REPORT.md` |
| Decision log (v1) | `~/Desktop/case_005_rae_m2129_sduct/docs/decisions_v1.md` |
| SSOT YAML | `~/Desktop/case_005_rae_m2129_sduct/config/case.yaml` |
| Codex deliverables | `.planning/methodology/kickoff/case_005_codex_response.md` (in this repo) |
| Validation report | `.planning/methodology/kickoff/case_005_validation.md` |
| A3 falsification evidence | `~/Desktop/case_005_rae_m2129_sduct/evidence/v1_a3_falsification.json` |
| A2 falsification evidence (v1, lower-level helper) | `~/Desktop/case_005_rae_m2129_sduct/evidence/v1_a2_falsification.json` |
| A2 falsification evidence (v2, public `_run_shared` API; V21 disambiguation) | `~/Desktop/case_005_rae_m2129_sduct/evidence/v2_a2_run_shared.json` |
| Defect verification evidence | `~/Desktop/case_005_rae_m2129_sduct/evidence/v1_defect_verification.json` |
| DC60 + AIP recovery evidence | `~/Desktop/case_005_rae_m2129_sduct/evidence/v1_post/dc60.{json,txt}` |
| 9-script pipeline | `~/Desktop/case_005_rae_m2129_sduct/scripts/{01_extract_stl, 04_scaffold_case, 05_make_dicts, 06_run_mesh, 09_run_solver, 10b_compute_dc60, build_cad, verify_defects, a3_falsification}.{py,sh}` |
| Templates | `~/Desktop/case_005_rae_m2129_sduct/templates/` (Jinja2; first-time compressible thermo + 0/ field set) |

## Per-step wall time (v1 baseline)

Measured 2026-05-08 on macOS Apple Silicon, Docker `opencfd/openfoam-default:2312`:

| Step | Script | Wall time | Output |
|---|---|---|---|
| 0 | `build_cad.py` | ~7 s | `inputs/cad_codex_v1.step` (330 MB; cadquery 2.7.0) |
| 0' | `verify_defects.py` (FreeCAD) | ~30 s STEP import + ~1 s D1/D2 | D1=0.350 mm exact PASS; D2=102,401 fragmented Part::Feature objects (V16) |
| 0'' | `a3_falsification.py` | <1 s (5 tier-decimation runs on 102,400 trimesh faces) | Q1 PASS / Q2 PASS / Q3 FAIL → V17 |
| 0''' | `a2_falsification.py` | <1 s | Q1 PASS / Q2 EXPECTED_FAIL_BY_DESIGN / Q3 SCOPE_GAP_CONFIRMED → V19 |
| 1 | `01_extract_stl.py` | <1 s | `inputs/cleaned_combined.stl` (m units, 15,552 faces, 3 named regions) |
| 4 | `04_scaffold_case.py` | <1 s | `case/{0.orig,constant,system}/` |
| 5 | `05_make_dicts.py` | <1 s | rendered Jinja2 → all OpenFOAM dicts |
| 6 | `06_run_mesh.sh` | ~10 s | blockMesh + sfx + sHM (52,078 cells; 1,688 concave but solver-tolerable) + checkMesh |
| 9 | `09_run_solver.sh` | 144 s | rhoSimpleFoam 0-500 iter |
| 10b | `10b_compute_dc60.py` | ~5 s | AIP slice + DC60 + recovery PR via PyVista |

Total: **~3 min** wall clock for v1 (excluding the 30 s one-time defect-audit FreeCAD STEP import).

### Per-step wall time (v2, 2026-05-08 afternoon)

v2 = minimum-change CFD push: URF.p 0.20→0.10, URF.U 0.50→0.30, iter 500→2000, transport const→sutherland. No mesh / template / script changes (other than `10b_compute_dc60.py` made version-aware via `CASE005_VERSION` env var).

| Step | Script | Wall time | Output |
|---|---|---|---|
| 0' | `a2_falsification_run_shared.py` | <1 s | `evidence/v2_a2_run_shared.json` (V21 disambiguation: matched=True both orderings, V25 surfaced) |
| 5 | `05_make_dicts.py` (re-render with v2 config) | <1 s | dicts updated |
| 9 | `09_run_solver.sh` (rhoSimpleFoam, 2000 iter) | **767 s** (12.8 min) | case/{200..2000}/ |
| 10b | `CASE005_VERSION=v2 .venv/bin/python 10b_compute_dc60.py` | ~5 s | `evidence/v2_post/dc60.{json,txt}` |

Total: **~13 min** wall clock for v2 solver + post (excluding ~1 s for V21 disambiguation script).

### v2 metrics summary (vs v1 vs reference)

| Metric | v1 (iter 500) | v2 (iter 2000) | Reference target | v2 verdict |
|---|---|---|---|---|
| Ux Initial residual @ end | ~0.2-0.5 | **~0.007-0.008** | <1e-3 | **30-70× improvement** |
| AIP Mach (avg) | 0.18 | 0.153 | 0.40-0.60 | DROPPED (URF damping) |
| AIP recovery PR | 0.955 | 0.955 | 0.839 | UNCHANGED |
| DC60 distortion | 0.351 | **0.264** | 0.10-0.20 | IMPROVED, 1.3× target |
| phi_inlet (kg/s) | -1.51 | -1.49 | balanced | UNCHANGED |
| phi_outlet (kg/s) | +4.36 | +4.16 | balanced | UNCHANGED |
| Mass-flow asymmetry | 2.9× | 2.8× | <5% | UNCHANGED |
| Continuity cumulative @ end | 130,957 | 418,924 | low → good | grew, BUT growth rate slower |
| Tmax | 389 K | 484 K | <600 K | warmer (Sutherland) |

**v2 verdict: PSEUDO-STEADY OSCILLATION PERSISTS; V18 REINFORCED**.

URF damping + extended iter + Sutherland made the SOLVER converge cleanly (Ux residual dropped 30-70×) but did NOT fix the inlet/outlet mass imbalance (preserved at 2.8×). The structural cause is the BC chain (totalPressure inlet + fixedValue outlet on coarse mesh), not URF tuning. **S13 sharpened**: path 2 (Fix #2) alone is INSUFFICIENT — must combine with path 1 (potentialFoam) OR path 3 (rhoPimpleFoam) OR mesh refinement.

## What was hand-coded vs reused from main project

**Hand-coded in case-local scripts** (V-series source material, all new for compressible-RANS):
- `01_extract_stl.py` — parametric trimesh STL generator (bypasses V16 STEP-roundtrip pathology and enacts A3 falsification's "DROP overlay" semantic)
- Compressible BC writer via `templates/0/{p,T,U,k,omega,nut,alphat}.j2` (totalPressure inlet, fixedValue/waveTransmissive outlet, compressible::alphatWallFunction, etc.)
- Compressible thermophysicalProperties writer via `templates/constant/thermophysicalProperties.j2` (perfectGas, hConst, const transport with sutherland fallback)
- `10b_compute_dc60.py` — DC60 distortion coefficient computation (AIP polar grid sampling + 60° sector sweep + recovery PR)
- `verify_defects.py` — FreeCAD-based D1/D2 audit (also surfaces V16)
- `a3_falsification.py` — A3 advisor industrial falsification harness
- `06_run_mesh.sh` + `09_run_solver.sh` shell wrappers
- 9-script pipeline orchestration

**Reused from main project** via `PYTHONPATH`:
- `ui.backend.services.geometry_ingest.geometry_surgery` — A3 advisor (exercised by `a3_falsification.py`)

(The main project's existing `geometry_ingest.stl_loader`, `case_scaffold`, `case_bc.writer`, `mesh_quality` modules — used by case_002a/b — were **not** consumed by case_005 because case_005's compressible BC family is outside the schema currently supported by `case_bc.writer`. This is itself a stale-assumption finding; see "Stale-assumption main-session attention" below.)

## Mapping to V-series and artifact extraction

The hand-coded portions above map to V-series findings + likely future artifact extractions:

| Hand-coded item | V-series | Likely extraction (priority) |
|---|---|---|
| Parametric trimesh STL bypass | V16 | low — case-005-specific Codex CAD pattern; main-project fix is upstream Codex case-design protocol revision |
| Compressible 0/p (totalPressure) + 0/T (totalTemperature) + 0/p outlet (fixedValue/waveTransmissive) writer | (no V-finding — preventive; absence is the gap) | **HIGH after case_006 lands** (also compressible) — `compressible_bc_writer.py` artifact |
| Compressible thermophysicalProperties writer (perfectGas + const/sutherland + hConst/janaf) | (no V-finding — preventive) | **HIGH after case_006 lands** — `compressible_thermophysical_writer.py` artifact |
| DC60 + AIP recovery post-processor | (preventive; method is well-known but no main-project utility exists) | **HIGH for M5 milestone** — `dc60_post_processor.py` artifact |
| `verify_defects.py` FreeCAD pattern | V16 (defect-injection-precision) | medium — generalize to a `freecad_defect_verifier.py` once 2-3 cases use the same pattern |
| `a3_falsification.py` harness | V17 (A3 advisor scope gap) | medium — case-thread A3 falsification harness pattern |
| Compressible-RANS pseudo-steady mass-imbalance behavior | V18 | low (V13-class symptom; the playbook entry S13 is the value, not main-project code) |

The main project's existing 5-artifact extraction (A1-A5 from APU bay) is unchanged by case_005 — A2 (`virtual_interface_detector`) extraction priority compounds (now 3-of-3 cases surfacing it: case_003 + case_004 + case_005), but no new A-artifact arc opens here.

## What this case does NOT yet have

- **Converged steady state**: v1 ended at iter 500 with cumulative continuity error 130,957 and 2.9× mass-flow asymmetry between inlet (-1.51 kg/s) and outlet (+4.36 kg/s) patches. V13-pattern pseudo-steady, but a degree more severe than case_002a v13 (which had ~1% continuity error). **v2 update (2026-05-08 afternoon)**: 2000 iter with URF.p=0.10, URF.U=0.30, Sutherland transport — Ux Initial residual converged to 0.007-0.008 (30-70× improvement) but mass-flow asymmetry preserved at 2.8×. **V18 reinforced; S13 sharpened**: BC chain is structurally responsible, not URF tuning. v3 needed for full convergence.
- **AIP Mach within reference target**: v1 produced 0.185 vs the 0.40-0.60 reference target. v2 produced 0.153 (slightly LOWER due to URF damping). Flow has not pressurized through the diffuser to the design point — the BC chain is in transient balance.
- **DC60 in physical range**: v1 produced 0.351 vs typical RAE M2129 reference at PR=0.839 of 0.10-0.20. v2 produced 0.264 — improvement, closer to physical range, but still 1.3× typical. Consistent with the under-pressurized flow.
- **waveTransmissive outlet**: Codex's primary BC plan; v1+v2 used fixedValue p as the documented fallback. v3 should attempt waveTransmissive once flow field is established.
- **Prism layers**: v1+v2 disabled. v3 should add 3-layer prism with expansion 1.2 once the geometry-side concave cells are addressed (1,688 in v1+v2 mesh).
- **`potentialFoam` warm start**: v1+v2 used a non-zero internal U seed (100 m/s) instead. v3 should pre-iterate `potentialFoam -writePhi` to seed a divergence-free U field — REQUIRES temp BC swap (compressible inlet incompatible with potentialFoam directly). S13 path 1.
- **Sutherland transport**: v1 used `transport const`; **v2 switched to sutherland** for variable-T accuracy. Hot-cell Tmax climbed 389→484 K with sutherland (vs const-mu); fvOptions limit 600 K not active.
- **rhoPimpleFoam transient escalation**: Codex's v2 fallback if pseudo-steady oscillation persists past 2000 iter. **v2 confirmed pseudo-steady persists at 2000 iter; rhoPimpleFoam now confirmed v3-priority** (S13 path 3).

## When to update this entry

- **Each time `~/Desktop/case_005_rae_m2129_sduct/` runs a new development version** (v2, v3, ...): append to per-step wall time + V-series rows.
- **When a new compressible-RANS case opens** (case_006 follow-on, case_011-class, ...): cross-reference here as a sibling root or as a same-class consumer of case_005's V-findings.
- **When `compressible_bc_writer.py` / `compressible_thermophysical_writer.py` / `dc60_post_processor.py` artifacts land in main project**: update the "Mapping to V-series and artifact extraction" table to note "extracted, see `<path-to-extracted-module>`".
- **When converged**: add §"Converged outcome" with residual history + AIP final-frame metrics + comparison vs RAE M2129 published reference data.

## Stale-assumption main-session attention

1. **Kickoff narrative drift correction (A2 status)**: kickoff prompt claimed A2 is "still pending" and predicted case_005 would be the 3rd consecutive case to compound evidence for extraction priority. **Codebase reality**: A2 was landed at commit a09ae0a (with follow-up commits 4d2fb26 + 15ae33e closing V2 status to "closed" and backfilling case_003/case_004 kickoffs). case_005 kickoff was NOT backfilled. **Recommendation**: case kickoff prompt generation pipeline should gain a "verify advisor status against current HEAD" pre-flight check so newly-dispatched cases inherit the latest landed-vs-pending state. This is a process finding, not a numerics finding — file under `methodology/kickoff/` revision queue.

2. **Advisor scope-expansion arc (V17 + V25, v2 sharpened from V19)**: BOTH landed advisors A2 and A3 surfaced PARTIAL falsifications in case_005 due to the same SHAPE — scope is too narrow to cover the industrial-defect signature being tested. A3 decimates but does not classify (drop / decimate / preserve / repair). A2 `_run_shared` runs and finds candidate faces but **returns matched=True with hardcoded placeholder result fields that hide the gap-magnitude** — so the engineer cannot distinguish "shared (gap=0)" from "should-have-been-shared-but-isn't (gap=0.35mm)". **Recommended sub-DEC under DEC-V61-198 for an "advisor-scope-expansion" arc** covering both: add `inter_face_gap_mm` field + `should_have_been_shared_with_unintended_gap(detected, max_gap_mm)` classifier to A2; add `classify(mesh, context)` to A3. The 2-of-2 pattern in a single case-thread is enough signal to act now without waiting for a 2nd industrial confirmation.

5. **case_003 + case_004 D1 PASS re-interpretation (V25 cross-case implication)**: V25's silent-placeholder semantic affects how case_003 + case_004 D1 PASSes were reported. Those PASSes confirm `_run_shared` runs cleanly + finds facing-face candidates on axis-aligned planar bodies — that's a real signal. They do NOT confirm A2 detects the 0.35 mm / 0.30 mm gap as a defect, because A2's `DetectedInterface` schema has no surface for gap-magnitude. **Recommend main session add a short note to case_003 + case_004 reference profiles** clarifying what those A2 PASSes do and do not validate. Cannot do this from sub-session per CLAUDE.md guardrails ("cannot modify another case's reference profile").

3. **`case_bc.writer` schema gap**: the existing main-project case-BC writer was designed for the case_002a buoyantSimpleFoam BC family (incompressible-buoyant; primary fields p_rgh + T + U + k + omega; mass-flow / freestream / pressure_outlet patch types). It does not support compressible BC types (totalPressure, totalTemperature, waveTransmissive, pressureInletOutletVelocity, compressible::alphatWallFunction). case_005 force-surfaced this by hand-crafting case-locally. **Likely main-project extraction priority rises after case_006 (also compressible-class) lands.**

4. **Codex case-design protocol** (V16): Codex's `cq.Compound.makeCompound([Face_1, Face_2, ...])` over-density export pattern fragments through STEP roundtrip into N independent Part::Feature objects, not 1 object with N faces. The defect manifest's verification command (single-object `len(.Faces)`) consequently underreports the face count by factor N. **Recommendation: future Codex case-design prompts should specify "single Solid or single Compound" output for over-density defects.** Document in `codex_case_design_protocol.md`.

## Solver-class capability axis

This case fills the **internal compressible diffuser (subsonic-transonic)** row in the project's coverage map (per DEC-V61-198 Pillar 1). Project state advanced from:

```
{ internal+buoyancy ✅ (case_002a),
  CHT ✅ (case_002b),
  external high-Re   🟦 dispatched (case_003),
  rotating MRF       🟦 dispatched (case_004),
  internal compressible diffuser 🟦 dispatched (case_005) }
```

to:

```
{ internal+buoyancy ✅ (case_002a),
  CHT ✅ (case_002b),
  external high-Re   🟦 dispatched (case_003, deferred),
  rotating MRF       🟦 dispatched (case_004, deferred),
  internal compressible diffuser ✅ (case_005, v1 baseline) }   <— filled
```

upon V16+V17+V18+V19 capture. Closure not required — partial coverage at "first run through it" depth counts as covered, per the DEC-V61-198 convention case_002a established.

## References

- DEC-V61-198 — APU bay strategic pivot (parent decision)
- `case_002a_apu_bay_buoyant_simple.md` — sibling industrial reference (different solver class)
- `case_002b_apu_bay_cht.md` — sibling (CHT class)
- `industrial_case_solver_findings.md` — V-series (V16, V17, V18, V19 sourced here)
- `solver_convergence_playbook.md` — decision tree (S13 sourced here)
- `case_kickoff_prompt_template.md` + `methodology/kickoff/case_005_*` — sub-session briefing artifacts
- `case_index.md` — multi-case tracker
- `~/Desktop/case_005_rae_m2129_sduct/evidence/v1_final/REPORT.md` — v1 audit trail
- `~/Desktop/case_005_rae_m2129_sduct/docs/decisions_v1.md` — v1 engineering decision log
