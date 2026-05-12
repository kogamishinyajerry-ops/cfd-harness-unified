# Case 016 · M219 Cavity DES + Acoustic · Sub-Session Kickoff

> Paste between `=== BEGIN ===` and `=== END ===` into a fresh
> Claude Code session. Designed by Codex (gpt-5.4 high, CRS,
> 228k tok single-round emit). Validated 2026-05-08 — see
> `case_016_validation.md`. PASS.
>
> **Phase 3 #2 of industrial-extension batch** — first
> aeroacoustic capability for project. Combines case_006
> compressible-shock + case_010 LES into compressible-DES
> compound root.
>
> **D6 + D9 BOTH FIRST INJECTIONS** — no LANDED advisors for
> "extra-body-in-fluid" or "curved-surface-tessellation-accuracy"
> patterns. Manual FreeCAD verification only. Post-Phase-3 retro
> evaluates advisor candidates.
>
> **Codex flagged + corrected a request math error**: original
> request claimed "0.1s ≥ 100 fundamental cycles"; at f1≈142 Hz
> that's only ~14 cycles. Codex set v1 min=0.12s, convergence
> window=0.75s for true 100-cycle R1 statistics.

=== BEGIN ===

You are a Claude Code sub-session under cfd-harness-unified
orchestration. Task: **case_016_m219_cavity_des_acoustic**.

**Phase 3 #2** — first aeroacoustic case (FW-H + Rossiter modes).

## Project context
cfd-harness-unified at `/Users/Zhuanz/Desktop/cfd-harness-unified/`.
16 prior cases (002a/b + 003-015).

## Required reading
1. `.planning/decisions/2026-05-07_v61_198_apu_bay_strategic_pivot.md`
2. `.planning/strategic/case_011_020_industrial_extension_roadmap_2026-05-08.md`
3. `.planning/strategic/case_013_020_dispatch_plan_2026-05-08.md`
4. `.planning/case_proposal_queue.md`
5. **`.planning/methodology/kickoff/case_006_codex_response.md`** —
   compressible-shock-density inheritance (V26-V32)
6. **`.planning/methodology/kickoff/case_010_codex_response.md`** —
   LES inheritance (V45-V46)
7. `.planning/case_profiles/case_006_onera_m6_transonic.md`
8. `.planning/methodology/industrial_case_solver_findings.md`
9. `.planning/methodology/knowledge_status_convention.md` — D6/D9
   first injections, advisor-gap markers
10. `.planning/methodology/kickoff/case_016_codex_response.md`
11. `.planning/methodology/kickoff/case_016_validation.md`

## Hard guardrails
1. V130 advisory-only · V132 no AI-mutating routes
2. No date/calendar gating
3. **No advisors for D6 or D9** — manual FreeCAD verification
4. Do NOT redesign — round-cap=3
5. **rhoPimpleFoam transient + IDDES** (NOT rhoCentralFoam — that's
   case_006; this is transient compressible)
6. **Non-reflective BCs at outer boundaries** required
7. **No new defects outside D1-D10**
8. **No 2D simplification** (cavity 3D spanwise required)

## Case identifier
`case_016_m219_cavity_des_acoustic` · solver-class
**rhoPimpleFoam + k-ω-SST IDDES** · numerics-class
**compressible-DES** (NEW compound root from 006 + 010)

## Codex brief summary
- Component: M219 weapons-bay cavity (Tier-1 UK MOD; bank ID
  `E4_m219_weapons_bay_cavity`)
- Geometry: M219 spec L:W:D = 5:1:1 (508×102×102 mm); upstream
  plate ≥ 6× L; downstream ≥ 4× L; far-field box ≥ 30× L
- Operating point: M=0.85, U=290 m/s, T=273.15 K, Re_L≈6e6
- Turbulence: k-ω-SST IDDES preferred; SA-DDES alternate
- FW-H: porous surface in cavity flow region; observer at
  (254.0, 0.0, 8000.0) mm (8m above)
