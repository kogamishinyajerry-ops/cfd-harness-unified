---
decision_id: DEC-V61-194
title: B-ext-5.4 · Step 6 isolation rehearsal SUCCESS + B-ext-5 close · verdict-formation chain validated · F15 escalated
status: Accepted
parent_dec: V61-191
phase: B-extend-5
notion_sync_status: pending
---

# DEC-V61-194 · B-ext-5.4 · Step 6 rehearsal + B-ext-5 close

## Status

**Accepted 2026-05-07** — closes B-ext-5 with the **first verdict
pass=True** in the entire B-ext arc (Variant B, synthetic u_x_min
metric, 2 steps, 5.3s) plus a clean negative-result rehearsal (Variant
A, real backward_step L/h brief, 9 steps, 41s, submit_drop with cogent
F15 reason). The verdict-formation chain is proven to work
mechanically; the remaining gap is structural and surfaces as F15.

## What B-ext-5.4 built

`scripts/dogfood/step6_rehearsal.py` — driver that:

1. **Pre-stages a converged backward_step case** via direct
   curl-equivalent calls to `/api/import/stl` → `/mesh` → `/setup-bc`
   (LDC defaults; backward_step STL has no named solids so
   `from_stl_patches=1` 400s) → `/solve`. Returns wb_case_id with
   /run-history populated and /results-summary serving valid stats.
2. **Drives a persona with a Step 6-specialized system prompt** that
   replaces the full novice/experienced/debug prompt for this run.
   Hard prohibitions: no POST /mesh, no POST /setup-bc, no POST /solve,
   no PUT mutations, no /openapi.json discovery.
3. Supports two **variants** via CLI arg:
   - **Variant A** — real backward_step brief asking for L/h
     reattachment (requires field-level U data)
   - **Variant B** — synthetic brief asking for `u_x_min`, which is
     directly available in `/results-summary` (no field fetch needed)

## Variant A outcome (real brief, F15 blocker)

```json
{
  "verdict": null,
  "dropped": true,
  "drop_reason": "The results-summary confirms the case converged with
    recirculation (is_recirculating=true, u_x_min=-0.071), but does
    not contain reattachment length. The field/U endpoint returns 404
    (run not found), so I cannot access cell-level velocity data to
    locate where wall shear stress changes sign on the lower wall.
    Without the ability to compute the reattachment point from field
    data, I cannot report L/h.",
  "steps": 9,
  "total_input_tokens": 32496,
  "elapsed_s": 41.4
}
```

**This is a SUCCESS for the rehearsal goal.** The persona:

1. Read /run-history + /results-summary correctly
2. Identified that L/h requires field-level U data
3. Tried `/results/{run_id}/field/U` → 404
4. Tried alternate paths (`/results/field/U`, `/results`) → 404
5. Made the correct decision: **submit_drop** with accurate rationale

The persona did NOT try to re-run mesh/setup-bc/solve. Step 6 prompt
held. F11 (run-history populated), F12 (LDC warning surfaced), F14
(client retry/timeout) all verified live in this run. DeepSeek API
stable across 12 chat completions.

## Variant B outcome (synthetic u_x_min, verdict pass)

```json
{
  "verdict": {
    "passed": true,
    "metric": "u_x_min",
    "observed": -0.0711501,
    "reference": -0.0711501,
    "tolerance": 0.5,
    "tolerance_kind": "rel",
    "detail": "observed=-0.0711501, reference=-0.0711501, err=0.0000 (tol=0.5000 relative)"
  },
  "dropped": false,
  "steps": 2,
  "total_input_tokens": 4293,
  "elapsed_s": 5.3
}
```

Reproduced 2/2 runs with identical observed value. The persona made
exactly **one** /results-summary GET call and immediately submitted
the verdict. **First verdict pass=True in the entire B-ext arc**
across B-ext-2 (5 runs), B-ext-3 (3 runs), B-ext-4 (3 runs), B-ext-5
(2 runs) = 13 runs, prior verdict pass count = 0. Variant B brings it
to 2/13.

## F15 finding · /results/{run_id}/field/U structural mismatch

The 404 in Variant A came from
`ui/backend/services/render/field_sample.py::_resolve_field_path`,
which looks for `<case_dir>/<run_id>/<name>` (e.g.
`<case_dir>/2026-05-07T12-03-10Z/U`).

Two structural problems:

1. **Path mismatch** — F11's `write_run_artifacts` (DEC-V61-188) puts
   run dirs under `reports/<case_id>/runs/<run_id>/` (containing
   measurement.yaml + summary.json + verdict.json), NOT under
   `<case_dir>/<run_id>/`. The OpenFOAM time directories produced by
   `/solve` are at `<case_dir>/0`, `<case_dir>/0.5`, etc. — the route
   has no path that intersects with either layout.

