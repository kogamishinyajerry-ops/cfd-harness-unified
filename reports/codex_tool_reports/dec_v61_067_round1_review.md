# DEC-V61-067 Round 1 Codex Review

## Verdict

**CHANGES_REQUIRED**

Stage A gets the big structural calls right: the F1 family split is sound, `cd_mean` is correctly downgraded to `PROVISIONAL_ADVISORY`, and the Path 1 early-return removal does not appear to regress the V61-052 primary reattachment path. But two of the new HARD_GATED secondaries still fail open under degenerate inputs, and the F2 audit-key contract drifted from the intake.

## Findings

1. **[HIGH] Class: NEW**  
   **Location:** `src/foam_agent_adapter.py:9286-9303`, `knowledge/gold_standards/backward_facing_step_steady.yaml:8-13,56-75`  
   **Issue:** `pressure_recovery` does not prove that the required measurement stations actually exist. The adapter always snaps to the nearest available `x` columns and then computes Cp, even if the domain is not the canonical `x/H≈-10` to `x/H≈30` BFS mesh that the observable definition assumes. I verified this by calling `_extract_bfs_secondary_observables(...)` with only `x={-1, 8, 6}` present; it still emitted `pressure_recovery` and recorded `bfs_pressure_recovery_x_inlet=-1.0` and `bfs_pressure_recovery_x_outlet=8.0` instead of failing. That is especially risky because the gold YAML still advertises the old `x∈[-1,8]` geometry in `physics_contract.geometry_assumption`, so the knowledge contract and the extraction contract currently reinforce the wrong interpretation. A HARD_GATED observable measured at the wrong stations must fail closed, not silently reuse the nearest columns.  
   **Suggested fix:** Before calling `extract_pressure_recovery`, require the chosen inlet/outlet columns to be within an explicit tolerance of the canonical targets (for example, `abs(x_inlet + 10.0) <= x_station_tol` and `abs(x_outlet - 30.0) <= x_station_tol`, where `x_station_tol` is derived from local `dx` or fixed conservatively). If either station is missing, emit a machine-visible error such as `bfs_pressure_recovery_error="required_x_station_missing: target=-10 actual=-1; target=30 actual=8"` and do not publish `pressure_recovery`. In the same slice, update `knowledge/gold_standards/backward_facing_step_steady.yaml` so `physics_contract.geometry_assumption` and its evidence refs match the canonical DEC-V61-052/V61-067 mesh actually required by the observable set.

2. **[HIGH] Class: F4**  
   **Location:** `src/bfs_extractors.py:200-245`, `src/foam_agent_adapter.py:9330-9339`  
   **Issue:** `extract_velocity_profile_at_x` is not conservative on degenerate inputs. It validates `U_bulk`, `step_height`, `x_target_physical`, and `y_targets_physical`, but it does not validate the sampled cell tuples or the vertical coverage of the chosen column. As written, it can:  
   - raise raw `ValueError` instead of `BfsExtractorError` for malformed cells (`[(6.0, 1.0)]`, `[(6.0, "bad", 0.4)]`),  
   - return non-finite outputs such as `{'y_H': inf}` or `{'u_Ubulk': nan}` when the nearest cell contains non-finite data,  
   - fabricate a full 3-point hard-gated profile from a single cell by reusing the same nearest sample for all `y_targets`. I reproduced this through `_extract_bfs_secondary_observables(...)` with only one `x=6, y=0.5` sample; it emitted three entries, all at `y_H=0.5`, instead of failing.  
   This breaks the V61-063/V61-066 conservative-validation rule: a HARD_GATED secondary should reject insufficient or non-finite sampling loudly, not synthesize a plausible-looking profile. The exact-midpoint tie-break you called out is part of the same problem: today it depends on input order rather than an explicit policy.  
   **Suggested fix:** Validate every `cells` entry up front and raise `BfsExtractorError` on malformed tuples or non-finite `x/y/u_x`. Add a coverage guard so each requested `y_target` must have either an exact/bracketed match or a nearest cell within an explicit admissible distance; otherwise raise `BfsExtractorError` and let the adapter stamp an error key. Also make the midpoint behavior explicit in code, for example by sorting on `(abs(cell[1] - y_target), cell[1])` if lower-`y` wins, or by interpolating between the two bracketing cells. Add tests for malformed cells, non-finite cell data, missing `y` coverage, repeated-nearest-cell reuse, and exact-midpoint tie behavior.

3. **[MEDIUM] Class: F2**  
   **Location:** `src/foam_agent_adapter.py:9250,9314-9322,9341,9364-9370`, `tests/test_bfs_alias_parity.py:329-356`, `.planning/intake/DEC-V61-067_backward_facing_step.yaml:202-205,245`  
   **Issue:** The implementation and tests drifted away from the declared audit-key class. The docstring and intake both say secondary failures must be folded into `bfs_*_error` keys, but the code actually emits unprefixed keys such as `pressure_recovery_error`, `velocity_profile_reattachment_error`, and `cd_mean_error`. The tests then assert those unprefixed names, which locks the drift in. The failures are still machine-visible, but they no longer follow the per-case audit-key pattern required by the intake and used by earlier Type II slices. That weakens automated discovery for downstream consumers scanning prefixed audit diagnostics.  
   **Suggested fix:** Rename the emitted keys to a consistent BFS-prefixed class such as `bfs_pressure_recovery_error`, `bfs_velocity_profile_reattachment_error`, and `bfs_cd_mean_error`. If back-compat matters, keep one-cycle aliases but make the prefixed keys authoritative. Update the alias-parity tests to assert the prefixed names, and add one dispatch-level failure test per extractor so the F2 contract is exercised from the real BFS branch rather than only from the isolated static method.

## Comments

- **F1 tautology check:** no blocking issue found. `reattachment_length`, `pressure_recovery`, and `velocity_profile_reattachment` do span three physically distinct families, and `cd_mean` is correctly demoted to `PROVISIONAL_ADVISORY` because it is another reduction of the same wall-shear signal.
- **Path 1 early-return removal / Path 2 guard:** no regression found in the refactor itself. Compared with pre-A.2, the new branch keeps the authoritative wall-shear result, skips Path 1b when `reattachment_length` is already set, and skips the near-wall-Ux fallback via the new guard at `src/foam_agent_adapter.py:8408-8412`. I do not see an overwrite hazard there.
- **`cd_mean` placeholder `ref_value`:** acceptable for Stage A only because it is explicitly advisory-only and the YAML now says the scalar is a legacy placeholder, not a like-for-like literature anchor. I would not block the slice on that point, but I would also not treat any advisory PASS/FAIL on `cd_mean` as physically meaningful until the reference is replaced by a quantity derived from the same downstream-floor integral.
- **Verification:** `.venv/bin/pytest -q tests/test_bfs_extractors.py tests/test_bfs_alias_parity.py tests/test_foam_agent_adapter.py -q` passed (`214 passed in 1.13s`). The blockers above are therefore test-coverage gaps plus fail-open behavior, not already-failing checks.

## Self-pass-rate Calibration

The intake's `self_estimated_pass_rate=0.65` did **not** hold. I would calibrate this Stage A slice closer to **0.35-0.40**: the architectural shape is mostly right, but two HARD_GATED secondary paths still accept bad input too easily, and the F2 audit-key contract was not landed as specified.
