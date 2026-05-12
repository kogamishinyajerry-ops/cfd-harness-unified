# Case 009 · Sandia Flame D · Sub-Session Kickoff

> Paste between `=== BEGIN ===` and `=== END ===` into a fresh
> Claude Code session. Designed by Codex (gpt-5.5 xhigh, 86gs,
> round 1 of 2). Validated 2026-05-08 — see
> `case_009_validation.md`. PASS WITH NOTES (highest infra climb;
> longest case in roster: 12-16h).
>
> **A2 advisor LANDED 2026-05-08 (commit `a09ae0a`) BUT scope-narrow
> per V25** (open · sourced by case_005 v2 disambiguation, captured
> in harvest cycle 002): A2's `_run_shared` returns matched=True
> with hardcoded placeholder fields regardless of actual gap
> distance. **A3 advisor LANDED but scope-narrow per V17** (open ·
> case_005 D2 falsification): `decimate_to_tier` reduces face count
> cleanly but lacks redundancy/overlay-detection classification.
> If case_009 defect manifest uses D1 or D2, exercise produces
> algorithm-runs-cleanly evidence, NOT capability field-validation.
> A2-v2 sub-DEC drafted at
> `.planning/patches/draft_a2_v2_gap_detection_2026-05-08.md`.

=== BEGIN ===

You are a Claude Code sub-session under cfd-harness-unified
orchestration. Task: **case_009_sandia_flame_d**.

⚠️ **Highest-effort case in the 10-case roster (12-16h, 3+
versions). Reacting-low-Mach is brand new for the project.**

## Project context
cfd-harness-unified at `/Users/Zhuanz/Desktop/cfd-harness-unified/`.
Per DEC-V61-198, accumulates industrial CFD experience.

Eight prior cases:
- case_002a, 002b: active
- case_003 (CRM-HLS, external high-Re): active · v1 paused on V20
  unit-scale block
- case_004 (NREL Phase VI rotor, MRF): active · v1 advisor-validation
  done; CFD pending v2
- case_005 (RAE M2129 S-duct): active · v1+v2 ran; sourced
  V16-V25 chain (incl. V25: A2 placeholder semantic OPEN; V17:
  A3 redundancy gap OPEN)
- case_006 (ONERA M6 transonic): dispatched-deferred
- case_007 (KCS ship VOF): dispatched-deferred
- case_008 (GLC305 Lagrangian): dispatched-deferred

Your case fills **reacting-low-Mach combustion** — first reacting
case; biggest infrastructure climb in roster (5+ artifact
extraction candidates).

## Required reading
1. `.planning/decisions/2026-05-07_v61_198_apu_bay_strategic_pivot.md`
2. `.planning/case_proposal_queue.md`
3. `.planning/case_profiles/case_002a_*.md`, `case_002b_*.md`
4. `.planning/methodology/industrial_case_solver_findings.md`
   (Pattern 6: case_009 inherits NONE of V3-V25; reacting-low-Mach
   is a new numerics root)
5. `.planning/methodology/solver_convergence_playbook.md`
6. `.planning/methodology/rag_corpus_format.md`
7. **`.planning/methodology/knowledge_status_convention.md`**
   (NEW · 2026-05-08 harvest 002) — defines `[QUESTIONABLE]` /
   `[REFUTED]` / `[SUPERSEDED]` / `[VALIDATED]` markers
8. `.planning/cross_cuts/v_series_2026-05-08.md` (V-series snapshot)
9. `.planning/harvest_reports/2026-05-08_harvest_002.md` (cycle 002
   findings — A2/A3 capability framing notes)
10. `~/Desktop/apu-bay-ventilation/` (sandbox layout)
11. `.planning/methodology/kickoff/case_009_codex_response.md`
12. `.planning/methodology/kickoff/case_009_validation.md`

