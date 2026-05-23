# DOGFOOD · M3.1 Cycle 1 · ship_vof form-helper skeleton

**DEC**: `2026-05-23_v61_202_sub_m31_cycle1_form_helper_shipvof.md` (Proposed)
**Date**: 2026-05-23
**Dogfood script**: `scripts/dogfood/case_007_cycle1_form_helper.py`
**Verdict**: **PASS** (7/7 checks · post Codex R0 verbatim fixes)
**Codex**: R0 = 1 P1 + 1 P2 closed verbatim (case_family solver-inference
fallback + duplicate-CTA suppression). See closure addendum at DEC bottom.

---

## What this cycle adds

When a `ship_vof` case lands at step 4 (boundary) without `bc.patches`
configured, the workbench rail now offers a one-click **"应用骨架 /
Apply skeleton"** CTA that PATCHes the canonical 3-patch ship-VOF
boundary skeleton — `inlet:fixedValue + outlet:zeroGradient +
wall:noSlip` — in a single round trip.

This is the first concrete "domain-aware UI form helper" from the M3.0
retro M3.1 charter recommendation. The cycle-7 surrogate's
client-side `_synthesize_value("bc.patches")` is now a real engineer
affordance at the rail.

---

## Journey trace

```
Step-4 GET frame on sparse ship_vof manifest →
  rail.kind = info_gap
  rail.field_path = bc.patches
  rail.cta_label = "应用骨架 / Apply skeleton"
  rail.suggested_skeleton keys = ['inlet', 'outlet', 'wall']

PATCH /api/cases/.../manifest with skeleton value →
  status = 200
  success = True
  applied_path = bc.patches

Step-4 GET frame post-PATCH →
  rail.kind = step_default
  rail.field_path = None
  manifest bc.patches keys = ['inlet', 'outlet', 'wall']
```

The rail surfaces the gap, the engineer clicks once, the skeleton
lands schema-validated, the rail clears. The whole loop is one
round-trip on the same `/manifest` endpoint that scalar `suggested_default`
applies use — no parallel construction track.

---

## Codex R0 closure (1 P1 + 1 P2 · verbatim · 1 round)

- **P1 · case_family not persisted in imported-case flow**: the M5
  `case_scaffold/manifest_writer.py` writes `source/origin/created_at`
  but not `case_family`. Real imported cases never carry it, so the
  cycle-1 lookup returned None for every ship_vof case in production —
  the feature only worked in tests/dogfood that hand-injected the
  field. Fix: added `_resolve_case_family(state)` with two-step
  resolution: (1) explicit `manifest["case_family"]`, then (2)
  solver-based inference — `physics.solver == "interFoam"` → ship_vof.
  The dogfood manifest no longer hand-injects `case_family`, mirroring
  a real imported case; the skeleton still fires via the inference
  fallback.

- **P2 · duplicate "Apply skeleton" buttons**: when only a skeleton
  was offered, the backend set `cta_label = "应用骨架 / Apply skeleton"`
  on the primary CTA, but the primary's `canApply` evaluator needs
  `suggested_default` (which is null on a skeleton-only rail), so the
  primary rendered disabled while the secondary skeleton CTA rendered
  live — two identical buttons, one dead. Fix: when only the skeleton
  is the affordance, the backend now sets `cta_label = null`; the
  frontend renders only the secondary skeleton button.

Regression tests added:
- `test_decide_skeleton_inferred_from_interFoam_when_case_family_missing`
- `test_decide_no_skeleton_when_case_family_unknown` (strengthened to
  explicitly use a non-interFoam solver so the inference fallback
  doesn't pollute the assertion)
- Frontend: `does NOT render primary CTA when only skeleton is offered`

## Checks (7/7 PASS)

```
  [PASS] Rail at step 4 surfaces suggested_skeleton
  [PASS] Skeleton has canonical inlet/outlet/wall keys
  [PASS] Primary cta_label suppressed (skeleton-only path)
  [PASS] Rail provenance records skeleton_keys
  [PASS] PATCH with skeleton value returns 200 + success=True
  [PASS] Manifest bc.patches landed with 3 entries (inlet/outlet/wall)
  [PASS] Post-PATCH rail no longer surfaces bc.patches as a gap
```

Manifest used in dogfood has **NO `case_family`** (mirroring a real
imported case post-R0 fix). The skeleton fires via the solver-based
inference: `physics.solver: interFoam` → `case_family: ship_vof`.

---

## Test coverage delta

| Layer | File | Tests added |
|---|---|---|
| Backend rail | `ui/backend/tests/test_workbench_frame.py` | +3 tests (skeleton attached on ship_vof / no skeleton on unknown family / scalar wins primary CTA when both present) |
| Frontend component | `ui/frontend/src/pages/workbench/step_panel_shell/dynamic_frame/__tests__/DynamicFramePanel.test.tsx` | +5 tests (renders / omits / disabled-without-context / coexists with scalar / click calls PATCH with skeleton payload) |

Full backend regression: **80/80 PASS** on the 4 workbench_frame test
files (32 + 24 + 13 + 14, includes cycle 1 + provenance + cycle 2/3
baseline).

Full frontend regression: **904/904 PASS** across 87 test files.

TypeScript: clean (`npx tsc --noEmit` on `ui/frontend/`).

---

## Where the skeleton lives

`ui/backend/services/workbench_decide.py::_FORM_HELPER_SKELETONS`:

```python
_FORM_HELPER_SKELETONS: dict[tuple[str, str], dict] = {
    ("bc.patches", "ship_vof"): {
        "inlet":  {"patch_type": "fixedValue",   "fields": {"U": [1.0, 0.0, 0.0]}},
        "outlet": {"patch_type": "zeroGradient", "fields": {"p": "zeroGradient"}},
        "wall":   {"patch_type": "noSlip",       "fields": {}},
    },
}
```

Lookup is keyed by `(field_path, case_family)` so future cycles
(RANS / LES / compressible / CHT) add entries without disturbing
this one.

`case_family` is read from `state.manifest` (raw dict) because the
Pydantic `CaseManifest` schema doesn't declare it. Adding it as a
typed field is M3.1 cycle 2+ scope.

---

## What this does **not** prove

1. **Domain correctness of the placeholder values**. `U = [1.0, 0.0, 0.0]`
   is not the KCS Fr=0.26 velocity (2.1962 m/s). The skeleton accelerates
   *dict-shape typing*, not *physics defaulting*. Engineers MUST visit
   `inlet.fields.U` post-apply.

2. **Multi-family generalisation**. Cycle 1 is ship_vof only. Other
   case families surface the gap with no skeleton → fall back to the
   "Edit" CTA (graceful degradation). Cycles 2-5 extend.

3. **Failure-path UX**. Engineer applies the skeleton, decides one
   patch is wrong, edits it manually — the rail's response to that
   compound state is M3.1 cycle X (failure-path ergonomics from M3.0
   backlog).

4. **Visual diff preview**. Right now the engineer sees the CTA, clicks
   it, and the dict appears in the manifest. No "here's what will be
   written before you commit" preview. M3.1 cycle 2+ scope.

---

## Bottom line

The first form helper is live. Engineers on a ship_vof case can now
construct boundary patches in one click instead of typing a nested
dict. The cycle-7 surrogate journey of 8 decide() calls remains the
same shape, but now the bc.patches step in that journey is no longer
a stub — it's the real UI affordance.

M3.1 cycle 2 should extend to one more family (recommend
`rans_steady_incompressible` since cycle 4's multiphysics dogfood
already exercises it) to prove the lookup pattern scales.
