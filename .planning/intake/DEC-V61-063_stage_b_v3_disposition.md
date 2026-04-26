# DEC-V61-063 Stage B v3 Disposition

**Run:** 2026-04-25 · commit `66f0e42` · 14.5s wall · solver_success=True
**Verdict:** FAIL (`comparator_passed=false`) — 4/4 HARD_GATED observables outside 10% relative tolerance.
**Strategic decision:** **Accept FAIL as the genuine Stage B outcome.** The new V61-063 gates correctly reject the run because the physics deviation is real and outside tolerance. Further iteration on Stage B inside DEC-V61-063 would constitute scope creep.

## Run summary

| Field | Value |
|---|---|
| commit | `66f0e42` (Stage A.7 laminar case-gen) |
| solver_success | `True` ✓ |
| comparator_passed | `False` (per gold tolerance, expected) |
| cf_spalding_fallback_count | `0` ✓ (laminar contract honored) |
| cf_sign_flip_activated | `False` ✓ |
| cf_x_profile_n_samples | 4 ✓ |
| cf_blasius_invariant_rel_spread | 0.037 ✓ (well within 5% audit guideline) |

## Per-observable rel_error

| Observable | Measured | Reference | rel_error |
|---|---|---|---|
| cf_skin_friction (back-compat scalar) | 0.00465 | 0.00420 | 10.7% |
| cf_x_profile_points (max-over-profile) | n/a | n/a | 14.5% (worst at x=1.0) |
| cf_blasius_invariant_mean_K | 0.736 | 0.664 | 10.9% |
| delta_99_x_profile (max-over-profile) | n/a | n/a | 30.1% (BL too thin) |

Per-x K_x: 0.698 → 0.735 → 0.751 → 0.760 (monotonic increasing).
This pattern (Cf over-predicted, increasingly so with x; δ_99 under-predicted)
is the canonical signature of a boundary layer that hasn't fully developed
into Blasius similarity.

## Root cause analysis

### Direct evidence (proven root cause)

**Top wall is no-slip, not freestream.** `_generate_steady_internal_flow`
emits a channel domain with `walls` patch covering BOTH upper AND lower
walls (per the 0/U BC at src/foam_agent_adapter.py:4510:
`walls { type noSlip }`, and the matching geometry at line 4032). This
is correct for internal channel flow but WRONG for the gold's external
ZPG flat-plate flow per `knowledge/gold_standards/turbulent_flat_plate.yaml:15`
("zero-pressure-gradient external flow"). Two no-slip walls in a finite
channel mechanically constrain the core flow and break Blasius
similarity at the lower wall.

### Likely contributor (inferred, not A/B-tested)

**No leading-edge development.** Inlet BC is uniform U=(1, 0, 0) with no
inflow boundary-layer profile. Blasius assumes a sharp leading edge at
x=0, with the BL growing from there. The numerical BL likely needs an
inflow buffer (~10×δ_99) to develop into similarity, while the
measurement window starts at x=0.25 — possibly too close to the inlet.
This is a plausible contributor but has not been confirmed by an A/B
rerun (e.g., `_FLAT_PLATE_CF_X_TARGETS` shifted to x ∈ {0.5, 1.0, 1.5,
2.0}). It would be empirically separable from the top-wall mismatch in
V61-064.

### Scope rationale

The V61-063 intake §3a (`in_scope` block at intake YAML line 136)
defines this DEC's surgical envelope as extractor + comparator work
(multi-x sampling, secondary observables module, gold YAML expansion,
adapter contract field, comparator-gates wiring, alias parity). A
top-wall/freestream BC fix is a structural execution-plane change to
the case generator, not extractor/comparator work — it belongs in a
new DEC (V61-064 proposed below) rather than scope-creeping V61-063.
Intake §3b explicitly excludes "AMR/GCI study" from V61-063 but does
NOT explicitly enumerate domain-BC fixes; the boundary-fix queueing
decision rests on the §3a envelope, not on §3b.

## Why the F1 gate is working correctly

Pre-A.5 (canonical_K hard-gated): the comparator would PASS this run
because cf_blasius_invariant_canonical_K is constant 0.664 — a tautology
gate that ignores per-x deviations. Codex round 1 reproduced exactly
this false-pass on a synthetic emit.

Post-A.5 (mean_K hard-gated): the comparator correctly FAILS this run
because the measured mean_K=0.736 is 10.9% off the Blasius reference,
indicating the similarity solution is not being recovered. Stage B v3
provides **real-world evidence** that the F1 fix has the intended teeth.

## Why this is success, not failure

DEC-V61-063 charter: add Type II multi-dim validation observables for
turbulent_flat_plate. Stage A delivered the observables + comparator
wiring + gates; Codex round 2 APPROVED the code as correct.

Stage B v3 demonstrates:
1. The gates RUN against live OpenFOAM output (not synthetic data).
2. The gates produce DIFFERENTIATED verdicts per observable (not just a
   single FAIL flag).
3. The gates DETECT real physics deviation (mesh + domain limitations
   that were silently passing before).
4. The audit trail (cf_extractor_path, cf_enrichment_path,
   cf_spalding_fallback_*, cf_sign_flip_*) is populated end-to-end.

The new V61-063 contract is **working as designed**.

## What gets queued as separate DEC(s)

- **DEC-V61-064 (proposed): Flat-plate domain fix.** Differentiate
  flat-plate generator (top wall = symmetry/freestream, x_origin offset)
  from channel generator. May reuse `_generate_steady_internal_flow` with
  a `flat_plate_mode=True` switch or split into `_generate_flat_plate`.
  Acceptance: cf_blasius_invariant_mean_K rel_error <10% on the same mesh.
- **DEC-V61-065 (proposed, optional): Mesh refinement / GCI study.** If
  V61-064 closes the domain issue but residual mesh truncation keeps
  cf_skin_friction ≥10% rel_error, ramp ncy to 160 or 320 with a Richardson
  extrapolation cross-check.

## Disposition for Codex round 3

Codex R3 review focus:
- A.6 dispatch fix: whitelist-first turbulence selection at SIMPLE_GRID
  branch. Verbatim mirror of cylinder R1 fix.
- A.7 laminar refactor: `_generate_steady_internal_flow` laminar branch
  for turbulenceProperties + fvSolution + early-return after 0/p so
  turbulent-only fields are skipped.
- Stage B v3 acceptance: solver convergence + gates working as designed
  + 4-way HARD_GATED FAIL is the correct outcome under the current
  domain.
- Closeout disposition: this document.

R3 is NOT being asked to greenlight Stage B PASS — it's being asked to
APPROVE the **disposition** that V61-063 closes with FAIL on Stage B as
the genuine outcome and queues V61-064/065 for the structural fixes.
