---
decision_id: DEC-V61-199
dec_id: V61-199
title: Anthropic agent canon adoption · sub-agent return budget · /goal passes field · canon section · anti-orchestration guard
status: Accepted
parent_dec: V61-133
parent_artifacts:
  - ~/CLAUDE.md (global; v2.3 + Anthropic Agent Canon 采纳要点 section appended 2026-05-12)
  - ~/.claude/projects/-Users-Zhuanz/memory/reference_anthropic_agent_canon.md (new global memory · 9 sources + 5 techniques)
  - ~/.claude/projects/-Users-Zhuanz/memory/project_cfd_canonical_eval_set.md (new project memory · eval-set seed)
  - ~/.claude/projects/-Users-Zhuanz/memory/MEMORY.md (index updated)
phase: governance · meta · v2.3 increment
trigger: User mandate 2026-05-12 — "把 Anthropic agent 经验采纳到 claude code 和开发工作流" after surveying Anthropic engineering blog 2025-09..2026-Q1 series (context engineering / long-running harness / agent skills / writing tools / multi-agent research / evals / 2026 trends report)
autonomous_governance: true
counter_impact: +1
counter_value_after: 31 (V133 was 30; intermediate DECs V134..V198 sit in B-extend arc and APU bay pivot)
codex_review_relay: SKIPPED (governance-rule-change, not code; no risk-tier trigger; user-confirmed adoption of external industry-published best practices)
kogami_review_path: SKIPPED (v2.3 §1 — Kogami opt-in; user did not summon)
notion_sync_status: pending session-end batch
authored_by: Claude Code Opus 4.7 (1M context)
authored_at: 2026-05-12
confidence: high (narrow scope, additive only, reversible by removing one CLAUDE.md section)
---

# DEC-V61-199 · Anthropic agent canon adoption

## 1. Why now

The Anthropic engineering blog has, over 2025-09..2026-Q1, published a coherent
series on agent engineering that codifies practices we have been **converging
on independently** through cfd-harness-unified's v2.0..v2.3 governance arc:

- Context-as-scarce-resource → our v2.3 §3 minimal DEC frontmatter
- Note-taking external memory → our STATE.md / RESUME.md / DEC corpus
- Sub-agent isolated context → our `~/CLAUDE.md 长项目 · Subagent 使用规则`
- Single-agent + context-aware prompt ≥ multi-agent (Anthropic harness paper) → our v2.3 §1 Kogami opt-in retreat
- DEC scope-driven + spike-class first-class → our v2.3 round-1 loosen

