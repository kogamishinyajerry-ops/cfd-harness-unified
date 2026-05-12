# Case 003 · CRM-HLS Boundary Layer · Sub-Session Kickoff (paste-ready)

> **Paste the section between `=== BEGIN KICKOFF ===` and
> `=== END KICKOFF ===` into a fresh Claude Code session as the
> first message.**
>
> Designed by Codex (gpt-5.5 via codex-relay) per
> `codex_case_design_protocol.md`. Validated by main session
> 2026-05-07 evening — see `case_003_validation.md` for the
> 6-check report. Verdict: PASS WITH NOTES.
>
> **A2 advisor LANDED 2026-05-08 (commit `a09ae0a`)** — kickoff
> updated to direct sub-session at the landed
> `virtual_interface_detector`; Pillar 2 force-extraction signal
> for V2 has discharged.

---

=== BEGIN KICKOFF ===

You are a Claude Code sub-session under orchestration of the
cfd-harness-unified project. You are taking ONE industrial CFD
case as your task: **case_003_crm_hls_boundary_layer**. The
project main session is held in a separate Claude Code session
and will harvest your sediment after you complete (or pause)
your work.

## Project context (read first)

cfd-harness-unified is a CFD harness over OpenFOAM at
`/Users/Zhuanz/Desktop/cfd-harness-unified/`. Per DEC-V61-198
(2026-05-07) the project is reframed as "a container that
accumulates industrial CFD experience" — each industrial case
extends coverage of a solver-class axis and feeds the V-series
finding index + RAG corpus.

Two cases already covered:
- case_002a (APU bay buoyantSimpleFoam, internal flow + buoyancy)
- case_002b (APU bay CHT, multi-region thermal coupling)

Your case fills the **external high-Re + boundary layer** row —
currently uncovered. You are the FIRST of 8 dispatched cases
(003-010) to actually run sub-session execution. After you
complete, the project's solver-class coverage advances by one
axis AND the harvest cycle gains its first 003-series sediment.

You are NOT here to ship a generic feature. You are here to:
1. Run case_003 end-to-end in its desktop sandbox
2. Produce sediment artifacts in the format the main session expects
3. Surface and document new failure modes (V-series candidates V16+)
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
   V-series; **note**: your case is `incompressible-RANS` numerics
   class. Per Pattern 6, you inherit NO V3-V13 / V15 findings
   (those are compressible-buoyant-RANS). You will source net-new
   findings
5. `.planning/methodology/solver_convergence_playbook.md` — S1-S12
   decision tree; consult when convergence stalls
6. `.planning/methodology/rag_corpus_format.md` — the 5 artifacts
   your case-thread must produce
7. `~/Desktop/apu-bay-ventilation/` — case_002a actual sandbox.
   Mirror its structure: `inputs/`, `config/case.yaml`,
   `templates/`, `scripts/01..11`, `case/`, `evidence/`. The
   numbered-script + Jinja2 + SSOT YAML pattern is canonical
8. `.planning/methodology/kickoff/case_003_codex_response.md` —
   **Codex's full case design** (your starting point — 5
   deliverables: brief + CAD script + STEP path + parts manifest +
   defect manifest)
9. `.planning/methodology/kickoff/case_003_validation.md` — main
   session's validation notes
10. `.planning/cross_cuts/v_series_2026-05-08.md` — current
    V-series snapshot; note the A2 advisor LANDED row covering
    cases 003-010

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
   - `from ui.backend.services.geometry_ingest.virtual_interface_detector
     import detect_virtual_interfaces, InterfaceSpec` (for D1 — A2
     LANDED 2026-05-08, commit a09ae0a)
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

`case_003_crm_hls_boundary_layer`

### Solver class + numerics class

- Solver class (coverage map row): **external high-Re + boundary layer**
- Numerics class (Pattern 6): **incompressible-RANS** (root — no
  inheritance from prior cases)

### Codex's engineering brief (deliverable 1)

Read in full at
`.planning/methodology/kickoff/case_003_codex_response.md` §
"Deliverable 1 — Engineering brief". Summary:

- **Component**: NASA/AIAA HLPW6 CRM-HLS (transport-aircraft
  high-lift wing with main element + slat + flap + slat brackets)
- **Source**: Tier-1 public reference;
  https://aiaa-hlpw.org/HLPW6/cases (page) +
  https://aiaa-hlpw.org/assets/HLPW6/CRM_HLS_HLPW6_TC1.stp
  (direct STEP). Both confirmed reachable HTTP 200 by main
  session validation
