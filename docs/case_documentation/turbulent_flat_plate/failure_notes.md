# Failure notes — turbulent_flat_plate

> Free-form yaml/markdown — not a P4 KOM schema artifact.

## FM-TFP-1: Wrong-regime gold (turbulent Spalding fit applied to laminar Re_x)

- **Tag**: `regime_mismatch_gold_value`
- **Trigger**: Pre-DEC-V61-006 gold was Cf = 0.0076 from a Prandtl 1/7-power Spalding fit, but Re_x = 25000 is well below transition (3·10⁵–5·10⁵ on smooth plate). The 1/7-law is validated for turbulent BL (Re_x ≳ 5·10⁵), not laminar.
- **Symptom**: solver running laminar simpleFoam reported Cf ≈ 0.0042 (Blasius), gold compared at 0.0076 → systematic 45% miss; verdict was FAIL even though physics was correct
- **Detected**: docs/whitelist_audit.md §5.2 audit, 2026-04-20
- **Status**: RESOLVED — DEC-V61-006 (Gate Q-new Case 4 Path A, approved by Kogami 2026-04-20) flipped gold to Blasius Cf = 0.664/√Re_x: at x=0.5 → 0.00420; at x=1.0 → 0.00297. case_id retained for stability.

## FM-TFP-2: Mesh undersampling (historical)

- **Tag**: `wall_normal_cell_count_too_low`
- **Trigger**: pre-fix mesh had 20 wall-normal cells; insufficient to resolve δ_99 of laminar BL
- **Symptom**: Cf measurements drifted from Blasius by mesh-resolution-sensitive amounts
- **Detected**: STATE.md regression audit
- **Status**: RESOLVED — commit 9d843e9 (per ~/CLAUDE.md project memory): mesh 20→80 y-cells with 4:1 wall grading

## FM-TFP-3: Wall-cell gradient extraction degeneracy

- **Tag**: `extractor_uses_degenerate_wall_cell`
- **Trigger**: extractor computing τ_w = μ·∂u/∂y on the wall-cell itself uses Δu = u_wall = 0 (fixedValue BC), giving zero or numerical-noise values
- **Symptom**: τ_w extraction returned 0 or NaN at the wall
- **Detected**: pre-DEC-V61-006 era
- **Status**: RESOLVED — commit 6411d0b: `_compute_wall_gradient` (foam_agent_adapter.py:6870-6879) now skips the wall-cell, requires `len(interior_samples) ≥ 2`, and uses (c0,u0)(c1,u1) for the gradient.

## FM-TFP-4: Spalding fallback as silent regime-mismatch absorber

- **Tag**: `extractor_fallback_could_mask_regime_error`
- **Trigger**: Spalding-fallback branch is still present in `foam_agent_adapter.py` (~line 6924) — designed for turbulent flow but executable from laminar contract
- **Symptom**: under correctly-laminar declared physics, fallback should NEVER fire (measured Cf < 0.01 organically). If it does fire under a laminar contract, it now indicates a genuine extraction failure rather than a regime-mismatch absorber. But there is no assertion guarding this.
- **Detected**: DEC-V61-006 closure review
- **Status**: PARTIAL — fallback retained for backward compatibility; **follow-up audit recommended**: assert that Spalding fallback did NOT fire when contract is laminar.

## Pattern themes

- **regime_mismatch_gold_value**: gold value derived from a correlation valid in regime A applied to a case configured in regime B. Recurs at differential_heated_cavity (Ra=1e10 turbulent gold applied to laminar adapter). P4 should require gold values to declare `valid_regime: { Re_min, Re_max, Pr_range, ... }` and FAIL ingest if case `Re ∉ valid_regime`.
- **extractor_fallback_could_mask_regime_error**: extractors with multi-tier fallbacks can silently absorb a regime mismatch by switching from the regime's authoritative formula to a "compatible" one. Recurs at circular_cylinder_wake (St → U_max_approx). P4 extractors should fail loudly when their primary measurement is unavailable, not silently downgrade.
- **wall_normal_cell_count_too_low**: BL-resolution mesh sizing decoupled from solver regime. P4 should auto-derive minimum wall-normal cell count from declared regime + δ_99 estimate.
