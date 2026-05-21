# RESUME — Next session checkpoint (2026-05-21)

> Drop this file once Phase E is fully closed; until then, **read me first** when picking up.

## Where the work stands

AI-CFD-V2 → cfd-harness-unified `ui/backend/audit/` merge is **5 phases complete, 7 commits landed on local feature branch, NOT pushed yet**. User explicitly chose to defer push + archive until Codex review (v2.3 round cap=3) per DEC-V61-201 governance discipline.

## What is on disk (do not duplicate)

- Worktree: `/Users/Zhuanz/Desktop/cfd-audit-merge/` on branch `feature/audit-cfdtrust-merge`
- Source repo: `/Users/Zhuanz/Desktop/cfd-harness-unified/` still on `codex/v4-import-blueprint-fidelity` (untouched throughout merge)
- Source archive target: `github.com/kogamishinyajerry-ops/AI-CFD-V2` (still live, not yet archived)
- `/Users/Zhuanz/Desktop/AI-CFD-V2/` (still active local repo; will be archived only after merge accepted)

## Commits on the feature branch (7)

```
7952c79 docs(DEC-V61-201): charter DEC for AI-CFD-V2 → audit subsystem merge
d7e44db fix(audit): close phantom + test fixture gaps post-migration (Phase D finalize)
5d607d0 feat(audit): land CWOS governance + tools + docs + .claude/agents/
26925e0 feat(agents): import 13 AI-CFD-V2 agents scoped to ui/backend/audit/
6b41176 feat(audit): land cfdtrust_tests/ + cases/ from AI-CFD-V2
e2e25f5 feat(audit): land cfdtrust/ source package from AI-CFD-V2
633d55c chore(audit): create audit/ subsystem skeleton for AI-CFD-V2 merge
```

## State signals

- Tests: 360 passed / 1 skipped (identical to AI-CFD-V2 baseline)
- Cockpit: AMBER (matches pre-merge — 2/3 cases still mocked solver; channel real-validated 2.22% vs NASA)
- Phantom evidence count: 0
- main branch: untouched
- codex/v4 branch: untouched
- Kogami workflow files (P-1..P-5): untouched

## What MUST happen next session (in order)

1. `cd /Users/Zhuanz/Desktop/cfd-audit-merge`
2. `codex-review-relay --base main` to get Codex review of the 7 commits
3. If `CHANGES_REQUIRED`: iterate fix commits, re-run review (v2.3 round cap=3 — max 3 rounds)
4. If `APPROVE`: 
   - `git push origin feature/audit-cfdtrust-merge`
   - Update DEC-V61-201 frontmatter `status` from `Proposed` to `Accepted` + record Codex round count
   - `gh repo archive kogamishinyajerry-ops/AI-CFD-V2`
   - Add migration note to `/Users/Zhuanz/Desktop/AI-CFD-V2/README.md` pointing at the merge commit SHA and DEC-V61-201
   - Commit AI-CFD-V2/README change + push to AI-CFD-V2 origin
   - Delete this RESUME file

## What MUST NOT happen

- Do NOT `git merge` feature/audit-cfdtrust-merge into main locally. Wait for PR + user approval.
- Do NOT modify Kogami files (P-1..P-5) — would require user + Codex ratification per CLAUDE.md.
- Do NOT alter the 3 historical CWOS events that were rewritten in Phase D unless you've read the rationale in DEC-V61-201 §Trade-offs and have a better fix.
- Do NOT delete the AI-CFD-V2 GitHub repo (user chose archive, not delete).

## Key decisions made (user-ratified 2026-05-21)

| Question | User's choice |
|---|---|
| Direction after strategy-director review | Aggressive option: fork AI-CFD-V2 into cfd-harness-unified/audit/ |
| Agent scope | All 13 agents migrate |
| Governance | CWOS limited to audit subsystem internal |
| Code location | ui/backend/audit/ |
| Source repo disposition | Archive (read-only), don't delete |
| Push timing | Deferred until Codex review APPROVE |

## File paths cheat sheet

- DEC: `.planning/decisions/2026-05-21_v61_201_aicfdv2_merge_audit_subsystem.md`
- audit subsystem README: `ui/backend/audit/README.md`
- pre-migration CWOS backup: `ui/backend/audit/.cwos/agent_events.jsonl.pre_migration_backup`
- 13 agents (dual location): `.claude/agents/` AND `ui/backend/audit/.claude/agents/`
- audit cockpit: `ui/backend/audit/docs/status/COCKPIT.md`
