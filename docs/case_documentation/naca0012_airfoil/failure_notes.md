# Failure notes — naca0012_airfoil

> Free-form yaml/markdown — not a P4 KOM schema artifact.

## FM-NACA-1: Unreliable pre-V61-058 source (retired)

- **Tag**: `unreliable_paper_provenance`
- **Trigger**: pre-DEC-V61-058 source field cited "Thomas 1979 / Lada & Gostling 2007" with DOI 10.1017/S0001924000001169 (Aeronautical Quarterly)
- **Symptom**: Codex F4 round-1 plan review flagged the provenance as unreliable — paper not findable in canonical archives or DOI resolves inconsistently
- **Detected**: DEC-V61-058 round 1 plan review (2026-04-25)
- **Status**: RESOLVED — DEC-V61-058 Batch A pivoted to multi-source pinned anchors: Ladson 1988 NASA TM-4074 (NTRS archive ID 19880019495) for Cl/Cd, Abbott 1959 + Gregory 1970 for Cp shape

## FM-NACA-2: Cp magnitude attenuation from cell-band sampling (active design choice)

- **Tag**: `extractor_geometry_systematically_attenuates_signal`
- **Trigger**: DEC-V61-044 added in-solver `airfoilSurface` FO writing `p_aerofoil.raw`. `src/airfoil_surface_sampler.py` reads + computes Cp via `cellPoint` interpolation of a near-surface band of cell centres. Reference Cp values are exact-surface from Abbott 1959 / Gregory 1970.
- **Symptom**: Cp magnitudes systematically attenuated 30-50% vs exact-surface gold
- **Detected**: DEC-EX-A (2026-04-18) PASS_WITH_DEVIATIONS finding
- **Status**: ACCEPTED design — profile gate retains 20% tolerance for QUALITATIVE shape match; magnitude reproduction deferred to a future snappyHexMesh body-fitted DEC. The 30-50% attenuation is well-characterized and absorbed.

## FM-NACA-3: TE Cp anchor inconsistent with Kutta condition (retired)

- **Tag**: `gold_anchor_inconsistent_with_physics`
- **Trigger**: pre-DEC-V61-058 v1 had Cp=0.2 at x/c=1.0 (TE). Kutta condition for inviscid limit gives Cp_TE ≈ 0; the cell-band sampler is degenerate at zero-thickness anyway.
- **Symptom**: extractor either failed silently at TE or returned a coarse-mesh-dependent value with no physical meaning
- **Detected**: DEC-V61-058 Codex F4 round 1
- **Status**: RESOLVED — Codex F4 dropped the x/c=1.0 anchor; added x/c=0.5 as Abbott Fig. 4-7 cross-check anchor instead

## FM-NACA-4: Cl@α=0° SNR trap (retired from gate set)

- **Tag**: `gold_zero_value_numerical_noise_snr_trap`
- **Trigger**: gold = 0 EXACTLY for symmetric airfoil at α=0° by symmetry. Comparator's relative-error mode is undefined at gold=0; falls back to absolute-error mode.
- **Symptom**: any non-zero Cl numerical noise produces "infinite" relative error or comparator zero-handling artifact (per RETRO-V61-050)
- **Detected**: DEC-V61-058 risk_flags.lift_signal_at_alpha_zero_snr_trap
- **Status**: RESOLVED — DEC-V61-058 §3 (Codex F1+Q4) excludes Cl@α=0° from the HARD gate set. Comparator zero-reference handling (gold_standard_comparator.py:68 + result_comparator.py:203) auto-flips to absolute-error mode. Cl@α=0° remains as SANITY_CHECK with absolute band `|Cl| < 0.005`, surfaced in UI but excluded from gate verdict.

## FM-NACA-5: Stateful α persistence across calls (Codex F1)

- **Tag**: `parameter_resolution_stale_state`
- **Trigger**: pre-Codex-F1 implementation could persist α from a previous task_spec call
- **Symptom**: subsequent runs at different α might pick up stale rotation
- **Detected**: DEC-V61-058 Codex F1 round 1
- **Status**: RESOLVED — commit a00ff88 ensures α resolution is per-call-fresh (no stateful persistence)

