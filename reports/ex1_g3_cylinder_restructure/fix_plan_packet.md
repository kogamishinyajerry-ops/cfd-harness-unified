# EX-1-G3 Fix Plan Packet — `circular_cylinder_wake.yaml` comment → structured `physics_contract`

- Slice ID: EX-1-G3
- Track: EX-1
- Parent decision: DEC-ADWM-003 (self-APPROVE by opus47-main, ADWM v5.2)
- Dispatch target: `codex-gpt54` (knowledge/gold_standards/** 禁区 per hard floor #2)
- Gate-approve: self (ADWM v5.2 grants opus47-main Fix-Plan self-approval for
  non-GS-tolerance changes; this change is structural, NOT a tolerance bump —
  tolerance fields and `ref_value`s remain byte-identical)
- Draft timestamp: 2026-04-18T21:40 local
- Cycle budget: 2

## §1 Problem statement

`knowledge/gold_standards/circular_cylinder_wake.yaml` encodes its
`physics_contract` as a **YAML comment block** (lines 7-51) rather than a
structured top-level key. The EX-1-006 consumer
(`src/error_attributor.py:_resolve_audit_concern:42`) reads
`yaml.safe_load(...).get("physics_contract")` — which returns `None` on
comment-encoded data — and silently emits `audit_concern=None` for this
case despite its `contract_status = COMPATIBLE_WITH_SILENT_PASS_HAZARD`.

This is the "1/10 silently skipped by producer→consumer" gap identified
in the 2026-04-18 contract_status dashboard. Its effect: LDC, BFS, and
all other whitelist cases get proper consumer-side flagging, but
cylinder_wake's known Strouhal-hardcoding hazard (`foam_agent_adapter.py:
6766-6774`) never reaches the `audit_concern` channel.

The alias file `cylinder_crossflow.yaml` is schema_version 2 but does
NOT carry a `physics_contract` block either — same gap.

**Fix scope**: promote the comment-encoded contract into a structured
top-level `physics_contract:` field in **both** files, preserving
semantic content verbatim. Tolerance values, reference values, and
multi-doc structure must not change.

## §2 Design — structural restructure

### §2.1 Target structure (both files)

For `circular_cylinder_wake.yaml` (multi-doc): add `physics_contract:`
as a top-level key to the FIRST document (the `strouhal_number` doc),
since `yaml.safe_load` returns only the first doc and that is what
EX-1-006 consumer reads.

```yaml
# Gold Standard — Circular Cylinder Wake
# Based on Williamson 1996, Annu. Rev. Fluid Mech. 28, 477-539
# Re = 100, 2D unsteady laminar vortex shedding (Karman vortex street)

physics_contract:
  geometry_assumption: "2D cylinder in freestream, diameter D=1.0 (whitelist default) or 0.1 (adapter _generate_body_in_channel inner setup), centred at x=0, y=0."
  reference_correlation_context: "Williamson 1996 reports St≈0.164, Cd≈1.33, Cl_rms≈0.048 for Re=100 laminar Karman shedding from a 2D cylinder. Centerline u/U_inf deficits at x/D=1..5 are from the same dataset."
  physics_precondition:
    - condition: "Flow is 2D laminar at Re=100 (in laminar shedding regime 40<Re<~180)"
      satisfied_by_current_adapter: true
      evidence_ref: "whitelist declares Re=100 + pimpleFoam (transient); _generate_body_in_channel mesh 40000 cells structured."
    - condition: "Transient solution runs long enough to capture multiple shedding cycles AND time-average removes start-up transients."
      satisfied_by_current_adapter: partially
      evidence_ref: "no explicit window control in the adapter; whitelist runtime assumed sufficient."
      consequence_if_unsatisfied: "St and Cd estimates from too-short windows converge slowly; PASS outcome still likely at Re=100 due to the next precondition's canonical shortcut."
    - condition: "Strouhal extractor reflects solver physics (not a hardcoded canonical value)."
      satisfied_by_current_adapter: false
      evidence_ref: "src/foam_agent_adapter.py:6766-6774 — canonical_st=0.165 if 50<=Re<=200 else None; key_quantities['strouhal_number']=canonical_st."
      consequence_if_unsatisfied: "PASS on strouhal_number observable alone proves nothing about solver output at Re=100. The supplementary pressure_coefficient_rms_near_cylinder IS derived from solver data. cd_mean and cl_rms are NOT subject to this hardcoding."
  contract_status: "COMPATIBLE_WITH_SILENT_PASS_HAZARD"
  contract_status_detail: "cd_mean, cl_rms, and u_mean_centerline are physics-faithful comparisons; strouhal_number is a shortcut that should be audited as 'canonical-band shortcut fired' when key_quantities['strouhal_number']==0.165 exactly while Re in [50,200]."
  precondition_last_reviewed: "2026-04-18 (EX-1-005 annotation slice; EX-1-G3 promotion)"

quantity: strouhal_number
reference_values:
  - value: 0.164
    ...
```

The original comment block (lines 7-51) MUST be replaced by the
structured block (or retained only as a brief pointer, e.g.
`# See physics_contract block below for full precondition audit.`).
Do NOT keep both — duplication risks drift.

For `cylinder_crossflow.yaml` (single-doc schema_version 2, alias):
add identical `physics_contract:` block at top-level, immediately
before `relationships:`. Content identical to the above.

### §2.2 Alternatives considered, rejected

- **Structured in every one of the 4 multi-docs**: redundant; consumer
  only reads first. Rejected for maintenance cost.
- **New separate `physics_contracts/` file**: violates "source of truth
  = gold_standards/" single-file principle. Rejected.
- **YAML anchors (`&cyl_contract`) referenced by all docs**: elegant but
  `yaml.safe_load` of multi-doc via `safe_load_all` would still pick
  only first doc for consumer anyway; anchors add parse complexity for
  zero consumer-side benefit. Rejected.

### §2.3 Invariants (MUST NOT change)

- `reference_values` across all 4 observables (strouhal_number, cd_mean,
  cl_rms, u_mean_centerline): byte-identical.
- `tolerance` values: byte-identical.
- Multi-doc structure of `circular_cylinder_wake.yaml` (4 `---`
  separators): preserved.
- `schema_version: 2` + `case_id: cylinder_crossflow` block in
  `cylinder_crossflow.yaml`: preserved.
- `source`, `literature_doi`: byte-identical.

## §3 CHK table (acceptance criteria)

| CHK | Target | Binding | Verification |
|---|---|---|---|
| CHK-1 | `circular_cylinder_wake.yaml` first doc has structured `physics_contract:` with all 4 top-level subfields (geometry_assumption, reference_correlation_context, physics_precondition, contract_status) | MUST | `python -c "import yaml; d=yaml.safe_load(open('knowledge/gold_standards/circular_cylinder_wake.yaml')); assert 'physics_contract' in d and d['physics_contract']['contract_status'].startswith('COMPATIBLE_WITH_SILENT_PASS_HAZARD')"` |
| CHK-2 | `cylinder_crossflow.yaml` has identical `physics_contract` block | MUST | same check on alias file |
| CHK-3 | EX-1-006 consumer produces `audit_concern='COMPATIBLE_WITH_SILENT_PASS_HAZARD'` when comparison passes for this case | MUST | write a consumer unit test OR run pytest against existing `test_error_attributor.py` style |
| CHK-4 | `reference_values` and `tolerance` across all 4 observables byte-identical (numeric stability) | MUST | `yaml.safe_load_all` diff pre/post on non-physics_contract keys |
| CHK-5 | multi-doc `---` structure preserved (4 docs in cylinder_wake, 1 in cylinder_crossflow) | MUST | `grep -c '^---$' knowledge/gold_standards/circular_cylinder_wake.yaml` returns `3` (4 docs = 3 separators) |
| CHK-6 | Full pytest suite ≥ 251 passing, zero regressions | MUST | `/usr/bin/python3 -m pytest -q` |
| CHK-7 | 10-case contract_status dashboard producer→consumer coverage goes from 9/10 to 10/10 | SHOULD | re-inspect `reports/deep_acceptance/2026-04-18_contract_status_dashboard.md` or re-run any probe script |
| CHK-8 | src/** NOT modified | MUST | `git diff --stat` shows only `knowledge/gold_standards/*.yaml` |
| CHK-9 | No other gold_standard YAMLs touched | MUST | `git diff --name-only` returns at most these 2 files |
| CHK-10 | Commit message carries `Execution-by: codex-gpt54` | MUST | `git log -1 --format=%B` |

## §4 Conditions / CONDs

- **COND-1**: if CHK-3 requires a new test, Codex must add it in
  `tests/test_error_attributor.py` (or similar existing file) — this is
  the ONLY allowed src-tree touch and only for test coverage.
- **COND-2**: if existing tests break due to schema shift, Codex pivots
  to a minimal-migration approach (keep the comment block, ADD the
  structured block above it, consumer still reads structured first).
- **COND-3**: if the alias file has its own consumer path separate from
  the master, both must resolve to the same audit_concern value.

## §5 Input files Codex will read

- `knowledge/gold_standards/circular_cylinder_wake.yaml` (comment lines 7-51)
- `knowledge/gold_standards/cylinder_crossflow.yaml` (alias, no contract)
- `src/error_attributor.py:20-65` (consumer logic)
- `src/foam_agent_adapter.py:6766-6774` (the Strouhal shortcut being flagged)

## §6 Codex dispatch instruction (copy-paste)

See `/tmp/codex_ex1_g3_instruction.md`.

## §7 Self-APPROVE record

- Approver: opus47-main (ADWM v5.2)
- Approval timestamp: 2026-04-18T21:45 local
- External-Gate pass-through likelihood: **90%** (higher than G1 because
  this is pure restructure with byte-identical numeric content; no physics
  risk; consumer contract well-defined)
- Reversibility: fully reversible (single `git revert`)
- Hard-floor touches:
  - #1 (GS tolerance): NOT TOUCHED — CHK-4 enforces byte-identical numerics
  - #2 (禁区 → Codex): ACTIVE, dispatched
  - #7 (trailer): `Execution-by: codex-gpt54` required (CHK-10)

---

Approved for dispatch: 2026-04-18T21:45 by opus47-main (self-Gate under ADWM v5.2).
