# P4 KNOWLEDGE_OBJECT_MODEL · failure-pattern schema input

> Synthesis of 10 per-case `failure_notes.md` files into recurring pattern themes.
> GOV-1 v0.5 deliverable · DEC-V61-080 closure follow-on · 2026-04-26
>
> **Purpose**: explicit input material for P4 schema design. Each pattern below is observed in ≥2 cases (with case-anchor references), giving P4 designers concrete failure modes to encode as schema invariants rather than designing in the abstract.

This is a **proposal-grade synthesis**, not a binding specification. P4 schema design owns final field naming, data types, and gate semantics. The patterns below are the empirical evidence that motivates the schema.

## Pattern catalog

### P-1 · `regime_mismatch_gold_value`

**What**: Gold value derived from a correlation valid in regime A is applied to a case configured in regime B. Comparator math runs; physics meaning is wrong.

**Observed in**:
- `turbulent_flat_plate` FM-TFP-1 (retired): pre-DEC-V61-006 gold 0.0076 was Spalding turbulent fit applied to Re_x=25000 laminar regime
- `differential_heated_cavity` FM-DHC-1 (retired): pre-DEC-V61-006 gold Nu=30 at Ra=10¹⁰ was turbulent-regime claim that the laminar adapter could not reproduce on the available mesh
- `plane_channel_flow` FM-PCF-1 (active): laminar icoFoam adapter cannot reproduce Kim 1987 / Moser 1999 turbulent DNS u⁺ profile

**Proposed P4 schema field**:
```yaml
gold_value:
  value: 8.8
  source: de_vahl_davis_1983_table_iv
  valid_regime:
    Re_min: null  # natural convection
    Re_max: null
    Ra_range: [1e5, 1e7]   # de Vahl Davis Table IV applies in this band
    Pr_range: [0.7, 0.72]
    geometry_topology: square_cavity_AR_1
    flow_class: NATURAL_CONVECTION_LAMINAR
```
**Proposed gate**: ingest validation FAILs if `task_spec.regime ∉ gold_value.valid_regime`.

---

### P-2 · `geometry_topology_silent_simplification`

**What**: Adapter generates a topologically simpler geometry than the case label claims (planar instead of axisymmetric, flat-channel instead of step, rectangular instead of pipe). High-level metadata claims geometry G but mesh is G'.

**Observed in**:
- `backward_facing_step` FM-BFS-1 (retired): pre-DEC-V61-052 single-block adapter produced flat channel with no step, while YAML claimed expansion ratio 1.125
- `duct_flow` FM-DCT-1 (retired): pre-DEC-V61-011 case_id was `fully_developed_pipe` but `SIMPLE_GRID` adapter emitted rectangular duct
- `impinging_jet` FM-IJ-1 (active): adapter declares axis patch as `empty` (2D planar), not `wedge` (true axisymmetric) — silent geometry simplification

**Proposed P4 schema field**:
```yaml
case_profile:
  declared_geometry_topology: AXISYMMETRIC_WEDGE
  geometry_assertion:
    callable: validators.assert_topology_matches_mesh
    expected_patches:
      axis: wedge
      front: empty       # acceptable for thin-slab cases only
      back: empty
    rejected_patches:
      axis: empty        # would indicate planar slice
```
**Proposed gate**: pre-solver gate runs `geometry_assertion.callable` against the actual generated mesh; FAILs if patches don't match.

---

### P-3 · `extractor_emits_wrong_observable_under_correct_name`

**What**: Extractor produces a real number from real measurements, but the value's physical meaning ≠ the observable's declared meaning. Comparator labels it correctly; the value itself is wrong-quantity.

**Observed in**:
- `circular_cylinder_wake` FM-CCW-5 (in flight): St falls back to `U_max_approx` (a velocity surrogate) when FFT finds no dominant peak; comparator surfaces "St" verdict against a non-frequency value
- `impinging_jet` FM-IJ-3 (resolved-but-pattern-defining): historical fixture had `ref_value=0.0042` labeled "nusselt_number" but populated by Cf extraction

**Proposed P4 schema field**:
```yaml
observable:
  name: nusselt_number
  expected_dimensions: dimensionless
  expected_quantity_id: NUSSELT          # canonical taxonomy ID
extractor:
  emits_quantity_id: NUSSELT             # extractor self-declares what it produces
  fallback_chain: []                     # explicit empty list — fallback to a different quantity_id is FORBIDDEN
```
**Proposed gate**: comparator FAILs (does NOT fall back to surrogate) when `extractor.emits_quantity_id ≠ observable.expected_quantity_id`.

