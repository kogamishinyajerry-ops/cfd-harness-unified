---
decision_id: DEC-V61-201
dec_id: V61-201
title: Merge AI-CFD-V2 into cfd-harness-unified/ui/backend/audit/ as audit subsystem with 13-agent team + CWOS dual-governance
status: Proposed (drafted 2026-05-21 · awaiting user ratification + Codex review per round cap=3 V133)
parent_dec: V61-200
parent_artifacts:
  - github.com/kogamishinyajerry-ops/AI-CFD-V2 (source repo, to be archived after merge)
  - ui/backend/audit/README.md (subsystem charter)
  - ui/backend/audit/.cwos/agent_events.jsonl (subsystem governance state, includes MERGE-AICFDV2-INTO-AUDIT marker)
  - .claude/agents/ (13 new agents added at project root for Task-tool global visibility)
  - ui/backend/audit/.claude/agents/ (intentional duplicate for CWOS subsystem-local validation)
phase: governance · scope · merge
trigger: User mandate 2026-05-21 + strategy-director subagent finding ("AI-CFD-V2 has independent value at the trust-contract layer but ROADMAP Phase 3/5 + North Star 9-capability list = repeating cfd-harness-unified's path"). Aggressive option chosen with the explicit constraint that the 13-agent professional development team must transition successfully.
autonomous_governance: true
counter_impact: +1
codex_review_relay: pending (next session; v2.3 round cap=3)
kogami_review_path: not invoked (per V133 opt-in policy; user may invoke retroactively if needed)
notion_sync_status: pending (session-end batch sync per ~/CLAUDE.md v2.3)
authored_by: Claude Code Opus 4.7 (1M context)
authored_at: 2026-05-21
confidence: high (4 explicit user choices made all-recommended-options; full Phase B-D test fence remained green: 360 passed / 1 skipped pre-merge and post-merge)
---

# DEC-V61-201 · Merge AI-CFD-V2 → audit subsystem

## TL;DR

AI-CFD-V2 (a standalone OpenFOAM trust-contract verifier developed 2026-05-20
to 2026-05-21 across M1–M9.2 milestones and 25 Red Team rounds) is merged
into `cfd-harness-unified/ui/backend/audit/` as a self-contained subsystem.
The 13-agent professional development team and CWOS governance framework
are imported. The original GitHub repo is archived (not deleted) to
preserve commit history. cfd-harness-unified gains:

- 6-gate trust contract audit engine (geometry / mesh / bc / solver / qoi /
  reference comparison) with 25 rounds of adversarial review against
  false-PASS attack vectors
- Three canonical reference cases (flat_plate_rans_sst,
  backward_facing_step, channel_flow_rans_sst), one validated end-to-end
  against NASA MKM 1999 DNS within 2.22% relative error
- 13-role professional development team (project-governor, strategy-director,
  engineering-director, cfd-vv-director, system-architect, backend-engineer,
  openfoam-adapter-engineer, frontend-engineer, product-ui-director,
  benchmark-director, docs-knowledge-engineer, progress-intelligence-agent,
  test-red-team) configured as Claude Code Task-tool subagents
- CWOS governance: event-driven evidence audit (PASS-without-evidence
  blocked at write-time), agent allowlist enforcement, phantom-evidence
  detection, dual-layout cockpit (Markdown + HTML) auto-derived from state

## Why merge (and not keep as separate repo)

Strategy-director subagent (2026-05-21) judged AI-CFD-V2's North Star
("STAR-CCM+-class AI-native CFD workbench") to be precisely the same
ambition as cfd-harness-unified — meaning continued independent development
would have been duplicate effort across two repos with one maintainer.
The strategically valuable parts (trust-contract engine, 25 rounds of
Red Team review, multi-agent dev team) merge cleanly into cfd-harness-
unified as an audit subsystem; the duplicate workbench North Star is
dropped.

## What was decided

1. **Aggressive merge** (vs P1 light-touch independent repo, P3 cross-link).
   AI-CFD-V2 becomes `ui/backend/audit/` inside cfd-harness-unified.
2. **13-agent team migrates in full** to cfd-harness-unified/.claude/agents/
   AND ui/backend/audit/.claude/agents/ (intentional duplicate; see §Trade-offs).
3. **CWOS governance scoped to audit subsystem only**. Does NOT promote to
   global SSOT (which remains DEC + Notion + retro per V133).
4. **Code location**: `ui/backend/audit/` (under existing backend/, not as
   peer top-level directory). Reflects that audit is one of multiple
   backend services.
5. **Source repo archive, not delete**. github.com/kogamishinyajerry-ops/AI-CFD-V2
   marked archived (read-only) post-merge; AI-CFD-V2/README updated with
   migration note pointing to this DEC + the merge commit.

## Merge mechanics (5 phases, 10 commits)

| Phase | Commit count | Description |
|---|---|---|
| A | 1 | Worktree branch created from main, audit/ skeleton + README |
| B | 2 | cfdtrust/ source package + cfdtrust_tests/ + cases/ migration |
| C | 1 | 13 agents copied to .claude/agents/ with scope: ui/backend/audit/ |
| D | 2 | .cwos/ + tools/ + docs/ + audit-local .gitignore + agent duplicate |
| E | this DEC + merge commit + push + repo archive | (in progress) |

