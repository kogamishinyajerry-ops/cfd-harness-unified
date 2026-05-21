# audit/ — Trust Contract Subsystem (merged from AI-CFD-V2)

This subdirectory is the **CFD trust-contract audit engine** merged into
`cfd-harness-unified` on 2026-05-21 from the standalone repo
`kogamishinyajerry-ops/AI-CFD-V2` (now archived).

## What lives here

| Path | Purpose |
|---|---|
| `cfdtrust/` | Python package — manifest loader, 6-gate audit (geometry/mesh/bc/solver/qoi/reference), report assembler, CLI (`cfdtrust run`, `audit`, `report`, `explain`, `doctor`) |
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

## Cockpit overall_status: RED is honest (not a bug)

After the merge, `tools/cwos_status.py` reports `phantom_count = 4`. These
are events from PH0-BOOTSTRAP, PH0-AGENTS-001, PH0-SKILLS-001, and
REDTEAM-ROUND14-META-FIX whose evidence paths point to files that live
at the cfd-harness-unified project root (e.g. `CLAUDE.md`,
`.gitignore`, `.claude/skills/plan-sprint/SKILL.md`) — OUTSIDE the
audit subsystem boundary.

This is **architectural phantom**, not validation drift. The files DO
exist (in cfd-harness-unified at large); they just aren't resolvable
from the audit subsystem's REPO_ROOT. Per CLAUDE.md §Non-negotiable #11
"Do not hide mocked execution" we surface this honestly. The marker
event `MERGE-AICFDV2-INTO-AUDIT` records the merge boundary as the
authoritative explanation.

If a future audit needs to relax this gate, two options exist:
(a) extend `cwos_paths.evidence_paths_all_safe_and_exist` with a
"resolve relative to ancestor repo root if missing locally" fallback;
(b) rewrite the 4 historical events' evidence to in-subsystem
equivalents (potentially destructive — history would no longer point
to the original validation artifacts). Neither is in scope at merge time.

## Migration provenance

- Source repo: github.com/kogamishinyajerry-ops/AI-CFD-V2 (archived after merge)
- Source SHA at merge: see commit `feat(audit): land cfdtrust/ source package from AI-CFD-V2` body
- Pre-migration CWOS state backed up at `.cwos/agent_events.jsonl.pre_migration_backup`
- Path rewrites performed in events.jsonl:
  - `"src/cfdtrust/<path>"` → `"cfdtrust/<path>"` (src/ middle layer removed)
  - `"tests/<path>"` → `"cfdtrust_tests/<path>"` (renamed to avoid clash with cfd-harness-unified/tests/)
