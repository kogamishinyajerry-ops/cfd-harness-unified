# Case 007 · KCS Ship VOF · Sub-Session Kickoff (paste-ready)

> **Paste section between `=== BEGIN ===` and `=== END ===` into a
> fresh Claude Code session.**
>
> Designed by Codex (gpt-5.5 xhigh, 86gs, round 2 of 2 — round 1
> hallucinated read-only-workspace objection, round 2 succeeded
> with clarification). Validated by main session 2026-05-08 — see
> `case_007_validation.md`. Verdict: PASS WITH NOTES (D8 exercises
> landed thin_wall_advisor; ITTC license context: bake-into-script
> strategy).
>
> **A2 advisor LANDED 2026-05-08 (commit `a09ae0a`) BUT scope-narrow
> per V25** (open · sourced by case_005 v2 disambiguation, captured
> in harvest cycle 002): A2's `_run_shared` returns matched=True
> with hardcoded placeholder fields regardless of actual gap
> distance. D1 exercise produces algorithm-runs-cleanly evidence,
> NOT gap-detection field-validation. A2-v2 sub-DEC drafted at
> `.planning/patches/draft_a2_v2_gap_detection_2026-05-08.md`.

=== BEGIN ===

You are a Claude Code sub-session under orchestration of
cfd-harness-unified. Your task: **case_007_kcs_ship_vof**. Main
session is separate; sediment harvested via commits.

## Project context

cfd-harness-unified at `/Users/Zhuanz/Desktop/cfd-harness-unified/`.
Per DEC-V61-198, accumulates industrial CFD experience.

Six prior cases:
- case_002a, 002b: active
- case_003 (CRM-HLS, external high-Re): active · v1 paused on V20
  unit-scale block
- case_004 (NREL Phase VI rotor, MRF): active · v1 advisor-validation
  done; CFD pending v2
- case_005 (RAE M2129 S-duct): active · v1+v2 ran; sourced
  V16-V25 chain (incl. V25: A2 placeholder semantic OPEN)
- case_006 (ONERA M6 transonic): dispatched-deferred

Your case fills **multiphase-VOF** — first multiphase for project.
You are also second case in roster expected to exercise landed
thin_wall_advisor on a thin-shell defect (case_004 0.75mm shim
+ case_007 0.80mm transom plate → 4-case cross-topology evidence
when complete: 002a + 003 + 004 + 007). Coverage map advances by
one axis after you complete.

## Required reading
1. `.planning/decisions/2026-05-07_v61_198_apu_bay_strategic_pivot.md`
   — strategic philosophy SSOT
2. `.planning/case_proposal_queue.md`
3. `.planning/case_profiles/case_002a_*.md` AND `case_002b_*.md`
   (reference profile format)
4. `.planning/methodology/industrial_case_solver_findings.md`
   (Pattern 6: case_007 inherits NONE of V3-V25; multiphase-VOF
   is a new numerics root)
5. `.planning/methodology/solver_convergence_playbook.md`
6. `.planning/methodology/rag_corpus_format.md`
7. **`.planning/methodology/knowledge_status_convention.md`**
   (NEW · 2026-05-08 harvest 002) — defines `[QUESTIONABLE]` /
   `[REFUTED]` / `[SUPERSEDED]` / `[VALIDATED]` markers for any
   claim in this kickoff or your output sediment
8. `.planning/cross_cuts/v_series_2026-05-08.md` (V-series snapshot)
9. `.planning/harvest_reports/2026-05-08_harvest_002.md` (cycle 002
   findings — A2 capability framing notes)