## Hard guardrails
1. V130 advisory-only · V132 no AI-mutating routes
2. No date/calendar gating; OpenFOAM is truth source
3. Use main-project advisors:
   - `from ui.backend.services.geometry_ingest.thin_wall_advisor
     import detect_thin_wall_patches_at_risk` (for any thin shim
     in defect manifest, e.g. `bracket_lip_thin` — LANDED, robust
     across cross-topology arc per V23)
   - `from ui.backend.services.geometry_ingest.virtual_interface_detector
     import detect_virtual_interfaces, InterfaceSpec` (if defect
     manifest includes D1 sub-mm gap — A2 LANDED 2026-05-08
     a09ae0a, BUT see `[QUESTIONABLE]` marker in defect verification
     section below)
   - `from ui.backend.services.geometry_ingest.geometry_surgery
     import decimate_to_tier` (for D2 over-dense triangulation
     if used; LANDED but V17 scope-narrow per case_005 evidence)
   - DO NOT re-implement these case-locally
4. Do NOT redesign the case — execute Codex's brief; revision
   request only if fundamentally unworkable (round-cap=2)
5. **DRM-19 primary** chemistry; if too expensive, drop to
   2-step Westbrook-Dryer fallback. **DO NOT use GRI-Mech 3.0**
   (53 species — too expensive for v1; v3 only after v2 stable)
6. **2D axisymmetric wedge** (5°); do NOT escalate to 3D LES
   (case_010 territory)
7. **Non-premixed diffusion flame** scope; do NOT add premixed
8. Z(r,z) and T(r,z) measurement stations at z/D = 7.5/15/30/45/60
   must remain mesh-clean
9. Do NOT add `isSame()` fast-path to `virtual_interface_detector`
   (V2 lesson preserved)

## Case identifier
`case_009_sandia_flame_d` · solver-class **reacting low-Mach** ·
numerics-class **reacting-low-Mach** (root)

## Codex brief summary
- Sandia TUD Flame D (TNF Workshop CH4/air piloted jet)
- Geometry: fuel_jet D=7.2 mm, pilot_annulus 7.7-18.2 mm OD,
  coflow OD=240 mm, domain L=576 mm (80D), R=250 mm, 5° wedge
- Inlets:
  - fuel_jet: 25/75 vol% CH4/air mix, U=49.6 m/s, T=294 K
  - pilot_annulus: stoichiometric burn products, T=1880 K, U=11.4 m/s
  - coflow_air: O2=0.232/N2=0.768, U=0.9 m/s, T=291 K
- Solver: reactingFoam (or rhoReactingFoam) + DRM-19 + PaSR (Cmix=1.0)
- Thermo: hePsiThermo + reactingMixture + sutherland + janaf + perfectGas + sensibleEnthalpy
- Turbulence: kEpsilon (compressible variant)
- Sc=Sc_t=0.7, radiation off in v1
- Effort: 12-16h, ~3 versions
- v1: cold-flow → enable chemistry with small Δt → ramp
- v2: PaSR → EDC if turbulence-chemistry interaction matters
- v3: optional radiation (opticallyThin) if T over-predicted

## Codex CAD script (deliverable 2)
Save at `scripts/build_cad.py`. 230 LOC, deterministic. 13 named
bodies including 3 inlets + wedge front/back + outer_side +
far_outlet + 4 defect bodies (`coflow_plenum_mount_bracket`,
`coflow_plenum_mount_shim`, `bracket_lip_thin`, +
`fuel_nozzle_lip` and `pilot_housing_exterior` and
`burner_base_wall`).

```bash
cd ~/Desktop/case_009_sandia_flame_d
python3 -m venv .venv
.venv/bin/pip install cadquery numpy pyyaml jinja2 trimesh
python scripts/build_cad.py --out inputs/cad_codex_v1.step
```

## Reacting-low-Mach-specific work (case_009 unique)

