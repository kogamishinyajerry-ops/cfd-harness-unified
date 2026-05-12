# Case 017 · Pin-Fin Electronic Heatsink · Sub-Session Kickoff

> Paste between `=== BEGIN ===` and `=== END ===` into a fresh
> Claude Code session. Designed by Codex (gpt-5.4 high, CRS,
> 157k tok single-round emit). Validated 2026-05-08 — see
> `case_017_validation.md`. PASS.
>
> **Phase 4 #1 of industrial-extension batch** — microscale CHT
> extension. Booming data center / EV battery / IGBT industry.
> Re-anchors `A1` component-bank entry to its ORIGINAL pin-fin
> heatsink meaning (case_011 promoted A1 to compact HX; case_017
> validates A1 at native scale).
>
> **D8 thin_wall_advisor LANDED + [VALIDATED 6-of-6]** — case_017
> = **9th cross-topology arc data point**.
>
> **D9 faceted-pin** — second or third D9 evidence (after case_016
> + possibly case_017); helps consolidate D9 advisor decision.

=== BEGIN ===

You are a Claude Code sub-session under cfd-harness-unified
orchestration. Task: **case_017_pin_fin_electronic_heatsink**.

**Phase 4 #1** — microscale CHT for electronic cooling.

## Project context
17 prior cases (002a/b + 003-016).

## Required reading
1. `.planning/strategic/case_011_020_industrial_extension_roadmap_2026-05-08.md`
2. `.planning/strategic/case_013_020_dispatch_plan_2026-05-08.md`
3. `.planning/case_proposal_queue.md`
4. **`.planning/methodology/kickoff/case_002b_codex_response.md`** — CHT inheritance
5. **`.planning/methodology/kickoff/case_011_codex_response.md`** — multi-region patterns (case_017 is 4-region; A1 reinterpretation)
6. `.planning/methodology/kickoff/case_016_codex_response.md` — D9 first-injection precedent
7. `.planning/case_profiles/case_002b_apu_bay_cht.md`
8. `.planning/methodology/industrial_case_solver_findings.md` (V14/V15 + multi-region findings)
9. `.planning/methodology/knowledge_status_convention.md`
10. `.planning/methodology/kickoff/case_017_codex_response.md`
11. `.planning/methodology/kickoff/case_017_validation.md`

## Hard guardrails
1. V130 advisory · V132 no AI-mutating routes
2. No date/calendar gating
3. Use `thin_wall_advisor` for D8 (LANDED, [VALIDATED 6-of-6], 9th arc data point)
4. For D9: NO LANDED advisor; manual chord-length verification
5. Do NOT redesign — round-cap=3
6. **chtMultiRegionFoam steady · 4 regions** (air + chip + TIM + heatsink)
7. **Re_pin laminar/transitional** — do NOT default to k-ε; document choice
8. **No new defects outside D1-D10**
9. Do NOT add `isSame()` fast-path (V2 lesson)

## Case identifier
`case_017_pin_fin_electronic_heatsink` · solver-class
**chtMultiRegionFoam steady** · numerics-class **chtMultiRegionFoam
microscale** (extends case_002b — partial inheritance with scale
shift to mm/μm)

## Codex brief summary
- Component: pin-fin electronic heatsink (bank ID `A1` ORIGINAL)
- Geometry:
  - Heatsink base 50×50×5 mm
  - Chip die 10×10×0.7 mm (silicon)
  - TIM layer (thermal interface material) ~0.05-0.10 mm
  - Pin-fin array: per Codex CAD (8×8 or 10×10; D=1-2 mm;
    H=10-15 mm; pitch 2.5-4 mm)
- Thermophysics:
  - Air at 25°C inlet
  - Silicon (chip): k=130 W/m·K
  - Aluminum 6063 (heatsink): k=200 W/m·K
  - TIM: k=4 W/m·K
- Operating point:
  - Air U=2-5 m/s, T=298.15 K
  - Power: 50-100 W from chip die
  - Re_pin ≈ 300-400 (laminar/transitional)
  - T_chip target < 85°C
- Solver: chtMultiRegionFoam steady (4 regions)
- Defects:
  - **D8**: 4 corner pins thinned to 0.5 mm (within 0.3-0.6 mm spec)
  - **D9**: 4 inboard corner-adjacent pins faceted to 10-sided
    polygon (within 8-12 facets spec)
- Effort: 8-10h, ~3 versions

## Codex CAD script (deliverable 2)
Save at `scripts/build_cad.py`. 179 LOC, deterministic. CadQuery
parametric, exports STEP with 4 fused regions.

```bash
cd ~/Desktop/case_017_pin_fin_electronic_heatsink
python3 -m venv .venv
.venv/bin/pip install cadquery numpy pyyaml jinja2 trimesh
python scripts/build_cad.py --out inputs/cad_codex_v1.step
```

## Multi-region setup (case_017 main work — 4 regions)

### `00_check_regions.py`
Verify 4 regions: region_air + region_chip_die + region_tim +
region_heatsink.

### `02_split_mesh_regions.py`
blockMesh + sHM + `splitMeshRegions -cellZones -overwrite`.
Refine near pin tips + chip die surface + TIM layer (very thin).

### `03_write_regionProperties.py`
```
regions
(
    fluid (region_air)
    solid (region_chip_die region_tim region_heatsink)
);
```

### `04_write_thermophysical.py` per region
- region_air: air at 25°C, ρ=1.2, μ=1.8e-5
- region_chip_die: hSolidThermo silicon, k=130
- region_tim: hSolidThermo thermal grease, k=4
- region_heatsink: hSolidThermo aluminum 6063, k=200

