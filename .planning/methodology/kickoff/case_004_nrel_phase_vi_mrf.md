# Case 004 · NREL Phase VI · MRF · Sub-Session Kickoff (paste-ready)

> **Paste the section between `=== BEGIN KICKOFF ===` and
> `=== END KICKOFF ===` into a fresh Claude Code session as the
> first message.**
>
> Designed by Codex (gpt-5.5 via codex-relay) per
> `codex_case_design_protocol.md`. Validated by main session
> 2026-05-07 evening — see `case_004_validation.md` for the
> 6-check report. Verdict: PASS WITH NOTES (A2 advisor pending +
> URL fetch may fail on local network with DNS hijacking;
> documented as non-blocking).

---

=== BEGIN KICKOFF ===

You are a Claude Code sub-session under orchestration of the
cfd-harness-unified project. You are taking ONE industrial CFD
case as your task: **case_004_nrel_phase_vi_mrf**. The project
main session is held in a separate Claude Code session and will
harvest your sediment after you complete (or pause) your work.

## Project context (read first)

cfd-harness-unified is a CFD harness over OpenFOAM at
`/Users/Zhuanz/Desktop/cfd-harness-unified/`. Per DEC-V61-198
(2026-05-07) the project is reframed as "a container that
accumulates industrial CFD experience" — each industrial case
extends coverage of a solver-class axis and feeds the V-series
finding index + RAG corpus.

Three cases already in the case fleet:
- case_002a (APU bay buoyantSimpleFoam, internal flow + buoyancy) — active
- case_002b (APU bay CHT, multi-region thermal coupling) — active
- case_003 (CRM-HLS, external high-Re + boundary layer) — dispatched, **DEFERRED** awaiting user resources

Your case fills the **rotating machinery (MRF / sliding mesh)**
row — currently uncovered. After you complete, the project's
solver-class coverage advances by one axis. Note: case_003 may
or may not have run before you. Either order works because both
cases are root-of-numerics-class (no inheritance between them).

You are NOT here to ship a generic feature. You are here to:
1. Run case_004 end-to-end in its desktop sandbox
2. Produce sediment artifacts in the format the main session expects
3. Surface and document new failure modes (V-series candidates,
   especially MRF-specific)
4. Verify Codex's injected defects against main-project advisors
5. Do NOT refactor main project code beyond what your case
   strictly forces

## Required reading (in cfd-harness-unified repo, in order)

1. `.planning/decisions/2026-05-07_v61_198_apu_bay_strategic_pivot.md`
   — strategic philosophy SSOT
2. `.planning/case_proposal_queue.md` — your row + lifecycle
3. `.planning/case_profiles/case_002a_apu_bay_buoyant_simple.md`
   AND `case_002b_apu_bay_cht.md` — examples of reference profile
   format you will produce
4. `.planning/methodology/industrial_case_solver_findings.md` —
   V-series; **note**: your case is `incompressible-RANS-MRF`
   numerics class. Per Pattern 6, you inherit NO V3-V13/V15
   findings (compressible-buoyant-RANS) AND NO findings from
   case_003's external-incompressible-RANS once they accumulate.
   You will source net-new findings (likely V20+; case_003 has
   priority on V16-V19 if it runs first)
5. `.planning/methodology/solver_convergence_playbook.md` —
   S1-S12 decision tree; consult when convergence stalls.
   MRF-specific patterns will likely become S13+
6. `.planning/methodology/rag_corpus_format.md` — the 5 artifacts
   your case-thread must produce
7. `~/Desktop/apu-bay-ventilation/` — case_002a actual sandbox.
   Mirror its structure: `inputs/`, `config/case.yaml`,
   `templates/`, `scripts/01..11`, `case/`, `evidence/`. The
   numbered-script + Jinja2 + SSOT YAML pattern is canonical
8. `.planning/methodology/kickoff/case_004_codex_response.md` —
   **Codex's full case design** (your starting point — 5
   deliverables: brief + CAD script + STEP path + parts manifest +
   defect manifest)
9. `.planning/methodology/kickoff/case_004_validation.md` — main
   session's validation notes (especially A2-pending finding +
   DNS-hijack note)

