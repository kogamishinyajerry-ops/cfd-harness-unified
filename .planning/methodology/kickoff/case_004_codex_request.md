# Codex Case-Design Request · case_004

> **Status**: SENT to Codex 2026-05-07 evening (gpt-5.5 xhigh via
> codex-relay-with). Round 1 returned `case_004_nrel_phase_vi_mrf`.
> Validation: PASS WITH NOTES (see `case_004_validation.md`).
> Kickoff: `case_004_nrel_phase_vi_mrf.md` (paste-ready).
>
> Same pattern as case_003 request — Codex 出题, then 6-check
> validation, then sub-session kickoff.

## Target

| field | value |
|---|---|
| case_id | `case_004_<short_name>` (Codex picks short_name) |
| solver_class_target | rotating machinery (steady MRF; transient sliding-mesh as v2 only if v1 unstable) |
| numerics_class | incompressible-RANS-MRF (new — no inheritance from case_002a/b/case_003) |
| coverage map row to fill | "Rotating machinery (MRF / sliding mesh)" — currently ⏸️ pending |
| CAD source priority | Tier 1 (NREL Phase VI / NREL 5MW / NASA Stage 35 / DLR HART-II / etc.) preferred; Tier 3 fallback acceptable if Tier 1 doesn't fit |
| defect injection count | 2 |
| sandbox path suggestion | `~/Desktop/case_004_<short_name>/` |

## Why rotating machinery as case_004

After case_003 (external high-Re + boundary layer, incompressible-RANS), the
coverage map's pending classes by industrial impact and Tier-1 availability:

| Class | Impact | Tier-1 quality | Effort | Fits as case_004? |
|---|---|---|---|---|
| Rotating machinery (MRF) | Huge (turbomachinery is a major CFD market) | Excellent (NREL, NASA Stage series) | Medium-high (MRF setup is the long pole) | **YES — picked** |
| Internal compressible diffuser | Medium | Good (RAE M2129) | Medium | Defer to case_005 |
| Compressible high-speed | Medium | Limited Tier-1 (Sajben is Lane-B-only) | Low-medium | Defer to case_006 |

Rotating machinery forces NEW capabilities the project doesn't have:
- `cellZones` definition for rotating zone vs stationary
- MRF dictionary (`MRFProperties`)
- Periodic boundary writer (`cyclic` / `cyclicAMI`)
- Rotating-frame post-processing (head-vs-flow curve, thrust)

These capabilities have no prior infrastructure in cfd-harness-unified; case_004
will surface "missing-capability" V-findings the same way case_003 will surface
A2-pending. This is exactly the Pillar 2 force-extraction pattern working at
scale.

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

Three cases are already in the case fleet:
- case_002a (APU bay buoyantSimpleFoam, internal flow + buoyancy) — active
- case_002b (APU bay CHT, multi-region thermal coupling) — active
- case_003 (CRM-HLS, external high-Re + boundary layer) — dispatched, deferred awaiting user resources

The next solver-class target is **rotating machinery (MRF / sliding mesh)** — currently uncovered. You design case_004 to fill this row. Note: case_004 is being drafted ahead of case_003's actual run; both will sit in the dispatched queue.

## Required reading (in cfd-harness-unified repo)

Read these in order before designing:
1. .planning/methodology/codex_case_design_protocol.md — your contract (5 deliverables + validation steps)
2. .planning/methodology/component_bank.md — Tier-3 fallback menu (class D · rotating-machinery rows D1-D4) + Defect Catalog D1-D10
3. .planning/methodology/public_cad_sources.md — Tier 1+2 catalog (PRIORITY — check first; rotating-machinery candidates are NREL Phase VI / NREL 5MW / NASA Stage 35 / NASA Stage 67 / HART-II rotor / MEXICO rotor)
4. .planning/methodology/kickoff/case_003_codex_response.md — example of your prior case design output (you wrote this); follow the same pattern
5. .planning/case_profiles/case_002a_apu_bay_buoyant_simple.md AND case_002b_apu_bay_cht.md — examples of the case-thread pattern your design will inherit
6. .planning/methodology/industrial_case_solver_findings.md — V-series; note Pattern 6 (numerics-class inheritance). Your design is incompressible-RANS-MRF so it inherits NONE of the compressible-buoyant-RANS findings (V3-V13, V15) AND NONE of case_003's external-RANS findings (when they accumulate)

## Hard constraints