That convergence is itself evidence the direction is correct. This DEC
**adopts the 3 specific increments** Anthropic's writing makes hard rules
that we had only soft-applied, and **codifies a guard** against being pulled
into the over-engineered narrative that the same Anthropic also publishes
(2026 Agentic Coding Trends Report's "orchestration era" framing).

## 2. What changes (3 hard rules + 1 guard)

### Rule 1 · Sub-agent return budget ≤ 2000 tokens

Source: *How we built our multi-agent research system* (Anthropic, 2025-06).

**Landed in `~/CLAUDE.md` Subagent 协议 §5** (2026-05-12):

> 回传预算 ≤ 2000 tokens：briefing 必须显式写 `report in under 2000 tokens` /
> `summary only, no raw logs`；原始 grep 结果、文件全文、tool stdout 留在
> agent 侧，主 session 只收综合结论 + 关键 path/line 引用。

**Project impact**: Future `gsd-explore`, `gsd-debugger`, `general-purpose`
subagent invocations must carry an explicit return-budget clause in their
prompt. No tooling change required; this is a prompt-discipline rule.

### Rule 2 · /goal Pattern A `passes` field

Source: *Effective harnesses for long-running agents* (Anthropic, 2025).

**Landed in `~/CLAUDE.md` /goal Pattern A** (2026-05-12): every PLAN.md task
must satisfy both `status: COMPLETED` AND `passes: true`. `passes` flips to
true **only after** E2E smoke / pytest / human verification — not on commit.

**Project impact**: starting **N2**, PLAN.md task tables gain a `passes`
column. This directly addresses the N1.1 22-round Codex review chain root
cause (one of several): the absence of a hard E2E gate between "I edited"
and "it works end-to-end". This rule is preventative, not retroactive —
N1.x and earlier phases are not refactored.

**Out of scope**: introducing a new JSON spec file (Anthropic's harness uses
a separate `feature_list.json`). Our PLAN.md already carries task structure;
we add a column, not a new artifact.

### Rule 3 · Tool / Skill description = prompt (transcript-driven iteration)

Source: *Writing effective tools for AI agents* (Anthropic, 2025).

**Landed in `~/CLAUDE.md` Anthropic Agent Canon §四** (2026-05-12):

- namespace prefix grouping (already in use: `gsd-*`, `codex-relay`)
- unambiguous parameter names
- "onboarding paragraph" style description, not API field doc
- **new**: monthly (or retro-triggered) Opus reviews skill-invocation transcripts
  and rewrites `SKILL.md` descriptions based on observed misroute / miss / error.

**Project impact**: the existing skill catalog (`codex-relay`,
`cad-step-stl-prep`, `gsd-*`) gets a maintenance loop. Not auto-triggered;
opt-in like Kogami per v2.3 §1.

### Guard · Reject "orchestration era" over-correction

Source: *Anthropic harness paper* explicitly notes single-agent + context-aware
prompt currently ≥ multi-agent; *2026 Agentic Coding Trends Report* (same
publisher) frames "orchestration era".

**Landed in `~/CLAUDE.md` Anthropic Agent Canon §七** (2026-05-12) as
explicit anti-pattern list:

- Do NOT restart Kogami auto-trigger
- Do NOT restructure cfd-harness into a 3-layer agent hierarchy
- Do NOT replace Codex relay with Agent Teams
- v2.3 simplification direction is correct; continue subtracting, not adding.

**Why this matters as a DEC rule**: external narrative momentum is real and
will reach us through PR reviewers, blog posts, conference talks. Codifying
the rejection in a DEC means the next time someone (including future-me)
proposes "let's split Opus into 4 specialized sub-agents", this DEC is the
linked rebuttal.

## 3. Eval-set seed (new artifact category)

Source: *Demystifying evals for AI agents* (Anthropic, 2025).

Captured in global memory `project_cfd_canonical_eval_set.md` (not committed
to this repo yet — it is **seeded, not started**):

- Target: 10-20 canonical cases drawn from V-series 24-51 corpus
- Purpose: regression test for advisor judgment quality
- Format: `.planning/evals/canonical/case_<id>.yaml`
- Trigger to start: N2 completion + V20+ artifacts fully LANDED
- Anti-scope: NOT a solver-passrate test; NOT for any case >20

**Project impact**: when triggered, this will add a new top-level directory
under `.planning/`. No code or schema change required at adoption time.

## 4. What does NOT change

- v2.3 spike-class definition (≤30 LOC + 1 test + no DEC/Codex/Kogami/Notion)
- v2.3 Kogami opt-in posture
- v2.3 Codex review round cap = 3
- Codex relay dual-backend (86gs xhigh / CRS high) routing
- DEC frontmatter 6 required fields
- AI advisor contract (V130 / V131 / V132)
- Four-question gate (LLM offline / artifacts / TrustGate / advisory-only)
- M1-M6 roadmap v2 sequencing
- APU bay strategic pivot (V61-198) and its 5-artifact extraction

## 5. Sources (verbatim, for audit trail)

1. https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
2. https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents
3. https://www.anthropic.com/engineering/writing-tools-for-agents
4. https://www.anthropic.com/engineering/multi-agent-research-system
5. https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills
6. https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents
7. https://www.anthropic.com/research/building-effective-agents
8. https://resources.anthropic.com/hubfs/2026%20Agentic%20Coding%20Trends%20Report.pdf
9. https://resources.anthropic.com/hubfs/Claude%20Code%20Advanced%20Patterns_%20Subagents,%20MCP,%20and%20Scaling%20to%20Real%20Codebases.pdf

## 6. Reversal cost

Low. To reverse: delete `Anthropic Agent Canon 采纳要点` section from
`~/CLAUDE.md`, revert Subagent 协议 §5, revert /goal Pattern A `passes`
clause, delete global memory files. No code, no schema, no CI changes.
Two-week probation alongside v2.3 (until ~2026-05-26); if observed to
reduce signal density rather than increase it, mark superseded.

## 7. Codex review skip rationale

Per v2.3 §1 risk-tier triggers:
- No auth / signing / security boundary changes → no sync block
- No byte-reproducibility-sensitive path changes → no async post-merge
- No ≥3 E2E test failures → no async batch trigger
- Pure governance documentation; revertable in one delete

Skip is consistent with v2.3 §1 §5 spike-class spirit applied to governance
artifacts: rule changes that are **additive + reversible + author-confident**
do not require Codex relay. If user explicitly summons review, re-evaluate.

## 8. Kogami review skip rationale

Per v2.3 §1: Kogami auto-trigger废止; opt-in only. User mandate was direct
("采纳到我的 claude code 和开发工作流"); no strategic-layer ambiguity
warranting independent reviewer. Skip per v2.3 §1.

---

**Companion artifacts (global, not in this repo):**
- `~/CLAUDE.md` — Anthropic Agent Canon 采纳要点 section (~80 lines added)
- `~/.claude/projects/-Users-Zhuanz/memory/reference_anthropic_agent_canon.md`
- `~/.claude/projects/-Users-Zhuanz/memory/project_cfd_canonical_eval_set.md`
- `~/.claude/projects/-Users-Zhuanz/memory/MEMORY.md` (2 new index lines)

**Linked decisions:**
- parent: DEC-V61-133 (v2.3 governance simplification B+)
- sibling: DEC-V61-130 (AI advisor pivot)
- consumer: future PLAN.md schemas (N2 onward) — `passes` column

**Notion sync**: deferred to session-end batch per v2.3 §10
(Notion syncs only Status=Accepted DECs); this DEC is Accepted at write-time
because user mandate is explicit; sync will land in the next session-end pass.
