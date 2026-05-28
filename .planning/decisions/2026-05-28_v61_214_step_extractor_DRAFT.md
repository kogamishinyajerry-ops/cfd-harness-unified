---
decision_id: V61-214
title: STEP-path extractor (case dir → step_path | None) — sub-DEC
status: Proposed
parent_dec: V61-211
phase: P2 (Blueprint v4)
notion_sync_status: not-yet (Proposed; sync only when Accepted per v2.3)
---

# DEC-V61-214 · STEP-path extractor for case-behavioral eval (Stage-2 2c extension) — DRAFT

## Context

DEC-V61-211 landed the first `case_extractors/` member (`solver_block_extractor`)
and established the pattern: pure stdlib reader, local-mirror dataclass when
upstream import drags trimesh, density-based refusal as honest omission, scope-
locked NON-features in the docstring, and a Codex R0/R1 review cycle.

`assemble_stack` (`ui/backend/services/advisor_stack.py:665-667`) consumes a
second triplet of kwargs that no production code constructs from a `case_dir`:
`step_path`, `step_bbox_max_extent_raw`, `step_body_extents_raw`. The wire-form
HTTP route already auto-discovers these in `ui/backend/routes/ai_review.py:342`
(`_autodiscover_step`) and `:359` (`_autodiscover_geometry_metadata`) — but
the **case-behavioral eval has no equivalent path**, mirroring the gap that
DEC-V61-211 closed for `SolverBlockSnapshot`.

### Correction to brief assumption (truth-chain)

The scoping brief stated that `step_path` / `step_bbox_max_extent_raw` /
`step_body_extents_raw` feed `face_orientation_advisor` and
`extra_body_advisor`. They do not. The single consumer is
`unit_detector.detect_unit` (advisor_stack.py:898-911; signature at
`ui/backend/services/geometry_ingest/unit_detector.py:166`). Recording this
explicitly so a future reader does not over-credit the extractor's
downstream reach.

## Decision

Add `case_extractors.step_path_extractor.extract(case_dir) → StepArtifacts | None`
mirroring the v0.1 shape of `_autodiscover_step` + the bbox/extents subset of
`_autodiscover_geometry_metadata`. Return `None` when no STEP file is found
under `<case_dir>` or `<case_dir>/cad/` — absence is a normal case-class
signal (most OF cases are bbox-meshed, not CAD-imported), not an error.

### v0.1 scope (this DEC)

- **In**:
  - `step_path`: first `*.step` / `*.stp` / `*.STEP` / `*.STP` under
    `<case_dir>` (root first), then `<case_dir>/cad/`. Sorted for
    determinism. Absolute `str` for JSON-safety.
  - `bbox_max_extent_raw`: from `<case_dir>/cad/bbox.json` `bbox` field
    (6-tuple `[xmin,ymin,zmin,xmax,ymax,zmax]`) → `max(dx,dy,dz)`. Same
    arithmetic as `ai_review.py:_bbox_max_extent` at :764. Returns None
    on arity/type failure (honest omission, not 400).
  - `body_extents_raw`: from `<case_dir>/cad/bbox.json` `extents` list
    of floats. None on type-coercion failure.
  - Manifest fallback: if `<case_dir>/manifest.json` carries `bbox` /
    `extents` keys, use them when `cad/bbox.json` absent — same fallback
    order as `_autodiscover_geometry_metadata`.

- **Out (deferred to v0.2 / future sub-DEC)**:
  - Actually opening the STEP file to compute a bbox/extents from B-rep
    (would require OpenCascade / FreeCAD; violates stdlib-only). v0.1
    surfaces only what is **pre-staged on disk**.
  - Disambiguating multiple STEP files in the same case (today: first
    sorted-win, same as `_autodiscover_step`).
  - Parsing STEP-header unit (`unit_detector.parse_step_header_unit`
    already does this from the path itself; the extractor stays out
    of the unit-decision business).

### Architectural placement

`Lift, not re-implement`. The existing `_autodiscover_step` (18 LOC) and
the bbox/extents portion of `_autodiscover_geometry_metadata` (~25 LOC) are
already battle-tested in the HTTP path. The extractor copies that logic
into `case_extractors/step_path_extractor.py` and returns a single
`StepArtifacts` dataclass; the HTTP autodiscover stays put so the route's
behavior is byte-stable. A follow-on sub-DEC may DRY the two later when
both have ≥1 release of bake time.

Re-implementation would risk drift between `case_dir` semantics on the
HTTP path vs. the eval path — exactly the failure mode V20 reclassification
captured. A lift preserves drift-parity at zero cost.

### Why this extractor (priority context)

Rank within case_extractors backlog (v0.1 scope only):
- `solver_block_extractor` — LANDED (DEC-V61-211).
- **`step_path_extractor` (this DEC)** — universal-applicability LOW (zero
  in-repo case profiles ship STEP files today; see §case-differentiation),
  but unblocks `unit_detector` dispatch in the eval and is the smallest
  remaining extractor (~50-70 LOC). Worth landing now precisely **because**
  the case_profiles corpus is CAD-poor: the absence pattern itself becomes
  the eval signal.
- `shm_dict_extractor`, `thermo_dict_extractor`, `thin_wall_inputs_extractor`
  — bigger surface, defer to follow-on DECs.

### Case-differentiation signal (honest)

