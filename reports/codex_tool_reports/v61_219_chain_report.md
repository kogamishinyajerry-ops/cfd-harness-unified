# Codex chain report · DEC-V61-219 (P3 W3.0.1 shm_dict multi-region)

- **Date**: 2026-05-30
- **Relay**: CRS `gpt-5.4` (effort **high**) — **86gs `gpt-5.4` xhigh attempted
  first, returned 502 Bad Gateway (upstream unavailable) twice mid-review**;
  failed over to CRS per DEC-V61-214 precedent. Effort-downgrade xhigh→high logged.
- **Target**: `shm_dict_multi_region.py` (new) + `test_shm_dict_multi_region.py`
  (new) + `test_shm_dict_multi_region_redteam.py` (new) + `__init__.py` (re-export)
  + DEC-V61-219.
- **Outcome**: **cap=3 reached** (R0→R1→R2 all CHANGES_REQUIRED, **all P2/P3, NO
  P1**). R0+R1 (6 findings) fixed+verified; R2 (2 findings) fixed at cap WITHOUT
  an independent R3 round (overflow record + user-ratified path; consult tool
  errored, autonomous-mode option (a) applied).
- **Pre-Codex hardening**: the 2-lens `test-red-team` workflow pass caught a **P1
  circular-fixture / surface-name-keying fabrication bug** — fixed before Codex.

---

## R0 — CHANGES_REQUIRED (2× P2)

1. **patchInfo nested leak** — `_find_top_level_block` is line-anchored
   (`^\s*key\s*{`), NOT brace-depth-aware, so a `patchInfo` indented inside a
   nested `regions { ... }` sub-block still matched and leaked to the parent.
   **Fix**: `_find_depth0_block` (brace-depth-aware). Tests:
   `test_nested_patchinfo_does_not_leak_to_parent` + depth-0 guard.
2. **legacy locationInMesh syntax dropped** — `location_syntax` was gated on
   `location_seed_present`, clearing the token for legacy global-seed cases.
   **Fix**: set `location_syntax` unconditionally (file-level property). Test:
   `test_legacy_locationInMesh_syntax_preserved`.

## R1 — CHANGES_REQUIRED (2× P2)

3. **non-fluid/solid "pass-through" docstring lie** — the docstring claimed
   `porous` etc. pass through "via a field the RegionPropertiesSnapshot carries",
   but W3.0 (DEC-V61-218) carries only fluid/solid. **Fix**: docstring corrected
   to state the inherited fluid/solid-only boundary. Test:
   `test_only_snapshot_groups_iterated_no_phantom_porous`.
4. **duplicate locationsInMesh seed last-wins** — a zone seeded twice silently
   kept the last seed. **Fix**: duplicate-seed honest refusal (symmetric with
   duplicate-cellZone). Test: `test_duplicate_locationsInMesh_seed_yields_honest_none`.

## R2 — CHANGES_REQUIRED (P2 + P3) → cap=3, fixed at cap (no R3)

5. **[P2] seed-only sHM gate (V90-reachable)** — `_extract_master_shm()` returns
   None for a sHM with no `refinementSurfaces`/`refinementRegions`, wrongly
   rejecting valid V90 `locationsInMesh`-only cases. **Fix**: drop the gate; gate
   on file-exists + `castellatedMeshControls` presence. Test:
   `test_seed_only_v90_shm_without_refinementsurfaces`.
6. **[P3] malformed locationsInMesh entry silently dropped** — a named zone with
   bad coords was `continue`d → read as honest absence. **Fix**: extract the
   trailing zone name first; named-zone-bad-coords → honest refusal. Test:
   `test_malformed_locationsInMesh_entry_refuses_named_zone`.

---

## Outcome

- All Codex findings P2/P3 — **no P1, no logic-class defect** (the P1 was caught
  pre-Codex by the red-team workflow).
- Tests: **38 passed** (W3.0.1 main + red-team) · **214 passed, 12 skipped**
  (full P3 + sibling extractors — no regression). Stdlib-only.
- DEC-V61-219 → **Accepted** (`confidence: med` — honest, the chain did not reach
  a clean APPROVE; R2 fixed at cap without re-review).

## Calibration (RETRO-V61-001 intake)

1. **Circular-fixture detection** is the highest-value red-team move for
   association parsers: require ≥1 fixture where the join key ≠ the entry key.
2. **~3-round honest-refusal floor** holds for OF-dict parsers; the recurring
   defect classes are "line-anchored vs brace-depth-aware" and "malformed/
   ambiguous/duplicate → silent collapse vs honest refusal." Enumerate these UP
   FRONT (a parser honest-refusal checklist) for W3.0.2 to compress the floor.
3. **86gs 502×2** forced the CRS effort-downgrade — logged; consider CRS-primary
   if 86gs instability persists.
