# DEC-V61-059 — Codex round-2 review summary

- **Branch**: `dec-v61-059-pc` (commits 48cf994 → 55f32db, post round-1 fixes)
- **Reviewer**: Codex CLI v0.118.0, model `gpt-5.4` (forced via `-c model="gpt-5.4"` because the CLI's default `gpt-5.5` rejects the installed v0.118.0), reasoning effort xhigh
- **Account**: ramaiamandhabdbs@gmail.com (auto-switched from picassoer651 mid-run; score >87% remaining)
- **Invocation**: `codex review --base origin/main -c model="gpt-5.4"`
- **Session ID**: `019dc3c8-295a-7fc1-85fd-fd7b842a0e61` (initial gpt-5.5 attempt rejected) and follow-up gpt-5.4 session
- **Verdict tier**: P1 + P2 — 2 findings, both actionable; **NOT a clean close** (round-3 needed for clean APPROVE)

## Findings

### F3 [P1 / HIGH] — `src/comparator_gates.py:451-452` — G2 concern not in hard-fail set

**Issue (verbatim from Codex):**
> Emitting `CANONICAL_BAND_SHORTCUT_LAMINAR_DNS` here is not sufficient by
> itself, because `_derive_contract_status()` in
> `ui/backend/services/validation_report.py` still hard-fails only the older
> concern types (`MISSING_TARGET_QUANTITY`, `VELOCITY_OVERFLOW`,
> `TURBULENCE_NEGATIVE`, `CONTINUITY_DIVERGED`, etc.). For a plane-channel run
> whose scalar still lands inside the gold band, the API and `audit_real_run`
> fixture metadata will therefore continue to resolve to `PASS`/`HAZARD` even
> though G2 fired, which means the new shortcut detector does not actually
> block the laminar-pass scenario it was added to catch.

**Impact (P1):** This is the **root failure of the entire DEC-V61-059 thesis**.
G2 detection works (round-1 confirmed), G2 emit works, G2 even gets surfaced
in `audit_concerns[]`. But the verdict engine ignored it, so the user-facing
PASS/FAIL never flips. The gate was toothless. This kind of gap is exactly
what RETRO-V61-001 added the "executable smoke test" methodology slot to
catch — Codex round-1's pure unit-test review missed it because no test
exercised the full extractor → fixture → verdict-engine pipeline.

**Fix (committed in this round):** Add `"CANONICAL_BAND_SHORTCUT_LAMINAR_DNS"`
to `_HARD_FAIL_CONCERNS` in `ui/backend/services/validation_report.py` so
`_derive_contract_status()` hard-FAILs whenever G2 fires, regardless of
whether the scalar measurement happens to lie inside the gold tolerance band.

**Test:** `test_validation_report_hard_fails_on_g2_canonical_band_shortcut`
in `ui/backend/tests/test_comparator_gates_g3_g4_g5.py` — passes a
G2 concern alongside an in-band scalar (the PASS-wash scenario the gate
exists to block) and asserts the verdict resolves to `FAIL` with
`within_tolerance=None` (per DEC-036b Codex round-1 nit pattern).

### F4 [P2 / MED] — `src/plane_channel_extractors.py:149-152` — SNR floor optimistic, not conservative

**Issue (verbatim):**
> This diagnostic is described as a conservative numerical-floor estimate,
> but `min(spacings)` does the opposite: any nearly flat segment drives the
> reported floor toward zero and makes `u_plus_profile_snr` arbitrarily large
> even when other intervals are very coarse. On non-uniform profiles—which
> is exactly what the sampled channel curve looks like—the new SNR warning
> will systematically overstate profile quality and can miss under-resolved
> runs that should be flagged.

**Verification of claim:** Confirmed — a non-uniform profile with a single
flat segment near the centerline (where du/dy≈0) produces `min(spacings)≈0`,
giving SNR → ∞ regardless of how poorly resolved the steep sublayer
transition is. The original docstring claimed "conservative" but the math
gave the optimistic dual.

**Fix (committed in this round):** Switch from `min(spacings)` to
`max(spacings)` so the floor reflects the *worst-case* linear-interpolation
error bound: a target y+ landing in the largest Δu+ gap has interpolation
error at most that gap. This makes the diagnostic genuinely conservative.

**Tests added:**
- `test_signal_metrics_high_snr_when_sampling_is_uniform_in_uplus` — a
  60-point profile with uniform Δu+ ≈ 0.31 achieves SNR ≈ 59 (above 10× threshold)
- `test_signal_metrics_loglaw_profile_under_resolved_at_sublayer_boundary` —
  a 64-point uniform-in-y+ Moser-like profile correctly reports SNR < 10×
  due to the y+=5 sublayer-to-log-law transition producing a Δu+ ≈ 5 jump.
  This is the *expected* behaviour: the diagnostic surfaces under-resolution
  on profiles that previously silently passed.
- The old "rich profile" test (`test_signal_metrics_low_snr_for_sparse_non_
  uniform_profile`) is retained as a regression — its 10-point sparse profile
  now correctly reports SNR ≈ 4.75 (was inflated to ~27× under min).

## Pass-rate calibration

- **Round-1 self-est**: 0.40
- **Round-1 actual**: 2 P2 (no P0/P1) → looked like ~0.55
- **Round-1 gap (after fixing F1+F2)**: 0 critical findings *expected* in round-2
- **Round-2 actual**: 1 P1 + 1 P2 → harder verdict than round-1 (Codex went deeper into the cross-plane wiring this round)
- **Lesson**: my round-1 fixes were correct but didn't proactively scan the verdict-engine wiring. The intake §6 honesty calibration improved (predicted MED-tier round-2; actual P1) but the round-2 finding is the kind of thing the *post-fix executable smoke test* (RETRO-V61-053 slot) would have caught — landing a verdict-engine integration test ahead of round-2 would have caught F3 self-host.

## Methodology delta

For DEC-V61-060+: when adding a new `concern_type` to the gate emit path,
**always check the `_HARD_FAIL_CONCERNS` set in
`ui/backend/services/validation_report.py`** in the same commit. The
deliberate-cross-plane-duplication pattern (Execution emits, Evaluation
filters) means a unilateral edit on either side is easy to miss without an
end-to-end fixture test. RETRO-V61-053 already added this as
`executable_smoke_test`; this DEC adds a finer rule:

> Whenever `comparator_gates.py` introduces a new `concern_type` literal,
> the same commit must extend `_HARD_FAIL_CONCERNS` in
> `validation_report.py` AND add a unit test asserting the verdict engine
> hard-FAILs on that concern even with an in-band scalar.

Recommend promoting this to a methodology patch for the next RETRO.

## Round-3 readiness

- F3 + F4 fixes landed (this commit)
- 73 DEC-V61-059 tests green (added 1 verdict-engine regression for F3,
  2 SNR-semantics tests for F4, retired the optimistic-floor "rich profile"
  test in favour of conservative-floor variants)
- Codex budget remaining: 2 rounds (per intake §8: 4-round soft target,
  rounds 1+2 spent)
- Recommend round-3 review after this commit lands to clean-close Stage A
  before A.4.b/A.5 begin.