---

### P-4 · `extraction_noise_floor_dominated`

**What**: Gold magnitude is many orders of magnitude smaller than the extractor's intrinsic numerical noise floor. The "match within tolerance" can be coincidence of noise rather than physics validation.

**Observed in**:
- `lid_driven_cavity` FM-LDC-4 (acknowledged): secondary vortex BL/BR have ψ_gold ~1e-6 / ~1e-5, but trapezoidal ∫ U_x dy' wall-closure residual is ~3.4e-3 — gold is 270-2000× below noise floor
- `differential_heated_cavity` FM-DHC-3 (acknowledged): ψ_max trapezoidal reconstruction has closure residual that demotes the observable from HARD_GATED to PROVISIONAL_ADVISORY when ≥ 1% of gold

**Proposed P4 schema field**:
```yaml
observable:
  name: secondary_vortices.psi
  expected_value_magnitude: 1e-6
  noise_floor_estimator:
    callable: extractors.measure_psi_wall_closure_residual
    fail_if: estimated_floor / abs(expected_value_magnitude) > 0.01
  noise_floor_action: DEMOTE_TO_PROVISIONAL_ADVISORY   # or FAIL_INGEST, or WARN_BUT_KEEP_HARD
```
**Proposed gate**: at extraction time, run `noise_floor_estimator`; if it exceeds the threshold, observable's role auto-demotes from `HARD_GATED` to `PROVISIONAL_ADVISORY` for that run only. The DHC ψ_max already implements this pattern as a one-off; P4 should formalize it.

---

### P-5 · `gold_value_provisional_pending_paper_reread`

**What**: Honest "we don't know if the gold value is right". Audit flagged a numerical discrepancy too large to fix without re-reading the cited paper.

**Observed in**:
- `impinging_jet` FM-IJ-5 (HOLD): Nu(r/d=0)=25 vs Behnad 2013 ~110-130 (4-5× discrepancy)
- `rayleigh_benard_convection` FM-RBC-2 (HOLD): Chaivat correlation recompute 9.4 vs stored 10.5 (11.5% off — within tolerance but suspicious)

**Proposed P4 schema field**:
```yaml
gold_value:
  value: 25.0
  status: PROVISIONAL          # one of: VERIFIED, PROVISIONAL, HOLD, RETIRED
  status_evidence: "Gate Q-new Case 9 audit 2026-04-20: Nu peak literature ~110-130 vs stored 25; paper re-read pending"
  status_blocks_verdict: true  # comparator suppresses verdict on PROVISIONAL/HOLD observables
```
**Proposed gate**: comparator runs the comparison and reports the value, but **suppresses the pass/fail verdict** when `status ∈ {PROVISIONAL, HOLD}`. UI surfaces a banner explaining why.

---

### P-6 · `gold_zero_value_numerical_noise_snr_trap`

**What**: Relative-error tolerance is mathematically undefined when gold value is exactly zero. Comparator falls back to absolute-error mode, but the observable has no physical content (e.g., Cl@α=0° for symmetric airfoil = 0 by symmetry). HARD-gating is meaningless because any solver noise produces "infinite" relative error.

**Observed in**:
- `naca0012_airfoil` FM-NACA-4 (resolved as SANITY_CHECK): Cl@α=0° gold = 0 exactly by symmetry; SNR trap

**Proposed P4 schema field**:
```yaml
observable:
  expected_value: 0.0
  expected_value_origin: SYMMETRY      # one of: MEASURED, ANALYTIC, SYMMETRY, CONSERVATION_LAW
  comparator_mode:
    when_gold_nonzero: relative
    when_gold_exact_zero: absolute_with_band   # |measured| < band
    absolute_band: 0.005
  role: SANITY_CHECK                   # excluded from HARD gate set
```
**Proposed gate**: ingest forbids `role: HARD_GATED` when `expected_value_origin ∈ {SYMMETRY, CONSERVATION_LAW}` AND `expected_value == 0`.

---

### P-7 · `verdict_pass_does_not_imply_physics_correct`

**What**: Composite of P-1 + P-3 + P-4 — comparator path runs end-to-end and reports PASS, but physics audit reveals the verdict is meaningless because the underlying configuration is incompatible with the gold's regime.

**Observed in**:
- `plane_channel_flow` FM-PCF-5 (active, canonical example): ATTEST_PASS via comparator-path artifact while physics audit says FAIL; the laminar parabolic profile and turbulent log-law cross at intermediate y⁺ regions, allowing accidental tolerance pass

