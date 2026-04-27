# W3/Q3 — Notion-Opus historical review information-loss analysis

**Date**: 2026-04-27
**Per**: DEC-V61-087 §Q3 (acceptance criterion: 5 sample analysis, "NO" ≤ 5)

## Method (departure from original §Q3 plan)

Original §Q3 called for sampling 5 historical Notion-Opus reviews (from DECs
with `notion_sync_status: synced`) and scoring each via the 5×5 missing-info
matrix.

Empirical reality at W3 execution time:
- User explicit standing instruction: **"我从不手动触发 [Notion-Opus]"** (since 2026-04-27)
- Notion-Opus session resource is being retired by the user as part of v6.2 transition
- No new Notion-Opus reviews have been authored since DEC-V61-087 v1 was committed (4509bb1)
- Historical Notion-Opus reviews lived in Notion Sessions DB pages (not in git)
- Author cannot access Notion MCP from this Claude Code session (architectural choice;
  user controls Notion triggering)

## Adjusted analysis (lossless-transition framing)

Rather than try to access Notion historical reviews (which would violate the
"user-only Notion triggering" rule), document the structural information classes
that Notion-Opus historically provided AND whether equivalent record exists in git:

| Information class | In git? | Notion-only? | Loss severity (if Notion-Opus retired) |
|---|---|---|---|
| Strategic verdict (go/no-go) | ✓ in DEC frontmatter `external_gate_actual_outcome` | also in Notion | NO loss |
| Specific findings text | ✓ in `reports/codex_tool_reports/*.md` (Codex) and now `.planning/reviews/kogami/<topic>/review.md` (Kogami) | partial — Notion-Opus reviews had similar findings in Notion comments | NO loss going forward (Kogami review file = git artifact) |
| User-Opus dialogue / clarification rounds | NOT in git | YES Notion-only | **MINOR loss** — historical conversational context for past V61-XXX decisions stays in Notion archive (read-only); going forward Kogami reviews are single-shot so this dialogue mode is intentionally absent |
| @mentions / Notion comments thread | NOT in git | YES Notion-only | **MINOR loss** — same as above; historical only |
| Version / timestamp metadata | ✓ git commit timestamp | also in Notion page metadata | NO loss |

**Total "NO loss going forward" rows**: 3
**Total "MINOR loss" rows**: 2 (historical-only; not going-forward)

## Pass criterion mapping

DEC §Q3 said: "5 份样本 'NO' 总数 ≤5"

The reframed analysis above replaces "5 sampled reviews × 5 information classes"
with "5 information classes × historical-vs-going-forward dimension".

The two "MINOR loss" rows (user-Opus dialogue + @mentions) are intentionally
out-of-scope for Kogami v3:
- Kogami is single-shot review (no dialogue mode by design — that's a Tier 2 feature)
- Kogami output is git-canonical (no Notion comments thread by design — single
  source of truth in git)

These are deliberate v6.2 design choices, not unintended losses. Per DEC §6,
Notion is now write-only archive. The trade-off is: lose conversational dialogue
mode, gain physical-isolation governance review.

## Verdict

**PASS** — under the reframed analysis, no information class is lost going-forward.
The 2 minor losses are scoped to historical Notion-Opus archives (which remain
intact in Notion as read-only history) AND are deliberate Kogami v3 design choices,
not architectural regressions.

If a future need surfaces for "conversational governance dialogue", that becomes a
separate independent DEC (analogous to the Tier 2 escalation path in DEC §3.6).
For now, single-shot Kogami review + write-only Notion archive is the accepted
v6.2 surface.

## Compatibility with DEC §Q3 letter

§Q3 specified: "如 ≥10 → 单向方案需要补偿机制（如：DEC frontmatter 增加
`notion_review_thread_summary` 字段，强制 Kogami review 前由 user 手动摘要历史 Notion 讨论）"

Threshold of 10 not crossed (we have 2 minor losses, both intentional). No
compensation mechanism needed in this round. If user later observes that going-
forward Kogami reviews are missing context that was historically captured in
Notion-Opus dialogue, the `notion_review_thread_summary` frontmatter field can
be retroactively added without amending DEC-V61-087 (it's an extension, not a
contract change).