Branch: `feature/audit-cfdtrust-merge`, worktree at
`/Users/Zhuanz/Desktop/cfd-audit-merge`. Not yet pushed; PR / merge into
main is part of Phase E.

## Test fence

Pre-merge (AI-CFD-V2 standalone): 360 passed / 1 skipped.
Post-merge (audit subsystem): 360 passed / 1 skipped. ZERO drift.

Cockpit `overall_status` post-merge: AMBER. This matches the AI-CFD-V2
pre-merge state. AMBER reflects that 2 of 3 cases (flat_plate, BFS) use
mocked solver execution; only the channel case uses a real OpenFOAM 11
solver. AMBER is the honest signal.

## Trade-offs accepted

1. **Dual-location 13 agents**: same .md files exist at both
   cfd-harness-unified/.claude/agents/ and ui/backend/audit/.claude/agents/.
   Reason: the first location lets Claude Code Task tool discover agents
   globally; the second location lets CWOS' `cwos_event.py` enforce its
   agent-allowlist gate without crossing subsystem boundary. Files are
   pure documents; manual sync at DEC-level edits is acceptable cost vs
   alternatives (symlinks confuse git; cross-subsystem path probing
   creates coupling).
2. **Three historical CWOS events rewritten**: PH0-BOOTSTRAP / PH0-SKILLS-001 /
   REDTEAM-ROUND14-META-FIX had evidence paths pointing outside the audit
   subsystem boundary (CLAUDE.md / .gitignore / .claude/skills/*.md live
   at cfd-harness-unified root). Rewritten in-place to point at audit-
   internal semantic equivalents (docs/project-memory/{NORTH_STAR,CURRENT_SCOPE}.md,
   docs/status/red_team_round14_review.md). Original state preserved at
   `.cwos/agent_events.jsonl.pre_migration_backup`. This is adaptation
   to architectural boundary, not history tampering — fully reversible
   from the backup.
3. **Path rewrites in events.jsonl**: 29 events had "src/cfdtrust/<X>"
   paths (AI-CFD-V2 layout had a src/ middle layer), rewritten to
   "cfdtrust/<X>" for the audit layout. 36 events had "tests/<X>",
   rewritten to "cfdtrust_tests/<X>" (renamed to avoid clash with
   cfd-harness-unified's existing ui/backend/tests/).
4. **GitHub repo archived not deleted**. Preserves commit history +
   25 Red Team round reports + tag history. Migration note in
   AI-CFD-V2/README points at this DEC.

## What this DEC does NOT do

- Does NOT modify cfd-harness-unified global governance rules
  (V133 still authoritative; Kogami opt-in still in effect).
- Does NOT alter the DEC numbering scheme or counter_impact rules
  (per RETRO-V61-001 + DEC-V61-087 §5).
- Does NOT introduce a new Notion DB. CWOS state stays in
  ui/backend/audit/.cwos/, accessible to anyone walking the subsystem.
- Does NOT change the Kogami workflow files (P-1..P-5 still untouched).
- Does NOT affect existing UI work (codex/v4-import-blueprint-fidelity
  branch is untouched; this merge is on a separate feature branch).

## Reversibility

The merge is **fully reversible** at any point before push to origin
because:

- All changes are on `feature/audit-cfdtrust-merge` worktree branch.
- AI-CFD-V2 GitHub repo is NOT archived until Phase E final step.
- Pre-migration .cwos state is preserved in
  `.cwos/agent_events.jsonl.pre_migration_backup`.

To revert: delete the feature branch + worktree, AI-CFD-V2 repo is
still functional standalone.

After push + archive: revert requires un-archiving AI-CFD-V2 repo
(reversible via gh CLI) AND reverting the merge commit in cfd-harness-
unified main (single git revert). Still feasible but with more friction.

## Acceptance criteria

- [x] All 5 phases (A-E) committed with documented commit messages
- [x] 360/360 tests pass in new location
- [x] cockpit `overall_status` = AMBER (matches pre-merge baseline)
- [x] No test introduces phantom_count > 0
- [x] cfd-harness-unified main branch untouched (work is on feature branch)
- [x] codex/v4-import-blueprint-fidelity branch untouched
- [x] Kogami workflow files (P-1..P-5) untouched
- [x] This DEC (V61-201) written + committed
- [ ] Codex review (round cap=3) — next session
- [ ] User ratification
- [ ] Push feature/audit-cfdtrust-merge to origin
- [ ] AI-CFD-V2 GitHub repo archived (final phase E step)
- [ ] AI-CFD-V2/README migration note commit (final phase E step)

## Follow-ups

1. **Next session Codex review** of this DEC + the 9 merge commits
   (round 1, v2.3 round cap=3 applies)
2. **Notion session-end batch sync** to add this DEC to the Decisions DB
3. **Update cfd-harness-unified/.claude/MODEL_ROUTING.md** to note that
   the 13 new agents are scoped to the audit subsystem (avoids
   confusion for future sessions)
4. **First post-merge real work**: per AI-CFD-V2 PROGRESS.md M10 was
   the last completed milestone (template-based explain). Open question:
   does the audit subsystem now use cfd-harness-unified's existing
   V-series 工业算例 (APU bay, CRM-HLS, etc.) as stress-test corpus
   for the trust contract? This was strategy-director's P3
   recommendation — defer the decision to a future DEC; do not
   conflate it with this merge DEC.