1. **Solver class**: rotating machinery (MRF / sliding mesh). v1 solver target: simpleFoam + MRF (steady). v2 fallback: pimpleFoam + AMI sliding mesh only if v1 forces oscillate
2. **CAD source priority**: Tier 1 first. Strong rotating-machinery Tier-1 candidates per public_cad_sources.md:
   - T1.W1 NREL Phase VI / Phase II — 2-blade research wind turbine, NASA Ames wind tunnel reference
   - T1.W2 NREL 5 MW reference — standard offshore wind turbine
   - T1.E2 NASA Stage 35 / Stage 67 transonic compressor — single-stage axial
   - T1.H1 HART-II rotor — 4-bladed model rotor
   Tier 3 fallback only if no Tier 1 fits
3. **Defect injection**: exactly 2 defects from defect catalog (D1-D10 in component_bank.md). Document in defect manifest. Defects must NOT be in regions where reference experimental data is taken
4. **Patch naming**: all body names must satisfy ^[A-Za-z][A-Za-z0-9_]*$ (OpenFOAM rule)
5. **cellZone identification**: parts manifest must explicitly identify which body is the rotating cellZone (this is unique to rotating machinery — the sub-session will set MRFProperties using this)
6. **Determinism**: CadQuery script must regenerate byte-identical STEP given identical inputs
7. **Industrial flavor**: case must be recognizable as a real industrial component
8. **Reference-data preservation** (if Tier 1): inject defects in regions OUTSIDE published experimental measurement zones; note `reference_data_validity` in defect manifest

## Your 5 deliverables

Same format as case_003's response. Per codex_case_design_protocol.md §"What Codex returns":

### 1. Engineering brief (Markdown)

Sections (mandatory): Component picked + bank ID / Engineering question / Physics signature / Parts inventory (mark cellZone explicitly) / Boundary conditions plan (note periodic / cyclicAMI requirements) / Expected metrics (rotating frame: head-vs-flow, thrust, torque) / Hypothesized failure modes (V-findings prediction including MRF-specific) / Defect injection summary / Sub-session estimated effort.

### 2. CAD generation script (Python, executable)

CadQuery preferred. Same requirements as case_003 (deterministic, --out CLI, parametric constants, comments at decision points, cache fetch for Tier 1). Must:
- Define rotating zone explicitly as one named body
- Stationary zone (or domain) as separate named body
- Export STEP with named bodies preserved

### 3. STEP file path

Same format as case_003.

### 4. Parts manifest YAML

Same schema as case_003 PLUS:
- Mark which part is the rotating cellZone (`role: rotating_cellzone`)
- Specify rotation axis (e.g., `rotation_axis_xyz: [0, 0, 1]`) and angular velocity (e.g., `omega_rad_per_s: 50.0`)
- Identify any cyclic / cyclicAMI patches if periodic

### 5. Defect manifest YAML

Same schema as case_003. Two defects, catalog IDs from D1-D10.

## Format your response

Wrap your full response in clear section headers (same as case_003 response):

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
- Do NOT pick Ahmed body / NACA airfoil / Sajben diffuser (Lane B validation references)
- Do NOT write a CAD script that requires interactive GUI input
- Do NOT propose new defect types not in catalog (D1-D10)
- Do NOT pick a ROTATING + COMPRESSIBLE case (e.g., NASA Stage 35/67 transonic compressor) — that combines two new solver classes and is too much scope for case_004. Prefer a pure rotating + incompressible case (NREL Phase VI / NREL 5MW / mixer tank). NASA Stage rows are reserved for case_005 or case_006

## Begin
```

## Validation checklist (main session runs after Codex responds)

Before writing the per-case kickoff:

- [ ] CAD source picked (Tier 1 / 2 / 3 declared)
- [ ] If Tier 1: source URL valid + license confirmed
- [ ] CadQuery script executes locally
- [ ] Generated STEP opens in FreeCAD without errors
- [ ] FreeCAD reports body count + names matching parts manifest
- [ ] All patch names satisfy ^[A-Za-z][A-Za-z0-9_]*$
- [ ] **Rotating cellZone body explicitly identified** in parts manifest
- [ ] **Rotation axis + omega specified** in parts manifest
- [ ] Both injected defects measurable in geometry
- [ ] Defect manifest field `expected_advisor_to_catch` references a real (or pending) main-project advisor
- [ ] BC plan handles cyclic / cyclicAMI if periodic
- [ ] Engineering brief targets MRF + incompressible-RANS

## After validation passes

1. Save Codex response at `kickoff/case_004_codex_response.md`
2. Format per-case kickoff at `kickoff/case_004_<name>.md`
3. Update `case_proposal_queue.md` with row in Dispatched section
4. Update `case_index.md` with case_004 row, status=dispatched
5. Tell user: "case_004 kickoff ready. Open new Claude Code session and paste contents of `kickoff/case_004_<name>.md`."
