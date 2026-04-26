# DEC-V61-067 Round 2 Codex Review

## Verdict

**APPROVE**

## Findings

No new findings.

## Comments

1. **F#1 landed as requested.**  
   `src/foam_agent_adapter.py:9283-9339` now guards `pressure_recovery` with `X_STATION_TOL=0.5` against the canonical `x/H={-10, 30}` stations and fails closed via `bfs_pressure_recovery_error` when they are absent. I re-ran the R1 reproducer with only `x={-1, 6, 8}` cells and confirmed the adapter emitted `required_x_station_missing: target_inlet=-10.0 actual=-1.0; target_outlet=30.0 actual=8.0; tol=0.5` and did not publish `pressure_recovery`. The YAML update at `knowledge/gold_standards/backward_facing_step_steady.yaml:8-24` also fixes the stale geometry contract to canonical `x∈[-10,30], y∈[0,9·H]` and preserves the V61-052 evidence trail in `physics_precondition`.

2. **F#2 landed as requested.**  
   `src/bfs_extractors.py:221-305` now validates every `(cx, cy, u_x)` entry, wraps non-numeric `float()` coercions into `BfsExtractorError`, rejects non-finite values, makes the midpoint tie-break explicit via `(abs(Δy), y)`, and gates sparse columns with `y_target_max_distance` only when the caller enables it. Back-compat is preserved because the new kwarg defaults to `0.0`; the legacy one-cell/three-target case still returns three reused points in that mode. The adapter correctly opts into fail-closed behavior by passing `y_target_max_distance=0.4 * H` at `src/foam_agent_adapter.py:9345-9357`.

3. **F#3 landed as requested.**  
   All three adapter error emit sites are BFS-prefixed: `bfs_pressure_recovery_error` (`src/foam_agent_adapter.py:9302-9339`), `bfs_velocity_profile_reattachment_error` (`src/foam_agent_adapter.py:9360-9363`), and `bfs_cd_mean_error` (`src/foam_agent_adapter.py:9383-9390`). The alias-parity assertions were updated accordingly in `tests/test_bfs_alias_parity.py:329-360`, and the new regression surface at `tests/test_bfs_alias_parity.py:366-523` covers the x-station fail-close path plus the velocity-profile validation paths.

4. **Coverage check against the R1 verbatim request is sufficient.**  
   The new tests hit malformed tuples, non-numeric cells, non-finite data, missing `y` coverage / repeated-nearest reuse under the enabled guard, exact-midpoint tie behavior, and adapter-level dispatch of the coverage guard. That is enough to demonstrate the requested fail-close behavior without reopening the broader post-R3 methodology questions already deferred in the YAML contract.

## Verification

- `.venv/bin/pytest -q tests/test_bfs_extractors.py tests/test_bfs_alias_parity.py tests/test_foam_agent_adapter.py` → `223 passed in 1.11s`
- Manual reproducer: non-canonical `x={-1, 6, 8}` cells now omit `pressure_recovery` and stamp `bfs_pressure_recovery_error=required_x_station_missing: ...`
- Manual reproducer: one-cell velocity column now raises `BfsExtractorError` when `y_target_max_distance=0.4`, while default `0.0` still preserves legacy back-compat behavior

## Self-pass-rate Calibration

Yes. This R1 fix arc landed cleanly enough that the next bounded review-fix intake should self-estimate higher than `0.35-0.40`. For a similarly scoped verbatim-fix slice, `~0.60-0.70` is now defensible. I would keep broader first-pass feature-slice estimates lower until they demonstrate the same review-closure discipline.
