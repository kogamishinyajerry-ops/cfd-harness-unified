# Codex Case-Design Request · case_006

> **Status**: drafted 2026-05-08; about to be sent to Codex
> via `codex-relay-with gpt-5.5` (xhigh, 86gs).
>
> Same pattern as case_003 / case_004 / case_005 requests — Codex
> 出题, then 6-check validation, then sub-session kickoff.

## Target

| field | value |
|---|---|
| case_id | `case_006_<short_name>` (Codex picks short_name; `case_006_onera_m6_transonic` is the working name) |
| solver_class_target | external transonic 3D wing (compressible high-speed, shock-capturing) |
| numerics_class | **compressible-shock-density-based** (new — no inheritance from case_002a/b/case_003/case_004/case_005) |
| coverage map row to fill | "Compressible high-speed (shock-density-based)" — currently 📝 proposed |
| CAD source priority | Tier 1 (T1.A3 ONERA M6 wing) preferred; Tier 3 fallback acceptable if Tier 1 doesn't fit |
| defect injection count | 2 |
| sandbox path suggestion | `~/Desktop/case_006_<short_name>/` |

## Why ONERA M6 transonic as case_006

After case_005 (compressible-RANS internal), the next high-priority
pending row is compressible-shock-density-based external. Coverage
landscape:

| Class | Numerics class | Tier-1 quality | New infra | Fits as case_006? |
|---|---|---|---|---|
| External transonic wing | compressible-shock-density-based | Excellent (ONERA M6) | High (density-based solver, Riemann solver, shock capturing) | **YES — picked** |
| Multiphase VOF | multiphase-VOF | Good (KCS) | Very high (free-surface, MULES, alpha eq.) | Defer to case_007 |
| Lagrangian particle | RANS-Lagrangian | Good (NASA IRT) | High (kinematic cloud, particle injection) | Defer to case_008 |

case_006 is the **first density-based solver case** for the
project. Distinct from case_005 which uses pressure-based
rhoSimpleFoam. New infrastructure forced:
- `rhoCentralFoam` solver path (Kurganov central-upwind scheme)
- `fluxScheme Kurganov;` in `fvSchemes`
- shock-capturing limiters (`Minmod`, `vanLeer` on convective
  fluxes for ρ, ρU, ρE)
- Mach-number probes + λ-shock detection post-processing
- Surface Cp slice at multiple spans for AGARD validation
- Symmetry plane treatment at wing root

Pure new numerics root — inherits NONE of the prior 5 cases'
findings (per Pattern 6 in industrial_case_solver_findings.md).

## ONERA M6 reference conditions (for Codex's brief grounding)

The canonical AGARD AR-138 / Schmitt-Charpin test point:
- M_inf = 0.8395
- α = 3.06°
- Re = 11.72e6 (chord-based)
- T_inf ≈ 255-300 K (depends on test source)
- p_inf ≈ 35-45 kPa (varies)
- Geometry: semi-span 1.1963 m, root chord 0.8059 m, taper ratio
  0.562, sweep 30° at LE, ONERA D-section airfoil
- Published Cp at 7 spans: η = 0.20, 0.44, 0.65, 0.80, 0.90, 0.95, 0.99
- Lambda-shock signature: forward shock + aft shock merging
  toward tip

Codex picks parameters; this is just to ground the prompt.

## Codex prompt (paste-ready)