- Time window: **v1 min 0.12s, convergence 0.75s** (corrected
  from request's 0.1s claim)
- Sample rate: dt ≤ 1e-4 s (CFL ≤ 1, Nyquist ≥ 5 kHz)
- Defects:
  - **D6**: 10 mm debris cube at (320.0, 18.0, -79.0) mm inside
    cavity. Advisor=NONE [QUESTIONABLE 2026-05-08]
  - **D9**: 16-facet approximation of LE+TE lip radii. Advisor=
    NONE [QUESTIONABLE 2026-05-08]
- Reference data: published K09 Rossiter modes 142/353/592/813
  Hz at M=0.85; SPL ~141.6/146.3/143.4/130.2 dB
- Effort: 12-14h, ~3 versions

## Codex CAD script (deliverable 2)
Save at `scripts/build_cad.py`. 325 LOC, deterministic.

```bash
cd ~/Desktop/case_016_m219_cavity_des_acoustic
python3 -m venv .venv
.venv/bin/pip install cadquery numpy pyyaml jinja2 trimesh
python scripts/build_cad.py --out inputs/cad_codex_v1.step
```

## DES + Acoustic setup (case_016 main work)

### `00_check_region.py`
Verify STEP has region_air + cavity patches + debris_cube + FW-H
surface.

### `02_blockmesh_shm.py`
blockMesh + sHM with refinement near cavity LE/TE shear layer +
debris_cube + FW-H porous surface region.

### `03_write_thermophysical.py`
Air ideal gas + Sutherland.

### `04_write_BCs.py`
ESI-compatible (V29 lesson from case_006):
- inflow: freestream + freestreamPressure at M=0.85
- outflow: waveTransmissive + pressureInletOutletVelocity
- top_far_field, far_field_port/starboard: waveTransmissive /
  freestream non-reflective
- cavity walls + flat plates + debris_cube: noSlip

### `05_write_turbulenceProperties.py`
```
simulationType  RAS;
RAS
{
    RASModel  kOmegaSSTIDDES;
    turbulence on;
    printCoeffs on;
}
```

### `06_write_fvSchemes.py`
DES-compatible:
- ddt: backward
- divSchemes: linearUpwindV grad(U) (or LUST grad(U))
- gradSchemes: Gauss linear
- laplacianSchemes: Gauss linear corrected

### `07_write_FW_H.py`
controlDict function objects:
- fwh1: porous surface integration; sample at every dt (or every
  2-3 dt)
- pressureProbes at K05 (279.4, 0.0, -102.0) and K09 (482.6, 0.0,
  -102.0); sample every dt
- forces1: drag on cavity_floor + walls + flat_plate_*

### `08_run_solver.sh`
1. potentialFoam initialization for M=0.85 freestream
2. rhoPimpleFoam transient at dt=1e-4 s
3. Run 0.05 s settling
4. Run minimum 0.12 s with FW-H + probe sampling
5. Recommended convergence 0.75 s for full R1 spectrum

### `09_compute_rossiter_modes.py`
- FFT of K05 + K09 pressure time series
- Locate Rossiter peaks; compare to 142/353/592/813 Hz
- SPL spectrum

### `10_compute_drag_increment.py`
Run baseline (cavity replaced by flush panel) once; compute
Δdrag.

### `11_compute_FW_H_far_field.py`
FW-H far-field SPL at observer (254.0, 0.0, 8000.0).

## Defect verification

### D6 (10mm debris cube at (320,18,-79)) — NO LANDED ADVISOR

> **First D6 injection**. No advisor for extra-body-in-fluid.

**Step 1**: FreeCAD body count verification (cavity should have
N+1 bodies including debris_cube).
**Step 2**: bbox verification (10mm cube confirmed).
**Step 3**: V-finding: D6 advisor-gap surfaced; flag for harvest
003 retro evaluation of "fluid-body-inventory advisor" candidate.

### D9 (16-facet LE+TE lips) — NO LANDED ADVISOR

> **First D9 injection**. No advisor for curved-surface
> tessellation accuracy.

**Step 1**: FreeCAD chord-length comparison vs smooth reference
arc.
**Step 2**: Document facet count + max chord deviation.
**Step 3**: V-finding: D9 advisor-gap surfaced; flag for harvest
003 retro evaluation of "curved-surface-tessellation-accuracy
advisor" candidate.

## Six per-case standard moves

1. Reference profile at `case_profiles/case_016_m219_cavity_des_acoustic.md`
2. V-series append: tonal-noise capture vs cavity LE refinement,
   FW-H surface placement (must be inside resolved-turbulence
   region), FFT window length sufficiency for low Rossiter modes,
   acoustic boundary reflection, IDDES blending function
   sensitivity. ALSO: **D6 advisor-gap V-finding** + **D9
   advisor-gap V-finding** + **first compound-DES root validation**.
3. Playbook S15+ candidates:
   - "Tonal noise weak → check cavity LE refinement (≥5 cells
     across shear layer)"
   - "FW-H spectrum noisy → move porous surface inside resolved
     turbulence region"
   - "Low Rossiter mode missing → extend time window to 0.75 s
     for 100-cycle FFT"
   - "Acoustic reflection contamination → verify waveTransmissive
     coefficient + far-field box ≥ 30L"
