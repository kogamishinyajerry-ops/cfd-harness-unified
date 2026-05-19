---
name: cfd-harness-dream
description: |
  Background optimizer for the cfd-harness-unified knowledge base.
  Runs four light-touch activities per fire: (1) compress + dedupe
  cross-cuts and methodology files for ID collisions / duplicate
  paragraphs / stale references, (2) triage `[QUESTIONABLE]` markers
  against newer evidence, (3) synthesize cross-case patterns from
  recent V-series rows that haven't been promoted to S-playbook,
  (4) detect new sub-session sediment and route to cfd-harness-harvest
  full mode if warranted.

  Designed to be invoked on a recurring `/loop 6h /cfd-harness-dream`
  schedule. Each fire writes ONE artifact to .planning/dreams/ and
  does NOT commit. Main session reviews artifacts on next active
  turn and decides what to land.

  This skill is the night-shift complement to cfd-harness-harvest:
  harvest is event-driven (sediment landed, advisor LANDED, etc.);
  dream is calendar-driven background consolidation.
---

# cfd-harness-dream skill

Project-specific background optimizer. Operates only in
`/Users/Zhuanz/Desktop/cfd-harness-unified/`.

## What this skill is NOT for

- **Not** a replacement for `cfd-harness-harvest` — dream is
  light-touch consolidation; harvest is deep cross-case synthesis
- **Not** a code-mutator — dream NEVER edits source code, NEVER
  edits live methodology / V-series / S-playbook / DEC files
- **Not** an auto-committer — every dream artifact is untracked
  in `.planning/dreams/`; user reviews + decides what to land
- **Not** a sub-session dispatcher — dream observes, doesn't dispatch
- **Not** a Notion syncer / Codex caller / governance triggerer

## Hard guardrails (do NOT violate)

1. **Write only to `.planning/dreams/<YYYY-MM-DD-HHMM>_dream.md`** —
   one file per fire, dated to the minute. Never overwrite.