## Hard guardrails (do NOT violate)

1. **V130 advisory-only**: AI does not write case files. Your role
   is engineer-level — you write case.yaml, BC files, scripts.
   When workbench AI advisor surfaces suggestions, you accept/
   reject manually
2. **V132 no AI-mutating routes**: do not invoke any
   `KNOWN_MUTATION_FUNCTIONS` from advisor surfaces; do not add
   new mutating callers
3. **No date/calendar gating**: progress is dependency-driven
4. **No persona-driven dogfood**: F-series is closed-arc; you are
   V-series-source
5. **OpenFOAM is truth source**: numerical claims must trace to a
   real OpenFOAM run
6. **Use main-project advisors when applicable**:
   - `from ui.backend.services.geometry_ingest.thin_wall_advisor
     import detect_thin_wall_patches_at_risk` (for D8 verification)
   - `from ui.backend.services.geometry_ingest.geometry_surgery
     import decimate_to_tier, axial_stretch, apply_surgery` (if
     you need sHM-friendly mesh adjustments)
   - DO NOT re-implement these case-locally
7. **Do NOT redesign the case** — Codex's brief is your starting
   point; if you find the design fundamentally unworkable, flag
   in your final report under "Main session attention required"
   and pause; main session asks Codex for revision (round-cap=2)

## Your case-specific assignment

### Case identifier

`case_004_nrel_phase_vi_mrf`

### Solver class + numerics class

- Solver class (coverage map row): **rotating machinery (MRF / sliding mesh)**
- Numerics class (Pattern 6): **incompressible-RANS-MRF** (root —
  no inheritance from prior cases)

### Codex's engineering brief (deliverable 1)

Read in full at
`.planning/methodology/kickoff/case_004_codex_response.md` §
"Deliverable 1 — Engineering brief". Summary:

- **Component**: NREL Phase VI two-bladed wind-turbine rotor
  (UAE rotor). 5.029 m radius, 72 rpm, S809 airfoil
- **Source**: Tier-1 NREL/DOE public reference (NREL/TP-500-29955)
- **Engineering question**: "Can the harness ingest a
  rotating-machinery STEP, preserve a named `rotating_cellzone`,
  configure `simpleFoam + MRFProperties` correctly, and produce
  physically sane thrust/torque trends for a public reference
  rotor while detecting two controlled CAD defects before
  meshing?"
- **Physics**:
  - Solver v1: `simpleFoam` + MRF (steady)
  - v2 fallback: `pimpleFoam` + AMI sliding mesh (ONLY if v1
    thrust/torque monitors stay oscillatory)
  - Turbulence: kOmegaSST
  - Fluid: air at 288 K, ν=1.5e-5 m²/s
  - U_inf baseline = 7 m/s; sweep points 7 / 10 / 15 m/s
  - ω = 7.539822 rad/s (72 rpm) about x-axis
  - Tip speed ≈ 37.9 m/s; M < 0.13 (incompressible OK)
  - Re ≈ 0.9-1.1e6 at 80% span
- **Expected metrics**: rotor thrust Fx, torque Mx, power
  P = ω·Mx, Ct/Cq/Cp vs U_inf, MRF audit (cell count in
  `rotating_cellzone`, rotating-wall enclosure check, ω sign
  check), y+ histogram on blades + hub, residuals + force
  monitor stability, advisor detection results for D1+D8
- **Estimated effort**: 6-10 hours, ~3 versions

### Codex's CAD generation script (deliverable 2)

Located in Codex response. Save it to your sandbox at
`scripts/build_cad.py`. It:
- Defines a 64-point S809 airfoil + 26-station chord/twist
  schedule for blade A (blended from circular root cylinder
  through transition to pure S809)
- Lofts blade A; rotates 180° about x-axis to make blade B
- Builds `rotating_cellzone` as an explicit cylindrical volume
  (radius 5632 mm, length 1800 mm, axis x)
- Builds `hub_spinner`, `nacelle_body`, `tower_body`,
  `nacelle_service_cover`, `yaw_sensor_shim`
