# Case 006 · ONERA M6 Transonic · Sub-Session Kickoff (paste-ready)

> **Paste the section between `=== BEGIN KICKOFF ===` and
> `=== END KICKOFF ===` into a fresh Claude Code session as the
> first message.**
>
> Designed by Codex (CRS gpt-5.4 high effort, fallback path —
> 86gs gpt-5.5 xhigh primary 503'd twice). Validated by main
> session 2026-05-08 — see `case_006_validation.md` for the
> 13-check report. Verdict: PASS WITH NOTES (A2 advisor pending —
> 4th consecutive case; D4 advisor mapping likely wrong, sub-session
> exercises judgment; NASA Glenn URL HTTP 500 persistent).

---

=== BEGIN KICKOFF ===

You are a Claude Code sub-session under orchestration of the
cfd-harness-unified project. You are taking ONE industrial CFD
case as your task: **case_006_onera_m6_transonic**. The project
main session is held in a separate Claude Code session and will
harvest your sediment after you complete (or pause) your work.

## Project context (read first)

cfd-harness-unified is a CFD harness over OpenFOAM at
`/Users/Zhuanz/Desktop/cfd-harness-unified/`. Per DEC-V61-198
(2026-05-07) the project is reframed as "a container that
accumulates industrial CFD experience" — each industrial case
extends coverage of a solver-class axis and feeds the V-series
finding index + RAG corpus.

Five cases already in the case fleet:
- case_002a (APU bay buoyantSimpleFoam, internal flow + buoyancy) — active
- case_002b (APU bay CHT, multi-region thermal coupling) — active
- case_003 (CRM-HLS, external high-Re + boundary layer, incompressible-RANS) — dispatched, deferred
- case_004 (NREL Phase VI rotor, MRF, incompressible-RANS-MRF) — dispatched, deferred
- case_005 (RAE M2129 S-duct, internal compressible diffuser, compressible-RANS / rhoSimpleFoam) — dispatched, deferred

Your case fills the **external transonic 3D wing
(compressible high-speed, shock-capturing)** row — currently
uncovered. After you complete, the project's solver-class
coverage advances by one axis. **case_006 is the first
density-based solver case for the project** (vs case_005's
pressure-based rhoSimpleFoam).

You are NOT here to ship a generic feature. You are here to:
1. Run case_006 end-to-end in its desktop sandbox
2. Produce sediment artifacts in the format the main session expects
3. Surface and document new failure modes (V-series candidates,
   especially compressible-shock-density-based-specific —
   lambda-shock capture, limiter calibration, characteristic-BC
   far-field treatment)
4. Verify Codex's injected defects against main-project advisors,
   exercising **judgment on the D4 advisor mapping** (Codex
   pointed at A3 geometry_surgery, but a sliver may be better
   caught by A1 thin_wall_advisor — try both)
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
   V-series; **note**: your case is `compressible-shock-density-based`
   numerics class. Per Pattern 6, you inherit NO V3-V13/V15
   (compressible-buoyant-RANS), NO incompressible-RANS findings
   (case_003), NO MRF findings (case_004), NO pressure-based
   compressible-RANS findings (case_005). Pure new numerics root.
   Source net-new V-findings
5. `.planning/methodology/solver_convergence_playbook.md` —
   S1-S12 decision tree; consult when convergence stalls.
   density-based-specific patterns will likely become S13+
6. `.planning/methodology/rag_corpus_format.md` — the 5 artifacts
   your case-thread must produce
7. `~/Desktop/apu-bay-ventilation/` — case_002a actual sandbox.
   Mirror its structure: `inputs/`, `config/case.yaml`,
   `templates/`, `scripts/01..11`, `case/`, `evidence/`. The
   numbered-script + Jinja2 + SSOT YAML pattern is canonical
8. `.planning/methodology/kickoff/case_006_codex_response.md` —
   **Codex's full case design** (your starting point — 5
   deliverables: brief + CAD script + STEP path + parts manifest +
   defect manifest)
