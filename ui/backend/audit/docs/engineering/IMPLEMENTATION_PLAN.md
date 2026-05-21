# Implementation Plan

Owned by `engineering-director`. Phase 0 status: complete; Phase 1 not started.

## Phase 0 (this bootstrap) — complete

- repo skeleton + project memory + agent definitions + skills
- `cfdtrust` CLI with `validate-manifest`, `audit`, `run`, `report`
- JSON schemas for `case_manifest` + `trust_report`
- `flat_plate_rans_sst` sample case
- `.cwos/` state + tools + cockpit
- pytest suite (manifest, trust_report, negative cases, status, cockpit)

## Phase 1 — Real OpenFOAM adapter + canonical benchmark

**Tasks (in priority order):**

1. PH1-ADAPTER-001 — Implement `src/cfdtrust/backends/openfoam.py` thin adapter
   - acceptance: `cfdtrust run cases/flat_plate_rans_sst` executes real simpleFoam
     when adapter is enabled, falls back to mocked when not
2. PH1-CASE-001 — Populate real polyMesh / 0 / system directories for flat plate
   - acceptance: `checkMesh` passes; residuals reach declared targets
3. PH1-REF-001 — Resolve OQ-0001; commit reference data + provenance.md
   - acceptance: `reference_comparison.status == "finalized"`; license recorded
4. PH1-QOI-001 — Real QoI extraction from solver output
   - acceptance: `qoi.csv` populated from real solver fields, not placeholders
5. PH1-COMPARE-001 — Real reference comparison
   - acceptance: `reference_comparison.csv` carries numerical agreement values
6. PH1-VALIDATE-001 — First `validation_status: validated` trust_report
   - acceptance: all gates PASS; Red Team review passes

## Phase 2 — Negative tests

**Tasks:**

1. PH2-NEG-001 — Populate `negative_tests/missing_wall_patch/`
2. PH2-NEG-002 — Populate `negative_tests/wrong_unit_scale/`
3. PH2-NEG-003 — Populate `negative_tests/coarse_mesh/`
4. PH2-NEG-004 — Populate `negative_tests/missing_turbulence_field/`
5. PH2-NEG-005 — Populate `negative_tests/residual_converged_but_qoi_unstable/`
6. PH2-NEG-006 — Populate `negative_tests/missing_reference_comparison/`
7. PH2-NEG-007 — Populate `negative_tests/wrong_turbulence_bc/`
8. PH2-TEST-001 — pytest tests asserting each negative case yields FAIL/WARN

## Phase 3 — Three static screens

(see `docs/product/SCREEN_SPECS.md`)

## Phase 4 — AI advisor over evidence

(see `docs/product/AI_ADVISOR_INTERACTION.md`)

## Phase 5 — Design exploration

Out of scope until Phases 0–4 hold.

## Estimation discipline

Estimates are deliberately omitted from this plan. The project trades velocity
for evidence; "how long will it take" is the wrong question for the wedge.

## Re-planning triggers

Re-open this file if:

- Red Team identifies a structural defect in Phase 0
- OQ-0001 or OQ-0002 changes the OpenFOAM adapter strategy
- the operator adds a hard external deadline
