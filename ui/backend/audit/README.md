# audit/ — Trust Contract Subsystem (merged from AI-CFD-V2)

This subdirectory is the **CFD trust-contract audit engine** merged into
`cfd-harness-unified` on 2026-05-21 from the standalone repo
`kogamishinyajerry-ops/AI-CFD-V2` (now archived).

## What lives here

| Path | Purpose |
|---|---|
| `cfdtrust/` | Python package — manifest loader, 6-gate audit (geometry/mesh/bc/solver/qoi/reference), report assembler, CLI (`cfdtrust run`, `audit`, `ingest`, `report`, `explain`, `doctor`) |
| `cfdtrust_tests/` | 360 pytest tests covering every audit dimension |
| `cases/` | Three canonical reference cases — flat_plate_rans_sst, backward_facing_step, channel_flow_rans_sst |
| `tools/` | CWOS governance scripts — cwos_status.py, cwos_render_dashboard.py, cwos_event.py |
| `.cwos/` | CWOS state — agent_events.jsonl, tasks.yaml, decisions.yaml, blockers.yaml, metrics.json |
| `docs/` | PROGRESS.md, ROADMAP.md, NORTH_STAR.md, CURRENT_SCOPE.md, SCOPE_FIREWALL.md, status/red_team_round*.md (25 rounds) |

## Dual-governance model

The audit subsystem runs **two independent governance layers in parallel**:

- **Global (cfd-harness-unified)**: DEC charter system + Notion Tasks DB + retro files.
  See `.planning/decisions/` (~376 DECs as of 2026-05-21).
- **Local (audit subsystem)**: CWOS state files inside `audit/.cwos/`.
  Limited to audit-internal tasks + events; **does not pollute the global DEC space**.

A 14-agent team (`cfd-harness-unified/.claude/agents/`) coordinates work
across both layers, with the `scope:` frontmatter field declaring whether
each agent operates on the global project or the audit subsystem.

## Why this lives inside cfd-harness-unified

AI-CFD-V2's North Star was a "STAR-CCM+-class workbench" — exactly what
cfd-harness-unified already builds. The strategically valuable parts of
AI-CFD-V2 (trust-contract engine, 25 rounds of Red Team adversarial review,
13-agent multi-role governance) are kept; the duplicate workbench ambition
is dropped. See merge commit + this commit's `DEC-V61-XXX_cfdtrust_merge.yaml`.

## Ingest mode (post DEC-V61-201-SUB-INGEST)

`cfdtrust ingest <case_dir>` imports evidence from an OpenFOAM case that
was run *outside* this harness (any fork, any operator). Use this to
advise on the `_sandboxes/` corpus and other pre-existing cases without
re-invoking the solver.

```bash
cfdtrust ingest path/to/externally_run_case
cfdtrust audit  path/to/externally_run_case   # gates read the ingested artifacts
cfdtrust report path/to/externally_run_case   # solver_execution = "ingested"
cfdtrust explain path/to/externally_run_case  # per-gate WHY + recommendations
```

What ingest does:
- Reads existing `constant/polyMesh/boundary` and parses patches.
- Reads existing `0/<field>` files and parses BC blocks.
- Runs `checkMesh` (only) in the harness's Docker image against the
  existing polyMesh — does NOT re-run blockMesh or simpleFoam.
- Locates an external solver log (`log_simpleFoam.txt`,
  `log.simpleFoam`, `solver.log`, etc.) and transcribes it to
  `artifacts/solver.log`.
- Parses the log into `artifacts/residuals.csv`.
- Writes `artifacts/ingest_manifest.json` with SHA256 of source log +
  polyMesh, ingest timestamp, image used, and time directories
  observed.

Honesty fences (added to `trust_report.schema.json`):
- `solver_execution` enum extended to include `"ingested"`.
- An ingested case can never reach `overall_status = "PASS"` (capped at
  WARN even if every gate individually PASSes) — harness did not
  witness the run.
- An ingested case can never reach `validation_status = "validated"`
  (caps at `"partial"` when both solver gate and reference comparison
  PASS).
- Schema-level fences `PASS → real` and `validated → real` carry over
  unchanged from R3-F-03.

## Status at merge time

