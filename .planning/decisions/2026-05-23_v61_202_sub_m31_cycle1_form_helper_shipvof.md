---
decision_id: DEC-V61-202-SUB-M31-CYCLE1-FORM-HELPER-SHIPVOF
title: M3.1 cycle 1 — domain-aware form helper · ship_vof bc.patches skeleton
status: Proposed
proposed_date: 2026-05-23
parent_dec: DEC-V61-202-WORKBENCH-DYNAMIC-GUIDED
phase: M3.1 cycle 1 (form helpers, ship_vof entry)
notion_sync_status: pending_accepted
autonomous_governance: true
counter_status: v6.1 telemetry
charter_class: false
scope_class: sub_dec
ssot: .planning/workbench/GUIDED_CASE_CONSTRUCTION_FLOW.md
predecessors:
  - DEC-V61-202-SUB-M30-CYCLE7-BEGINNER-TEST  # cycle-7 surrogate showed bc.patches needed UI affordance
  - DEC-V61-202-SUB-M30-CYCLE6-PROVENANCE-AUDIT-V2  # audit log will record skeleton-apply decisions
---

## Why

Cycle 7's beginner-test surrogate landed `bc.patches` by synthesizing a
canonical 3-patch ship_vof skeleton client-side — a stand-in for the UI
form helper that doesn't exist yet. Real engineers at the workbench
have no such affordance: when the rail says "fill `bc.patches`", they
either type a multi-key nested dict from memory or hunt through other
cases for templates. Both paths violate the M3.0 "engine drives
monotonic forward progress" promise.

M3.1 cycle 1 adds the missing affordance: when the rail surfaces a
gap on a structural dict field (like `bc.patches`) for a known
case_family (start with `ship_vof`), it offers a one-click
"Apply skeleton" CTA alongside the existing "Apply" / "Edit" CTAs.
The skeleton mirrors cycle 7's synthesized payload (inlet:fixedValue
+ outlet:zeroGradient + wall:noSlip), so the surrogate becomes a real
engineer affordance — not just test scaffolding.

Scope is **deliberately one case_family + one field** so:
- The DEC stays sub-DEC sized (~150 LOC across 6 files)
- We measure whether the skeleton design actually helps before
  generalizing to RANS / LES / compressible / CHT (cycle 2-5 scope)