### `08b_load_chemistry_mech.py` (NEW, primary new artifact)
Download DRM-19 chem.inp + therm.dat + tran.dat from UCSD or LLNL
mirror. Place at `constant/chemistry/DRM19/`. Convert via:
```bash
chemkinToFoam constant/chemistry/DRM19/chem.inp \
              constant/chemistry/DRM19/therm.dat \
              constant/chemistry/DRM19/tran.dat \
              constant/reactions
```
If `chemkinToFoam` failures → use Westbrook-Dryer 2-step fallback
(simpler manual reaction definition).

### `08c_write_combustion_thermo.py` (NEW)
Emit `constant/thermophysicalProperties` with:
```
thermoType
{
    type            hePsiThermo;
    mixture         reactingMixture;
    transport       sutherland;
    thermo          janaf;
    energy          sensibleEnthalpy;
    equationOfState perfectGas;
    specie          specie;
}
```

### `08d_write_species_bcs.py` (NEW)
Emit `0/CH4`, `0/O2`, `0/N2`, `0/CO2`, `0/H2O` (and rest of DRM-19
species) at each inlet patch with the mass fractions per Codex's
manifest. Walls: zeroGradient. Wedge: wedge.

### `08e_write_combustion_properties.py` (NEW)
Emit `constant/combustionProperties`:
```
combustionModel  PaSR;
PaSRCoeffs
{
    Cmix          1.0;
    chemistry
    {
        type      EulerImplicit;
        EulerImplicitCoeffs { cTauChem 1.0; equilibriumRateLimiter off; }
    }
}
```

### `09_run_solver.sh` for reactingFoam
1. Cold flow without reactions: `combustion off` in
   combustionProperties; run reactingFoam ~ 0.05 s
2. Enable chemistry: `combustion on`; small Δt = 1e-6 s; run ~
   0.1 s
3. Ramp Δt to 1e-5 s; run to ~ 0.5-1.0 s; tail-average species + T
4. Optionally enable radiation in v3

### `10b_compute_mixture_fraction.py`
1. Compute Bilger-style mixture fraction Z from local CH4/O2/H2O/CO2
2. Sample Z(r,z) at z/D = 7.5/15/30/45/60 (5 published TNF stations)
3. Compare to Barlow & Frank Raman/Rayleigh data
4. Emit `evidence/<v>/mixture_fraction_report.md`

### `10c_compute_temperature_profile.py`
Same idea but for T(r,z). Compare to TNF measurements.

## Defect verification

### Read defect manifest first

Open `.planning/methodology/kickoff/case_009_codex_response.md`
for exact D-codes, body IDs, and verification commands. Likely
combination: D2 (over-dense triangulation) + D1 or D6 (geometric
defect). Defect bodies on `coflow_plenum_mount_bracket` /
`coflow_plenum_mount_shim` / `bracket_lip_thin` — all OUTSIDE the
flame core and z/D measurement stations.

### If defect manifest includes D1 (sub-mm gap)

> [QUESTIONABLE 2026-05-08]: "exercise A2; expect detection of
> sub-mm gap" framing assumes a capability A2 v1 does NOT have.
> A2 LANDED for V2 pattern (shared-interface confirmation on
> non-manifold STEP), NOT D1 pattern (gap-as-defect detection).
> Per V25 (open · `industrial_case_solver_findings.md#V25`),
> A2's `_run_shared` returns `matched=True` with hardcoded
> placeholder `bbox_overlap_fraction=1.0` /
> `area_diff_fraction=0.0` regardless of actual gap distance.
> Verification pending: A2-v2 sub-DEC adds `inter_face_gap_mm`
> field to `DetectedInterface` (drafted at
> `.planning/patches/draft_a2_v2_gap_detection_2026-05-08.md`).
> To resolve: A2-v2 lands AND case_009 sub-session re-runs D1
> falsification on combustion-burner mount-bracket geometry.
> Until then, your A2 PASS confirms only that `_run_shared` runs
> cleanly — NOT gap-detection.

