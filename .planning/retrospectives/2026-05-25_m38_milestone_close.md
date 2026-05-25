# M3.8 milestone close · DRY useEffectiveCaseId hook · 2026-05-25

> Parent: DEC-V61-202 (Workbench Dynamic-Guided) M-track
> Cycles: 1 (janitorial DRY extraction)
> Closing commit: `059ad04` refactor(workbench): M3.8 cycle 1
> Deliverable: shared `useEffectiveCaseId` hook eliminates 3-way copy-paste of blueprint-vs-case gate

## TL;DR

M3.7 cycle 1 fixed B7 by inlining the same gate logic in 3 V4 shell components (TopBarV4 / LeftRailV4 / KpiStripV4). M3.8 cycle 1 extracted the pattern into a single hook so future shell additions inherit the gate automatically. 79/79 V4 tests pass; visual spot-check confirms behavior preservation.

## Counter table

| Cycle | Goal | LOC delta | Tests | Codex round | Confidence | Outcome |
|---|---|---|---|---|---|---|
| 1 | Extract repeated blueprint-vs-case gate into shared hook | +66 -24 (48 LOC new hook · -24 inline in 3 callers · +18 hook usage in 3 callers) | 79 V4 unit tests + visual spot-check on circular_cylinder_wake | 0 | high | Behavior-equivalent · all callers use hook |

`autonomous_governance_counter_v61` +1.

## Why this cycle exists (vs. defer)

M3.7 retro explicitly listed DRY as deferred candidate (#4). User explicitly picked it from the post-M3.7 survey. Doing it while the pattern is fresh in head is cheaper than re-discovering it later.

## What worked

- **Hook contract is explicit**: `EffectiveCaseId` interface with 4 fields (effectiveCaseId / isBlueprintMode / isDoe / isGeometryBlueprint) lets callers pick the granularity they need without re-deriving.
- **useMemo dependency clarity**: hook memoizes on (caseId, activeStep) — stable identity when nothing changes, recomputes when either input flips.
- **Zero behavior change**: spot-check screenshot identical to post-M3.7. Refactor is true refactor.

## What hurt / blind spots

- **Net LOC didn't shrink**: 27 LOC of inline gates × 3 callers = ~21 LOC saved by removal, but hook file (48 LOC) + 3 imports + 3 destructures (~18 LOC added) = +42 net. The win is centralization, not raw count. Trade-off acceptable for a single point of truth.
- **The hook would've prevented B7 if it existed before M3.7**: counterfactually, if M3.5 / M3.6 cycles had spawned with the hook in place, the geometry-blueprint gate would've propagated through `effectiveCaseId` consistently. Reminder: extract shared patterns early — but only when the pattern has stabilized (3 occurrences is the rule, which is exactly where we landed).

## v2.3 governance check

| Rule | Cycle 1 |
|---|---|
| Spike-class scope | ✅ functional change is single hook extraction (~9 LOC of moved logic) + 3-caller refactor (~9 LOC each); hook file is documentation-heavy |
| Codex review trigger hit? | ❌ pure refactor · no logic change · no schema · no security boundary |
| Kogami invoked? | ❌ no charter / no governance-rule-change |
| Notion sync? | not yet (session-end batch) |
| Surface-scan mandatory? | optional · touched 3 known V4 shell files + new hook |
| Counter charge? | +1 (autonomous) |
| post-R3 defect? | 0 |

## Session accumulator (post-M3.8 · 7 milestones · 24 commits this run)

| Milestone | Cycles | Closing commit | Note |
|---|---|---|---|
| M3.2 | 7 (3 new this run) | `092a710` ish · prior runs | Playwright dogfood E2E |
| M3.3 | 3 | `???` · this run | UX validation + spot-check methodology |
| M3.4 | 5 | `093e5b9` | Empty-state + B6 cascade-clear |
| M3.5 | 2 | `f3f055b` | Demo recording infrastructure |
| M3.6 | 1 | `6de6504` | Real-CAD demo iteration |
| M3.7 | 1 + bonus | `6ea1725` | Chrome de-hardcoding (B7) + post-B7 demo re-record |
| **M3.8** | **1** | **`059ad04`** | DRY useEffectiveCaseId hook |
| **Total** | **20 cycles** | **24 commits ahead origin/main** | **0 post-R3 defects** |

## Next milestone candidates

1. **Stop · session-end batch sync** (RECOMMENDED): 7 milestones + 24 commits + 4 demo .webm + ~10 retro docs + new backlog findings → time to land Notion sync + RESUME.md update + clean session handoff.
2. **M3.9 = B4 sidebar dead-space**: only open P3 from M3.2 visual audit.
3. **M3.9 = M4 charter scoping**: strategic · multi-day scope · likely needs Kogami opt-in.

Default if user 30 秒不开口: walk forward with #1 (stop) — accumulator is high; clean handoff is more valuable than another janitor cycle.