- **Engineering question**: "Can the harness ingest and mesh a
  public industrial high-lift aircraft STEP, preserve named CFD
  boundary patches, detect CAD defects before meshing, and obtain
  a stable incompressible-RANS baseline for separated high-lift
  external flow?"
- **Physics**:
  - Solver v1: `simpleFoam` (steady incompressible)
  - v2 fallback: `pimpleFoam` only if force monitors oscillate
  - Turbulence: kOmegaSST
  - Freestream: air at 288 K, ν=1.5e-5 m²/s
  - U_inf = 55 m/s, alpha = 8°
  - Mach ≈ 0.16 (incompressible-baseline acceptable)
  - Re ≈ 3.7e6 per 1 m reference chord
- **Expected metrics**: Cl, Cd, Cm via `forceCoeffs`; sectional
  Cp; y+ histogram; wake visualization; advisor detection results
  for both defects
- **Estimated effort**: 5-8 hours, ~3 versions

### Codex's CAD generation script (deliverable 2)

Located in Codex response. Save it to your sandbox at
`scripts/build_cad.py`. It:
- Downloads the CRM-HLS STEP from HLPW6 (with caching at
  `inputs/cache/tier1_crm_hls_hlpw6_tc1.stp`)
- Uses CadQuery to load the reference geometry
- Adds 4 wall bodies: airframe_reference + auxiliary fixtures
  (root_mount_pad, root_mount_cover, thin_access_plate)
- Adds 6 domain patches: inlet, outlet, symmetry_plane,
  farfield_top, farfield_bottom, farfield_outer
- Injects D1 (0.35 mm gap between root_mount_pad and
  root_mount_cover) and D8 (0.80 mm thin access plate)
- Canonicalizes STEP header for byte-identical regeneration

**Install requirement**: cadquery is NOT in the main project venv.
Your sandbox needs its own venv:

```bash
cd ~/Desktop/case_003_crm_hls_boundary_layer
python3 -m venv .venv
.venv/bin/pip install cadquery numpy pyyaml jinja2 trimesh
```

### Codex's STEP file path (deliverable 3)

Output target:
`/Users/Zhuanz/Desktop/case_003_crm_hls_boundary_layer/inputs/cad_codex_v1.step`

Run the script with:
```bash
python scripts/build_cad.py --out inputs/cad_codex_v1.step
```

### Codex's parts manifest (deliverable 4)

Save at `inputs/parts_manifest.yaml` per Codex's spec — 10 parts,
roles + BCs documented. Use as input for `08_write_bcs.py` (or
equivalent) when you write BC field files.

### Codex's defect manifest (deliverable 5)

Save at `inputs/defect_manifest.yaml`. Two defects:
- **D1**: 0.35 mm gap between `root_mount_pad` and
  `root_mount_cover`. Verification: FreeCAD `distToShape`
  (command in manifest)
- **D8**: 0.80 mm thick `thin_access_plate`. Verification:
  FreeCAD `BoundBox` min dimension

## Defect verification protocol (extra step for Codex-designed cases)

Before running the CFD pipeline, verify defects:

### D1 verification — A2 advisor LANDED, USE IT

A2 advisor extracted to main project 2026-05-08 (commit `a09ae0a`).
You are the FIRST sub-session to exercise it on a real industrial
case. Treat your run as **field validation**.

> [QUESTIONABLE 2026-05-08]: "exercise A2; expect detection of
> 0.35 mm gap" framing assumes a capability A2 v1 does NOT have.
> A2 LANDED for V2 pattern (shared-interface confirmation on
> non-manifold STEP), NOT D1 pattern (gap-as-defect detection).
> Per V25 (open · `industrial_case_solver_findings.md#V25`),
> A2's `_run_shared` returns `matched=True` with hardcoded
> placeholder fields regardless of actual gap distance.
> Verification pending: A2-v2 sub-DEC adds `inter_face_gap_mm`
> field to `DetectedInterface` (drafted at
> `.planning/patches/draft_a2_v2_gap_detection_2026-05-08.md`).
> To resolve: A2-v2 lands AND sub-session re-runs case_003 D1
> falsification. Until then, your A2 PASS confirms only that
> `_run_shared` algorithm runs cleanly and finds a facing-face
> candidate — NOT that A2 detects the 0.35 mm gap as a defect.

**Step 1 — manual ground truth via FreeCAD**:

```bash
FreeCADCmd -c "import FreeCAD as App, Import; \
  doc=App.newDocument(); \
  Import.insert('/Users/Zhuanz/Desktop/case_003_crm_hls_boundary_layer/inputs/cad_codex_v1.step', doc.Name); \
  o={x.Label:x for x in doc.Objects}; \
  print(o['root_mount_pad'].Shape.distToShape(o['root_mount_cover'].Shape)[0])"
```

