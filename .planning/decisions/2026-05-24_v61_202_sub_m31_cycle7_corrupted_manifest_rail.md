---
decision_id: DEC-V61-202-SUB-M31-CYCLE7-CORRUPTED-MANIFEST-RAIL
title: M3.1 cycle 7 — surface corrupted-manifest critical on rail (fix BUG-CYCLE5-3)
status: Accepted
proposed_date: 2026-05-24
accepted_date: 2026-05-24
codex_review_arc: R0 APPROVE (0 P1 / 0 P2 / 0 P3 · "I did not identify an actionable bug introduced by this diff")
final_commit: 0e912b0
parent_dec: DEC-V61-202-WORKBENCH-DYNAMIC-GUIDED
phase: M3.1 cycle 7 (manifest-corruption visibility)
notion_sync_status: synced 2026-05-24 (https://www.notion.so/36ac68942bed8156854dfee0533bc755)
autonomous_governance: true
counter_status: v6.1 telemetry
charter_class: false
scope_class: sub_dec
ssot: .planning/workbench/GUIDED_CASE_CONSTRUCTION_FLOW.md
predecessors:
  - DEC-V61-202-SUB-M31-CYCLE5-FAILURE-PATH-DOGFOOD  # surfaced BUG-3
  - DEC-V61-202-SUB-M31-CYCLE6-PATCH-TYPE-PRESERVATION  # PATCH-side closure
---

## Why

Cycle-5 failure-path dogfood documented BUG-CYCLE5-3: when a manifest
is corrupted on disk (e.g. legacy data, manual YAML edit, or any
future PATCH-bypass), the workbench rail still shows
`kind=step_default` ("ready to proceed") instead of surfacing the
corruption.

Cycle 6 prevented corruption via the PATCH endpoint (type
preservation). Cycle 7 closes the analyzer-side gap so corruption
arriving via **any** ingress path becomes visible.

Probe (post-cycle-6, manifest corrupted directly to disk):
- `analyze_case_completeness()` correctly returns 1 critical missing
  at `field_path="case_manifest.yaml"` ("fails schema validation")
- Workbench `decide()` filters it out because `_gaps_for_step` only
  includes gaps whose `field_path` matches `_STEP_PATH_PREFIXES[step]`
- No prefix matches `case_manifest.yaml` (it's a meta-path, not a
  manifest field) → critical is dropped → rail falls through to
  `step_default`

Root: structural-meta gaps (corruption-class) are globally blocking
but the step-prefix filter treats them as off-step noise.

## What

### In scope

1. **`_gaps_for_step` short-circuit** for structural-meta critical
   gaps. Add a constant `_STRUCTURAL_META_PATHS =
   frozenset({"case_manifest.yaml"})` and unconditionally include
   matching critical gaps regardless of step. Severity `critical` is
   the gate (only manifest-schema-invalid surfaces this path; other
   uses can be added later if they emerge).

2. **Unit test** in
   `ui/backend/tests/test_workbench_decide_corrupted_manifest.py`
   exercising: corrupted-manifest fixture → `decide()` returns a
   critical info_gap rail on every step (1-5), with topbar CTA
   disabled.

3. **Extend cycle-5 dogfood** with a corruption-via-disk regression
   step: write a corrupted manifest directly, fetch frame, assert
   rail surfaces the critical. This protects the new code path
   without coupling to the PATCH flow (cycle 6 already covers PATCH).

4. **Out of scope (cycle 8+)**: a "repair corrupted manifest" UI
   affordance (today's recovery is manual YAML edit). The rail will
   say `kind=info_gap` with `why="Imported case_manifest.yaml is
   parseable YAML but fails schema validation: …"` — engineer-readable,
   but not auto-fixable from the UI.

### Why structural-meta only (not all corruption-class gaps)

`case_manifest.yaml` is the only meta-path the analyzer surfaces
today. Treating "any field_path not in any step prefix" as
unconditional would over-promote — many legitimate gaps have
step-specific prefixes by design. The narrow allow-list (just
`case_manifest.yaml`) closes BUG-3 without expanding the
classification surface. Future additions (e.g. circular-import
detection, irreparably-malformed YAML structure) can join the
allow-list as they arise.

## Closure criteria

- [ ] `_STRUCTURAL_META_PATHS` exists + `_gaps_for_step` honors it
- [ ] Unit test (multi-step + topbar CTA + rail.kind) passes
- [ ] Cycle-5 dogfood extended with disk-corruption regression step,
      verdict still PASS
- [ ] Existing workbench_decide / frame regression tests still pass
- [ ] Codex review ≤ 3 rounds → APPROVE (or user-ratified close)
- [ ] DEC Proposed → Accepted
- [ ] DOGFOOD report updated (BUG-3 marked FIXED)
- [ ] Notion sync (session-end, Accepted DECs only)

## Risks + mitigations

| Risk | Mitigation |
|---|---|
| Unconditional gap promotion masks a legitimate step-specific finding | Severity-priority rules unchanged. A FAIL-class audit finding still wins over a critical gap (see `_pick_rail_primary` priority tree). The corruption rail only displaces lower-priority items at the same step. |
| The allow-list grows unbounded as analyzer surfaces more meta-paths | Allow-list is explicit + small; reviewing each addition is cheap. Pattern doesn't grow into ad-hoc filtering logic. |
| Engineer cannot repair via UI; rail says "fix the YAML" with no action | Documented as out-of-scope (cycle 8+ UI affordance). Today's escape hatch is direct YAML edit — same as any corruption-detection tool. |
| Analyzer adds a new manifest-corruption critical with a different field_path the allow-list doesn't cover | The analyzer is the SSOT for what "critical at structural-meta path" means. Adding new such paths means simultaneously extending `_STRUCTURAL_META_PATHS`. Caught by code review since the touch points are colocated in mind. |

## Provenance

- Charter: DEC-V61-202-WORKBENCH-DYNAMIC-GUIDED
- SSOT: `.planning/workbench/GUIDED_CASE_CONSTRUCTION_FLOW.md`
- Surfaced by: cycle-5 DOGFOOD `BUG-CYCLE5-3`
- Probe finding (post-cycle-6): analyzer surfaces critical correctly;
  `_gaps_for_step` filters it out via step-prefix mismatch.
- User mandate 2026-05-24: 持续开发，自动执行下一步建议

Surface-scan-found: `ui/backend/services/workbench_decide.py:_gaps_for_step`
(line 955) — step-prefix filter excludes meta-paths. Disposition:
extend in-place with allow-list pattern. No analyzer-side changes
(analyzer already does its job; decide() was the filter).
