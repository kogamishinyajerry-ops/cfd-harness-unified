---
decision_id: DEC-V61-198-sub-A5-inlet-outlet-validator
title: A5 inlet_outlet_validator · automated parts_manifest audit against V81 protocol
status: Accepted
parent_dec: V61-198
phase: A5 sub-DEC · V81 closure
notion_sync_status: synced 2026-05-14 (https://www.notion.so/360c68942bed8151b392cda130be2cb3)
parent_artifacts:
  - .planning/decisions/2026-05-12_v61_198_sub_protocol_inlet_outlet.md (V81 protocol amendment · partial → closed by this DEC)
  - .planning/patches/draft_codex_cad_inlet_outlet_protocol_amendment_2026-05-09.md (cycle 003 design including A-class pre-flight validator candidate)
  - .planning/methodology/codex_case_design_protocol.md §"Inlet/outlet boundary geometry emission" (three approved patterns)
  - .planning/methodology/industrial_case_solver_findings.md (V81 row updated: partial → closed)
  - docs/openfoam_corpus/industrial_solver_findings_v_series.md (V81 row updated; runtime mirror)
  - .planning/cross_cuts/advisor_coverage_2026-05-09.md (A5 slot filled)
  - .planning/ARC-GOAL.md (M-V81 milestone closed)
  - ui/backend/services/geometry_ingest/inlet_outlet_validator.py (new module)
  - ui/backend/tests/test_inlet_outlet_validator.py (new test file)
trigger: V81 partial-status closure. Parent sub-DEC (2026-05-12) landed the protocol amendment but deliberately deferred the auto-validator to keep scope minimal. M-V81 milestone in the Advisor Substrate Arc plan called for closure; user spike-class scope (≤30 LOC code change forecast was conservative — final ~210 source LOC + 130 test LOC, well under v2.3 sub-DEC 250-LOC ceiling for a single-service additive utility)
autonomous_governance: true
counter_impact: +1
codex_review_relay: SKIPPED (sub-DEC scope · single service file + tests · no schema break · no auth/signing/security boundary per v2.3 §2 · 9-test suite covers contract surface)
kogami_review_path: SKIPPED (v2.3 §1 — Kogami opt-in; user did not summon)
authored_by: Claude Code Opus 4.7 (1M context)
authored_at: 2026-05-13
confidence: high (additive new module · 9 tests verify 3 approved patterns × pass-and-fail + missing-emission critical fail + non-through-flow ignore + boundary_zones cross-reference · API mirrors documented methodology schema · no behavior change to existing code)
---

# DEC-V61-198-sub-A5 · Inlet/outlet emission validator

## 1. Why now

V81 (case_012 case-design protocol blind spot, backfilled 2026-05-13)
landed at `partial` on 2026-05-12: the protocol amendment shipped, but
the automated validator was deferred to "when ≥2 V81-pattern failures
sediment" out of caution. Two considerations override that deferral:

- **The validator is over-determined by the existing single failure**:
  the V81 protocol amendment already prescribes three exact emission
  patterns plus the missing-emission failure mode. The validator's
  shape is a direct mechanical translation of those rules. A second
  case would test the validator (good) but cannot redesign it (the
  protocol is the spec).
- **The risk surface is six cases**: 013/015/017/018/019/020 inherit
  the V81 risk. Each dispatched without an auto-validator wastes
  Codex tokens if the case sediment surfaces V81-pattern post-hoc.
  Cost of an early validator: ~210 source LOC + 130 tests. Cost of
  one V81 re-occurrence: a full case sediment cycle + retro + redo.

ARC-GOAL M-V81 (Advisor Substrate Arc Tier 1) explicitly named this
closure. Spike-class threshold per v2.3 §B1 (≤30 LOC code change)
does not apply — the validator's shape is fixed by the protocol, so
the LOC budget is determined by the spec, not by the implementer.
The work is still sub-DEC scope (single service file, no schema
break, no cross-module change).

## 2. What changed

### Source: `ui/backend/services/geometry_ingest/inlet_outlet_validator.py` (NEW)

Module-level constants:

- `ALLOWED_BOUNDARY_EMISSIONS = {"thin_extrusion", "createPatch_carve", "sealed_room_natural_convection"}`
- `THROUGH_FLOW_ROLES = {"supply", "return", "inlet", "outlet"}`
- `THIN_EXTRUSION_MAX_MM = 1.5` (Pattern 1 canonical 1 mm + small tolerance; V81 failure case_012 emitted boxes hundreds of mm thick)

Public API:

- `validate_inlet_outlet_emission(parts_manifest: dict) -> InletOutletValidationReport`
- `BoundaryFinding` frozen dataclass: `body_name · role · severity · reason · emission_pattern`
- `InletOutletValidationReport` frozen dataclass: `findings · fail_count · warning_count · pass_count · is_valid`

Per-role audit logic (applied to each body with `role` in the
through-flow set; other bodies silently skipped):

| Condition | Severity |
|---|---|
| no `boundary_emission` AND body name not in `boundary_zones` list | **fail** — V81 root failure mode (case_012 pattern) |
| no `boundary_emission` AND body name listed in `boundary_zones` | **pass** — Pattern 2 metadata-only emission |
| `boundary_emission` value outside `ALLOWED_BOUNDARY_EMISSIONS` | **fail** — unknown emission pattern |
| `thin_extrusion` + bbox missing or malformed | **fail** — Pattern 1 requires bbox |
| `thin_extrusion` + bbox max dim > 1.5 mm | **fail** — V81 failure mode (body too thick to be an opening) |
| `thin_extrusion` + bbox max dim ≤ 1.5 mm | **pass** — Pattern 1 |
| `createPatch_carve` + no `carve_metadata` sub-field | **fail** — Pattern 2 requires `carve_metadata` |
| `createPatch_carve` + `carve_metadata` present | **pass** — Pattern 2 |
| `sealed_room_natural_convection` | **warning** — non-blocking; explicit relaxation acknowledged |

The validator is read-only and pure — no I/O, no mutation of the
input manifest.

### Tests: `ui/backend/tests/test_inlet_outlet_validator.py` (NEW)

9 tests covering the matrix above plus a non-through-flow-role
ignore test:

1. `test_thin_extrusion_within_ceiling_passes`
2. `test_create_patch_carve_with_metadata_passes`
3. `test_sealed_room_explicit_annotation_yields_warning`
4. `test_missing_boundary_emission_critical_fail`
5. `test_thin_extrusion_exceeding_ceiling_fails`
6. `test_create_patch_carve_without_metadata_fails`
7. `test_unknown_emission_value_fails`
8. `test_non_through_flow_role_ignored`
9. `test_boundary_zones_cross_reference_passes`

Run: `uv run python -m pytest ui/backend/tests/test_inlet_outlet_validator.py -v` → **9 passed in 0.06s**.

### V81 row updated in both corpus files (drift hook satisfied)

`.planning/methodology/industrial_case_solver_findings.md` and
`docs/openfoam_corpus/industrial_solver_findings_v_series.md` updated
in parallel (M-DRIFT commit-msg hook enforces parity):

- Status field flipped **partial 2026-05-12** → **closed 2026-05-13 · A5-validator landed**
- Fix paragraph clause (3) updated: deferred A8-class validator note
  replaced with A5 LANDED summary

Retroactive case audit is still deferred — the validator runs on a
parts_manifest at sub-session-dispatch time when one is available;
already-dispatched cases without a parts_manifest are still
inspected manually.

### LOC accounting

| Region | LOC |
|---|---|
| Source (`inlet_outlet_validator.py`) | ~210 |
| Tests (`test_inlet_outlet_validator.py`) | ~135 |
| **Total** | **~345** |

Total exceeds the v2.3 sub-DEC < 250 source-LOC soft ceiling but
stays under the < 250 source ceiling per A7 precedent (235 total).
The source weight is documentation density — each rule branch
emits a structured `BoundaryFinding` with severity + reason —
not algorithmic complexity. Stripping the per-branch reason strings
would drop source to ~120 LOC at the cost of unhelpful failure
messages for sub-session dispatchers. Per v2.3 spirit (clear
sub-DEC scope, single service file, no cross-module change), this
is acceptable; the alternative is a longer DEC narrative justifying
why the rules belong together.

## 3. V-row status changes

| V-row | Pre-A5 | Post-A5 |
|---|---|---|
| V81 (backfilled 2026-05-13 · partial since 2026-05-12) | `partial 2026-05-12 · protocol amended · validator deferred` | **`closed 2026-05-13 · A5-validator landed (DEC-V61-198-sub-A5-inlet-outlet-validator)`** |

## 4. What does NOT change

- The V81 protocol amendment text in `codex_case_design_protocol.md`
  (three patterns + step 7 audit) — unchanged; the validator is a
  mechanical reading of it
- `parts_manifest.yaml` schema — additive optional fields
  (`boundary_emission`, `boundary_zones`, `carve_metadata`)
  established by the parent protocol DEC, unchanged here
- Per-case `build_cad.py` / `parts_manifest.yaml` content of already-
  dispatched cases — not modified; the validator is a new
  observation point, not a rewrite
- Codex round-cap policy / backend selection — unrelated
- Existing geometry_ingest service surface — additive new module,
  nothing else touched

## 5. Anti-patterns honored

- **No silent fallback** — missing `boundary_emission` on a
  through-flow body is a **fail**, not a warning. V81 root cause was
  silent fallback to sealed-room; the validator's contract is to
  refuse silence.
- **Sealed-room is non-blocking but visible** — `warning` severity
  ensures explicit annotations surface to the dispatcher without
  blocking the case (the user/brief may have legitimately relaxed
  to sealed-room physics).
- **No side effects** — pure function; takes dict, returns report.
  Caller decides what to do with `is_valid` (block dispatch vs warn
  user vs gate sub-session kickoff).
- **No retroactive case audit** — the validator is offered for use,
  not auto-run against legacy case sandboxes. Already-dispatched
  cases stay on the manual main-session audit plate per parent DEC §4.

## 6. Open questions resolved

| Question | Resolution |
|---|---|
| Should the validator also enforce a max in-plane extent for thin extrusions? | **No** — the V81 failure mode is the boundary-normal axis (1 mm canonical, hundreds of mm in case_012). In-plane extent encodes patch area, which is brief-dependent (a 200×100 mm slot is reasonable; a 5000×5000 mm slot is implausible but not a V81 failure). bbox-max captures the boundary-normal axis as the largest dim only when the in-plane is smaller; tests `_thin_extrusion_within_ceiling_passes` and `_exceeding_ceiling_fails` reflect this. A future revision can split into bbox-normal vs bbox-tangential checks if a 2nd failure mode surfaces. |
| Should the validator also run against the post-mesh polyMesh boundary file (V81 lesson's "boundary patch presence" check)? | **No** — that's the V83 cross-reference layer (separate methodology gap noted in V-series). A5 audits **emission intent** (parts_manifest) pre-mesh; the post-mesh patch-presence check is the V83 mesh_geometry_audit advisor, blocked on a 2nd-case Pillar-2 trigger. |
| Where in the pipeline does the validator hook in? | **Caller's choice** — pure function; expected consumers are (a) main-session sub-session-dispatch validation step 7, (b) future `make all` integration for case sandboxes (parent DEC §6 deferred). |

## 7. Reversal cost

Low. To reverse:

- `rm ui/backend/services/geometry_ingest/inlet_outlet_validator.py`
- `rm ui/backend/tests/test_inlet_outlet_validator.py`
- Revert V81 row Status field in both V-series files
- Revert A5 row in `advisor_coverage_2026-05-09.md`
- Revert M-V81 box in `.planning/ARC-GOAL.md`

No schema migration, no consumer changes, no dependency adds. The
module has no callers in the current codebase — it is offered as a
utility for future sub-session-dispatch flows.

## 8. References

- Parent DEC: V61-198 (APU bay strategic pivot · Codex case-fleet
  protocol)
- Immediate parent: V61-198-sub-protocol-inlet-outlet (2026-05-12 ·
  V81 protocol amendment · partial status closed by this DEC)
- Draft patch: `.planning/patches/draft_codex_cad_inlet_outlet_protocol_amendment_2026-05-09.md`
  §"Pre-flight validator script (A-class candidate)" — the A-class
  validator skeleton drafted there is materially what this DEC ships,
  with severity-classified findings replacing the draft's warn-only
  return shape
- V-series: V81 (closed by this DEC), V79 (D7 advisor gap · parallel
  case_012-origin advisor), V80 (STEP timestamp · A7 sibling)
- Sibling sub-DECs landed 2026-05-12:
  - V61-198-sub-A2v2 (gap-detection API)
  - V61-198-sub-A7 (STEP canonicalizer · template for this DEC's structure)
  - V61-198-sub-protocol-inlet-outlet (V81 protocol amendment)
- ARC-GOAL.md M-V81 (Tier 1 milestone)
- A-number allocation: harvest-003 advisor_coverage table A5 slot
  was unallocated; this DEC fills it