Expected: ≈ 0.35 mm. Report actual measured value.

**Step 2 — exercise landed A2 advisor**:

```python
import sys
sys.path.insert(0, "/Users/Zhuanz/Desktop/cfd-harness-unified")
from ui.backend.services.geometry_ingest.virtual_interface_detector import (
    detect_virtual_interfaces, InterfaceSpec, FaceGeometry, BodyGeometry,
)
# Build BodyGeometry for root_mount_pad and root_mount_cover from STEP
# face extraction (FreeCAD or trimesh — your choice). Each face needs:
#   area, bbox_min, bbox_max, normal, centroid (case units, meters).
spec = InterfaceSpec(
    name="root_mount_pad__root_mount_cover_interface",
    mode="shared",
    bodies=("root_mount_pad", "root_mount_cover"),
)
result = detect_virtual_interfaces(bodies=[pad_body, cover_body],
                                   specs=[spec])
# Expect: result contains 1 DetectedInterface with the two facing
# faces despite isSame() failing on the BREP (V2 lesson).
```

**Step 3 — V-finding judgments**:

- If A2 detects the interface → upgrade V2 / case_003 row in
  `industrial_case_solver_findings.md` from "advisor landed" to
  "advisor field-validated on case_003"
- If A2 misses (false negative) → V16 finding "A2 advisor toy-case
  bias on industrial-scale BREP face counts/areas" + propose
  threshold tuning sub-DEC
- If A2 produces extra spurious matches (false positive) → V17
  finding "A2 advisor over-eager on adjacent-but-not-shared faces"
  + propose `mode='shared'` tightening

The advisor's docstring explicitly forbids `isSame()` fast-path —
do NOT propose adding one (V2 lesson preserved).

### D8 verification

```bash
FreeCADCmd -c "import FreeCAD as App, Import; \
  doc=App.newDocument(); \
  Import.insert('/Users/Zhuanz/Desktop/case_003_crm_hls_boundary_layer/inputs/cad_codex_v1.step', doc.Name); \
  o={x.Label:x for x in doc.Objects}; \
  bb=o['thin_access_plate'].Shape.BoundBox; \
  print(min(bb.XLength, bb.YLength, bb.ZLength))"
```

Expected: ≈ 0.80 mm. Report actual measured value.

Then exercise the landed advisor:

```python
# In a Python script invoked from your sandbox (NOT the runtime case venv;
# from main-project's venv with cfd-harness-unified PYTHONPATH set)
import sys
sys.path.insert(0, "/Users/Zhuanz/Desktop/cfd-harness-unified")
from ui.backend.services.geometry_ingest.thin_wall_advisor import (
    PatchGeometry, detect_thin_wall_patches_at_risk
)
# Build PatchGeometry for thin_access_plate from STEP bbox
# (FreeCAD or trimesh — your choice)
warnings = detect_thin_wall_patches_at_risk(
    patches=[PatchGeometry(name="thin_access_plate",
                            bbox_dimensions=(plate_dx_m, plate_dy_m, 0.0008))],
    refinement_levels={"thin_access_plate": (1, 2)},
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
   `.planning/case_profiles/case_003_crm_hls_boundary_layer.md`
   in the main repo with the structure of case_002a/b
2. **V-series append**: every NEW failure mode goes in
   `industrial_case_solver_findings.md` as V_n (next available is
   V16 — V14, V15 already taken by case_002b). Watch for:
   - **A2 advisor field-behavior on industrial BREP** (above —
     three-branch V-finding decision tree)
   - Prism layer first-cell-height vs y+ target mismatch
   - Wake-region cell sizing under-resolved
   - kOmegaSST inadequate at high-lift separated zones
   - Far-field too-close blockage effects
   - High-lift separated steady RANS pseudo-steady oscillation
3. **Playbook tree append**: if a new generalizable pattern
   surfaces, add S13+ to `solver_convergence_playbook.md`
4. **Stale-assumption falsification**: if your case exposes a
   main-project default / threshold / schema that doesn't match
   external-RANS reality, fix in place. Commit message tag
   `corrects-assumption: <X>, surfaced-by: case_003-V<n>`
5. **Artifact extraction**: if you're forced to hand-craft
   reusable patterns, extract as small sub-DEC commits (<250 LOC
   + tests). Most likely candidate this case: a y+ post-flight
   advisor (parses solver log → reports first-cell y+ histogram
   + suggests prism layer adjustment). This is M2 advisor
   territory and will be valuable for case_005+
6. **RAG corpus injection**: produce the 5 artifacts per
   `rag_corpus_format.md` (reference profile + case.yaml +
   per-version run logs + final report + decision log)

## Your sandbox structure

Create at `~/Desktop/case_003_crm_hls_boundary_layer/`. Mirror
case_002a layout:

```
~/Desktop/case_003_crm_hls_boundary_layer/
├── README.md                  ← case-thread overview
├── Makefile                   ← `make all` runs full pipeline
├── .venv/                     ← case-local venv with cadquery
├── config/
│   └── case.yaml              ← SSOT
├── inputs/
│   ├── cad_codex_v1.step      ← generated by build_cad.py
│   ├── parts_manifest.yaml    ← from Codex deliverable 4
│   ├── defect_manifest.yaml   ← from Codex deliverable 5
│   └── cache/                 ← cached HLPW6 source STEP
├── templates/                 ← Jinja2 for OpenFOAM dicts
├── scripts/
│   ├── _lib.py                ← shared helpers
│   ├── build_cad.py           ← from Codex deliverable 2
│   ├── 01_validate_cad.py     ← STEP import + body name check
│   ├── 02_verify_defects.py   ← run D1+D8 verification
│   ├── 03_validate_stl.py     ← multi-solid STL → harness loader
│   ├── 04_scaffold_case.py    ← case/ directory tree
│   ├── 05_make_dicts.py       ← Jinja2 → all OpenFOAM dicts
│   ├── 06_run_mesh.sh         ← Docker: blockMesh + sHM
│   ├── 07_check_mesh.py       ← harness checkmesh + advisor
│   ├── 08_write_bcs.py        ← harness BC writer per parts manifest
│   ├── 09_run_solver.sh       ← Docker: simpleFoam (potentialFoam warm start)
│   ├── 10_post.py             ← ParaView slices + Cp + force coeffs
│   └── 11_audit.py            ← signed evidence pack
├── case/                      ← OpenFOAM runtime (gitignored)
└── evidence/<version>/        ← per-version reports
    └── REPORT.md
