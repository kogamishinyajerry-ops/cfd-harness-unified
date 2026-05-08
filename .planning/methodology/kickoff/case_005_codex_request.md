# Codex Case-Design Request · case_005

> **Status**: drafted 2026-05-07 evening; about to be sent to Codex
> via `codex-relay-with gpt-5.5` (xhigh, 86gs).
>
> Same pattern as case_003 / case_004 requests — Codex 出题, then
> 6-check validation, then sub-session kickoff.

## Target

| field | value |
|---|---|
| case_id | `case_005_<short_name>` (Codex picks short_name; `case_005_rae_m2129_sduct` is the working name) |
| solver_class_target | internal compressible diffuser (subsonic-transonic), steady |
| numerics_class | **compressible-RANS** (new — no inheritance from case_002a/b/case_003/case_004) |
| coverage map row to fill | "Internal compressible diffuser (subsonic to transonic)" — currently 📝 proposed |
| CAD source priority | Tier 1 (T1.I1 RAE M2129 S-duct) preferred; Tier 3 fallback acceptable if Tier 1 doesn't fit |
| defect injection count | 2 |
| sandbox path suggestion | `~/Desktop/case_005_<short_name>/` |

## Why internal compressible diffuser as case_005

After case_004 (rotating machinery MRF), the coverage map's
remaining HIGH-priority pending classes:

| Class | Numerics class | Tier-1 quality | New infra | Fits as case_005? |
|---|---|---|---|---|
| Internal compressible diffuser | compressible-RANS | Excellent (RAE M2129) | Medium (compressible thermo + Mach BC + energy eq.) | **YES — picked** |
| External transonic | compressible-shock-density-based | Excellent (ONERA M6) | High (density-based solver) | Defer to case_006 |
| Multiphase VOF | multiphase-VOF | Good (KCS) | High (VOF + free surface) | Defer to case_007 |

case_005 is the **first compressible case** for the project. New
infrastructure forced:
- `thermophysicalProperties` (perfectGas + sutherland or const cv/cp)
- `T` field (temperature, energy equation)
- Compressible BCs: `totalPressure` inlet + `waveTransmissive` outlet
- `rhoSimpleFoam` (or `rhoPimpleFoam`) solver path
- DC60 distortion coefficient post-processing at AIP

These have no prior infrastructure in cfd-harness-unified;
case_005 will surface "missing-capability" V-findings (compressible
thermo writer, totalPressure BC writer, DC60 post-processor) the
same way case_003 / case_004 surface their respective gaps. This
is the Pillar 2 force-extraction pattern.

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

Four cases are already in the case fleet:
- case_002a (APU bay buoyantSimpleFoam, internal flow + buoyancy) — active
- case_002b (APU bay CHT, multi-region thermal coupling) — active
- case_003 (CRM-HLS, external high-Re + boundary layer, incompressible-RANS) — dispatched, deferred
- case_004 (NREL Phase VI rotor, MRF, incompressible-RANS-MRF) — dispatched, deferred

The next solver-class target is **internal compressible diffuser (subsonic-transonic)** — currently uncovered. You design case_005 to fill this row. case_005 is being drafted ahead of case_003/case_004's actual run; all three sit in the dispatched queue awaiting compute resources (user has Codex quota but limited compute right now).

## Required reading (in cfd-harness-unified repo)

Read these in order before designing:
1. .planning/methodology/codex_case_design_protocol.md — your contract (5 deliverables + validation steps)
2. .planning/methodology/component_bank.md — Tier-3 fallback menu + Defect Catalog D1-D10. **Note Lane B exclusions** (Ahmed body, NACA 0012, Sajben transonic diffuser, BFS, Ercoftac mixing tank — these are validation references, NOT primary roster, do NOT pick)
3. .planning/methodology/public_cad_sources.md — Tier 1+2 catalog (PRIORITY — check first; for case_005 the canonical Tier-1 candidate is **T1.I1 RAE M2129 S-duct** from RAE / NASA TMR archives)
4. .planning/methodology/kickoff/case_003_codex_response.md AND case_004_codex_response.md — examples of your prior case-design output (you wrote both); follow the same pattern
5. .planning/case_profiles/case_002a_apu_bay_buoyant_simple.md AND case_002b_apu_bay_cht.md — examples of the case-thread pattern your design will inherit
6. .planning/methodology/industrial_case_solver_findings.md — V-series; note Pattern 6 (numerics-class inheritance). Your design is **compressible-RANS** so it inherits NONE of the compressible-buoyant-RANS findings (V3-V13, V15) AND NONE of the incompressible-RANS or MRF findings (when case_003/case_004 accumulate). Pure new numerics root.

## Hard constraints

1. **Solver class**: internal compressible diffuser, subsonic-transonic. v1 solver target: `rhoSimpleFoam` (steady compressible, pressure-based). v2 fallback: `rhoPimpleFoam` ONLY if shock-induced unsteadiness or oscillatory residuals
2. **CAD source priority**: Tier 1 first. Strong candidate per public_cad_sources.md:
   - T1.I1 RAE M2129 S-duct — RAE / NASA TMR archives, public reference
   - T1.I3 NASA Energy Efficient Engine inlet — secondary if RAE M2129 license issues
   Tier 3 fallback only if no Tier 1 fits
