---
decision_id: DEC-V61-201-SUB-INGEST-LES-CONTRACT
title: les_contract schema for SGS + filter + wall-treatment declarations (Gap #28)
status: Proposed
proposed_date: 2026-05-22
parent_dec: DEC-V61-201-SUB-INGEST
phase: M2.8 cycle 5 (LES regime charter)
notion_sync_status: pending_accepted
autonomous_governance: true
counter_status: v6.1 N/A pending accepted
charter_class: true
---

## Why (LES regime is structurally invisible)

case_010 DrivAer fastback LES dogfood enumerated the gap explicitly:

> "`bc_contract.turbulence_fields` lacks a 'LES vs RANS' physics-regime
> branch. The 6 prior dogfoods all declared k+omega; the `expected_fields`
> hardcoded list in bc_contract parser includes them. On an LES case
> the parser may produce a spurious `missing` finding for k/omega — or,
> more subtly, may silently iterate over the schema's triplet without
> noticing that no k file ever should exist."

case_010's actual on-disk LES declaration:
- `constant/turbulenceProperties`: `simulationType LES; LESModel WALE; delta cubeRootVol; ...`
- `0.orig/nut`: nut field present (algebraic SGS — NOT a transported field)
- NO `0.orig/k`, NO `0.orig/omega`, NO `0.orig/epsilon` — LES algebraic SGS solves no transport eqns

Engine state:
- Gap #31 turb-model derivation (cycle 1) handles `physics.turbulence_model = LES_WALE` → derives [nut] expected fields ✓
- BUT manifest has NO slot to declare `LESModel WALE` / `delta cubeRootVol` / SGS coefficients
- The `turbulenceProperties` dict is structurally invisible — `grep -r "LESModel\|simulationType\|cubeRootVol"` across `ui/backend/audit/cfdtrust/` returns 0 hits

Result: ingest succeeds, but the case carries declared LES physics the engine cannot audit. A case_010-class manifest that wrongly declares `LESModel kEqn` (which DOES transport k) but ships `0.orig/` without `k` file would silently pass the BC layer with `turb_fields = [nut]` derivation, missing the contradiction.

Witnesses queued:
- case_010 DrivAer fastback LES (WALE) — primary trigger
- Any future LES intake (case_036 transition flows / V-series turbulent boundary layers / etc.)
- Future hybrid LES-RANS cases (DDES, IDDES — case_036 transition-tagged)

## What (scope contract — single-charter-per-cycle)

Same shape as cycle-3 compressible_contract charter: ship the data layer
+ schema validation. Out of scope: on-disk `turbulenceProperties` parsing
+ cross-check (would require an OpenFOAM dict parser — separate spike or
sub-charter). Out of scope: per-region per-class verdict refinement
(separate spike, Gap #45, deferred from cycle-4 spike B).

### In scope (this charter)

**1. Schema: `les_contract` top-level optional object** (all fields
optional except `simulation_type` when block present):

```json
"les_contract": {
  "type": "object",
  "additionalProperties": true,
  "properties": {
    "simulation_type": {
      "type": "string",
      "enum": ["LES", "RAS", "DES", "DDES", "IDDES", "laminar"]
    },
    "les_model": {
      "type": "string",
      "enum": ["WALE", "Smagorinsky", "dynamicSmagorinsky",
               "kEqn", "dynamicKEqn",
               "kOmegaSSTDES", "kOmegaSSTDDES", "kOmegaSSTIDDES",
               "SpalartAllmaras", "SpalartAllmarasDES",
               "SpalartAllmarasDDES", "SpalartAllmarasIDDES",
               "deardorffDiffStress"]
    },
    "delta": {
      "type": "string",
      "enum": ["cubeRootVol", "vanDriest", "smooth", "Prandtl",
               "maxDeltaxyz", "IDDESDelta"]
    },
    "delta_coeff": { "type": "number", "exclusiveMinimum": 0 },
    "sgs_wall_function": {
      "type": "string",
      "enum": ["nutUSpaldingWallFunction", "nutkWallFunction",
               "nutUWallFunction", "nutLowReWallFunction",
               "calculated"]
    },
    "transported_fields": {
      "type": "array",
      "items": { "type": "string" },
      "$comment": "Auxiliary: which fields the LES model itself transports. WALE/Smagorinsky → []; kEqn/dynamicKEqn → ['k']; deardorffDiffStress → ['R'] (Reynolds stress tensor). Engine cross-checks against bc_contract.turbulence_fields/thermal_fields and the on-disk 0/ field list (Gap #31 derivation path)."
    }
  }
}
```

**2. Engine integration: Gap #31 `_turb_fields_from_model` consults `les_contract` when present.**

Current Gap #31 derivation:
```python
def _turb_fields_from_model(turb_model: str) -> List[str]:
    if "wale" in m or "smagorinsky" in m: return ["nut"]
    if "les" in m and ("keqn" in m or ...): return ["nut", "nuSgs", "k"]
    ...
```

Extension: when manifest carries `les_contract.transported_fields`, prefer
that explicit list over the heuristic. When `les_contract.les_model` is
set without explicit `transported_fields`, derive from the model name
using the same algebraic-vs-transport-eqn taxonomy.

**3. Tests** (≥4 new):
- `test_les_contract_optional_absent_no_break` — incompressible
  RANS manifest still validates (backwards compat).
- `test_les_contract_full_case010_shape` — case_010-shape (LES + WALE
  + cubeRootVol + nutUSpaldingWallFunction) round-trips through
  validate_manifest.
- `test_les_contract_transported_fields_overrides_derivation` —
  manifest with `les_contract.transported_fields: [nut, nuSgs]` wins
  over `_turb_fields_from_model` heuristic.
- `test_les_contract_keqn_transports_k` — `les_model: kEqn` →
  derived `transported_fields` includes `k` (cross-check against the
  hardcoded Gap #31 LES one-eq branch).

### Out of scope (deferred follow-ups)

- **`turbulenceProperties` dict parser**: reading
  `constant/turbulenceProperties` off-disk + cross-checking with
  manifest declaration. Requires an OpenFOAM dict parser. Same shape
  as cycle-3's deferred `thermophysicalProperties` parser — separate
  charter.
- **Gap #45 per-region per-class verdict refinement** (cycle-4 spike B
  ceiling). Separate spike — needs per-region expected_fields semantics
  schema (this charter is single-region LES + multi-region as future
  combined work).
- **DES/DDES/IDDES hybrid models**: schema enum lists them but engine
  doesn't yet have hybrid-mode-specific verdict semantics. Future LES
  intake will surface those.

## Codex review plan

Codex 86gs gpt-5.4 xhigh:
- R0: full review of schema + engine integration + 4 new tests
- R1 fixes if any P1 (round cap=3 per DEC-V61-133). Same precedent as
  cycle-3 compressible_contract (R0 caught 2 enum omissions, R1 closed).

## Verification (case_010 dogfood post-implementation)

```bash
# 1. Update case_010 case_manifest.yaml to declare les_contract:
#    simulation_type: LES
#    les_model: WALE
#    delta: cubeRootVol
#    delta_coeff: 1.0
#    sgs_wall_function: nutUSpaldingWallFunction
# 2. Re-ingest:
cfdtrust ingest ~/Desktop/cfd-harness-unified/_sandboxes/case_010_drivAer_fastback_les/case
# 3. Verify: validate_manifest accepts, bc_quality.expected_fields=[U,p,nut]
#    (NOT [U,p,k,omega,nut] — LES WALE only has nut)
```

This is the cycle-3 followup pattern: schema closure verified via
synthetic + production-case integration.

## Status

**Proposed** — pending implementation + Codex R0 + verification.
Becomes **Accepted** when:
- Implementation lands + Codex APPROVE on the change
- All 4 new tests pass
- case_010 synthetic test exercising the new schema path validates

## Provenance

- case_010 manifest (gap enumeration): `~/Desktop/cfd-harness-unified/_sandboxes/case_010_drivAer_fastback_les/case/case_manifest.yaml` (LES contract section + the "candidate gap" comments)
- Parent DEC: `.planning/decisions/2026-05-21_v61_201_sub_audit_ingest_mode.md`
- Cycle-3 precedent (same shape): `.planning/decisions/2026-05-22_v61_201_sub_audit_compressible_contract.md`
- Gap #31 turb-model derivation (composed with): `ui/backend/audit/cfdtrust/backends/openfoam.py` `_turb_fields_from_model`
- V-series corpus map: `.planning/V_SERIES_CORPUS_MAP.md` row "Incompressible external LES"
