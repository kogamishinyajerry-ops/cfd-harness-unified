---
decision_id: DEC-V61-239
title: V93 · Agent Crew Observatory — 多 agent 治理回路只读可视化页（/agent-crew）
status: Accepted (autonomous under sponsor mandate 2026-06-10 「把项目的交互UI界面做出来，我想直观的看到这个多agent系统是怎么工作的」)
parent_dec: DEC-V61-226 (workflow-monitor observation-surface precedent) · DEC-V61-133 (governance v2.3 the page visualizes)
phase: V93 (observation surface · NOT workbench shell)
notion_sync_status: n/a (Notion retired per sponsor 2026-06-09)
autonomous_governance: true
confidence: high
date: 2026-06-10
spec: .planning/V93_CREW_UI_SPEC.md
codex_tool_report_path: reports/codex_tool_reports/2026-06-10_v93_crew_ui_R{0,1,2}.md
codex_review_relay: 86gs (gpt-5.4 xhigh · R0 CHANGES_REQUIRED [P1 annotated refs, P2 fabricated fix step] -> R1 CHANGES_REQUIRED [P2 directory refs] -> R2 CHANGES_REQUIRED [P2 self-arc report discoverability, fixed verbatim] · chain closed cap=3)
---

# DEC-V61-239 · Agent Crew Observatory

## TL;DR

新增只读观察页 `/agent-crew`（Layout 证据面，同 /workflow-monitor 先例）：左栏
SVG 拓扑图（Sponsor → Claude 总师 → Subagents → Codex(cap=3) → loop-auditor →
Kogami(opt-in) → Git/DEC 档案，9 条带标签的流向边）；中栏 arc 列表 + 回放条
（按真实字段推导步骤：设计审 → 实现 → R0..Rn verdict → 收口，回放时拓扑图对应
边脉冲）；右栏工件检查器（frontmatter 原文 + Codex 报告节选）。

**数据 100% 解析自真实治理工件**：441 个 `.planning/decisions/*.md`、148 份
`reports/codex_tool_reports/*`、16 次 `.planning/reviews/kogami/*/` invocation
（live API 冒烟实测数字，无一硬编码）。解析不到 → UNPARSED/未记录；verdict 与
P1-P3 计数是启发式正则，UI 显著标注「启发式解析 · 点击看原文」。

## 实施方式（模型路由实践 · sponsor 同日要求「足够重要的地方才用 Fable 5」）

- **Fable 5（总师）**：契约设计（`.planning/V93_CREW_UI_SPEC.md` 钉死 API JSON
  形状/文件清单/honesty 规则/禁令）、diff 验收、死代码清理、live 冒烟、本 DEC。
- **Sonnet ×3（Workflow 编排）**：包 A backend（service+route+16 pytest）与包 B
  frontend（api+page+3 组件+6 vitest）并行盲拼，第三个独立核验员复跑全部验证 +
  禁令扫描（零命中）。契约盲拼跨包零返工。

## 四问门控

- **LLM 离线可跑**: YES — 纯文件解析，请求路径无 LLM/无 subprocess/无网络。
- **artifacts**: YES — 页面本身就是治理工件的渲染器（DEC/报告/审计原文直出）。
- **TrustGate 解释**: n/a-forward — 观察面不产 verdict；显示的 verdict 全部来自
  已归档 Codex 报告原文。
- **AI advisory-only**: YES — 零 mutating 路由（核验员扫描确认无 POST/PUT/DELETE）。

## 验证

- `pytest -q ui/backend/tests/test_agent_crew.py` → 16 passed（含真仓 smoke、
  brace 展开、verdict fail-closed、APPROVE_WITH_COMMENTS 不误判 APPROVE、
  非法 id 不泄露文件）。
- `ui/frontend`: `npx tsc -b` clean · `npx vitest run src/pages/agent_crew` →
  6 passed（角色节点渲染/stats 无硬编码/verdict 徽章色/只读断言）。
- live 冒烟（uvicorn 临时空闲端口）：`GET /api/agent-crew` → roles 7 / edges 9 /
  arcs 80 / stats {441,148,222,2,16}；`GET /api/agent-crew/arc/DEC-V61-237` →
  R0/R1 报告自动关联。
- 工作台冻结零触碰（`ui/frontend/src/pages/workbench/**` 无改动）；无新依赖。

## Surface scan (V61-088)

ROADMAP：观察面系 V61-226 workflow-monitor 方向的延伸，无冲突项。Grep
`agent.crew|crew|topology` over src/ ui/: 仅 workflow_monitor（CFD 运行时阶段图，
非治理拓扑）→ **disposition: parallel new**（不同数据域：governance artifacts vs
.cwos 运行时事件；复用其三栏布局 idiom 而非代码）。
**Surface-scan-found: ui/frontend/src/pages/workflow_monitor/ · disposition: parallel**

## Rollback

git revert 单 commit；无 workbench/状态耦合。