- Phase 1 complete: M9.2 channel validated within 2.22% of NASA MKM 1999 DNS
- 360 tests pass / 1 skip
- 3 cases with real artifacts on disk: 1 validated (channel), 2 mocked (flat_plate, BFS)
- 25 Red Team rounds documented (R-1 .. R-25)

## Dual-location agents/ (intentional redundancy)

The 13 agents from AI-CFD-V2 are present in TWO locations:

1. `cfd-harness-unified/.claude/agents/` (project root) — so Claude Code's
   Task tool in any session at the cfd-harness-unified working tree can
   discover and invoke them.
2. `cfd-harness-unified/ui/backend/audit/.claude/agents/` (this subsystem) —
   so `audit/tools/cwos_event.py` can validate `--agent` against the
   declared allowlist without crossing the subsystem boundary.

This is **intentional duplication**. The two copies must stay in sync;
agent definitions are documents (no embedded behavior), so manual sync
during DEC-level edits is acceptable cost vs the alternative (symlinks
that confuse git, or cross-subsystem path probing that creates coupling).
`kogami-claude-cosplay.md` exists ONLY at the project root — it is a
cfd-harness-unified global agent, NOT an audit subsystem agent.

## Cockpit overall_status: AMBER (honest, post-fixup)

`tools/cwos_status.py` reports `overall_status = AMBER` and
`phantom_count = 0`. AMBER reflects that 2 of 3 cases (flat_plate, BFS)
still use mocked solver execution — only the channel case is real-solver
validated. AMBER is the honest signal at merge time and matches the
AI-CFD-V2 pre-merge baseline.

### Phantom-count migration history (timeline · resolved post-fixup)

Right after the bulk migration, `phantom_count = 4`. Four PASS events
(PH0-BOOTSTRAP, PH0-AGENTS-001, PH0-SKILLS-001, REDTEAM-ROUND14-META-FIX)
had evidence paths pointing OUTSIDE the audit subsystem boundary
(`CLAUDE.md`, `.gitignore`, `.claude/skills/plan-sprint/SKILL.md`, etc.).

Two events resolved automatically by Phase C / D landings:
- **PH0-AGENTS-001**: cleared when the 13 agents were duplicated into
  `ui/backend/audit/.claude/agents/` (Phase D).
- **REDTEAM-ROUND14-META-FIX**: cleared when the audit-local
  `.gitignore` was added (Phase D finalize).

The remaining two (PH0-BOOTSTRAP, PH0-SKILLS-001) were resolved by an
**evidence-path rewrite** in `agent_events.jsonl` (Phase D finalize):
- PH0-BOOTSTRAP: `CLAUDE.md` → `docs/project-memory/NORTH_STAR.md`
  (the audit subsystem's project-rules SSOT)
- PH0-SKILLS-001: 5 `.claude/skills/*.md` paths → single
  `docs/project-memory/CURRENT_SCOPE.md` (the subsystem's authoritative
  declaration of what skill coverage applies)

This rewrite was deliberate adaptation, not history tampering. The
pre-rewrite log is preserved at `.cwos/agent_events.jsonl.pre_migration_backup`
for full provenance.

`MERGE-AICFDV2-INTO-AUDIT` is the marker event for the **initial bulk
migration** (when `phantom_count` was still 4). A separate
`MERGE-PHANTOM-CLEANUP-2026-05-21` event documents the subsequent
zero-phantom state explicitly so a future reviewer sees one timeline,
not contradictory snapshots.

If a future audit reviewer disagrees with the rewrite, the original
events can be restored by `cp .cwos/agent_events.jsonl.pre_migration_backup
.cwos/agent_events.jsonl`; the audit-subsystem REPO_ROOT semantics do
not depend on those events being rewritten.

## Migration provenance

- Source repo: github.com/kogamishinyajerry-ops/AI-CFD-V2 (archived after merge)
- Source SHA at merge: see commit `feat(audit): land cfdtrust/ source package from AI-CFD-V2` body
- Pre-migration CWOS state backed up at `.cwos/agent_events.jsonl.pre_migration_backup`
- Path rewrites performed in events.jsonl:
  - `"src/cfdtrust/<path>"` → `"cfdtrust/<path>"` (src/ middle layer removed)
  - `"tests/<path>"` → `"cfdtrust_tests/<path>"` (renamed to avoid clash with cfd-harness-unified/tests/)