### `05_write_BCs.py`
**Fluid patches**:
- air_inlet: flowRateInletVelocity, T=298.15K
- air_outlet: pressureOutlet
**Solid surface BCs**:
- chip_bottom (chip die bottom face): fixedHeatFlux = P/A_chip
- outer faces (chip top covered by TIM, TIM covered by heatsink,
  heatsink outer): zeroGradient
**Conjugate interfaces** (3 fluid↔solid + 2 solid↔solid):
- air↔heatsink_pins / air↔heatsink_base:
  turbulentTemperatureCoupledBaffleMixed
- chip_die↔TIM: solidThermo coupled
- TIM↔heatsink: solidThermo coupled

### `06_write_fvSchemes.py`
Steady laminar/transitional:
- ddt: steadyState
- divSchemes: linearUpwind grad(U), limitedLinear 1 for T
- gradSchemes: Gauss linear
- laplacianSchemes: Gauss linear corrected

### `07_run_solver.sh`
chtMultiRegionFoam steady; convergence < 1e-5; verify T_chip
distribution stable.

### `08_compute_R_theta.py`
T_chip = max(T) on chip_die top surface
R_θ_junction-to-ambient = (T_chip - T_air_in) / P_chip
Compare to TIMA/IBM correlation prediction ± 15%.

### `09_compute_local_h.py`
Per-pin h_local on 4 representative pins:
- 2 corner thin (D8) pins
- 2 corner faceted (D9) pins
- 1 center pin
- 1 edge nominal pin
Document h variation.

## Defect verification

### D8 (4 corner pins 0.5 mm thinned) — thin_wall_advisor LANDED [VALIDATED 6-of-6]

> case_017 = 9th cross-topology arc data point (after expected
> case_010 6-of-6 + case_011 7th + case_014 8th).

**Step 1**: FreeCAD bbox-min on each thin corner pin; expected 0.5 mm.
**Step 2**: thin_wall_advisor exercise (expected critical warnings).
**Step 3**: 9-of-9 consistency check or context-sensitivity finding.

### D9 (4 inboard corner-adjacent pins 10-faceted) — NO LANDED ADVISOR

> 2nd or 3rd D9 evidence (after case_016 + possibly case_020).

**Step 1**: FreeCAD chord-length comparison vs smooth circular pin.
**Step 2**: V-finding: D9 advisor-gap evidence accumulating.
**Step 3**: Post-Phase-4 retro: D9 advisor-candidate decision.

## Six per-case standard moves

1. Reference profile at `case_profiles/case_017_pin_fin_electronic_heatsink.md`
2. V-series append: chip-scale meshing sensitivity, low-Re pin-array
   transitional regime, solid-solid conjugate BC handling (3-pair
   stack), faceted-pin h_local deviation, thin-pin thermal short-
   circuit. **9th D8 cross-topology arc + 2nd/3rd D9 evidence**.
3. Playbook S15+ candidates:
   - "Microscale conjugate residual oscillation → relax T 0.95→0.85"
   - "Solid-solid coupling instability → check TIM layer mesh
     resolution (≥3 cells across)"
4. Stale-assumption fixes: case_002b/case_011 templates may need
   solid-solid conjugate variants. Commit tag pattern.
5. Artifact extraction (3-4 likely):
   - `r_theta_post_processor.py`
   - `local_h_calculator.py`
   - `thermal_resistance_advisor.py`
   - (optional) `solid_solid_conjugate_writer.py`
6. RAG corpus: 5 artifacts.

## Sandbox structure
```
~/Desktop/case_017_pin_fin_electronic_heatsink/
├── README.md, Makefile, .venv/
├── inputs/, templates/, scripts/, case/, evidence/
```

## Sediment + commit convention
Same as cases 011-016. `confidence: <high|med|low>` trailer.

## Boundaries
- CAN: end-to-end, sandbox, sediment, <250 LOC artifact extraction (3-4)
- CANNOT: redesign, k-ε without rationale, single-region promotion,
  exceed 10h

## Known issues
1. **9th D8 cross-topology arc** — chip-scale topology data point
2. **2nd/3rd D9 evidence** — D9 advisor-gap accumulating
3. **First solid-solid conjugate (3-pair stack)** — TIM layer
   adds chip↔TIM + TIM↔heatsink couplings beyond 002b's single
   fluid↔solid pair
4. **TIM layer thinness** — 0.05-0.10 mm requires careful mesh
   resolution
5. **A1 bank entry re-anchoring** — case_011 promoted A1 to
   compact HX; case_017 uses A1's ORIGINAL pin-fin heatsink
   meaning. Component_bank.md may need split: A1a (compact HX,
   case_011) + A1b (pin-fin heatsink, case_017)

## Strategic role within batch

After case_017 lands, project demonstrates:
- chtMultiRegion at chip scale (mm/μm)
- 4-region setup with solid-solid conjugate
- Pattern 6 numerics-class inheritance with scale shift
- 9th D8 [VALIDATED] + 2nd/3rd D9 evidence
- Industry KPI: R_θ junction-to-ambient (CPU/GPU/IGBT/EV-battery
  thermal industry)

This is **Phase 4 #1**; remaining Phase 4 cases are 018-020
(cyclone / static mixer / porous filter).

=== END ===

## Main session post-dispatch checklist
- [ ] Move case_017 to Dispatched
- [ ] Update case_index.md / INDEX.md
- [ ] When sub-session reports D8 outcome: 9th cross-topology data point
- [ ] When sub-session reports D9 outcome: 2nd-3rd D9 advisor-gap evidence
- [ ] When sub-session extracts R_θ / h_local post-processors: evaluate promotion
- [ ] component_bank.md: consider A1a/A1b split (compact HX vs pin-fin heatsink)
