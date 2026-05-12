# Case 005 · RAE M2129 S-duct · Sub-Session Kickoff (paste-ready)

> **Paste the section between `=== BEGIN KICKOFF ===` and
> `=== END KICKOFF ===` into a fresh Claude Code session as the
> first message.**
>
> Designed by Codex (gpt-5.5 via codex-relay) per
> `codex_case_design_protocol.md`. Validated by main session
> 2026-05-07 evening / 2026-05-08 — see `case_005_validation.md`
> for the 13-check report. Verdict: PASS WITH NOTES.
>
> **A2 advisor LANDED 2026-05-08 (commit `a09ae0a`)** — D1 now
> exercises landed `virtual_interface_detector` (first field
> validation on compressible-internal topology); D2 exercises
> landed A3 `geometry_surgery.decimate_to_tier` against
> 102,400-triangle industrial-flavored input (first real A3
> falsification opportunity).

---

=== BEGIN KICKOFF ===

You are a Claude Code sub-session under orchestration of the
cfd-harness-unified project. You are taking ONE industrial CFD
case as your task: **case_005_rae_m2129_sduct**. The project main
session is held in a separate Claude Code session and will harvest
your sediment after you complete (or pause) your work.

## Project context (read first)

cfd-harness-unified is a CFD harness over OpenFOAM at
`/Users/Zhuanz/Desktop/cfd-harness-unified/`. Per DEC-V61-198
(2026-05-07) the project is reframed as "a container that
accumulates industrial CFD experience" — each industrial case
extends coverage of a solver-class axis and feeds the V-series
finding index + RAG corpus.

Four cases already in the case fleet:
- case_002a (APU bay buoyantSimpleFoam, internal flow + buoyancy) — active
- case_002b (APU bay CHT, multi-region thermal coupling) — active
- case_003 (CRM-HLS, external high-Re + boundary layer) — dispatched
- case_004 (NREL Phase VI rotor, MRF) — dispatched

Your case fills the **internal compressible diffuser
(subsonic-transonic)** row — currently uncovered.
**case_005 is the FIRST compressible case for the project AND
the FIRST case to exercise a LANDED advisor end-to-end** (D2 →
A3 `geometry_surgery.decimate_to_tier` against 102,400-triangle
industrial-flavored input — first real falsification opportunity).

You are NOT here to ship a generic feature. You are here to:
1. Run case_005 end-to-end in its desktop sandbox
2. Produce sediment artifacts in the format the main session expects
3. Surface and document new failure modes (V-series candidates,
   especially compressible-RANS-specific)
4. Verify Codex's injected defects against main-project advisors —
   D1 against landed A2 (`virtual_interface_detector`) AND
   D2 against landed A3 (`geometry_surgery.decimate_to_tier`,
   real falsification on 102,400-triangle overlay)
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
   V-series; **note**: your case is `compressible-RANS` numerics
   class. Per Pattern 6, you inherit NO V3-V13/V15 (compressible-
   buoyant-RANS), NO incompressible-RANS findings (case_003), NO
   MRF findings (case_004). Pure new numerics root. Source net-new
   V-findings (likely V20+ depending on case_003/004 sequencing)
5. `.planning/methodology/solver_convergence_playbook.md` —
   S1-S12 decision tree; consult when convergence stalls.
   compressible-RANS-specific patterns will likely become S13+
6. `.planning/methodology/rag_corpus_format.md` — the 5 artifacts
   your case-thread must produce
7. `~/Desktop/apu-bay-ventilation/` — case_002a actual sandbox.
   Mirror its structure: `inputs/`, `config/case.yaml`,
   `templates/`, `scripts/01..11`, `case/`, `evidence/`. The
   numbered-script + Jinja2 + SSOT YAML pattern is canonical
8. `.planning/methodology/kickoff/case_005_codex_response.md` —
   **Codex's full case design** (your starting point — 5
   deliverables: brief + CAD script + STEP path + parts manifest +
   defect manifest)
9. `.planning/methodology/kickoff/case_005_validation.md` — main
   session's 13-check validation (A3 falsification + URL HTTP 500
   caveat)
