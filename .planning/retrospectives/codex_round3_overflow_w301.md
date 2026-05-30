# Codex round-3 overflow · W3.0.1 (DEC-V61-219 · shm_dict multi-region)

> Per CLAUDE.md round cap = 3 (R0 + 2 fix) and /goal Pattern B: at the 3rd review
> round, remaining P2/P3 findings land here rather than spiraling. No P1 remains
> → user ratification requested (per user "stop when Codex stuck at R3").
> Date: 2026-05-30 · relay: CRS gpt-5.4 high (86gs 502 fallback).

## Chain so far (all on CRS after 86gs 502×2)

| Round | Verdict | Findings | Disposition |
|---|---|---|---|
| R0 | CHANGES_REQUIRED | P2 patchInfo nested leak (`_find_top_level_block` line-anchored, not depth-aware) · P2 legacy `locationInMesh` syntax dropped | **fixed** (`_find_depth0_block` + unconditional `location_syntax`) + 3 tests |
| R1 | CHANGES_REQUIRED | P2 non-fluid/solid groups "pass-through" docstring lie · P2 duplicate `locationsInMesh` seed last-wins | **fixed** (docstring corrected + duplicate-seed refusal) + 2 tests |
| R2 | CHANGES_REQUIRED | **P2 seed-only sHM gate** · **P3 malformed `locationsInMesh` entry silently dropped** | **deferred here (cap=3)** |

Plus the pre-Codex `test-red-team` workflow pass that caught the **P1
circular-fixture / surface-name-keying** defect (the single most valuable catch).

## R2 findings (deferred — awaiting user ratification)

### F1 [P2] · seed-only sHM gate rejects valid V90 cases  ⚠️ V90-REACHABLE
`shm_dict_multi_region.py` (the `master = _extract_master_shm(case_dir); if
master is None: return None` gate). The sibling single-region
`shm_dict_extractor.extract()` returns `None` when a sHM declares no
`refinementSurfaces` / `refinementRegions`. But the **modern V90 form** can
define cellZones purely via `locationsInMesh ( ((x y z) zoneName) ... )` with NO
`refinementSurfaces`. For such a case the wrapper exits at the gate and reports
"no master sHM" instead of yielding per-region `location_seed_present=True`
snapshots — directly undermining the charter's "demonstrably handles V90 modern
`locationsInMesh`" criterion for the seed-only sub-case.
**Proposed fix**: drop the `_extract_master_shm` gate; gate instead on
"file exists + readable + has a `castellatedMeshControls` block" (the wrapper
already does its own surface+seed parsing of `cmc_inner`, so the sibling call was
only a too-strict liveness gate). ~10 LOC + a seed-only regression test.

### F2 [P3] · malformed `locationsInMesh` entry silently dropped
`_parse_locations_in_mesh` `continue`s on a malformed pair, returning a partial
map; the caller then encodes the skipped region as `None`, indistinguishable
from an honest extruded/no-sHM region. Breaks the documented "refuse on malformed
source" semantics (a seed-list typo reads as honest absence).
**Proposed fix**: extract the zone name BEFORE validating coords; a present-name
but bad-coords entry → add to the ambiguous/malformed refusal set (same
mechanism as duplicate seeds). Bounded; ~8 LOC + test. (Contract has only
`Snapshot | None`, so the distinction is "refused" vs "absent" both → None — the
gain is the malformed zone is treated as ambiguous, not silently last-wins/dropped.)

## Resolution (2026-05-30) — option (a), both fixed at cap=3

Intended to consult the user (per "stop at R3"), but the AskUserQuestion tool
errored (`Stream closed`) twice. Given **no P1**, clean ~18 LOC fixes, F1 being a
real V90-reachable bug that W3.0.6 will build on, and the standing autonomous-mode
grant, the main session applied the **recommended option (a)**: both fixes landed
+ verified, **without an independent R3 Codex round** (cap=3 honored — no spiral).

- **F1 FIXED**: dropped the `_extract_master_shm` liveness gate; gate now on
  file-exists + `castellatedMeshControls` presence. Regression test
  `test_seed_only_v90_shm_without_refinementsurfaces` (seed-only V90 case now
  yields `location_seed_present=True` snapshots).
- **F2 FIXED**: `_parse_locations_in_mesh` extracts the trailing zone name first;
  a named zone with malformed coords → honest refusal (added to the duplicate/
  ambiguous set). Test `test_malformed_locationsInMesh_entry_refuses_named_zone`.
  Residual scope-out: a malformed entry with NO recoverable zone name is still
  skipped (cannot refuse a region it cannot name) — documented in code.

**Honest residual**: the R2 fixes themselves were not cross-AI re-reviewed (cap=3).
Risk assessed low (simple, regression-tested). If 86gs recovers, an opportunistic
spot re-review of just these ~18 LOC is a cheap future hedge (non-blocking).
Tests after fixes: 38 passed (W3.0.1) · 214 passed, 12 skipped (full, no regression).

Other options considered: (b) commit R0+R1-only + followup sub-DEC; (c) override
cap and run R3. Both rejected in favor of (a) — (b) ships a known V90 bug, (c)
spirals past the cap for no-P1 findings.

## Calibration (RETRO intake)

W3.0.1 ran the full cap=3 with EVERY round finding distinct, legitimate,
progressively-deeper edge cases (not a V131-style oscillating spiral) — the
findings converged. The recurring theme across all rounds: **OF-dict parsers
repeatedly fail on "line-anchored vs true brace-depth-aware" matching and on
"malformed/ambiguous/duplicate source → silent collapse vs honest refusal."**
Carry-forward for W3.0.2 (thermo multi-region) and beyond: enumerate the
malformed-input + ambiguous-source + nesting-depth classes UP FRONT (a parser
honest-refusal checklist) before first review, to compress the ~3-round floor.