4. Stale-assumption fixes: case_006 templates may need
   transient-DES variants; case_010 LES templates need
   compressible variant. Commit tag pattern.
5. Artifact extraction (4-5 likely):
   - `rossiter_mode_post_processor.py`
   - `FW_H_acoustic_writer.py`
   - `cavity_spl_advisor.py`
   - `frequency_spectrum_extractor.py`
6. RAG corpus: 5 artifacts.

## Sandbox structure
```
~/Desktop/case_016_m219_cavity_des_acoustic/
├── README.md, Makefile, .venv/
├── inputs/, templates/, scripts/, case/, evidence/
```

## Sediment + commit convention
Same as cases 011-015. `confidence: <high|med|low>` trailer.

## Boundaries
- CAN: end-to-end run, sandbox modify, sediment commits, <250 LOC
  artifact extraction (4-5 likely)
- CANNOT: redesign case, modify other cases, use 2D simplification,
  use rhoCentralFoam (transient is the case identity), exceed 14h

## Known issues
1. **D6 first injection — no advisor** — flag advisor-gap
2. **D9 first injection — no advisor** — flag advisor-gap
3. **First aeroacoustic for project** — FW-H + IDDES infrastructure
   all-new
4. **Time-window cost** — 0.75s convergence at dt=1e-4 = 7,500
   timesteps; budget compute carefully
5. **Acoustic reflection** — non-reflective BC critical; far-field
   box geometry sized appropriately
6. **Tonal capture sensitivity** — cavity LE shear layer must be
   refined to capture coherent vortices spawning Rossiter modes
7. **K05 inferred at x/L=0.55** — Codex documented the inference
   (K09 at x/L=0.95 is the explicit benchmark station; K05
   exact coordinate per M219 documentation may differ; sub-session
   can refine)

## Strategic role within batch

After case_016 lands, project demonstrates:
- compressible + DES compose (validates 2nd compound numerics
  root after case_015)
- FW-H acoustic + Rossiter mode infrastructure
- D6 + D9 advisor-gap V-findings consolidate (along with case_012
  D7) → harvest 003 retro evaluates A4-A8 advisor candidates
- New industry KPIs: SPL spectrum, Rossiter modes, FW-H far-field
  → first aeroacoustic capability

This **closes Phase 3** (cases 015 + 016). Phase 3 close unblocks
Phase 4 (cases 017-020 specialized industrial verticals).

=== END ===

## Main session post-dispatch checklist
- [ ] Move case_016 to Dispatched
- [ ] Update case_index.md
- [ ] Update INDEX.md
- [ ] D6 + D9 advisor-gap V-findings → harvest 003 retro
- [ ] When sub-session extracts FW-H / Rossiter / SPL post-
      processors: evaluate promotion
- [ ] After case_015 + case_016 sediment: trigger Phase 3 close
