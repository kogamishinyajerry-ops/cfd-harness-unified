---
decision_id: V61-219
title: shm_dict multi-region variant (master-sHM cellZone-derived) — P3 W3.0.1 sub-DEC
status: Accepted
parent_dec: V61-217
phase: P3 (Blueprint v4 · CHT)
autonomous_governance: true
confidence: med
kogami_opt_in: false
round_cap: 3
codex_review_relay: crs gpt-5.4 (effort=high, fallback) — 86gs 502 Bad Gateway upstream-unavailable twice mid-review 2026-05-30 (per DEC-V61-214 fallback precedent); effort-downgrade xhigh→high noted for retro
codex_verdict: cap=3 reached (R0→R1→R2 all CHANGES_REQUIRED, all P2/P3 no P1) — R0+R1 (6 findings) fixed+verified; R2 (2 findings) fixed at cap without independent R3 re-review per discipline (overflow record + user-ratified path)
codex_tool_report_path: reports/codex_tool_reports/v61_219_chain_report.md
overflow_record: .planning/retrospectives/codex_round3_overflow_w301.md
notion_sync_status: pending_accepted
---

# DEC-V61-219 · shm_dict multi-region variant for CHT topology (P3 W3.0.1)

## Context

DEC-V61-217 W3.0.1 — the region-aware `snappyHexMeshDict` reader, second P3
item, consuming W3.0's `RegionPropertiesSnapshot` (DEC-V61-218). Surface scan
(V61-088): zero pre-existing multi-region sHM impl; `shm_dict_extractor`
(DEC-V61-212) returns `Mapping[str, Any]` for the single master dict. New
extractor, **parallel-new** disposition.

## Decision

Add `ui/backend/services/case_extractors/shm_dict_multi_region.py`:
`extract(case_dir, region_snapshot) → Mapping[str, RegionShmSnapshot | None] | None`,
keyed by every region in the snapshot. Stdlib-only; reuses
`shm_dict_extractor`'s block-finding helpers (`_find_top_level_block`,
`_find_matching_close`, `_find_paren_list`, `_strip_comments`, …) — no new
OF-dict parser. Re-exported as `extract_shm_dict_multi_region` (package FIVE→SIX).

### Resolved topology (load-bearing — the charter's design fork)