10. `.planning/cross_cuts/v_series_2026-05-08.md` — current
    V-series snapshot; note A2 advisor LANDED row (your case_005
    D1 row is one of 8 cases waiting for field validation; D2 is
    first A3 industrial validator)

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
   - `from ui.backend.services.geometry_ingest.geometry_surgery
     import decimate_to_tier, axial_stretch, apply_surgery`
     — **mandatory exercise** for D2's 102,400-triangle overlay
   - `from ui.backend.services.geometry_ingest.virtual_interface_detector
     import detect_virtual_interfaces, InterfaceSpec` (for D1 — A2
     LANDED 2026-05-08, commit a09ae0a)
   - `from ui.backend.services.geometry_ingest.thin_wall_advisor
     import detect_thin_wall_patches_at_risk` — not directly
     exercised by case_005 (no thin-wall defect), but useful if
     the throat liner gets extruded thinly during decimation
   - DO NOT re-implement these case-locally
7. **Do NOT redesign the case** — Codex's brief is your starting
   point; if you find the design fundamentally unworkable, flag
   in your final report under "Main session attention required"
   and pause; main session asks Codex for revision (round-cap=2)
8. **Mach ceiling = 1.3 strong-shock limit**: case_005 is
   subsonic-transonic (AIP Mach 0.40-0.60, throat 0.70-0.78). If
   your run produces a strong normal shock (M>1.3) with separation,
   that's a case_006 (compressible-shock-density-based) regime,
   not case_005. Reduce p_back if needed to stay subsonic.

## Your case-specific assignment

### Case identifier

`case_005_rae_m2129_sduct`

### Solver class + numerics class

- Solver class (coverage map row): **internal compressible
  diffuser (subsonic-transonic)**
- Numerics class (Pattern 6): **compressible-RANS** (root — no
  inheritance from prior cases)

### Codex's engineering brief (deliverable 1)

Read in full at
`.planning/methodology/kickoff/case_005_codex_response.md` §
"Deliverable 1 — Engineering brief". Summary:

- **Component**: RAE M2129 circular S-duct intake diffuser
  (canonical UAV / cruise missile intake reference). Throat
  diameter 128.5 mm, AIP diameter 152.4 mm, AIP at x=489.458 mm,
  duct offset 137.16 mm
- **Source**: Tier-1 NASA Glenn `WWW/wind/valid/sduct/sduct02/`
  (validation archive); NTRS `citations/20040021333` durable
  fallback. **NOTE**: GRC URLs returned HTTP 500 at validation
  time (likely transient). Script doesn't depend on URL —
  geometry baked into constants
- **Engineering question**: "Can the harness ingest a
  rotating-machinery — wait, internal compressible — STEP,
  preserve named compressible BC patches (totalPressure /
  waveTransmissive / totalTemperature), configure rhoSimpleFoam
  + perfectGas thermophysics correctly, and produce physically
  sane DC60 distortion + recovery PR for the M2129 reference
  while detecting D1 sub-mm flange gap and D2 102,400-triangle
  throat-wall overlay before meshing?"
- **Physics**:
  - Solver v1: `rhoSimpleFoam` (steady compressible)
  - v2 fallback: `rhoPimpleFoam` ONLY if oscillatory residuals
  - Turbulence: kOmegaSST
  - Thermophysics: perfectGas, γ=1.4, R=287.05, Cp=1004.5,
    Pr=0.72, μ_ref=1.79e-5 Pa·s, T_ref=288 K
  - Reference conditions: p_total_inlet=101325 Pa,
    T_total_inlet=288 K, p_back=85000 Pa (PR=0.839)
  - Target throat Mach 0.70-0.78; AIP Mach 0.40-0.60
  - Subsonic-transonic; weak normal shock OK; M>1.3 = stop and
    reduce PR
- **Expected metrics**: AIP Mach map, total pressure recovery PR,
  **DC60 distortion coefficient**, centerline static pressure,
  mass-flow balance, residual + density/temperature bounds,
  advisor detection results for D1 and D2
- **Estimated effort**: 5-8 hours, ~3 versions

### Codex's CAD generation script (deliverable 2)

