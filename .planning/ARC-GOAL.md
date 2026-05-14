# ARC-GOAL · V62 Advisor Stack Closure Arc

**Plan SSOT**: [.planning/2026-05-14_v62_charter.md](2026-05-14_v62_charter.md)
**Predecessor**: [V61-198 advisor substrate arc · CLOSED 2026-05-14](ARC-GOAL-V61-198-CLOSED.md)
**Started**: 2026-05-14
**Mode**: milestone-driven (no calendar)
**Selected**: V62-A (Stack consolidation) · user-ratified 2026-05-14 from 3 candidates

> 读这个文件 90 秒能回答：「这个 arc 完了没？」「该不该开新 arc？」「下个 session 接什么？」

---

## North Star（一句话）

> **让 advisor stack 从 "8 个 LANDED 模块" 升级为 "1 个 LANDED stack" — plumbed into `/ai-review` + `/ai-diagnose` live routes · LLM 离线四问门控全通过 · 跨 ≥3 industrial case 的 stack-level e2e 验证 · D-class advisor ≥1 LANDED.**

---

## Done Definition（必须全部命中）

| # | 维度 | 起点 (2026-05-14) | Done 阈值 | 验证方式 |
|---|---|---|---|---|
| 1 | Advisor stack 路由聚合 | 0 (no stack-level route) | **2 routes LANDED · 每条调用 ≥3 advisor 模块** | `grep -E "advisor\|geometry_ingest" ui/backend/routes/ai_*.py` |
| 2 | 四问门控 cross-feature audit | partial (per-advisor LLM-offline OK) | **stack-level 4Q audit + sign-off** | `.planning/audits/v62_stack_4q_audit.md` exists + signed |
| 3 | Stack-level Track C e2e | 0 (V61-198 全 module-level) | **≥ 2 sessions · advisor stack 接管决策** | `ls .planning/retrospectives/*stack_track_c*.md \| wc -l` |
| 4 | D-class advisor LANDED | 0 D-class LANDED | **≥ 1 (D6 or D9 or D10) promoted** | `grep "D-class.*LANDED" .planning/cross_cuts/advisor_coverage_2026-05-09.md` |
| 5 | 雷达图右半轴 AI axis | 9.0 | **≥ 9.5** | `build_radar_v4.py` AI sub-value |
| 6 | 雷达图左半轴维持 | 7.15 (v3) | **≥ 7.20** (顺手关 V61-198 epsilon-margin) | `build_radar_v4.py` left half |

**任一未达成 = V62 不 close**，启动 root-cause retro。

---

## Done 条件**不算** Done 的反命题（防 stack-shipped-but-not-real）

- ❌ 路由 LANDED 但 4Q gate 没过（LLM 离线时报错） → 失败（违反 V130 advisor-not-driver）
- ❌ Stack 路由 plumbed 但 Track C session 仍靠 engineer 手写决策 → 失败（M6 charter 未操作化）
- ❌ D6 LANDED 但 stack 没消费它 → 失败（孤儿 advisor）

---

## 触发性 redirect 条件（命中 → 修改 plan，不算 Done）

| 条件 | 动作 |
|---|---|
| Stack assembly cross-cutting refactor ≥3 service 文件 schema 变 | 升级为完整 charter DEC |
| 任一 milestone 卡 ≥ 3 周 | 跳过 + retro · 不死等 |
| 商业 CAE AI ≥ 6 (Siemens GA / ANSYS GenAI ship) | 战略复审 · V62 可能拉前 OSS readiness |
| 用户工作焦点偏离 ≥1 周（demo/OSS/frontend pull） | 每 Tier 末 review redirect |
| Codex review round cap = 3 命中且仍有 P1 | 用户裁决（继续 / 接受 / 推 sub-DEC） |

---

## Tier 状态板（每 milestone 完成时打勾 + 填 commit hash）

### Tier 1 · 解锁性（M-STACK-ASSEMBLY 必须先）

- [ ] **M-STACK-ASSEMBLY** advisor stack assembly layer · dispatch + composition pattern · commit: `_____`
- [ ] **M-ROUTE-AI-REVIEW** `/ai-review` route scaffold + V-series corpus retrieval + 4Q gate · commit: `_____`
- [ ] **M-ROUTE-AI-DIAGNOSE** `/ai-diagnose` route scaffold + V-series-similarity matching · commit: `_____`
- [ ] **M-4Q-AUDIT** 四问门控 stack-level cross-feature audit + LLM-offline acceptance test framework · commit: `_____`

