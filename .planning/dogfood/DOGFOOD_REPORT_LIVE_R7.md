# Dogfood live partial · R7 + direct E2E (B-extend-3)

> Iteration of B-ext-3 charter (DEC-V61-180). 3 DeepSeek-V4-Pro
> personas × 3 cases attempted at max_steps=80, max_input_tokens=3M
> with F10 fix (DEC-V61-182) loaded into workbench. Plus a curl-driven
> direct E2E to validate the F10 fix path independently of persona
> behavior.

## Verdict

**Charter target verdict pass ≥ 1/3 NOT met** (0/3 in R7).
**However**: a curl-driven direct E2E achieved /solve POST 200 with
SolveSummary `converged=True` — the **first ever successful end-to-
end Steps 1-5 sequence in 7 R-iterations** (R1 through R7). F9 + F10
fixes are verified working. The remaining verdict gap is now
persona-side (anti-mesh-cycle prompts + proper from_stl_patches
usage) plus two new workbench findings (F11, F12).

## R7 raw stats

| Cell | Steps | Tokens (in/out) | Wall (s) | Verdict | /solve POSTs | /solve 200 | Cause |
|---|---|---|---|---|---|---|---|
| naca0012/experienced_fluent | 63 | 1.33M / 25k | 773 | None | 0 | 0 | persona stuck in /mesh + /setup-bc cycle (4× /mesh, 2× /setup-bc); SSL EOF on llm_chat at step 63 |
| backward_step/novice | 1 | 0 / 0 | 0.0 | None | 0 | — | DNS resolution failure (`[Errno 8] nodename nor servname not known`) — transient network |
| pipe_expansion/debug | 1 | 0 / 0 | 0.0 | None | 0 | — | DNS resolution failure (same) |

R7 was largely a wash on the persona-driven path: cell 1 never
reached /solve due to mesh-cycle behavior; cells 2+3 hit transient
DNS errors and never started.

## Direct E2E (curl-driven, F10 fix verification)

To independently validate the F10 fix end-to-end with a real
OpenFOAM solver, drove a clean Steps 1-5 sequence on a fresh
NACA0012 case via curl:

```bash
# Step 1: Stage STL
POST /api/import/stl  → 200 (case_id assigned)

# Step 2: Mesh
POST /api/import/<case_id>/mesh {"mesh_mode":"beginner"}
  → 200 (cell_count=1584, face_count=980)

# Step 4: Setup BC (LDC default)
POST /api/import/<case_id>/setup-bc
  → 200 (bc_kind=ldc, n_lid_faces=233, n_wall_faces=747, Re=100)

# Step 5: Solve
POST /api/import/<case_id>/solve
  → 200 SolveSummary {
       converged: True,
       end_time_reached: 2.0,
       last_initial_residual_p: 0.000776357,
       last_initial_residual_U: [0.124, 0.086, 0.170],
       last_continuity_error: 8.5e-8,
       n_time_steps_written: 5,
       time_directories: ['0', '0.5', '1', '1.5', '2'],
       wall_time_s: 66.45,
     }
```

**F9 fix path**: post-solve scanner correctly skipped `0.orig`
(set by setup-bc) and sorted only numeric time dirs.
**F10 fix path**: `_check_mesh_bc_consistency` returned None
(mesh patches `lid+fixedWalls` matched 0/p, 0/U boundaryField
keys); /solve invocation proceeded; OpenFOAM ran cleanly.

## R7 pattern: persona mesh-cycle behavior

Cell 1 (naca0012) friction log shows the persona executed:

| Sequence | Action | Status |
|---|---|---|
| early | POST /mesh | 200 |
| later | POST /setup-bc?from_stl_patches=1 | 200 |
| later | POST /mesh again | 200 (Fix 2 invalidated 0/) |
| later | POST /setup-bc again | 200 |
| later | POST /mesh × 2 more | 200 |
| step 63 | llm_chat SSL EOF | terminate |

The persona never POSTed /solve. Each /mesh erased prior /setup-bc
output (Fix 2 working as designed); persona kept regenerating mesh
trying to "fix" upstream issues it perceived in /face-index or
/patch-classification responses, instead of advancing to /solve.

This is **persona-prompt behavior**, not workbench correctness.
The Step 6 prompt added in B-ext-2.1 only addresses post-/solve
flow; it doesn't tell the persona "/mesh is destructive — POST
once at start of Step 2, never again after /setup-bc". That gap
is B-ext-4's job.