Located in Codex response. Save it to your sandbox at
`scripts/build_cad.py`. It (425 LOC):
- Defines RAE M2129 centerline (S-shape with smoothstep
  transition between inlet, throat, and AIP) and radius profile
  (throat → AIP expansion)
- Builds `stationary_domain` as the duct + outlet plenum fluid
  volume
- Builds `duct_wall_reference` as the primary S-duct wall
- Builds `inlet`, `outlet` as planar faces with correct normals
- Builds `aip_plane_marker` as exterior annular ring (does NOT
  block flow volume — actual AIP analysis uses `cutting_planes.AIP`)
- Builds D1 defect: `inlet_flange_ring` and `inlet_flange_cover`
  separated by `DEFECT_GAP_MM = 0.35` axially
- Builds D2 defect: `throat_liner_overdense` as 102,400-triangle
  wall overlay (offset 0.15 mm into solid, not on centerline)
- Canonicalizes STEP header for byte-identical regeneration

**Install requirement**: cadquery is NOT in the main project venv.
Your sandbox needs its own venv:

```bash
cd ~/Desktop/case_005_rae_m2129_sduct
python3 -m venv .venv
.venv/bin/pip install cadquery numpy pyyaml jinja2 trimesh
```

### Codex's STEP file path (deliverable 3)

Output target:
`/Users/Zhuanz/Desktop/case_005_rae_m2129_sduct/inputs/cad_codex_v1.step`

Run the script with:
```bash
python scripts/build_cad.py --out inputs/cad_codex_v1.step
```

URL fetching is best-effort and can be skipped (no
`--require-reference-cache` flag mentioned for this case).

### Codex's parts manifest (deliverable 4)

Save at `inputs/parts_manifest.yaml` per Codex's spec — 8 parts +
1 cutting plane (AIP). Includes:
- `thermophysics:` block (perfectGas constants)
- `reference_conditions:` block (p_total, T_total, p_back, Mach
  targets)
- `geometry_reference:` block (throat / AIP / duct offset)
- `cutting_planes.AIP` (DC60 + recovery + Mach map at x=489.458 mm)
- Per-patch `bc:` with U / p / T / mut / alphat / k / omega
- `postprocessing.required_metrics:` includes DC60 + recovery PR

Use as input for `08_write_bcs.py` AND new
`08b_write_thermophysical.py` (you'll need this for case_005 —
see below).

### Codex's defect manifest (deliverable 5)

Save at `inputs/defect_manifest.yaml`. Two defects:
- **D1**: 0.35 mm gap between `inlet_flange_ring` and
  `inlet_flange_cover` on external inlet flange (upstream of
  throat, away from AIP). Verification: FreeCAD `distToShape`
- **D2**: `throat_liner_overdense` body with `expected_face_count:
  102400`. Verification: FreeCAD `len(Shape.Faces)`. **First case
  to exercise A3 advisor on industrial-flavored over-dense input**

`protected_reference_zones:` block explicitly forbids defects on
centerline or within ±5 mm of AIP.

## Compressible-RANS-specific work (case_005 unique territory)

The main project has **no prior compressible BC writer or
thermophysical writer**. You will hand-craft these case-locally
first; main session harvest cycle will decide what to extract:

### thermophysicalProperties writer

Add `scripts/08b_write_thermophysical.py` consuming the parts
manifest's `thermophysics:` block, emitting `case/constant/
thermophysicalProperties`:

```
thermoType
{
    type            hePsiThermo;
    mixture         pureMixture;
    transport       sutherland;     // or const if μ_ref + S
    thermo          hConst;          // or janaf
    equationOfState perfectGas;
    specie          specie;
    energy          sensibleInternalEnergy;
}

