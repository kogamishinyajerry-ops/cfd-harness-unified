---
decision_id: DEC-V61-202-SUB-M31-CYCLE6-PATCH-TYPE-PRESERVATION
title: M3.1 cycle 6 — PATCH type preservation (fix BUG-CYCLE5-1 + BUG-CYCLE5-2)
status: Accepted
proposed_date: 2026-05-24
accepted_date: 2026-05-24
codex_review_arc: pending (will land in cycle-6 close commit)
final_commit: TBD (set post-commit)
parent_dec: DEC-V61-202-WORKBENCH-DYNAMIC-GUIDED
phase: M3.1 cycle 6 (engineer mistake-recovery fix)
notion_sync_status: pending_accepted
autonomous_governance: true
counter_status: v6.1 telemetry
charter_class: false
scope_class: sub_dec
ssot: .planning/workbench/GUIDED_CASE_CONSTRUCTION_FLOW.md
predecessors:
  - DEC-V61-202-SUB-M31-CYCLE5-FAILURE-PATH-DOGFOOD  # surfaced BUG-1+2
  - DEC-V61-202-SUB-M30-CYCLE2-PATCH-ENDPOINT       # original endpoint
---

## Why

Cycle-5 failure-path dogfood (`case_007_cycle5_failure_path.py`)
documented two P1 bugs in `manifest_patch`:

1. **BUG-CYCLE5-1**: PATCH `bc.patches.inlet = "not_a_dict"` succeeds
   silently. Manifest's `inlet` overwritten from dict to string,
   breaking the patch-entry contract.
2. **BUG-CYCLE5-2**: cascade — once `bc.patches.inlet` is a string,
   PATCH `bc.patches.inlet.patch_type = "fixedValue"` (revert) returns
   400 because path traversal can't descend through a string node.
   Engineer has no in-workbench path back from the corruption.

Root cause: `manifest_patch._validate_at_or_below_path` runs jsonschema
validation, but `case_manifest.schema.json` only knows about
`bc_contract` — the dynamic-guided UX's `bc.patches.*` subtree is
**outside the schema's surface**, so jsonschema is silent on type
errors there. `_write_at_path` only checks that intermediate segments
are dicts (preventing dict-clobber of intermediates); it doesn't
check that the **leaf** value's type is compatible with what exists.

Both bugs share one root fix: **PATCH must preserve the existing
manifest value's structural type** at the target path. The fix is
surface-agnostic (works for any path, in-schema or not) because it
type-compares against the live manifest, not against a JSON schema.

## What

### In scope

1. **New helper** `_check_type_preservation(manifest, segments, value)`
   in `ui/backend/services/manifest_patch.py`. Returns an error
   message string if the new value's type breaks the existing value's
   structural-type contract, else None.

   Rules:
   - existing **dict** at path → new value MUST be dict
   - existing **list** at path → new value MUST be list
   - existing **scalar** (str / int / float / bool / None) → new value
     MUST be scalar (not dict, not list)
   - path **doesn't exist** → any type allowed (creating new fields
     is the engineer's intent)

   Returned error names the path, the existing type, and the
   offending new type. Reason-keyword vocabulary
   (`type` / `dict` / `expected`) chosen so the cycle-5 dogfood's
   `_is_rejection_with_named_reason()` predicate matches it.

2. **Wire** the check into `apply_field_path_patch` for `op == "set"`
   only (unset is type-neutral — it removes the key). Runs for ALL
   case kinds (`imported_user`, `draft`, `whitelist`) — type
   preservation is a structural invariant, not schema-bound.

3. **Order matters**: the check runs AFTER `_load_for_write` and the
   `expected_state_sha` SHA-check, BEFORE the deepcopy + `_write_at_path`.
   This way it's inside the per-case lock (consistent with R0 P1-1's
   atomicity guarantee) and uses the current manifest as the source
   of truth for "existing type".

4. **Failure envelope**: same shape as the existing
   `_validate_at_or_below_path` failure path —
   `ManifestPatchResponse(success=False, applied_path="",
   new_state_sha=current_sha, validation_errors=[err])`. 200 status,
   not 4xx. Matches engineer-recovery contract (state_sha stays
   valid; engineer retries with corrected value, no SHA-refresh needed).