## New findings (B-ext-4 candidates)

### F11 — /run-history returns empty after successful solve

```bash
# After /solve returned SolveSummary 200:
GET /api/cases/<case_id>/run-history
  → 200 {"case_id":"...","runs":[]}
```

The /run-history route's run registry is not being populated when
icoFoam runs via /solve. Persona Step 6 prompts direct to
/run-history for run_id discovery (which feeds /results/{run_id}/
field/{name}); without populated runs, that path is unusable.

### F12 — LDC defaults on NACA0012 produce NaN U field

```bash
GET /api/cases/<case_id>/results-summary
  → 422 {"failing_check":"results_malformed",
         "detail":"U field at .../2/U contains 1584 NaN/Inf entries
                   — solver diverged to non-finite values."}
```

The icoFoam solver "converged" residual-wise (last_initial_residual_p
~7.7e-4) but produced NaN in the U field. Root cause: the LDC
default mode (`from_stl_patches=0`) writes lid_velocity=(1,0,0),
nu=1e-3, Re=100, BC patches `lid` (top of bbox) + `fixedWalls`
(everything else). This is physically nonsensical on a NACA0012
airfoil: the "lid" patch is just whatever face happens to be on
+y of the bbox, which doesn't correspond to any meaningful aero
geometry. The solver runs but produces gibberish.

For verdict-eligible state, persona must use `from_stl_patches=1`
with a proper bc_contract reflecting the case physics (Re~1e6,
ν=1.45e-5 m²/s, freestream BC at "inlet" patch, etc.). The Step 4
prompt mentions this but the persona didn't get there in R7.

## V130 + V132 contract

R7 + curl E2E add 6 more live runs to V130 sample (now 27 total:
9 R1+R2+R3 + 3 R4 + 3 R4.5 + 3 R5 + 3 R6 + 3 R7 + 3 curl direct).
0 violations across all. Sample bound to DeepSeek; cross-family
validation gated on API keys.

V132 MUTATING_ROUTES + KNOWN_MUTATION_FUNCTIONS: zero impact (no
new routes; F10 fix is a contract correction in existing routes).

## R3 → R7 verdict-floor progression

| Iter | Step 5 reach (POST 200) | Verdict pass | New findings | New workbench fix |
|---|---|---|---|---|
| R3 | 0/3 | 0/3 | F1-F5 | (B-arc B.1-B.5.5) |
| R4 | 0/3 | 0/3 | F6, F7 | F6, F7 |
| R4.5 | 2/3 | 0/3 | (none) | (R4.5 tuning) |
| R5 | 0/3 (F9 regression) | 0/3 | F9 | — |
| R6 | 0/3 | 0/3 | F10 | F9 |
| R7 | 0/3 (DNS+cycle) | 0/3 | F11, F12 | F10 |
| curl direct | **1/1** ✅ | n/a (no model verdict) | — | (F9+F10 verified) |

## Counter

B-ext-3.4 increment: +1 (this DEC). Cumulative B-ext-3: 5 (charter
+1, V61-181 +1, V61-182 +1, V61-183 +1, V61-184 +1).

## Recommendation

**Stop R-iterations on the current persona prompts.** The workbench-
correctness gap (F10) is closed. Open B-ext-4 to:

1. **Persona prompt** "Step 2 — never re-/mesh after /setup-bc"
   guidance (small content change; testable via persona library
   test). Will likely close the cell 1 mesh-cycle pathology.
2. **F11 fix**: investigate why /api/cases/{id}/run-history returns
   empty after /solve POST 200; populate the run registry
3. **F12 / persona prompt**: stronger Step 4 guidance to use
   `from_stl_patches=1` with actual case physics (high-Re for
   external aero; kinematic viscosity from brief; proper inlet
   patch type). Possibly also reject the LDC fall-through when
   the case isn't a cube (warning-only or hard-error)

(1) + (2) + (3) together should land verdict pass ≥ 1/3 in R8.

## References

- DEC-V61-180 · B-ext-3 charter
- DEC-V61-181 · F10 investigation
- DEC-V61-182 · F10 fix (Fix 1 + Fix 2)
- DEC-V61-183 · F10 E2E contract test
- DEC-V61-184 · this DEC
- `.planning/dogfood/runs/live_2026_05_07_r7/` — friction logs
- Direct E2E case dir: `imported_2026-05-07T09-54-23Z_14bc8a10`
