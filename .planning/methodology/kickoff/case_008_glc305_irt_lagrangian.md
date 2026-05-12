# Case 008 · GLC305 IRT Lagrangian · Sub-Session Kickoff

> Paste section between `=== BEGIN ===` and `=== END ===` into a
> fresh Claude Code session. Designed by Codex (gpt-5.5 xhigh,
> 86gs, round 1 of 2). Validated 2026-05-08 — see
> `case_008_validation.md`. PASS WITH NOTES.
>
> **A2 advisor LANDED 2026-05-08 (commit `a09ae0a`) BUT scope-narrow
> per V25** (open · sourced by case_005 v2 disambiguation, captured
> in harvest cycle 002): A2's `_run_shared` returns matched=True
> with hardcoded placeholder fields regardless of actual gap
> distance. D1 exercise produces algorithm-runs-cleanly evidence,
> NOT gap-detection field-validation. A2-v2 sub-DEC drafted at
> `.planning/patches/draft_a2_v2_gap_detection_2026-05-08.md`.

=== BEGIN ===

You are a Claude Code sub-session under cfd-harness-unified
orchestration. Task: **case_008_glc305_irt_lagrangian**.

## Project context
cfd-harness-unified at `/Users/Zhuanz/Desktop/cfd-harness-unified/`.
Per DEC-V61-198, accumulates industrial CFD experience.

Seven prior cases:
- case_002a, 002b: active
- case_003 (CRM-HLS, external high-Re): active · v1 paused on V20
  unit-scale block
- case_004 (NREL Phase VI rotor, MRF): active · v1 advisor-validation
  done; CFD pending v2
- case_005 (RAE M2129 S-duct): active · v1+v2 ran; sourced
  V16-V25 chain (incl. V25: A2 placeholder semantic OPEN)
- case_006 (ONERA M6 transonic): dispatched-deferred
- case_007 (KCS ship VOF): dispatched-deferred

Your case fills **incompressible-RANS-Lagrangian** (icing droplet
impingement) — first Lagrangian for project. You also complete
the thin_wall_advisor 5-case cross-topology validation arc:
case_002a (curved CATIA frame) + case_003 (planar aero plate) +
case_004 (rotating-machinery shim) + case_007 (ship transom) +
case_008 (airfoil TE tab) — last in the arc unless case_010 surfaces
sub-mm thin geometry too.

## Required reading
1. `.planning/decisions/2026-05-07_v61_198_apu_bay_strategic_pivot.md`
2. `.planning/case_proposal_queue.md`
3. `.planning/case_profiles/case_002a_*.md`, `case_002b_*.md`
4. `.planning/methodology/industrial_case_solver_findings.md`
   (Pattern 6: case_008 inherits NONE of V3-V25; Lagrangian is
   a new numerics root)
5. `.planning/methodology/solver_convergence_playbook.md`
6. `.planning/methodology/rag_corpus_format.md`
7. **`.planning/methodology/knowledge_status_convention.md`**
   (NEW · 2026-05-08 harvest 002) — defines `[QUESTIONABLE]` /
   `[REFUTED]` / `[SUPERSEDED]` / `[VALIDATED]` markers
8. `.planning/cross_cuts/v_series_2026-05-08.md` (V-series snapshot)
9. `.planning/harvest_reports/2026-05-08_harvest_002.md` (cycle 002
   findings — A2 capability framing notes)