### Tier 2 · advisor 加宽 + D-class literal closure + stack 验证

- [ ] **M-D6-PROMOTE** D6 extra_body_in_fluid advisor LANDED (closes V61-198 §5.2 D-class waiver) · commit: `_____`
- [ ] **M-STACK-TRACK-1** Stack-level Track C session 1 · case_011 v5b re-run with stack routing · retro: `_____`
- [ ] **M-STACK-TRACK-2** Stack-level Track C session 2 · new numerics class crossover · retro: `_____`
- [ ] **M-DRIFT-V2** stack-level corpus drift hook (V-series ↔ runtime corpus enforcement at /ai-review boundary) · commit: `_____`

### Tier 3 · charter close + V63

- [ ] **M-STACK-TRACK-3** Stack-level Track C session 3 · validation case · retro: `_____`
- [ ] **M-RADAR-V4** capability radar v4 · 右半轴 AI ≥ 9.5 + 左半轴 ≥ 7.20 · commit: `_____`
- [ ] **M-V63** V62 close DEC + V63 charter draft · commit: `_____`

---

## 进度计数器（每 session 末更新）

```
当前 stack-level 路由 LANDED:           0 / 2
当前 4Q audit 状态:                    not started
当前 stack-level Track C session:       0 / 3
当前 D-class advisor LANDED:            0 / 1
当前右半轴 AI axis:                    9.0 / 9.5
当前左半轴均分:                        7.15 (v3) / 7.20
```

最后更新时间：`2026-05-14 (V62 charter Accepted · V61-198 CLOSE Accepted · arc transition · 10-12 milestones · 14-21 days estimated based on V61-198 7-day actual)` · 更新人：`Claude Code Opus 4.7 session (main · V62 charter finalize)`

---

## 关键依赖图

```
M-STACK-ASSEMBLY  ─┬─→  M-ROUTE-AI-REVIEW   ──┐
                   │                          ├──→  M-4Q-AUDIT  ──→  M-STACK-TRACK-1
                   └─→  M-ROUTE-AI-DIAGNOSE  ─┘                       │
                                                                       ↓
                                                  M-D6-PROMOTE ────→  M-STACK-TRACK-2
                                                                       │
                                                  M-DRIFT-V2     ────→ │
                                                                       ↓
                                                              M-STACK-TRACK-3
                                                                       │
                                                                       ↓
                                                              M-RADAR-V4  ──→  M-V63
```

M-STACK-ASSEMBLY 是结构性 blocker · 路由 + audit 都 depend on it.

---

## 沿用 V61-198 §不变规则

- LLM offline 四问门控 (V130 thesis)
- advisor 不是 driver · 只 advise · engineer 最终决策
- 双 corpus drift-prevention hook (M-DRIFT v1) 保留 + V62 加 stack-level v2
- session-end Notion sync (仅 Accepted DECs · v2.3 round-1 rule)
- DEC scope-driven: ≥3 共享代码路径 / governance-rule-change → charter
- Codex 1-sync-trigger (auth/signing/security boundary · ≥3 round cap)

---

## v2.3 governance 合规

- V62-A 跨 routes/ai_*.py + services/advisor_stack.py (新建) ≥ 3 共享代码路径 → **首个 sub-DEC 落地时 elevate 到完整 charter DEC**
- Codex review: routes/ai_*.py 是 security boundary (operator-facing) → **每个 route PR 必走 Codex review (86gs gpt-5.4 xhigh baseline)** pre-merge
- Kogami opt-in (用户主动召唤)
- counter 纯遥测

---

## 下一步建议（每次会话末由 main session 写）

> **2026-05-14 V61-198 CLOSE + V62 charter Accepted** · V62-A North Star ratified.
> Tier 1 unblock starts with M-STACK-ASSEMBLY (advisor stack assembly layer · dispatch + composition).
>
> **下一会话候选**：
> 1. **M-STACK-ASSEMBLY** (Tier 1 critical · structural blocker for routes + audit · ~3-5 day sub-DEC)
> 2. **M-ROUTE-AI-REVIEW** (后 M-STACK-ASSEMBLY · security-boundary route work · Codex 必走)
> 3. **M-D6-PROMOTE** (parallel · D-class literal closure · independent of stack assembly)
>
> **推荐**：**M-STACK-ASSEMBLY** — 唯一结构性 blocker · 必须先 LAND 路由才能挂。