mixture
{
    specie
    {
        molWeight   28.96;
    }
    thermodynamics
    {
        Cp          1004.5;
        Hf          0;
    }
    transport
    {
        As          1.4584e-06;     // Sutherland
        Ts          110.4;          // Sutherland
        // OR mu/Pr if 'const'
    }
}
```

### Compressible BC writer (totalPressure / waveTransmissive /
totalTemperature / inletOutlet)

Extend `scripts/08_write_bcs.py` (or add `08c_write_compressible_bcs.py`)
to emit:
- `0/p` with `totalPressure` BC at inlet (`p0 101325`,
  `value uniform 101325`) and `waveTransmissive` at outlet
  (`gamma 1.4`, `psi thermo:psi`, `fieldInf 85000`,
  `lInf 1.0` or larger; primary plan, fallback to `fixedValue
  uniform 85000`)
- `0/T` with `totalTemperature` at inlet (`T0 288`,
  `psi thermo:psi`, `gamma 1.4`) and `inletOutlet` at outlet
  (`inletValue 288`)
- `0/U` with `pressureInletOutletVelocity` at inlet,
  `zeroGradient` at outlet
- `0/k`, `0/omega`, `0/mut`, `0/alphat` with appropriate wall
  functions

If templates/0.orig.j2 doesn't support compressible thermo
fields, this is a **stale-assumption candidate** — fix in place.
Commit message tag `corrects-assumption: 0orig-compressible-fields,
surfaced-by: case_005-V<n>`.

### DC60 post-processor

Add `scripts/10b_compute_dc60.py`:
1. Use ParaView (or pyvista) to slice the AIP plane at x=489.458 mm
2. Sample total pressure p0 = p + 0.5·ρ·|U|² over the AIP disk
3. Compute area-averaged p0_AIP_avg
4. Sweep azimuthal sectors of 60° width at every 1° azimuth, find
   the sector with lowest area-averaged p0
5. DC60 = (p0_AIP_avg - p0_worst60deg) / q_AIP_avg
6. Emit `evidence/<v>/dc60.txt` with value + sector position

Reference target for RAE M2129 at PR=0.839 typically DC60 ~ 0.10-
0.20 depending on operating point.

### A3 advisor falsification (the high-value part)

Before sub-session runs sHM, exercise main-project A3 against the
102,400-triangle overlay:

```python
import sys
sys.path.insert(0, "/Users/Zhuanz/Desktop/cfd-harness-unified")
from ui.backend.services.geometry_ingest.geometry_surgery import (
    decimate_to_tier, axial_stretch, apply_surgery
)
import trimesh

mesh = trimesh.load(
    "/Users/Zhuanz/Desktop/case_005_rae_m2129_sduct/inputs/cad_codex_v1.step",
    # ... use trimesh's STEP→STL conversion or load from generated STL
)
# Filter to throat_liner_overdense body
overdense = filter_body(mesh, "throat_liner_overdense")
print(f"original face count: {len(overdense.faces)}")  # expect ~102400

decimated = decimate_to_tier(overdense, target_tier="medium")
print(f"decimated face count: {len(decimated.faces)}")

# Falsification questions:
# 1. Does decimate_to_tier reduce ~100k → ~10k without breaking
#    the wall geometry?
# 2. Does it preserve the cylindrical near-throat curvature, or
#    over-flatten?
# 3. Does it issue any warning when input is "redundant overlay"
#    (offset 0.15 mm INTO solid side) — i.e., does the advisor
#    recognize geometric redundancy?
```

If A3 fails any of the above, that's a real V-finding tagged
"A3 toy-case bias surfaced by case_005 industrial CAD". Document
in your final report under "main-project advisor blind spots"
and propose a fix (or hand off to main session).

If A3 passes cleanly, document as "A3 advisor first industrial
falsification: PASS" — that's also valuable.

## Defect verification protocol (extra step for Codex-designed cases)

Before running the CFD pipeline, verify defects:

### D1 verification — A2 advisor LANDED, USE IT

A2 advisor extracted to main project 2026-05-08 (commit `a09ae0a`).
You are among the first sub-sessions to exercise it on a real
industrial case. Treat your run as **field validation**.

> [QUESTIONABLE 2026-05-08]: "exercise A2; expect detection of
> 0.35 mm gap" framing assumes a capability A2 v1 does NOT have.
> A2 LANDED for V2 pattern (shared-interface confirmation on
> non-manifold STEP), NOT D1 pattern (gap-as-defect detection).
> Per V25 (open · `industrial_case_solver_findings.md#V25` —
> sourced by THIS case's v2 disambiguation), A2's `_run_shared`
> returns `matched=True` with hardcoded placeholder fields
> regardless of actual gap distance. case_005 v1+v2 falsification
> already complete (V19 superseded by V25, V21 closed via
> `_run_shared` re-run). v3 of this case re-runs A2 falsification
> via A2-v2 API once it lands (drafted at
> `.planning/patches/draft_a2_v2_gap_detection_2026-05-08.md`).
> To resolve: A2-v2 lands AND case_005 v3 confirms `inter_face_gap_mm
> ≈ 0.35` AND classifier returns True. Until then, your previous
> A2 PASS confirms only that `_run_shared` runs cleanly + finds
> facing-face candidates on flange-ring axial-end faces.

