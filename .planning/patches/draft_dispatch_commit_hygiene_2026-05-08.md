# DRAFT patch · Dispatch commit hygiene

> **Status**: DRAFT · suggested-only · NOT auto-applied
> **Author**: harvester · 2026-05-08 · cycle 001
> **Target**: main session — orchestration discipline
> **Scope**: process change, no LOC. May warrant a sentence in
> `case_proposal_queue.md` "How to add a new entry" §

## Observed gap

`git status` shows:
- Modified (uncommitted): `.planning/INDEX.md`,
  `.planning/case_index.md`, `.planning/case_proposal_queue.md`
- Untracked (uncommitted): kickoff 4-file sets for cases 004-010
  (28 files total spanning ~9000 LOC of validated, paste-ready
  case briefs)

These represent **8 dispatched cases** (per case_index.md "dispatched ·
DEFERRED" rows) where the dispatch lifecycle move is in working tree
but not in git history.

## Risk

1. **Audit trail loss**: if the main session's working tree is
   reset, abandoned, or the harness compacts the conversation
   away, ~9000 LOC of validated Codex output disappears. Re-running
   Codex is non-deterministic and may produce different defect
   choices, different CAD scripts, different validation deltas
2. **Notion-mirror divergence**: `notion_sync_status` SSOT lives
   in commit-tracked DEC frontmatter. With orchestration moves
   uncommitted, the main session has nothing to sync — Notion stays
   blind to 8 case dispatches
3. **Three-actor handoff fragility**: when sub-sessions eventually
   start (paste from kickoff file in fresh terminal), they read
   from working tree. If the orchestrator restarts before sub-session
   loads, kickoffs vanish
4. **Harvester fidelity**: this harvest report cites uncommitted
   files. Future harvests can't reproduce conclusions if files
   weren't committed

## Proposed rule (suggestion, not auto-applied)

Add to `.planning/case_proposal_queue.md` under "How to add a new
entry to this queue" (after step 11):

```
12. After main session writes the kickoff file, atomically commit:
    - .planning/methodology/kickoff/case_NNN_codex_request.md
    - .planning/methodology/kickoff/case_NNN_codex_response.md
    - .planning/methodology/kickoff/case_NNN_validation.md
    - .planning/methodology/kickoff/case_NNN_<name>.md
    - .planning/case_proposal_queue.md (Dispatched row appended)
    - .planning/case_index.md (status update)

    Single commit, conventional message:

      chore(dispatch): case_NNN <name> · Codex round R · paste-ready

    Sub-session pickup is git-tracked from this point.
```

## Backfill recommendation

Once this rule is accepted, propose a backfill commit for the
existing 8 cases. Two options:

**Option A — single backfill commit** (simpler):
```
chore(dispatch): backfill cases 004-010 kickoffs · pre-rule batch

Atomic-commit-after-dispatch rule established 2026-05-08; this
commit captures the 8-case batch dispatched 2026-05-07/08 before
the rule was in force.
```

**Option B — per-case backfill** (cleaner audit trail, more commits):
8 commits, one per case, dated retroactively to the dispatch date
(via `--date=` if user accepts).

Option A recommended for harvest cycle 001; Option B for any future
batch (i.e., once rule is in force, commits should be per-case at
dispatch time, not batched).

## Why this is harvester-scope (not main-session-scope)

This is a process-discipline gap that the **main session is too
close to see**: the orchestrator has been productively dispatching,
the kickoffs do exist in working tree, and the lifecycle moves work
correctly. The gap only becomes visible from harvester's
"cumulative-state-scan" position. Exactly the role this harvester
exists for.

## What this patch does NOT propose

- Does NOT modify the codex_case_design_protocol or kickoff template
- Does NOT add a pre-commit hook or automated check (per v2.3
  retired hook approach; rule should be human-followable)
- Does NOT prescribe how main session handles in-flight Codex
  rounds where the kickoff file isn't yet finalized (only the
  *paste-ready* state triggers the commit)
- Does NOT change the 4-file naming convention

## References

- `.planning/case_proposal_queue.md` "How to add a new entry"
- DEC-V61-198 §"Operating procedure" — six per-case standard moves
- Project rule `~/CLAUDE.md` — atomic-commit discipline + commit-trailer
  conventions