**Proposed P4 schema architecture**:
- Separate `comparator_verdict` (numerical match within tolerance) from `physics_validity_verdict` (regime + topology + extractor preconditions all hold)
- Final case verdict = `comparator_verdict AND physics_validity_verdict`; either alone is insufficient
- UI must surface both verdicts (not collapse them into a single ATTEST_PASS / ATTEST_FAIL)

---

### P-8 · `whitelist_field_silently_ignored`

**What**: High-level case metadata is parsed but the adapter's per-case path makes its own decision, ignoring the field.

**Observed in**:
- `circular_cylinder_wake` FM-CCW-1 (in flight): `whitelist.yaml` declares `turbulence_model: laminar` per DEC-V61-005 but adapter's `_turbulence_model_for_solver` returns `kOmegaSST` for `BODY_IN_CHANNEL` regardless

**Proposed P4 schema field** (run-manifest invariant, not case-profile field):
```yaml
run_manifest:
  effective:
    solver: simpleFoam
    turbulence_model: kOmegaSST           # what the adapter actually instantiated
  declared:
    solver: simpleFoam
    turbulence_model: laminar             # what task_spec / whitelist declared
  invariant_check:
    must_match: [solver, turbulence_model]
    on_mismatch: FAIL_AT_GATE             # or WARN_AND_LOG
```
**Proposed gate**: post-solver gate compares `effective` vs `declared`; FAILs if any `must_match` field differs without explicit override.

---

### P-9 · `provisional_observable_promoted_too_aggressively`

**What**: Mesh-quality diagnostics or convergence indicators treated as physics gates. y⁺ band, residual residue, oscillation amplitude — these can FLAG mesh issues but should not produce case-level FAIL verdicts on their own.

**Observed in**:
- `naca0012_airfoil` FM-NACA-6 (resolved via Codex F5): y⁺_max promotion to HARD_GATED was rolled back to PROVISIONAL_ADVISORY

**Proposed P4 role taxonomy** (already partially implemented in DEC-V61-058 §3):
```yaml
role: HARD_GATED                          # contributes to case-level pass/fail
role: SAME_SURFACE_CROSS_CHECK            # HARD_GATED but extracted from same patch as headline
role: INDEPENDENT_CROSS_CHECK             # HARD_GATED, independent extraction path
role: SAME_RUN_CROSS_CHECK                # HARD_GATED, same physical run as headline
role: PROFILE_GATE                        # qualitative shape match
role: QUALITATIVE_GATE                    # linearity, monotonicity, etc.
role: PROVISIONAL_ADVISORY                # NOT counted toward verdict; surfaces in UI
role: SANITY_CHECK                        # NEVER counted; passive surface only
role: HELPER_FOR_SLOPE_FIT                # input to a derived observable; NOT a gate
```
**Proposed P4 schema rule**: ingest validation enforces taxonomy; only `HARD_GATED*` and `PROFILE_GATE`/`QUALITATIVE_GATE` count toward verdict.

---

### P-10 · `independent_observable_family_double_counts_same_run`

**What**: Pass-fraction inflation when N "independent" observables share extraction path. e.g., Cl@α=0°, Cl@α=4°, Cl@α=8° all extracted from the same `forceCoeffs1/0/coefficient.dat` per-α run; treating as independent inflates family pass count.

**Observed in**:
- `naca0012_airfoil` FM-NACA-7 (resolved via Codex F1): demoted Cl@α=0° to SANITY_CHECK; Cl@α=4° to HELPER_FOR_SLOPE_FIT; only Cl@α=8° is HEADLINE

**Proposed P4 schema field**:
```yaml
observable:
  extraction_family: forceCoeffs_FO_aerofoil_patch
  extraction_independence_class: SAME_RUN     # same physical solver run + same FO file
gate_aggregation_rule:
  per_extraction_family_max_count: 1          # only 1 HARD_GATED observable per family
  per_extraction_independence_class_count:
    SAME_RUN: 1
    INDEPENDENT_RUN: unlimited
```
**Proposed gate**: ingest FAILs if a single `extraction_family` has >1 `HARD_GATED` observable, unless explicitly justified with a `family_independence_evidence` field.

---

### P-11 · `key_name_misleads_extractor_consumers`

**What**: Backward-compat key names whose semantics drifted. Same key represents different quantities in different generations of the gold YAML.

