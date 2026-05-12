# DRAFT patch · Revisit pre-allocation policy

> **Status**: DRAFT · suggested-only · NOT auto-applied
> **Author**: harvester · 2026-05-08 · cycle 001
> **Target**: user (escalation) + main session
> **Scope**: text change in `case_proposal_queue.md` (≤30 LOC)

## Observed contradiction

`case_proposal_queue.md` § "Concurrency policy" says:

> Up to 4 sub-sessions in parallel ...
> Beyond 4, harvest cadence stalls.

`case_proposal_queue.md` § "Why 'queue' not 'list'" says:

> The queue's contents are NEVER pre-allocated more than 1-2 cases
> ahead — premature enqueueing wastes Codex compute

`case_proposal_queue.md` § "Dispatch policy" says:

> No pre-allocation beyond 1-2 cases ahead

Current state per `case_index.md`:
- 2 active threads (case_002a/b) — fits "in-flight" budget
- **8 dispatched-deferred** (cases 003-010) — kickoffs paste-ready,
  no sub-sessions started

8 deferred dispatches violates the "1-2 cases ahead" rule by 4×.

## What actually happened (interpretation)

Reading the validation reports + INDEX.md, the 10-case roster was
deliberately fired in a batch on 2026-05-07/08 to **complete numerics-
class coverage in one go**. Per `case_proposal_queue.md` "Roster
rationale":

> Why these 6, in this order: 1. Numerics-class diversity is the
> ranking objective ... After all 10 land, the project covers ...
> the workhorse OpenFOAM solver matrix.

The user appears to have explicitly chosen "saturate the coverage
matrix now, run sub-sessions when compute frees up." That's a
legitimate strategic choice — it locks in design contracts via
Codex while context is loaded, defers compute-bound work.

The pre-allocation rule, as written, does not anticipate this
**strategic batch fire** for coverage-saturation purposes.

## Two reconcilable interpretations

### Interpretation A · "Strategic batch fire" is a sanctioned exception

Update queue policy to acknowledge:

```diff
- No pre-allocation beyond 1-2 cases ahead
+ Standard pre-allocation budget: 1-2 cases ahead.
+ EXCEPTION — coverage-saturation batch fire: a one-shot
+ multi-case dispatch is allowed when the goal is to lock in
+ a complete numerics-class coverage matrix with sub-sessions
+ deferred to compute availability. Document explicitly in the
+ Dispatched section's "Status note" column ("DEFERRED — awaiting
+ user resources").
```

### Interpretation B · The current state IS the violation; queue should be drained

Pause new dispatches. Run sub-sessions for 1-2 cases first. Confirm
A2 extraction gap behaves as predicted in case_005 sub-session
before dispatching another wave.

Under this interpretation: **8 deferred is a backlog warning, not a
feature**. Future dispatches throttle until backlog burns down to
≤2.

## Recommendation

**Interpretation A**, conditional on three additions:
1. Append-only "Status note" must distinguish
   `DEFERRED — strategic batch` from `DEFERRED — awaiting compute`
   (right now both read "awaiting user resources" without explaining
   why)
2. Set a **dispatch freeze marker**: no new case_NNN+1 enqueues
   until at least 2 of the deferred batch reach `in-flight` or
   `closed`. Else the batch grows unboundedly
3. Each deferred case ages cheaply — but kickoff files are
   point-in-time snapshots of A1/A2/A3/A4 advisor state. If the
   project lands A2 before case_005 sub-session runs, the
   case_005 kickoff's "expected_advisor: virtual_interface_detector_pending_A2"
   is stale. Add a "validity-as-of" date to each kickoff file's
   header so sub-sessions know to re-check advisor state if the
   file is older than the most recent sub-DEC affecting advisor
   inventory.

## Why this is harvester-scope

The contradiction between policy text and observed state is
exactly the kind of "drift the main session is too close to see"
the harvester role is positioned for. The main session's
turn-by-turn focus produced 8 valid dispatches; the policy text is
a few clicks down a navigation tree the dispatcher doesn't routinely
re-read.

## Escalation note

Interpretation choice (A vs B) is a **user decision** — both are
defensible:
- A favors current trajectory (coverage matrix complete; sub-sessions
  on user's cadence)
- B preserves the original "small queue + tight feedback" intent

Harvester recommends A but does not choose unilaterally.

## What this patch does NOT propose

- Does NOT touch the 10-case roster itself (cases 003-010 stay
  paste-ready)
- Does NOT modify `concurrency policy` in-flight budget (4 still
  applies once sub-sessions actually start)
- Does NOT alter the kickoff template
- Does NOT couple to Interpretation B mechanics (case-draining)
  unless user picks B

## References

- `.planning/case_proposal_queue.md` § "Dispatch policy",
  § "Concurrency policy", § "Why 'queue' not 'list'"
- `.planning/case_index.md` — 8 deferred rows
- DEC-V61-198 §"Operating procedure" — six per-case standard moves
