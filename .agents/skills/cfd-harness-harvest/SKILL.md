---
name: cfd-harness-harvest
description: |
  Project-specific harvest workflow for cfd-harness-unified. Use when
  the project has accumulated cross-case sediment that needs
  consolidation, or when an advisor lands / major V-finding shifts
  and stale references need backfill, or when a claim should be
  marked as questionable pending future evidence.

  Three modes:
    full              — fresh-session 4th-actor deep harvest (Move 1-6)
    backfill-sweep    — main-session inline knowledge-decay propagation
    mark-questionable — quick marker for a single claim awaiting evidence

  This skill DOES NOT auto-trigger. It activates when the user invokes
  it explicitly OR when the main session detects a documented trigger
  condition and surfaces the recommendation to the user.
---

# cfd-harness-harvest skill

Project-specific harvest workflow. Operates only in
`/Users/Zhuanz/Desktop/cfd-harness-unified/`.

## When to invoke (user-facing triggers)

Surface these to the user; user decides which mode (or none).

### Triggers for **full** mode (fresh 4th-actor session)

- ≥3 sub-session sediments since last harvest report (commit count
  in `~/Desktop/case_NNN_*/` sandboxes, or new V-rows in
  `industrial_case_solver_findings.md`)
- Phase boundary closed (M2 / M3 / etc. complete)
- Methodology suspicion accumulated (validation reports getting
  shorter, defect distribution skewed, kickoff template drifting)
- User asks "what does the corpus actually know now?"
- Main session has been running ≥2 weeks of project work without
  a harvest checkpoint

### Triggers for **backfill-sweep** mode (main session inline)

- Advisor LANDED → backfill all references using the old
  "_pending_AN" / "expect AN to detect" / "AN not yet landed"
  language
- New V-finding contradicts text in active kickoff files (e.g.,
  V25 reveals A2 has no gap-detection API; kickoffs claiming
  "expect A2 to detect gap" need update)
- A case lifecycle moves (deferred → in-flight → closed) without
  INDEX.md / case_index.md / case_proposal_queue.md staying in sync
- Status field in `industrial_case_solver_findings.md` changes
  (open → playbook, partial → confirmed, etc.)
- New methodology file created that other files should reference

### Triggers for **mark-questionable** mode

- A claim is being written that meets one of the 4 questionable
  criteria (see `.planning/methodology/knowledge_status_convention.md`)
- During a backfill-sweep, a claim is found that should be
  preserved-but-doubted rather than overwritten
- User says "I'm not sure that's right yet, but I want to write
  it down with a question mark"

## What this skill is NOT for

- **Not** deep cross-case pattern detection (that's `full` mode,
  which dispatches to a fresh-session harvester role)