3-step protocol if D1 present:
1. FreeCAD `distToShape` ground truth on the two named bodies
   (per defect manifest)
2. Exercise A2 via `detect_virtual_interfaces` +
   `InterfaceSpec(mode='shared', bodies=(<a>, <b>))`
3. V-finding judgment:
   - `matched=True` → "case_009 cross-topology PASS for
     `_run_shared` on combustion-burner topology" (NOT
     gap-detection per V25)
   - `matched=False` → NEW finding documenting geometric reason;
     contrast with case_003/004 (axis-aligned-planar PASS) and
     case_005 (flange-ring axial-end PASS)
   - Do NOT propose `isSame()` fast-path (V2 lesson)

### If defect manifest includes D2 (over-dense triangulation)

Verify face count via FreeCAD `len(o['<body>'].Shape.Faces)` per
manifest. Then exercise A3 advisor:

```python
import sys
sys.path.insert(0, "/Users/Zhuanz/Desktop/cfd-harness-unified")
from ui.backend.services.geometry_ingest.geometry_surgery import (
    decimate_to_tier
)
decimated = decimate_to_tier(overdense_mesh, target_tier="medium")
```

> [QUESTIONABLE 2026-05-08]: A3 LANDED but V17 (open) shows it
> lacks redundancy/overlay-detection logic — `decimate_to_tier`
> reduces face count cleanly but does NOT classify whether the
> overlay should be DROPPED vs DECIMATED. case_005 v1 surfaced
> A3 PARTIAL on D2 throat liner. case_009 D2 (if used) is 2nd
> industrial falsification opportunity. Document outcome:
> A3 reduces face count? Does it warn on geometric redundancy?
> 2-of-N evidence triggers A3-v2 sub-DEC arc draft.

### If defect manifest includes D8 (thin shell, e.g. `bracket_lip_thin`)

Standard thin_wall_advisor exercise via
`detect_thin_wall_patches_at_risk` per cases 002a/003/004/007/008
pattern. case_009 would be 6th case in cross-topology arc;
already robust 5-of-5 expected — bonus consistency evidence.

### If defect manifest includes D6 or other

Per Codex's verification command + flag any advisor blind spots
as new V-finding. Component bank D6 (anisotropic mesh near sharp
edges) is not yet exercised by any case in roster.

## Six per-case standard moves
1. Reference profile at `case_profiles/case_009_sandia_flame_d.md`
2. V-series append: chemistry timestep stability, PaSR vs EDC
   sensitivity, hot-pilot startup spikes, species boundedness,
   heat-release rate post-processing pitfalls, mixture-fraction
   Bilger formula edge cases, radiation coupling. ALSO:
   **A2 / A3 advisor outcome on combustion-burner topology**
   if D1 / D2 used (above)
3. Playbook S13+ candidates: "reactingFoam NaN at startup →
   verify cold-flow first stage; small Δt; chemistry off until
   stable" / "species mass fractions out of [0,1] → check thermo
   janaf coefficients vs UCSD mirror" / "PaSR ↔ EDC sensitivity
   quantification at z/D=7.5"
4. Stale-assumption fixes: 0.orig has no species fields;
   thermophysicalProperties has no reactingMixture path. Commit
   tag: `corrects-assumption: <X>, surfaced-by: case_009-V<n>`
5. Artifact extraction (LIKELY 5+ for case_009 — biggest
   sub-DEC budget consumer in roster):
   - `chemkin_mechanism_loader.py` (DRM-19 fetch + chemkinToFoam)
   - `combustion_thermo_writer.py` (reactingMixture +
     sutherland + janaf + sensibleEnthalpy)
   - `species_bc_writer.py` (per-inlet mass fractions for N
     species)
   - `combustion_properties_writer.py` (PaSR / EDC)
   - `mixture_fraction_post_processor.py` (Bilger formula)
6. RAG corpus: 5 artifacts per `rag_corpus_format.md`

