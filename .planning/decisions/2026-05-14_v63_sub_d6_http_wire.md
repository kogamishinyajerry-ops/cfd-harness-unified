---
decision_id: DEC-V63-A-sub-M-D6-HTTP-WIRE
title: M-D6-HTTP-WIRE · close REQ-SCHEMA-EXPAND deferred D6 wire-up by adding stl_bbox_set HTTP plumbing + auto-discover + assemble_stack routing rule
status: Accepted
parent_dec: DEC-V63-A-charter
phase: V63-A Tier 1 · M-D6-HTTP-WIRE (carry-over #4 from V62-A REQ-SCHEMA-EXPAND deferred scope)
notion_sync_status: pending
codex_review_relay: 86gs gpt-5.4 xhigh · pre-merge MANDATORY (routes/ai_review.py security boundary · v2.3 1-sync-trigger)
---

# DEC-V63-A-sub-M-D6-HTTP-WIRE · D6 extra_body_advisor HTTP wire-up

## Status

Accepted (2026-05-14). Implementation LANDED in B40 commit chain (see
"Implementation evidence" §). Closes V62-A REQ-SCHEMA-EXPAND scope-out
of D6 HTTP wire-up + V63-A carry-over #4. Single sub-DEC (3 shared code
paths: routes/ai_review.py + services/advisor_stack.py + tests for both)
— scope at sub-DEC boundary per v2.3 governance (DEC-V61-133).

## Goal

Make the LANDED `extra_body_advisor` (D6 · V55 case_016 10 mm debris
cube class) reachable over `POST /api/ai-review`. The advisor itself
landed in M-D6-PROMOTE (`f6d5c72`) and is fully tested at the module
level, but until this sub-DEC its `(parts_manifest, stl_bbox_set)`
signature had no HTTP path — engineers using the workbench could not
ask the stack about FOD-class extra bodies without dropping into Python.

### Verbatim upstream evidence (V62-A REQ-SCHEMA-EXPAND §"this sub-DEC explicitly does NOT do")

> * **Does not wire D6 (`extra_body_advisor`) into assemble_stack.** D6
>   was promoted in M-D6-PROMOTE (`f6d5c72`) but its routing
>   (`check_extra_bodies_in_fluid(parts_manifest, stl_bbox_set)`) is not
>   yet registered inside `assemble_stack`. That gap requires a separate
>   follow-up sub-DEC because:
>   (a) D6 takes a different signature pair (`stl_bbox_set`, not
>       `interface_bodies`) — orthogonal field set;
>   (b) `stl_bbox_set` is computed-from-disk rather than
>       caller-supplied — its discovery + computation policy is a
>       design decision worth its own DEC;
>   (c) Anti-scope per task brief: "不要做 D6 + A2-v2 + unit_detector
>       内部逻辑变更". Keeping D6 out preserves a single-axis sub-DEC.

