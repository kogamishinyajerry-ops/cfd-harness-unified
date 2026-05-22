# Dogfood · case_007 KCS VOF · M3.0 cycle 3 focus_patch driver

> **Cycle**: DEC-V61-202-SUB-M30-CYCLE3-FOCUS-DRIVER
> **Date**: 2026-05-22
> **Surface under test**: GET frame with `?focus_patch=<name>` → rail.primary + bottom_cards bias
> **Method**: programmatic via FastAPI TestClient in `scripts/dogfood/case_007_cycle3_focus.py`
> **Verdict**: **PASS** · 8/8 checks

## Context

Cycle 1 surfaced what's blocking; cycle 2 closed the observation → action → state-change
loop with a PATCH endpoint and topbar CTA. Cycle 3 wires the **4th SSOT driver**
("focus") to actually do something — when an engineer is looking at a specific patch
(via the Viewport pick or a deep-link `?focus_patch=`), the rail.primary + bottom_cards
should preferentially surface problems mentioning that patch within the same severity
bucket.

Per SSOT §3 driver 4:
> Engineer clicks "inlet" patch in viewport → rail auto-switches to inlet BC editor;
> advisor cards filtered to inlet-relevant.

This dogfood proves the BACKEND half of that loop. The frontend half (FacePickContext
→ URL sync) is covered by `FacePickUrlSync.test.tsx` (6/6 vitest).

## Test design

Synthetic case_007 state:
- `manifest`: interFoam + kOmegaSST + vof_contract.phases = [water, air]
- `artifacts.bc_audit.json`:
  - `gate_status: FAIL`
  - `patch_coverage_dimension.gaps_by_field`:
      - `U: [inlet, outlet, wall]`
      - `p: [inlet, outlet]`
  - `value_match_dimension.gaps_by_field`:
      - `alpha.water: [inlet]`  ← outlet NOT mentioned here on purpose

The asymmetry between dimensions is what makes the focus driver visible:
- `focus_patch=inlet` should bubble both patch_coverage AND value_match toward
  the top (both mention inlet).
- `focus_patch=outlet` should bubble only patch_coverage (value_match doesn't
  mention outlet).

## Trace

```
[baseline]     rail.title = 'bc_audit.json FAIL'
               bottom_cards top-3 = ['bc_audit.json FAIL',
                                     'patch_coverage FAIL',
                                     'value_match FAIL']

[focus=inlet]  rail.title = 'patch_coverage FAIL'
               bottom_cards top-3 = ['patch_coverage FAIL',
                                     'value_match FAIL',
                                     'bc_audit.json FAIL']

[focus=outlet] rail.title = 'patch_coverage FAIL'
               bottom_cards top-3 = ['patch_coverage FAIL',
                                     'bc_audit.json FAIL',
                                     'value_match FAIL']

[focus=ghost]  rail.title = 'bc_audit.json FAIL'   ← falls through to baseline
               rail.kind = problem_fix
```

Interpretation:
- **focus=inlet**: patch_coverage moves to rail.primary AND top of cards.
  value_match (which mentions inlet) bubbles ahead of bc_audit (whole-artifact,
  no specific patch).
- **focus=outlet**: patch_coverage still wins (it mentions outlet via
  gaps_by_field's `U` + `p`). value_match does NOT bubble (it only mentions inlet),
  so bc_audit slots ahead of it. This is the asymmetric bias working as designed.
- **focus=ghost_patch**: nothing in the case mentions this patch name; the
  decide() falls through to severity-sort (baseline).

## Closure criteria (cycle 3)

| # | Check | Result |
|---|---|---|
| 1 | Baseline frame returned with bottom_cards populated | PASS |
| 2 | focus=inlet reorders bottom_cards vs baseline | PASS |
| 3 | focus=outlet reorders bottom_cards vs baseline | PASS |
| 4 | focus=inlet and focus=outlet produce DIFFERENT bottom_cards order | PASS |
| 5 | focus=ghost_patch preserves baseline ordering (no-match fallback) | PASS |
| 6 | focus=inlet rail.primary differs from baseline rail.primary | PASS |
| 7 | focus=ghost_patch returns a valid frame (no errors, no crash) | PASS |
| 8 | Cards remain length-stable (focus reorders, doesn't drop) | PASS |

**Verdict**: PASS · the focus_patch driver actually changes the UI when the engineer
indicates they are "looking at" a patch, and gracefully degrades when no patch matches.

## Reproduction

```bash
cd /Users/Zhuanz/Desktop/cfd-audit-merge
PYTHONPATH=. .venv/bin/python scripts/dogfood/case_007_cycle3_focus.py
```

## Confidence

`confidence: high` — happy-path + no-match fallback both verified empirically; the
behavior is deterministic given a fixed fixture (no real audit pipeline or LLM in
the loop). Backend 9 unit tests (test_workbench_frame_cycle3.py) cover the per-
matcher contract (field_path / body_text / gaps_by_field) at the unit level; this
dogfood proves the integration into the real route + real `decide()`.