## Sandbox structure
```
~/Desktop/case_009_sandia_flame_d/
├── README.md, Makefile, .venv/
├── config/case.yaml
├── inputs/{cad_codex_v1.step, parts_manifest.yaml, defect_manifest.yaml}
├── constant/chemistry/{DRM19/, westbrook_dryer_2step/}    (filled by 08b)
├── templates/{thermophysicalProperties.j2 (NEW), combustionProperties.j2 (NEW),
│              0.orig.j2 species extension, ...}
├── scripts/{01..11 + 08b/c/d/e + 10b/c}
├── case/    (gitignored)
└── evidence/<v>/{REPORT.md, mixture_fraction_report.md, temperature_report.md}
```

## Sediment + commit convention
Same as case_002a/b. `confidence: <high|med|low>` trailer.
Co-author Claude Opus 4.7. `case/` runtime gitignored.

If you produce a V-finding involving an advisor capability claim,
apply `knowledge_status_convention.md` grammar — do NOT write
"A2 field-validated" or "A3 field-validated" if you only confirmed
algorithm-runs-cleanly behavior.

## Boundaries
- CAN: end-to-end run, sandbox modify, sediment, <250 LOC
  artifact extraction (likely 5+ for this case), advisor-bias
  fixes, add reacting fields to 0.orig if missing
- CANNOT: redesign case, modify other cases, open new DEC arcs,
  upgrade to GRI-Mech 3.0 in v1, escalate to 3D LES, add
  `isSame()` fast-path to `virtual_interface_detector` (V2 lesson)

## Known issues
1. **A2 advisor LANDED but scope-narrow (V25 open)** — D1 exercise
   (if defect manifest uses D1) produces algorithm-runs-cleanly
   evidence, NOT gap-detection field-validation. See
   `[QUESTIONABLE]` marker in defect verification section above.
   A2-v2 sub-DEC drafted
   (`patches/draft_a2_v2_gap_detection_2026-05-08.md`); after it
   lands, case_009 v3 re-runs if applicable.
2. **A3 advisor LANDED but scope-narrow (V17 open)** — D2 exercise
   (if defect manifest uses D2) is 2nd industrial falsification
   after case_005. 2-of-N evidence triggers A3-v2 sub-DEC arc.
3. **DRM-19 mech files** — must fetch externally (UCSD / LLNL
   mirror). chemkinToFoam conversion is brand new for project.
4. **Highest infra climb** — 5+ artifact extractions likely;
   biggest sub-DEC budget consumer in roster.
5. **Chemistry startup is fragile** — cold-flow → enable chem →
   small Δt → ramp; do NOT skip stages. NaN at startup is the
   primary failure mode.
6. **First reacting case** — heavy V-series sourcing expected;
   reacting-low-Mach numerics-class root has no inheritance from
   any prior V-finding (Pattern 6).
7. **Effort budget 12-16h** — longest in roster. v3 may not fit
   in single sub-session; v2 stable + radiation-deferred-to-v3
   is acceptable sediment.

=== END ===

## Main session post-dispatch checklist
- [ ] Move case_009 row from "Active queue" to "In-flight"
- [ ] Update `case_index.md` with case_009 status=active
- [ ] Update `INDEX.md` kickoff list status reconciled
- [ ] When sub-session reports A2 `_run_shared` outcome on
      combustion-burner topology (if D1 in manifest; PASS =
      algorithm-runs-cleanly, NOT gap-detection per V25), update
      V22 / V25 evidence rows
- [ ] When sub-session reports A3 outcome on D2 redundancy overlay
      (if D2 in manifest), update V17 evidence; 2-of-N triggers
      A3-v2 sub-DEC arc draft
- [ ] When sub-session extracts chemkin loader / combustion thermo
      writer / species BC writer / combustion properties writer /
      mixture fraction post-processor infrastructure, evaluate for
      promotion to main-project shared services
