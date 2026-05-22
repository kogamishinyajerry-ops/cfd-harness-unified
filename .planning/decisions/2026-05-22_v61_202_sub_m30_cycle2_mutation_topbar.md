---
decision_id: DEC-V61-202-SUB-M30-CYCLE2-MUTATION-TOPBAR
title: M3.0 cycle 2 — manifest field-path PATCH + topbar_cta slot + rail CTA wired
status: Accepted
proposed_date: 2026-05-22
accepted_date: 2026-05-22
parent_dec: DEC-V61-202-WORKBENCH-DYNAMIC-GUIDED
phase: M3.0 cycle 2 (mutation + 4th slot)
notion_sync_status: pending
autonomous_governance: true
counter_status: v6.1 telemetry
charter_class: false
scope_class: sub_dec
ssot: .planning/workbench/GUIDED_CASE_CONSTRUCTION_FLOW.md
predecessors:
  - DEC-V61-202-SUB-M30-CYCLE1-DECIDE-STATE (Accepted 2026-05-22 · the display layer)
codex_review:
  r0_commit: 524d40b
  r0_relay: crs (effort=high)
  r0_verdict: CHANGES_REQUIRED (2 P1 + 1 P2)
  r0_findings:
    - "P1-1: SHA-check + write not atomic (race condition under concurrent PATCH)"
    - "P1-2: case_manifest.schema applied to whitelist/draft cases that have different shapes"
    - "P2: type errors leaked across paths, blocking unrelated PATCHes"
  r1_commit: 8ce2e1b
  r1_verdict: APPROVED (verbatim Codex P1+P2 fix per v2.3 verbatim exception)
---

## Why

