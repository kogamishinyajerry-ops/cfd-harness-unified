# DEC-V61-066 Round 2 Codex Review

**Reviewer**: Codex GPT-5.4  
**Date**: 2026-04-26  
**Branch**: `dec-v61-066-duct-flow` @ `e19b883`

## Verdict

**APPROVE_WITH_COMMENTS** · 1 MED · runtime fix arc landed cleanly; one intake/spec drift remains

| | Findings |
|---|---|
| HIGH | 0 |
| MED  | 1 |
| LOW  | 0 |

## Verification

- Reviewed landed code in `2399c06`, `719443c`, `e19b883`
- Confirmed comparator precedent at `src/auto_verifier/gold_standard_comparator.py:24-50`
- Ran `uv run --extra dev python -m pytest -q tests/test_duct_flow_alias_parity.py tests/test_auto_verifier/test_gold_standard.py` -> `29 passed`

## Findings

### F1-MED · F#3 downgrade did not land consistently in the intake contract

**File refs**:
- `.planning/intake/DEC-V61-066_duct_flow.yaml:103-119`
- `.planning/intake/DEC-V61-066_duct_flow.yaml:183`
- `.planning/intake/DEC-V61-066_duct_flow.yaml:259-262`
- `.planning/intake/DEC-V61-066_duct_flow.yaml:391-392`
- `knowledge/gold_standards/duct_flow.yaml:74-98`

**Finding**: The runtime contract is fixed correctly: `knowledge/gold_standards/duct_flow.yaml` now marks `friction_velocity_u_tau` as `PROVISIONAL_ADVISORY`, and the comparator already excludes advisory observables from the pass fraction. But the intake still describes the same observable as `HARD_GATED` in the `observable_schema`, `in_scope`, batch A.3 scope text, and Stage B acceptance block. That means the F#3 repair did not land verbatim across the planning/spec surface, and a future reader could still conclude the slice requires "4 HARD_GATED" closure.

**Why it matters**: This does not break the current runtime verdict path, but it leaves the control-plane contract internally inconsistent. For this repo, that is not cosmetic: the intake is used as the planning truth for future batches and reviews, so stale gate language can reintroduce the exact F1 misunderstanding the R1 finding was trying to remove.

**Suggested fix**: Normalize the remaining intake references to `3 HARD_GATED + 1 PROVISIONAL_ADVISORY`. At minimum:
- change `observable_schema.friction_velocity_u_tau.gate_status` to `PROVISIONAL_ADVISORY`
- replace the remaining "3 new HARD_GATED observables" / "all 4 HARD_GATED observables" wording
- add the same "reported, not counted in pass-fraction" rationale in the schema block or explicitly point to the gold YAML as the operative contract

## Checks That Landed Cleanly

- **F#1 / dy-weighted `U_bulk`**: landed as requested. `src/foam_agent_adapter.py:9773-9801` now computes `U_bulk = sum(u_i * dy_i) / sum(dy_i)` from midpoint-derived `dy` with wall bounds `[0.0, 0.5]`, and stamps `duct_flow_U_bulk_method`. The regression at `tests/test_duct_flow_alias_parity.py:354-432` uses a deliberately non-uniform synthetic `cy` grid and proves the emitted value is the dy-weighted result, not the arithmetic mean.
- **F#2 / `nut` staging + audit keys**: landed as requested. `_copy_postprocess_fields` now stages `nut` at `src/foam_agent_adapter.py:7794-7803`. The extractor stamps `duct_flow_nut_source`, `duct_flow_nut_fallback_activated`, and `duct_flow_nut_length_mismatch` before any downstream early return at `src/foam_agent_adapter.py:9701-9718`, so the path is machine-visible on success, fallback, and length-mismatch branches. The new tests at `tests/test_duct_flow_alias_parity.py:435-507` cover both unstaged and staged cases.
- **F#3 / comparator behavior**: the operative runtime contract is correct. `knowledge/gold_standards/duct_flow.yaml:74-98` is downgraded to `PROVISIONAL_ADVISORY`, the alias-parity tests assert the new gate split at `tests/test_duct_flow_alias_parity.py:206-238`, and `src/auto_verifier/gold_standard_comparator.py:24-50` already excludes advisory observables from `hard_checks`, matching the V61-057 precedent.

## Self-pass-rate calibration

Yes, higher than `0.55`.

I would move the next intake self-estimate to roughly **0.75-0.80**. The two extractor-path defects from R1 are fixed in code with credible regression coverage, and the F#3 runtime semantics are correct. The only remaining issue is contract drift inside the intake/planning document, which is worth cleaning up but is materially lighter than the R1 defects.