9. `.planning/methodology/kickoff/case_006_validation.md` — main
   session's validation notes (especially CRS fallback context +
   D4 advisor mapping caveat + 4-of-4 A2-pending compounding +
   NASA Glenn URL HTTP 500)

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
     import detect_thin_wall_patches_at_risk` — **try first** for
     D4's 0.18 mm sliver (likely correct advisor)
   - `from ui.backend.services.geometry_ingest.geometry_surgery
     import decimate_to_tier, axial_stretch, apply_surgery` —
     try second per Codex's (likely incorrect) mapping;
     mismatch is a useful V-finding
   - DO NOT re-implement these case-locally
7. **Do NOT redesign the case** — Codex's brief is your starting
   point; if you find the design fundamentally unworkable, flag
   in your final report under "Main session attention required"
   and pause; main session asks Codex for revision (round-cap=2)
8. **Mach regime ceiling**: M_inf = 0.8395 ± 0.005, α = 3.06° ± 0.1°.
   If you push α above 6° or M_inf above 0.95, that's case_010 LES
   territory — stop and flag
9. **Don't bypass the lambda-shock check**: case_006's primary
   engineering question is whether the lambda shock pattern at
   η=0.65-0.95 is captured. v1 may not get it; v2 limiter tuning
   should. If v3 still doesn't show lambda shock with reasonable
   refinement, that's a real V-finding about rhoCentralFoam's
   limits — document it

## Your case-specific assignment

### Case identifier

`case_006_onera_m6_transonic`

### Solver class + numerics class

- Solver class (coverage map row): **external transonic 3D wing
  (compressible high-speed, shock-capturing)**
- Numerics class (Pattern 6): **compressible-shock-density-based**
  (root — no inheritance from prior cases)

### Codex's engineering brief (deliverable 1)

Read in full at
`.planning/methodology/kickoff/case_006_codex_response.md` §
"Deliverable 1 — Engineering brief". Summary:

- **Component**: ONERA M6 wing (canonical transonic CFD validation
  reference, AGARD AR-138 / Schmitt-Charpin 1979). Half-wing,
  span 1196.3 mm, root chord ~806 mm, taper 0.562, LE sweep 30°,
  no twist, ONERA D-section airfoil. Geometry from NASA Glenn
  archive (URL HTTP 500 — see Known issues)
- **Source**: Tier-1 T1.A3 NASA Glenn `WWW/wind/valid/m6wing/`
  (geometry baked into CadQuery script as constants — script
  doesn't actually fetch URLs)
- **Engineering question**: "Can the harness preserve and mesh a
  real transonic wing geometry, run a density-based shock-
  capturing solver, and recover the ONERA M6 lambda-shock pattern
  and spanwise Cp distributions at the published seven stations?"
- **Physics**:
  - Solver v1: `rhoCentralFoam` (Kurganov central-upwind)
  - v2 fallback: `rhoPimpleFoam` ONLY if Kurganov over-smoothes
    the lambda shock
  - Turbulence: kOmegaSST (compressible variant)
  - Freestream: M_inf=0.8395, α=3.06°, Re=11.72e6,
    T_inf=288 K, p_inf=93.6 kPa, T0=328.5 K, p0=148.4 kPa,
    ρ_inf=1.133 kg/m³, U_inf=285.6 m/s
  - Regime: transonic external RANS, upper-surface local supersonic
    pocket, lambda shock around η=0.65-0.95, shock/BL interaction
- **Expected metrics**: Cp(x/c) at 7 published η stations,
  Cl/Cd/Cm, max upper-surface Mach, lambda-shock map at η=0.65 +
  η=0.95, shock-foot x/c, max |∂M/∂n|, spanwise shock migration
- **Estimated effort**: 6-9 hours, ~3 versions

### Codex's CAD generation script (deliverable 2)

Located in Codex response. Save it to your sandbox at
`scripts/build_cad.py`. It (356 LOC):
- Lofts wing surface from chord/twist/sweep parametric stations
  (ONERA D-section airfoil coordinates baked in)
- Separates `tip_cap` (the 3D rounded end) from main wing
  surface so the D4 sliver lives outside published Cp stations
- Builds 5-face farfield box (upstream / downstream / top /
  bottom / outboard)
- Defines `symmetry_plane_root` as planar face at y=0
- Builds D1: `root_fairing_pad` and `root_fairing_cover`
  separated by 0.35 mm gap (below η=0.20, away from Cp stations)
- Builds D4: `tip_cap_sliver` at tip-cap edge (0.18 mm sliver
  body, outside η=0.99 station)
- Canonicalizes STEP header for byte-identical regeneration

**Install requirement**: cadquery is NOT in the main project venv.
Your sandbox needs its own venv:

```bash
cd ~/Desktop/case_006_onera_m6_transonic
python3 -m venv .venv
.venv/bin/pip install cadquery numpy pyyaml jinja2 trimesh
```

**Verification task during v1**: confirm the D-section airfoil
coordinates baked into `S_DSECTION_COORDS` (or equivalent) match
AGARD AR-138 Appendix. If coordinates differ by >0.5% at any
x/c station, lambda-shock pattern may be displaced — flag as
geometry-fidelity V-finding.

### Codex's STEP file path (deliverable 3)

Output target:
`/Users/Zhuanz/Desktop/case_006_onera_m6_transonic/inputs/cad_codex_v1.step`

Run the script with:
```bash
python scripts/build_cad.py --out inputs/cad_codex_v1.step
```

URL fetching not required (geometry parametric).

### Codex's parts manifest (deliverable 4)

Save at `inputs/parts_manifest.yaml` per Codex's spec — 12 parts
including 5-face farfield, plus `freestream:`,
`geometry_reference:`, `validation_stations:`, `numerics_hints:`,
`shock_detection:` blocks.

Use as input for `08_write_bcs.py` AND new
`08b_write_density_fvschemes.py` (you'll need this for case_006 —
see below).

### Codex's defect manifest (deliverable 5)

Save at `inputs/defect_manifest.yaml`. Two defects:
- **D1**: 0.35 mm gap between `root_fairing_pad` and
  `root_fairing_cover` near root symmetry (below η=0.20).
  Verification: FreeCAD `distToShape`. Same A2-pending advisor
  caveat as case_003/004/005
- **D4**: 0.18 mm sliver `tip_cap_sliver` on tip-cap edge.
  Verification: FreeCAD `BoundBox.min`. Codex pointed at
  geometry_surgery; sub-session should also try thin_wall_advisor
  (likely correct)

`protected_reference_zones:` block explicitly forbids defects on
any of the 7 Cp stations or the wing upper/lower surfaces.

## Density-based-specific work (case_006 unique territory)

The main project has **no prior density-based fvSchemes writer
or characteristic-BC family writer**. You will hand-craft these
case-locally first; main session harvest cycle will decide what
to extract:

### Density-based fvSchemes writer

Add `scripts/08b_write_density_fvschemes.py` consuming the parts
manifest's `numerics_hints:` block, emitting `case/system/fvSchemes`:

```
ddtSchemes
{
    default         localEuler;
}