2. **Never edit live methodology files** — that's harvest's role
   (and even harvest only drafts patches, doesn't auto-apply)
3. **Never commit** — dream artifacts stay untracked. If a dream
   surfaces something worth committing, list it in § "For main
   session to consider committing" within the dream artifact
4. **Never spawn subagents / sub-sessions / Codex calls / Kogami**
5. **Never run advisors / OpenFOAM / build tools**
6. **Time budget: ≤10 min per fire** — read enough to do the four
   activities, then stop. If a deeper investigation is warranted,
   recommend escalation to harvest full-mode in the dream artifact;
   do NOT attempt the deep work in dream
7. **Single-file output** — all four activity sections in one
   artifact; no scratch files, no intermediate writes
8. **Idempotent on no-op** — if no work to do, write the artifact
   with explicit "no work this cycle" sections rather than skip;
   keeps the dream cadence visible in `.planning/dreams/` even
   when quiet

## Four dream activities (execute in order)

### Activity 1 · Compression + dedupe

Targets: `.planning/cross_cuts/`, `.planning/methodology/`,
`.planning/case_profiles/`.

Checks:
- **V-row ID collisions**: grep `^### V[0-9]+ ·` across master
  V-series file + all `.planning/cross_cuts/v_series_*append*.md`;
  flag any V-id appearing in 2+ files with different topics
- **S-row ID collisions**: same for `^### S[0-9]+` and
  `^## S[0-9]+`
- **Cross-cut staleness**: any cross-cut snapshot older than 7
  days that hasn't been superseded by a newer one — flag for
  archive
- **Stale references**: grep for filenames known-deleted (e.g.,
  `case_list.md`, deleted by user 2026-05-07); flag occurrence
  count + file paths
- **Duplicate paragraphs**: simple sliding-hash check on V-series
  + S-playbook paragraphs ≥3 lines; flag suspected dups

Output: § "Activity 1 · Compression + dedupe findings". Each
finding lists file path + line range + recommendation. Do NOT
auto-fix.

### Activity 2 · `[QUESTIONABLE]` marker triage

Targets: all `.planning/` files via `grep -rn '\[QUESTIONABLE\|\[REFUTED\|\[SUPERSEDED\|\[VALIDATED'`.

For each `[QUESTIONABLE YYYY-MM-DD]` marker:
- Compute marker age in days (today - YYYY-MM-DD)
- Look at the marker's "Verification pending: <observable>" field
- Check whether any post-marker commit touches the V-series row,
  advisor file, or case profile that would resolve the observable
- Output decision tier:
  - **GREEN**: marker fresh (≤2 days), no new evidence — leave alone
  - **YELLOW**: marker ageing (3-5 days), new commits touch related
    files but resolution unclear — recommend manual harvest review
  - **RED**: marker stale (≥6 days OR explicit resolution evidence
    found) — recommend upgrade to `[VALIDATED]` / `[REFUTED]` with
    citation
  - **ALARM**: marker stale ≥10 days AND no resolution evidence
    AND verification observable not yet tested — escalate to user

Output: § "Activity 2 · QUESTIONABLE marker triage". Table form:
file:line · marker text · age · tier · recommendation.

### Activity 3 · Cross-case pattern synthesis (light-touch)

Targets: `.planning/methodology/industrial_case_solver_findings.md`
(V-series master) + recent append files in `.planning/cross_cuts/`.

Read the most-recently-added 5-10 V-rows. For each pair (V_a, V_b):
- Are they in the same numerics class?
- Do they share a root-cause keyword (e.g., "Codex CAD", "wall
  function", "STEP timestamp")?
- Could they be promoted to a single S-playbook entry, OR does the
  pair indicate an emerging cross-cutting pattern not yet documented
  in `industrial_case_solver_findings.md` § "Cross-cutting patterns
  observed"?

Constraint: surface patterns with **≥2 V-row instances** only.
Single-instance "could be a pattern" is observation-only.

Output: § "Activity 3 · Pattern synthesis candidates". Each
candidate lists supporting V-rows + proposed S-row (or pattern-row)
text + recommended placement. Do NOT auto-apply.

### Activity 4 · Sediment detection + harvest routing

Targets: `git log --since="<last dream timestamp>" --oneline -- .planning/methodology/industrial_case_solver_findings.md .planning/case_profiles/ .planning/cross_cuts/` AND
`ls ~/Desktop/case_NNN_*/evidence/ -la` since last dream.

If new sediment found (≥1 new V-row OR ≥1 new sandbox `evidence/vN/`
directory since last dream):
- Compute "harvest pressure score" = new V-rows × 1 + new
  sandboxes × 3 + advisor LANDED commits × 5
- If score ≥ 5: recommend `cfd-harness-harvest` full-mode in next
  active session
- If score 2-4: recommend `cfd-harness-harvest` backfill-sweep mode
- If score 0-1: no harvest needed; dream alone is sufficient

Output: § "Activity 4 · Sediment + harvest routing". State the
score + recommended action + which sub-session sediments triggered
it.

## Per-fire workflow

1. Read `.planning/dreams/` ls; find most-recent
   `<YYYY-MM-DD-HHMM>_dream.md`. Use its timestamp as "since"
   boundary for git diffs.
2. Run Activities 1-4 in order, capturing findings.
3. Write single artifact at
   `.planning/dreams/<YYYY-MM-DD-HHMM>_dream.md` (today's date +
   current hour:minute, UTC or local — be consistent within the
   project).
4. End with § "For main session to consider committing": list of
   actionable items the main session might want to address. ≤5
   items. Each item: brief description + estimated effort.
5. End with § "Next dream fire expected": ETA based on cadence
   (e.g., "in ~6h, around 14:00 local").
6. Stop. Do NOT commit. Do NOT spawn agents. Do NOT continue work.

## Dream artifact template

```markdown
# Dream · <YYYY-MM-DD HH:MM>

> Cadence: every 6h via local /loop. Previous dream:
> `<YYYY-MM-DD-HHMM>_dream.md`. Time since last fire: <Nh Mm>.

## Activity 1 · Compression + dedupe findings

<findings table or "No new collisions / stale refs detected this cycle.">

## Activity 2 · QUESTIONABLE marker triage

<table: file:line · marker · age · tier · recommendation>

## Activity 3 · Pattern synthesis candidates

<list of ≥2-instance patterns OR "No new patterns above threshold this cycle.">

## Activity 4 · Sediment + harvest routing

- Sediment delta since last dream: <list>
- Harvest pressure score: <N>
- Recommended action: <full / backfill-sweep / none>

## For main session to consider committing

1. <item>
2. <item>
...

## Next dream fire expected

~<duration> from now (cadence: 6h, /loop dependent on Codex
session being open).
```

## Boundaries summary

You CAN:
- Read all `.planning/`, `~/Desktop/case_NNN_*/evidence/` files
- Run `git log` / `git diff` for sediment detection
- Write ONE dream artifact per fire to `.planning/dreams/`
- Recommend escalation to `cfd-harness-harvest`

You CANNOT:
- Edit any file outside `.planning/dreams/`
- Commit anything
- Spawn subagents / sub-sessions / Codex calls
- Modify governance / DECs / methodology files in-place
- Auto-apply patches drafted by harvest
- Take more than 10 min per fire

## How user starts the loop

```
/loop 6h /cfd-harness-dream
```

To stop the loop: send `/loop stop` or end the Codex session
(loop only fires while session is open).

To run a one-off dream without scheduling: just `/cfd-harness-dream`.

## Cross-references

- `.Codex/skills/cfd-harness-harvest/SKILL.md` — sibling skill for
  event-driven deep harvest
- `.planning/methodology/knowledge_status_convention.md` —
  `[QUESTIONABLE]` marker grammar (Activity 2 input)
- `.planning/methodology/industrial_case_solver_findings.md` —
  V-series master (Activity 3 input)
- `.planning/dreams/README.md` — directory convention
- DEC-V61-198 — strategic philosophy SSOT
