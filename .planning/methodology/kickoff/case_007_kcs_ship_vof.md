# Case 007 · KCS Ship VOF · Sub-Session Kickoff (paste-ready)

> **Paste section between `=== BEGIN ===` and `=== END ===` into a
> fresh Claude Code session.**
>
> Designed by Codex (gpt-5.5 xhigh, 86gs, round 2 of 2 — round 1
> hallucinated read-only-workspace objection, round 2 succeeded
> with clarification). Validated by main session 2026-05-08 — see
> `case_007_validation.md`. Verdict: PASS WITH NOTES (5th
> consecutive A2-pending; D8 exercises landed thin_wall_advisor;
> ITTC license context: bake-into-script strategy).

=== BEGIN ===

You are a Claude Code sub-session under orchestration of
cfd-harness-unified. Your task: **case_007_kcs_ship_vof**. Main
session is separate; sediment harvested via commits.

## Project context

cfd-harness-unified at `/Users/Zhuanz/Desktop/cfd-harness-unified/`.
Per DEC-V61-198, accumulates industrial CFD experience. Six
prior cases (002a/b active; 003/004/005/006 dispatched-deferred).
Your case fills **multiphase-VOF** — first multiphase for project.
Coverage map advances by one axis after you complete.

## Required reading
1. `.planning/decisions/2026-05-07_v61_198_apu_bay_strategic_pivot.md`
2. `.planning/case_proposal_queue.md`
3. `.planning/case_profiles/case_002a_*.md` AND `case_002b_*.md` (reference profile format)
4. `.planning/methodology/industrial_case_solver_findings.md` (Pattern 6: case_007 inherits NONE)
5. `.planning/methodology/solver_convergence_playbook.md`
6. `.planning/methodology/rag_corpus_format.md`
7. `~/Desktop/apu-bay-ventilation/` (sandbox layout reference)
8. `.planning/methodology/kickoff/case_007_codex_response.md` (Codex's 5 deliverables)
9. `.planning/methodology/kickoff/case_007_validation.md` (validation notes)

## Hard guardrails
1. V130 advisory-only (no AI writes case files)
2. V132 no AI-mutating routes
3. No date/calendar gating
4. No persona dogfood (F-series closed)
5. OpenFOAM is truth source
6. Use main-project advisors: `thin_wall_advisor` (LANDED, D8 verification);
   `geometry_surgery` if mesh adjustments forced
7. Do NOT redesign the case — execute Codex's brief
8. Mach ceiling negligible (incompressible); no compressible thermo
9. Hull surface and wave-cut at y/L=0.1509 must remain mesh-clean
10. **License**: Codex's bake-into-script approach is the safe path — do NOT redistribute the generated STEP externally without ITTC permission verification

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

### D1 (rudder hub gap, 0.35 mm)
```bash
FreeCADCmd -c "import FreeCAD as App, Import; \
  doc=App.newDocument(); \
  Import.insert('inputs/cad_codex_v1.step', doc.Name); \
  o={x.Label:x for x in doc.Objects}; \
  print(o['rudder_hub_fairing'].Shape.distToShape(o['rudder_reference'].Shape)[0])"
```
Expected ≈ 0.35 mm. **A2 advisor pending — 5th consecutive case**.

### D8 (thin transom plate, 0.80 mm)
```bash
FreeCADCmd -c "import FreeCAD as App, Import; \
  doc=App.newDocument(); \
  Import.insert('inputs/cad_codex_v1.step', doc.Name); \
  o={x.Label:x for x in doc.Objects}; \
  bb=o['stern_transom_plate_thin'].Shape.BoundBox; \
  print(min(bb.XLength, bb.YLength, bb.ZLength))"
```
Expected ≈ 0.80 mm. Exercise `thin_wall_advisor` (LANDED). Compare
result with case_004's 0.75 mm yaw_sensor_shim — consistency
expected; if divergent, document as advisor-context-sensitivity
V-finding.

## Six per-case standard moves
1. Reference profile at `.planning/case_profiles/case_007_kcs_ship_vof.md`
2. V-series append: alpha smearing patterns, MULES boundedness, p_rgh hydrostatic init pitfalls, free-surface refinement vs cell aspect ratio, Kelvin wake decay rate
3. Playbook S13+ candidates: free-surface convergence (tail-averaging vs steady residuals), MULES Courant limits, alpha.water BC family pitfalls
4. Stale-assumption fixes: 0.orig template likely has no alpha.water; transportProperties may not have multiphase block
5. Artifact extraction: multiphase_bc_writer / setFields_water_level / wave_cut_post_processor
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

## Boundaries
- CAN: run case end-to-end, modify sandbox freely, commit sediment,
  extract <250 LOC artifacts, fix toy-case advisor biases, add
  multiphase fields to 0.orig if missing
- CANNOT: redesign case, modify other cases, open new DEC arcs,
  redistribute KCS-derived STEP externally without permission

## Known issues
1. **A2 pending — 5-of-5 compounded evidence**. Manual D1
   verification + flag for extraction (top harvest priority)
2. **D8 thin_wall_advisor consistency check** — case_004's 0.75 mm
   shim and case_007's 0.80 mm transom should produce similar
   advisor signals; divergence is V-finding
3. **First multiphase case** — 0.orig template, transportProperties,
   setFieldsDict all need extension or addition
4. **License sensitivity** — bake-into-script keeps STEP
   regeneration deterministic from public offsets; do NOT publish
   the generated binary externally
5. **Kelvin wake capture** — v1 alpha smearing may degrade pattern;
   v2 interIsoFoam fallback is the documented escape

=== END ===

## Main session post-dispatch checklist
- [ ] Move case_007 row from "Active queue" to "Dispatched"
- [ ] Update `case_index.md` with case_007 status=dispatched
- [ ] Update `INDEX.md` with case_007 in kickoff list
- [ ] When sub-session reports A2 still pending (it will), elevate A2 priority
- [ ] When sub-session extracts multiphase infrastructure, evaluate for promotion
