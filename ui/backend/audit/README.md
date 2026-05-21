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