gradSchemes
{
    default         Gauss linear;
}

divSchemes
{
    default                         none;
    div(phi,U)                      Gauss linearUpwind grad(U);
    div(phid,p)                     Gauss linearUpwind default;
    div(phi,K)                      Gauss linearUpwind default;
    div(phi,h)                      Gauss linearUpwind default;
    div(phi,k)                      Gauss upwind;
    div(phi,omega)                  Gauss upwind;
    div(((rho*nuEff)*dev2(T(grad(U))))) Gauss linear;
}

fluxScheme      Kurganov;

interpolationSchemes
{
    default         linear;
    reconstruct(rho)        Minmod;     // or vanLeer / venkatakrishnan
    reconstruct(U)          MinmodV;
    reconstruct(T)          Minmod;
}
```

### Characteristic-BC writer for compressible far-field

Extend `scripts/08_write_bcs.py` (or add `08c_write_characteristic_bcs.py`)
to emit:
- `0/p` with `characteristicPressureInletOutletPressure` on all
  5 farfield patches (`pInf 93600`, `T0 328.5`, etc.)
- `0/U` with `characteristicVelocityInletOutletVelocity`
  (`UInf (285.6 0 0)` rotated by α=3.06°)
- `0/T` with `freestream` (`freestreamValue uniform 288`)
- Wing/aux walls: noSlip / zeroGradient / zeroGradient
- Symmetry plane: `symmetry` for all U/p/T/k/omega/nut

If templates/0.orig.j2 doesn't support characteristic-BC family,
this is a **stale-assumption candidate** — fix in place. Commit
message tag `corrects-assumption: 0orig-characteristic-bc-family,
surfaced-by: case_006-V<n>`.

### Lambda-shock detector / Cp slice post-processor

Add `scripts/10b_compute_lambda_shock.py`:
1. Use ParaView (or pyvista) to slice the upper wing surface at
   η = 0.20, 0.44, 0.65, 0.80, 0.90, 0.95, 0.99
2. Sample Cp(x/c) along each slice
3. Compute Mach(x/c) along each upper-surface slice
4. Detect lambda pattern: forward shock x/c (where Cp recovers
   first), aft shock x/c (where Cp recovers second), separation
   distance, peak max Mach
5. Compare against AGARD AR-138 published Cp at each η
6. Emit `evidence/<v>/lambda_shock_report.md` with:
   - Cp overlay plots (computed vs AGARD) per η
   - Lambda-shock geometry (forward/aft x/c per η)
   - Max upper-surface Mach
   - Verdict: lambda-shock-CAPTURED / SMEARED / ABSENT

### Defect ↔ advisor exercise (case_006 specific)

**For D1 (0.35 mm gap)**: same as case_003/004/005. Manually
verify via FreeCAD distToShape. Document A2-pending — this is
**4th consecutive case** to surface this gap. Compounded
evidence for A2 extraction.

**For D4 (0.18 mm sliver)**: exercise BOTH advisors:

```python
import sys
sys.path.insert(0, "/Users/Zhuanz/Desktop/cfd-harness-unified")