**Observed in**:
- `circular_cylinder_wake` FM-CCW-4 (resolved via doc + extractor self-naming): gold key `u_Uinf` historically meant raw u/U_inf but values 0.83→0.35 are actually wake **deficit**

**Proposed P4 schema field**:
```yaml
observable:
  name: u_mean_centerline
  legacy_aliases:
    - alias: u_Uinf
      meaning_at_alias_creation: "raw u/U_inf"
      current_meaning: "wake deficit (U_inf - u)/U_inf"
      deprecation_date: 2026-04-23
      removal_target_dec: V61-future
```
**Proposed gate**: at YAML-load time, log a warning if any `legacy_aliases` field is encountered. Never silently rename.

---

### P-12 · `unreliable_paper_provenance`

**What**: DOI resolves inconsistently or paper not findable in canonical archives.

**Observed in**:
- `naca0012_airfoil` FM-NACA-1 (resolved via Codex F4 multi-source pivot): pre-V61-058 source "Thomas 1979 / Lada & Gostling 2007" with DOI 10.1017/S0001924000001169 was unreliable

**Proposed P4 schema field**:
```yaml
gold_value:
  source:
    primary_archive_id: NTRS-19880019495         # NTRS, ISBN+page, DOI, ARC-RM-NNNN
    primary_archive_url: https://ntrs.nasa.gov/...
    secondary_archive_id: ARC-RM-3726
    secondary_archive_url: https://naca.cranfield.ac.uk/...
    link_rot_check_date: 2026-04-25
```
**Proposed gate** (CI cron, not ingest): periodic link-rot check on all `primary_archive_url` fields; alert if any return 4xx/5xx.

---

## Pattern coverage matrix

| Pattern | Cases observed | Severity (when active) |
|---|---|---|
| P-1 regime_mismatch_gold | TFP, DHC, PCF | HIGH (verdict meaningless) |
| P-2 geometry_topology_silent | BFS, DCT, IJ | HIGH (mesh ≠ label) |
| P-3 extractor_wrong_observable | CCW, IJ | CRITICAL (verdict on wrong quantity) |
| P-4 noise_floor_dominated | LDC, DHC | MEDIUM (managed via demotion) |
| P-5 provisional_paper_reread | IJ, RBC | MEDIUM (verdict suppressed) |
| P-6 gold_zero_snr_trap | NACA | LOW (resolved by SANITY_CHECK role) |
| P-7 verdict_vs_physics | PCF | CRITICAL (composite hazard) |
| P-8 whitelist_silently_ignored | CCW | HIGH (silent metadata override) |
| P-9 advisory_promoted | NACA | LOW (resolved by Codex F5) |
| P-10 family_double_count | NACA | LOW (resolved by Codex F1) |
| P-11 key_name_drift | CCW | MEDIUM (managed via aliases) |
| P-12 unreliable_provenance | NACA + IJ + RBC + DCT + CCW (5/10) | **HIGH** (escalated 2026-04-26 from LOW; 40% case prevalence — see addendum below) |

### P-12 severity escalation (post-audit, 2026-04-26)

The post-DEC `_research_notes/gov1_paper_reread_2026-04-26.md` full DOI
integrity audit revealed that P-12 prevalence is **4 of 10 active cases (40%)**,
not 1 of 10 as originally framed:

- IJ: DOI resolves to **unrelated paper** (Rao 2013 LES turbines, not Behnia)
- RBC: DOI resolves to **unrelated paper** (Meyer 2006 jet array cooling); author "Chaivat" not findable
- DCT: cited under **wrong journal** (IJHMT vs actual ASME J Fluids Eng)
- CCW: DOI **typo** (`.002421` should be `.002401`)
- NACA: previously resolved via DEC-V61-058 multi-source pivot

The independent audit verdict (RATIFY_WITH_AMENDMENTS, 2026-04-26) confirmed
this escalation as supported by the evidence base. Severity therefore moves
LOW → **HIGH**: P-12 is recurring, latent, and undetectable by reading the
YAML alone. P4 schema MUST encode automated DOI integrity at ingest time.

## Recommended P4 schema architecture (high-level)

> ⚠️ **Non-normative banner (post-audit A3, 2026-04-26)**: The 7-class
> proposal below is **illustrative only**. Final field names, class
> boundaries, and gate semantics are normatively defined by the P4 KOM
> ratification process, NOT by this document. The 12 P-patterns are the
> binding acceptance-test set; the class structure to encode them is
> P4 design freedom. See "§ Mapping to Pivot Charter §3 8-class KOM"
> below for compatibility analysis.