10. `~/Desktop/apu-bay-ventilation/` (sandbox layout)
11. `.planning/methodology/kickoff/case_008_codex_response.md`
    (Codex's brief + script + manifests)
12. `.planning/methodology/kickoff/case_008_validation.md`

## Hard guardrails
1. V130 advisory-only · V132 no AI-mutating routes
2. No date/calendar gating; OpenFOAM is truth source
3. Use main-project advisors:
   - `from ui.backend.services.geometry_ingest.thin_wall_advisor
     import detect_thin_wall_patches_at_risk` (for D8 — LANDED,
     robust 3-of-3 cross-topology per V23)
   - `from ui.backend.services.geometry_ingest.virtual_interface_detector
     import detect_virtual_interfaces, InterfaceSpec` (for D1 — A2
     LANDED 2026-05-08 a09ae0a, BUT see `[QUESTIONABLE]` marker
     in D1 verification section below)
   - `from ui.backend.services.geometry_ingest.geometry_surgery
     import decimate_to_tier` (if mesh adjustments forced)
   - DO NOT re-implement these case-locally
4. Do NOT redesign the case — execute Codex's brief; revision
   request only if fundamentally unworkable (round-cap=2)
5. **No ice horn** — input is CLEAN GLC305; harness predicts where ice WOULD form via β(s/c)
6. **No NACA 0012 substitution** — Lane B excluded
7. **1-way coupling for v1** — particle volume fraction 7e-7 is dilute; DPMFoam is v2 fallback only
8. Do NOT add `isSame()` fast-path to `virtual_interface_detector`
   (V2 lesson preserved)

## Case identifier
`case_008_glc305_irt_lagrangian` · solver-class **incompressible-RANS-Lagrangian** · numerics-class **incompressible-RANS-Lagrangian** (root)

## Codex brief summary (deliverable 1)
- Clean GLC305, 305 mm chord, 2D-extruded slab (1 chord spanwise)
- U_inf=67 m/s vector with α=4°: U=(66.84, 4.67, 0)
- T_inf=268 K (icing T below freezing), ν_air=1.4e-5
- Re_chord=1.46e6 (slightly below nominal IRT 1.8e6 due to cold T; sub-session may re-tune)
- MVD=25 µm, LWC=0.7 g/m³, ρ_p=1000, K_inertia=0.41, Stokes=0.41
- Engineering question: collection efficiency β(s/c) at LE + impingement limits s_upper/s_lower
- v1: simpleFoam → converge → freeze U/p/nut → kinematicCloud one-way tracking
- v2 fallback: DPMFoam if 2-way coupling effects emerge
- Effort: 8-12h, ~3 versions

## Codex CAD script (deliverable 2)
Save at `scripts/build_cad.py`. 231 LOC, deterministic. 10 named
bodies including airfoil_clean / root_mount_pad / root_mount_strut /
trailing_edge_tab_thin / inlet / outlet / farfield_top/bottom /
sym_plane_left/right.

```bash
cd ~/Desktop/case_008_glc305_irt_lagrangian
python3 -m venv .venv
.venv/bin/pip install cadquery numpy pyyaml jinja2 trimesh
python scripts/build_cad.py --out inputs/cad_codex_v1.step
```

## Lagrangian-specific work (case_008 unique territory)

### `08b_write_kinematic_cloud.py`
Consume parts manifest's `lagrangian_cloud:` block → emit
`constant/kinematicCloudProperties` with patchInjection,
particle drag, dispersion model, particle-wall interaction
(stick for icing collection):
```
kinematicCloudProperties
{
    type        kinematicCloud;
    solution
    {
        active          true;
        coupled         false;     // one-way
        transient       no;        // steady-state cloud after frozen Eulerian
        cellValueSourceCorrection  off;
        sourceTerms { schemes {} }
        interpolationSchemes
        {
            U  cell;
            p  cell;
        }
        integrationSchemes { U  Euler; }
    }
    constantProperties
    {
        rho0            1000;     // water
        d0              25e-6;    // MVD
        T0              268;
    }
    subModels
    {
        particleForces { sphereDrag; }
        injectionModels
        {
            modelInlet
            {
                type        patchInjection;
                patchName   inlet;
                duration    1.0;
                massTotal   <derived>;
                ...
            }
        }
        dispersionModel    none;
        patchInteractionModel localInteraction;
        localInteraction
        {
            patches
            (
                airfoil_clean { type stick; }
                root_mount_pad { type stick; }
                ...
            );
        }
    }
}
```

### `09_run_solver.sh`
1. simpleFoam to steady (residuals < 1e-5)
2. Snapshot final U, p, nut → freeze in next stage's `0/`
3. Run kinematicCloud-only stage with frozen Eulerian fields
4. Cloud post-processing: count parcels stuck per patch face

### `10b_compute_collection_efficiency.py`
1. Parse cloud's per-patch parcel count + mass
2. β = (mass per unit area at airfoil_clean face) / (LWC × U_inf × cosθ)
3. Map face β to s/c arc-length on airfoil
4. Plot β(s/c) for upper + lower surface
5. Find impingement limits: s_upper where β > 0.05, s_lower likewise
6. Compare to Wright et al. 2002 (NASA/TM-2002-211557) or
   IRT-published β at GLC305 if accessible

## Defect verification

### D1 (root_mount_pad / strut gap, 0.35 mm) — A2 advisor LANDED with caveat

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
> To resolve: A2-v2 lands AND case_008 sub-session re-runs D1
> falsification on root_mount_pad/strut geometry. Until then,
> your A2 PASS confirms only that `_run_shared` runs cleanly on
> mount-pad faces — NOT that A2 detects the 0.35 mm gap as a defect.

**Step 1 — manual ground truth via FreeCAD**:

```bash
FreeCADCmd -c "import FreeCAD as App, Import; doc=App.newDocument(); \
  Import.insert('/Users/Zhuanz/Desktop/case_008_glc305_irt_lagrangian/inputs/cad_codex_v1.step', doc.Name); \
  o={x.Label:x for x in doc.Objects}; \
  print(o['root_mount_pad'].Shape.distToShape(o['root_mount_strut'].Shape)[0])"
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
    name="root_mount_pad__root_mount_strut_interface",
    mode="shared",
    bodies=("root_mount_pad", "root_mount_strut"),
)
result = detect_virtual_interfaces(bodies=[pad_body, strut_body],
                                   specs=[spec])
# Expect: matched=True (per V21/V22 pattern) BUT this PASS is
# NOT field-validation of gap-detection capability per V25.
```

**Step 3 — V-finding judgments**:

- If `matched=True`: document as "case_008 cross-topology PASS for
  `_run_shared` on incompressible-Lagrangian airfoil-mount geometry"
  (algorithm-runs-cleanly, NOT gap-detection per V25).
- If `matched=False`: NEW V-finding documenting which geometric
  property of mount-pad/strut fails `find_face_facing_target`;
  contrast with case_003/004 (axis-aligned-planar PASS) and
  case_005 (flange-ring axial-end PASS).
- Do NOT propose `isSame()` fast-path (V2 lesson).

### D8 (trailing_edge_tab_thin, 0.80 mm) — thin_wall_advisor LANDED
```bash
FreeCADCmd -c "import FreeCAD as App, Import; doc=App.newDocument(); \
  Import.insert('inputs/cad_codex_v1.step', doc.Name); \
  o={x.Label:x for x in doc.Objects}; \
  bb=o['trailing_edge_tab_thin'].Shape.BoundBox; \
  print(min(bb.XLength, bb.YLength, bb.ZLength))"
```
Expected ≈ 0.80 mm. Then exercise:

```python
import sys
sys.path.insert(0, "/Users/Zhuanz/Desktop/cfd-harness-unified")
from ui.backend.services.geometry_ingest.thin_wall_advisor import (
    PatchGeometry, detect_thin_wall_patches_at_risk
)
warnings = detect_thin_wall_patches_at_risk(
    patches=[PatchGeometry(name="trailing_edge_tab_thin",
                            bbox_dimensions=(tab_dx_m, 0.0008, tab_dz_m))],
    refinement_levels={"trailing_edge_tab_thin": (1, 2)},
    background_cell_size=YOUR_BG_CELL_SIZE_METERS,
)
print(warnings)  # expect 'critical'
```

**5-case cross-topology validation arc (last in roster unless
case_010 surfaces sub-mm thin)**: case_002a (curved CATIA Frame)
+ case_003 (planar CadQuery thin_access_plate) + case_004
(rotating-machinery `yaw_sensor_shim` 0.75mm) + case_007 (ship
transom plate 0.80mm) + case_008 (airfoil TE tab 0.80mm). If all
5 produce critical warning consistent with cases 002a-007,
**upgrade V10 / V23 status to "5-of-5 — robust across (curved-shell,
planar-aero, rotating-aux, ship-hydro, airfoil-TE) topologies"**
per `knowledge_status_convention.md` `[VALIDATED]` marker. If
divergent, flag as advisor-context-sensitivity V-finding.