3. **Defect injection**: exactly 2 defects from defect catalog (D1-D10 in component_bank.md). Document in defect manifest. Defects must NOT be in regions where reference experimental data is taken (RAE M2129 has published Mach contours at AIP and centerline pressure — keep those zones clean)
4. **Patch naming**: all body names must satisfy ^[A-Za-z][A-Za-z0-9_]*$ (OpenFOAM rule)
5. **Inlet/Outlet roles explicit**: parts manifest must declare inlet (`totalPressure` BC role) and outlet (`waveTransmissive` or `fixedValue p` BC role); these are NEW BC types not used by case_002a/b/case_003/case_004 (those used `fixedValue U` / `zeroGradient`)
6. **Energy equation explicit**: parts manifest must declare which patches need T BC (typically: inlet `totalTemperature` 288 K; walls `zeroGradient` adiabatic OR `fixedValue` if isothermal; outlet `inletOutlet`)
7. **AIP plane explicit**: parts manifest must include an "AIP" (Aerodynamic Interface Plane) named patch or `cuttingPlane` location for DC60 post-processing
8. **Determinism**: CadQuery script must regenerate byte-identical STEP given identical inputs
9. **Industrial flavor**: case must be recognizable as a real industrial component (RAE M2129 IS — it's the canonical UAV / cruise missile intake reference)
10. **Reference-data preservation** (Tier 1): inject defects in regions OUTSIDE published experimental measurement zones (NOT on the centerline, NOT at the AIP); note `reference_data_validity` in defect manifest
11. **Mach regime**: aim for AIP Mach ~0.4-0.6 (subsonic-transonic baseline). v1 must be shock-free or have at most a weak normal shock. STRONG shocks (M > 1.3) are case_006 territory, NOT case_005.

## Your 5 deliverables

Same format as case_003 / case_004. Per codex_case_design_protocol.md §"What Codex returns":

### 1. Engineering brief (Markdown)

Sections (mandatory): Component picked + bank ID / Engineering question / Physics signature (note compressible-RANS specifics: Mach, Re, T_ref, total pressure ratio) / Parts inventory (mark inlet / outlet / AIP explicitly with their BC types) / Boundary conditions plan (note totalPressure / waveTransmissive / temperature BC) / Expected metrics (DC60 distortion coefficient, recovery PR, AIP Mach map, centerline pressure) / Hypothesized failure modes (V-findings prediction including compressible-RANS-specific) / Defect injection summary / Sub-session estimated effort.

### 2. CAD generation script (Python, executable)

CadQuery preferred. Same requirements as case_003 / case_004 (deterministic, --out CLI, parametric constants, comments at decision points, cache fetch for Tier 1). Must:
- Define inlet, outlet, and AIP plane as separate named patches (or AIP as a cuttingPlane definition consumable by post-processing)
- Stationary domain (the duct + outlet plenum) as a properly named body
- Export STEP with named bodies preserved

### 3. STEP file path

Same format as case_003 / case_004.

### 4. Parts manifest YAML

Same schema as case_003 / case_004 PLUS:
- Each patch role explicitly declares its compressible BC types (U / p / T separately)
- AIP marker (either as a patch with `role: aip_plane` or a `cutting_planes:` block with axial position)
- Reference total pressure / total temperature for inlet (e.g., `p_total_inlet_pa`, `T_total_inlet_k`)
- Reference back pressure for outlet (e.g., `p_back_pa` for fixedValue path)

### 5. Defect manifest YAML

Same schema as case_003 / case_004. Two defects, catalog IDs from D1-D10. AIP and centerline must remain defect-free.

## Format your response

Wrap your full response in clear section headers (same as case_003 / case_004 response):

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
- Do NOT push the regime into strong shocks (M > 1.3 / shock-induced separation) — that's case_006 territory (compressible-shock-density-based with rhoCentralFoam). case_005 stays in the rhoSimpleFoam / rhoPimpleFoam regime
- Do NOT include MRF / rotating elements — case_004 covers that, case_005 is pure stationary internal compressible

## Begin
```

## Validation checklist (main session runs after Codex responds)

Before writing the per-case kickoff:

- [ ] CAD source picked (Tier 1 / 2 / 3 declared)
- [ ] If Tier 1: source URL valid + license confirmed (RAE M2129 typical: open academic, OK for derived STEP)
- [ ] CadQuery script executes locally (or at least py_compile passes)
- [ ] Generated STEP opens in FreeCAD without errors (deferred if cadquery not in main venv)
- [ ] FreeCAD reports body count + names matching parts manifest
- [ ] All patch names satisfy ^[A-Za-z][A-Za-z0-9_]*$
- [ ] **Inlet declared with `totalPressure` BC role**
- [ ] **Outlet declared with `waveTransmissive` or `fixedValue p` BC role**
- [ ] **AIP plane declared** (patch or cuttingPlane location)
- [ ] **T (temperature) BC declared on each patch** (energy equation explicit)
- [ ] **Reference total pressure + total temperature numerics specified** in manifest
- [ ] Both injected defects measurable in geometry
- [ ] AIP and centerline remain defect-free
- [ ] Defect manifest field `expected_advisor_to_catch` references a real (or pending) main-project advisor
- [ ] Engineering brief targets compressible-RANS (rhoSimpleFoam) + AIP Mach ~0.4-0.6 baseline

## After validation passes

1. Save Codex response at `kickoff/case_005_codex_response.md`
2. Format per-case kickoff at `kickoff/case_005_<name>.md`
3. Update `case_proposal_queue.md`: move case_005 row from Active queue to Dispatched
4. Update `case_index.md` with case_005 row, status=dispatched
5. Tell user: "case_005 kickoff ready. Single-fire continues — fire case_006 next?"