Cycle 1 landed the display layer (3 dynamic slots reading from `decide()`),
but rail CTAs are dead — engineers see what's blocking but can't act. Per
SSOT §3 driver 3 ("just-in-time, one field per ask when constraints
unresolved"), the workbench needs a **field-path PATCH surface** so each
CTA targets exactly the manifest path the rail card displays. This
closes the observation → action → state-change loop.

Cycle 1 also wired only 3 of 4 driver-slots. SSOT §4 names topbar CTA as
the 4th slot; cycle 1 deferred. This cycle lands it.

## What

### In scope

**Backend** (~350 LOC + tests):

1. `ui/backend/schemas/workbench_frame.py` (extend):
   - `TopbarCta` model: `{label: str, kind: Literal["next_step", "re_audit", "submit_solve", "step_default"], target_step: int | None, enabled: bool, reason: str | None}`
   - Add `topbar_cta: TopbarCta` to `WorkbenchFrame`

2. `ui/backend/services/workbench_decide.py` (extend):
   - `_pick_topbar_cta(state)`: returns CTA based on rail kind +
     step number:
     - `problem_fix` → "复检 / Re-audit" (re-run audit gate)
     - `info_gap` (critical) → CTA disabled, reason = "先补齐 X 才能进入下一步"
     - `step_default` + step < 5 → "下一步 / Next step" (target_step = step+1)
     - `step_default` + step == 5 → "提交求解 / Submit solve"

3. `ui/backend/schemas/manifest_patch.py` (new):
   - `ManifestPatchRequest`: `{field_path: str, value: JsonValue,
     expected_state_sha: str}`
   - `ManifestPatchResponse`: `{success: bool, new_state_sha: str,
     applied_path: str, validation_errors: list[str]}`

4. `ui/backend/services/manifest_patch.py` (new):
   - `apply_field_path_patch(case_id, request)` — pure-ish function:
     - Load current manifest (imported / draft / whitelist resolver)
     - Compute current state_sha; reject if doesn't match
       `expected_state_sha` (optimistic concurrency)
     - Parse `field_path` (dot-separated, JSON-Pointer-like) into a
       sequence of dict/list traversals, applying value at the leaf
     - Validate result against `case_manifest.schema.json`
     - Write back (imported case YAML / draft YAML; whitelist forks to draft)
     - Recompute new state_sha + return
   - Whitelist cases get **forked to a draft on first write** —
     the engineer's edit creates `user_drafts/{case_id}.yaml` from the
     whitelist entry. Subsequent PATCHes hit the draft, not the
     immutable catalog.

5. `ui/backend/routes/workbench_frame.py` (extend):
   - `PATCH /api/cases/{case_id}/manifest`
   - 200 + ManifestPatchResponse on success
   - 409 on state_sha mismatch (concurrency conflict)
   - 422 on schema validation failure
   - 404 on case not found

**Frontend** (~250 LOC + tests):

1. `ui/frontend/src/types/workbench_frame.ts` (extend): TS mirror of TopbarCta
2. `ui/frontend/src/types/manifest_patch.ts` (new): TS mirror of patch req/resp
3. `ui/frontend/src/pages/workbench/step_panel_shell/dynamic_frame/useManifestPatch.ts`:
   React Query mutation hook; on success invalidates the
   `["workbench-frame", caseId, ...]` query so the next frame is
   re-fetched with the new state.
4. `ui/frontend/src/pages/workbench/step_panel_shell/dynamic_frame/DynamicTopbarCta.tsx`:
   pill rendered in TopBar; kind-driven color (next_step = sky, re_audit =
   amber, submit_solve = emerald, disabled = gray); tooltip shows reason
   when disabled.
5. `DynamicFramePanel.tsx` (extend): wire `cta_label` button to
   `useManifestPatch` mutation when `rail.field_path` + `rail.suggested_default`
   both present.
6. `StepPanelShell.tsx` (extend): render `DynamicTopbarCta` inside TopBar
   when `dynamicFrameEnabled`.

**Dogfood**:
- `scripts/dogfood/case_007_dogfood.py` (extend) or new
  `case_007_cycle2_closed_loop.py`: simulate stage-1 case (no phases) →
  call PATCH endpoint with `vof_contract.phases = [water, air]` → fetch
  next frame → verify Step 3 rail flipped from `info_gap` to
  `step_default` and Step 4 still surfaces `p_rgh` problem (proving
  partial-progress feedback works).

### Out of scope (defer)

- Spatial 3D viewport overlays (deferred to cycle 3)
- focus_patch click handler in vtk.js (cycle 3)
- Multi-physics horizontal dogfood (cycle 4)
- Real browser e2e via Playwright (cycle 5)
- Feature flag `?dynamic_frame=1` default-on (cycle 5)
- LLM-backed "explain this field" tooltips (V130 advisor; cycle 6+ if at all)

## Field-path semantics

`field_path` is dot-separated, like JSON Pointer but human-readable:
- `bc_contract.inlet.velocity.type` → manifest["bc_contract"]["inlet"]["velocity"]["type"]
- `vof_contract.phases` → manifest["vof_contract"]["phases"] (list-valued OK)
- `mesh_contract.y_plus_target.max` → numeric leaf

List indices use `[N]` suffix: `bc_contract.patches[0].name`. Cycle 2
supports dict-only leafs to keep scope; list index PATCH lands in cycle 2.5
if needed.

## State_sha optimistic concurrency

Workflow:
1. Frontend reads frame → `state_sha = "abc123..."`
2. Engineer clicks CTA → PATCH with `expected_state_sha: "abc123..."`
3. Backend computes current state_sha:
   - Match → apply patch + return new_state_sha
   - Mismatch → 409 with current state_sha + applied_path = ""
4. On 409, frontend re-fetches frame and retries (or surfaces conflict)

This protects against:
- Two browser tabs editing same case (one wins, the other gets 409)
- Stale frame after another route mutated the case
- Race between PATCH and frame refetch

## Closure criteria

- [x] Backend schemas + service + route landed (`524d40b`, `8ce2e1b`)
- [x] Backend tests: 24 passing (4 topbar + 3 manifest_state_sha + 7 PATCH service + 5 route + 4 Codex R0 R1 regressions + 1 unset)
- [x] Frontend hook + component + wiring landed (`d4f… frontend commit`)
- [x] Frontend tests: 9 passing (6 DynamicTopbarCta + 3 useManifestPatch)
- [x] Closed-loop dogfood passing on case_007: 8/8 checks PASS — rail CTA → PATCH → next frame mutation observed; partial-progress preserved
- [x] Codex R0 (CRS, effort=high) CHANGES_REQUIRED with 2 P1 + 1 P2; R1 verbatim Codex fix → APPROVED in 1 round (round cap=3 used 1)
- [x] DEC Proposed → Accepted (this commit)
- [ ] Notion sync (session-end batch)

## Risks + mitigations

| Risk | Mitigation |
|---|---|
| field_path parser security (`__class__.__init__`-style injection) | Whitelist allowed top-level prefixes per case_manifest.schema.json + reject anything containing `__` |
| Whitelist case forking semantics — when does a draft get created? | First PATCH on whitelist case auto-forks to draft; explicit in DEC §What; tested explicitly |
| 409 conflict UX is bad | Frontend invalidates + refetches automatically on 409; engineer never sees raw 409 |
| Schema validation false-rejects valid partial states | jsonschema validate against schema with `additionalProperties: true` (already permissive); per-PATCH lenient check |
| Cycle scope creep | List-index PATCH (`[N]`) explicitly deferred to cycle 2.5 if dogfood needs it |

## Provenance

- Charter: DEC-V61-202-WORKBENCH-DYNAMIC-GUIDED (Accepted 2026-05-22)
- SSOT: `.planning/workbench/GUIDED_CASE_CONSTRUCTION_FLOW.md` §3 driver-3 + §4 4 slots
- Predecessor: DEC-V61-202-SUB-M30-CYCLE1-DECIDE-STATE (cycle 1 display layer)
- User scoping 2026-05-22: "按推荐继续" + "field-path PATCH 粒度（SSOT 对齐选择）"

Surface-scan-found: ui/backend/services/case_completeness/analyzer.py · disposition: extend (manifest_patch reuses the imported/draft/whitelist resolver chain established by cycle 1's _load_manifest, which itself extends case_completeness's chain)