Based on the patterns above, a P4 KNOWLEDGE_OBJECT_MODEL should encode:

1. **`CaseProfile`** (per-case metadata): regime, geometry topology, BC compatibility, validators
2. **`Observable`** (per-quantity gold + tolerance): expected_quantity_id, role taxonomy, comparator_mode, noise_floor_estimator, extraction_family
3. **`GoldValue`** (separated from observable): value, valid_regime, status (VERIFIED/PROVISIONAL/HOLD/RETIRED), source archive IDs
4. **`Extractor`** (extractor declaration): emits_quantity_id, fallback_chain (explicit, no surrogate fallbacks)
5. **`RunManifest`** (per-run effective config): effective vs declared comparison, invariant_check
6. **`FailurePattern`** (case history): failure_mode_tag, trigger, symptom, status, resolution_dec
7. **`Gate`** (verdict aggregation): pass_rule, role taxonomy, extraction_independence_class

The 12 patterns cataloged here are the **acceptance test set** for P4: a P4 schema that cannot encode all 12 patterns is incomplete; a P4 schema that encodes them all gives the harness a real chance to detect each failure mode automatically rather than relying on Codex review or post-hoc audits.

## Mapping to Pivot Charter §3 8-class KOM

The Pivot Charter §3 defines 8 canonical knowledge classes:

> CaseProfile / SolverRecipe / MeshRecipe / BCRecipe / ObservableDefinition /
> FailurePattern / CorrectionPattern / ProvenanceRecord

Mapping the illustrative 7-class proposal above onto the Charter's 8 classes:

| Session B 7-class proposal | Pivot Charter §3 8-class KOM | Mapping notes |
|---|---|---|
| `CaseProfile` | `CaseProfile` | Direct match. Charter's CaseProfile is the umbrella; SolverRecipe / MeshRecipe / BCRecipe are separate but referenced by it. |
| `Observable` | `ObservableDefinition` | Direct match. Charter naming is more explicit. |
| `GoldValue` | (subsumed in `ObservableDefinition`) | Charter does not split GoldValue from Observable. P4 design choice: split (Session B proposal) vs unified (Charter literal). Either is encoder-equivalent for the 12 P-patterns. |
| `Extractor` | (not in Charter's 8) | New class required for P-3 (extractor_emits_wrong_observable). P4 may add it OR encode as a method/field on `ObservableDefinition`. |
| `RunManifest` | `ProvenanceRecord` | Charter naming. RunManifest's "effective vs declared" comparison is part of provenance. |
| `FailurePattern` | `FailurePattern` | Direct match. |
| `Gate` | (not in Charter's 8) | Verdict aggregation rule. P4 may add it as new class OR encode as method on `ProvenanceRecord` / `CaseProfile`. |
| (not in Session B proposal) | `SolverRecipe` | Implicit in Session B's `CaseProfile.solver` field. P4 should hoist to first-class per Charter. |
| (not in Session B proposal) | `MeshRecipe` | Implicit in Session B's `CaseProfile.mesh` field. P4 should hoist to first-class per Charter. |
| (not in Session B proposal) | `BCRecipe` | Implicit in Session B's `CaseProfile.boundary_conditions` field. P4 should hoist to first-class per Charter. |
| (not in Session B proposal) | `CorrectionPattern` | NOT addressed by the 12 P-patterns. Charter pairs FailurePattern with CorrectionPattern; P4 should design them together. |

**Compatibility verdict**: Session B's 7-class proposal is **non-normative**
and partially overlaps with the Charter's 8-class KOM. Three Charter classes
(SolverRecipe, MeshRecipe, BCRecipe) are absent from Session B's proposal
because the 12 P-patterns do not surface failure modes that distinguish
them from `CaseProfile` umbrella fields — but Charter §3 names them as
first-class and P4 should respect that.

One Charter class (`CorrectionPattern`) is **not addressed by the P-pattern
set at all**. This is a real gap: the 12 patterns cover failure detection
but not failure remediation. P4 will need a separate input set for
CorrectionPattern design (e.g., the historical Codex-fix patterns from
Session A's PR 4d/c arc, or the per-case `failure_notes.md` "Status:
RESOLVED" entries which are de facto correction patterns).

Two Session B classes (`Extractor`, `Gate`) are net-new vs the Charter.
Whether P4 adopts them as separate classes, folds them into existing
classes as methods, or rejects them entirely is **P4 design freedom**.
