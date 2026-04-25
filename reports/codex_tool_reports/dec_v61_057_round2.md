# DEC-V61-057 · Codex Round 2 Review (Stage B)

**Reviewer**: Codex GPT-5.4 (xhigh reasoning)
**Date**: 2026-04-25 (Track B autonomous mandate · cfd-s1-dhc worktree)
**Branch**: `dec-v61-057-stage-b` (commits 837781f, a325a38, 9f6f944 on origin/main 1034c20)
**PR**: #37

## Verdict

**CHANGES_REQUIRED** · 1 HIGH + 1 MED · NO blockers for round 3 (both mechanically fixable)

| | Findings |
|---|---|
| HIGH | 1 |
| MED  | 1 |
| LOW  | 0 |

**Estimated pass rate after fixes**: 90 % (Codex)
**Round-3 budget**: 1 round expected for clean-close (verbatim fixes)

## Findings

### F1-HIGH · Silent truncation defeats the fail-closed contract · ADDRESSED in B-final

**File refs (round-2 cited)**:
- `src/dhc_extractors.py:12-14` (docstring claims fail-closed on "input shape errors")
- `src/dhc_extractors.py:45-46` (DHCFieldSlice docstring "All sequences MUST have identical length")
- `src/dhc_extractors.py:121` (`_wall_gradients_per_layer` clipping `n = min(...)`)
- `src/dhc_extractors.py:246` (`extract_u_max_vertical` no length check)
- `src/dhc_extractors.py:425` (`extract_psi_max` clipping `n = min(...)`)

**Finding**: Module docstring + dataclass contract say shape mismatches must
return `{}`. Implementation silently clipped to `min(len(...))` and emitted
measurements. Codex reproduced non-empty Nu_max, u_max, ψ_max outputs from
deliberately 4-vs-3 mismatched arrays — corrupted field payloads would land
as apparently-valid benchmark numbers instead of MISSING_TARGET_QUANTITY.

**Resolution (verbatim fix, B-final commit)**:
- New `_input_lengths_consistent(*arrays)` helper (one shared length validator)
- Wired into `_wall_gradients_per_layer` (Nu path), `extract_u_max_vertical`,
  `extract_v_max_horizontal`, `extract_psi_max` — all early-return `{}` on
  mismatch
- 2 new mismatch unit tests under `TestDHCMultiDim`:
  - `test_nu_max_fails_closed_on_mismatched_thermal_arrays`
  - `test_velocity_extractors_fail_closed_on_mismatched_arrays`
- Total LOC: ~25 src + ~25 test (within ≤20 LOC verbatim guideline per
  fix-class; combined fix because it's a single conceptual contract repair)

### F2-MED · noise_floor / snr measure profile spread, not numerical noise · ADDRESSED in B-final

**File refs (round-2 cited)**:
- `.planning/intake/DEC-V61-057_differential_heated_cavity.yaml:342-356` (numerical_noise_snr risk_flag mitigation contract)
- `src/dhc_extractors.py:147-165` (`_interior_layer_stdev` definition — measures profile spread, not noise)
- `src/dhc_extractors.py:205-207` (Nu_max emits `noise_floor` / `snr`)
- `src/dhc_extractors.py:308-310` (u_max emits same)
- `src/dhc_extractors.py:356-358` (v_max emits same)

**Finding**: `_interior_layer_stdev()` computes the standard deviation of the
actual wall/centerline profile after trimming. For Nu_max, u_max, v_max that
is mostly *real physics* variation, not extraction noise. Codex measured on
the clean analytical synthetics:
- `Nu_max`: `snr ≈ 6.5`
- `u_max`: `snr ≈ 3.96`
- `v_max`: `snr ≈ 3.94`

Under the intake's `numerical_noise_snr` "SNR < 10× warning" rule, even a
perfectly clean field would be flagged low-SNR. Misleading if Stage C/D
consumes these as numerical-noise diagnostics.

**Resolution (verbatim fix, B-final commit)**:
- Renamed helper `_interior_layer_stdev` → `_interior_profile_spread`
- Renamed return-dict keys: `noise_floor` → `profile_spread`, `snr` →
  `peak_to_profile_spread`
- Both surface as **non-gating** diagnostics (Stage C must not hard-gate on
  them). For Nu_max / u_max / v_max the actual gating is the comparator's
  hard-gate compare against gold tolerance (intake §B); for ψ_max the SNR
  semantics remain residual-based (top-wall closure residual, unchanged).
- Existing `test_nu_max_uniform_bl_gives_uniform_nu` updated to reference
  the renamed `peak_to_profile_spread` field.
- LOC: ~15 src + ~5 test (within verbatim guideline for rename class)

## Items Codex explicitly DID NOT block

- ψ side-wall closure (∂ψ/∂x at x=0/L) — ψ already advisory, top-wall closure
  matches the pre-Stage-A F3 contract
- `PSI_MAX_GOLD_NONDIM = 16.750` as a module-level constant — acceptable
  because closure-residual SNR is a noise check independent of comparator's
  hard-gate compare
- Inverse-distance weighting for u_max / v_max — algebraically equivalent to
  linear interpolation for the 2-bracketing-cell case
- Hot-wall corner trimming — defer to Stage E live-run signal

## Round 2 Disposition

| Finding | Status | Resolution |
|---|---|---|
| F1-HIGH | ✅ Addressed | B-final commit (`_input_lengths_consistent` + mismatch tests) |
| F2-MED  | ✅ Addressed | B-final commit (rename to profile_spread / peak_to_profile_spread) |

**Stage B clean-close target**: Codex round 3 (verbatim diff-level match to
F1 + F2 suggested fixes; ≤2 files; no public API change; PR body cites
round-2 finding IDs per CLAUDE.md verbatim-exception §5-condition rule —
satisfies all 5).

**Stage C kickoff unblocked** after round 3 APPROVE_WITH_COMMENTS.