```
You are Codex, acting as case 出题者 (case designer) for the
cfd-harness-unified project. The project main session is asking
you to design ONE industrial CFD case end-to-end so a Claude Code
sub-session can execute it.

This is your design task, not your solver task. You design; the
sub-session runs.

## Project context (read first)

cfd-harness-unified is a CFD harness over OpenFOAM at /Users/Zhuanz/Desktop/cfd-harness-unified/. Per DEC-V61-198 (2026-05-07 strategic charter), the project's development philosophy is "container that accumulates industrial CFD experience" — each industrial case extends a solver-class coverage axis and feeds the V-series finding index.

Five cases are already in the case fleet:
- case_002a (APU bay buoyantSimpleFoam, internal flow + buoyancy) — active
- case_002b (APU bay CHT, multi-region thermal coupling) — active
- case_003 (CRM-HLS, external high-Re + boundary layer, incompressible-RANS) — dispatched, deferred
- case_004 (NREL Phase VI rotor, MRF, incompressible-RANS-MRF) — dispatched, deferred
- case_005 (RAE M2129 S-duct, internal compressible diffuser, compressible-RANS / rhoSimpleFoam) — dispatched, deferred

The next solver-class target is **external transonic 3D wing (compressible high-speed, shock-capturing)** — currently uncovered. You design case_006 to fill this row. This is the first DENSITY-BASED solver case for the project (case_005 was pressure-based rhoSimpleFoam; case_006 forces rhoCentralFoam with Kurganov central-upwind). All 6 cases sit in the dispatched queue awaiting compute resources.

## Required reading (in cfd-harness-unified repo)

Read these in order before designing:
1. .planning/methodology/codex_case_design_protocol.md — your contract (5 deliverables + validation steps)
2. .planning/methodology/component_bank.md — Tier-3 fallback menu + Defect Catalog D1-D10. **Note Lane B exclusions** (Ahmed body, NACA 0012, Sajben transonic diffuser, BFS, Ercoftac mixing tank — these are validation references, NOT primary roster, do NOT pick)
3. .planning/methodology/public_cad_sources.md — Tier 1+2 catalog (PRIORITY — check first; for case_006 the canonical Tier-1 candidate is **T1.A3 ONERA M6 wing** from ONERA public dataset / AGARD AR-138)
4. .planning/methodology/kickoff/case_003_codex_response.md, case_004_codex_response.md, case_005_codex_response.md — examples of your prior case-design output (you wrote all three); follow the same pattern
5. .planning/case_profiles/case_002a_apu_bay_buoyant_simple.md AND case_002b_apu_bay_cht.md — examples of the case-thread pattern your design will inherit
6. .planning/methodology/industrial_case_solver_findings.md — V-series; note Pattern 6 (numerics-class inheritance). Your design is **compressible-shock-density-based** so it inherits NONE of the compressible-buoyant-RANS findings (V3-V13, V15), NONE of the incompressible-RANS findings (case_003), NONE of the MRF findings (case_004), AND NONE of case_005's pressure-based compressible-RANS findings. Pure new numerics root.

## Hard constraints

1. **Solver class**: external transonic 3D wing, density-based shock-capturing. v1 solver target: `rhoCentralFoam` (Kurganov central-upwind, density-based). v2 fallback: `rhoCentralDyMFoam` for moving-mesh deformation OR `rhoPimpleFoam` (pressure-based) ONLY if rhoCentralFoam suffers excessive numerical dissipation that wipes out the lambda-shock signature
2. **CAD source priority**: Tier 1 first. Strong candidate per public_cad_sources.md:
   - T1.A3 ONERA M6 wing — ONERA public dataset, AGARD AR-138 / Schmitt-Charpin reference
   - T1.A1 NASA CRM cruise configuration — alternative if M6 license issues (but case_003 already uses CRM-HLS variant; sub-session might find collision confusing)
   Tier 3 fallback only if no Tier 1 fits
3. **Defect injection**: exactly 2 defects from defect catalog (D1-D10 in component_bank.md). Document in defect manifest. Defects must NOT be in regions where reference experimental data is taken — for ONERA M6 this means NO defects on upper or lower wing surfaces between root and tip in the suction/pressure-side regions where AGARD published Cp at η = 0.20, 0.44, 0.65, 0.80, 0.90, 0.95, 0.99
4. **Patch naming**: all body names must satisfy ^[A-Za-z][A-Za-z0-9_]*$ (OpenFOAM rule)
5. **Symmetry plane explicit**: parts manifest must declare a `symmetry_plane_root` patch at the wing root (standard practice for half-wing transonic cases) with `bc.U: symmetry`, `bc.p: symmetry`, `bc.T: symmetry`
6. **Farfield BC family explicit**: parts manifest must declare farfield patches with `bc.U: characteristicVelocityInletOutletVelocity` (or `freestream` family) and `bc.p: characteristicPressureInletOutletPressure` — these are NEW BC types not used by case_005 (totalPressure / waveTransmissive)
7. **Density-based fvSchemes hint**: parts manifest's `numerics_hints:` block should declare `fluxScheme: Kurganov` (or `Tadmor`), and shock-limiter choices for ρ/ρU/ρE convective fluxes
8. **Shock-detection post-processing explicit**: parts manifest must include `shock_detection:` block with the engineering metric (e.g., max ∂M/∂n on the upper surface, or λ-shock pattern visualization at η = 0.65 and 0.95)
9. **Determinism**: CadQuery script must regenerate byte-identical STEP given identical inputs
10. **Industrial flavor**: case must be recognizable as a real industrial component (ONERA M6 IS — it's the canonical transonic wing reference for shock-capturing CFD validation)
11. **Reference-data preservation** (Tier 1): inject defects in regions OUTSIDE the published Cp measurement zones; note `reference_data_validity` in defect manifest. Likely safe defect locations: wing root fillet (away from spans) or tip cap (η=0.99 still has Cp data, but tip CAP itself — the 3D rounded end — is not part of the Cp validation, so a defect ON the tip cap geometry is OK if it doesn't bleed into the η=0.99 station)
12. **Mach regime**: aim for M_inf around 0.84 (canonical Schmitt-Charpin point) producing the well-known lambda-shock pattern. v1 must capture both forward and aft shocks. STRONG separated regimes (M_inf > 0.95 or α > 6°) are out of scope for case_006 — those would force LES / DES territory (case_010)

## Your 5 deliverables

Same format as case_003 / case_004 / case_005. Per codex_case_design_protocol.md §"What Codex returns":

### 1. Engineering brief (Markdown)

Sections (mandatory): Component picked + bank ID / Engineering question / Physics signature (note compressible-shock-density-based specifics: M_inf, α, Re, T_inf, p_inf, expected lambda-shock structure) / Parts inventory (mark wing surfaces, root symmetry, farfield, tip cap explicitly with their BC types) / Boundary conditions plan (note characteristicVelocity / characteristicPressure / symmetry / freestream BC) / Expected metrics (Cp at 7 published spans, lambda-shock map, integrated Cl/Cd/Cm, max upper-surface Mach) / Hypothesized failure modes (V-findings prediction including density-based shock-capturing-specific) / Defect injection summary / Sub-session estimated effort.

### 2. CAD generation script (Python, executable)

CadQuery preferred. Same requirements as case_003 / case_004 / case_005 (deterministic, --out CLI, parametric constants, comments at decision points, cache fetch for Tier 1). Must:
- Define wing surface (one body or split upper/lower) with ONERA D-section airfoil and the published planform parameters (semi-span, taper, sweep, twist if any)
- Define wing root as a planar face on the symmetry plane
- Define farfield as box or hemisphere outer boundary, sized ≥ 25 chord lengths from wing in all directions to avoid blockage
- Optional: tip cap as separate named body (so a defect can live there without polluting Cp stations)
- Export STEP with named bodies preserved

### 3. STEP file path

Same format as case_003 / case_004 / case_005.

### 4. Parts manifest YAML

Same schema as case_003 / case_004 / case_005 PLUS:
- Each patch role explicitly declares its compressible-density-based BC types (U / p / T separately)
- `freestream:` block with M_inf, α, p_inf, T_inf, Re_chord, T_total_inf, p_total_inf reference values
- `numerics_hints:` block with `fluxScheme: Kurganov`, `shock_limiter` choices, `ddtSchemes: backward` or steady-state `localEuler`
- `validation_stations:` block listing the 7 AGARD η stations + their published Cp source URL
- `shock_detection:` block describing the engineering metric

### 5. Defect manifest YAML

Same schema as case_003 / case_004 / case_005. Two defects, catalog IDs from D1-D10. AGARD Cp stations and centerline (root symmetry plane) must remain defect-free.

## Format your response

Wrap your full response in clear section headers (same as case_003 / case_004 / case_005 response):

## Deliverable 1 — Engineering brief
<markdown>

## Deliverable 2 — CAD generation script
```python
<full script>
```

## Deliverable 3 — STEP file path
<single path string>

## Deliverable 4 — Parts manifest
```yaml
<full yaml>
```

## Deliverable 5 — Defect manifest
```yaml
<full yaml>
```

## Round budget

Round 1 of 2 (round 2 reserved for revision if validation fails).

## What you should NOT do

- Do NOT design the case to be easy. Industrial CAD is messy
- Do NOT skip the defect injection
- Do NOT pick Ahmed body / NACA 0012 / Sajben diffuser / BFS / Ercoftac mixing tank (Lane B validation references — explicitly excluded)
- Do NOT write a CAD script that requires interactive GUI input
- Do NOT propose new defect types not in catalog (D1-D10)
- Do NOT pick a 2D airfoil — case_006 is 3D wing (RAE 2822 2D would also be fine technically but the user explicitly wants the 3D wing complexity for industrial flavor and to force more sHM features)
- Do NOT pick the cruise CRM (T1.A1) — case_003 already covers CRM-HLS variant; risk of mental collision
- Do NOT push into separated transonic regimes (M_inf > 0.95 OR α > 6°) — that's case_010 LES territory
- Do NOT include MRF / rotating elements — case_004 covers that
- Do NOT include heat transfer or buoyancy — case_002a/b cover those

## Begin
```

