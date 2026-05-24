---
decision_id: DEC-V61-202-SUB-M31-CYCLE8-PATCH-TYPE-ENUM-WARNING
title: M3.1 cycle 8 — info warning for unknown OpenFOAM patch_type (closes BUG-CYCLE5-4)
status: Accepted
proposed_date: 2026-05-24
accepted_date: 2026-05-24
codex_review_arc: R0 (1 P2 catalog-reuse + 1 P2 bc non-dict crash) → R1 (1 P1 import-tree leak + 1 P2 groovyBC regression) → R2 (1 P2 swak4Foam not a real type · fixed inline · cap=3 close)
final_commit: cf1541b
parent_dec: DEC-V61-202-WORKBENCH-DYNAMIC-GUIDED
phase: M3.1 cycle 8 (final cycle-5 backlog drain)
notion_sync_status: pending_accepted
autonomous_governance: true
counter_status: v6.1 telemetry
charter_class: false
scope_class: sub_dec
ssot: .planning/workbench/GUIDED_CASE_CONSTRUCTION_FLOW.md
user_ratification: 2026-05-24 AskUserQuestion — "Cycle 8 = BUG-4 P3 polish"
predecessors:
  - DEC-V61-202-SUB-M31-CYCLE5-FAILURE-PATH-DOGFOOD  # surfaced BUG-4
  - DEC-V61-202-SUB-M31-CYCLE7-CORRUPTED-MANIFEST-RAIL  # immediate predecessor
---

## Why

Cycle-5 failure-path dogfood BUG-CYCLE5-4 (the last open cycle-5
backlog item, P3 / ergonomics): PATCH `bc.patches.inlet.patch_type
= "fixedValue_typo"` succeeds with no validation warning. OpenFOAM
accepts arbitrary strings here and only validates at solver-startup
time — a typo therefore manifests as a cryptic runtime FATAL IO
ERROR rather than a workbench-time gap.

The original dogfood explicitly flagged this as a design call:
> "This might be intentional (OpenFOAM accepts arbitrary strings here
> and validates at solver-startup time). But for engineer ergonomics,
> the workbench could surface a warning…"
> "Optional — weigh ergonomics vs free-text flexibility."

User ratified the polish (AskUserQuestion 2026-05-24).

## What

### In scope

1. **`_KNOWN_OPENFOAM_PATCH_TYPES`** frozenset in
   `case_completeness/analyzer.py` listing the common 80% of patch
   types: constraint types (empty/wedge/symmetry/cyclic/processor/
   wall/patch), field-level types (fixedValue/zeroGradient/noSlip/
   slip/inletOutlet/totalPressure/etc), VOF/multiphase types
   (alphaContactAngle/etc), and low-Mach pressure-coupling types
   (prghPressure/etc). ~30 entries.

2. **Walk + flag** in `_analyze_imported`: after the bc.patches
   critical check, iterate `raw_manifest_yaml["bc"]["patches"]`.
   For each patch with a string `patch_type` not in the known set,
   add a `MissingField(severity="info", field_path=
   "bc.patches.{name}.patch_type", why=…)`.

3. **`expected_info_count`** updated to equal `unknown_patch_type_count`
   so readiness percentage stays balanced (each unknown adds 1 to
   both total and missing → present unchanged).

4. **Unit tests** in
   `ui/backend/tests/test_case_completeness_patch_type_warning.py`:
   - all-known → no info gaps
   - constraint types recognized
   - typo'd value → 1 info gap with full message context
   - multiple unknowns → multiple gaps
   - info gap does not block `ready_for_archive`
   - non-dict patch entry (cycle-7 corruption surface) doesn't crash
   - patch entry with no `patch_type` field is skipped (other layers
     own missing-field warnings)

### Why severity=info (not warning, not critical)

- **info** = soft-gap tier in `workbench_decide._pick_rail_primary`
  (lowest priority — only shown when nothing else fires)
- Engineer can still progress (`topbar_cta.enabled = True`)
- Mirrors the original dogfood characterization: "ignore vs correct"
  is the engineer's call

If "warning" or "critical" were used, the rail would force the user
to acknowledge or block proceed — over-correcting on what the source
dogfood explicitly called a "weigh ergonomics vs free-text
flexibility" trade-off.

### Out of scope

- **Custom user enum lists** (engineer-configurable known-types
  vocabulary) — cycle 9+ if a real engineer flags `pressureInletOutletVelocity`
  too often as "false positive"
- **Whitelist-case patch_type scan** — the whitelist analyzer is a
  separate path; only the imported_user surface gets the warning
- **Auto-correct suggestions** ("did you mean fixedValue?") —
  cosmetic UI enhancement, frontend cycle territory

## Closure criteria

- [x] `_KNOWN_OPENFOAM_PATCH_TYPES` frozenset added
- [x] `_analyze_imported` walks bc.patches + adds info gaps
- [x] `expected_info_count` reflects unknown count
- [x] 8/8 new unit tests pass
- [x] 49/49 existing `test_case_completeness` tests pass
- [x] 146/146 PATCH+frame regression tests pass
- [x] Cycle-5 dogfood still 10/10 PASS
- [ ] Codex review ≤ 3 rounds → APPROVE (or user-ratified close)
- [ ] DEC `final_commit` set + DOGFOOD `BUG-CYCLE5-4` marked FIXED
- [ ] Notion sync (session-end batch)

## Risks + mitigations

| Risk | Mitigation |
|---|---|
| Vocabulary list misses a common type, engineers see spurious info warnings | Severity=info is the lowest gap; doesn't block. False positives are easy to ignore. Add types to the set if reported. |
| Auto-warning becomes annoying noise in cases with intentionally custom types (e.g. groovyBC variants) | `groovyBC`, `codedFixedValue`, `uniformFixedValue` are already in the set. Engineers can request additions; the cost of being wrong-permissive is the same warning they would otherwise ignore. |
| Test coverage for "non-dict patch entry" overlaps with cycle 7 | The cycle-8 test checks cycle-8 doesn't *crash* on cycle-7 territory (defensive). Pure no-overlap is impossible since both layers walk the same dict. |

## Provenance

- Charter: DEC-V61-202-WORKBENCH-DYNAMIC-GUIDED
- SSOT: `.planning/workbench/GUIDED_CASE_CONSTRUCTION_FLOW.md`
- Surfaced by: cycle-5 DOGFOOD `BUG-CYCLE5-4` (explicitly Optional)
- User ratification 2026-05-24
- User mandate 2026-05-24: 持续开发，自动执行下一步建议

Surface-scan-found: `ui/backend/services/case_completeness/analyzer.py:_analyze_imported`
(line 495); existing constraint-types list at
`ui/backend/services/case_solve/bc_setup_from_stl_patches.py:170`
(`_CONSTRAINT_PATCH_TYPES`) covers different scope (symmetry-defect
fix only). Disposition: parallel-new constant in analyzer (different
purpose: warning-surface vs runtime-rewrite). No conflict.