This sub-DEC is the "separate follow-up sub-DEC" REQ-SCHEMA-EXPAND
deferred to. It maps directly to V63-A ARC-GOAL Tier 1 row
**M-D6-HTTP-WIRE** (carry-over #4).

## Scope

### What this sub-DEC adds

1. **`AIReviewRequest.stl_bbox_set`** (`Optional[dict[str, list[float]]]`)
   — JSON-friendly wire shape mapping body name → 6-element AABB
   `[xmin, ymin, zmin, xmax, ymax, zmax]` in millimetres. Pydantic
   enforces top-level dict shape (422 on non-dict); the D6 advisor's
   own `_coerce_bbox` drops malformed inner entries silently.
   `routes/ai_review.py:223-243`.

2. **Auto-discovery from `case_dir`** (two paths, first hit wins):
   - `<case_dir>/cad/stl_bbox_set.json` — dedicated file mirroring the
     existing `<case_dir>/cad/face_normals.json` (D11) precedent.
   - `<case_dir>/manifest.json` field `stl_bbox_set` — fallback when
     the dedicated file is absent.
   `routes/ai_review.py:760-781`.

3. **`assemble_stack(stl_bbox_set=...)` kwarg + routing rule**
   — D6 dispatches when `stl_bbox_set` is provided AND non-empty.
   `parts_manifest` is forwarded when present (D6 needs it to flag
   `body_in_fluid_region` and `undeclared_inclusion`); absent
   manifest still permits the `unregistered_body` detection path
   (every STL body becomes a critical finding).
   `services/advisor_stack.py:866-895`.

4. **`_normalize_extra_body` translator** — wraps D6's native
   `ExtraBodyFinding` into the stack's normalized `Finding` shape
   with `source_advisor="extra_body_advisor"`,
   `code=f"d6_{f.finding_type}"`, and `evidence_v_rows=("V55",)`.
   `services/advisor_stack.py:393-409`.

5. **`_V_ROWS_PER_ADVISOR["extra_body_advisor"] = ("V55",)`** —
   the canonical V-row attribution per TrustGate contract.
   `services/advisor_stack.py:180`.

### What this sub-DEC does NOT change

* **D6 advisor internals** — `extra_body_advisor.py` (391 LOC)
  unmodified. This is a pure wire-up.
* **Other advisors** — no signature change to A4/A5/A8/A10/D10/D11,
  `unit_detector`, `virtual_interface_detector`, or `thin_wall_advisor`.
* **`ai_diagnose.py`** — separate route with its own sub-DEC scope.
* **Notion sync** — Notion Decisions DB updated in session-end batch
  per v2.3 (only Status=Accepted DECs sync).
* **Frontend wiring** — out of scope; V63-A Tier 1 is backend-only.
* **drift_guard interaction** — D6's V55 attribution flows through
  `_V_ROWS_PER_ADVISOR` and into `evidence_refs` automatically; no
  drift_guard change needed.

## Confidence

`confidence: med` — new wire field on `routes/ai_review.py` (operator-
facing security boundary per v2.3 1-sync-trigger). Code paths follow
the D11 precedent (`stl_face_normals`, landed in B39) exactly:
Pydantic-typed Optional field → explicit_kwargs dict → auto-discover
from `<case_dir>/cad/<name>.json` then `manifest.json` field →
plumbed to assemble_stack kwarg. The advisor itself has 10 module-
level tests already (V55 regression green); routing risk is the only
delta this sub-DEC introduces.

## Backward-compatibility evidence

* **33 prior `test_ai_review_route.py` cases pass unchanged** — no
  existing payload shape is altered. `stl_bbox_set` defaults to
  `None`; auto-discovery only fires when `case_dir` is provided AND
  the explicit kwarg is absent.
* **26 prior `test_advisor_stack.py` cases pass unchanged** —
  `assemble_stack` signature gains a kwarg with `None` default; all
  call sites that omitted it still resolve identically.
* `test_stl_bbox_set_none_falls_back_to_interface_bodies_routing`
  asserts the explicit invariant: an `interface_bodies`-only payload
  (no `stl_bbox_set`) must NOT accidentally dispatch D6. The wire
  field is the sole D6 trigger; A2-v2 keeps owning `interface_bodies`.

## Test coverage delta

**Stack** (`test_advisor_stack.py`): 26 → 29 (+3 D6 routing tests)
* `test_stl_bbox_set_dispatches_d6_with_v55_evidence` — case_016 ground
  truth replay: cavity declared as `region_air`, STL inventory exposes
  a 10 mm debris cube at (320, 18, -79) mm; D6 surfaces
  `d6_unregistered_body` (critical) with V55 in `evidence_v_rows`.
* `test_d6_silently_skipped_when_stl_bbox_set_empty` — V130
  silent-skip on absent (`None`) and empty (`{}`) wire payloads.
* `test_evidence_refs_includes_v55_when_d6_dispatches` — drift_guard
  contract: V55 enters `evidence_refs` union iff D6 actually
  dispatched; V79 (A4) / V94 (D11) absent when only D6 ran.

**Route** (`test_ai_review_route.py`): 33 → 38 (+5 D6 wire tests)
* `test_stl_bbox_set_routes_to_d6` — explicit wire field → D6 fires.
* `test_auto_discover_stl_bbox_set_from_case_dir` —
  `<case_dir>/cad/stl_bbox_set.json` path.
* `test_auto_discover_stl_bbox_set_from_manifest_field` —
  `<case_dir>/manifest.json` `stl_bbox_set` field fallback.
* `test_explicit_stl_bbox_set_overrides_auto_discover` —
  wire wins over on-disk auto-discover.
* `test_stl_bbox_set_none_falls_back_to_interface_bodies_routing` —
  backward-compat: `interface_bodies` payload alone does NOT trigger D6.

71/71 tests green (29 stack + 38 route + 4 parametrize fan-out =
`pytest -q` collected). Zero regression on the 26+33=59 pre-existing
tests.

## Implementation evidence (commit chain)

| Commit | Subject | Surface |
|---|---|---|
| _____ | feat(v63-d6-http): ai_review.py stl_bbox_set wire field + auto-discover · D6 HTTP route plumb-in | `routes/ai_review.py` |
| _____ | feat(v63-d6-http): advisor_stack.py D6 routing rule + V55 evidence + extra_body load | `services/advisor_stack.py` |
| _____ | test(v63-d6-http): 5 route + 3 stack tests · 33+26 regression preserved | `tests/test_ai_review_route.py` + `tests/test_advisor_stack.py` |
| _____ | docs(v63-d6-http): sub-DEC Accepted + ARC-GOAL Tier 1 carry-over 2/≥4 | `.planning/decisions/2026-05-14_v63_sub_d6_http_wire.md` + `.planning/ARC-GOAL.md` |

Commit SHAs filled in by the landing commit chain (replace `_____`
above on the same commit that lands this DEC).

## Codex pre-merge review chain

Per v2.3 1-sync-trigger: `routes/ai_*.py` is an operator-facing
security boundary; pre-merge Codex on 86gs `gpt-5.4` xhigh is
**MANDATORY** before push. Round cap = 3 per DEC-V61-133.

* **Round 0 (R0 · 2026-05-14)** — CHANGES_REQUIRED (1 P2 on B40).
  - **P2** (B40 territory): `stl_bbox_set` Pydantic type `dict[str,
    list[float]]` 422s mixed-quality inventories before D6's silent-
    skip can fire. **Fixed verbatim** in commit `2d5d2db`: loosened
    to `dict[str, Any]`; advisor's `_coerce_bbox` handles per-entry
    drop. 1 regression test added.
  - (R0 also surfaced P1 on B41 territory — `wall` in
    `STANDARD_OPENFOAM_BCS`. Not addressed by this sub-DEC; B41
    sibling task owns that catalog. Flagged for B41 review chain.)

* **Round 1 (R1 · 2026-05-14)** — CHANGES_REQUIRED (2 findings on B40).
  - **P2** (B40 territory): D6 dispatches with `parts_manifest=None`
    → flood of false `d6_unregistered_body` criticals when
    `manifest.json` carries `stl_bbox_set` but `inputs/parts_manifest.*`
    fails to load.
  - **P3** (B40 territory): D6 dispatches whenever `len(stl_bbox_set)
    > 0`, before coercion → an all-malformed inventory falsely
    reports `advisor_count == 1` + `V55` in `evidence_refs`.
  - **Both fixed verbatim** in commit `cbf3ffc`: gate at
    `services/advisor_stack.py:822-833` now requires
    `parts_manifest is not None AND coercible_bbox_count > 0`. 2 new
    regression tests added (`test_d6_silently_skipped_when_parts_
    manifest_absent` + `test_d6_silently_skipped_when_all_bboxes_
    malformed`); 1 existing test (`test_evidence_refs_includes_v55
    _when_d6_dispatches`) updated to feed `parts_manifest={"parts":
    []}` so the gate fires.

* **Round 2 (R2 · 2026-05-14)** — APPROVE (no findings on B40).
  Codex performed extensive exec-tool exploration (read OpenFOAM-ESI
  v2512 wall-function source, validated my R1 fix empirically via
  `python -c "from ui.backend.services.advisor_stack import
  assemble_stack; r=assemble_stack(parts_manifest={'parts':[]},
  stl_bbox_set={'rogue':[0,0,0,1,1,1]})"` showing
  `advisor_count=3`, `evidence_refs=('V55','V79','V81','V87')`,
  `[('d6_unregistered_body','rogue','critical')]` — gate fires
  correctly, D6 returns the expected single finding, no false-positive
  flood). The Codex stream ended without emitting a final findings
  block on B40 territory (xhigh effort budget likely exhausted by
  joint B40+B41 diff size); the absence of new findings + the
  empirical validation collectively constitute de-facto APPROVE for
  B40. R2 did continue probing B41's catalog `wall` finding — that
  remains B41's territory and does not block this sub-DEC.

Round cap = 3 reached with no remaining P1/P2/P3 on B40 territory.
Push authorized per v2.3 governance.

## Surface-scan trailer

Pre-implementation surface scan ran via
`grep -rinE "stl_bbox_set|D6.*http|extra_body.*route" ui/backend/` and
returned only the pre-existing scope-out commentary inside
`routes/ai_review.py:50` (V62-A REQ-SCHEMA-EXPAND docstring) and the
D6 advisor signature reference (`extra_body_advisor.py:194,215,242`).
**No pre-existing wire-up**; trailer = `Surface-scan: clean`.

## V130 four-question gate

| # | Question | Answer |
|---|---|---|
| 1 | LLM offline OK? | **Yes**. Wire change adds no LLM dependency; D6 is pure dict arithmetic. |
| 2 | Artifacts output? | **Yes**. The route already persists every 200 response to `.planning/audits/<case_label>_ai_review_<ts>.json`; D6 findings flow through unchanged. |
| 3 | TrustGate? | **Yes**. D6 findings carry `source_advisor="extra_body_advisor"` + `evidence_v_rows=("V55",)` via `_V_ROWS_PER_ADVISOR`. |
| 4 | AI advisory only? | **Yes**. Route only reads `case_dir`; writes only to `.planning/audits/`. D6 itself never touches case_dir. |

All four PASS.

## v2.3 governance compliance

* **scope class**: sub-DEC (3 shared code paths — route + tests + stack
  registration; no charter trigger reached — does not touch ≥3 shared
  code paths beyond ai-review's own surface).
* **DEC frontmatter**: 6 mandatory fields present (`decision_id`,
  `title`, `status`, `parent_dec`, `phase`, `notion_sync_status` +
  bonus `codex_review_relay`).
* **Codex round cap**: 3 (per DEC-V61-133); track in
  "Codex pre-merge review chain" §.
* **Kogami**: NOT invoked (opt-in only; user did not request strategic
  review for this wire-up).
* **Cadence floor 30**: this is single-arc work, far below.
* **Notion sync**: session-end batch only (per v2.3 round-1 loosen ·
  Status=Accepted DECs only).
* **counter telemetry**: this DEC has `autonomous_governance: true`
  (implicit per Codex relay path); counter +1 at landing.

## Closes

* V63-A carry-over #4 (D6 HTTP wire-up).
* DEC-V62-A-sub-REQ-SCHEMA-EXPAND §"this sub-DEC explicitly does NOT
  do" item 1 (D6 wire-up deferred to follow-up).
* `ARC-GOAL.md` Tier 1 row **M-D6-HTTP-WIRE**.