**Step 1 — manual ground truth via FreeCAD**:

```bash
FreeCADCmd -c "import FreeCAD as App, Import; \
  doc=App.newDocument(); \
  Import.insert('/Users/Zhuanz/Desktop/case_005_rae_m2129_sduct/inputs/cad_codex_v1.step', doc.Name); \
  o={x.Label:x for x in doc.Objects}; \
  print(o['inlet_flange_ring'].Shape.distToShape(o['inlet_flange_cover'].Shape)[0])"
```

Expected: ≈ 0.35 mm. Report actual measured value.

**Step 2 — exercise landed A2 advisor**:

```python
import sys
sys.path.insert(0, "/Users/Zhuanz/Desktop/cfd-harness-unified")
from ui.backend.services.geometry_ingest.virtual_interface_detector import (
    detect_virtual_interfaces, InterfaceSpec, FaceGeometry, BodyGeometry,
)
# Build BodyGeometry for inlet_flange_ring and inlet_flange_cover
# from STEP face extraction (FreeCAD or trimesh). Each face needs:
#   area, bbox_min, bbox_max, normal, centroid (case units, meters).
spec = InterfaceSpec(
    name="inlet_flange_ring__inlet_flange_cover_interface",
    mode="shared",
    bodies=("inlet_flange_ring", "inlet_flange_cover"),
)
result = detect_virtual_interfaces(bodies=[ring_body, cover_body],
                                   specs=[spec])
# Expect: result contains 1 DetectedInterface with the two facing
# faces despite isSame() failing on the BREP (V2 lesson).
```

**Step 3 — V-finding judgments**:

- If A2 detects → upgrade V2 / case_005 row in
  `industrial_case_solver_findings.md` from "advisor landed" to
  "advisor field-validated on case_005 (compressible-internal
  topology)"
- If A2 misses (false negative) → V_n finding "A2 advisor
  toy-case bias on circular-flange face counts" + propose
  threshold tuning sub-DEC
- If A2 produces extra spurious matches (false positive) → V_n
  finding "A2 advisor over-eager on adjacent-but-not-shared
  faces in flange topology" + propose `mode='shared'` tightening

The advisor's docstring explicitly forbids `isSame()` fast-path —
do NOT propose adding one (V2 lesson preserved).

### D2 verification

```bash
FreeCADCmd -c "import FreeCAD as App, Import; \
  doc=App.newDocument(); \
  Import.insert('/Users/Zhuanz/Desktop/case_005_rae_m2129_sduct/inputs/cad_codex_v1.step', doc.Name); \
  o={x.Label:x for x in doc.Objects}; \
  print(len(o['throat_liner_overdense'].Shape.Faces))"
```

Expected: ≈ 102,400. Report actual measured value (Codex's
generation may produce ±5% due to STEP→Faces translation).

Then exercise A3 advisor (see "A3 advisor falsification" above).

## Six per-case standard moves (DEC-V61-198)

Execute these as your work plan:

1. **Reference profile**: write
   `.planning/case_profiles/case_005_rae_m2129_sduct.md` in the
   main repo with the structure of case_002a/b
