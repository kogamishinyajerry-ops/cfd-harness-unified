# Case 008 · GLC305 IRT Lagrangian · Sub-Session Kickoff

> Paste section between `=== BEGIN ===` and `=== END ===` into a
> fresh Claude Code session. Designed by Codex (gpt-5.5 xhigh,
> 86gs, round 1 of 2). Validated 2026-05-08 — see
> `case_008_validation.md`. PASS WITH NOTES (6th A2-pending).

=== BEGIN ===

You are a Claude Code sub-session under cfd-harness-unified
orchestration. Task: **case_008_glc305_irt_lagrangian**.

## Project context
cfd-harness-unified at `/Users/Zhuanz/Desktop/cfd-harness-unified/`.
Per DEC-V61-198, accumulates industrial CFD experience. Seven
prior cases (002a/b active; 003-007 dispatched-deferred). Your
case fills **incompressible-RANS-Lagrangian** (icing droplet
impingement) — first Lagrangian for project.

## Required reading
1. `.planning/decisions/2026-05-07_v61_198_apu_bay_strategic_pivot.md`
2. `.planning/case_proposal_queue.md`
3. `.planning/case_profiles/case_002a_*.md`, `case_002b_*.md`
4. `.planning/methodology/industrial_case_solver_findings.md` (Pattern 6: case_008 inherits NONE)
5. `.planning/methodology/solver_convergence_playbook.md`
6. `.planning/methodology/rag_corpus_format.md`
7. `~/Desktop/apu-bay-ventilation/` (sandbox layout)
8. `.planning/methodology/kickoff/case_008_codex_response.md` (Codex's brief + script + manifests)
9. `.planning/methodology/kickoff/case_008_validation.md`

## Hard guardrails
1. V130 advisory-only · V132 no AI-mutating routes
2. No date/calendar gating; OpenFOAM is truth source
3. Use main-project advisors:
   - `thin_wall_advisor` (LANDED) for D8's 0.80 mm TE tab
   - `geometry_surgery` if mesh adjustments forced
4. Do NOT redesign the case
5. **No ice horn** — input is CLEAN GLC305; harness predicts where ice WOULD form via β(s/c)
6. **No NACA 0012 substitution** — Lane B excluded
7. **1-way coupling for v1** — particle volume fraction 7e-7 is dilute; DPMFoam is v2 fallback only

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

### D1 (root_mount_pad / strut gap, 0.35 mm) — A2 PENDING (6th case)
```bash
FreeCADCmd -c "import FreeCAD as App, Import; doc=App.newDocument(); \
  Import.insert('inputs/cad_codex_v1.step', doc.Name); \
  o={x.Label:x for x in doc.Objects}; \
  print(o['root_mount_pad'].Shape.distToShape(o['root_mount_strut'].Shape)[0])"
```
Expected ≈ 0.35 mm. Document A2-pending — case_008 is **6th
consecutive** to surface this gap. Compounded evidence is
overdetermined.

### D8 (trailing_edge_tab_thin, 0.80 mm) — thin_wall_advisor LANDED
```bash
FreeCADCmd -c "import FreeCAD as App, Import; doc=App.newDocument(); \
  Import.insert('inputs/cad_codex_v1.step', doc.Name); \
  o={x.Label:x for x in doc.Objects}; \
  bb=o['trailing_edge_tab_thin'].Shape.BoundBox; \
  print(min(bb.XLength, bb.YLength, bb.ZLength))"
```
Expected ≈ 0.80 mm. Run thin_wall_advisor (LANDED). **3-case
consistency check**: case_004 (0.75 mm shim) + case_007 (0.80
mm transom) + case_008 (0.80 mm TE tab) should produce
similar advisor signals. Divergence = V-finding on advisor
context-sensitivity.

## Six per-case standard moves
1. Reference profile at `case_profiles/case_008_glc305_irt_lagrangian.md`
2. V-series: kinematicCloud injection model robustness, particle
   trajectory near LE stagnation singularity, β(s/c) artifact
   at sharp LE, freeze-Eulerian-then-cloud workflow pitfalls
3. Playbook S13+: "1-way cloud after Eulerian freeze →
   converge Eulerian first to <1e-5; cloud needs no further
   pressure-velocity coupling"
4. Stale-assumption fixes: 0.orig may not have cloud sub-models
5. Artifact extraction: lagrangian_cloud_writer +
   collection_efficiency_post_processor
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

## Boundaries
- CAN: end-to-end run, sandbox modify, sediment commits, <250 LOC
  artifact extraction, advisor-bias fixes
- CANNOT: redesign case, modify other cases, open new DEC arcs,
  add ice-horn geometry to input, switch to NACA 0012

## Known issues
1. **A2 pending — 6-of-6 evidence**. Manual D1 verify + flag for extraction
2. **D8 thin_wall_advisor 3-case consistency** (case_004 + 007 + 008)
3. **Re slightly off nominal** — 1.46e6 vs 1.8e6 IRT canonical;
   document in v1, sub-session may re-tune ν or accept
4. **First Lagrangian** — kinematicCloud infrastructure all-new
5. **Cold-start Eulerian → freeze → cloud** workflow pattern
   brand new; pitfalls likely

=== END ===

## Main session post-dispatch checklist
- [ ] Move case_008 row from "Active queue" to "Dispatched"
- [ ] Update `case_index.md` with case_008 status=dispatched
- [ ] Update `INDEX.md` kickoff list
- [ ] When 6-of-6 A2 evidence + sub-session signal arrive, A2 extraction = top harvest