- Builds `stationary_domain` + 6 box-faced patches
  (`inlet`, `outlet`, `tunnel_walls`)
- Injects D1 (0.30 mm gap nacelle_body↔nacelle_service_cover)
  and D8 (0.75 mm thick yaw_sensor_shim)
- Canonicalizes STEP header for byte-identical regeneration
- Optional Tier-1 PDF cache fetch (best-effort; non-fatal
  without `--require-reference-cache`)

**Install requirement**: cadquery is NOT in the main project venv.
Your sandbox needs its own venv:

```bash
cd ~/Desktop/case_004_nrel_phase_vi_mrf
python3 -m venv .venv
.venv/bin/pip install cadquery numpy pyyaml jinja2 trimesh
```

### Codex's STEP file path (deliverable 3)

Output target:
`/Users/Zhuanz/Desktop/case_004_nrel_phase_vi_mrf/inputs/cad_codex_v1.step`

Run the script with:
```bash
python scripts/build_cad.py --out inputs/cad_codex_v1.step
```

Do NOT pass `--require-reference-cache` on first run — main
session validation noted local DNS hijacking on the nrel.gov
URL (URL form is canonical, but `nlr.gov` redirect resolves to
RFC 2544 reserved IP). Cache fetch failure is non-fatal; CAD
generates purely from in-script constants.

If you want the actual NREL TP-500-29955 PDF for reference,
fetch outside the corporate network and place at
`inputs/cache/tier1_nrel_phase_vi_nrel_tp_500_29955.pdf`.

### Codex's parts manifest (deliverable 4)

