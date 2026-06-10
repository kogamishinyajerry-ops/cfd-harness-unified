---
decision_id: DEC-V92-notion-retirement
title: Retire Notion archive layer · git + GitHub becomes the sole decision-archive channel
status: Accepted
parent_dec: DEC-V61-087 (three-layer governance bootstrap) · DEC-V61-133 (v2.3 simplification)
phase: V92
notion_sync_status: n/a (this DEC retires the channel)
autonomous_governance: false  # external gate — user verdict 2026-06-10 (verbatim): "以后不用Notion了，我认为github已经足够了"; counter N/A per RETRO-V61-001
confidence: high
date: 2026-06-10
---

# DEC-V92-notion-retirement · Notion archive layer retired

## TL;DR

User verdict (2026-06-10, verbatim): "以后不用Notion了，我认为github已经足够了".
The **Archive** layer of the three-layer governance moves from Notion
(write-only mirror, session-end batch sync) to **git + GitHub only**.
`.planning/decisions/` + `.planning/retrospectives/` in git were already
the verifiable SSOT ("冲突时以 git 为准") — this removes the mirror, not
the truth.

## Changes (this commit)

- `CLAUDE.md` three-layer table: Archive row → git + GitHub.
- `CLAUDE.md` sections "Notion 深度同步规则" and "Notion 指挥中枢模型分工
  一致性" retired in place (full original text preserved in git history).
- Session-end checklist: Notion items dropped; replacement = "本会话
  Accepted DEC 已 commit（push 视用户指示）"; non-Notion items (STATE.md
  timestamp / external_gate_queue strike-through / codex report links)
  survive unchanged.
- DEC frontmatter field `notion_sync_status`: frozen as historical —
  existing values untouched; new DECs write `n/a` or omit the field.
- Skill `notion-sync-cfd-harness` + suggested subagent `notion-sync-worker`:
  dormant (not deleted; no remaining trigger path in project docs).

## Unchanged

- Strategic layer (Kogami opt-in) and Code layer (Codex relay) untouched.
- DEC / retro file formats and all other v2.3 governance rules.
- Existing Notion DB pages: left as-is (stale mirror, read-only relic;
  never authoritative).
- `NOTION_TOKEN` in `~/.zshrc`: untouched (user-owned credential).

## Reversibility

HIGH — git revert of this commit restores the sync rules; Notion pages
were never deleted, so resuming session-end batch sync resumes the mirror.
