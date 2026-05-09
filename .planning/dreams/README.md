# `.planning/dreams/` directory

Background-optimizer artifacts produced by the `cfd-harness-dream`
skill. One file per fire, dated to the minute:

```
.planning/dreams/
├── README.md                              ← this file
└── 2026-05-09-1430_dream.md               ← one per fire
```

## What dreams are for

Light-touch knowledge-base consolidation between event-driven
harvest cycles. The dream skill runs four activities per fire:

1. **Compression + dedupe** — V-row / S-row ID collisions, stale
   references, duplicate paragraphs
2. **`[QUESTIONABLE]` marker triage** — age + resolution-evidence
   check; flags markers ready to upgrade or stale enough to alarm
3. **Cross-case pattern synthesis** — light-touch ≥2-instance
   pattern detection from recent V-rows
4. **Sediment detection + harvest routing** — recommends
   `cfd-harness-harvest` full or backfill-sweep mode based on
   pressure score

## What dreams are NOT for

- Deep cross-case synthesis (that's `cfd-harness-harvest` full-mode)
- Auto-fixing methodology files (dreams are advisory; main session
  decides what to land)
- Auto-committing (dreams stay untracked in this directory until
  main session reviews)
- Sub-session dispatching / Codex calls / Notion sync

## Lifecycle

| Dream age | What happens |
|---|---|
| 0-7 days | Stays in `.planning/dreams/`; main session reviews on next active turn; landable items get committed via main-session work |
| 7-30 days | Older dreams remain for audit but become low-relevance (knowledge they reference may have shifted) |
| ≥30 days | Candidate for archive sweep — move to `.planning/dreams/archive/<YYYY-MM>/` (manual; dream skill never moves files) |

## Conventions

- **File naming**: `<YYYY-MM-DD-HHMM>_dream.md` — `HHMM` is local
  time at the fire moment, no seconds (one fire per minute is the
  highest realistic cadence)
- **One artifact per fire** — never overwrite a previous dream;
  if the same minute fires twice, append `-2`, `-3` suffixes
- **Untracked by git** — `.gitignore` should add
  `.planning/dreams/*_dream.md` (this README is tracked; per-fire
  artifacts are not)
- **Brief is good** — dreams should be 100-300 lines; longer
  output is a sign the skill is overstepping its 10-min budget
- **Honest no-ops** — dreams that find no work write the artifact
  with explicit "no findings" sections rather than skip; keeps
  cadence visible

## How to start dreaming

Open a Claude Code session in
`/Users/Zhuanz/Desktop/cfd-harness-unified/` and:

```
/loop 6h /cfd-harness-dream
```

To run a one-off dream without scheduling:

```
/cfd-harness-dream
```

To stop a running loop: `/loop stop` or end the session.

## Cross-references

- `.claude/skills/cfd-harness-dream/SKILL.md` — full skill spec
- `.claude/skills/cfd-harness-harvest/SKILL.md` — event-driven
  sibling for deep harvest
- `.planning/harvest_reports/` — where event-driven harvest output
  lands (committed artifacts; complementary to dreams)
- `.planning/methodology/knowledge_status_convention.md` — Activity
  2 grammar reference