**Zero** of 27 `*_dicts/` profiles ship `.step` / `.stp` / `bbox.json` /
`cad/` (verified 2026-05-28: `find .planning/case_profiles -iname "*.step"
-o -iname "*.stp" -o -name "bbox.json" -o -type d -name cad` → empty).
The only STEP files in the repo are gmsh tutorials under `.venv/share/`.

So at v0.1 every existing profile returns `None`, which is the **correct
honest output** — they have no CAD, `unit_detector` should not dispatch,
and the eval sees a deterministic 27/27 absence row. The extractor's value
is unlocked when a future case (e.g., APU bay 0527, case_002a/b with CAD)
sediments a STEP into its profile dir; the extractor then starts producing
non-None and `unit_detector` joins the dispatch set without any other
code change.

This is **honest discrimination = 1 output** today (None for all), vs.
solver_block's `5 density-based / 22 incompressible` two-class split.
We accept it because: (a) the absence row itself is a case-class signal
the eval can assert, and (b) the cost is low and the future-proofing is
free.

### Codex review

Risk-tier per RETRO-V61-001: pre-merge Codex on the extractor since the
output feeds advisor dispatch (correctness-critical shared code). Round
cap = 3 per v2.3 DEC-V61-133. Expected review surface:

- bbox arity / type coercion path (mirrors `_bbox_max_extent` at
  `ai_review.py:764` which raises HTTPException; the extractor must
  silently return None — different error model for a different transport).
- Sort determinism across case-insensitive filesystems (HFS+ / APFS
  default insensitive; `sorted()` over a glob that includes both
  `*.step` and `*.STEP` could double-yield on macOS — verify with a
  case_insensitive fixture).
- `manifest.json` precedence: must NOT override an existing
  `cad/bbox.json` field (R1 risk if precedence inverted).

### Truth-chain risks specific to this extractor

1. **STEP present but unparseable**: this extractor never opens the
   STEP file, so it cannot encounter parse failure. `unit_detector`
   handles header-parse failure (`parse_step_header_unit` returns
   `(None, evidence)`). v0.1's contract: "the file exists and is
   readable as a path string." Truth chain stays clean.
2. **bbox.json present but malformed**: return `None` for the
   malformed field, keep the `step_path` if STEP itself was found.
   Per-field honest omission, not all-or-nothing refusal — different
   from solver_block's whole-snapshot refusal because the fields here
   are independent and the downstream advisor (`unit_detector`) tolerates
   partial input (per its docstring at `unit_detector.py:170-173`).
3. **STEP file collision with auto-generated tutorial paths**: must
   not glob into `.venv/` or other vendored dirs. v0.1 only looks at
   `<case_dir>` and `<case_dir>/cad/` — no recursion, no ancestor
   traversal. Codex R0 likely flags this; pre-empt with a test.

## Scope locking (anti-feature-creep)

This DEC is **file-discovery + on-disk-metadata lift only**. Any of the
following requires a new sub-DEC, not a v0.1 expansion:

- Opening the STEP file to inspect contents (B-rep parsing, header
  re-read for unit beyond what `parse_step_header_unit` already does).
- Picking among multiple STEPs by heuristic (size, mtime, name match).
- Synthesizing a bbox when `bbox.json` absent by walking the STEP.
- Caching across calls.
- Writing anything to disk.

## Estimated LOC

- Extractor: ~50 LOC (dataclass + 1 entry function + 2 small helpers).
- Tests: ~150 LOC (file-found/absent/cad-subdir-win, bbox arity,
  malformed-field-per-field None, manifest fallback, no-recursion-into-
  vendored, drift-parity canary asserting the extractor and
  `_autodiscover_step` agree on every in-repo `*_dicts/` profile —
  all should agree on `None` today).
- `__init__.py` update: 2 LOC.

Total: ~200 LOC, well under sub-DEC threshold.

## Out of scope (explicit)

- Lifting / DRYing `ai_review.py` autodiscover (separate refactor DEC
  once the eval extractor has bake time).
- Wire-form `step_bbox` validation parity with `_bbox_max_extent` (the
  HTTP route raises 400, the extractor silently omits — by design).
- A `cad_artifacts_extractor` aggregating STEP + STL + face_normals +
  stl_bbox_set into one snapshot (would be a v0.2 convenience; v0.1
  keeps one extractor per kwarg-cluster for Codex review surface).

## Verification plan

1. Unit tests as above.
2. Drift-parity canary: parameterized over all 27 `*_dicts/` profiles,
   assert `extract(profile_dir).step_path == _autodiscover_step(profile_dir)`
   (both `None` today; the canary lights up immediately if either path
   silently changes).
3. Eval integration: extend the case-behavioral eval added in
   DEC-V61-211 with an "unit_detector dispatched: yes/no" column; today
   all 27 say "no" — the column gains value as CAD-bearing cases land.

## Recommended priority

**Rank 2** among un-LANDED case_extractors (after `solver_block`
LANDED, before `shm_dict` / `thermo_dict` / `thin_wall_inputs`):
smallest surface, lift-not-rewrite, future-proofing for CAD-bearing
cases.

## Codex risk class

**Low**. The extractor adds no new logic — it lifts proven HTTP-path
discovery into a pure-function shape. Main R0 surface = the three
truth-chain risks above (sort determinism, manifest precedence,
no-recursion-into-vendored). Honest expectation: 0-2 P2 findings, R1
closes them. R1 likely sufficient (well under round cap = 3).
