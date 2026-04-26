# Failure notes — plane_channel_flow

> Free-form yaml/markdown — not a P4 KOM schema artifact.
> This is the **canonical case** for "INCOMPATIBLE_WITH_LITERATURE_DISGUISED_AS_COMPATIBLE" — a key motivating example for P4 schema design.

## FM-PCF-1: Laminar solver vs turbulent DNS reference (active)

- **Tag**: `solver_choice_incompatible_with_reference_regime`
- **Trigger**: `foam_agent_adapter.py:3270` configures `application icoFoam` (transient PISO incompressible **laminar** N-S; no turbulence transport equations). At Re_bulk=5600 a laminar N-S solution converges to the parabolic Poiseuille profile, not to a turbulent log-law.
- **Symptom**: Kim 1987 / Moser 1999 reference values (u+=5.4 at y+=5, u+=13.5 at y+=30) are fundamentally inaccessible to this solver path. ATTEST_PASS records as PASS, but the field being compared is a laminar Poiseuille profile mis-presented against a turbulent DNS reference.
- **Detected**: STATE.md:1292-1295 explicit flag, "ATTEST_PASS but Codex physics audit says physically FAIL — those are comparator/extractor bugs"
- **Status**: ACTIVE — no comparator or extractor fix can bridge the gap. Queued for Phase 9 real-solver routing. Two viable resolutions:
  - **(a)** move to pimpleFoam + LES (or RANS k-ω SST with wall functions) at Re_τ=180 — matches the Kim/Moser regime
  - **(b)** demote the case to a **laminar Poiseuille benchmark** at a new gold (e.g., Hagen-Poiseuille u_max/u_bulk = 1.5, parabolic profile) — matches the current adapter
- **Why this matters for P4**: this is the canonical demonstration that "comparator pass" is not the same as "physics correct". It motivates a `regime_assertion` precondition in P4 that fails ingest if `task_spec.solver_regime ≠ gold.required_regime`.

## FM-PCF-2: u_τ derived from laminar wall stress (silent)

- **Tag**: `derived_quantity_uses_wrong_regime_input`
- **Trigger**: `src/plane_channel_uplus_emitter.py:246-287` computes u_τ = √(τ_w/ρ), Re_τ = u_τ·h/ν. The math is correct, but τ_w is the **laminar Poiseuille** wall stress at Re_bulk=5600, not the **turbulent** wall stress at Re_τ=180.
- **Symptom**: emitter produces a numerically self-consistent but physics-wrong u_τ. STATE.md:405 flags: "u_tau = nu·Re_tau/h requires valid DNS setup that current icoFoam laminar adapter doesn't satisfy".
- **Detected**: STATE.md audit, same era as FM-PCF-1
- **Status**: ACTIVE — same root cause as FM-PCF-1; remedied by either solver pivot or gold pivot

## FM-PCF-3: case_info.steady_state mismatch with adapter

- **Tag**: `case_metadata_solver_regime_drift`
- **Trigger**: gold yaml `case_info` declares `steady_state: STEADY`, but adapter uses **transient** PISO icoFoam
- **Symptom**: second-order regime mismatch (laminar-vs-turbulent + steady-vs-transient) compounding the FM-PCF-1 hazard
- **Detected**: STATE.md audit
- **Status**: ACTIVE — would be resolved by a coordinated solver/gold pivot

## FM-PCF-4: y+=100 gold value (22.8) anomalous

- **Tag**: `gold_value_inconsistent_with_correlation`
- **Trigger**: gold reports u+=22.8 at y+=100, but log-law gives u+ = (1/0.41)·ln(100) + 5.2 ≈ 16.4, and Moser Re_τ=180 centerline is u+ ≈ 18.3
- **Symptom**: even under a hypothetical correct turbulent solver, the gold value itself is suspect (~25% off log-law, ~25% off Moser centerline)
- **Detected**: docs/whitelist_audit.md §5.2 audit
- **Status**: QUEUED FOR FOLLOW-UP — out of audit §5.2 scope. The y+=30 anchor was already corrected (14.5 → 13.5) in DEC-V61-006. y+=100 awaits a separate audit pass.

## FM-PCF-5: ATTEST_PASS comparator-path artifact

- **Tag**: `verdict_pass_does_not_imply_physics_correct`
- **Trigger**: comparator extracts u_plus and y_plus from the (laminar) field, applies the (turbulent DNS) gold values, and computes a ratio. The ratio happens to fall within the 5% tolerance for some y+ slices because the laminar parabolic profile and the turbulent log-law cross at intermediate y+ regions.
- **Symptom**: `ATTEST_PASS` recorded; UI shows green; physics audit says FAIL
- **Detected**: STATE.md audit
- **Status**: ACTIVE — partial mitigation via DEC-V61-036c G2 (extractor key-chain widening) which fixes the **extractor reads correct keys**; root cause is FM-PCF-1 solver mismatch

## Pattern themes

- **solver_choice_incompatible_with_reference_regime**: solver path generates regime A; gold values are valid in regime B; comparator math runs but physics meaning is wrong. Most-important pattern for P4 to encode as an explicit `regime_assertion: { solver_supports_regime: [...], gold_validity_regime: [...], assertion: solver_supports_regime ⊇ gold_validity_regime }`.
- **derived_quantity_uses_wrong_regime_input**: a "correct" formula applied to wrong-regime inputs. Recurs at impinging_jet (Cf used as Nu surrogate). P4 should require derived quantities to declare `valid_input_regimes` and inherit validity from inputs.
- **gold_value_inconsistent_with_correlation**: gold value disagrees with the correlation it claims to come from. Recurs at LDC pre-DEC-V61-030 (sign/value error vs Ghia). P4 should require gold values to pass an automated **cross-check** against the cited correlation/table during ingest.
- **verdict_pass_does_not_imply_physics_correct**: composite of all above. The strongest argument for P4 to separate **comparator verdict** from **physics validity** as two distinct gates.