## Validation checklist (main session runs after Codex responds)

Before writing the per-case kickoff:

- [ ] CAD source picked (Tier 1 / 2 / 3 declared)
- [ ] If Tier 1: source URL valid + license confirmed (ONERA M6 typical: open academic, OK for derived STEP)
- [ ] CadQuery script syntax-clean (`python3 -m py_compile`)
- [ ] Generated STEP opens in FreeCAD without errors (deferred if cadquery not in main venv)
- [ ] FreeCAD reports body count + names matching parts manifest
- [ ] All patch names satisfy ^[A-Za-z][A-Za-z0-9_]*$
- [ ] **Symmetry plane declared at wing root** with `bc.U: symmetry`, `bc.p: symmetry`, `bc.T: symmetry`
- [ ] **Farfield BC declared** with characteristicVelocity / characteristicPressure (or freestream family)
- [ ] **freestream block** in manifest with M_inf, α, p_inf, T_inf, Re_chord, T_total_inf, p_total_inf
- [ ] **numerics_hints block** with fluxScheme + shock_limiter
- [ ] **validation_stations block** with 7 AGARD η stations
- [ ] **shock_detection block** with engineering metric
- [ ] Both injected defects measurable in geometry
- [ ] Defects NOT on Cp validation stations (η = 0.20, 0.44, 0.65, 0.80, 0.90, 0.95, 0.99 on upper/lower surface)
- [ ] Defect manifest field `expected_advisor_to_catch` references a real (or pending) main-project advisor
- [ ] Engineering brief targets compressible-shock-density-based (rhoCentralFoam) + M_inf ≈ 0.84, α ≈ 3°

## After validation passes

1. Save Codex response at `kickoff/case_006_codex_response.md`
2. Format per-case kickoff at `kickoff/case_006_<name>.md`
3. Update `case_proposal_queue.md`: move case_006 row from Active queue to Dispatched
4. Update `case_index.md` with case_006 row, status=dispatched
5. Tell user: "case_006 kickoff ready. Single-fire continues — fire case_007 KCS ship VOF next? (license verification needed first)"