- Failure-path ergonomics (what happens when engineer applies skeleton
  then wants to edit one patch's U vector) get exercised once
  before fanning out

## What

### In scope

1. **Schema** — add `suggested_skeleton: dict | None` to:
   - `ui/backend/schemas/workbench_frame.py::RailPrimary`
   - `ui/backend/services/case_completeness/schemas.py::MissingField`

   Parallel to existing `suggested_default: Any | None`. Distinct field
   (option A from surface scan) because suggested_default semantics
   are scalar; skeletons are structural dicts and the frontend renders
   them differently.

2. **Decide layer** — `ui/backend/services/workbench_decide.py`:
   - `_rail_from_gap` now forwards `gap.get("suggested_skeleton")`
     onto the RailPrimary. CTA label resolves as:
     `suggested_default → "填入 / Apply"` ; else
     `suggested_skeleton → "应用骨架 / Apply skeleton"` ; else
     `"编辑 / Edit"`.
   - **New helper** `_skeleton_for_gap(gap, state) → dict | None`:
     looks at `gap.field_path` + `state.manifest.get("case_family")`
     and returns the canonical skeleton when a match is registered.
     Cycle 1 registers exactly one entry: `(field_path="bc.patches",
     case_family="ship_vof")` → 3-patch dict below. Skeletons are
     attached to the gap dict in `_gaps_for_step` before
     `_rail_from_gap` runs, so the rail builder stays oblivious to
     family-specific logic.

   Canonical ship_vof bc.patches skeleton:
   ```python
   {
       "inlet":  {"patch_type": "fixedValue",   "fields": {"U": [1.0, 0.0, 0.0]}},
       "outlet": {"patch_type": "zeroGradient", "fields": {"p": "zeroGradient"}},
       "wall":   {"patch_type": "noSlip",       "fields": {}},
   }
   ```
   The U vector is a placeholder the engineer overrides post-apply.

   **Why decide layer not analyzer**: `CaseManifest` Pydantic schema
   doesn't declare `case_family` (no `extra="allow"` at top level), so
   the analyzer can't read it without a schema change. The decide layer
   has access to `state.manifest` (raw dict). Long-term, `case_family`
   should join CaseManifest as a typed field (M3.1 cycle 2+ scope).

4. **Frontend** —
   `ui/frontend/src/pages/workbench/step_panel_shell/dynamic_frame/DynamicFramePanel.tsx`:
   render a second CTA button when `rail.suggested_skeleton` is
   non-null. Reuses the existing `patch.mutate()` flow with the
   skeleton payload as `value`. Amber styling distinguishes it from
   the primary blue "Apply" button (skeleton is a bigger commit).

5. **Frontend type** —
   `ui/frontend/src/types/workbench_frame.ts`:
   add `suggested_skeleton?: Record<string, unknown> | null` on
   RailPrimary.

6. **Tests**:
   - `ui/backend/tests/test_workbench_frame.py` — `_rail_from_gap`
     with `suggested_skeleton` populated → RailPrimary carries it
   - `ui/backend/tests/test_workbench_frame_cycle2.py` —
     end-to-end PATCH with skeleton payload validates against
     BCSection.patches schema cleanly
   - `ui/frontend/src/pages/workbench/step_panel_shell/dynamic_frame/__tests__/DynamicFramePanel.test.tsx`:
     · skeleton button renders when suggested_skeleton present
     · skeleton button disabled without caseId / manifestStateSha
     · click triggers patch.mutate with skeleton value
     · skeleton + scalar CTA can coexist (both buttons render
       when both fields populated)

7. **Dogfood** — `scripts/dogfood/case_007_cycle1_form_helper.py`:
   stage a sparse ship_vof manifest, hit GET frame at step 4, assert
   `rail.suggested_skeleton` is the canonical 3-patch shape, PATCH it,
   verify `bc.patches` lands with 3 entries.

### In scope (expanded post Codex R2 P1 · user-ratified)

- **case_family persistence in CaseManifest Pydantic schema** —
  `case_family: str | None = None` added as a top-level field. Manifest
  read/write round-trips it cleanly.

- **case_family gap surfaced by case_completeness** — when
  `_analyze_imported` encounters a manifest without `case_family`, it
  emits a `MissingField` with severity `warning`. Routed to step 1 via
  `_STEP_PATH_PREFIXES[1]` so engineers are prompted early.

- **PATCH-able case_family** — the existing `PATCH /api/cases/{id}/manifest`
  endpoint accepts `field_path: "case_family"` because (a) the path
  parser handles top-level fields and (b) the JSON schema already
  declared case_family (validation passes).

### Out of scope (M3.1 later cycles)

- **UI labeling form for case_family** (Codex R4 P1 honest acknowledgement):
  cycle 1 has no inline edit affordance on the rail for top-level scalar
  string fields. The case_family gap surfaces on the rail with an
  "编辑 / Edit" cta_label, but the button is disabled because the gap
  carries no `suggested_default`. Engineers today PATCH `case_family`
  via the API directly (what tests + dogfood do) or by YAML edit. **M3.1
  cycle 2 will add an inline text/enum input** in DynamicFramePanel
  that activates when the gap has no `suggested_default` + no
  `suggested_skeleton` — generic affordance for any top-level scalar
  field, with case_family as the first user-facing surface.
- **Persisting case_family at import time** — `case_scaffold/manifest_writer.py`
  still doesn't write case_family. M3.1 cycle 2 will add it as an
  optional param so the ingest path can pre-fill when known.
- **More (field_path, case_family) registry entries** —
  RANS / LES / compressible / CHT — cycles 2-5
- Other structural fields (`physics.fvSolution`, `mesh_contract.regions`)
- Failure-path: engineer applies skeleton, then wants to override one
  patch — that's a "compose / merge" UX question, scoped to M3.1 cycle X
- Skeleton versioning (different ship-VOF skeletons for ITTC vs NMRI
  validation cases)
- Visual diff preview before apply

## Closure criteria

- [ ] Schema + analyzer + decide + frontend + types + tests implemented
- [ ] `scripts/dogfood/case_007_cycle1_form_helper.py` 4+ checks PASS
- [ ] DOGFOOD report `.planning/dogfood/DOGFOOD_M31_CYCLE1_FORM_HELPER.md`
- [ ] Codex review ≤ 3 rounds (v2.3 cap)
- [ ] DEC Proposed → Accepted
- [ ] Notion sync (session-end, Accepted DECs only)

## Risks + mitigations

| Risk | Mitigation |
|---|---|
| Skeleton placeholder U vector confuses engineers (they don't know it's a stub) | Frontend renders skeleton-applied fields with a "review needed" badge until engineer touches them; M3.1 cycle 2 |
| `case_family` not actually populated on all imports | Cycle 1 fail-soft: if case_family missing, no skeleton offered, fall back to scalar "Apply" / "Edit" CTA. Tests cover the missing-case_family path |
| Form helpers become a parallel manifest-construction track that diverges from manual edits | Skeleton apply uses the same `PATCH /manifest` endpoint as manual edits; nothing bypasses validation |
| `bc.patches` schema evolves (e.g. adds new required field) → skeleton becomes stale | Skeleton lives in the analyzer; same place that knows the schema rules. Co-located so they evolve together |

## Provenance

- Charter: DEC-V61-202-WORKBENCH-DYNAMIC-GUIDED
- SSOT: `.planning/workbench/GUIDED_CASE_CONSTRUCTION_FLOW.md`
- M3.0 retro (`.planning/retrospectives/2026-05-23_m30_milestone_close.md`)
  recommended "domain-aware form helpers" as the engine-side M3.1 win
- Cycle 7 surrogate proved the affordance shape works (synthesized
  client-side); cycle 1 makes it a real UI feature
- User authorization 2026-05-23: "我批准你的多agent团队持续工作，奔着里程碑继续"

Surface-scan-found: `ui/backend/schemas/workbench_frame.py::RailPrimary` ·
disposition: extend (add suggested_skeleton field next to suggested_default);
no parallel-new component, no rename, no break.