## Six per-case standard moves
1. Reference profile at `case_profiles/case_008_glc305_irt_lagrangian.md`
2. V-series: kinematicCloud injection model robustness, particle
   trajectory near LE stagnation singularity, β(s/c) artifact at
   sharp LE, freeze-Eulerian-then-cloud workflow pitfalls. ALSO:
   **A2 `_run_shared` behavior on Lagrangian-airfoil topology**
   (above); **thin_wall 5-case cross-topology check** (above)
3. Playbook S13+: "1-way cloud after Eulerian freeze → converge
   Eulerian first to <1e-5; cloud needs no further pressure-
   velocity coupling"
4. Stale-assumption fixes: 0.orig may not have cloud sub-models.
   Commit tag: `corrects-assumption: <X>, surfaced-by: case_008-V<n>`
5. Artifact extraction: `lagrangian_cloud_writer.py` +
   `collection_efficiency_post_processor.py`
6. RAG corpus: 5 artifacts per `rag_corpus_format.md`

## Sandbox structure
```
~/Desktop/case_008_glc305_irt_lagrangian/
├── README.md, Makefile, .venv/
├── config/case.yaml
├── inputs/{cad_codex_v1.step, parts_manifest.yaml, defect_manifest.yaml}
├── templates/{kinematicCloudProperties.j2 (NEW), 0.orig.j2 extension, ...}
├── scripts/{01..11 + 08b_write_kinematic_cloud.py + 10b_compute_collection_efficiency.py}
├── case/    (gitignored)
└── evidence/<v>/{REPORT.md, beta_report.md, d8_thin_wall_consistency.md}
```