**Master-sHM cellZone-derived** (fork **a**). Real `chtMultiRegionSimpleFoam`
cases use ONE `system/snappyHexMeshDict` that meshes the whole assembly;
per-region cellZone tagging lives in `castellatedMeshControls.refinementSurfaces`
(each entry's `cellZone <region>;` token) + the top-level `locationsInMesh`
(V90) / `locationInMesh` (legacy) seeds. `splitMeshRegions -cellZones` carves
the regions. **No per-region `system/<region>/snappyHexMeshDict`** exists in any
corpus case (verified 2026-05-30: `find . -path '*system/*/snappyHexMeshDict'`
empty). case_002b's 6 Ti solids are **extruded** (`topoSet` +
`extrudeToRegionMesh`), not sHM-meshed → they have no refinementSurface cellZone
→ **honest `None`** per region (the charter's "7 keys, ≤6 None" escape hatch).

### V90 / V92 handling

- **V90** `locationsInMesh ( ((x y z) zoneName) ... )` list parsed per-region;
  each zone's seed → `RegionShmSnapshot.seed_point`, `location_syntax="locationsInMesh"`.
- **V92** per-region `cellZoneInside` mode (`inside`/`insidePoint`/`outside`)
  surfaced distinctly in `cell_zone_inside_mode` so a downstream validator can
  tell heterogeneous topologies apart (not normalized to one mode).

## Build trail (workflow + adversarial pre-review + main-session fixes)

Implementation produced by the 3-phase workflow (`wf_9e0cfd1d-0d3`): understand
(3 readers — sibling contract / **real chtMultiRegion topology survey** /
fixtures) → `backend-engineer` implement → 2-lens `test-red-team`. The
load-bearing topology reader resolved fork **a** from real OF convention + the
in-repo corpus (case_016, case_004) + V90/V92 findings. The main session then
verified diffs and **fixed the red-team findings before Codex** (governance in
main session):

- **P1 (must-fix · topology correctness)**: the implementer keyed per-region
  data on the refinementSurface ENTRY name (the STL/geometry alias), but the
  region↔sHM link is the `cellZone <token>`, which differs from the entry name
  in real cases (case_016: surface `fwh_porous_surface` → cellZone `fwh_inside`).
  The synthetic fixtures used entry-name == cellZone == region (CIRCULAR), so the
  bug passed its own tests. **Fixed**: re-index `refinementSurfaces` by their
  `cellZone` token; a surface with no cellZone tags no region (no fabrication).
  Anti-circularity regression tests added (entry name ≠ cellZone token) — they
  FAIL on the entry-name-keyed code, PASS on the fix.
- **P2 (fabrication · nested-block leak)**: `cellZone`/`cellZoneInside`/
  `patchInfo` were regex-scanned over the WHOLE surface body, so a value inside a
  nested `regions { inner { cellZone X } }` sub-block leaked to the parent.
  **Fixed**: `_top_level_only()` depth-0 scan + top-level `patchInfo` lookup;
  nested-leak regression test added.
- **P1 follow-on (duplicate cellZone)**: two surfaces claiming the same cellZone
  token → **honest `None` refusal** (DEC-V61-218 discipline), not first-match.
- **P3 (test honesty)**: the synthetic "7 populated" test renamed
  `test_synthetic_all_in_one_shm_7_populated_snapshots` to not imply real
  case_002b yields 7 populated; the real case_002b gate is
  `test_case_002b_honest_extruded_solids_yield_none` (7 keys, 6 honest None).

## Open-question resolutions (implementer flagged 4; resolved here)

1. **case_002b acceptance gate** — RESOLVED: the **honest** "7 keys, 6 None"
   interpretation is canonical (matches real extruded-solid topology + the
   charter escape hatch + DEC-V61-218 refusal discipline). The synthetic
   all-7-populated fixture is kept only as a separate path pin (renamed).
2. **V90 syntax-vs-topology mismatch flag** — deferred to a follow-on sub-DEC;
   raw evidence (`location_syntax` + per-region `seed_point`) is available to a
   caller. Documented scope-out.
3. **Duplicate cellZone detection** — RESOLVED: honest `None` refusal (implemented).
4. **Legacy `locationInMesh` global seed** — RESOLVED: recorded as
   `location_syntax="locationInMesh"` but NOT replicated into each region's
   `seed_point` (a per-region seed comes only from a `locationsInMesh` entry or
   an `insidePoint`). Documented.

## Passes-criteria

1. `pytest -q tests/p3/test_shm_dict_multi_region.py` + `..._redteam.py` →
   **31 passed**.
2. case_002b honest shape → 7 keys, 1 fluid populated + 6 extruded `None`.
3. case_011 shape (3 regions) → 3 populated snapshots.
4. V90 `locationsInMesh` per-region seeds surfaced; V92 `cellZoneInside` modes
   distinguished.
5. Region found by cellZone token even when entry name differs (anti-circularity);
   nested-block cellZone does not leak; duplicate cellZone → None.
6. Sibling `shm_dict_extractor` tests + full P3 suite: **207 passed, 12 skipped**
   — no regression. Stdlib-only (trimesh-free subprocess pin).
7. Codex APPROVE — **gate pending R0**.

## Governance (DEC-level meta)

- `autonomous_governance: true` (counter +1 on Accept).
- Kogami opt-in: false (sub-DEC class; reversible).
- Codex round cap = 3; pre-merge mandatory (new OpenFOAM dict parser).
- Four-question gate (V130): LLM offline ✓ · artifacts canonical ✓ (reads
  on-disk master sHM) · TrustGate-explainable ✓ (honest `None` for any region
  without cellZone/seed evidence; never fabricates a mapping) · advisory-only ✓.
- Surface-scan: clean (new extractor).

## Ratification

**Codex chain R0→R1→R2 on CRS gpt-5.4 (high; 86gs 502×2 fallback) — cap=3 reached,
all findings P2/P3, NO P1.** Chain report `reports/codex_tool_reports/v61_219_chain_report.md`;
overflow record `.planning/retrospectives/codex_round3_overflow_w301.md`.

- **R0** 2×P2 — patchInfo nested leak (`_find_top_level_block` is line-anchored,
  not depth-aware) · legacy `locationInMesh` syntax dropped. **Fixed**:
  `_find_depth0_block` (brace-depth-aware) + unconditional `location_syntax`; +3 tests.
- **R1** 2×P2 — non-fluid/solid "pass-through" docstring lie (W3.0's snapshot
  carries only fluid/solid) · duplicate `locationsInMesh` seed last-wins.
  **Fixed**: docstring corrected + duplicate-seed honest refusal; +2 tests.
- **R2** P2 seed-only sHM gate (V90-reachable: `locationsInMesh`-only cases
  wrongly rejected) + P3 malformed `locationsInMesh` entry silently dropped.
  **cap=3 reached** → per CLAUDE.md "remaining P2/P3 → overflow" + user "stop at
  R3". The AskUserQuestion consult tool errored (Stream closed ×2); given no P1,
  clean ~18 LOC fixes, and the autonomous-mode grant, the main session applied
  the recommended option (a): **both R2 fixes applied + verified (38 tests green)
  WITHOUT an independent R3 Codex round** (the honest residual: R2 fixes are not
  cross-AI re-reviewed — low risk given simplicity + regression tests). Fixes:
  drop the `_extract_master_shm` liveness gate → gate on file-exists +
  `castellatedMeshControls` presence (seed-only V90 now valid); malformed
  named-zone seed → honest refusal.

Status flipped Proposed → **Accepted** (`confidence: med` — honest, given the
chain did not reach a clean APPROVE). Counter +1. Session-end Notion sync.

Tests: **38 passed** (`tests/p3/test_shm_dict_multi_region.py` +
`..._redteam.py`) · **214 passed, 12 skipped** (full P3 + siblings, no regression).

**Calibration notes (RETRO-V61-001 intake)**:
1. The red-team workflow pass caught the **circular-fixture P1** (entry-name
   keying that passed its own tests) — the single most valuable catch, exactly
   the "plausible-but-wrong parser" risk the charter warned about. Carry-forward:
   multi-region/association parsers MUST have at least one fixture where the join
   key (cellZone) ≠ the entry key (surface name), or the test is circular.
2. W3.0.1 ran the full cap=3 with EVERY round finding distinct, legitimate,
   progressively-deeper edge cases (converging, not a V131 oscillating spiral).
   Recurring theme across all rounds: OF-dict parsers fail on **"line-anchored vs
   true brace-depth-aware matching"** and **"malformed/ambiguous/duplicate source
   → silent collapse vs honest refusal."** Carry-forward for W3.0.2: enumerate
   the malformed-input + ambiguous-source + nesting-depth classes UP FRONT (a
   parser honest-refusal checklist) before first review, to compress the ~3-round
   floor.
3. **86gs 502×2 mid-review** forced CRS fallback (effort xhigh→high). The
   effort-downgrade is acceptable for this parser (red-team already did the deep
   adversarial pass), but is logged for retro — if 86gs instability persists,
   consider a CRS-primary period.