# Primary attempt (likely correct per main session validation):
from ui.backend.services.geometry_ingest.thin_wall_advisor import (
    PatchGeometry, detect_thin_wall_patches_at_risk
)
warnings = detect_thin_wall_patches_at_risk(
    patches=[PatchGeometry(name="tip_cap_sliver",
                            bbox_dimensions=(slx, sly, 0.00018))],
    refinement_levels={"tip_cap_sliver": (1, 2)},
    background_cell_size=YOUR_BG_CELL_SIZE_METERS,
)
print("thin_wall_advisor:", warnings)
# Expected: 'critical' warning (0.18 mm < 2× cell size)

# Secondary attempt (per Codex's mapping, likely silent):
from ui.backend.services.geometry_ingest.geometry_surgery import (
    decimate_to_tier
)
import trimesh
sliver = trimesh.load_step("inputs/cad_codex_v1.step")
sliver = filter_body(sliver, "tip_cap_sliver")
result = decimate_to_tier(sliver, target_tier="medium")
print("geometry_surgery:", result.face_count, "(input:",
      sliver.face_count, ")")
# Expected: silent (small sliver, not over-dense)
```

**Three possible outcomes**:
1. Both fire → unlikely; both advisors aren't hardened for
   sliver geometry
2. thin_wall_advisor fires, geometry_surgery silent → expected;
   Codex's mapping is wrong but defect IS caught by an advisor
3. Both silent → real V-finding tagged "main-project advisor
   blind spot for sub-mm sliver bodies"; flag for A4 sliver-
   detector extraction

Document outcome in evidence/`v1`/d4_advisor_exercise.md.

## Defect verification protocol (extra step for Codex-designed cases)

Before running the CFD pipeline, verify defects:

### D1 verification

```bash
FreeCADCmd -c "import FreeCAD as App, Import; \
  doc=App.newDocument(); \
  Import.insert('/Users/Zhuanz/Desktop/case_006_onera_m6_transonic/inputs/cad_codex_v1.step', doc.Name); \
  o={x.Label:x for x in doc.Objects}; \
  print(o['root_fairing_pad'].Shape.distToShape(o['root_fairing_cover'].Shape)[0])"
```

Expected: ≈ 0.35 mm. Report actual measured value.

### D4 verification

```bash
FreeCADCmd -c "import FreeCAD as App, Import; \
  doc=App.newDocument(); \
  Import.insert('/Users/Zhuanz/Desktop/case_006_onera_m6_transonic/inputs/cad_codex_v1.step', doc.Name); \
  o={x.Label:x for x in doc.Objects}; \
  bb=o['tip_cap_sliver'].Shape.BoundBox; \
  print(min(bb.XLength, bb.YLength, bb.ZLength))"
