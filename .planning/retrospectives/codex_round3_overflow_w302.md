# Codex round-3 overflow · W3.0.2 (DEC-V61-220 · thermo_dict multi-region)

> Per CLAUDE.md round cap = 3 (R0 + 2 fix) and /goal Pattern B: at the 3rd review
> round, remaining findings land here rather than spiraling. The user's standing
> instruction was "stop only on charter-trigger OR Codex-stuck-at-R3"; this is the
> Codex-at-R3 case. The AskUserQuestion consult tool errored ("Stream closed")
> twice (same failure mode as W3.0.1) — user unreachable in autonomous mode, so
> the W3.0.1 precedent (accept-at-cap + overflow record) was applied.
> Date: 2026-05-30 · relay: 86gs R0, then CRS gpt-5.4 high (86gs upstream-failed).

## Chain

| Round | Relay | Verdict | Findings | Disposition |
|---|---|---|---|---|
| R0 | 86gs gpt-5.4 xhigh | CHANGES_REQUIRED | **2× P2** — eConst/non-pureMixture region still built a populated snapshot (single-region refuses) · solid `rho` extracted from any EOS block regardless of declared `rhoConst` | **fixed** (scope-out gate → region None · `_extract_rho_const` gated on `eos_kind=="rhoConst"`) + 3 pins |
| R1 | CRS gpt-5.4 high (86gs stream-failed) | CHANGES_REQUIRED | **2× P1** — multi-region returned partial snapshots (required `Cp` / fluid transport / `molWeight` None) where single-region returns None; "malformed file looks parsed" | **fixed** (Contract A: required-field-absent → region None, symmetric with single-region; builders return `\| None`; unknown-type → region None) + 5 pins updated |
| R2 | CRS gpt-5.4 high | CHANGES_REQUIRED | **1× P1** — a region name in BOTH `fluid_regions` and `solid_regions` collapsed the map key (fewer keys than declared) | **fixed** (`dict.fromkeys` dedup; in-both → single None key) + 1 pin |

Plus the pre-Codex 2-lens `test-red-team` workflow pass that caught **P1×3 + P2×2 + P3**
(solid-kappa gating, nesting-depth leaks incl. the load-bearing `thermoType.type`
discriminator, directive-inside-block, docstring overclaim) — all fixed before R0.

## Cap analysis & honest residual

- **All findings across all rounds are FIXED + regression-pinned** (153 p3+single-region
  tests green; 308 case-extractor surface green; no regression).
- The findings **converged** (each round a distinct, progressively narrower edge
  case: out-of-scope models → required-field refusal contract → a duplicate-key
  edge case) — NOT a V131-style oscillating spiral. But the chain was **P1-heavy**
  (R1 + R2 both P1), so it did not reach a clean APPROVE within the cap.
- **What R2 implicitly validated**: R2 reviewed the post-R1 code (the substantial
  Contract-A required-field refactor — both builders + unknown-type branch + the
  molWeight gate) and did **NOT** re-flag any of it, finding only the narrow
  dedup edge case. So the substantial R1 fix was effectively cross-AI reviewed.
- **Honest residual**: the **only** change NOT re-reviewed by Codex is the R2 fix
  itself — a 5-LOC `dict.fromkeys` dedup + a docstring clarification, regression-
  pinned (`test_region_name_in_both_tuples_single_key_none`). Risk assessed **low**
  (trivial, deterministic, tested). If 86gs recovers, an opportunistic spot
  re-review of just that ~5 LOC is a cheap future hedge (non-blocking).

## Resolution (2026-05-30) — accept at cap=3 (W3.0.1 precedent)

Options considered: (a) accept-at-cap + overflow record [CHOSEN]; (b) authorize one
confirming R3 review; (c) user reviews. The AskUserQuestion consult to choose
between them errored twice; per the standing autonomous-mode grant + the W3.0.1
precedent (identical situation, identical tool failure) the main session applied
**(a)**: all R0→R2 fixes landed + verified, DEC-V61-220 → Accepted at
`confidence: med` (honest — the chain did not reach a clean APPROVE), **no R3**
(cap honored — no spiral). (b) was the runner-up and remains available if the user
prefers a confirming round on next touch; (c) is moot while the consult tool is down.

## Calibration (RETRO-V61-001 intake)

1. **The honest-refusal checklist worked but missed the CONTRACT axis.** The W3.0.1
   carry-forward checklist (malformed / ambiguous / nesting-depth) caught the
   red-team P1s pre-Codex, but the **"required-vs-optional payload" contract**
   (Contract A: required-field-absent → region None, symmetric with the wrapped
   single-region extractor) was the R1 P1 the checklist didn't enumerate.
   **Carry-forward for W3.0.3+ and any "wrapper around an existing extractor":**
   add a checklist item — *"does the wrapper's refusal bar match the wrapped
   extractor's required-field bar? enumerate the required vs optional fields UP
   FRONT and pin a region-None test per required field."*
2. **Map-key uniqueness under union iteration** (R2 P1) is a generic multi-region
   wrapper hazard (`fluid + solid` concatenation can duplicate a name). Carry-forward:
   any extractor keyed by a name drawn from ≥2 source lists must `dict.fromkeys`-dedup
   and pin the in-both case.
3. **86gs upstream instability persists** (R1 stream-failed mid-review, after
   W3.0.1's 502×2). The CRS effort-downgrade (xhigh→high) is acceptable for these
   parsers (red-team already did the deep adversarial pass), but if 86gs
   instability continues, consider a CRS-primary period for governance review.