5. **Unit test** `tests/services/test_manifest_patch_type_preservation.py`
   covering dict→scalar / list→scalar / scalar→dict / scalar→scalar
   allowed / fresh-path allowed / unset still works.

6. **Cycle-5 dogfood regression**: after fix, re-run
   `scripts/dogfood/case_007_cycle5_failure_path.py`. Verdict MUST
   flip from FAIL to PASS for steps 5, 6, 7. Update DOGFOOD report
   to mark BUG-CYCLE5-1, BUG-CYCLE5-2 as FIXED.

### Out of scope (later cycles)

- **BUG-CYCLE5-3** (analyzer misses corruption-by-other-paths) —
  cycle 7+ scope. Cycle 6 fix prevents corruption via the PATCH
  endpoint, but doesn't add an analyzer-side schema check for
  corrupted manifests arriving via other routes (legacy data,
  manual YAML edit, etc.).
- **BUG-CYCLE5-4** (typo'd `patch_type` enum warning) — cycle 7+,
  ergonomics layer.
- **UI "replace whole node" recovery affordance** — frontend, cycle 8+.
- **Generalized jsonschema coverage of `bc.patches.*`** — would
  require extending `case_manifest.schema.json`'s additionalProperties
  surface to describe the new dynamic-guided UX shape. Big scope;
  type-preservation fix sidesteps the need.

## Closure criteria

- [ ] `_check_type_preservation` exists with rules above
- [ ] Wired into `apply_field_path_patch` (set op only, all case kinds)
- [ ] Unit test file exists and passes
- [ ] Cycle-5 dogfood verdict flips to PASS (re-run shows all checks green)
- [ ] DOGFOOD doc updated (BUG-1, BUG-2 marked FIXED with cycle-6 ref)
- [ ] Existing manifest_patch tests still pass (no regression)
- [ ] Codex review ≤ 3 rounds → APPROVE (or user-ratified close)
- [ ] DEC Proposed → Accepted
- [ ] Notion sync (session-end, Accepted DECs only)

## Risks + mitigations

| Risk | Mitigation |
|---|---|
| Type preservation breaks a legitimate "I really meant to change the shape" PATCH (e.g. engineer changes a list-valued field to a dict mid-design) | The check only fires when an existing value is present. To change shape, the engineer first unsets the path (op=unset, no type check), then sets the new shape. Two PATCHes — explicit intent. |
| `bool` is subclass of `int` in Python — `isinstance(True, int)` is True. Could permit unintended bool↔int swap | We treat all scalars (str/int/float/bool/None) as one class — bool→str or str→bool is allowed. Scalar→scalar is intentionally permissive; engineer-typo at the leaf is the analyzer's job (BUG-4 territory), not the PATCH endpoint's job. |
| Adding a structural check inside the lock slows PATCH | Check is O(path-depth) dict traversal. Negligible vs the I/O cost already inside the lock. |
| `unset` of an intermediate dict followed by `set` of a scalar at the same path would succeed (loses the structural-preservation guarantee in a 2-PATCH sequence) | This is the documented escape hatch. The check protects against single-PATCH accidents, not deliberate engineer action across PATCHes. |

## Provenance

- Charter: DEC-V61-202-WORKBENCH-DYNAMIC-GUIDED
- SSOT: `.planning/workbench/GUIDED_CASE_CONSTRUCTION_FLOW.md`
- Surfaced by: cycle-5 DOGFOOD report (BUG-CYCLE5-1, BUG-CYCLE5-2)
- User mandate 2026-05-24: 持续开发，自动执行下一步建议

Surface-scan-found: `ui/backend/services/manifest_patch.py:_write_at_path`
(line 249) does intermediate-dict check but no leaf-type check; pre-existing
`_validate_at_or_below_path` (line 331) is jsonschema-bound, schema
silent on `bc.patches.*`. Disposition: extend `apply_field_path_patch`
in-place with new structural helper; no parallel-new service, no schema
file modification.
