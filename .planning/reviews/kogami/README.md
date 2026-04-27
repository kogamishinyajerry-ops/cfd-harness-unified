# Kogami-Claude-cosplay Strategic Reviews

This directory holds Kogami subprocess strategic-layer review outputs.
Established by **DEC-V61-087** (Accepted 2026-04-27).

## What Kogami is

A `claude -p` subprocess invoked with the empirically-verified Tier 1 flag combo
(see `DEC-V61-087 §3.1` for the **full** load-bearing flag table — do NOT modify
the wrapper without re-running W0 Q1/Q5 probes). Provides physical-isolation
strategic governance review of artifacts. See `DEC-V61-087 §3` for the complete
isolation contract.

Kogami is the **strategic layer** of the v6.2 three-layer governance:

| Layer | Role | Tool |
|---|---|---|
| Strategic | Kogami | `claude -p --tools ""` subprocess |
| Code | Codex GPT-5.4 | `codex exec` |
| Archive | Notion (write-only from us) | existing sync chain |

Kogami does NOT replace Codex (code review) or the human user (final merge gate).

## Directory layout

Each Kogami review lives in its own subdirectory:

```
.planning/reviews/kogami/<topic_slug>_<YYYY-MM-DD>[_<run_idx>]/
├── review.json              # Kogami output JSON (schema in DEC §3.4)
├── review.md                # Human-readable rendering of review.json
├── prompt.txt               # Full prompt sent to subprocess (debugging / reproducibility)
├── prompt_sha256.txt        # sha256 of prompt.txt (deterministic-input proof)
├── briefing_manifest.json   # source files used to build prompt (hashes, versions)
└── invoke_meta.json         # subprocess metadata (cost, turns, claude version, flag combo)
```

Plus W0 artifacts at the root level:
```
w0_q1_canary_report.json     # Q1 canary regression test results
w0_q5_keyword_report.json    # Q5 keyword sampling results
```

## Naming convention

`<topic_slug>` should be:
- For DEC reviews: `dec_v61_<NNN>` (e.g., `dec_v61_088`)
- For RETRO reviews: `retro_v61_<NNN>` (e.g., `retro_v61_007`)
- For phase reviews: `phase_<phase_id>` (e.g., `phase_p3_t1`)
- For high-risk PR reviews: `pr_<branch_or_topic>` (e.g., `pr_workbench_m5`)
- For arc-size retros: `arc_size_retro_<counter_at_trigger>` (e.g., `arc_size_retro_60`)

If multiple reviews of same topic same day (rare), append `_run_<N>`.

## Review JSON schema

Per DEC-V61-087 §3.4, every `review.json` MUST satisfy:

```json
{
  "verdict": "APPROVE | APPROVE_WITH_COMMENTS | CHANGES_REQUIRED | INCONCLUSIVE",
  "summary": "<2-3 sentence overall judgment>",
  "findings": [
    {
      "severity": "P0 | P1 | P2 | P3",
      "title": "<short>",
      "position": "<artifact section reference>",
      "problem": "<what's wrong>",
      "recommendation": "<how to fix>"
    }
  ],
  "strategic_assessment": "<paragraph on roadmap fit / decision arc coherence>",
  "recommended_next": "<merge | revise | escalate-to-user-discussion>"
}
```

Subprocess returns an outer envelope; wrapper does **two-step extraction** per DEC §3.4:
1. `echo "$RAW" | jq -r '.result'` extracts the inner Kogami JSON string from the envelope
2. The extracted string is then validated with `jq -e '.verdict and .summary and .findings and .strategic_assessment and .recommended_next'`

Schema-invalid → retry once with max-turns=2 → INCONCLUSIVE on second failure.
The INCONCLUSIVE fallback shape is `{"verdict":"INCONCLUSIVE","_meta":{"reason":"schema_validation_failed_2x",...}}`.

## Counter / governance handling

Per DEC-V61-087 §5:
- Kogami review artifact does **NOT** advance `autonomous_governance_counter_v61`
- Kogami review is **NOT** included in retro counter table
- The DEC under review gets a `kogami_review_status: APPROVED|CHANGES_REQUIRED <date> <review_path>`
  frontmatter field (post-V61-088 going forward)
- Kogami CHANGES_REQUIRED on a DEC blocks the DEC from advancing to Status=Accepted

## Hard boundary (Out of Scope per DEC §2 + §Out of Scope hard boundary)

Kogami **CANNOT** approve modifications to:
- `.claude/agents/kogami-claude-cosplay.md` (P-1)
- `scripts/governance/kogami_invoke.sh` (P-1.5)
- `scripts/governance/kogami_brief.py` (P-2)
- `scripts/governance/validate_strategic_package.py` (P-2.5)
- `.planning/methodology/kogami_triggers.md` (P-4)
- `.planning/methodology/kogami_counter_rules.md` (P-5)
- This file (P-3)

Any DEC modifying these requires user explicit ratification + Codex APPROVE.
This is the anti-self-approval hard boundary preventing governance self-inflation.

## Notion sync

Kogami subprocess **physically cannot** call Notion MCP (per `--tools ""` + `--strict-mcp-config`).
Reviews are committed to git here, then synced to Notion via the existing `.planning → Notion`
chain (the same way DECs are synced).

## Tier 1 → Tier 2 escalation

If any of the following occurs:
- Q1 canary regression test (monthly cron) fails
- Anthropic upgrades `claude` CLI and any §3.1 flag combo behavior changes
- Live governance incident is attributed to Kogami exceeding isolation
- OS platform changes (macOS → Linux requires re-verification)

→ trigger an independent DEC for Tier 2 escalation (Docker container or `sandbox-exec`).
Tier 2 is **out of scope** for DEC-V61-087.
