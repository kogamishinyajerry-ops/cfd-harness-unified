# DEC-V61-066 Round 3 Codex Review

**Reviewer**: Codex GPT-5.4  
**Date**: 2026-04-26  
**Branch**: `dec-v61-066-duct-flow` @ `0060c4a`

## Verdict

**APPROVE** · 0 findings · intake contract is now consistent with the R1 F#3 downgrade

| | Findings |
|---|---|
| HIGH | 0 |
| MED  | 0 |
| LOW  | 0 |

## Verification

- Reviewed full `.planning/intake/DEC-V61-066_duct_flow.yaml`
- Reviewed landed patch in `0060c4a`
- Scanned every `HARD_GATED`, `PROVISIONAL_ADVISORY`, and `friction_velocity_u_tau` reference in the intake
- Confirmed `git diff --name-only e19b883..0060c4a` touches only `.planning/intake/DEC-V61-066_duct_flow.yaml`
- Confirmed `HEAD` is still `0060c4a` and `git status --short` shows no tracked runtime-file edits in this R2 fix arc
- Did **not** re-run the 47 duct tests in R3; this round is intake-only and the runtime contract is unchanged by diff, so the R2 runtime verification carries forward

## Findings

No new findings.

## Checks That Passed

- **HARD_GATED scope is now clean**: the intake’s explicit pass-condition block lists exactly 3 `HARD_GATED` observables plus 1 `PROVISIONAL_ADVISORY` observable at `.planning/intake/DEC-V61-066_duct_flow.yaml:67-76`. The per-observable schema also keeps `HARD_GATED` only on `friction_factor`, `bulk_velocity_ratio_u_max`, and `log_law_inner_layer_residual` at `.planning/intake/DEC-V61-066_duct_flow.yaml:98`, `.planning/intake/DEC-V61-066_duct_flow.yaml:135`, and `.planning/intake/DEC-V61-066_duct_flow.yaml:154`.
- **The intake no longer re-promotes `friction_velocity_u_tau` to a counted gate elsewhere**: the schema marks it `PROVISIONAL_ADVISORY` at `.planning/intake/DEC-V61-066_duct_flow.yaml:103-119`; the independence block keeps it as `SAME_RUN_CROSS_CHECK` at `.planning/intake/DEC-V61-066_duct_flow.yaml:159-173`; the in-scope text and A.3 batch scope both preserve the downgrade at `.planning/intake/DEC-V61-066_duct_flow.yaml:183` and `.planning/intake/DEC-V61-066_duct_flow.yaml:257-266`; and Stage B acceptance explicitly says it is reported but excluded from the pass fraction at `.planning/intake/DEC-V61-066_duct_flow.yaml:392-399`.
- **Runtime contract remains unchanged from R2**: the only committed delta from `e19b883` to `0060c4a` is the intake YAML, so the previously-verified gold YAML, comparator behavior, and duct tests remain untouched in this cleanup pass.

## Self-pass-rate calibration

No revision recommended. Keep the R2 post-fix calibration at **0.75-0.80**.

Reason: this round confirms spec-surface consistency only. It closes the planning/control-plane drift cleanly, but it does not add new runtime evidence beyond the R2 verification that would justify pushing the estimate materially higher.