## Sediment + commit convention
Same as case_002a/b. `confidence: <high|med|low>` trailer.
Co-author Claude Opus 4.7. `case/` runtime gitignored.

If you produce a V-finding involving an advisor capability claim,
apply `knowledge_status_convention.md` grammar — do NOT write
"A2 field-validated" if you only confirmed `_run_shared` runs cleanly.

## Boundaries
- CAN: end-to-end run, sandbox modify, sediment commits, <250 LOC
  artifact extraction, advisor-bias fixes, add Lagrangian fields
  to 0.orig if missing
- CANNOT: redesign case, modify other cases, open new DEC arcs,
  add ice-horn geometry to input, switch to NACA 0012, add
  `isSame()` fast-path to `virtual_interface_detector` (V2 lesson)

## Known issues
1. **A2 advisor LANDED but scope-narrow (V25 open)** — D1 exercise
   produces algorithm-runs-cleanly evidence, NOT gap-detection
   field-validation. See `[QUESTIONABLE]` marker in D1 verification
   section above. A2-v2 sub-DEC drafted
   (`patches/draft_a2_v2_gap_detection_2026-05-08.md`); after it
   lands, case_008 v3 re-runs D1 falsification.
2. **D8 thin_wall_advisor 5-case consistency check** — case_002a
   + 003 + 004 + 007 + 008 should all produce critical warning;
   completes the cross-topology validation arc. Upgrade V10/V23
   to `[VALIDATED]` on consistency, or flag context-sensitivity
   V-finding on divergence.
3. **Re slightly off nominal** — 1.46e6 vs 1.8e6 IRT canonical
   due to T_inf=268K (cold ν shifts Re). Document in v1; sub-
   session may re-tune ν or accept.
4. **First Lagrangian** — kinematicCloud infrastructure all-new;
   templates / writers / β post-processor all hand-crafted.
5. **Cold-start Eulerian → freeze → cloud workflow** brand new;
   pitfalls likely (e.g., U/p/nut dictionary lookup mismatch in
   cloud stage, ddtScheme requirement for steady-state cloud).

=== END ===

## Main session post-dispatch checklist
- [ ] Move case_008 row from "Active queue" to "In-flight"
- [ ] Update `case_index.md` with case_008 status=active
- [ ] Update `INDEX.md` kickoff list status reconciled
- [ ] When sub-session reports A2 `_run_shared` outcome on
      Lagrangian-airfoil-mount topology (PASS = algorithm-runs-cleanly,
      NOT gap-detection per V25), update V22 / V25 evidence rows
- [ ] When sub-session reports thin_wall 5-case cross-topology
      outcome, upgrade V10/V23 to `[VALIDATED]` (5-of-5) or open
      context-sensitivity V-finding on divergence
- [ ] When sub-session extracts Lagrangian infrastructure
      (lagrangian_cloud_writer / collection_efficiency_post_processor),
      evaluate for promotion to main-project shared services
