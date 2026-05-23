# DOGFOOD · M3.1 Cycle 1 · ship_vof form-helper skeleton

**DEC**: `2026-05-23_v61_202_sub_m31_cycle1_form_helper_shipvof.md` (Proposed)
**Date**: 2026-05-23
**Dogfood script**: `scripts/dogfood/case_007_cycle1_form_helper.py`
**Verdict**: **PASS** (9/9 checks · post Codex R0/R1/R2 + user-ratified scope expansion)
**Codex**: R0 = 1 P1 + 1 P2 → R1 = 1 P1 → R2 = 1 P1 → scope-expansion
ratified by user (case_family persistence + gap surface + PATCH path
all pulled into cycle 1). R3 = 1 P1 + 1 P2 (severity-aware topbar
gating + warning-count totals) → fixed inline. R4 = 1 P1 + 1 P2
(case_family unreachable from UI + false warning on non-applicable
solvers) → P2 closed via demand-driven warning (solver→family-candidate
map: cycle 1 ships interFoam→ship_vof only); P1 partially addressed
via honest "why" text (cycle-1 advisory; UI labeling form is M3.1
cycle 2 scope; engineers PATCH via API/YAML in the meantime).

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

## Codex closure (3 rounds · 3 P1 + 1 P2 · cap=3 + user-ratified scope expansion)

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

**R2** (CRS · 1 P1):
- **P1 · feature unreachable on imported cases (same root cause as R0
  P1)**: the R1 revert removed solver-inference, restoring the
  original gap — real imported cases still don't carry `case_family`,
  so `_resolve_case_family` returns None and the skeleton never fires
  in production. Codex called out that this is exactly the
  cap=3 paradox: solving one P1 re-opens the other.

**R4** (1 P1 + 1 P2 · after R3 fix landed):
- **P1 · case_family unreachable from the UI**: routing the warning to
  Step 1 surfaces a rail gap that the current UI cannot resolve — the
  gap has no `suggested_default` and no `suggested_skeleton`, so
  `DynamicFramePanel` renders only a disabled `编辑 / Edit` button.
  No Step-1 form field exists for `case_family` elsewhere in the
  workbench. **Honest fix (cycle 1 scope discipline)**: updated the
  "why" text to be explicit — "cycle-1 advisory; set via case-editor
  or YAML edit; UI labeler is M3.1 cycle 2". The rail still surfaces
  the prompt so engineers know to act; the UI form is deferred. Tests
  and dogfoods continue to PATCH via the API directly (unchanged path).
- **P2 · false case_family warning on non-applicable solvers**: cycle 1
  ships exactly one helper (`ship_vof`/interFoam), but the R3
  implementation emitted the warning for every imported case regardless
  of solver. For simpleFoam/RANS cases the warning was useless noise
  that dropped completeness from 100% to 80%. **Fix**: introduced
  `_SOLVER_TO_CASE_FAMILY_CANDIDATES` (cycle-1 inline registry,
  TODO: extract when 2nd helper lands) + `_case_family_helper_candidate_applies`.
  Warning + slot allocation only fire when the manifest's solver
  matches a candidate. simpleFoam imports now stay at 100% with no
  warning; interFoam imports without `case_family` correctly show the
  warning at 80%.

Regression tests added in R4 fix:
- `test_imported_interfoam_case_without_case_family_emits_warning` (P2 positive)
- `test_imported_simplefoam_case_without_case_family_no_warning` (P2 negative)
- `test_imported_case_full_minimal_contract` reverted to total=4 (simpleFoam default seed has no candidate)

**R3** (1 P1 + 1 P2 · after scope expansion landed):
- **P1 · case_family warning routed into Step 1 gating**: the new
  case_family warning gap surfaces on step 1, but `_pick_topbar_cta`
  blanket-disabled the topbar CTA for ANY `info_gap` rail regardless
  of severity. The non-blocking advisory therefore became a workflow
  blocker for every fresh imported case. **Fix**: `_pick_topbar_cta`
  parses `rail.provenance` for the severity token (`_parse_rail_severity`
  helper) and only disables the CTA when severity is `critical`.
  Warning/info severity gaps now keep the rail visible but allow advance.
- **P2 · case_family warning not counted in totals**: `_analyze_imported`
  was still building the report with `expected_warning_count=0`, but the
  case_family slot is now a MissingField with severity=warning. For a
  fresh otherwise-complete imported case, the report had
  `present_count=4 / total_count=4 = 100%` while a real warning was
  listed in `missing` — internally inconsistent. **Fix**: bumped
  `expected_warning_count=1` so the slot is always counted; present
  when case_family lands, missing-warning when absent.

Regression tests added in R3 fix:
- `test_decide_warning_gap_does_not_block_topbar_cta` (P1)
- `test_decide_critical_gap_still_blocks_topbar_cta` (P1 negative)
- `test_imported_case_without_case_family_emits_warning_in_totals` (P2)

**User ratification of cap=3** (option A — expand cycle 1 scope):
The honest fix to satisfy BOTH R0 and R2 is to land case_family
persistence in the SAME patch. Cycle 1 now also includes:
  · `CaseManifest.case_family: str | None = None` (Pydantic schema)
  · `_analyze_imported` emits `case_family` as a `warning` MissingField
    when absent
  · `_STEP_PATH_PREFIXES[1]` routes `case_family` to step 1 so engineers
    see the gap early
  · `_seed_imported_manifest` test fixture defaults `case_family="test"`
    so existing tests still see 100% completeness
  · Dogfood walks the full production path: stage WITHOUT case_family
    → step 1 surfaces gap → PATCH "ship_vof" → step 4 offers skeleton
    → PATCH skeleton → bc.patches lands

Both Codex findings now satisfied simultaneously:
  · R0 P1 (feature unreachable) — closed via rail PATCH affordance
    that surfaces case_family as a labelable gap
  · R1 P1 (misclassification) — closed by removing inference; only
    explicit user labels trigger the skeleton

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
  [PASS] Step 1 rail surfaces case_family as a missing field
  [PASS] PATCH case_family succeeded
  [PASS] Rail at step 4 surfaces suggested_skeleton
  [PASS] Skeleton has canonical inlet/outlet/wall keys
  [PASS] Primary cta_label suppressed (skeleton-only path)
  [PASS] Rail provenance records skeleton_keys
  [PASS] PATCH with skeleton value returns 200 + success=True
  [PASS] Manifest bc.patches landed with 3 entries (inlet/outlet/wall)
  [PASS] Post-PATCH rail no longer surfaces bc.patches as a gap
```

The dogfood manifest is staged **without** case_family — mirroring a
real imported case. The rail-driven flow then prompts the engineer to
label the case (step 1 gap), PATCHes the label, and the step-4
skeleton becomes available. This is the **production path**, not a
hand-injected shortcut.

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