## FM-NACA-6: y+_max threshold scope creep (Codex F5)

- **Tag**: `provisional_observable_promoted_too_aggressively`
- **Trigger**: initial DEC-V61-058 plan had y+_max as a HARD-GATED observable
- **Symptom**: y+ band [11, 500] is mesh-dependent; HARD-gating would couple solver verdict to mesh-quality diagnostics
- **Detected**: DEC-V61-058 Codex F5 round 1
- **Status**: RESOLVED — Codex F5 ruling demoted y+_max to PROVISIONAL_ADVISORY: y+ in [11, 500] → ADVISORY_PASS; outside [11, 500] → ADVISORY_FLAG (does NOT fail case); outside [5, 1000] → ADVISORY_BLOCK (rendered RED, but case verdict still uses HARD gates only)

## FM-NACA-7: Same-extraction-path family inflation (Codex F1)

- **Tag**: `independent_observable_family_double_counts_same_run`
- **Trigger**: initial plan had Cl@α=0°, Cl@α=4°, Cl@α=8° as three independent HARD gates
- **Symptom**: all three are extracted from the same `forceCoeffs1/0/coefficient.dat` per-α run; treating them as independent inflates the "family pass count"
- **Detected**: DEC-V61-058 Codex F1 ruling
- **Status**: RESOLVED — only Cl@α=8° is HEADLINE_PRIMARY_SCALAR; Cl@α=0° is SANITY_CHECK; Cl@α=4° is HELPER_FOR_SLOPE_FIT. Slope itself uses the 3-point fit as a separate QUALITATIVE_GATE.

## FM-NACA-8: y+ first-cell math error (Codex F3)

- **Tag**: `wall_distance_estimate_arithmetic_error`
- **Trigger**: initial plan had a y+_min calculation with the wrong dz_min basis
- **Symptom**: estimated y+ outside the wall-function high-Re branch [11, 500], causing alarm
- **Detected**: DEC-V61-058 Codex F3 round 1
- **Status**: RESOLVED — corrected math: u_τ = U_inf·sqrt(Cf/2) ≈ 0.0447, dz_min = z_far/(n_z·expansion) = 2.0/(80·40) = 6.25e-4, y+_min ≈ 84 — well inside [11, 500] for α=0 mid-chord

## Pattern themes

- **unreliable_paper_provenance**: DOI resolves inconsistently or paper not findable. P4 should require gold values to declare `archive_id` (NTRS, DOI, ISBN+page) and link-rot-check during ingest.
- **extractor_geometry_systematically_attenuates_signal**: known systematic measurement bias accepted via wider tolerance. Recurs at LDC ψ noise floor demotion. The **good** pattern when bias is well-characterized (30-50% attenuation here is documented + qualitative gate). P4 should support `extraction_bias: { type: 'systematic_attenuation', factor: 0.5, source: 'cell_band_vs_exact_surface' }`.
- **gold_zero_value_numerical_noise_snr_trap**: relative-error tolerance undefined at gold=0; comparator must auto-flip to absolute-error mode AND the observable should be SANITY_CHECK not HARD_GATED. Recurs anywhere there's an exact-zero gold (symmetry, conservation laws). P4 should encode `comparator_mode: { relative | absolute_when_gold_is_exact_zero }`.
- **provisional_observable_promoted_too_aggressively**: mesh-quality diagnostics treated as physics gates. Suggests P4 needs role taxonomy: HARD_GATED | SAME_SURFACE_CROSS_CHECK | INDEPENDENT_CROSS_CHECK | SAME_RUN_CROSS_CHECK | PROFILE_GATE | QUALITATIVE_GATE | PROVISIONAL_ADVISORY | SANITY_CHECK | HELPER. (DEC-V61-058 §3 already implements this; P4 should adopt as schema.)
- **independent_observable_family_double_counts_same_run**: pass-fraction inflation when N observables share extraction path. P4 should encode `extraction_family` as a graph and require independence assertion.