- **Not** governance / DEC review (that's Kogami opt-in path)
- **Not** Codex case design (that's `codex-relay` skill)
- **Not** Notion sync (that's `notion-sync-cfd-harness` skill;
  invoke that AFTER harvest writes a report)
- **Not** an auto-trigger — user invokes; main session
  recommends

## Mode 1 · `full` (fresh 4th-actor session)

### How it works

The full harvest is a separate Codex session role
(established 2026-05-08 by DEC-V61-198 four-actor extension).
This skill does NOT run the harvest itself — it surfaces the
paste-ready prompt that the user opens in a fresh terminal.

### Steps (this session does)

1. Confirm with user that ≥3 sub-session sediments have landed
   since last harvest (or another full-mode trigger applies)
2. Print the paste-ready prompt by reading
   `.planning/methodology/harvest_session_kickoff.md` and
   extracting the section between `=== BEGIN ===` and `=== END ===`
3. Tell the user: "Open a fresh Codex terminal, paste the
   prompt below as the first message. The fresh session will run
   Move 1-6 and write `.planning/harvest_reports/<date>_harvest_<NNN>.md`."
4. Stop. Do NOT execute the harvest yourself.

### Why a fresh session is required

Main session is turn-driven and biased by current dispatches.
Cross-case pattern detection benefits from a fresh context that
scans cumulative state without the bias. The harvester role is
INTROSPECTIVE; main session is TRANSACTIONAL.

## Mode 2 · `backfill-sweep` (main session inline)

### How it works

When an advisor lands or a V-finding shifts the truth, references
across kickoffs / case profiles / queue entries / INDEX.md decay
fast. This mode is a focused stale-reference + status-coherence
sweep — much narrower than full mode, executable inline.

### Steps (this session does)

1. **Identify the trigger**: what changed? Examples:
   - "A2 landed at commit a09ae0a → grep for `_pending_A2`"
   - "V25 (open) shows A2 has no gap-detection API → grep for
     `expect A2 to detect`"
   - "case_005 v1 paused on V20 → grep INDEX.md and case_proposal_queue
     for stale `deferred awaiting resources` on case_005"

2. **Scan**:
   ```bash
   grep -rln "<stale phrase>" .planning/ --include="*.md"
   ```
   Then `grep -n` per file to see exact lines.

3. **Categorize hits**:
   - **Live SSOT** (must update): kickoff files, INDEX.md,
     case_proposal_queue.md, V-row Status fields
   - **Audit trail** (preserve): harvest reports, draft patches,
     codex_response files, validation reports closed with old
     framing
   - **Methodology** (apply convention): V-rows / S-rows update
     to `[REFUTED]` / `[SUPERSEDED]` / `[VALIDATED]` markers

4. **Apply convention markers** per
   `.planning/methodology/knowledge_status_convention.md`:
   - Don't delete refuted claims; strikethrough + forward link
   - Add `[VALIDATED <date>]` when ≥2 cases validate
   - Add `[QUESTIONABLE <date>]` when capability is implied but
     not coded

5. **One commit per logical unit** (not one big commit):
   - `chore(backfill): <unit>` — e.g., `chore(backfill): A2 LANDED → kickoffs 003-006`
   - `chore(backfill): V25 → A2-capability framing`
   - `chore(backfill): case_005 v1+v2 → INDEX.md + case_proposal_queue`

6. **Write a short backfill record**: append a row to
   `.planning/harvest_reports/_backfill_log.md` (flat list of
   sweeps, not per-cycle reports) — date, trigger, files touched,
   commit shas. Keeps the cumulative decay-correction record
   discoverable without inflating harvest report count.

### Round cap

Per v2.3 governance (Codex review round cap = 3): backfill-sweep
should converge in ≤3 passes. If a single trigger requires more
than 3 backfill iterations, it's actually a `full`-mode signal
— promote and run a real harvest.

## Mode 3 · `mark-questionable` (single-claim marker)

### How it works

User points at a claim; this skill helps draft the convention-
compliant marker.

### Steps (this session does)

1. Ask user (or infer from context):
   - **What claim?** (paste exact text or path:line)
   - **Why questionable?** (which of the 4 criteria fires?)
   - **Verification pending?** (what observable would settle?)
   - **To resolve?** (what evidence would close it?)

2. Draft the marker per
   `.planning/methodology/knowledge_status_convention.md` syntax:

   ```
   > [QUESTIONABLE 2026-05-08]: <claim text>.
   > Verification pending: <observable>.
   > To resolve: <evidence path>.
   ```

3. Edit the target file in place — don't rewrite, just wrap or
   prepend the marker.

4. **No commit per single mark** — accumulate in working tree
   until next harvest cycle batches them into a coherent commit
   ("chore(convention): batch QUESTIONABLE markers from <session>").

## Outputs (authoritative)

This skill never writes to:
- DEC files (governance scope)
- Source code (`ui/backend/...`, `ui/frontend/...`)
- Sub-session sandboxes (`~/Desktop/case_NNN_*/`)
- Live methodology files in `full` mode (the fresh-session
  harvester drafts patches; user/main-session promotes)

This skill writes to:
- `.planning/harvest_reports/<date>_harvest_<NNN>.md` (full mode
  output, written by fresh session not this one)
- `.planning/harvest_reports/_backfill_log.md` (backfill mode
  record)
- `.planning/cross_cuts/<topic>_<date>.md` (snapshot, on material
  change)
- `.planning/patches/draft_<topic>_<date>.md` (full mode drafts)
- Kickoff / INDEX / case_index / case_proposal_queue files
  (backfill mode in-place edits)
- V-row Status fields (mark-questionable + backfill modes)

## Relationship to existing project infrastructure

| Existing artifact | Relationship |
|---|---|
| `.planning/methodology/harvest_session_kickoff.md` | **Source of truth for `full` mode prompt**. This skill reads from it; doesn't replace it. |
| `.planning/methodology/knowledge_status_convention.md` | **Source of truth for status grammar**. This skill applies it. |
| `.planning/harvest_reports/` | Output directory for `full` mode |
| `.planning/cross_cuts/` | Output directory for periodic snapshots |
| `.planning/patches/` | Output directory for `full` mode drafted patches (suggested-only, awaiting promotion) |
| `notion-sync-cfd-harness` skill | Run AFTER `full` mode writes a report — push to Notion Decisions/Sessions DB |
| `codex-relay` skill | Independent; harvester does not run Codex (per harvest_session_kickoff.md guardrails) |
| Kogami subprocess (`scripts/governance/kogami_invoke.sh`) | Independent; opt-in strategic review, not harvest. Don't conflate. |

## Round-cap discipline (per v2.3 / DEC-V61-133)

- **`full` mode**: ≤6 moves per cycle (Move 1-6 in
  harvest_session_kickoff.md). One harvest report per invocation.
  No multi-cycle iteration in single session.
- **`backfill-sweep` mode**: ≤3 passes per trigger. If trigger
  needs more, escalate to `full`.
- **`mark-questionable` mode**: single claim per invocation.
  Batch multiple marks at end-of-session in one commit.

## Self-check before invoking

Ask yourself before running this skill:

1. Am I in `cfd-harness-unified` working directory? If no, stop —
   this is project-specific.
2. Is my requested action one of the 3 modes? If no, this is the
   wrong skill — try `notion-sync-cfd-harness` for sync,
   `codex-relay` for Codex, or just edit the file directly for
   trivial work.
3. Is my requested action ≥3 sub-session sediments + cross-case
   detection? If no, `backfill-sweep` is enough; don't escalate
   to `full`.
4. Am I about to auto-trigger? If yes, stop — this skill is
   user-invoked or main-session-recommended-then-user-confirmed.
   No cron, no schedule.

## Convention reminder

Always reference `.planning/methodology/knowledge_status_convention.md`
when applying status grammar. The skill does not duplicate the
convention; it applies it.
