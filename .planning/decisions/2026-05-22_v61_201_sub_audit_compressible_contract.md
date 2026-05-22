---
decision_id: DEC-V61-201-SUB-INGEST-COMPRESSIBLE-CONTRACT
title: compressible_contract schema + thermal_fields BC slot (Gap #18 + #19)
status: Proposed
proposed_date: 2026-05-22
parent_dec: DEC-V61-201-SUB-INGEST
phase: M2.7 cycle 3 (compressible-aero charter)
notion_sync_status: pending_accepted
autonomous_governance: true
counter_status: v6.1 N/A pending accepted
charter_class: true
---

## Why (three production blockers, one regime)

case_006 ONERA M6 transonic dogfood (V_SERIES_CORPUS_MAP: "Transonic
compressible (density-based)") surfaced **three structurally separate
gaps** that all manifest in the same physics regime:

- **Gap #18**: `constant/thermophysicalProperties` is structurally
  invisible to the engine. `grep -r "thermophysicalProperties\|
  hePsiThermo\|perfectGas\|sutherland"` across `ui/backend/audit/cfdtrust/`
  returns 0 hits. Manifest has no `compressible_contract` slot, so a case
  declaring real compressible physics (hePsiThermo + pureMixture +
  sutherland + hConst + perfectGas + sensibleEnthalpy) gets the SAME
  level of audit attention as a laminar incompressible case.
- **Gap #19**: `bc_contract` has slots `inlet`, `outlet`, `wall`,
  `turbulence_fields` — no `thermal_fields`. case_006's `0/T` declares
  `freestream` (T_inf=288K) + `zeroGradient` at walls. These BCs are
  silently uncovered.
- ~~**Gap #20**~~ (verified ALREADY CLOSED in current `_RESIDUAL_LINE_RE`
  alternation at `openfoam.py:482` — `diagonal` is in the allowlist).
  Confirmed via live parse of synthetic rhoCentralFoam log slice:
  `_parse_simplefoam_log` returns `{'rho': 0.0, 'rhoUx': 0.0, ...}`
  for `diagonal: Solving for rho, ...` lines. Gap #20 marker preserved
  in comments for provenance.

Witnesses queued:
- case_006 ONERA M6 transonic 3D wing (primary trigger)
- case_030 wedge15ma5 (15° wedge at M=5, supersonic compression-ramp shock)
- case_036 bump2D (transonic bump in 2D channel)
- Any future intake of rhoCentralFoam / rhoPimpleFoam / rhoSimpleFoam /
  sonicFoam / fireFoam / chemFoam case (density-based + compressible-PIMPLE family)

## What (scope contract — single-charter-per-cycle rule)

This DEC closes the **schema + parser** layer for compressible regime.
It explicitly does NOT close the **verdict layer** (per-region per-class
expected_fields for thermal/conserved variables semantically depends on
declared physics + on-disk thermophysicalProperties parsing, which is
charter-class on its own). Per the cycle-1 multi-region DEC's precedent:
**ship the data layer, defer the verdict layer to a follow-up**.

### In scope (this charter)

**1. Schema: `compressible_contract` top-level optional object** with these
properties (all optional; absence = "this case is not compressible"
which is the laminar/RANS default):

```json
"compressible_contract": {
  "type": "object",
  "additionalProperties": true,
  "properties": {
    "thermophysical_model": {
      "type": "string",
      "enum": ["hePsiThermo", "hRhoThermo", "ePsiThermo", "eRhoThermo",
               "hConstThermo", "psiThermo", "rhoThermo"]
    },
    "mixture_model": {
      "type": "string",
      "enum": ["pureMixture", "multiComponentMixture", "reactingMixture",
               "singleStepReactingMixture", "homogeneousMixture"]
    },
    "transport_model": {
      "type": "string",
      "enum": ["const", "sutherland", "polynomial", "logPolynomial",
               "icoPolynomial", "WLFTransport"]
    },
    "thermo_model": {
      "type": "string",
      "enum": ["hConst", "eConst", "hPolynomial", "ePolynomial",
               "janafThermo", "hTabulatedThermo"]
    },
    "equation_of_state": {
      "type": "string",
      "enum": ["perfectGas", "incompressiblePerfectGas", "PengRobinsonGas",
               "rhoConst", "perfectFluid", "Boussinesq", "rPolynomial",
               "adiabaticPerfectFluid", "linear"]
    },
    "energy": {
      "type": "string",
      "enum": ["sensibleEnthalpy", "sensibleInternalEnergy",
               "absoluteEnthalpy", "absoluteInternalEnergy"]
    },
    "freestream": {
      "type": "object",
      "additionalProperties": true,
      "properties": {
        "p_Pa": { "type": "number", "minimum": 0 },
        "T_K": { "type": "number", "minimum": 0 },
        "U_ms": {
          "type": "array",
          "items": { "type": "number" },
          "minItems": 3, "maxItems": 3
        },
        "Mach": { "type": "number", "minimum": 0 },
        "Re_chord": { "type": "number", "minimum": 0 }
      }
    }
  }
}
```

**2. Schema: `bc_contract.thermal_fields`** (optional list, mirrors
`turbulence_fields`). Engine's expected-fields walker honors any field
name listed here (defaults: T, e, h for compressible cases when absent).

**3. Tests** (≥4 new tests in cfdtrust_tests/):
- `test_compressible_contract_optional_absent_no_break` — incompressible
  manifest (no compressible_contract key) still validates.
- `test_compressible_contract_full_case006_shape` — case_006-shape
  manifest with all 6 model declarations + freestream validates.
- `test_thermal_fields_in_bc_contract_walked` — bc_contract with
  `thermal_fields: [T]` + `0/T` file present → `bc_quality.json`
  fields_present includes T.
- `test_diagonal_solver_residuals_already_parsed` — synthetic
  rhoCentralFoam log → asserts current parser captures `rho`, `rhoUx`,
  etc. (regression guard for the already-closed Gap #20).

### Out of scope (deferred follow-up)

- **Compressible audit gate**: parsing `constant/thermophysicalProperties`
  off-disk + cross-checking with manifest declaration. Requires an
  OpenFOAM dictionary parser (separate spike or charter).
- **Density residual targets**: extending `solver_contract.residual_targets`
  to accept rho / rhoUx / rhoUy / rhoUz / rhoE (the schema's
  `additionalProperties: { type: "number" }` already allows any key, so
  no schema work needed; deferred only the engine's per-field semantics
  understanding of these).
- **forceCoeffs extractor** for Cd/Cl QoI (Gap #16, already tracked separately).
- **Per-region per-class expected_fields**: solid region wants T not U/p;
  fluid region wants U/p/turbulence/thermal — this is the multi-region
  CHT charter (Gap #28) which depends on this DEC landing first.

## Codex review plan

Codex 86gs gpt-5.4 xhigh on the implementation commit:
- R0: full review of schema + parser changes + 4 new tests
- R1 fixes if any P1 found (round cap=3 per DEC-V61-133)
- Push only after APPROVE (this is a charter-class change; cadence-floor
  cannot be overridden for the verdict gate — same discipline as
  Gap #11 + Gap #23 cycle-1 chains)

## Verification (dogfood case_006 post-implementation)

After the implementation lands:

```bash
# 1. Add compressible_contract block to case_006 case_manifest.yaml
#    (using rhoCentralFoam / pureMixture / sutherland / hConst /
#     perfectGas / sensibleEnthalpy from the actual case)
# 2. Re-ingest and inspect:
cfdtrust ingest ~/Desktop/cfd-harness-unified/_sandboxes/case_006_onera_m6_transonic/case
cat .../case/artifacts/bc_quality.json | jq '.fields | keys'
# Expect: ["T", "U", "k", "omega", "p"]  (T now visible via thermal_fields)
cat .../case/artifacts/residuals.csv | head -1
# Expect: iter,rho,rhoUx,rhoUy,rhoUz,rhoE,Ux,Uy,Uz,e,k,omega
# (rho et al. now captured via diagonal: parser fix)
```

If both expectations hold → Gap #18 + #19 + #20 data-layer closed →
flip Status from Proposed to Accepted → Notion sync.

## Status

**Proposed** — pending implementation + Codex R0 + dogfood verification.
Becomes **Accepted** only when all three closure criteria hold.

## Provenance

- case_006 manifest (gap enumeration): `~/Desktop/cfd-harness-unified/_sandboxes/case_006_onera_m6_transonic/case/case_manifest.yaml`
- Parent DEC: `.planning/decisions/2026-05-21_v61_201_sub_audit_ingest_mode.md`
- Multi-region precedent (same scope-contract shape): `.planning/decisions/2026-05-22_v61_201_sub_audit_multi_region_bc_parser.md`
- V-series corpus map: `.planning/V_SERIES_CORPUS_MAP.md` row "Transonic compressible (density-based)"
- Project-governor cycle-2 recommendation: `.planning/milestones/PROJECT_GOVERNOR_CHECKPOINT_2_2026-05-22.md` ("recommend Gap #18 compressible_contract since case_006 ONERA M6 + case_030 wedge15ma5 + case_036 bump2D would all light up simultaneously")