2. **V-series append**: every NEW failure mode goes in
   `industrial_case_solver_findings.md` as V_n. Watch for:
   - **A2 advisor field-behavior on compressible-internal
     topology** (above three-branch decision tree)
   - **A3 advisor first industrial falsification** (above)
   - `totalPressure` inlet BC initialization that diverges if
     phi (mass flux) starts unfavorable
   - `waveTransmissive` outlet causing pressure waves to bounce
     back into duct (set `lInf` to ≥ 5x duct length)
   - kOmegaSST under-prediction of S-duct secondary flow
   - sHM cellZone-equivalent for compressible internal flow
     (hex-dominant in straight sections, polyhedral near bends)
   - DC60 sector-sweep numerical stability (ParaView slice
     area-average vs custom Python quadrature)
3. **Playbook tree append**: compressible-RANS-specific patterns
   become S13+ in `solver_convergence_playbook.md`. Likely
   candidates:
   - "Total pressure inlet diverging in first iteration → start
     with low PR, ramp up over 200 iterations"
   - "waveTransmissive pressure-wave bounce → increase lInf or
     fall back to fixedValue"
   - "Density residual blows up while pressure converges → check
     thermophysical Cp / R consistency"
4. **Stale-assumption falsification**: case_005 will likely
   surface main-project assumptions that don't apply to
   compressible (sHM template may not support compressible
   thermo, 0.orig template may be incompressible-only). Fix in
   place. Commit message tag `corrects-assumption: <X>,
   surfaced-by: case_005-V<n>`
5. **Artifact extraction**: most likely candidates this case:
   - `compressible_bc_writer.py` (totalPressure /
     waveTransmissive / totalTemperature / inletOutlet)
   - `compressible_thermophysical_writer.py` (perfectGas +
     sutherland/const + hConst/janaf)
   - `dc60_post_processor.py` (AIP slice + sector sweep)
   These are M3-M5 advisor territory and valuable for case_006+
6. **RAG corpus injection**: produce the 5 artifacts per
   `rag_corpus_format.md` (reference profile + case.yaml +
   per-version run logs + final report + decision log)

## Your sandbox structure

Create at `~/Desktop/case_005_rae_m2129_sduct/`. Mirror case_002a
layout, plus compressible-specific scripts:

```
~/Desktop/case_005_rae_m2129_sduct/
├── README.md                        ← case-thread overview
├── Makefile                         ← `make all` runs full pipeline
├── .venv/                           ← case-local venv with cadquery
├── config/
│   └── case.yaml                    ← SSOT (includes thermophysics block)
├── inputs/
│   ├── cad_codex_v1.step            ← generated by build_cad.py
│   ├── parts_manifest.yaml          ← from Codex deliverable 4
│   ├── defect_manifest.yaml         ← from Codex deliverable 5
│   └── cache/                       ← optional cached NASA tarball
├── templates/                       ← Jinja2 for OpenFOAM dicts
│   ├── thermophysicalProperties.j2  ← NEW for case_005
│   ├── 0.orig.j2                    ← may need compressible-field
│   │                                    extension
│   └── ...
├── scripts/
│   ├── _lib.py                      ← shared helpers
│   ├── build_cad.py                 ← from Codex deliverable 2
│   ├── 01_validate_cad.py           ← STEP import + body name check
│   ├── 02_verify_defects.py         ← D1+D2 verification + A3 advisor
│   ├── 03_validate_stl.py           ← multi-solid STL → harness loader
│   ├── 04_scaffold_case.py          ← case/ directory tree
│   ├── 05_make_dicts.py             ← Jinja2 → all OpenFOAM dicts
│   ├── 06_run_mesh.sh               ← Docker: blockMesh + sHM
│   ├── 07_check_mesh.py             ← harness checkmesh + advisor
│   ├── 08_write_bcs.py              ← BC writer per parts manifest
│   ├── 08b_write_thermophysical.py  ← NEW: thermophysicalProperties
│   ├── 08c_write_compressible_bcs.py ← NEW: compressible field BCs
│   ├── 09_run_solver.sh             ← Docker: rhoSimpleFoam
│   ├── 10_post.py                   ← ParaView slices + Cp + recovery
│   ├── 10b_compute_dc60.py          ← NEW: DC60 distortion coefficient
│   └── 11_audit.py                  ← signed evidence pack
├── case/                            ← OpenFOAM runtime (gitignored)
└── evidence/<version>/              ← per-version reports
    ├── REPORT.md
    ├── dc60.txt                     ← from 10b_compute_dc60.py
    └── a3_falsification.md          ← A3 advisor exercise outcome
```

