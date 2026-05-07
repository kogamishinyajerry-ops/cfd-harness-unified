# DOGFOOD_REPORT_LIVE_R9 — B-ext-4 final R-iteration

**Date:** 2026-05-07
**Charter:** verdict pass ≥ 1/3 across {naca0012/experienced_fluent,
backward_step/novice, pipe_expansion/debug} × DeepSeek-V4-Pro.
**Result:** **0/3 verdict pass · charter NOT met**.
**Closes:** B-ext-4 (per DEC-V61-190).

## Setup delta vs R8

- `max_steps: 80 → 120` (+40, give backward_step headroom for Step 6
  + submit_verdict flow that R8 ran out of steps to reach)
- `max_input_tokens: 3M → 4M` (+1M, absorb extended Step 6 budget)
- All other knobs unchanged: `prune_keep_full=3`,
  `prune_min_turns_before_active=4`, anti-mesh-cycle prompts (V61-187),
  F11 fix (V61-188), F12 mitigation (V61-189) all in place.

## Per-cell outcome

| cell | steps | in_tokens | out_tokens | elapsed | exit | /solve POST | submit_verdict |
|---|---|---|---|---|---|---|---|
| naca0012 / experienced_fluent | 120/120 | 3,694,281 | 38,312 | 812.5s | max_steps_reached | 0×200 / 6×502 | 0 |
| backward_step / novice | 20/120 | 332,522 | 4,618 | 184.0s | DeepSeek read timeout | none | 0 |
| pipe_expansion / debug | 113/120 | 4,031,269 | 38,523 | 954.5s | input_token_budget_exceeded | 0×200 / 5×502 | 0 |

## Two new findings surfaced

### F13 · /solve 502 Bad Gateway (workbench, stress-induced)

11 events across naca0012 (6×) and pipe_expansion (5×). Workbench
`/api/health` healthy throughout; `cfd-openfoam` container 35h uptime.
A leftover `compassionate_neumann` container (42 min runtime) suggests
the solver-launch path leaks ephemeral containers under repeated runs.

R7 curl direct E2E and R8 backward_step persona drive both produced
/solve 200, so F13 is **not deterministic** — it's a stress-mode
failure. Diagnosis deferred to B-ext-5.

### F14 · DeepSeek API read timeout

backward_step step 20 client-side timeout after 15.5 min waiting for
chat completion response. R7 + R8 saw none. Likely upstream
api.deepseek.com instability. Mitigation: client-side timeout/retry in
`OpenAICompatClient` or vendor swap (Codex relay gpt-5.4).

## R8 vs R9 regression: backward_step

R8's lone bright spot was backward_step reaching /solve POST 200 with
`reports/imported_..1e6fcecf/runs/2026-05-07T10-37-10Z/measurement.yaml`
(p=6.5e-7, continuity=9.9e-12, success=True). That run consumed all 80
max_steps before reaching submit_verdict.

R9 backward_step crashed at step 20 on F14 — never got to Step 4. The
R8 signal is **valid but not stable**: workbench can do this on a real
persona drive when the geometry is simple and the upstream APIs are
healthy. R9 added neither.

## Pipe_expansion's pivot: F12 mitigation works, F8'/8" surface

R9 pipe_expansion explicitly used `from_stl_patches=1` per the F12
prompt update — but received **11× HTTP 400** on POST /setup-bc with
that flag, suggesting bc_contract validation rejected its
inlet/outlet/wall partition. This is a **different flavor of F8**
(bc_contract schema gap) than what F12 mitigates. New tracker for
B-ext-5: "F15 bc_contract validation rejects valid persona-authored
non-LDC channel partitions on STL with multi-region patches".

## Anti-mesh-cycle prompt effectiveness across the arc

| cell | R7 mesh count | R8 mesh count | R9 mesh count |
|---|---|---|---|
| naca0012 | 6 | 6 | 10 |
| backward_step | 4 | 1 (✅) | 1 (timed out before mesh-cycle could occur) |
| pipe_expansion | 4 | 1 (✅) | 3 |

Naca0012 is **immune** to the prompt — the persona keeps re-meshing
even with explicit Step 2 destructive warnings. This is a charter-cell
selection issue, not a workbench issue.

## V130 advisory-only contract

**0 violations across ~30 cumulative samples** (B-arc + B-ext-2 +
B-ext-3 + B-ext-4). Contract holds firmly across all R-iterations.
This is the only sub-charter that has been fully achieved.

## Final assessment

5 R-iterations across B-ext-2 / B-ext-3 / B-ext-4, each landing a real
fix (F9 / F10 / F11 / F12), have not produced a single verdict pass.
R8's /solve 200 was the strongest single signal but did not reach
verdict. The remaining gap is structural and crosses three layers
(workbench under stress, DeepSeek API stability, persona budget /
verdict-formation prompt). No single fixable defect remains.

**Per V133 round-cap=3, B-ext-4 stops here.** Outstanding work moves to
B-ext-5 with a fundamentally different strategy: diagnose F13 first,
re-pick charter cells (drop naca0012), reduce charter to 1 cell with
verdict-formation focus, mitigate F14, and rehearse Step 6 in
isolation.

## Artifacts

- Raw runs: `.planning/dogfood/runs/live_2026_05_07_r9/`
- DEC: `.planning/decisions/2026-05-07_v61_190_b_ext_4_4_r9_close.md`
- Chinese summary: `.planning/dogfood/B_EXT_4_CLOSE_SUMMARY_ZH.md`
