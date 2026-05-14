---
decision_id: DEC-V62-A-charter
title: V62-A advisor stack closure arc · charter DEC · elevated from plan-file at first sub-DEC landing (M-STACK-ASSEMBLY)
status: Accepted
parent_dec: V61-198
phase: V62-A charter (Tier 1 unblock + Tier 2 stack validation + Tier 3 close)
notion_sync_status: pending (Notion sync deferred to session-end batch · session 2026-05-14 · Status=Accepted will trigger sync per v2.3 round-1 loosen)
---

# DEC-V62-A-charter · V62-A advisor stack closure arc

## Status

**Accepted 2026-05-14** — elevated from `.planning/2026-05-14_v62_charter.md`
plan-file at the first sub-DEC landing (M-STACK-ASSEMBLY) per V62 charter
§"v2.3 governance 合规":

> DEC scope: V62-A 跨 routes/ai_review.py + routes/ai_diagnose.py +
> services/advisor_stack.py (新建) ≥ 3 共享代码路径 → charter-level DEC
> required. 本 charter plan-file 是 ROADMAP-style；首个 sub-DEC 落地时
> elevate to full charter DEC.

The plan-file remains the human-readable roadmap; this DEC is the
governance artifact that anchors the parent_dec field for all V62-A
sub-DECs (M-STACK-ASSEMBLY, M-ROUTE-AI-REVIEW, M-ROUTE-AI-DIAGNOSE,
M-4Q-AUDIT, M-D6-PROMOTE, M-STACK-TRACK-1/2/3, M-DRIFT-V2, M-RADAR-V4,
M-V63).

## North Star (verbatim from plan-file line 13)

> **让 advisor stack 从 "8 个 LANDED 模块" 升级为 "1 个 LANDED stack" —
> plumbed into `/ai-review` + `/ai-diagnose` live routes · LLM 离线四问
> 门控全通过 · 跨 ≥3 industrial case 的 stack-level e2e 验证 · D-class
> advisor ≥1 LANDED.**

## Done Definition (verbatim from plan-file line 17)

| # | 维度 | 起点 (2026-05-14) | Done 阈值 |
|---|---|---|---|
| 1 | Advisor stack 路由聚合 | 0 | 2 routes LANDED · 每条 ≥3 advisor 调用 |
| 2 | 四问门控 cross-feature audit | partial | stack-level 4Q audit + sign-off · LLM offline 全功能 |
| 3 | Stack-level Track C e2e | 0 | ≥ 2 sessions · advisor stack 接管决策 |
| 4 | D-class advisor LANDED | 0 | ≥ 1 (D6 or D9 or D10) promoted |
| 5 | 雷达图右半轴 AI axis | 9.0 | ≥ 9.5 |
| 6 | 雷达图左半轴维持 | 7.15 (v3) | ≥ 7.20 |

任一未达成 = V62 不 close · 启动 root-cause retro。

## Cross-cutting code paths (≥3 = charter scope per v2.3 DEC-V61-133)

1. `ui/backend/services/advisor_stack.py` (新建 by M-STACK-ASSEMBLY · this
   sub-DEC 2026-05-14)
2. `ui/backend/routes/ai_review.py` (M-ROUTE-AI-REVIEW · pending)
3. `ui/backend/routes/ai_diagnose.py` (M-ROUTE-AI-DIAGNOSE · pending)
4. `.planning/audits/v62_stack_4q_audit.md` (M-4Q-AUDIT · pending)
5. `ui/backend/services/geometry_ingest/extra_body_advisor.py` (M-D6-PROMOTE
   sub-DEC already drafted Status=Proposed)

5 paths confirmed → charter scope satisfied.

## v2.3 governance compliance

- **DEC scope**: charter-level DEC required (≥3 共享代码路径 confirmed
  above); this file satisfies that requirement.
- **Codex review**: routes/ai_*.py are security-boundary (operator-facing) →
  each route PR will require Codex review via `codex-review-relay --base
  origin/main` (86gs gpt-5.4 xhigh baseline). The charter itself + first
  sub-DEC land in this session will be Codex-reviewed once together to set
  the V62-A baseline.
- **Round cap = 3**: per V133 unchanged. After R3, remaining P1 → user
  ratification; remaining P2/P3 → retro queue.
- **Kogami**: opt-in only per V133; no auto-trigger on this charter.
- **Notion sync**: deferred to session-end batch; only Status=Accepted
  DECs sync per v2.3 round-1 loosen.

## Tier dependency map

```
M-STACK-ASSEMBLY (this session, sub-DEC) ──┬─→ M-ROUTE-AI-REVIEW
                                            ├─→ M-ROUTE-AI-DIAGNOSE  ──→  M-4Q-AUDIT  ──→ Tier 2 stack-level Track C
                                            └─→ (M-D6-PROMOTE parallel · already drafted)
```

## Inherited rules from V61-198 (unchanged)

- LLM offline four-question gate (V130 thesis)
- advisor-not-driver: stack composes advisors but never executes
  mutations on case directories
- M-DRIFT v1 (V-series corpus enforcement) preserved · V62 adds v2 at
  /ai-review boundary (M-DRIFT-V2 milestone)

## End of charter DEC

Plan-file `.planning/2026-05-14_v62_charter.md` remains the
operational roadmap (Tier status, milestones, redirect conditions,
counters); this DEC is the governance anchor. Subsequent V62-A
sub-DECs MUST set `parent_dec: V62-A-charter` to chain correctly.