```

Expected: ≈ 0.18 mm. Report actual measured value.

## Six per-case standard moves (DEC-V61-198)

Execute these as your work plan:

1. **Reference profile**: write
   `.planning/case_profiles/case_006_onera_m6_transonic.md` in
   the main repo with the structure of case_002a/b
2. **V-series append**: every NEW failure mode goes in
   `industrial_case_solver_findings.md` as V_n. Watch for:
   - Kurganov + venkatakrishnan limiter too dissipative for
     lambda shock (likely v1 finding)
   - Characteristic far-field BCs reflect pressure waves at
     <25 chord distance
   - Cold-start density/energy initialization overshoots at LE
   - kOmegaSST compressible variant under-predicts shock-induced
     separation
   - Symmetry plane treatment with characteristic BCs at
     intersection edges
3. **Playbook tree append**: density-based shock-capturing
   patterns become S13+ in `solver_convergence_playbook.md`.
   Likely candidates:
   - "Lambda shock smeared on first run → switch ρ/ρU/ρE
     reconstruction from venkatakrishnan to vanLeer or Minmod"
   - "Pressure-wave reflection visible in upper-surface Cp →
     extend farfield to ≥ 50 chords"
4. **Stale-assumption falsification**: case_006 will likely
   surface main-project assumptions that don't apply to
   density-based (sHM template, fvSchemes default ddt). Fix in
   place. Commit message tag `corrects-assumption: <X>,
   surfaced-by: case_006-V<n>`
5. **Artifact extraction**: most likely candidates this case:
   - `density_based_fvschemes_writer.py` (Kurganov + limiters
     + reconstruction)
   - `characteristic_farfield_bc_writer.py`
   - `lambda_shock_detector.py` (ParaView slice + Cp / Mach
     comparison vs AGARD)
   These are M3-M5 advisor territory; case_006 + future
   external-compressible cases benefit
6. **RAG corpus injection**: produce the 5 artifacts per
   `rag_corpus_format.md`

## Your sandbox structure

Create at `~/Desktop/case_006_onera_m6_transonic/`. Mirror
case_002a layout, plus density-based-specific scripts:

```
~/Desktop/case_006_onera_m6_transonic/
├── README.md                            ← case-thread overview
├── Makefile                             ← `make all` runs full pipeline
├── .venv/                               ← case-local venv with cadquery
├── config/
│   └── case.yaml                        ← SSOT (includes freestream + numerics)
├── inputs/
│   ├── cad_codex_v1.step                ← generated by build_cad.py
│   ├── parts_manifest.yaml              ← from Codex deliverable 4
│   ├── defect_manifest.yaml             ← from Codex deliverable 5
│   └── cache/                           ← optional cached AGARD AR-138 PDF
├── templates/                           ← Jinja2 for OpenFOAM dicts
│   ├── fvSchemes_density.j2             ← NEW for case_006
│   ├── 0.orig.j2                        ← may need characteristic-BC extension
│   └── ...
├── scripts/
│   ├── _lib.py                          ← shared helpers
│   ├── build_cad.py                     ← from Codex deliverable 2
│   ├── 01_validate_cad.py               ← STEP import + body name check
│   ├── 02_verify_defects.py             ← D1+D4 + dual advisor exercise
│   ├── 03_validate_stl.py               ← multi-solid STL → harness loader
│   ├── 04_scaffold_case.py              ← case/ directory tree
│   ├── 05_make_dicts.py                 ← Jinja2 → all OpenFOAM dicts
│   ├── 06_run_mesh.sh                   ← Docker: blockMesh + sHM
│   ├── 07_check_mesh.py                 ← harness checkmesh + advisor
│   ├── 08_write_bcs.py                  ← BC writer per parts manifest
│   ├── 08b_write_density_fvschemes.py   ← NEW: Kurganov + limiters
│   ├── 08c_write_characteristic_bcs.py  ← NEW: characteristic far-field
│   ├── 09_run_solver.sh                 ← Docker: rhoCentralFoam
│   ├── 10_post.py                       ← ParaView base post
│   ├── 10b_compute_lambda_shock.py      ← NEW: Cp / lambda-shock detector
│   └── 11_audit.py                      ← signed evidence pack
├── case/                                ← OpenFOAM runtime (gitignored)
└── evidence/<version>/                  ← per-version reports
    ├── REPORT.md
    ├── lambda_shock_report.md           ← from 10b_compute_lambda_shock.py
    └── d4_advisor_exercise.md           ← thin_wall vs geometry_surgery
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
9. **Lambda-shock verdict**: prominent
   "CAPTURED / SMEARED / ABSENT" line in final report
10. **D4 advisor exercise verdict**: prominent
    "thin_wall_advisor / geometry_surgery / both silent" outcome

