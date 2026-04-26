# Failure notes — circular_cylinder_wake

> Free-form yaml/markdown — not a P4 KOM schema artifact.

## FM-CCW-1: Silent kOmegaSST override ignores whitelist laminar declaration

- **Tag**: `whitelist_field_silently_ignored`
- **Trigger**: `whitelist.yaml:83` declares `turbulence_model: laminar` per DEC-V61-005, but `_turbulence_model_for_solver` (`foam_agent_adapter.py:668`) returns `kOmegaSST` for `BODY_IN_CHANNEL` regardless of the whitelist field
- **Symptom**: kOmegaSST over-dissipates the laminar wake at Re=100 → underpredicts St by 10-20%, Cl_rms by 30-50%; audit fixture falls back to `U_max_approx` because St FFT finds no dominant peak
- **Detected**: DEC-V61-053 intake audit (2026-04-23)
- **Status**: IN-FLIGHT — DEC-V61-053 Batch B1 decision (a) threads `task_spec.turbulence_model` through `_turbulence_model_for_solver` so whitelist override wins

## FM-CCW-2: Hardcoded canonical Strouhal value (retired)

- **Tag**: `hardcoded_canonical_value`
- **Trigger**: pre-DEC-V61-041 emitter returned a hardcoded `canonical_st = 0.165` instead of measuring St from the solver's Cl(t) time-series
- **Symptom**: PASS verdicts that did not reflect solver physics — any solver bug would still report 0.165
- **Detected**: 2026-04-21 era audit
- **Status**: RESOLVED — DEC-V61-041 retired the hardcode; `cylinder_strouhal_fft.emit_strouhal` now reads `forceCoeffs1/0/coefficient.dat` and computes St via FFT of Cl(t)

## FM-CCW-3: Domain blockage residual

- **Tag**: `geometry_simplification_residual_bias`
- **Trigger**: pre-DEC-V61-053 Batch B1 domain was 20% blockage (D / channel_height); Williamson 1996 anchors assume unconfined flow
- **Symptom**: Cd bias +8-12% per Zdravkovich 1997 Ch.6 blockage correction; St also biased
- **Detected**: DEC-V61-053 round 1 intake review
- **Status**: PARTIALLY RESOLVED — Batch B1a grew domain to 8.3% blockage (residual 3-5% Cd bias); Codex round-1 MED-1 flagged this is still above the ~5% rule-of-thumb. RESIDUAL_RISK_CARRIED for this DEC; future DEC may grow H to 10D for <5%

## FM-CCW-4: u_mean_centerline naming ambiguity (raw vs deficit)

- **Tag**: `key_name_misleads_extractor_consumers`
- **Trigger**: gold key is `u_Uinf` (suggests raw u/U_inf), but values 0.83→0.35 are monotonically decreasing — only consistent with **deficit** (U_inf − u)/U_inf, NOT raw (which would increase as wake recovers)
- **Symptom**: extractor or comparator reading `u_Uinf` as raw u/U_inf would compare apples to oranges; documentation confusion
- **Detected**: DEC-V61-053 Batch B2 audit (Codex round 1)
- **Status**: RESOLVED via documentation + extractor-self-naming. Per-point `description: centerline velocity deficit` clarifies intent; extractor self-names output keys `deficit_x_over_D_*`. Key rename `u_Uinf → u_deficit` deferred — downstream blast radius too large for this DEC

## FM-CCW-5: Audit-fixture St falls back to U_max_approx

- **Tag**: `extractor_fallback_masks_solver_failure`
- **Trigger**: when kOmegaSST silent override dampens shedding, FFT finds no dominant peak → fixture surface falls back to `measurement.quantity = U_max_approx` (a cell-centre velocity surrogate, not a Strouhal frequency)
- **Symptom**: fixture appears "extracted" but is a different physical quantity than the gold demands; comparator may surface a verdict against U_max_approx that has no relation to St=0.164
- **Detected**: pre-DEC-V61-053
- **Status**: IN-FLIGHT — Batch B3 phase5_audit_run.py will write St as primary; expected to succeed once the Batch B1 laminar override + Batch B1a grown domain produce physical shedding

## Pattern themes

- **whitelist_field_silently_ignored**: high-level metadata is parsed but adapter's per-case path makes its own decision. P4 should add an audit trail: `effective_turbulence_model` written to the run's results manifest and compared against `task_spec.turbulence_model`.
- **extractor_fallback_masks_solver_failure**: extractors with multi-tier fallbacks can return a value while silently changing the physical meaning of the measurement. P4 should require extractors to declare `expected_quantity` and FAIL (not fall back to a surrogate) when the expected quantity cannot be produced.
- **hardcoded_canonical_value**: literal gold values copied into emitter code; recurs at impinging_jet (Cf-as-Nu leakage). P4 should ban literal gold-value copies in `src/`; emitter must read from `gold_standards/`.
- **key_name_misleads_extractor_consumers**: backward-compat key names that semantically drifted. P4 should support `key_aliases` with explicit deprecation date.
