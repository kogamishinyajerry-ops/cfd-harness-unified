# DOGFOOD · M3.1 Cycle 1 · ship_vof form-helper skeleton

**DEC**: `2026-05-23_v61_202_sub_m31_cycle1_form_helper_shipvof.md` (Proposed)
**Date**: 2026-05-23
**Dogfood script**: `scripts/dogfood/case_007_cycle1_form_helper.py`
**Verdict**: **PASS** (7/7 checks · post Codex R0+R1 verbatim fixes)
**Codex**: R0 = 1 P1 + 1 P2 → R1 = 1 P1 → R2 = APPROVE (3 reviews,
under v2.3 cap=3). Closure: explicit case_family required (M3.1
cycle 2 will persist it); cta_label=null when only skeleton.

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

## Codex closure (3 rounds · 2 P1 + 1 P2 · under v2.3 cap=3)

**R0** (1 P1 + 1 P2):
- **P1 · case_family not persisted**: M5 `case_scaffold/manifest_writer.py`
  writes source/origin/created_at but not `case_family`. Real imported
  cases never carry it, so the lookup returned None for every case in
  production — feature only worked with hand-injected test data.
  **R0 fix attempted**: added solver-based inference fallback
  (`physics.solver == "interFoam"` → ship_vof). **R1 caught this fix**:
  see R1 below.
- **P2 · duplicate "Apply skeleton" buttons**: when only a skeleton
  was offered, the backend set `cta_label = "应用骨架 / Apply skeleton"`
  on the primary CTA, but the primary's `canApply` evaluator needs
  `suggested_default` (null on skeleton-only rail), so the primary
  rendered disabled while the secondary skeleton CTA rendered live —
  two identical buttons, one dead. **Fixed** (still holds): backend
  sets `cta_label = null` when only skeleton; frontend renders only
  the secondary skeleton button.

**R1** (1 P1):
- **P1 · solver-inference misclassifies non-ship interFoam cases**:
  Codex R1 caught that the R0 inference traded "missing helper" for
  "wrong helper". interFoam is a generic VOF solver — sloshing tanks,
  dam breaks, multiphase pipes also use it, with very different BC
  topology (closed-domain walls only, atmosphere top, etc.). Inferring
  ship_vof from solver alone would let a user PATCH the ship-specific
  inlet/outlet/wall skeleton onto a sloshing-tank case → wrong manifest.
  **R2 fix** (verbatim · revert + scope clarification): removed the
  solver-based inference path. Cycle 1 now requires EXPLICIT
  `case_family` on the manifest. The scope of "real production
  activation" defers to M3.1 cycle 2 (case_family persistence + UI
  labeling).

**R2** (CRS APPROVE — no further findings).

Regression tests:
- `test_decide_attaches_ship_vof_bc_patches_skeleton_on_step4` (R0)
- `test_decide_no_skeleton_inference_from_solver_alone` (R1 — pins the
  no-inference contract: interFoam without explicit case_family
  produces NO skeleton)
- `test_decide_no_skeleton_when_case_family_unknown` (R0 strengthened)
- `test_decide_skeleton_does_not_clobber_existing_suggested_default` (R0)
- Frontend: `does NOT render primary CTA when only skeleton is offered`

## Cycle 1 honest scope (post R0-R1-R2)

Cycle 1 ships **the engine** for domain-aware form helpers, gated on
explicit `case_family` declaration. The skeleton fires when:
- Whitelist cases that declare `case_family: ship_vof` in their YAML
- Tests / dogfoods that hand-set the field

The skeleton does **NOT** fire for normal imported cases today, because
the M5 scaffold doesn't persist `case_family`. **M3.1 cycle 2 closes
that gap** by (a) adding `case_family` to `manifest_writer.py`, (b)
adding a UI label form during import / case-editor, and (c) registering
more (field_path, case_family) entries (RANS / LES / compressible / CHT).

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

Manifest used in dogfood explicitly declares `case_family: ship_vof`.
A real imported case (without case_family in its manifest) does NOT
get the skeleton — that's M3.1 cycle 2 scope.

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
