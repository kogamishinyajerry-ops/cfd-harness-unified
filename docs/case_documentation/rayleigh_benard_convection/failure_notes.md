# Failure notes — rayleigh_benard_convection

> Free-form yaml/markdown — not a P4 KOM schema artifact.

## FM-RBC-1: Solver convergence OSCILLATING (URF tuning)

- **Tag**: `pseudo_steady_oscillation_under_relaxation_dependent`
- **Trigger**: at Ra=10⁶ on the adapter mesh, the steady solve oscillates around the converged Nu rather than monotonically converging
- **Symptom**: residuals plateau in an oscillating band; Nu(t) measurement requires either time-averaging across the oscillation or aggressive URF
- **Detected**: pre-2026-04-21 era
- **Status**: RESOLVED — h (enthalpy) under-relaxation factor reduced 0.1 → 0.05 (commit e7fa556 per project memory). Final Nu = 10.5 matches ref exactly on Phase 7 Docker E2E (rel_error = 0.0).
- **Why this works**: at Ra=10⁶ the case sits near the laminar / soft-turbulence boundary where small perturbations to the temperature field oscillate without damping; reducing h URF damps the temperature update enough for steady SIMPLE to converge.

## FM-RBC-2: Chaivat correlation variant ambiguity (Gate Q-new Case 10 HOLD)

- **Tag**: `gold_value_correlation_variant_unclear`
- **Trigger**: initial audit claimed Chaivat correlation gives 7.2 at Ra=10⁶, but recompute shows 0.229·(10⁶)^0.269 = 9.4 — putting current gold 10.5 only 11.5% off (within 15% tolerance)
- **Symptom**: small discrepancy that does NOT fail the verdict but suggests the original gold-value source may have used a different Chaivat correlation variant than the description states
- **Detected**: Gate Q-new Case 10 audit, 2026-04-20
- **Status**: HOLD per Kogami 2026-04-20 — Chaivat 2006 (DOI 10.1016/j.ijheatmasstransfer.2005.07.039) paper re-read pending before any edit. Gold 10.5 retained meanwhile.

## FM-RBC-3: A-class metadata correction (laminar declaration)

- **Tag**: `metadata_drift_solver_label`
- **Trigger**: pre-DEC-V61-005 turbulence_model field for this case did not explicitly declare laminar — at Ra=10⁶ this is a steady-convective laminar regime, but k-omega SST would over-dissipate at this Ra → under-predict Nu
- **Symptom**: Chaivat correlation Nu=0.229·Ra^0.269 assumes laminar steady regime; mismatch would silently bias Nu low
- **Detected**: docs/whitelist_audit.md §3 A-class audit
- **Status**: RESOLVED — DEC-V61-005 set turbulence_model: laminar; reference_values untouched (A-class metadata correction)

## Pattern themes

- **pseudo_steady_oscillation_under_relaxation_dependent**: convergence cosmetic-only; Nu is stable but residuals oscillate. P4 should distinguish `convergence_metric: { residuals_below | quantity_stable_in_window }` so verdict is on the physical quantity, not on the residual.
- **gold_value_correlation_variant_unclear**: gold value derived from a published correlation but coefficients drift. Recurs at impinging_jet (Behnad 2013 4-5× discrepancy). P4 should require gold values to record `derivation: { paper, equation_number_in_paper, evaluated_with: {Ra:1e6, Pr:0.71, ...} }` so the value can be re-derived during ingest validation.
- **metadata_drift_solver_label**: turbulence_model label drift between whitelist and adapter behavior. Recurs at circular_cylinder_wake (silent kOmegaSST override). P4 should require runtime-effective turbulence_model to be written to the run manifest and compared against task_spec at gate time.