Commit messages NOT to mention being an AI:
```
chore(case_006): v<N> · <short summary>

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
  A2 virtual_interface_detector, density-based fvSchemes writer
  promotion) → hand-craft case-locally, document the gap, flag
  for main-session extraction
- Codex's design fundamentally unworkable → pause, flag, main
  session asks Codex for revision (round-cap=2; round 2 should
  request 86gs xhigh if available, since round 1 used CRS
  fallback)

## Boundaries

You CAN:
- Run case_006 commands end-to-end
- Modify your sandbox files freely
- Commit to main repo for sediment artifacts
- Extract small reusable artifacts (<250 LOC) when forced
- Fix toy-case-biased thresholds discovered in main-project
  advisors
- Add density-based and characteristic-BC support to templates
  if main project lacks it (compressible-shock forces this — flag
  as `corrects-assumption`)
- Override Codex's D4 advisor mapping if your exercise shows
  thin_wall_advisor is the correct catch (it almost certainly is)

You CANNOT:
- Modify another case's reference profile
- Open new full DEC arcs
- Change governance rules / framework decisions
- Run subagent or persona-driven dogfood
- Take a different case
- Re-design the case (only execute Codex's design + flag for
  revision if needed)
- Push regime above M_inf=0.95 or α=6° (case_010 LES territory)

## When you are done

Final report at `evidence/<latest>/REPORT.md`. Update
`case_index.md` status. Final commit summarizing. Then stop —
do NOT spawn additional sub-sessions or take additional cases.

## Known issues to watch

Per main session's validation report
(`case_006_validation.md`):

1. **CRS gpt-5.4 fallback used** — 86gs gpt-5.5 xhigh primary
   path 503'd at design time. Design quality is dispatch-ready
   but slightly less rigorous than case_005's xhigh path. If
   you find subtle inconsistencies (e.g., dimensions slightly
   off, missing detail in CAD script), main session round 2
   will retry on 86gs xhigh
2. **A2 (virtual_interface_detector) STILL not landed** — D1
   verified manually; flag for extraction with **4-of-4
   compounded evidence** (case_003/004/005/006 all surface this
   gap). Becomes 5-of-5 after case_007. Time to extract A2
   regardless
3. **D4 advisor mapping likely wrong** — Codex pointed at
   geometry_surgery.decimate_to_tier; thin_wall_advisor (LANDED)
   is more likely correct for a 0.18 mm sliver. **Exercise BOTH
   advisors and document outcome** — that's the high-signal
   exercise this case
4. **NASA Glenn URL HTTP 500** — `grc.nasa.gov/WWW/wind/valid/`
   archive persistent failure. Geometry baked into CadQuery
   constants — non-blocking. AGARD AR-138 PDF is durable
   reference for Cp data
5. **First density-based case for project** — no prior
   fvSchemes/Kurganov/characteristic-BC writer. Hand-craft
   case-locally; main session decides extraction priority. Likely
   shared with future external compressible cases
6. **Lambda-shock capture is the engineering question** — v1
   may not get it; v2 limiter tuning should. If v3 still fails
   with reasonable refinement, that's a real V-finding about
   rhoCentralFoam's limits
7. **D-section airfoil coordinate fidelity** — verify in v1
   against AGARD AR-138 Appendix; if >0.5% off at any x/c,
   shock pattern displaces — flag as geometry V-finding
8. **Mach ceiling = 0.95 / α ceiling = 6°** — beyond is
   case_010 LES territory; reduce if needed to stay in case_006
   envelope

=== END KICKOFF ===

---

## Main session post-dispatch checklist

After user pastes the kickoff into a new Claude Code session:

- [ ] Update `case_proposal_queue.md` — move case_006 row from
      "Active queue (proposed)" to "Dispatched"
- [ ] Update `case_index.md` — add case_006 row, status = "dispatched"
- [ ] Update `INDEX.md` — bump kickoff list to include case_006
- [ ] Wait for sub-session sediment in subsequent main-session
      turns
- [ ] When sub-session reports A2-extraction is needed (4-of-4
      evidence), elevate A2 priority in next harvest cycle
- [ ] When sub-session reports D4 advisor exercise outcome,
      decide whether thin_wall_advisor scope needs expansion or
      A4 sliver-detector extraction is warranted
- [ ] When sub-session extracts density-based / characteristic-BC
      / lambda-shock-detector infrastructure, evaluate for
      promotion to main-project shared services
