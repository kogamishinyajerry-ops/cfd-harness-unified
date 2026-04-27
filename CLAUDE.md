# cfd-harness-unified · Project CLAUDE.md

> Project-specific Claude Code configuration. Inherits from `~/CLAUDE.md` (user-level).
> See user-level for: 模型分工规则 (四角色架构 v6.2), Codex 调用规则, Subagent 优先原则.
>
> **Established by DEC-V61-087** (Accepted 2026-04-27).

---

## Three-layer governance (v6.2 · 2026-04-27 onwards)

This project uses three independent review layers:

| Layer | Reviewer | Trigger | Output location |
|---|---|---|---|
| **Strategic** | Kogami-Claude-cosplay (`claude -p` subprocess, `--tools ""`) | per `.planning/methodology/kogami_triggers.md` | `.planning/reviews/kogami/<topic>_<date>/` |
| **Code** | Codex GPT-5.4 (independent CLI) | per RETRO-V61-001 risk-tier triggers | `reports/codex_tool_reports/` |
| **Archive** | Notion (write-only, via existing sync) | DEC landing + post-incident retro | Notion Decisions/Sessions DB |

**Both Kogami and Codex APPROVE required for high-risk PR merge** (double-necessary, neither sufficient).
**User remains final authority** (can override either with explicit ratification).

## Kogami trigger checklist (per DEC-V61-087 §4)

Before any of the following, run `bash scripts/governance/kogami_invoke.sh <artifact> <topic> <trigger>`:

- [ ] Phase-close (if phase-dir model used) — input = phase CONTEXT.md + PLAN.md + commit list
- [ ] RETRO draft committed to git, before Notion sync — input = RETRO file
- [ ] High-risk PR after Codex APPROVE, before merge — input = DEC + intent_summary + merge_risk_summary + Codex verdict ENUM
- [ ] counter ≥ 20 arc-size retro — input = arc DEC titles + frontmatter
- [ ] Any autonomous_governance rule-change DEC — input = proposed DEC

**Skip Kogami when** (per DEC §4.2):
- Single-file ≤50 LOC routine commit
- Codex APPROVE'd verbatim-exception path
- docs-only CLASS-1 changes
- Kogami review of Kogami review (anti-recursion)
- Modification of Kogami's own files (P-1..P-5) OR meta-DECs touching DEC-V61-087 / its successors / Kogami contract

## Strategic package authoring (high-risk PR only)

Author must produce two YAML files alongside the linked DEC:
- `intent_summary.md` — see DEC-V61-087 §4.4 schema (`roadmap_milestone`, `business_goal`, `affected_subsystems`, optional `rationale`)
- `merge_risk_summary.md` — see DEC §4.4 schema (`risk_class`, `reversibility`, `blast_radius`, optional `rationale`)

Validation: `python3 scripts/governance/validate_strategic_package.py --intent <p> --risk <p>`
Schema-invalid → wrapper exits non-zero → review not triggered → fix schema first.

## Counter rules (per DEC-V61-087 §5 + RETRO-V61-001)

- `autonomous_governance_counter_v61` continues to be the RETRO-V61-001 telemetry counter
- Kogami review artifacts are **NOT** counted (advisory chain · counter +0)
- Kogami CHANGES_REQUIRED on a DEC blocks the DEC from advancing to Status=Accepted
- Kogami INCONCLUSIVE does NOT block but requires entry in next RETRO; 3+ INCONCLUSIVE within counter ≤5 triggers mini-retro
- Counter Interpretation B (STATE.md `last_updated` = SSOT) is canonical going forward (per W3 Kogami P2-2 finding)

## Tier 1 → Tier 2 escalation

If any of the following occurs, trigger an independent DEC for Tier 2 OS sandbox upgrade:
- Q1 canary regression test fails (`scripts/governance/verify_q1_canary.py`, dependency-triggered: claude CLI version change — runs in wrapper before each Kogami invocation if `claude --version` differs from baseline)
- Anthropic upgrades `claude` CLI and any §3.1 flag combo behavior changes
- Live governance incident attributed to Kogami exceeding isolation
- Q5 keyword sampling shows new content-leak vector (`scripts/governance/verify_q5_keyword_sampling.py`)
- OS platform changes (macOS → Linux requires re-verification)
- P-2.5 sampling audit finds ≥3 paraphrase laundering instances

Tier 2 implementation options (out-of-scope for DEC-V61-087):
- macOS `sandbox-exec -p '(deny default) (allow file-read* (subpath "$BUNDLE_DIR"))'` (deprecated but works)
- Docker container with bind-mount only briefing dir + `ANTHROPIC_API_KEY` injection
- Linux `bwrap` (bubblewrap) namespace isolation

## Files comprising the Kogami workflow (do NOT modify without Codex + user ratification)

- `.claude/agents/kogami-claude-cosplay.md` (P-1: agent system prompt)
- `scripts/governance/kogami_invoke.sh` (P-1.5: claude -p wrapper)
- `scripts/governance/kogami_brief.py` (P-2: briefing prompt builder)
- `scripts/governance/validate_strategic_package.py` (P-2.5: strategic package validator)
- `.planning/reviews/kogami/README.md` (P-3: review directory convention)
- `.planning/methodology/kogami_triggers.md` (P-4: trigger rules)
- `.planning/methodology/kogami_counter_rules.md` (P-5: counter rules)
- `.planning/decisions/2026-04-27_v61_087_kogami_cosplay_bootstrap.md` (P-7: this DEC)

## Verification scripts (run on `claude` CLI version change · NO calendar gating)

> Per 项目"禁用日期/调度门控"原则: scripts run on dependency triggers, not timers.
> Q1 canary auto-runs from `kogami_invoke.sh` when `claude --version` differs from `.planning/governance/claude_version_baseline.txt`.

- `python3 scripts/governance/verify_q1_canary.py` — Q1 canary regression test (target: 5/5 zero leaks)
- `python3 scripts/governance/verify_q5_keyword_sampling.py` — Q5 keyword sampling (target: 0 content hits)
- `python3 scripts/governance/verify_q4_counter_truth_table.py` — Q4 counter truth table compatibility (target: 0 drift)
- `bash scripts/governance/test_strategic_package.sh` — P-2.5 schema validator (target: 8/8 pass)

## Inherited rules from `~/CLAUDE.md`

User-level CLAUDE.md governs:
- Subagent 优先原则 (any work pushing main context > 20% should be subagent-outsourced)
- Codex 必须调用场景 (RETRO-V61-001 risk-tier triggers)
- Notion 深度同步规则 (DEC + RETRO sync cadence)
- v6.1 自主治理规则 (counter cadence, retro triggers, Codex per-risky-PR baseline)
- Verbatim-exception 5 条件
- Codex 账号自动切换 (`cx-auto 20 && codex exec ...`)

This project CLAUDE.md adds the Kogami strategic-layer governance ON TOP OF the above
(does not replace any of it). Codex code-layer review remains mandatory per RETRO-V61-001
risk-tier triggers; Kogami strategic-layer review is added per DEC-V61-087 triggers.