10. `~/Desktop/apu-bay-ventilation/` (sandbox layout reference)
11. `.planning/methodology/kickoff/case_007_codex_response.md`
    (Codex's 5 deliverables)
12. `.planning/methodology/kickoff/case_007_validation.md`
    (validation notes)

## Hard guardrails
1. V130 advisory-only (no AI writes case files)
2. V132 no AI-mutating routes
3. No date/calendar gating
4. No persona dogfood (F-series closed)
5. OpenFOAM is truth source
6. Use main-project advisors:
   - `from ui.backend.services.geometry_ingest.thin_wall_advisor
     import detect_thin_wall_patches_at_risk` (for D8 — LANDED,
     robust 3-of-3 cross-topology per V23)
   - `from ui.backend.services.geometry_ingest.virtual_interface_detector
     import detect_virtual_interfaces, InterfaceSpec` (for D1 — A2
     LANDED 2026-05-08 a09ae0a, BUT see [QUESTIONABLE] marker
     in D1 verification section below)
   - `from ui.backend.services.geometry_ingest.geometry_surgery
     import decimate_to_tier` (if mesh adjustments forced)
   - DO NOT re-implement these case-locally
7. Do NOT redesign the case — execute Codex's brief; revision
   request only if fundamentally unworkable (round-cap=2)
8. Mach ceiling negligible (incompressible); no compressible thermo
9. Hull surface and wave-cut at y/L=0.1509 must remain mesh-clean
10. **License**: Codex's bake-into-script approach is the safe path — do NOT redistribute the generated STEP externally without ITTC permission verification
11. Do NOT add `isSame()` fast-path to `virtual_interface_detector`
    (V2 lesson preserved)

## Case identifier
`case_007_kcs_ship_vof` · solver-class **multiphase-VOF / interFoam** · numerics-class **multiphase-VOF** (root)

## Codex's brief (deliverable 1)
Read full at `case_007_codex_response.md`. Summary:
- KCS half-hull + rudder, Lpp=7.2786 m model scale, Fr=0.26, U_inf=2.1962 m/s, Re=1.4e7
- Engineering question: can the harness ingest a real ship-hydro STEP, configure interFoam, preserve sharp alpha.water, report Ct/Cf/Cw + wave pattern
- Solver v1: interFoam + tail-averaged force/wave extraction
- v2 fallback: interIsoFoam if VOF smearing destroys Kelvin wake
- Effort: 8-12h, 3 versions

## Codex's CAD script (deliverable 2)
Save at `scripts/build_cad.py`. 312 LOC, deterministic. Bakes
KCS station offsets from NMRI public pages into Python constants
(no STEP redistribution). Generates 10 named bodies including
hull/rudder/atmosphere/water_inlet/water_outlet/symmetry plane/
domain box.

Sandbox install:
```bash
cd ~/Desktop/case_007_kcs_ship_vof
python3 -m venv .venv
.venv/bin/pip install cadquery numpy pyyaml jinja2 trimesh
python scripts/build_cad.py --out inputs/cad_codex_v1.step
```

## Multiphase-VOF-specific work (case_007 unique territory)

The harness has no prior multiphase infrastructure. Hand-craft
case-locally; main session decides extraction priority:

### `08b_write_multiphase_bc.py`
Consume parts manifest → emit `0/alpha.water`, `0/p_rgh`,
update `0/U` for VOF. Key BC types:
- atmosphere: alpha.water inletOutlet, p_rgh totalPressure(p0=0),
  U pressureInletOutletVelocity
- water_inlet: alpha.water variableHeightFlowRate (water below
  z=0), U fixedValue, p_rgh fixedFluxPressure
- water_outlet: alpha.water zeroGradient (or inletOutlet),
  p_rgh fixedValue 0
- side_walls / domain_bottom: slip + zeroGradient
- symmetry_plane_centerline: symmetry on all fields

### `08c_write_setFields_water_level.py`
Emit `system/setFieldsDict` initializing alpha.water=1 for z<=0,
=0 for z>0.

### `08d_write_thermophysical_water_air.py`
Emit `constant/transportProperties` with two phases (water, air)
+ ρ + ν + σ surface tension.

### `09_run_solver.sh` for interFoam
- `setFields` first
- `interFoam -decomposeParDict` (4 procs typical for case_007 mesh size)
- runTime ≥ 30 L/U_inf (10 flow-throughs); average forces over last 5

### `10b_compute_wave_metrics.py`
1. Extract `alpha.water=0.5` iso-surface → wave elevation z(x,y)
2. Longitudinal wave cut at y/L=0.1509 → cw(x) plot vs published
3. Tail-averaged total force on hull → Ct
4. ITTC-1957: Cf = 0.075 / (log10(Re)-2)²
5. Cw = Ct - Cf - form factor estimate
6. Emit `evidence/<v>/wave_report.md`

## Defect verification

### D1 (rudder hub gap, 0.35 mm) — A2 advisor LANDED with caveat

> [QUESTIONABLE 2026-05-08]: "exercise A2; expect detection of
> 0.35 mm gap" framing assumes a capability A2 v1 does NOT have.
> A2 LANDED for V2 pattern (shared-interface confirmation on
> non-manifold STEP), NOT D1 pattern (gap-as-defect detection).
> Per V25 (open · `industrial_case_solver_findings.md#V25`),
> A2's `_run_shared` returns `matched=True` with hardcoded
> placeholder `bbox_overlap_fraction=1.0` /
> `area_diff_fraction=0.0` regardless of actual gap distance.
> Verification pending: A2-v2 sub-DEC adds `inter_face_gap_mm`
> field to `DetectedInterface` (drafted at
> `.planning/patches/draft_a2_v2_gap_detection_2026-05-08.md`).
> To resolve: A2-v2 lands AND case_007 sub-session re-runs D1
> falsification on rudder-hub geometry. Until then, your A2 PASS
> confirms only that `_run_shared` runs cleanly on rudder-hub
> faces — NOT that A2 detects the 0.35 mm gap as a defect.

**Step 1 — manual ground truth via FreeCAD**:

```bash
FreeCADCmd -c "import FreeCAD as App, Import; \
  doc=App.newDocument(); \
  Import.insert('/Users/Zhuanz/Desktop/case_007_kcs_ship_vof/inputs/cad_codex_v1.step', doc.Name); \
  o={x.Label:x for x in doc.Objects}; \
  print(o['rudder_hub_fairing'].Shape.distToShape(o['rudder_reference'].Shape)[0])"
```

Expected ≈ 0.35 mm. Report actual measured value.

**Step 2 — exercise landed A2 advisor**:

```python
import sys
sys.path.insert(0, "/Users/Zhuanz/Desktop/cfd-harness-unified")
from ui.backend.services.geometry_ingest.virtual_interface_detector import (
    detect_virtual_interfaces, InterfaceSpec, FaceGeometry, BodyGeometry,
)
spec = InterfaceSpec(
    name="rudder_hub__rudder_reference_interface",
    mode="shared",
    bodies=("rudder_hub_fairing", "rudder_reference"),
)
result = detect_virtual_interfaces(bodies=[hub_body, ref_body],
                                   specs=[spec])
# Expect: matched=True (per V21/V22 pattern) BUT this PASS is
# NOT field-validation of gap-detection capability per V25.
```

**Step 3 — V-finding judgments**:

- If `matched=True`: document as "case_007 cross-topology PASS for
  `_run_shared`'s algorithm-runs-cleanly behavior on ship-hydro
  rudder-hub geometry." Add to V22-style consistency evidence.
  Do NOT claim "advisor field-validated as gap-defect detector"
  (V25 forbids until A2-v2 lands).
- If `matched=False`: NEW V-finding — `_run_shared`'s
  `find_face_facing_target` heuristic fails on rudder-hub geometry
  type (which differs from axis-aligned-planar of cases 003/004
  and flange-ring-axial-end of case 005). Document the geometric
  reason; this is genuinely new topology evidence.
- Either way: do NOT propose `isSame()` fast-path (V2 lesson).

### D8 (thin transom plate, 0.80 mm) — thin_wall_advisor LANDED
```bash
FreeCADCmd -c "import FreeCAD as App, Import; \
  doc=App.newDocument(); \
  Import.insert('inputs/cad_codex_v1.step', doc.Name); \
  o={x.Label:x for x in doc.Objects}; \
  bb=o['stern_transom_plate_thin'].Shape.BoundBox; \
  print(min(bb.XLength, bb.YLength, bb.ZLength))"
```
Expected ≈ 0.80 mm. Then exercise the landed advisor:

```python
import sys
sys.path.insert(0, "/Users/Zhuanz/Desktop/cfd-harness-unified")
from ui.backend.services.geometry_ingest.thin_wall_advisor import (
    PatchGeometry, detect_thin_wall_patches_at_risk
)
warnings = detect_thin_wall_patches_at_risk(
    patches=[PatchGeometry(name="stern_transom_plate_thin",
                            bbox_dimensions=(plate_dx_m, plate_dy_m, 0.0008))],
    refinement_levels={"stern_transom_plate_thin": (1, 2)},
    background_cell_size=YOUR_BG_CELL_SIZE_METERS,
)
print(warnings)  # expect 'critical'
```

**4-case cross-topology validation arc**: case_002a (curved CATIA
Frame) + case_003 (planar CadQuery thin_access_plate) + case_004
(rotating-machinery `yaw_sensor_shim` 0.75mm) + case_007 (ship
transom plate 0.80mm). If your case_007 produces critical warning
consistent with cases 002a/003/004, **upgrade V10 / V23 status
from "3-of-3 cross-topology consistency" to "4-of-4 — robust
across (curved-shell, planar-aero, rotating-aux, ship-hydro)
topologies"** per `knowledge_status_convention.md` `[VALIDATED]`
marker. If divergent, flag as advisor-context-sensitivity
V-finding.

## Six per-case standard moves
1. Reference profile at `.planning/case_profiles/case_007_kcs_ship_vof.md`
2. V-series append: alpha smearing patterns, MULES boundedness,
   p_rgh hydrostatic init pitfalls, free-surface refinement vs
   cell aspect ratio, Kelvin wake decay rate. ALSO:
   **A2 `_run_shared` behavior on ship-hydro topology** (above);
   **thin_wall_advisor 4-case consistency check** (above)
3. Playbook S13+ candidates: free-surface convergence
   (tail-averaging vs steady residuals), MULES Courant limits,
   alpha.water BC family pitfalls
4. Stale-assumption fixes: 0.orig template likely has no
   alpha.water; transportProperties may not have multiphase block.
   Commit tag: `corrects-assumption: <X>, surfaced-by: case_007-V<n>`
5. Artifact extraction: `multiphase_bc_writer.py` /
   `setFields_water_level_writer.py` / `wave_cut_post_processor.py`
6. RAG corpus: 5 artifacts per `rag_corpus_format.md`

## Sandbox structure
```
~/Desktop/case_007_kcs_ship_vof/
├── README.md
├── Makefile
├── .venv/
├── config/case.yaml
├── inputs/{cad_codex_v1.step, parts_manifest.yaml, defect_manifest.yaml}
├── templates/{0.orig.j2 (extend for alpha.water + p_rgh),
│              transportProperties.j2 (NEW), setFieldsDict.j2 (NEW), ...}
├── scripts/{01..11 numbered + 08b/c/d for multiphase + 10b for waves}
├── case/    (gitignored OpenFOAM runtime)
└── evidence/<v>/{REPORT.md, wave_report.md, d8_thin_wall_exercise.md}
```

## Sediment + commit convention
Same as case_002a/b: commit messages NOT to mention being an AI;
include `confidence: <high|med|low>` trailer; co-author Claude
Opus 4.7. `case/` runtime gitignored. Sediment artifacts to
main repo as separate commits.

If you produce a V-finding involving an advisor capability claim,
apply `knowledge_status_convention.md` grammar — do NOT write
"A2 field-validated" if you only confirmed `_run_shared` runs
cleanly.

## Boundaries
- CAN: run case end-to-end, modify sandbox freely, commit sediment,
  extract <250 LOC artifacts, fix toy-case advisor biases, add
  multiphase fields to 0.orig if missing
- CANNOT: redesign case, modify other cases, open new DEC arcs,
  redistribute KCS-derived STEP externally without permission,
  add `isSame()` fast-path to `virtual_interface_detector` (V2 lesson)

## Known issues
1. **A2 advisor LANDED but scope-narrow (V25 open)** — D1 exercise
   produces algorithm-runs-cleanly evidence, NOT gap-detection
   field-validation. See `[QUESTIONABLE]` marker in D1 verification
   section above. A2-v2 sub-DEC drafted
   (`patches/draft_a2_v2_gap_detection_2026-05-08.md`); after it
   lands, case_007 v3 re-runs D1 falsification.
2. **D8 thin_wall_advisor 4-case consistency check** — case_004's
   0.75 mm shim + case_007's 0.80 mm transom should produce similar
   advisor signals; this completes the 4-case cross-topology arc
   (002a/003/004/007). Upgrade V10/V23 status to `[VALIDATED]` on
   consistency, or flag context-sensitivity V-finding on divergence.
3. **First multiphase case** — 0.orig template, transportProperties,
   setFieldsDict all need extension or addition
4. **License sensitivity** — bake-into-script keeps STEP
   regeneration deterministic from public offsets; do NOT publish
   the generated binary externally without ITTC permission
5. **Kelvin wake capture** — v1 alpha smearing may degrade pattern;
   v2 interIsoFoam fallback is the documented escape
6. **Round-1 hallucination logged** (case_007_validation.md N5):
   round 1 misread Deliverable 3 as binary STEP requirement; round
   2 succeeded with clarification preamble. If you encounter the
   same misreading in any prompt you produce, flag for RETRO
   addendum.

=== END ===

## Main session post-dispatch checklist
- [ ] Move case_007 row from "Active queue" to "In-flight"
- [ ] Update `case_index.md` with case_007 status=active
- [ ] Update `INDEX.md` with case_007 status reconciled
- [ ] When sub-session reports A2 `_run_shared` outcome on
      ship-hydro topology (PASS = algorithm-runs-cleanly, NOT
      gap-detection per V25), update V22 / V25 evidence rows
- [ ] When sub-session reports thin_wall 4-case cross-topology
      outcome, upgrade V10/V23 to `[VALIDATED]` (4-of-4) or open
      context-sensitivity V-finding on divergence
- [ ] When sub-session extracts multiphase infrastructure
      (multiphase_bc_writer / setFields / wave_cut_post_processor),
      evaluate for promotion to main-project shared services
