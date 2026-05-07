# Dogfood live partial · R5 + R6 (B-extend-2)

> Iteration of B-ext-2 charter (DEC-V61-176). 3 DeepSeek-V4-Pro
> personas × 3 cases (NACA0012, backward_step, pipe_expansion).
> R5 attempted Step 6 prompts at max_steps=80, max_input_tokens=3M.
> R5 surfaced F9 (workbench-side `0.orig` ValueError); R6 reran with
> the F9 fix and surfaced F10 (BC patch-name mismatch).

## Verdict

**Charter target verdict pass ≥ 1/3 NOT met.** R5: 0/3. R6 (post
F9 fix): 0/3. Cells consistently fail at /solve → 502 due to
F10 (a real workbench-side BC pipeline bug). Per charter HARD
bound clause, escalating F10 to user as B-ext-3 candidate.

## R5 raw stats

| Cell | Steps | Tokens (in/out) | Wall (s) | Verdict | Step 5 reach (POST 200) |
|---|---|---|---|---|---|
| naca0012/experienced_fluent | 80 | 2.13M / 27k | 623 | None | 0 |
| backward_step/novice | 80 | 2.58M / 31k | 694 | None | 0 |
| pipe_expansion/debug | 80 | 2.49M / 32k | 651 | None | 0 |

R5 termination cause for all 3: max_steps_reached. /solve attempts
returned 405/500/502 due to F9 — workbench-side post-solve scanner
crashed on `0.orig` directory (`sorted(..., key=lambda s: float(s))`
ValueError) → solve route returned 500 → persona never received
SolveSummary → kept retrying Steps 4-5.

## F9 fix — landed inline (commit 8d0f13e)

Extracted `_filter_numeric_time_dirs()` helper in
`ui/backend/services/case_solve/solver_runner.py`. Drops any name
not parseable as float (e.g., `0.orig`, `0.bak`, arbitrary
non-numeric suffixes). 3 regression tests added; 15/15 solver_runner
tests pass.

## R6 raw stats (post F9 fix)

| Cell | Steps | Tokens (in/out) | Wall (s) | Verdict | /solve attempts | /solve 200s | /results-summary | /run-history |
|---|---|---|---|---|---|---|---|---|
| naca0012/experienced_fluent | 69 | 3.03M / 33k | 720 | None | 4 | 0 (all 502) | 0 | 0 |
| backward_step/novice | 80 | 3.00M / 33k | 729 | None | 0 | — | 0 | 0 |
| pipe_expansion/debug | 79 | 3.05M / 30k | 686 | None | 5 | 0 (all 502) | 1 | 2 |

R6 termination cause: max_steps_reached (3/3) or budget (naca0012 at
step 69 with 3M input tokens consumed).

## F10 (new finding) — BC patch-name mismatch in setup-bc

`POST /solve` returns 502 with body:
```
{"detail":{"failing_check":"solver_diverged","detail":"simpleFoam
exited with code 1; see ... log.icoFoam ..."}}
```

Solver log root cause:
```
--> FOAM FATAL IO ERROR:
Cannot find patchField entry for patch0
file: /tmp/.../<case>/0/p/boundaryField from line 6 to line 7.
```

`setup-bc` writes `0/p/boundaryField` referencing patch names
(`patch0`, `patch1`, …) that do not match the actual mesh patches
(`inlet`, `outlet`, `wall` after the F7 patch-split workflow runs).
The setup-bc → polyMesh/boundary contract is broken: BC names use
generic indexed labels while patch-classification stores semantic
names.

This is **workbench-side**, not a persona prompt issue. Persona
correctly drove Steps 1-4 (all 200), then Step 5 fails because the
artifacts setup-bc produced are inconsistent with the mesh.

Reproduction: `curl -sX POST -H "Content-Type: application/json" -d '{}' \
http://localhost:8000/api/import/<case_id>/solve` after a successful
Steps 1-4 sequence on any of the 3 charter cases.

## Step 6 prompts — partial effectiveness signal

Even though no cell reached /solve POST 200, **pipe_expansion/debug
called /results-summary 1× and /run-history 2×** in R6, attempting
the post-solve flow. naca0012 + backward_step did not. This suggests:

1. The Step 6 prompt content is being read by debug persona at least
2. naca0012 + backward_step exhausted budget on F10-driven /solve
   retries before reaching Step 6 in the workflow
3. We can't conclude whether Step 6 prompts would have reliably
   driven all 3 personas to verdict — gated on F10 fix first

## V130 advisory-only contract

15 R1-R4.5 runs + 6 R5+R6 runs = **21 live runs total, 0 violations**.
Aggregator V130 scan continues clean. Sample bound to DeepSeek-V4-Pro
(other 6 charter cells gated on Anthropic + CODEX_RELAY API keys).

## V132 contract

R5 added Step 6 persona prompt content (no new mutating routes).
R6 added F9 helper to solver_runner.py (read-only filter, no new
routes). MUTATING_ROUTES + KNOWN_MUTATION_FUNCTIONS registry
unchanged. Contract test 21/21 expected to pass.

## R3 → R6 verdict-floor progression

| Iteration | Step 5 reach (POST 200) | Verdict pass | Termination | Avg tokens/cell |
|---|---|---|---|---|
| R3 (B-arc close) | 0/3 | 0/3 | budget × 3 | 660k |
| R4 (F6+F7) | 0/3 | 0/3 | budget × 3 | 648k |
| R4.5 (tighter prune + 1.5M) | 2/3 | 0/3 | max_steps×2 / budget×1 | 1.33M |
| R5 (Step 6 prompts + 3M) | **0/3 (F9 regression)** | 0/3 | max_steps × 3 | 2.40M |
| R6 (post F9 fix) | **0/3 (F10 wall)** | 0/3 | max_steps × 3 | 3.03M |

R5 was a regression on the workbench surface (F9 crashed the post-
solve scanner). R6 cleared F9 and revealed F10 — a deeper BC
contract issue. Each R-iteration peels back one workbench layer.

## Counter

- B-ext-2.2 increment: +1 (this DEC, V61-178)
- B-ext-2 cumulative: 3 (charter +1, V61-177 prompts +1, V61-178 +1)
- B-ext + B-ext-2 + B-arc cumulative: **+16**

## Recommendation

**Stop iterating R-rounds at R6.** R7+ would burn DeepSeek tokens
without progress because F10 is a workbench-side BC artifact bug,
not a persona-prompt issue. Open B-ext-3 to:

1. Investigate `setup-bc` service → polyMesh/boundary patch-name
   contract. Either:
   (a) setup-bc must read mesh boundary patch names and emit
       matching `0/p/boundaryField` keys, or
   (b) the solver call must remap engineer-supplied names to mesh
       indices before invoking OpenFOAM
2. Add an integration test: full Steps 1-5 sequence on each charter
   case must produce a /solve POST 200 with `converged` field
3. Re-run R7 once F10 fixed; expect Step 6 prompts to drive verdict
   pass ≥ 1/3 once /solve actually returns SolveSummary

## References

- DEC-V61-176 · B-ext-2 charter (parent)
- DEC-V61-177 · B-ext-2.1 Step 6 prompts
- DEC-V61-178 · B-ext-2.2 R5+R6 measurement (this report)
- DEC-V61-179 · B-ext-2.3 close
- `ui/backend/services/case_solve/solver_runner.py` — F9 fix at
  `_filter_numeric_time_dirs()`
- `.planning/dogfood/runs/live_2026_05_07_r5/` — R5 friction logs
- `.planning/dogfood/runs/live_2026_05_07_r6/` — R6 friction logs
