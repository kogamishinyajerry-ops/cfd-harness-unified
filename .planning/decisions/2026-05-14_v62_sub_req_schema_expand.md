---
decision_id: DEC-V62-A-sub-REQ-SCHEMA-EXPAND
title: REQ-SCHEMA-EXPAND · AIReviewRequest exposes step_path + step_bbox + step_extents + interface_bodies + interface_specs
status: Accepted
parent_dec: V62-A-charter
phase: V62-A Tier 2 supplement · driven by M-STACK-TRACK-1 §8 + M-STACK-TRACK-2 architectural gap
notion_sync_status: synced 2026-05-14 (https://www.notion.so/360c68942bed8125a9c7e81145f2972c)
---

# DEC-V62-A-sub-REQ-SCHEMA-EXPAND · close HTTP-vs-Python advisor divergence

## Status

**Accepted 2026-05-14** — Tier 2 supplement that lights up
`unit_detector` and `virtual_interface_detector` (A2-v2) in the
`POST /api/ai-review` HTTP path. Pure route-layer plumbing: no
`assemble_stack` signature change, no advisor logic change. confidence:
high (path is well-trodden, scope strictly bounded to 5 Pydantic fields
+ auto-discovery + dataclass rehydration + 7 new tests). 25 prior
`test_ai_review_route.py` cases remain green.

## Goal

Close the divergence the two M-STACK-TRACK retros captured:

* **M-STACK-TRACK-1 §8** (case_011 v5b plate-fin compact-HX, steady-
  laminar-CHT-multi-stream) — Path A (HTTP `POST /api/ai-review`) ran 4
  advisors while Path B (direct `assemble_stack`) ran 5. The HTTP path
  was missing `unit_detector` entirely. Retro blind-spot #2 verbatim:
  > "AIReviewRequest body missing `step_path`/`step_bbox` field so
  > unit_detector route-stranded [echoes TRACK-2 gap]"
* **M-STACK-TRACK-2** (case_016 m219 cavity DES acoustic) — Same single
  architectural gap surfaced independently in a different numerics
  class:
  > "AIReviewRequest does not yet expose
  > interface_bodies/interface_specs/step_path so
  > D6/A2-v2/unit_detector are route-stranded for path B"

Two independent retros converging on the same root cause = real gap,
not a one-case artifact. The advisor stack's own `assemble_stack`
function already routes `step_path` → `unit_detector` (line 631) and
`interface_bodies` + `interface_specs` → `virtual_interface_detector`
(line 580). Only the **wire schema** prevented HTTP callers from
supplying these.

## Scope

### What this sub-DEC adds

To `ui/backend/routes/ai_review.py::AIReviewRequest`:

1. `step_path: Optional[str]` — CAD STEP file path. Passed through
   as-is (no open/write — V132 advisory-only).
2. `step_bbox: Optional[list[float]]` — six-tuple
   `[xmin, ymin, zmin, xmax, ymax, zmax]` (raw units). Converted to a
   scalar `step_bbox_max_extent_raw = max(dx, dy, dz)` before dispatch
   (assemble_stack's documented kwarg shape).
3. `step_extents: Optional[list[float]]` — list of per-body max bbox
   extents (raw units). Forwarded as `step_body_extents_raw` for
   airframe-class filtering inside `unit_detector`.
4. `interface_bodies: Optional[list[dict[str, Any]]]` — wire form of
   `BodyGeometry`. Each item carries `name`, `centroid: [x,y,z]`,
   `faces: [FaceGeometry-shaped dict, ...]`. Rehydrated to
   `dict[str, BodyGeometry]` (the mapping shape assemble_stack wants).
5. `interface_specs: Optional[list[dict[str, Any]]]` — wire form of
   `InterfaceSpec`. Each item carries `patch_name`, `mode`
   (`'shared'`|`'endcap'`), and optional `body_a/body_b/body/axis`.
   Rehydrated to `list[InterfaceSpec]`.

Plus the supporting plumbing:

* **Auto-discovery** (only when explicit kwarg absent and `case_dir`
  provided):
  * `step_path`: first `*.step`/`*.stp` under `<case_dir>` then
    `<case_dir>/cad/` (root before `cad/` so a top-level STEP wins).
  * `step_bbox` / `step_extents`: `<case_dir>/cad/bbox.json` (keys
    `bbox` and `extents`) or matching keys inside
    `<case_dir>/manifest.json`.
  * `interface_bodies` / `interface_specs`:
    `<case_dir>/interface_bodies.json` (list) /
    `<case_dir>/interface_specs.json` (list) or matching keys inside
    `<case_dir>/manifest.json`. Per-field "first hit wins"; per-field
    "missing artifact is silent skip" matches the existing V130
    discipline.
* **Rehydration helpers**: `_rehydrate_interface_bodies` /
  `_rehydrate_interface_specs` mirror the pattern already established
  by `_rehydrate_thin_wall_inputs` (Codex R0 P2 verbatim precedent —
  malformed dataclass inputs would otherwise crash inside the advisor
  and be silently lost to `assemble_stack`'s per-call isolation). Both
  raise `HTTPException(400)` with `failing_check` discriminator on
  bad shape, matching the existing route's error contract.

### Routing-rule-impact

| Field added                                  | Gated advisor              | Previously route-stranded? |
|----------------------------------------------|----------------------------|----------------------------|
| `step_path`                                  | `unit_detector`            | YES (TRACK-1 + TRACK-2)    |
| `step_bbox` → `step_bbox_max_extent_raw`     | `unit_detector` (refines)  | YES (couldn't tune via HTTP) |
| `step_extents` → `step_body_extents_raw`     | `unit_detector` (refines)  | YES                        |
| `interface_bodies` + `interface_specs` (pair)| `virtual_interface_detector` (A2-v2) | YES (TRACK-2)    |

After this sub-DEC, an HTTP caller supplying the right combination of
fields reaches **5+ advisors** in the same dispatch — closing the
Path A vs Path B count gap surfaced by both M-STACK-TRACK retros.

### What this sub-DEC explicitly does NOT do

* **Does not wire D6 (`extra_body_advisor`) into assemble_stack.** D6
  was promoted in M-D6-PROMOTE (`f6d5c72`) but its routing
  (`check_extra_bodies_in_fluid(parts_manifest, stl_bbox_set)`) is not
  yet registered inside `assemble_stack`. That gap requires a separate
  follow-up sub-DEC because:
  (a) D6 takes a different signature pair (`stl_bbox_set`, not
      `interface_bodies`) — orthogonal field set;
  (b) `stl_bbox_set` is computed-from-disk rather than
      caller-supplied — its discovery + computation policy is a
      design decision worth its own DEC;
  (c) Anti-scope per task brief: "不要做 D6 + A2-v2 + unit_detector
      内部逻辑变更". Keeping D6 out preserves a single-axis sub-DEC.
* **Does not change `advisor_stack.py`.** assemble_stack signature is
  unchanged — the kwargs all already existed
  (`step_path` / `step_bbox_max_extent_raw` /
  `step_body_extents_raw` / `interface_bodies` / `interface_specs`).
* **Does not touch `ai_diagnose.py`.** That route has its own sub-DEC
  scope.

## Backward-compat evidence

All 25 prior `test_ai_review_route.py` cases pass unchanged — no
existing payload shape is altered. New fields default to `None`. The
auto-discovery hop only fires when `case_dir` is supplied AND the
explicit kwarg is `None`, so legacy callers see identical behavior.

```
PYTHONPATH=. uv run pytest ui/backend/tests/test_ai_review_route.py -q
32 passed in 0.55s
  ↑ 25 prior + 7 new
```

The 7 new tests:

1. `test_step_path_routes_to_unit_detector` — explicit `step_path` →
   `unit_detector` in `advisor_calls`.
2. `test_interface_bodies_routes_to_a2v2_virtual_interface_detector`
   — explicit body+spec pair → `virtual_interface_detector` in
   `advisor_calls` with `status=ok`.
3. `test_auto_discover_step_path_from_case_dir` — STEP under
   `<case_dir>/cad/` discovered and surfaced in
   `input_summary`.
4. `test_auto_discover_interface_bodies_from_manifest` —
   `manifest.json` carrying both fields lights up A2-v2.
5. `test_explicit_step_and_interface_override_auto_discover` —
   explicit values WIN over disk-discovered values for both STEP path
   and body set.
6. `test_malformed_step_bbox_returns_400` — wrong-arity bbox →
   actionable 400 (not 500).
7. `test_malformed_interface_body_returns_400` — body missing required
   `centroid`/`faces` → actionable 400.

## Surface scan (per DEC-V61-088)

* **ROADMAP scan**: maps cleanly to V62-A Tier 2 supplement (the two
  Tier 2 stack-level Track C retros explicitly call for this).
* **Existing-implementation grep**:
  `grep -rin "step_path|interface_bodies" ui/backend/routes/` →
  zero pre-existing hits under `routes/` (the field set was net-new
  on the wire). `grep` inside `services/advisor_stack.py` confirmed
  kwargs already supported (lines 517–527 + dispatch at lines
  580–648). `scripts/stack_track_c_session_1/run_http_path.py:45-47`
  carried a comment explicitly noting the gap this sub-DEC closes:
  > "Note: AIReviewRequest does NOT accept step_path / step_bbox"
* **Disposition**: extend (route plumbing only) — single new schema
  field cluster on an existing top-level route file. **Surface-scan
  trailer**: `Surface-scan: clean (no pre-existing wire-form schema
  for these 5 fields in route layer)`.

## v2.3 compliance

* **scope**: 3 shared code paths (route schema + tests + sub-DEC
  doc) — sub-DEC scope, not charter. ✓
* **DEC frontmatter**: 6 required fields present
  (`decision_id` / `title` / `status` / `parent_dec` / `phase` /
  `notion_sync_status`). ✓
* **Codex review**: not required. Per v2.3 1-sync-trigger, only
  security-boundary changes (auth / signing / authorization) trigger
  pre-merge Codex review. This sub-DEC is wire-schema plumbing on an
  already-loopback-guarded route; no security boundary touched. The
  route already inherits `require_loopback` + thin-wall rehydration
  precedent — adding 5 more rehydration paths follows the same
  pattern. Opus 4.7 self-judgment: confidence high.
* **Kogami**: not invoked. v2.3 governance is opt-in only; this is
  scoped sub-DEC plumbing, not a charter / governance-rule / strategic
  pivot.
* **confidence: high** — justified by: (a) all 5 fields' downstream
  routing already exists and is exercised by Python-path tests;
  (b) wire schema follows the verbatim precedent
  `_rehydrate_thin_wall_inputs` set last week (Codex R0 P2); (c)
  ~30 LOC of net new logic + ~125 LOC of helpers, all bounded by
  the dispatch checkpoint; (d) 32/32 route tests including the 7
  new ones pass on first compile.

## How to apply (for future readers)

If a future advisor needs additional wire-form input that
`assemble_stack` already routes:

1. Add `Optional[...]` field to `AIReviewRequest`.
2. If the field is auto-discoverable from `case_dir`, extend
   `_autodiscover*` helpers (use first-hit-wins + silent-skip).
3. If the wire shape differs from the dataclass `assemble_stack`
   wants, add a `_rehydrate_*` helper raising `HTTPException(400)`
   on malformed input. Mirror `_rehydrate_thin_wall_inputs` /
   `_rehydrate_interface_bodies` / `_rehydrate_interface_specs`.
4. Plumb the new field through the explicit_kwargs dict and
   transform-before-dispatch block.
5. Add ≥1 positive routing test + ≥1 negative shape test.
6. Pop wire-only kwargs (e.g. `step_bbox` → mapped scalar) before
   the `assemble_stack(**stack_kwargs)` call so they don't reach the
   advisor signature as unknown kwargs.

If a future field needs `assemble_stack` routing that does NOT exist
(D6 is the current canonical example), a separate sub-DEC covering
both the routing wire-up AND the schema field is required.