```

Do NOT commit `case/` runtime contents to main repo.

## Sediment-back protocol

When you complete (or pause):

1. Reference profile up to date in main repo
2. V-series rows added to `industrial_case_solver_findings.md`
   (especially A2 field-validation row — this is high-value
   sediment, you are first 003-series case)
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
chore(case_003): v<N> · <short summary>

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
  A2 virtual_interface_detector) → hand-craft case-locally,
  document the gap, flag for main-session extraction
- Codex's design fundamentally unworkable → pause, flag, main
  session asks Codex for revision (round-cap=2)

## Boundaries

You CAN:
- Run case_003 commands end-to-end
- Modify your sandbox files freely
- Commit to main repo for sediment artifacts
- Extract small reusable artifacts (<250 LOC) when forced
- Fix toy-case-biased thresholds discovered in main-project advisors

You CANNOT:
- Modify another case's reference profile
- Open new full DEC arcs
- Change governance rules / framework decisions
- Run subagent or persona-driven dogfood
- Take a different case
- Re-design the case (only execute Codex's design + flag for
  revision if needed)
- Add `isSame()` fast-path to `virtual_interface_detector` (V2 lesson)

## When you are done

Final report at `evidence/<latest>/REPORT.md`. Update
`case_index.md` status. Final commit summarizing. Then stop —
do NOT spawn additional sub-sessions or take additional cases.

## Known issues to watch

Per main session's validation report
(`case_003_validation.md`):

1. **CRM-HLS reference flattens to one body** — Codex uses
   `cq.Compound.makeCompound`; loses internal slat/flap/main
   element separation. v1 acceptable; v2 may want per-component
   patches if needed
2. **SOURCE_SHA256 empty** — first run downloads without checksum;
   pin after first successful download for reproducibility
3. **A2 advisor JUST landed** (commit `a09ae0a`, 2026-05-08) — you
   are first industrial validator; expect threshold-tuning sub-DEC
   candidate to surface from your run

=== END KICKOFF ===

---

## Main session post-dispatch checklist

After user pastes the kickoff into a new Claude Code session:

- [ ] Update `case_proposal_queue.md` — move case_003 row from
      "Active queue" to "Dispatched"
- [ ] Update `case_index.md` — add case_003 row, status = "active"
- [ ] Wait for sub-session sediment in subsequent main-session
      turns
- [ ] When sub-session reports A2 field-validation outcome
      (validated / false-negative / false-positive), update
      `industrial_case_solver_findings.md` V2 row + queue any
      threshold-tuning sub-DEC for harvest cycle
