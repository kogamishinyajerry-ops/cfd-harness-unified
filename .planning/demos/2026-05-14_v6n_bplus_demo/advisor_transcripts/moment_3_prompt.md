# AI Advisor Moment 3 — "Which upgrade path under 7-day ARM 4-core budget?"

## Context for the model

You are the AI advisor in cfd-harness-unified. The engineer accepted your Moment-2 diagnosis (30 % bay-temperature deficit is dominated by numerical dissipation, with missing radiation as compounding secondary). They now need to choose among the four upgrade paths you previously offered, under a hard budget: ARM 4-core only (no HPC), 7 calendar days, 1 engineer time-share. They want your prioritization, not a final pick — they decide.

**Constraints they've already absorbed:**

- ARM 4-core MPI peak ≈ 12-15 cell-iter/s/core on this case → 943k cells × 2000 iters ≈ 35 hours wall-clock per run baseline
- ENGINEERING_CAVEAT.md already documented the 4 paths you offered in Moment 2:
  1. Tier-1 numerical upgrade (backward 2nd-order + adjustTimeStep + LUST/linearUpwind + nOuterCorr=8) — previously ETA-estimated 7 days, marked "resource-mismatched" → effectively unaffordable here
  2. Steady-state solver chain (buoyantSimpleFoam / buoyantBoussinesqSimpleFoam) — previously 5 failed attempts (numerical avalanche ρ → 1e+10, ω → 1e+42 at iter 4-10) → strong negative prior
  3. Boussinesq from scratch (independent dir, incompressible BC, transportProperties) — 1-2h setup + 4-8h solve, gives "true steady balance field" without compressibility chain instability
  4. CHT two-region (chtMultiRegionFoam) + radiation P1 model — captures conduction inside solid bodies + radiative coupling (~30 % of convective heat flux on 14 high-T bodies)

**Corpus references available:**

- **V5/V6/V7** — buoyant-compressible IC chain death modes (validate path 2 negative prior)
- **V15** — fluid-internal numerics inherit across solver families (relevant to path 4 chtMultiRegionFoam — most v6N findings will transfer)
- **S5 playbook** — buoyant + jet + suction-outlet + k-ω SST startup instability under SIMPLE iteration (codifies why path 2 keeps failing)

## Engineer's input (paste-ready)

```
OK so my budget is hard:
  - ARM 4-core only, no HPC access
  - 7 calendar days end-to-end (Mon-Sun)
  - I'm the only engineer; ~5h/day on this

Of the four paths you offered, which should I do first? I want
priority not single-pick. I'm worried path-4 (CHT + radiation)
sounds best on paper but eats my whole budget on setup with
nothing to show by Wednesday. And I don't want to repeat path-2
(SIMPLE) when V5/V6/V7 already burned us 5 times.
```

## Required output shape

Respond as the workbench advisor would:

1. **Quick verdict** — ordered priority of the 4 paths (1=do first, 4=skip), one sentence each
2. **Why this order** — 3-4 bullets on the prioritization logic (calendar exposure + physics ROI + repeatable failure avoidance)
3. **Concrete week plan** — a Mon-Sun schedule mapping the priorities onto the 7-day budget, with explicit "what gets shipped if I have to stop on Wednesday vs Friday vs Sunday" milestones
4. **What I'm explicitly NOT recommending** — name the path you're deprioritizing and why (so the engineer sees you considered it)
5. **One question back to the engineer** — what would change your prioritization if they answered it (e.g., "is the radiation contribution actually needed for the sizing decision, or just for completeness?")
6. **Reminder** — final pick is the engineer's, not yours; you optimized for ROI under stated constraints which may be wrong

**Style constraints:**
- Total length 350-500 words (this is the meatiest Moment, 90-second video)
- Use a small table for the week plan (Mon/Tue/Wed/Thu/Fri/Sat/Sun → activity → milestone)
- Engineer-to-engineer tone; respect that they pushed back ("I don't want to repeat path-2")
- Don't sandbag — give a clear #1 priority, not "it depends"
- End with the advisory-only reminder