Save at `inputs/parts_manifest.yaml` per Codex's spec — 12 parts,
roles + BCs documented + **explicit `rotating_cellzone` block +
top-level `rotation:` block with axis [1,0,0] and ω=7.539822
rad/s**. Use as input for `08_write_bcs.py` and a NEW
`08b_write_mrf.py` (you'll need this for case_004 — see below).

### Codex's defect manifest (deliverable 5)

Save at `inputs/defect_manifest.yaml`. Two defects:
- **D1**: 0.30 mm gap between `nacelle_body` and
  `nacelle_service_cover` on the +Y side of the downstream nacelle.
  Verification: FreeCAD `distToShape` (command in manifest)
- **D8**: 0.75 mm thick `yaw_sensor_shim` near nacelle/tower
  junction. Verification: FreeCAD `BoundBox` min dimension

## MRF-specific work (case_004 unique territory)

The main project has **no prior infrastructure** for rotating
machinery. You will hand-craft these case-locally first; main
session harvest cycle will decide what to extract:

### MRFProperties writer

Add `scripts/08b_write_mrf.py` that consumes the parts manifest's
`rotating:` block and emits `case/constant/MRFProperties`:

```
MRF1
{
    cellZone        rotating_cellzone;
    active          yes;
    nonRotatingPatches ();
    origin          (0 0 0);
    axis            (1 0 0);
    omega           7.539822369;
}
```

### cellZones in mesh

`snappyHexMeshDict` must define `cellZones` for `rotating_cellzone`.
Codex's cylindrical volume is in the STEP — your sHM config
references it as a `searchableSurface` named `rotating_cellzone`
and sets `cellZone rotating_cellzone; faceZone rotating_cellzone;`
in the `geometry` block.

If the harness's existing sHM template does NOT support cellZone
extraction, this is a **stale-assumption candidate** — fix in
place via `templates/snappyHexMeshDict.j2` if forced. Commit
message tag `corrects-assumption: sHM-cellZone-support,
surfaced-by: case_004-V<n>`.

### MRF audit (post-mesh)

Add `scripts/07b_audit_mrf.py`:
1. Parse `case/constant/polyMesh/cellZones` (binary or ASCII)
2. Verify `rotating_cellzone` exists, count cells in zone
3. For each rotating wall (`rotor_blade_A`, `rotor_blade_B`,
   `hub_spinner`): assert all wall faces are inside the zone
4. Audit ω sign: with `axis=(1,0,0)` and `ω>0`, blade A at
   azimuth 0° must move in +Y direction (right-hand rule)
5. Output `evidence/<v>/mrf_audit.txt`

If any audit fails, that's an MRF V-finding candidate.

### Force monitor stability check

Steady MRF may show oscillatory force monitors that look like
"converged residuals + non-converged forces." Add to
`scripts/09_run_solver.sh` an `forceCoeffs` function object on
`rotor_blade_A + rotor_blade_B + hub_spinner` patches with axis
of moment = (1,0,0) and reference values:
- ρ = 1.225
- A_ref = π·R² = 79.43 m²
- l_ref = R = 5.029 m
- U_ref = U_inf

In `10_post.py`, parse the `postProcessing/forceCoeffs/0/
coefficient.dat` and check thrust/torque oscillation amplitude
in the last N iterations. If amplitude > 5% of mean → flag v2
sliding mesh trigger.

## Defect verification protocol (extra step for Codex-designed cases)

Before running the CFD pipeline, verify defects:

### D1 verification

```bash
FreeCADCmd -c "import FreeCAD as App, Import; \
  doc=App.newDocument(); \
  Import.insert('/Users/Zhuanz/Desktop/case_004_nrel_phase_vi_mrf/inputs/cad_codex_v1.step', doc.Name); \
  o={x.Label:x for x in doc.Objects}; \
  print(o['nacelle_body'].Shape.distToShape(o['nacelle_service_cover'].Shape)[0])"
```

Expected: ≈ 0.30 mm. Report actual measured value.

**Important · A2 advisor pending**: D1's `expected_advisor_to_catch`
is `virtual_interface_detector`, which is **NOT yet extracted in
main project** (per DEC-V61-198 the A2 artifact is in pending
queue; case_003 also surfaces this). You must:

1. **Manually verify the defect via FreeCAD** (above command)
2. **Document in your final report**: "D1 sub-mm gap detected
   manually; main-project A2 (virtual_interface_detector) NOT
   YET LANDED — request main session A2 extraction in next
   harvest cycle"
3. This is **expected behavior**, not a defect — the case-thread
   force-surfacing missing advisors is exactly the Pillar 2
   run-and-correct loop in DEC-V61-198. After case_003 + case_004
   both surface the same A2 gap, main session has compounded
   evidence to extract A2 across rotating + external solver
   classes

### D8 verification

```bash
FreeCADCmd -c "import FreeCAD as App, Import; \
  doc=App.newDocument(); \
  Import.insert('/Users/Zhuanz/Desktop/case_004_nrel_phase_vi_mrf/inputs/cad_codex_v1.step', doc.Name); \
  o={x.Label:x for x in doc.Objects}; \
  bb=o['yaw_sensor_shim'].Shape.BoundBox; \
  print(min(bb.XLength, bb.YLength, bb.ZLength))"
```

Expected: ≈ 0.75 mm. Report actual measured value.

Then exercise the landed advisor:

```python
# In a Python script invoked from your sandbox
import sys
sys.path.insert(0, "/Users/Zhuanz/Desktop/cfd-harness-unified")
from ui.backend.services.geometry_ingest.thin_wall_advisor import (
    PatchGeometry, detect_thin_wall_patches_at_risk
)
warnings = detect_thin_wall_patches_at_risk(
    patches=[PatchGeometry(name="yaw_sensor_shim",
                            bbox_dimensions=(shim_dx_m, 0.00075, shim_dz_m))],
    refinement_levels={"yaw_sensor_shim": (1, 2)},
    background_cell_size=YOUR_BG_CELL_SIZE_METERS,
)
print(warnings)  # expect a 'critical' warning
```

If `thin_wall_advisor` does NOT produce a warning, that's a real
V-finding — flag in your report under
"main-project advisor blind spots".

## Six per-case standard moves (DEC-V61-198)

Execute these as your work plan:

1. **Reference profile**: write
   `.planning/case_profiles/case_004_nrel_phase_vi_mrf.md` in the
   main repo with the structure of case_002a/b
2. **V-series append**: every NEW failure mode goes in
   `industrial_case_solver_findings.md` as V_n (next available is
   V16 if case_003 hasn't run; otherwise pick up where case_003
   left off). MRF-specific candidates to watch for:
   - `rotating_cellzone` name mismatch in MRFProperties → false
     stationary run with near-zero useful torque
   - Rotating zone too short axially → blade leading/trailing
     edges leak outside the rotating source region
   - ω sign or axis error → reverses torque sign while residuals
     look healthy
   - Steady MRF inadequate for tower/nacelle interaction → force
     monitor oscillation
   - Tunnel-wall blockage if domain too narrow
3. **Playbook tree append**: rotating-machinery patterns will
   likely become S13+ in
   `solver_convergence_playbook.md`. Likely candidates:
   - "Force monitor oscillates with steady residuals → check MRF
     zone enclosure first, AMI sliding mesh second"
   - "Near-zero torque with healthy residuals → check
     `MRFProperties` cellZone name vs polyMesh cellZones"
4. **Stale-assumption falsification**: case_004 will likely
   surface main-project assumptions that don't apply to rotating
   machinery (sHM template may not support cellZones; advisors
   may not know about MRF). Fix in place. Commit message tag
   `corrects-assumption: <X>, surfaced-by: case_004-V<n>`
5. **Artifact extraction**: most likely candidates this case:
   - `mrf_properties_writer.py` (consumes parts manifest →
     emits MRFProperties)
   - `mrf_audit.py` (post-mesh cellZone + rotating-wall
     enclosure check)
   - `force_monitor_stability_advisor.py` (parses forceCoeffs.dat,
     reports oscillation amplitude)
   These are M3-M4 advisor territory and valuable for case_005+
6. **RAG corpus injection**: produce the 5 artifacts per
   `rag_corpus_format.md` (reference profile + case.yaml +
   per-version run logs + final report + decision log)

## Your sandbox structure

Create at `~/Desktop/case_004_nrel_phase_vi_mrf/`. Mirror
case_002a layout, plus MRF-specific scripts:

```
~/Desktop/case_004_nrel_phase_vi_mrf/
├── README.md                  ← case-thread overview
├── Makefile                   ← `make all` runs full pipeline
├── .venv/                     ← case-local venv with cadquery
├── config/
│   └── case.yaml              ← SSOT (includes `rotation:` block)
├── inputs/
│   ├── cad_codex_v1.step      ← generated by build_cad.py
│   ├── parts_manifest.yaml    ← from Codex deliverable 4
│   ├── defect_manifest.yaml   ← from Codex deliverable 5
│   └── cache/                 ← optional cached NREL PDF
├── templates/                 ← Jinja2 for OpenFOAM dicts
│   ├── snappyHexMeshDict.j2   ← cellZone-aware (case_004 may
│   │                              need to fix this in place)
│   ├── MRFProperties.j2       ← NEW for case_004
│   └── ...
├── scripts/
│   ├── _lib.py                ← shared helpers
│   ├── build_cad.py           ← from Codex deliverable 2
│   ├── 01_validate_cad.py     ← STEP import + body name check
│   ├── 02_verify_defects.py   ← run D1+D8 verification
│   ├── 03_validate_stl.py     ← multi-solid STL → harness loader
│   ├── 04_scaffold_case.py    ← case/ directory tree
│   ├── 05_make_dicts.py       ← Jinja2 → all OpenFOAM dicts
│   ├── 06_run_mesh.sh         ← Docker: blockMesh + sHM (with cellZones)
│   ├── 07_check_mesh.py       ← harness checkmesh + advisor
│   ├── 07b_audit_mrf.py       ← NEW: cellZone + rotating-wall audit
│   ├── 08_write_bcs.py        ← harness BC writer per parts manifest
│   ├── 08b_write_mrf.py       ← NEW: write MRFProperties from manifest
│   ├── 09_run_solver.sh       ← Docker: simpleFoam (potentialFoam warm start)
│   ├── 10_post.py             ← ParaView slices + Cp + thrust/torque + Cp_rotor
│   └── 11_audit.py            ← signed evidence pack
├── case/                      ← OpenFOAM runtime (gitignored)
└── evidence/<version>/        ← per-version reports
    ├── REPORT.md
    └── mrf_audit.txt          ← from 07b_audit_mrf.py
```

Do NOT commit `case/` runtime contents to main repo.

## Sediment-back protocol

When you complete (or pause):

1. Reference profile up to date in main repo
2. V-series rows added to `industrial_case_solver_findings.md`
3. Any new playbook patterns added to
   `solver_convergence_playbook.md`
4. `case_index.md` updated (your row's status + last-touch)
5. Stale-assumption fixes as separate commits
6. Extracted artifacts as separate sub-DEC-scope commits
7. `case_proposal_queue.md` "Dispatched" → "In-flight" → "Closed"
   row movement
8. Final report at `evidence/<final_version>/REPORT.md`

Commit messages NOT to mention being an AI:
```
chore(case_004): v<N> · <short summary>

<body explaining version delta + V-findings + decisions>

confidence: <high|med|low>

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

## Communication with main session

Async via commits. When you produce sediment, main session
harvests on its next active turn.

If you encounter:
- Stale assumption needing cross-case discussion → flag in final
  report under "Main session attention required"
- Blocker requiring un-extracted main-project capability (e.g.,
  A2 virtual_interface_detector, MRF advisor stack) → hand-craft
  case-locally, document the gap, flag for main-session extraction
- Codex's design fundamentally unworkable → pause, flag, main
  session asks Codex for revision (round-cap=2)

## Boundaries

You CAN:
- Run case_004 commands end-to-end
- Modify your sandbox files freely
- Commit to main repo for sediment artifacts
- Extract small reusable artifacts (<250 LOC) when forced
- Fix toy-case-biased thresholds discovered in main-project advisors
- **Add cellZone support to sHM template** if main project lacks
  it (rotating machinery forces this — flag as
  `corrects-assumption`)

You CANNOT:
- Modify another case's reference profile
- Open new full DEC arcs
- Change governance rules / framework decisions
- Run subagent or persona-driven dogfood
- Take a different case
- Re-design the case (only execute Codex's design + flag for
  revision if needed)

## When you are done

Final report at `evidence/<latest>/REPORT.md`. Update
`case_index.md` status. Final commit summarizing. Then stop —
do NOT spawn additional sub-sessions or take additional cases.

## Known issues to watch

Per main session's validation report
(`case_004_validation.md`):

1. **A2 (virtual_interface_detector) not yet landed** — D1 verified
   manually; flag for extraction (compounded with case_003 if it
   surfaced same gap)
2. **NREL URL DNS hijack on local network** — `nrel.gov` resolves
   via Alibaba DNS to RFC 2544 reserved range. Script's
   `resolve_reference_report` is best-effort; CAD generates from
   in-script constants. Skip `--require-reference-cache`
3. **SOURCE_SHA256 empty** — pin after first successful PDF
   download for reproducibility
4. **Domain half-width tight (1.25 D)** — consider expanding to
   ~5-10 D if v1 shows tunnel-wall blockage
5. **Blade airfoil from AirfoilTools may differ sub-mm from NREL's
   internal S809 tweak** — acceptable for v1 (engineering question
   is harness ingestion, not strict NASA Ames parity)
6. **Steady MRF may not converge force monitors** — v2 AMI
   sliding mesh is the documented fallback; AMI patch names
   (`rotor_ami_inner`, `stator_ami_outer`) declared in manifest
   but unused in v1
7. **MRF infrastructure all-new** — main project has no
   `MRFProperties` template, no cellZone-aware sHM, no MRF audit
   advisor. Hand-craft case-locally; flag for extraction

=== END KICKOFF ===

---

## Main session post-dispatch checklist

After user pastes the kickoff into a new Claude Code session:

- [ ] Update `case_proposal_queue.md` — add case_004 row to
      "Dispatched" section
- [ ] Update `case_index.md` — add case_004 row, status = "dispatched"
- [ ] Wait for sub-session sediment in subsequent main-session
      turns
- [ ] When sub-session reports A2-extraction is needed, queue
      the A2 sub-DEC commit in next harvest cycle (especially if
      case_003 also surfaces it — compounded evidence)
- [ ] When sub-session extracts MRF infrastructure
      (MRFProperties writer, audit advisor), evaluate for
      promotion to main-project shared services
