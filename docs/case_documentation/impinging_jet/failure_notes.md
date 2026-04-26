# Failure notes — impinging_jet

> Free-form yaml/markdown — not a P4 KOM schema artifact.

## FM-IJ-1: Axis patch is `empty`, not `wedge` — silent 2D planar slice

- **Tag**: `geometry_topology_silent_simplification`
- **Trigger**: `foam_agent_adapter.py:5184-5185` declares the axis patch as `empty`. An `empty` patch in OpenFOAM is the 2D simplification (front/back patches on a thin slab), whereas axisymmetric simulation requires a `wedge` patch on the axis with corresponding mesh wedge angle.
- **Symptom**: adapter produces a 2D-planar mesh; whitelist/YAML labels the case "axisymmetric"; mesh and label disagree silently. Stagnation-region dynamics in 2D-planar do **not** match true axisymmetric (azimuthal convergence of streamlines is absent).
- **Detected**: DEC-V61-006 era audit
- **Status**: ACTIVE — fix requires adapter rewrite to emit `wedge` patch + correct mesh wedge angle (typically 5°)

## FM-IJ-2: A4 solver_iteration_cap on p_rgh GAMG

- **Tag**: `pressure_solve_does_not_converge`
- **Trigger**: `src/plane_channel_uplus_emitter.py:53-56,86-88` records p_rgh GAMG repeatedly hitting the 1000-iter cap during simpleFoam steady solve
- **Symptom**: ATTEST_FAIL via A4; no converged steady field from which to extract Nu
- **Root cause** (per gold yaml `physics_precondition` evidence_ref): likely a composite of under-relaxation choice, pressure-velocity coupling settings, thermal-boundary inconsistency, and axis-patch treatment (compounding with FM-IJ-1)
- **Detected**: STATE.md:1286
- **Status**: ACTIVE — root-cause audit deferred to Phase 9 solver-config review

## FM-IJ-3: Cf-as-Nu value leakage (historical, but pattern-defining)

- **Tag**: `extractor_emits_wrong_observable_under_correct_name`
- **Trigger**: historical fixture (STATE.md:455) recorded `ref_value=0.0042 is the adapter's Cf, not the Cooper Nu=25`
- **Symptom**: comparator emitted a value labeled "nusselt_number" but actually populated by skin-friction-coefficient extraction. Honest in the value (it's the real measurement), but the **observable name is wrong**, so verdict is vacuous.
- **Detected**: STATE.md audit
- **Status**: PARTIALLY RESOLVED — DEC-V61-042 landed wall-gradient helper; `src/wall_gradient.py` + `src/cylinder_strouhal_fft.py` provide proper Nu extraction machinery. But extraction is still vacuous until A4 (FM-IJ-2) converges a steady field.

## FM-IJ-4: kEpsilon vs modern impinging-jet standard

- **Tag**: `turbulence_model_legacy_choice`
- **Trigger**: adapter uses `simulationType RAS; RASModel kEpsilon` (chosen "simpler for buoyant flow" per code comment at foam_agent_adapter.py:5295)
- **Symptom**: kEpsilon is a legacy jet-benchmark choice; modern standard for impinging-jet stagnation regions is v2f or k-ω SST (better near-wall behavior). Cooper 1984 itself is experimental, so turbulence-model choice is an engineering call — but the choice is not best-in-class.
- **Detected**: gold yaml `physics_precondition` review
- **Status**: PARTIAL (defensible-but-not-best). Resolution would be a coordinated `task_spec.turbulence_model = 'v2f'` + adapter path update.

## FM-IJ-5: Reference Nu values flagged HOLD (Gate Q-new Case 9)

- **Tag**: `gold_value_provisional_pending_paper_reread`
- **Trigger**: audit flagged Nu@r/d=0 = 25 in gold yaml vs Behnad 2013 ~110-130 — a 4-5× discrepancy too large to edit without reading Behnad et al. 2013 (DOI 10.1016/j.ijheatfluidflow.2013.03.003) directly and confirming whether (Re=10000, h/d=2) was the configuration cited
- **Possible mismatch sources**: confined-jet vs free-jet, different h/d, different Re, different non-dim convention
- **Detected**: Gate Q-new Case 9 audit, 2026-04-20
- **Status**: HOLD per Kogami 2026-04-20 — paper re-read pending. Values currently PROVISIONAL; may change in future DEC.

## FM-IJ-6: Phase regime/PNG mismatch (historical)

- **Tag**: `flow_field_artifact_regime_mismatch`
- **Trigger**: STATE.md:884 — earlier flow-field PNG showed Baughn Re=23750 regime but case was at Re=10000
- **Detected**: pre-Phase-7
- **Status**: LIKELY RESOLVED in recent Phase 7 regeneration pass; pattern to check during reviews

## Pattern themes

- **geometry_topology_silent_simplification**: adapter generates a topologically simpler geometry than the case label claims (planar instead of axisymmetric, flat-channel instead of step, rectangular instead of pipe). Recurs at backward_facing_step, duct_flow. P4 should encode `geometry_topology` and reject mismatches in ingest.
- **extractor_emits_wrong_observable_under_correct_name**: extractor produces a real number from real measurements but the value's physical meaning ≠ the observable's declared meaning. Recurs at circular_cylinder_wake (St → U_max_approx fallback). P4 should require extractors to emit `extracted_quantity_id` (e.g., `Cf`) which the comparator must match against `gold.observable_id` (e.g., `nusselt_number`) before applying the comparison — name mismatch = FAIL, not silent absorb.
- **pressure_solve_does_not_converge**: solver-config bug (under-relaxation, p-v coupling) compounding a geometry bug. Suggests P4 should have a separate `convergence_gate` distinct from `physics_correctness_gate` so failures are diagnosable.
- **gold_value_provisional_pending_paper_reread**: an honest "we don't know if the gold value is right". P4 should support `gold_value_status: { verified | provisional | hold }` so comparator can suppress verdicts on PROVISIONAL/HOLD observables.
