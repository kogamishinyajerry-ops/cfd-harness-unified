---
decision_id: DEC-V61-201-SUB-INGEST-VOF-CONTRACT
title: vof_contract schema + bc_contract.phase_fields slot + p_rgh + phases-driven derivation (TBD-3)
status: Accepted
proposed_date: 2026-05-22
accepted_date: 2026-05-22
parent_dec: DEC-V61-201-SUB-INGEST
phase: M2.9 cycle 6 (VOF multiphase regime charter — FINAL audit-engine charter per 2026-05-22 strategic pivot)
notion_sync_status: synced 2026-05-22 (https://www.notion.so/368c68942bed81eb89c0f6f9463f5663)
autonomous_governance: true
counter_status: v6.1 telemetry
charter_class: true
codex_review:
  r0_commit: ed393ab
  r0_verdict: CHANGES_REQUIRED (2 P1 + minor)
  r0_findings:
    - "Gap #48 (P1-1): vof_contract.pressure_field_name missing; engine hardcoded 'p' but interFoam ships 0/p_rgh"
    - "Gap #49 (P1-2): vof_contract.phases not used in derivation; engine ignored multiphase declaration"
  r1_commit: 2c050d2
  r1_verdict: APPROVED (verbatim Codex P1 fix per v2.3 verbatim exception)
final_audit_engine_charter: true
supersedes_pivot: 2026-05-22 strategic pivot — workbench dynamic guided UX (DEC-V61-202 forthcoming)
---

## Why (VOF multiphase is structurally invisible)

case_007 KCS ship VOF dogfood enumerated TBD-3 explicitly:

> "Non-schema additional axis — VOF phase fields. Schema is
> additionalProperties=true so this lands harmlessly; engine will not
> consume it (candidate gap)."

case_007's actual on-disk VOF declaration:
- `constant/transportProperties`: `phases (water air); water { rho 998.8; nu 1.05e-06 }; air { rho 1.225; nu 1.5e-05 }; sigma 0.072;`
- `0/alpha.water`: phase fraction field (the VOF transport variable)
- `0/p_rgh`: hydrostatic-decomposed pressure (interFoam canonical)

Engine state:
- Gap #25 (residual regex dotted-name fix): `alpha.water` parses cleanly via `[\w.()]+` — verified live
- BUT manifest has no slot to declare `phases (water air)` / `surface_tension` / `interface_method`
- BUT `bc_contract` has no `phase_fields` slot (parallel to turbulence_fields / thermal_fields)
- The `transportProperties` dict is structurally invisible — `grep -r "phases\b\|sigma\b\|alphaContact\|cAlpha"` across `ui/backend/audit/cfdtrust/` returns 0 hits

Result: ingest succeeds, but a case_007-class manifest declaring `phases (water oil mercury)` (3-phase) ships with only `alpha.water` and `alpha.oil` on disk (missing `alpha.mercury`) would silently pass — engine has no schema slot to enumerate phase BCs.

Witnesses queued:
- case_007 KCS ship VOF (primary trigger)
- Any future interFoam / compressibleInterFoam / multiphaseInterFoam intake (marine / dam-break / nuclear-thermal / aerospace tank-slosh)
- 3+ phase cases (multiphaseInterFoam supports N phases)

## What (scope contract — single-charter-per-cycle)

Same shape as cycle-3 compressible_contract + cycle-5 les_contract:
ship the data layer + schema validation. Out of scope: on-disk
`transportProperties` parsing + cross-check (separate spike or sub-charter).
Out of scope: per-phase BC verdict refinement (would compose with
Gap #45 multi-region per-class verdict refinement — separate cycle).

### In scope (this charter)

**1. Schema: `vof_contract` top-level optional object**

```json
"vof_contract": {
  "type": "object",
  "additionalProperties": true,
  "required": ["phases"],
  "properties": {
    "phases": {
      "type": "array",
      "items": { "type": "string" },
      "minItems": 2,
      "$comment": "Ordered phase list matching constant/transportProperties `phases (...)`. First phase is the alpha-tracked phase by interFoam convention (e.g. ['water', 'air'])."
    },
    "interface_method": {
      "type": "string",
      "enum": ["VOF", "level_set", "MULES", "isoAdvector", "VOF_MULES",
               "VOF_isoAdvector", "compressibleVOF"]
    },
    "alpha_field_name": {
      "type": "string",
      "$comment": "Canonical name of the alpha field that gets transported. interFoam: 'alpha.water'. compressibleInterFoam: 'alpha.<phase1>'. Used by bc_contract.phase_fields default + by downstream cross-check with on-disk 0/alpha.<phase> presence."
    },
    "surface_tension_N_per_m": { "type": "number", "minimum": 0 },
    "interface_compression_coeff": {
      "type": "number",
      "minimum": 0,
      "maximum": 4,
      "$comment": "cAlpha in fvSolution. Typical interFoam: 1.0 (full compression). 0 = no artificial compression. Values >2 are aggressive."
    },
    "density_pair": {
      "type": "object",
      "additionalProperties": true,
      "$comment": "Optional advisory: declared per-phase rho for verification against transportProperties. Keys are phase names from `phases`. Engine doesn't yet parse transportProperties — this is a future cross-check hook.",
      "patternProperties": {
        "^[a-zA-Z][a-zA-Z0-9_]*$": { "type": "number", "exclusiveMinimum": 0 }
      }
    },
    "viscosity_pair": {
      "type": "object",
      "additionalProperties": true,
      "patternProperties": {
        "^[a-zA-Z][a-zA-Z0-9_]*$": { "type": "number", "exclusiveMinimum": 0 }
      }
    },
    "mules_correctors": {
      "type": "integer",
      "minimum": 0,
      "maximum": 10,
      "$comment": "nAlphaCorr * nAlphaSubCycles from fvSolution. Engine doesn't yet parse fvSolution — informational only."
    }
  }
}
```

**2. Schema: `bc_contract.phase_fields`** (optional list, mirrors
`turbulence_fields` and `thermal_fields`). Engine's expected-fields
walker honors any field name listed here. Default: when
`vof_contract.alpha_field_name` is set but `bc_contract.phase_fields`
is absent, derive `[alpha_field_name]`.

**3. Engine integration: `_collect_and_persist_bc` walks phase_fields**
alongside turbulence_fields + thermal_fields. Same sentinel filter
applied.

**4. Tests** (≥4 new):
- `test_vof_contract_optional_absent_no_break`
- `test_vof_contract_full_case007_shape`
- `test_phase_fields_in_bc_contract_walked`
- `test_phase_fields_derived_from_vof_contract_alpha_field_name`
- `test_alpha_dotted_residual_already_parsed` (Gap #25 regression guard)

### Out of scope (deferred follow-ups)

- **`transportProperties` dict parser** (off-disk): cross-check rho /
  nu / sigma between manifest declaration + dict. Same shape as cycle 3
  `thermophysicalProperties` + cycle 5 `turbulenceProperties` deferrals.
- **Per-phase BC verdict refinement**: when `phases = [water, air]`,
  each phase's BC could have per-phase expected values. Composes with
  Gap #45 multi-region per-class refinement.
- **MULES sub-cycle convergence audit**: alpha.water residual is
  reported AFTER MULES correction; auditing the MULES sub-loop itself
  requires fvSolution dict parsing. Future spike.

## Codex review plan

Codex 86gs gpt-5.4 xhigh:
- R0: full review of schema + engine integration + 5 new tests
- R1 fixes if any P1 (round cap=3 per DEC-V61-133). Cycles 3 + 5
  precedent: 2-3 findings per R0 (typically enum omissions / required-field
  semantics).

## Verification (case_007 dogfood post-implementation)

```bash
# 1. Update case_007 case_manifest.yaml to declare vof_contract +
#    bc_contract.phase_fields:
#    vof_contract:
#      phases: [water, air]
#      interface_method: VOF_MULES
#      alpha_field_name: alpha.water
#      surface_tension_N_per_m: 0.072
#      density_pair: { water: 998.8, air: 1.225 }
#      viscosity_pair: { water: 1.05e-6, air: 1.5e-5 }
#      mules_correctors: 2
#    bc_contract:
#      ...
#      phase_fields: [alpha.water]
# 2. Re-ingest and inspect:
cfdtrust ingest ~/Desktop/cfd-harness-unified/_sandboxes/case_007_kcs_ship_vof/case
cat .../case/artifacts/bc_quality.json | jq '.expected_fields'
# Expect: ["U", "p", "k", "omega", "nut", "alpha.water"]
#         (alpha.water now visible via phase_fields)
```

## Status

**Accepted 2026-05-22.**

Closure criteria all green:
- Schema additions landed (commit `ed393ab`): `vof_contract` + `bc_contract.phase_fields` + (R1) `vof_contract.pressure_field_name`
- Engine integration landed (commit `2c050d2`): phases-driven derivation + p_rgh default + override-honored
- Tests: 8 vof/phase-fields tests passing (4 from R0 + 4 from R1) · full audit suite 472 passed / 1 skipped
- Codex R0 commit `ed393ab` → CHANGES_REQUIRED with Gap #48 + #49 → R1 commit `2c050d2` is verbatim verbatim Codex P1 fix → APPROVED per v2.3 verbatim exception

**FINAL audit-engine charter.** Per user 2026-05-22 strategic pivot
(see [feedback_cfd_workbench_dynamic_guided_pivot](../../../../.claude/projects/-Users-Zhuanz/memory/feedback_cfd_workbench_dynamic_guided_pivot.md)),
no further audit-engine charters will be proposed. Future work shifts
to workbench guided UX (DEC-V61-202 in flight).

## Provenance

- case_007 manifest (TBD-3 enumeration): `~/Desktop/cfd-harness-unified/_sandboxes/case_007_kcs_ship_vof/case/case_manifest.yaml` (alpha_field non-schema axis + "candidate gap" comment)
- Parent DEC: `.planning/decisions/2026-05-21_v61_201_sub_audit_ingest_mode.md`
- Cycle-3 precedent (compressible): `.planning/decisions/2026-05-22_v61_201_sub_audit_compressible_contract.md`
- Cycle-5 precedent (LES): `.planning/decisions/2026-05-22_v61_201_sub_audit_les_contract.md`
- Gap #25 (dotted-name regex, already closed): `ui/backend/audit/cfdtrust/backends/openfoam.py:483` `_RESIDUAL_LINE_RE`
- V-series corpus map: `.planning/V_SERIES_CORPUS_MAP.md` row "Multiphase VOF"
