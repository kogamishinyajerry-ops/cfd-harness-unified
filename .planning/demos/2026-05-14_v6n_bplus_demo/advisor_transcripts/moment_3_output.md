**Quick Verdict**

1. **Path 3 first**: Boussinesq-from-scratch is the best opening move because it is the only path that can plausibly give you a credible steady thermal field by Wednesday without re-entering the compressible SIMPLE failure regime.  
2. **Path 4 second**: CHT + radiation has the best physics upside after Path 3, but only as a back-half stretch once you already have something shippable, because the fluid-side numerical sensitivities still carry across solver families [V15].  
3. **Path 1 third**: Tier-1 numerics attacks the primary error source most directly, but on 4-core ARM it is a full-week bet with almost no schedule resilience and was already flagged resource-mismatched [CAVEAT].  
4. **Path 2 skip**: I would not spend this week on the steady compressible SIMPLE chain again; five prior blowups plus the S5 startup pattern make that a repeat-failure path, not a recovery path [V5/V6/V7][S5].

**Why This Order**

- **Calendar exposure**: Path 3 is the only option with a same-day setup and overnight-solve profile, so it preserves a Wednesday exit ramp.
- **Physics ROI per hour**: Path 3 buys a real steady balance field fast; Path 4 adds missing physics; Path 1 may improve the dominant deficit but eats the whole budget.
- **Failure avoidance**: Path 2 directly revisits a known instability class; Path 4 inherits some fluid-numerics risk, so it should follow, not lead [V15].
- **Shippability**: Under one-engineer, 5h/day conditions, “good result early, richer result later” is safer than “perfect fix or nothing.”

**Week Plan**

| Day | Activity | Milestone |
|---|---|---|
| Mon | Build independent Boussinesq case, convert BCs/properties, run smoke test | Case boots cleanly |
| Tue | Run to steady balance, fix any BC/transport mistakes, start post | First steady bulk-T estimate |
| Wed | Finish Path 3 post, compare vs v6N, decide whether Path 4 is worth remaining budget | **If stop Wed:** ship steady Boussinesq field, bulk-temperature correction, and delta-vs-v6N memo |
| Thu | Start minimal Path 4 setup, reusing geometry and proven fluid settings cautiously | Coupled case assembled |
| Fri | First Path 4 run and triage | **If stop Fri:** ship Path 3 package plus Path 4 feasibility result or first coupled trend |
| Sat | Only continue Path 4 if Friday is numerically sane; otherwise tighten reporting and sensitivity notes | Best available upgraded evidence |
| Sun | Final compare: v6N vs Path 3 vs optional Path 4 | **If stop Sun:** ship ranked recommendation pack with next-step decision |

**What I’m Explicitly Not Recommending**

Path 2. You already paid for that lesson five times. Under this budget, repeating a known SIMPLE startup avalanche is not disciplined engineering.

**One Question Back**

Is radiation/conjugate heat transfer actually required for this week’s design decision, or do you mainly need a defensible correction to bulk bay temperature? If radiation is decision-critical, Path 4 moves closer to the front right after Path 3.

Final pick is yours; this is a priority stack optimized for ROI under the stated 7-day, 4-core, one-engineer constraint, and that constraint set may itself be the thing to challenge.