Do NOT commit `case/` runtime contents to main repo.

## Sediment-back protocol

When you complete (or pause):

1. Reference profile up to date in main repo
2. V-series rows added to `industrial_case_solver_findings.md`
   (especially A2 + A3 field-validation rows + compressible-RANS-
   specific findings — high-value sediment, you are first
   compressible sub-session AND first A3 industrial validator)
3. Any new playbook patterns added to
   `solver_convergence_playbook.md`
4. `case_index.md` updated (your row's status + last-touch)
5. Stale-assumption fixes as separate commits
6. Extracted artifacts as separate sub-DEC-scope commits
7. `case_proposal_queue.md` "Dispatched" → "In-flight" → "Closed"
   row movement
8. Final report at `evidence/<final_version>/REPORT.md`
9. **A3 falsification report**: prominent "PASS / PARTIAL / FAIL"
   verdict in final report. If FAIL, hand off to main session for
   advisor refactor

Commit messages NOT to mention being an AI:
```
chore(case_005): v<N> · <short summary>

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
  compressible BC writer promotion to shared service) →
  hand-craft case-locally, document the gap, flag for
  main-session extraction (counter for harvester)
- Codex's design fundamentally unworkable → pause, flag, main
  session asks Codex for revision (round-cap=2)

## Boundaries

You CAN:
- Run case_005 commands end-to-end
- Modify your sandbox files freely
- Commit to main repo for sediment artifacts
- Extract small reusable artifacts (<250 LOC) when forced
- Fix toy-case-biased thresholds discovered in main-project
  advisors (especially A3 if your falsification surfaces a gap)
- Add compressible thermo support to 0.orig template if main
  project lacks it (compressible RANS forces this — flag as
  `corrects-assumption`)

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
(`case_005_validation.md`):

1. **A3 (geometry_surgery) FIRST industrial exercise** — D2's
   102,400-triangle overlay is the first non-toy input. Outcome
   shapes whether A3 needs refactor or stays as-is. Document
   verdict prominently
2. **NASA Glenn URL HTTP 500** — `grc.nasa.gov` archive transient
   failure at validation time. NTRS `citations/20040021333` is
   durable fallback. Script doesn't depend on URL — geometry
   parametric
3. **First compressible case for project** — no prior
   thermophysicalProperties writer, no totalPressure /
   waveTransmissive BC writer, no DC60 post-processor. Hand-craft
   case-locally; main session decides extraction priority
4. **Mach ceiling = 1.3** — if your run produces strong shocks
   (M>1.3) with separation, that's case_006 territory; reduce PR
   to stay in case_005 envelope
5. **D2 face count tolerance** — 102,400 ±5% is acceptable due
   to STEP→Faces translation noise; flag if Codex's claimed
   number is off by >10%
6. **A2 advisor JUST landed** (commit `a09ae0a`, 2026-05-08) —
   you are among first industrial validators on D1; expect
   threshold-tuning sub-DEC candidate to surface from your run

=== END KICKOFF ===

---

## Main session post-dispatch checklist

After user pastes the kickoff into a new Claude Code session:

- [ ] Update `case_proposal_queue.md` — move case_005 row from
      "Active queue (proposed)" to "Dispatched"
- [ ] Update `case_index.md` — add case_005 row, status = "dispatched"
- [ ] Update `INDEX.md` — bump kickoff list to include case_005
- [ ] Wait for sub-session sediment in subsequent main-session
      turns
- [ ] When sub-session reports A2 field-validation outcome
      (validated / false-negative / false-positive on
      compressible-internal topology), update
      `industrial_case_solver_findings.md` V2 row + queue any
      threshold-tuning sub-DEC for harvest cycle
- [ ] When sub-session reports A3 falsification verdict, decide
      whether A3 refactor is needed or A3 stays as-is
- [ ] When sub-session extracts compressible-BC / thermophysical /
      DC60 infrastructure, evaluate for promotion to main-project
      shared services (case_006 will benefit from compressible-BC
      writer)