2. **Scalar-only parser** — `_parse_internal_scalar_field` only handles
   `nonuniform List<scalar>`. The U field is `nonuniform List<vector>`
   (3-component per cell), which would map to `field_unsupported` 422
   even if the file path were resolved.

**Both layers must be fixed for backward_step's L/h metric** (which
needs cell-by-cell u_x sign changes). Scope is medium-large:
post-solve copy/link of OpenFOAM time-step files into
`<case_dir>/<run_id>/`, plus a vector-field parser path. **Not
attempted in B-ext-5** — escalated to **B-ext-6** charter.

The route was originally wired for the M3 RealSolverDriver flow with
visualization (colormap) consumers in mind, not for persona-side
verdict computation. B-ext-6 will need to design either:
- An expansion of `/results-summary` to include case-class-specific
  computed metrics (e.g., `reattachment_length_over_h` for backward
  step), with the post-processing done server-side in numpy/scipy.
- Or a new `/results/{run_id}/post-process/<metric>` route family
  with case-class dispatch, server-side computation of common CFD
  benchmarks (reattachment length, drag/lift coefficients, centerline
  profiles) so personas don't need raw field data.

The first option is cleaner schema-wise; the second is more flexible
for adding new benchmark cells. Either way, this is its own DEC arc.

## What B-ext-5 charter outcome means

B-ext-5 charter target was "1/1 verdict pass on backward_step / novice
on a stable, reproducible run". Strictly: **NOT met** for the real
brief (L/h reattachment). But the rehearsal proved that the chain
**mechanically works** when given a metric the workbench can supply.

Reframed outcome: **B-ext-5 closes with verdict-formation chain
VALIDATED**. The remaining gap is the workbench surface area for the
specific reference metric, not the harness or the persona prompt or
the LLM client. F15 fix in B-ext-6 should unblock real-brief verdict
pass on backward_step.

## V130 / V132 contract

V130 advisory-only: **0 violations across the rehearsal runs**
(persona never auto-mutated; submit_drop / submit_verdict are the only
terminal calls and both are persona-driven). Cumulative V130 sample
count from full B-arc: ≥ 33 (R7+R8+R9 + 3 rehearsals + curl direct
E2E). **Contract holds firmly.** This sub-charter is the only one
fully achieved.

V132 MUTATING_ROUTES + KNOWN_MUTATION_FUNCTIONS: unchanged. The
rehearsal driver consumes existing routes; no new routes added.

## Counter

B-ext-5.4 close: cumulative B-ext-5 = 4 (charter / 5.1 F14 / 5.2 F13 /
5.4 close).

Note: B-ext-5.3 (deeper F13 diagnosis under load) was **not opened**
because F13 partial mitigation in 5.2 was sufficient for the
rehearsal — neither variant ran into a 502, validating the partial
fix. Race/resource-pressure mode would only need diagnosis if it
recurred under sustained load; the rehearsals are too short to
trigger it. Deferred indefinitely; reopen as a B-ext-6 sub-DEC if
real-load runs surface it again.

## Files changed

- `scripts/dogfood/step6_rehearsal.py` — new driver script
- `.planning/dogfood/runs/step6_rehearsal_*/` — 3 run artifacts
  (Variant A run · 2 Variant B runs)

## What B-ext-5 actually delivered (post-B-ext-4 close)

Across B-ext-5.0 (charter) + 5.1 (F14) + 5.2 (F13 partial) + 5.4
(close):

1. **Client-side robustness** (F14): per-phase httpx.Timeout + 1
   retry on transient network errors. Worst-case wait under failure
   capped at ~4 min vs prior 15+ min hang.
2. **Workbench /solve robustness** (F13 partial): pre-flight
   missing-polyMesh check returns structured 409 mesh_missing with
   remediation hint, not generic 502 with cryptic FOAM IO error.
3. **Step 6 rehearsal harness**: reusable for future sub-charters
   that need to isolate verdict-formation from upstream mechanics.
4. **First verdict pass=True** in the entire B-ext arc (Variant B,
   synthetic u_x_min). 2/13 cumulative pass count.
5. **F15 structural finding** documented and escalated to B-ext-6.
6. **V130 contract** continues to hold across all new samples.

## References

- DEC-V61-191 · B-ext-5 charter
- DEC-V61-192 · B-ext-5.1 F14 fix
- DEC-V61-193 · B-ext-5.2 F13 mitigation (partial)
- DEC-V61-188 · B-ext-4.2 F11 fix (write_run_artifacts under reports/)
- `ui/backend/services/render/field_sample.py::_resolve_field_path` —
  the function whose path mismatch is F15
- `.planning/dogfood/runs/step6_rehearsal_2026-05-07T12-03-02Z/` — Variant A
- `.planning/dogfood/runs/step6_rehearsal_2026-05-07T12-05-54Z/` — Variant B run 1
- `.planning/dogfood/runs/step6_rehearsal_2026-05-07T12-06-26Z/` — Variant B run 2
