# cfd-harness-unified · Project CLAUDE.md

> Project-specific Claude Code configuration. Inherits from `~/CLAUDE.md` (user-level).
> See user-level for: 模型分工规则 v2.3 (Kogami opt-in · Codex round cap=3 · DEC scope-driven), Codex 调用规则, Subagent 优先原则.
>
> **Established by DEC-V61-087** (Accepted 2026-04-27); **简化 by DEC-V61-133** (B+ governance simplification, 2026-05-07).

---

## Three-layer governance (v2.3 · 2026-05-07 · DEC-V61-133)

This project uses three review layers, with strategic layer **opt-in** post-V133:

| Layer | Reviewer | Trigger | Output location |
|---|---|---|---|
| **Strategic** (opt-in) | Kogami-Claude-cosplay (`claude -p` subprocess, `--tools ""`) | **User explicitly invokes** when wanting an independent strategic review (auto-triggers废止) | `.planning/reviews/kogami/<topic>_<date>/` |
| **Code** | Codex GPT-5.4 / GPT-5.5 (relay CLI) | per RETRO-V61-001 risk-tier · v2.2 1-sync-trigger (security boundary / auth / signing) · **round cap = 3** per V133 | `reports/codex_tool_reports/` |
| **Archive** | Notion (write-only, session-end batch sync) | DEC landing + post-incident retro | Notion Decisions/Sessions DB |

**v2.3 changes from v6.2**:
- Strategic layer is opt-in only; Codex APPROVE alone is sufficient gate for high-risk PR merge (no longer double-necessary)
- Codex round cap = 3 (R0 + 2 fix iterations); after R3 user ratifies remaining P1 or remaining P2/P3 → retro queue
- User remains final authority (can invoke Kogami any time, or override Codex)

## When to consider invoking Kogami (advisory · not mandatory · per V133)

The auto-trigger conditions from old v6.2 are now examples of **when invoking might be high-value** — not requirements:

- Phase-close arcs (post-merge) where strategic narrative coherence matters
- Charter / governance-rule-change DECs where independent second opinion is desired
- Post-incident retros where blind-spot hypothesis benefits from external eyes
- High-risk PRs after Codex APPROVE when blast radius is large

**To invoke**: `bash scripts/governance/kogami_invoke.sh <artifact> <topic> <trigger>` (unchanged path; only the auto-trigger gate is removed).

**Skip clauses unchanged**:
- Single-file ≤50 LOC routine commit (no Kogami value added)
- Codex APPROVE'd verbatim-exception path
- docs-only CLASS-1 changes
- Kogami review of Kogami review (anti-recursion)
- Modification of Kogami's own files (P-1..P-5) — still requires user + Codex ratification

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

## Pre-implementation discipline (per DEC-V61-088 · 2026-05-03)

Before starting any non-trivial implementation work — **≥30 LOC OR new
top-level page/route/service file** — run a 2-step pre-implementation
surface scan and write findings to session memory:

1. **ROADMAP scan** — read the relevant ROADMAP §30/§60/§90-day section,
   identify whether the proposed feature maps to a known item, note its
   current status + planning artifact link.
2. **Existing-implementation grep** — `grep -rin "<feature_keyword>"` over
   `src/ ui/backend/ ui/frontend/src/ scripts/`; read first 60 lines of any
   matched file. If a substantial pre-existing implementation is found,
   STOP and surface to user with disposition options (a) extend / (b)
   parallel new / (c) refactor.

**Top-level file** = new file under `ui/backend/routes/*.py`,
`ui/backend/services/*.py` (top-level, not nested helper),
`ui/frontend/src/pages/**/*.tsx` (top-level page component), or
`scripts/*.py` (user-facing entry point). Internal helpers do NOT count.

**Skip clauses**: routine bugfix on already-located file · CLASS-1 docs-only ·
user explicitly says "rewrite X" · trivial single-file edit ≤10 LOC AND no
new top-level file. Trigger wins on conflict (a 9-LOC edit creating a new
top-level route file → scan mandatory).

**Commit-trailer discipline**:
- When prior implementation found: commit MUST carry
  `Surface-scan-found: <path> · disposition: extend|parallel|refactor`
- When scan finds nothing: commit SHOULD carry `Surface-scan: clean` (optional
  but encouraged — its absence is auditable).

**Interaction with §11 standing rules**: §11.1 freeze defaults to
extend-existing on workbench territory; parallel-new requires
BREAK_FREEZE rationale + Kogami acknowledgment. §11.4 quota accounting is
unchanged; what's new is awareness — check current quota before choosing
parallel-new vs extend on §11.4-tracked paths.

**Out of scope**: does NOT modify §10.5.4a audit-required surface gating
(supplements, does not replace).

See DEC-V61-088 for full rationale, Kogami review trail (2 rounds
APPROVE_WITH_COMMENTS · 9 governance-hygiene findings closed inline), and
RETRO follow-up on close-inline-vs-strict-text-validity convention.

## Inherited rules from `~/CLAUDE.md`

User-level CLAUDE.md governs (v2.3 baseline · 2026-05-07 · DEC-V61-133):
- Model routing v2.3 (Opus 4.7 主驱动 + Codex 4-model 双引擎 · Kogami opt-in)
- Subagent 优先原则 (任务 push 主 context ≥35% 才考虑外包 · 1M ctx 校准)
- Codex 调用 1-sync-trigger (auth / signing / 安全边界) + 2-async-post-merge (byte-repro / E2E ≥3 fail)
- Codex review round cap = 3
- DEC scope-driven (charter / 跨 ≥3 模块 / governance-rule-change 才写完整 DEC)
- Cadence floor THRESHOLD 30
- Surface-scan trailer (V61-088) optional
- Counter pure telemetry
- Notion session-end batch sync
- Codex relay (86gs xhigh primary, CRS high fallback)

This project CLAUDE.md previously added Kogami strategic-layer governance per V61-087.
Per V133 (2026-05-07), Kogami is now **opt-in only** (user explicitly invokes); the
manual invocation path remains operational with all contract files (P-1..P-5)
preserved and Q1 canary verification intact.
