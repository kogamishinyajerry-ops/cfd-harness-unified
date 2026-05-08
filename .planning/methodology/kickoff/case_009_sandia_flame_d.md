# Case 009 · Sandia Flame D · Sub-Session Kickoff

> Paste between `=== BEGIN ===` and `=== END ===` into a fresh
> Claude Code session. Designed by Codex (gpt-5.5 xhigh, 86gs,
> round 1 of 2). Validated 2026-05-08 — see
> `case_009_validation.md`. PASS WITH NOTES (highest infra climb;
> longest case in roster: 12-16h).

=== BEGIN ===

You are a Claude Code sub-session under cfd-harness-unified
orchestration. Task: **case_009_sandia_flame_d**.

⚠️ **Highest-effort case in the 10-case roster (12-16h, 3+
versions). Reacting-low-Mach is brand new for the project.**

## Project context
cfd-harness-unified at `/Users/Zhuanz/Desktop/cfd-harness-unified/`.
Per DEC-V61-198, accumulates industrial CFD experience. Eight
prior cases (002a/b active; 003-008 dispatched-deferred). Your
case fills **reacting-low-Mach combustion** — first reacting
case; biggest infrastructure climb in roster.

## Required reading
1. `.planning/decisions/2026-05-07_v61_198_apu_bay_strategic_pivot.md`
2. `.planning/case_proposal_queue.md`
3. `.planning/case_profiles/case_002a_*.md`, `case_002b_*.md`
4. `.planning/methodology/industrial_case_solver_findings.md` (Pattern 6: case_009 inherits NONE)
5. `.planning/methodology/solver_convergence_playbook.md`
6. `.planning/methodology/rag_corpus_format.md`
7. `~/Desktop/apu-bay-ventilation/` (sandbox layout)
8. `.planning/methodology/kickoff/case_009_codex_response.md`
9. `.planning/methodology/kickoff/case_009_validation.md`

## Hard guardrails
1. V130 advisory-only · V132 no AI-mutating routes
2. No date/calendar gating; OpenFOAM is truth source
3. Do NOT redesign the case
4. **DRM-19 primary** chemistry; if too expensive, drop to
   2-step Westbrook-Dryer fallback. **DO NOT use GRI-Mech 3.0**
   (53 species — too expensive for v1; v3 only after v2 stable)
5. **2D axisymmetric wedge** (5°); do NOT escalate to 3D LES
   (case_010 territory)
6. **Non-premixed diffusion flame** scope; do NOT add premixed
7. Use thin_wall_advisor / geometry_surgery if applicable
8. Z(r,z) and T(r,z) measurement stations at z/D = 7.5/15/30/45/60
   must remain mesh-clean

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

### Two defects (per Codex's manifest — read response file for exact IDs and locations)
Likely D2 (over-dense triangulation) + D1 or D6 (geometric defect).
Defect bodies on `coflow_plenum_mount_bracket` /
`coflow_plenum_mount_shim` / `bracket_lip_thin` — all OUTSIDE the
flame core and z/D measurement stations.

Run FreeCAD verification per defect manifest's verification
commands. Document A2-pending if D1 used (7th consecutive case).

## Six per-case standard moves
1. Reference profile at `case_profiles/case_009_sandia_flame_d.md`
2. V-series: chemistry timestep stability, PaSR vs EDC
   sensitivity, hot-pilot startup spikes, species boundedness,
   heat-release rate post-processing pitfalls, mixture-fraction
   Bilger formula edge cases, radiation coupling
3. Playbook S13+ candidates: "reactingFoam NaN at startup →
   verify cold-flow first stage; small Δt; chemistry off until
   stable" / "species mass fractions out of [0,1] → check thermo
   janaf coefficients vs UCSD mirror"
4. Stale-assumption fixes: 0.orig has no species fields;
   thermophysicalProperties has no reactingMixture path
5. Artifact extraction (LIKELY MULTIPLE for case_009):
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

## Boundaries
- CAN: end-to-end run, sandbox modify, sediment, <250 LOC
  artifact extraction (likely 5+ for this case), advisor-bias fixes
- CANNOT: redesign case, modify other cases, open new DEC arcs,
  upgrade to GRI-Mech 3.0 in v1, escalate to 3D LES

## Known issues
1. **A2 pending — likely 7-of-7 evidence after this case**
2. **DRM-19 mech files** — must fetch externally (UCSD / LLNL
   mirror). chemkinToFoam conversion is brand new
3. **Highest infra climb** — 5+ artifact extractions likely
4. **Chemistry startup is fragile** — cold-flow → enable chem →
   small Δt → ramp; do NOT skip stages
5. **First reacting case** — heavy V-series sourcing expected

=== END ===

## Main session post-dispatch checklist
- [ ] Move case_009 row from "Active queue" to "Dispatched"
- [ ] Update `case_index.md` with case_009 status=dispatched
- [ ] Update `INDEX.md` kickoff list
- [ ] When sub-session extracts chemkin loader / combustion thermo
      writer / species BC writer infrastructure, evaluate for promotion
