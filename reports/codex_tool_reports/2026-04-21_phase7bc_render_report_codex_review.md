2026-04-21T09:26:20.725356Z ERROR codex_core::codex: failed to load skill /Users/Zhuanz/.agents/skills/cfd-research-deerflow/SKILL.md: missing YAML frontmatter delimited by ---
2026-04-21T09:26:20.725374Z ERROR codex_core::codex: failed to load skill /Users/Zhuanz/.agents/skills/cfd-report-pretext/SKILL.md: missing YAML frontmatter delimited by ---
Reading additional input from stdin...
OpenAI Codex v0.118.0 (research preview)
--------
workdir: /Users/Zhuanz/Desktop/cfd-harness-unified
model: gpt-5.4
provider: openai
approval: never
sandbox: danger-full-access
reasoning effort: xhigh
reasoning summaries: none
session id: 019daf5c-b136-7092-a68f-2307a618ad85
--------
user
Review Phase 7b + 7c + 7f bundle for cfd-harness-unified — all uncommitted working tree. This is the "scientific-grade CFD vs gold reporting" Phase 7 user-visible payload; user-facing HTML+PDF report embedded in /learn frontend.

Files to review:

**Phase 7b (rendering pipeline, autonomous):**
- scripts/render_case_report.py (NEW, ~380 LOC) — matplotlib + plotly renderer, reads Phase 7a captured artifacts and produces 5 outputs to reports/phase5_renders/{case}/{ts}/: profile_u_centerline.png (sim vs Ghia overlay), profile_u_centerline.plotly.json, residuals.png (log-y), pointwise_deviation.png (color-coded bar), contour_u_magnitude.png (1D centerline slice MVP; full 2D VTK deferred). Also writes runs/{label}.json manifest. LDC-only via RENDER_SUPPORTED_CASES frozenset opt-in.

**Phase 7c (HTML+PDF report, Codex-required due to user-facing docs):**
- ui/backend/services/comparison_report.py (NEW, ~280 LOC) — reads LDC gold YAML (multi-doc yaml.safe_load_all), sim sample .xy, residuals.csv, mesh_{20,40,80,160} fixtures. Computes L2/Linf/RMS/pointwise-dev%. Verdict logic: PASS all, PARTIAL >= 60% gold points pass, FAIL otherwise. render_report_html via Jinja2; render_report_pdf via WeasyPrint (lazy import, requires DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib on macOS).
- ui/backend/templates/comparison_report.html.j2 (NEW, ~160 lines) — 8 sections, gradient verdict card, tables, img tags with relative src pointing into reports/phase5_renders/.
- ui/backend/routes/comparison_report.py (NEW, ~100 LOC) — 4 endpoints:
  * GET /api/cases/{case_id}/runs/{run_label}/comparison-report → HTML
  * GET .../comparison-report/context → JSON (raw template ctx)
  * GET .../comparison-report.pdf → FileResponse
  * POST .../comparison-report/build → rebuild
  Traversal defense via ui/backend/services/run_ids._validate_segment on case_id + run_label.
- ui/backend/main.py (MODIFIED, +2 LOC) — router registration.
- ui/backend/tests/test_comparison_report_route.py (NEW, 6 tests) — 200/404/400 cases including %2e%2e__pwn URL-encoded.

**Phase 7f (frontend live embed, Codex-required multi-file frontend):**
- ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx (MODIFIED, +162 LOC) — new ScientificComparisonReportSection component fetches /api/cases/{id}/runs/audit_real_run/comparison-report/context. Renders verdict card + metrics grid + iframe embed of the HTML report + "Open in new window" + "Download PDF" buttons. Silently hides on fetch error (case not yet opted-in). iframe has sandbox="" (strict).

Regression gate: PYTHONPATH=. .venv/bin/pytest ui/backend/tests/ -q → 103/103 passed (was 97/97; +6 new comparison_report tests). Live smoke: all 4 backend endpoints return expected status (200/200/200/400). PDF generated: 622 KB valid PDF 1.7 with all 8 sections rendered correctly including image links resolved via weasyprint base_url.

Focus your review on:
1. **7f iframe XSS / sandbox**: iframe embeds content from our own origin. sandbox="" is most restrictive (no scripts, no same-origin). Is this correct given we control the HTML? Any attack surface if HTML escapes the Jinja2 autoescape=select_autoescape(["html","htm"])?
2. **7c WeasyPrint base_url**: render_report_pdf sets base_url=_REPO_ROOT so img src="reports/phase5_renders/..." resolves via filesystem. Does this let an attacker with manifest-write access exfiltrate arbitrary files via template injection? (Note: _REPO_ROOT is fixed, template is Jinja2 autoescaped, data is typed.)
3. **7c template injection**: ctx values flow from build_report_context into Jinja2. Any field that could contain untrusted content? paper.title comes from gold YAML (trusted), verdict_subtitle is constructed server-side, metrics are numbers. Look for any {{ ... }} that renders untrusted text without |e escape.
4. **7b matplotlib determinism**: PNG byte-stability across re-runs — any seed needed? matplotlib has some non-determinism (font rendering). Is the bar chart byte-stable for the pointwise test assertion?
5. **7c grid_convergence yaml.safe_load vs safe_load_all**: _load_grid_convergence uses safe_load single-doc, LDC gold uses safe_load_all. Verify fixture files are single-doc (not multi-doc).
6. **Code smell**: the `else return None` in ScientificComparisonReportSection silently hides 404 but also hides 500. Should it show an error state for non-404 errors?
7. **Route trust**: comparison_report.py reuses _validate_segment from run_ids.py. Is run_label=audit_real_run always valid under that regex (^[A-Za-z0-9][A-Za-z0-9_\\-]*$)? Yes — checked.

Reply APPROVED / APPROVED_WITH_COMMENTS / CHANGES_REQUIRED with numbered findings + severity.
codex
Reviewing the Phase 7b/7c/7f bundle as a correctness/security review against the live working tree. I’m first pulling the repo state, the relevant planning context, and the specific files you named so the findings are grounded in the actual code, not the summary.
exec
/bin/zsh -lc "sed -n '1,220p' /Users/Zhuanz/.agents/skills/gsd-code-review/SKILL.md" in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc "sed -n '1,220p' .planning/PROJECT.md" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
# cfd-harness-unified

## 项目意图

统一知识治理层 + Foam-Agent 执行引擎，建立个人 CFD 知识图谱。

本项目是 AI-CFD Knowledge Harness 的下一代架构：
- **Foam-Agent** 作为外部 CFD 执行引擎（不自建 NL→OpenFOAM 生成能力）
- **Notion** 作为唯一的 Process SSOT 控制面
- **本地 YAML** 作为 Gold Standard 和 CorrectionSpec 知识库

## 核心约束

- Python 3.9+
- 所有类型定义用 dataclass（不用普通 dict）
- 所有枚举字段用 Enum（不用字符串常量）
- 接口定义用 Protocol（不用 ABC）
- 测试用 pytest，覆盖率 > 80%
- 不安装或调用真实 Foam-Agent，只实现 adapter 接口和 MockExecutor
- 不调用真实 Notion API，notion_client.py 留占位符，测试用 mock

## 不做的事

- 不自建 NL→OpenFOAM 生成能力（Foam-Agent 已覆盖）
- 不自建求解器
- 不管理 OpenFOAM 安装

## 唯一控制面

Notion 页面：cfd-harness-unified
- Phases 数据库 → Tasks 数据库 → Sessions 数据库
- Decisions 数据库 ← → Phases / Sessions
- Canonical Docs 数据库 ← → Phases / Tasks

## 架构流程

```
Notion TaskSpec
    ↓
task_runner.py（编排器）
    ├── knowledge_db.py（加载 Gold Standard + CorrectionSpec）
    ├── foam_agent_adapter.py（调用 CFDExecutor Protocol）
    │       ├── MockExecutor（测试用）
    │       └── FoamAgentExecutor（占位符）
    ├── result_comparator.py（结果 vs Gold Standard）
    └── correction_recorder.py（偏差 → CorrectionSpec）
    ↓
回写结果摘要到 Notion
```

 succeeded in 0ms:
---
name: gsd-code-review
description: "Review source files changed during a phase for bugs, security issues, and code quality problems"
argument-hint: "<phase-number> [--depth=quick|standard|deep] [--files file1,file2,...]"
allowed-tools:
  - Read
  - Bash
  - Glob
  - Grep
  - Write
  - Task
---

<objective>
Review source files changed during a phase for bugs, security vulnerabilities, and code quality problems.

Spawns the gsd-code-reviewer agent to analyze code at the specified depth level. Produces REVIEW.md artifact in the phase directory with severity-classified findings.

Arguments:
- Phase number (required) — which phase's changes to review (e.g., "2" or "02")
- `--depth=quick|standard|deep` (optional) — review depth level, overrides workflow.code_review_depth config
  - quick: Pattern-matching only (~2 min)
  - standard: Per-file analysis with language-specific checks (~5-15 min, default)
  - deep: Cross-file analysis including import graphs and call chains (~15-30 min)
- `--files file1,file2,...` (optional) — explicit comma-separated file list, skips SUMMARY/git scoping (highest precedence for scoping)

Output: {padded_phase}-REVIEW.md in phase directory + inline summary of findings
</objective>

<execution_context>
@$HOME/.Codex/get-shit-done/workflows/code-review.md
</execution_context>

<context>
Phase: $ARGUMENTS (first positional argument is phase number)

Optional flags parsed from $ARGUMENTS:
- `--depth=VALUE` — Depth override (quick|standard|deep). If provided, overrides workflow.code_review_depth config.
- `--files=file1,file2,...` — Explicit file list override. Has highest precedence for file scoping per D-08. When provided, workflow skips SUMMARY.md extraction and git diff fallback entirely.

Context files (AGENTS.md, SUMMARY.md, phase state) are resolved inside the workflow via `gsd-tools init phase-op` and delegated to agent via `<files_to_read>` blocks.
</context>

<process>
This command is a thin dispatch layer. It parses arguments and delegates to the workflow.

Execute the code-review workflow from @$HOME/.Codex/get-shit-done/workflows/code-review.md end-to-end.

The workflow (not this command) enforces these gates:
- Phase validation (before config gate)
- Config gate check (workflow.code_review)
- File scoping (--files override > SUMMARY.md > git diff fallback)
- Empty scope check (skip if no files)
- Agent spawning (gsd-code-reviewer)
- Result presentation (inline summary + next steps)
</process>

exec
/bin/zsh -lc "sed -n '1,220p' .planning/STATE.md" in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc 'rg -n "cfd-harness-unified|Phase 8 closeout|Phase 9" /Users/Zhuanz/.codex/memories/MEMORY.md' in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
115:- OpenClaw, AI-CFD, Notion作为指挥中枢，Github作为唯一代码真相库, ~/.openclaw/openclaw.json, plugins.allow, openclaw config validate --json, MAIN_OK, CODEX_BUILDER_OK, CLAUDE_REVIEW_OK, NOTION_SYNC_OK, cfd-harness-unified
135:- The real live config surface was `~/.openclaw/openclaw.json`; the actual repo truth for this rollout was `/Users/Zhuanz/Desktop/cfd-harness-unified`, not the chat thread cwd [Task 1]
356:# Task Group: cfd-harness-unified governance closeout and planning gates
358:scope: Close out accepted phases in `cfd-harness-unified`, normalize Notion-vs-repo naming drift, and keep future phases planning-only until the explicit solver/routing gate is reviewed.
359:applies_to: cwd=/Users/Zhuanz/Desktop/cfd-harness-unified; reuse_rule=safe for this repo’s Notion-governed phase/gate work, but phase/task IDs and review packets are rollout-specific.
365:- rollout_summaries/2026-04-16T17-04-02-U9ea-phase8_closeout_and_phase9_planning_gate_prep.md (cwd=/Users/Zhuanz/Desktop/cfd-harness-unified, rollout_path=/Users/Zhuanz/.codex/sessions/2026/04/17/rollout-2026-04-17T01-04-02-019d973f-efab-7132-bd99-5e0ebb839e12.jsonl, updated_at=2026-04-17T05:16:53+00:00, thread_id=019d973f-efab-7132-bd99-5e0ebb839e12, Phase 8 closeout and evidence normalization)
371:## Task 2: Open Phase 9 as planning-only and keep solver expansion bounded
375:- rollout_summaries/2026-04-16T17-04-02-U9ea-phase8_closeout_and_phase9_planning_gate_prep.md (cwd=/Users/Zhuanz/Desktop/cfd-harness-unified, rollout_path=/Users/Zhuanz/.codex/sessions/2026/04/17/rollout-2026-04-17T01-04-02-019d973f-efab-7132-bd99-5e0ebb839e12.jsonl, updated_at=2026-04-17T05:16:53+00:00, thread_id=019d973f-efab-7132-bd99-5e0ebb839e12, Phase 9 kept as planning-only with decision-tree packet))
379:- Phase 9 planning-only, PHASE9_EXTERNAL_SOLVER_DECISION_TREE.md, PHASE9_MODEL_ROUTING_BASELINE_PLAN.md, PHASE9_ACTIVATION_REVIEW_PACKET.md, replay_manifest, SU2 CLI Harness Skill, foam_agent_adapter.py
385:- rollout_summaries/2026-04-16T17-04-02-U9ea-phase8_closeout_and_phase9_planning_gate_prep.md (cwd=/Users/Zhuanz/Desktop/cfd-harness-unified, rollout_path=/Users/Zhuanz/.codex/sessions/2026/04/17/rollout-2026-04-17T01-04-02-019d973f-efab-7132-bd99-5e0ebb839e12.jsonl, updated_at=2026-04-17T05:16:53+00:00, thread_id=019d973f-efab-7132-bd99-5e0ebb839e12, handoff prompt prepared instead of silent activation))
400:- Phase 9 must start from a bounded decision tree: keep single-engine OpenFOAM, allow reference-only external solver surfaces, or open one bounded proof slice; anything broader still needs review [Task 2]
406:- Symptom: planning work accidentally looks like activation -> cause: Phase 9 docs/task text are not explicit enough about `Planned` vs `Active` -> fix: state planning-only mode in phase page, tasks, dashboard summary, and review packet [Task 2]
439:- rollout_summaries/2026-04-12T15-33-54-ByPi-jerry_ai_cfd_notion_sync_and_cfd_harness_unified_context_mis.md (cwd=/Users/Zhuanz/Documents/20260330 Jerry AI CFD Project, rollout_path=/Users/Zhuanz/.codex/sessions/2026/04/12/rollout-2026-04-12T23-33-54-019d8253-fa8b-7f40-9775-46e6e03db8ac.jsonl, updated_at=2026-04-16T17:03:18+00:00, thread_id=019d8253-fa8b-7f40-9775-46e6e03db8ac, later cfd-harness-unified instruction block correctly treated as mismatch)

 succeeded in 0ms:
---
gsd_state_version: 1.0
milestone: v1.6.0
milestone_name: milestone
status: unknown
last_updated: "2026-04-21T08:17:39.182Z"
progress:
  total_phases: 7
  completed_phases: 0
  total_plans: 3
  completed_plans: 2
  percent: 67
---

driving_model: claude-opus47-app (Sole Primary Driver under Model Routing v6.1; Codex GPT-5.4-xhigh demoted to Heterogeneous Code Tool, invoked on demand for the three-禁区 src/ · tests/ · knowledge/gold_standards/ perimeter. Notion Gate retained only for 4 hard-floor守护者 duties.)
tier: T3-Orchestrator
last_updated: "2026-04-21T08:30"
session: S-003p OPEN (v6.1 takeover landing + state reconciliation + visual-acceptance iteration audit + Path B UI-MVP Phase 0). Supersedes S-003o. v6.1 cutover: joint Codex↔Claude co-primary (v6.0) retired; Claude APP is now sole primary driver with codex-as-tool access pattern. Hard boundaries remain frozen: Q-1 (DHC gold Path P-1/P-2) and Q-2 (R-A-relabel pipe_flow→duct_flow). Q-3 Notion backfill CLOSED 2026-04-19 / re-closed 2026-04-20 (MCP online). **2026-04-20 pivot — Path B elected (DEC-V61-002)**: project reframes from R&D-harness to Agentic V&V-first commercial workbench; 6-phase MVP begins with Phase 0 (FastAPI backend + Vite/React frontend + Screen 4 Validation Report). Phase 9 "fresh activation review" hold is superseded — Phase 9 scope rolls into the Path-B phase plan.

# Phase Status

current_phase: **Path B — Phase 1..4 UI MVP** (Case Editor + Decisions Queue + Run Monitor + Dashboard) — LANDED on feat/ui-mvp-phase-1-to-4, DEC-V61-003 drafted, PR #3 pending
phase_status: ui/backend ✅ (21/21 pytest green — case_editor 6, decisions/run_monitor/dashboard 8, existing 7) · ui/frontend ✅ (tsc --noEmit clean, vite build ~232KB js gz / ~4KB css gz, 122 modules) · CodeMirror 6 YAML editor + 4-col Kanban + SSE residual streaming + 10-case matrix Dashboard all wired · scripts/start-ui-dev.sh + README UI quickstart + pyproject [ui] dep group landed · Phase 0 PR #2 merged as 6ae6d0b5 · DEC-V61-002 Notion-mirrored
next_phase: Path B — Phase 5 (Audit Package Builder)
next_phase_status: 🔒 BLOCKED on external Gate — Q-1 (DHC gold accuracy) + Q-2 (R-A-relabel pipe→duct) must resolve before signed audit packages can emit (per DEC-V61-002 + DEC-V61-003)
autonomous_governance_counter_v61: 3 (DEC-V61-001 cutover + DEC-V61-002 Path B + DEC-V61-003 Phase 1..4) · hard-floor-4 threshold ≥ 10 still has 7 slots of runway

legacy_phase: Phase 8 — COMPLETE (delivery hardening + control-plane sync; 2026-04-20)
legacy_next_phase_hold: Phase 9 planning-only review is SUPERSEDED by Path B phase plan; Q-1 / Q-2 remain visible in external_gate_queue.md and do not block Path B phases 0..4 (will re-enter at Phase 5 audit-package-signing gate if still open).

Path B phase-plan (DEC-V61-002): P0 UI MVP ⇒ P1 Case Editor ⇒ P2 Decisions Queue ⇒ P3 Run Monitor ⇒ P4 Dashboard ⇒ P5 Audit Package Builder.

Phase 5 Notion: `341c6894-2bed-81c4-9a22-eb6773a6e47c` → Done ✅ (2026-04-15)
Phase 6 Notion: TBD

# Phase 3 — COMPLETE

Phase 3 Notion: `341c6894-2bed-81b8-baa2-eccd49f4993a`

Opus Gate: ⚠️ APPROVED WITH CONDITIONS (2026-04-13) — CFDJerry (T0 proxy)

- Blocking Conditions: C1+C2 DONE
- Non-blocking (Phase 4 scope): C3 (归因链 P0), C4 (3 Docker E2E), C5 (DB cleanup)

Success Criteria:

1. task_runner E2E 闭环验证 (10 cases 全量执行) — ✅ DONE
2. CorrectionSpec 自动生成率 >80% — ⚠️ 70% Mock / >80% expected Docker
3. 知识库自我进化验证 — ✅ DONE (versioning confirmed)
4. 误差自动归因链验证 — ⏳ Deferred to Phase 4 P1

Phase 3 Tasks:

- [P0] 全量E2E闭环验证 — ✅ Done (10/10 executed, 3/10 passed)
- [P0] CorrectionSpec 进化机制 — ✅ Done (versioning confirmed, LDC 3 versions)
- [P1] 误差自动归因链 — ⏳ Ready (deferred to Phase 4)

Phase 3 E2E Results (MockExecutor):
| Case | Execute | Compare | Correction |
|------|---------|---------|------------|
| Lid-Driven Cavity | ✅ | ❌ value_deviation | ✅ |
| Backward-Facing Step | ✅ | ❌ key_mismatch | ✅ |
| Circular Cylinder Wake | ✅ | ✅ | — |
| Turbulent Flat Plate | ✅ | ❌ key_mismatch | ✅ |
| Fully Developed Pipe Flow | ✅ | ❌ key_mismatch | ✅ |
| Differential Heated Cavity | ✅ | ✅ | — |
| Plane Channel Flow (DNS) | ✅ | ❌ key_mismatch | ✅ |
| Axisymmetric Impinging Jet | ✅ | ❌ key_mismatch | ✅ |
| NACA 0012 Airfoil | ✅ | ❌ key_mismatch | ✅ |
| Rayleigh-Bénard Convection | ✅ | ✅ | — |
**TOTAL** | **10/10** | **3/10** | **7** |

CorrectionSpec 70% Root Cause (Session S-002c):

- 6/7: key_mismatch (flow_type preset vs case-specific quantity)
- 1/7: value_deviation (LDC preset vs Ghia 1982 reference)

Phase 4 Conditions (from Gate):

- C3: 误差自动归因链 → Phase 4 P0 (no deferral)
- C4: 3 Docker E2E (LDC/BFS/NC Cavity)
- C5: Phases DB cleanup (Phase 3 Gate archived ✅)

Phase 4 Conditions (from Gate):

- C3: 误差自动归因链 ✅ DONE (AttributionReport + ErrorAttributor)
- C4: 3 Docker E2E ✅ DONE (T2-D implemented: sampleDict + postProcessing解析)
- C5: Phases DB cleanup ✅ DONE

# Phase 4 — IN PROGRESS

Phase 4 Objective: 误差自动归因链 + 真实 Docker E2E 验证

Phase 4 Tasks (Gate Conditions):

- [P0] 误差自动归因链 — ✅ DONE (AttributionReport dataclass + ErrorAttributor engine)
- [P0] 3 Docker E2E (LDC/BFS/NC Cavity) — ✅ DONE
  - LDC: postProcess writeObjects+writeCellCentres 提取 uCenterline → u_centerline 映射
  - BFS: postProcess 提取 wallProfile → reattachment_length 计算 (Ux零交点)
  - NC Cavity: postProcess 提取 midPlaneT → nusselt_number 计算
- [P2] T2-D: OpenFOAM sample utility — ✅ DONE (postProcess替代方案实现完成)
  - system/sampleDict 添加到 LDC/BFS/NC Cavity generators
  - postProcess -funcs '(writeObjects writeCellCentres)' -latestTime 执行
  - _parse_writeobjects_fields 解析场文件并 case-specific 映射到 Gold Standard quantity 名称
  - _copy_postprocess_fields 复制 postProcess 输出到宿主机
- [P1] >80% CorrectionSpec 真实执行验证 — ✅ B1 DONE (LDC Docker E2E 完成)
  - B1 Evidence Chain: solver log → field output → key_quantities → ComparisonResult → AttributionReport
  - nu bug fixed: nu=0.1/Re → Re=100 时 nu=0.001 (之前硬编码 0.01 = Re=10)
  - ResultComparator y-aware interpolation: Gold Standard y 位置线性插值后比较
  - AttributionReport 正确识别 mesh 为 primary cause (coarse mesh → 347% rel_err at Re=100)

Phase 4 B1 Evidence Chain (LDC Re=100 Docker):
| 步骤 | 状态 | 证据 |
|------|------|------|
| Docker 真实执行 | ✅ | success=True, is_mock=False, 7.8s |
| 场提取 (postProcess) | ✅ | u_centerline[17 values], y_centerline[17 values] |
| Gold Standard 对比 | ⚠️ 5 deviations | y-aware interpolation, max 347% @ y=0.5 |
| AttributionReport | ✅ | chain_complete=True, primary=mesh, conf=50% |

Phase 4 B1 Root Cause (BFS/NC Cavity 同理):

- 20×20 mesh 太粗：Re=100 需要更密网格捕捉 secondary vortex
- 修正: nu bug → Re=100 物理量提取正确, u_max≈0.61 合理 (应为 1.0)
- 剩余误差: mesh 分辨率不足 (AttributionReport 建议 ncx/ncy 加倍)

# Phase 2 — COMPLETE

Opus Gate: ✅ APPROVED (2026-04-13) — 5/5 criteria, 10/10 tasks, 103 tests

Success Criteria:

1. ✅ 10+ 成功案例配置模板入库 (10 cases in whitelist.yaml)
2. ✅ 知识库覆盖 3+ geometry 类型 (6 geometry types)
3. ✅ 每条含完整 geometry→turbulence→BC→mesh→result 链路 (10 chains enriched with solver/turbulence_model)
4. ✅ 知识查询 API 可用 (query_cases, get_execution_chain, list_turbulence_models, list_solver_for_geometry)
5. ✅ CorrectionSpec 自动生成 E2E 验证 (Done)

Phase 2 Tasks:

- Backward-Facing Step (Grid Refinement Study) [P1] ✅ Done
- NACA 0012 Airfoil External Flow [P1] ✅ Done
- Verify CorrectionSpec Auto-Generation [P1] ✅ Done
- Natural Convection Cavity (Dhir 2001) [P2] ✅ Done

Phase 2 完成项:

- FoamAgentExecutor BFS support ✅ — single-block rectangular channel, ncx/ncy parameterizable
- FoamAgentExecutor NATURAL_CONVECTION_CAVITY ✅ — buoyantSimpleFoam, 3.97s execution
- Knowledge Query API ✅ — query_cases, get_execution_chain, list_turbulence_models, list_solver_for_geometry
- Knowledge base whitelist.yaml ✅ — expanded to 10 cases (3→10), 6 geometry types
- GeometryType enum 扩展 ✅ — NATURAL_CONVECTION_CAVITY, AIRFOIL, IMPINGING_JET
- FoamAgentExecutor ncx/ncy 参数化 ✅ — 网格无关性研究可用

Phase 2 剩余工作:

- T2-D: Add OpenFOAM sample utility for u_centerline / Xr extraction — ✅ DONE (Phase 4 T2-D, postProcess替代方案)

# Phase 1 — COMPLETE

Opus Gate: ✅ APPROVED (2026-04-13)

- E2E 闭环: Lid-Driven Cavity + Circular Cylinder Wake ✅
- CorrectionSpec 自动生成: ✅ 已测试
- D-001: Deferred to Phase 2+ (internal token sufficient)

# Code Health

tests_passing: 121
tests_total: 120
coverage: 91%
src_loc: 560
git_repo: ✅ kogamishinyajerry-ops/cfd-harness-unified

# Open Decisions

| ID | Topic | Status |
|----|-------|--------|
| D-001 | Notion API token 类型 | ✅ Closed (Deferred to Phase 2+) |
| D-002 | FoamAgentExecutor Docker | ✅ Done |
| D-003 | git repo 独立仓库 | ✅ Done |

# Known Risks

- R1: ✅ notion_client 真实 API
- R2: ⚠️ 容器 cfd-openfoam 必须运行
- R3: ✅ Gold Standards Ghia 1982 / Driver 1985 / Williamson 1996

# Session Summary

S-001: Phase 0 + Phase 1 完成
S-002: Phase 2 启动 — Full Benchmark Suite

# Next Action

Phase 6 COMPLETE (2026-04-16T20:53):

- ✅ turbulent_flat_plate: Docker E2E PASS, cf_skin_friction=0.0027, Gold Std PASS
- ✅ plane_channel_flow: Docker E2E PASS, u_mean_profile, Gold Std PASS
- ✅ rayleigh_benard_convection: FIXED + Docker E2E PASS, nusselt_number=10.5
- ✅ naca0012_airfoil: AIRFOIL fvSolution fix (p-relax 0.3, lower URFs), Docker E2E PASS 286s
- ✅ impinging_jet: Docker E2E PASS, nusselt_number=0.0042, 157s
- ✅ All 121 tests passing
- ⏳ Phase 8 AutoVerifier: SPEC.md ✅, 等待 Opus 4.6 Gate 架构审查

Phase 4 B1 完成 (2026-04-13):

- ✅ nu bug fixed: nu=0.1/Re (was 0.01 hardcoded)
- ✅ y-aware interpolation in ResultComparator
- ✅ LDC Docker E2E 完整证据链: 7.8s exec → u_centerline[17pts] → ComparisonResult → AttributionReport
- ⚠️ LDC comparison: 5/5 deviations (coarse mesh → primary vortex正确, secondary vortex未捕捉)
- ✅ AttributionReport 正确识别 mesh 为 primary cause

Phase 4 C4: BFS + NC Cavity Docker E2E 待验证

Phase 4 C4 Verification (S-002c 续):

- NC Cavity: ✅ Docker E2E SUCCESS (buoyantFoam + Boussinesq, 11s, success=True)
  - 根因: perfectGas/hConst 热力学配置与 buoyantFoam 不兼容
  - 修复: → Boussinesq approximation (equationOfState Boussinesq, rho0=1.177, beta=3e-3)
  - 修复: constant/g 添加 dimensions [0 1 -2 0 0 0 0]

exec
/bin/zsh -lc "sed -n '1,220p' .planning/config.json" in /Users/Zhuanz/Desktop/cfd-harness-unified
 exited 1 in 0ms:
sed: .planning/config.json: No such file or directory

exec
/bin/zsh -lc "sed -n '1,220p' .planning/ROADMAP.md" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
# ROADMAP

## Current

### Phase 5b — LDC simpleFoam migration + Ghia 1982 match
- Status: Infrastructure complete (DEC-V61-029) + Q-5 CLOSED via Path A (DEC-V61-030). LDC audit comparator: 11/17 PASS at 5% tolerance; 6/17 FAIL are physical residuals of uniform-grid vs Ghia's graded mesh — optional sub-phase-2 graded-mesh work could close them. 7 remaining FAIL-case sub-phases (5c..5j) queued with mandatory gold cross-check as first step.
- Goal: Migrate `lid_driven_cavity` case generator from icoFoam (transient PISO) to simpleFoam (steady-state SIMPLE) and tune mesh/schemes so `scripts/phase5_audit_run.py lid_driven_cavity` yields `audit_real_run` verdict=PASS against Ghia 1982 u_centerline at 5% tolerance. First of 8 per-case Phase 5b sub-phases; establishes the solver-swap pattern that the remaining 7 FAIL cases (BFS, TFP, duct_flow, impinging_jet, naca0012, DHC, RBC) will copy in Phase 5c..5j.
- Upstream: Phase 5a shipped (commits 3d1d3ec, d4cf7a1, 7a3c48b) — real-solver pipeline + HMAC signing + PDF + audit fixtures for all 10 whitelist cases; baseline 2 PASS / 8 FAIL.
- Required outputs:
  - Updated `src/foam_agent_adapter.py::_generate_lid_driven_cavity` emitting simpleFoam case dir (controlDict + fvSchemes + fvSolution rewrite) with 129×129 mesh.
  - Regenerated `ui/backend/tests/fixtures/runs/lid_driven_cavity/audit_real_run_measurement.yaml` with `comparator_passed: true`.
  - Backend 79/79 pytest green (no regression on teaching fixtures).
  - Signed audit package via `POST /api/cases/lid_driven_cavity/runs/audit_real_run/audit-package/build` now carries `measurement.comparator_verdict=PASS`.
- Non-goals (separate sub-phases): tuning the other 7 FAIL cases; simpleFoam generalization; second-order schemes upgrade; turbulence models.
- Constraints: `src/` is 三禁区 #1 — this phase WILL edit >5 LOC, Codex review mandatory per RETRO-V61-001.
- Frozen governance edges: none (Q-1/Q-2/Q-3/Q-4 all closed).
- **Plans:** 3 plans
  - [ ] 05b-01-PLAN.md — Rewrite `_generate_lid_driven_cavity` + `_render_block_mesh_dict` in `src/foam_agent_adapter.py` (simpleFoam + 129×129 + frontAndBack empty)
  - [ ] 05b-02-PLAN.md — Regenerate `audit_real_run_measurement.yaml` fixture; verify backend 79/79 + frontend tsc clean
  - [ ] 05b-03-PLAN.md — Codex post-edit review + DEC-V61-NNN + atomic git commit + STATE/ROADMAP update

### Phase 7: Scientific-grade CFD vs gold reporting
- Status: Proposed (not yet activated)
- Goal: Upgrade audit reports from "single-scalar verdict" to publication-grade CFD vs gold evidence — full-field visualizations, multi-point profile overlays, formal error norms, residual histories, and Richardson grid-convergence indices — so every `audit_real_run` produces a PDF/HTML a CFD reviewer would accept alongside a paper's Figure/Table. Root cause addressed: current comparator extracts one scalar per run; VTK fields, residual logs, and y+ distributions are never persisted, so the report HTML at `/validation-report/*` has no visual or statistical depth to defend the 11/17 PASS / 6/17 FAIL LDC verdict.
- Upstream: Phase 5a pipeline (commits 3d1d3ec, d4cf7a1, 7a3c48b) produces raw OpenFOAM case dirs but discards fields after scalar extraction. Phase 5b/Q-5 established Ghia 1982 as the reference transcription bar. `/learn` currently ships static placeholder flow-field PNGs — not derived from audit runs.
- Required outputs (end-of-Phase-7):
  - `scripts/phase5_audit_run.py` additionally emits `foamToVTK` / `sample` / `yPlus` artifacts into `reports/phase5_fields/{case}/{timestamp}/`
  - `scripts/render_case_report.py` converts VTK + CSV profiles into PNG contours, Plotly JSON profiles, and residual log plots under `reports/phase5_renders/{case}/{timestamp}/`
  - Per-case HTML + PDF CFD-vs-gold report with 8 sections (verdict, paper cite, profile overlay, pointwise deviation heatmap, field contours, residual convergence, grid-convergence table + GCI, solver metadata)
  - Signed audit-package zip embeds the new PDF + PNG assets with SHA256 in manifest (L4 canonical spec)
  - `/learn/{case}` fetches renders from backend API instead of loading static PNGs; `/validation-report/{case}` embeds the new comparison HTML
- Non-goals: new physics cases; solver-swap outside Phase 5c..5j; interactive ParaView in-browser (Trame migration is AI-CFD Knowledge Harness v1.6.0 scope); DNS-grade statistics beyond RMS / L2 / L∞.
- Constraints: Phase 7a touches `src/foam_agent_adapter.py` (三禁区 #1, >5 LOC, Codex mandatory per RETRO-V61-001). Phase 7e extends signed-manifest schema — byte-reproducibility sensitive path, Codex mandatory. Phase 7c HTML template is user-facing documentation; follow brand/voice in `~/.claude/get-shit-done/references/ui-brand.md`.
- Frozen governance edges: none at Phase 7 start (Q-1..Q-5 all closed). New Q-gates may be filed if paper-citation chase surfaces schema issues (precedent: Q-5 found gold wrong; Q-4 BFS re-sourced to Le/Moin/Kim).
- **Sub-phases:** 6 sub-phases (7a..7f). Sprint 1 = depth-first on LDC (7a+7b+7c-MVP); Sprint 2 = breadth across other 9 cases + GCI + zip + frontend (7c-full + 7d + 7e + 7f).

### Phase 7a: Field post-processing capture (Sprint 1, ~2-3 days)
- Status: COMPLETE (DEC-V61-031, 2026-04-21). 3 waves landed: adapter functions{} + executor capture + driver manifest; backend route/service/18 pytest; Codex 3 rounds → APPROVED_WITH_COMMENTS (2 HIGH security issues caught + fixed: URL basename collision + run_id path-traversal). Real LDC OpenFOAM integration produced 8 artifacts, HTTP manifest + subpath download + traversal 404 verified live. 97/97 pytest. v6.1 counter 16→17.
- Goal: Extend `scripts/phase5_audit_run.py` + `src/foam_agent_adapter.py` so every audit_real_run persists full VTK fields, sampled CSV profiles, and residual.log to `reports/phase5_fields/{case}/{timestamp}/`.
- Required outputs:
  - `controlDict` `functions {}` block emitted with `sample`, `yPlus`, `residuals` function objects (adapter change)
  - Post-run `foamToVTK` invocation inside Docker runner; stage output to host `reports/phase5_fields/`
  - New `ui/backend/schemas/validation.py::FieldArtifact` Pydantic model
  - New `GET /api/runs/{run_id}/field-artifacts` route returning asset URLs + SHA256
  - pytest coverage: new fixture asserts VTK + CSV + residual.log presence for LDC
- Constraints: Codex mandatory (三禁区 #1 + adapter >5 LOC). Must not regress 79/79 pytest.
- **Plans:** 3 plans
  - [x] 07a-01-PLAN.md — Adapter + driver edits (controlDict functions{} + _capture_field_artifacts + driver timestamp + manifest)
  - [ ] 07a-02-PLAN.md — Backend route + schema + service + tests (FieldArtifact models + field_artifacts route + 10 pytest cases)
  - [ ] 07a-03-PLAN.md — Integration + Codex review + DEC-V61-031 + atomic commit

### Phase 7b: Render pipeline (Sprint 1, ~2 days)
- Status: Planned
- Goal: New `scripts/render_case_report.py` converts 7a's VTK + CSV into `reports/phase5_renders/{case}/{timestamp}/`: `contour_u.png`, `contour_p.png`, `streamline.png`, `profile_u_centerline.html` (Plotly JSON), `residuals.png`.
- Required outputs:
  - matplotlib for 2D contours (CI-reproducible); PyVista headless (`PYVISTA_OFF_SCREEN=1`) for 3D streamlines
  - Plotly JSON for interactive profile (frontend consumer)
  - Rendering deterministic (fixed seeds, locked matplotlib rcParams)
  - pytest coverage: byte-stable PNG checksum across re-runs on same VTK
- Constraints: new script, no src/ touch → autonomous_governance allowed. Add `pyvista`, `plotly`, `matplotlib` to `pyproject.toml` [render] extra.

### Phase 7c: CFD-vs-gold comparison report template (Sprint 1 MVP + Sprint 2 fan-out, ~3 days)
- Status: Planned — **core deliverable, the "說服力" centerpiece**
- Goal: Per-case HTML + WeasyPrint PDF report with 8 sections:
  1. Verdict card (PASS / FAIL + L2 / L∞ / RMS / max |dev|%)
  2. Paper citation block (Ghia 1982 / Le-Moin-Kim 1997 / etc. + Figure/Table + native tabulation)
  3. Profile overlay (sim solid line + gold scatter markers on paper's native grid)
  4. Pointwise deviation heatmap along sampling axis
  5. Field contours (U / p / vorticity / Cf depending on case class)
  6. Residual convergence (log y-axis, all solved fields)
  7. Grid-convergence table with Richardson p_obs + GCI_21/32 (from 7d)
  8. Solver metadata (OpenFOAM version, Docker digest, commit SHA, schemes, tolerances)
- Required outputs:
  - `ui/backend/services/comparison_report.py` renders Jinja2 template → HTML
  - `ui/backend/services/comparison_report_pdf.py` HTML → WeasyPrint PDF
  - `POST /api/cases/{case}/runs/{run_id}/comparison-report/build` route
  - Sprint 1 MVP: LDC only; Sprint 2: other 9 cases
  - `/validation-report/{case}` frontend route embeds the HTML
- Constraints: WeasyPrint requires `DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib` (already in `.zshrc`). HTML/PDF templates checked into `ui/backend/templates/` to keep Codex diff visible.

### Phase 7d: Richardson grid-convergence index (Sprint 2, ~1 day)
- Status: Planned
- Goal: Compute observed order of accuracy `p_obs` and Grid Convergence Index `GCI_21` / `GCI_32` from existing `mesh_20/40/80/160` fixtures per Roache 1994.
- Required outputs:
  - `ui/backend/services/grid_convergence.py` implementing Richardson extrapolation + GCI formula
  - New columns in 7c's "grid-convergence table" section
  - pytest coverage: analytic fixture (known p=2 solution) + LDC regression (p_obs should fall in [1.0, 2.0])
- Constraints: pure numerical, no src/ or adapter touch → autonomous_governance allowed.

### Phase 7e: Signed audit-package integration (Sprint 2, ~1 day)
- Status: Planned
- Goal: Embed 7c PDF + 7b PNG/JSON into HMAC-signed audit-package zip; extend manifest schema to L4 canonical.
- Required outputs:
  - `audit_package.py` manifest `artifacts.field_renders[]` + `artifacts.comparison_report.pdf_sha256` blocks
  - `docs/specs/audit_package_canonical_L4.md` supersedes L3 build_fingerprint spec
  - zip byte-reproducibility preserved (re-run produces identical HMAC)
  - pytest coverage: `test_phase5_byte_repro.py` extended to cover new artifacts
- Constraints: **Byte-reproducibility-sensitive path → Codex mandatory** per RETRO-V61-001 new trigger #2. L3→L4 schema rename touches manifest builder + signer + verifier → ≥3 files → Codex mandatory per RETRO-V61-001 new trigger #3.

### Phase 7f: Frontend render consumption (Sprint 2, ~1 day)
- Status: Planned
- Goal: Replace static placeholder flow-field PNGs in `/learn/{case}` with live fetches from 7a's `/api/runs/{run_id}/field-artifacts` + 7b's `/api/runs/{run_id}/renders`.
- Required outputs:
  - `ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx` flow-field block fetches real renders; falls back to reference-run renders if the slider mesh has no artifacts yet
  - `ui/frontend/src/pages/ValidationReportPage.tsx` embeds 7c HTML via iframe or direct component
  - frontend tsc --noEmit clean; visual acceptance via dev server
- Constraints: multi-file frontend change → Codex mandatory per existing trigger. Must not regress the 3 deep-link buttons added in commit 7a3c48b.

### Phase 8 — Delivery hardening
- Status: Active (legacy lane)
- Goal: keep the visual acceptance surface reproducible, cache-resilient, and synced to GitHub/Notion without crossing external-gate boundaries.
- Required outputs: canonical HTML, timestamped snapshot HTML, machine-readable manifest, deep acceptance package, synced control-plane records.
- Frozen governance edges: `Q-1 DHC gold-reference`, `Q-2 R-A-relabel`.

### Phase 9 — Planning only
- Status: Planned
- Goal: comparator/model-routing follow-on work after a fresh activation review.
- Rule: no Phase 9 activation work starts until Phase 8 hardening closes and external-gate constraints are explicitly reviewed.

## Completed

- Phase 1–7: completed and retained as historical implementation/archive context in `.planning/STATE.md`.
- Phase 8 baseline reporting upgrade: landed up to `088e2a3`, including Chinese-first visual acceptance deck and raster evidence panels.

exec
/bin/zsh -lc 'pwd && git status --short' in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
/Users/Zhuanz/Desktop/cfd-harness-unified
 M reports/cylinder_crossflow/report.md
 M reports/deep_acceptance/visual_acceptance_report.html
 M reports/deep_acceptance/visual_acceptance_report_manifest.json
 M reports/differential_heated_cavity/report.md
 M reports/rayleigh_benard_convection/report.md
 M reports/turbulent_flat_plate/report.md
 M ui/backend/main.py
 M ui/frontend/public/flow-fields/circular_cylinder_wake/strouhal_curve.png
 M ui/frontend/public/flow-fields/lid_driven_cavity/centerline_profiles.png
 M ui/frontend/public/flow-fields/lid_driven_cavity/stream_function.png
 M ui/frontend/public/flow-fields/plane_channel_flow/wall_profile.png
 M ui/frontend/public/flow-fields/rayleigh_benard_convection/nu_ra_scaling.png
 M ui/frontend/public/flow-fields/turbulent_flat_plate/blasius_profile.png
 M ui/frontend/public/flow-fields/turbulent_flat_plate/cf_comparison.png
 M ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx
?? .claude/
?? .gitignore.patch.stale.1776663560182166739
?? knowledge/corrections/
?? reports/codex_tool_reports/2026-04-21_phase7bc_render_report_codex_review.md
?? reports/deep_acceptance/20260421_000138_visual_acceptance_package.md
?? reports/deep_acceptance/20260421_000139_visual_acceptance_package.md
?? reports/deep_acceptance/20260421_000231_visual_acceptance_package.md
?? reports/deep_acceptance/20260421_000232_visual_acceptance_package.md
?? reports/deep_acceptance/visual_acceptance_report_20260421_000138.html
?? reports/deep_acceptance/visual_acceptance_report_20260421_000139.html
?? reports/deep_acceptance/visual_acceptance_report_20260421_000231.html
?? reports/deep_acceptance/visual_acceptance_report_20260421_000232.html
?? reports/phase5_audit/20260421T081929Z_lid_driven_cavity_raw.json
?? reports/phase5_audit/20260421T082305Z_lid_driven_cavity_raw.json
?? reports/phase5_audit/20260421T082408Z_lid_driven_cavity_raw.json
?? reports/phase5_fields/
?? reports/phase5_renders/
?? reports/phase5_reports/
?? scripts/render_case_report.py
?? ui/backend/routes/comparison_report.py
?? ui/backend/services/comparison_report.py
?? ui/backend/templates/
?? ui/backend/tests/test_comparison_report_route.py
?? ui/frontend/vite.config.sandbox.ts.stale.1776667726
?? ui/frontend/vite.config.sandbox.ts.timestamp-1776667276256-33cd5f0862292.mjs

codex
I’ve got the repo state and Phase 7 roadmap context. I’m now reading the named files plus adjacent fixtures/tests to check the seven review points against the actual implementation, with emphasis on XSS/path trust, PDF asset resolution, and determinism claims.
exec
/bin/zsh -lc "sed -n '1,260p' scripts/render_case_report.py" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
#!/usr/bin/env python3
"""Phase 7b — render_case_report.py

Convert Phase 7a-captured field artifacts (reports/phase5_fields/{case}/{ts}/)
into visual renders (reports/phase5_renders/{case}/{ts}/):

- profile_u_centerline.png   — matplotlib static profile (sim vs gold)
- profile_u_centerline.html  — Plotly JSON (for frontend interactive)
- residuals.png              — log-y residual convergence history
- contour_u_magnitude.png    — 2D U-magnitude contour from final sample iter
- pointwise_deviation.png    — color heatmap of |dev|% per gold point

LDC MVP: works today for case_id=lid_driven_cavity. Other 9 cases will be
unlocked in Phase 7c Sprint-2 as their adapters emit Phase 7a function objects.

Usage:
    python scripts/render_case_report.py lid_driven_cavity
    python scripts/render_case_report.py lid_driven_cavity --run audit_real_run

Dependencies: matplotlib (2D plots), plotly (interactive JSON), numpy, PyYAML.
No PyVista / no VTK parser needed for MVP — uses the sample CSV directly.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

import matplotlib

matplotlib.use("Agg")  # headless — CI-safe
import matplotlib.pyplot as plt
import numpy as np
import plotly.graph_objects as go
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
FIELDS_ROOT = REPO_ROOT / "reports" / "phase5_fields"
RENDERS_ROOT = REPO_ROOT / "reports" / "phase5_renders"
GOLD_ROOT = REPO_ROOT / "knowledge" / "gold_standards"

# Deterministic matplotlib style — locked for byte-reproducibility.
plt.rcParams.update({
    "figure.figsize": (8, 5),
    "figure.dpi": 110,
    "savefig.dpi": 110,
    "savefig.bbox": "tight",
    "font.family": "DejaVu Sans",
    "font.size": 11,
    "axes.grid": True,
    "grid.alpha": 0.3,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "lines.linewidth": 1.8,
})

# Phase 7a opt-in mirror — matches scripts/phase5_audit_run.py::_PHASE7A_OPTED_IN.
RENDER_SUPPORTED_CASES = frozenset({"lid_driven_cavity"})


class RenderError(Exception):
    """Non-fatal render failure — caller decides whether to abort the batch."""


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------


def _resolve_run_timestamp(case_id: str, run_label: str) -> str:
    """Read the per-run manifest written by phase5_audit_run.py and return its timestamp."""
    manifest_path = FIELDS_ROOT / case_id / "runs" / f"{run_label}.json"
    if not manifest_path.is_file():
        raise RenderError(f"no run manifest: {manifest_path}")
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    ts = data.get("timestamp")
    if not ts:
        raise RenderError(f"manifest missing timestamp: {manifest_path}")
    return ts


def _artifact_dir(case_id: str, timestamp: str) -> Path:
    d = FIELDS_ROOT / case_id / timestamp
    if not d.is_dir():
        raise RenderError(f"artifact dir missing: {d}")
    return d


def _renders_dir(case_id: str, timestamp: str) -> Path:
    d = RENDERS_ROOT / case_id / timestamp
    d.mkdir(parents=True, exist_ok=True)
    return d


def _load_sample_xy(path: Path) -> tuple[np.ndarray, np.ndarray]:
    """Load OpenFOAM `sample` output (.xy file, whitespace-separated).

    Column layout for uCenterline: y  U_x  U_y  U_z  p.
    Returns (y, U_x). Skips header lines starting with '#'.
    """
    rows: list[list[float]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        parts = s.split()
        # Accept either 5 (y Ux Uy Uz p) or 2 (y Ux) column variants.
        try:
            y = float(parts[0])
            ux = float(parts[1])
        except (ValueError, IndexError):
            continue
        rows.append([y, ux])
    if not rows:
        raise RenderError(f"empty sample file: {path}")
    arr = np.array(rows)
    return arr[:, 0], arr[:, 1]


def _load_residuals_csv(path: Path) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    """Load residuals.csv written by _capture_field_artifacts.

    Format: Time,Ux,Uy,p  — first data row may be "N/A" for iter 0.
    Returns (iterations, {field_name: array}).
    """
    raw = path.read_text(encoding="utf-8").splitlines()
    if not raw:
        raise RenderError(f"empty residuals: {path}")
    header = [c.strip() for c in raw[0].split(",")]
    if header[0].lower() not in ("time", "iter", "iteration"):
        raise RenderError(f"unexpected residuals header: {header}")
    fields = header[1:]
    iters: list[int] = []
    data: dict[str, list[float]] = {f: [] for f in fields}
    for line in raw[1:]:
        parts = [c.strip() for c in line.split(",")]
        if len(parts) != len(header):
            continue
        try:
            iters.append(int(float(parts[0])))
        except ValueError:
            continue
        for f, v in zip(fields, parts[1:]):
            if v.upper() == "N/A" or v == "":
                data[f].append(float("nan"))
            else:
                try:
                    data[f].append(float(v))
                except ValueError:
                    data[f].append(float("nan"))
    return np.array(iters), {k: np.array(v) for k, v in data.items()}


def _load_gold_ldc() -> tuple[list[float], list[float], str]:
    """Return (y_points, u_values, citation) from knowledge/gold_standards/lid_driven_cavity.yaml.

    File is multi-document YAML (u_centerline, v_centerline, primary_vortex_location).
    Iterate safe_load_all and pick the u_centerline document.
    """
    gold = GOLD_ROOT / "lid_driven_cavity.yaml"
    if not gold.is_file():
        raise RenderError(f"gold file missing: {gold}")
    docs = list(yaml.safe_load_all(gold.read_text(encoding="utf-8")))
    u_doc = next(
        (d for d in docs if isinstance(d, dict) and d.get("quantity") == "u_centerline"),
        None,
    )
    if u_doc is None:
        raise RenderError("no quantity: u_centerline doc in LDC gold YAML")
    refs = u_doc.get("reference_values", [])
    ys: list[float] = []
    us: list[float] = []
    for entry in refs:
        if isinstance(entry, dict):
            y = entry.get("y")
            u = entry.get("value") or entry.get("u")
            if y is not None and u is not None:
                ys.append(float(y))
                us.append(float(u))
    citation = u_doc.get("source") or u_doc.get("citation") or \
        "Ghia, Ghia & Shin 1982 J. Comput. Phys. 47, 387-411 — Table I Re=100"
    return ys, us, citation


# ---------------------------------------------------------------------------
# Renderers
# ---------------------------------------------------------------------------


def _latest_sample_iter(artifact_dir: Path) -> Path:
    """Return the highest-iteration sample directory (e.g. .../sample/1000/)."""
    sample_root = artifact_dir / "sample"
    if not sample_root.is_dir():
        raise RenderError(f"sample/ missing under {artifact_dir}")
    iters = sorted(
        (d for d in sample_root.iterdir() if d.is_dir() and d.name.isdigit()),
        key=lambda d: int(d.name),
    )
    if not iters:
        raise RenderError(f"no numeric iter subdirs under {sample_root}")
    return iters[-1]


def render_profile_png(
    case_id: str,
    artifact_dir: Path,
    renders_dir: Path,
) -> Path:
    """Matplotlib PNG: sim U_x(y) solid line + Ghia 1982 scatter markers."""
    latest = _latest_sample_iter(artifact_dir)
    xy = latest / "uCenterline.xy"
    y_sim, u_sim = _load_sample_xy(xy)

    # LDC is stored in physical coords (convertToMeters 0.1 → y ∈ [0, 0.1]).
    # Normalize to y_star ∈ [0, 1] for Ghia comparison.
    y_norm = y_sim / max(y_sim.max(), 1e-12)

    y_gold, u_gold, citation = _load_gold_ldc()

    fig, ax = plt.subplots()
    ax.plot(u_sim, y_norm, color="#1f77b4", label="simpleFoam (sim)")
    ax.scatter(u_gold, y_gold, color="#d62728", s=36, zorder=5,
               label="Ghia 1982 (Table I, Re=100)", edgecolor="white", linewidth=0.8)
    ax.axvline(0, color="gray", linewidth=0.5, linestyle="--", alpha=0.5)
    ax.set_xlabel(r"$U_x$ / $U_{\mathrm{lid}}$")
    ax.set_ylabel(r"$y\,/\,L$")
    ax.set_title(f"{case_id} — U centerline profile vs Ghia 1982")
    ax.legend(loc="upper left", frameon=False)
    ax.text(0.02, 0.02, citation[:80] + ("..." if len(citation) > 80 else ""),
            transform=ax.transAxes, fontsize=8, color="gray", style="italic")
    out = renders_dir / "profile_u_centerline.png"
    fig.savefig(out)
    plt.close(fig)
    return out


def render_profile_plotly_json(
    case_id: str,
    artifact_dir: Path,
    renders_dir: Path,
) -> Path:
    """Plotly figure JSON (consumed by frontend for hover/zoom interactive)."""
    latest = _latest_sample_iter(artifact_dir)
    xy = latest / "uCenterline.xy"
    y_sim, u_sim = _load_sample_xy(xy)
    y_norm = y_sim / max(y_sim.max(), 1e-12)

    y_gold, u_gold, citation = _load_gold_ldc()

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=u_sim, y=y_norm, mode="lines", name="simpleFoam",
        line=dict(color="#1f77b4", width=2),
        hovertemplate="U<sub>x</sub>=%{x:.4f}<br>y/L=%{y:.4f}<extra>sim</extra>",
    ))
    fig.add_trace(go.Scatter(
        x=u_gold, y=y_gold, mode="markers", name="Ghia 1982",
        marker=dict(color="#d62728", size=9, line=dict(color="white", width=1)),

exec
/bin/zsh -lc "sed -n '1,260p' ui/backend/templates/comparison_report.html.j2" in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc "sed -n '261,520p' scripts/render_case_report.py" in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc "sed -n '1,260p' ui/backend/services/comparison_report.py" in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc "sed -n '261,520p' ui/backend/services/comparison_report.py" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>CFD vs Gold — {{ case_id }}</title>
<style>
  body { font-family: -apple-system, 'Segoe UI', 'Helvetica Neue', sans-serif;
         color: #1f2937; max-width: 960px; margin: 2em auto; padding: 0 1.5em;
         line-height: 1.55; }
  h1 { color: #111; border-bottom: 3px solid #1f77b4; padding-bottom: 0.3em; }
  h2 { color: #1f77b4; margin-top: 2em; font-size: 1.3em; }
  .verdict-card { background: linear-gradient(135deg, {{ verdict_gradient }});
                  color: white; padding: 1em 1.5em; border-radius: 10px; margin: 1em 0 2em 0;
                  box-shadow: 0 2px 12px rgba(0,0,0,0.08); }
  .verdict-card .verdict { font-size: 2em; font-weight: bold; letter-spacing: 1px; }
  .verdict-card .sub { font-size: 0.95em; opacity: 0.92; margin-top: 0.3em; }
  .metrics { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1em; margin-top: 1em; }
  .metric { background: rgba(255,255,255,0.15); padding: 0.6em 0.8em; border-radius: 6px; }
  .metric-label { font-size: 0.75em; opacity: 0.85; text-transform: uppercase; }
  .metric-value { font-size: 1.3em; font-weight: bold; margin-top: 0.2em; }
  .paper-cite { background: #f9fafb; border-left: 4px solid #374151;
                padding: 0.8em 1em; margin: 1em 0; font-size: 0.92em; }
  .paper-cite .title { font-weight: 600; color: #111; }
  .paper-cite .doi { font-family: 'SF Mono', Consolas, monospace; font-size: 0.85em; color: #6b7280; }
  figure { margin: 1.5em 0; text-align: center; }
  figure img { max-width: 100%; border: 1px solid #e5e7eb; border-radius: 4px; }
  figcaption { font-size: 0.88em; color: #6b7280; margin-top: 0.5em; font-style: italic; }
  table { border-collapse: collapse; width: 100%; margin: 1em 0; font-size: 0.92em; }
  th, td { padding: 0.5em 0.8em; text-align: left; border-bottom: 1px solid #e5e7eb; }
  th { background: #f9fafb; font-weight: 600; color: #374151; }
  td.num { text-align: right; font-variant-numeric: tabular-nums; }
  td.pass { color: #059669; font-weight: bold; }
  td.fail { color: #dc2626; font-weight: bold; }
  td.warn { color: #d97706; font-weight: bold; }
  .mono { font-family: 'SF Mono', Consolas, monospace; font-size: 0.88em;
          background: #f3f4f6; padding: 0.1em 0.4em; border-radius: 3px; }
  .residual-block { background: #fff7ed; border-left: 4px solid #f97316;
                    padding: 0.8em 1em; margin: 1em 0; font-size: 0.9em; }
  footer { margin-top: 3em; padding-top: 1em; border-top: 1px solid #e5e7eb;
           font-size: 0.82em; color: #9ca3af; }
</style>
</head>
<body>

<h1>CFD vs Gold — {{ case_display_name }}</h1>
<p style="color:#6b7280; margin-top:-0.5em;">
  Case ID: <span class="mono">{{ case_id }}</span> ·
  Run: <span class="mono">{{ run_label }}</span> ·
  Timestamp: <span class="mono">{{ timestamp }}</span>
</p>

<!-- Section 1 — Verdict card -->
<div class="verdict-card">
  <div class="verdict">{{ verdict }}</div>
  <div class="sub">{{ verdict_subtitle }}</div>
  <div class="metrics">
    <div class="metric"><div class="metric-label">max |dev|</div>
         <div class="metric-value">{{ '%.2f'|format(metrics.max_dev_pct) }}%</div></div>
    <div class="metric"><div class="metric-label">L² norm</div>
         <div class="metric-value">{{ '%.4f'|format(metrics.l2) }}</div></div>
    <div class="metric"><div class="metric-label">L∞ norm</div>
         <div class="metric-value">{{ '%.4f'|format(metrics.linf) }}</div></div>
    <div class="metric"><div class="metric-label">RMS</div>
         <div class="metric-value">{{ '%.4f'|format(metrics.rms) }}</div></div>
  </div>
</div>

<!-- Section 2 — Paper citation -->
<h2>2. 参考文献 (Gold standard)</h2>
<div class="paper-cite">
  <div class="title">{{ paper.title }}</div>
  <div>{{ paper.source }}</div>
  {% if paper.doi %}<div class="doi">DOI: {{ paper.doi }}</div>{% endif %}
  <div style="margin-top:0.6em; font-size:0.88em;">
    Gold sample count: <strong>{{ paper.gold_count }}</strong> points ·
    Tolerance: <strong>±{{ '%.1f'|format(paper.tolerance_pct) }}%</strong>
  </div>
</div>

<!-- Section 3 — Profile overlay -->
<h2>3. 中心线 profile 叠合对比</h2>
<figure>
  <img src="{{ renders.profile_png_rel }}" alt="U centerline profile overlay">
  <figcaption>simpleFoam 实线 vs {{ paper.short }} 离散点，x=0.5 垂直中心线。</figcaption>
</figure>

<!-- Section 4 — Pointwise deviation heatmap -->
<h2>4. 逐点偏差分布 (5% 容差)</h2>
<figure>
  <img src="{{ renders.pointwise_png_rel }}" alt="Pointwise deviation bar chart">
  <figcaption>
    沿 y/L 的逐 gold 点 |dev|%，绿色 &lt; 5% PASS，黄色 5-10% WARN，红色 &gt; 10% FAIL。
    {{ metrics.n_pass }}/{{ metrics.n_total }} 点通过 5% 容差。
  </figcaption>
</figure>

<!-- Section 5 — Full 2D field contour -->
<h2>5. 流场 contour (中心线切片)</h2>
<figure>
  <img src="{{ renders.contour_png_rel }}" alt="U magnitude contour slice">
  <figcaption>
    {{ contour_caption }}
  </figcaption>
</figure>

<!-- Section 6 — Residual convergence -->
<h2>6. 残差收敛历史</h2>
<figure>
  <img src="{{ renders.residuals_png_rel }}" alt="Residual log convergence">
  <figcaption>
    SIMPLE 迭代下 U_x / U_y / p 初始残差对数。收敛到
    {{ '%.1e'|format(residual_info.final_ux) if residual_info.final_ux else 'N/A' }}
    （Ux 终值）经 {{ residual_info.total_iter }} 次迭代。
  </figcaption>
</figure>

{% if residual_info.note %}
<div class="residual-block">{{ residual_info.note }}</div>
{% endif %}

<!-- Section 7 — Grid convergence -->
<h2>7. 网格收敛 (mesh_20 → mesh_160)</h2>
{% if grid_conv %}
<table>
  <thead>
    <tr><th>Mesh</th><th>u(y=0.0625)</th><th>|dev|% vs gold</th><th>verdict</th></tr>
  </thead>
  <tbody>
    {% for row in grid_conv %}
    <tr>
      <td class="mono">{{ row.mesh }}</td>
      <td class="num">{{ '%.4f'|format(row.value) }}</td>
      <td class="num">{{ '%.2f'|format(row.dev_pct) }}%</td>
      <td class="{{ row.verdict_class }}">{{ row.verdict }}</td>
    </tr>
    {% endfor %}
  </tbody>
</table>
<p style="color:#6b7280; font-size:0.88em; margin-top:0.5em;">
  单调收敛: {{ grid_conv_note }} · Richardson p_obs (观察阶数) 延后到 Phase 7d。
</p>
{% else %}
<p style="color:#9ca3af; font-style:italic;">网格收敛数据暂未加载。</p>
{% endif %}

<!-- Section 8 — Solver metadata -->
<h2>8. 求解器元数据</h2>
<table>
  <tbody>
    <tr><th>OpenFOAM</th><td class="mono">{{ meta.openfoam_version }}</td></tr>
    <tr><th>Solver</th><td class="mono">{{ meta.solver }}</td></tr>
    <tr><th>Docker image</th><td class="mono">{{ meta.docker_image }}</td></tr>
    <tr><th>Commit SHA</th><td class="mono">{{ meta.commit_sha }}</td></tr>
    <tr><th>Mesh</th><td class="mono">{{ meta.mesh }}</td></tr>
    <tr><th>Tolerance</th><td class="mono">{{ meta.tolerance }}</td></tr>
    <tr><th>Schemes</th><td class="mono">{{ meta.schemes }}</td></tr>
    <tr><th>Report generated</th><td class="mono">{{ meta.report_generated_at }}</td></tr>
  </tbody>
</table>

<footer>
  Report generated by Phase 7c comparison_report pipeline (DEC-V61-032, {{ meta.report_generated_at[:10] }}).
  CFD harness unified · cfd-harness-unified @ <span class="mono">{{ meta.commit_sha }}</span>
</footer>

</body>
</html>

 succeeded in 0ms:
        hovertemplate="U<sub>x</sub>=%{x:.4f}<br>y/L=%{y:.4f}<extra>gold</extra>",
    ))
    fig.update_layout(
        title=f"{case_id} — U centerline profile vs {citation[:60]}",
        xaxis_title="U_x / U_lid",
        yaxis_title="y / L",
        template="plotly_white",
        hovermode="closest",
        margin=dict(l=50, r=20, t=50, b=50),
    )
    # Static JSON (no widget state). include_plotlyjs='cdn' on frontend side.
    payload = fig.to_json()
    out = renders_dir / "profile_u_centerline.plotly.json"
    out.write_text(payload, encoding="utf-8")
    return out


def render_residuals_png(
    case_id: str,
    artifact_dir: Path,
    renders_dir: Path,
) -> Path:
    """Matplotlib PNG: log-y residual convergence for Ux, Uy, p."""
    csv = artifact_dir / "residuals.csv"
    if not csv.is_file():
        raise RenderError(f"residuals.csv missing: {csv}")
    iters, fields = _load_residuals_csv(csv)

    fig, ax = plt.subplots()
    palette = {"Ux": "#1f77b4", "Uy": "#2ca02c", "p": "#d62728"}
    for name, series in fields.items():
        color = palette.get(name, "#7f7f7f")
        # Use NaN-safe masking so iter-0 'N/A' doesn't break log plot.
        mask = np.isfinite(series) & (series > 0)
        ax.semilogy(iters[mask], series[mask], color=color, label=name)
    ax.set_xlabel("Iteration")
    ax.set_ylabel("Initial residual (log)")
    ax.set_title(f"{case_id} — solver residual convergence")
    ax.legend(loc="upper right", frameon=False)
    out = renders_dir / "residuals.png"
    fig.savefig(out)
    plt.close(fig)
    return out


def render_pointwise_deviation_png(
    case_id: str,
    artifact_dir: Path,
    renders_dir: Path,
) -> Path:
    """Bar chart of |dev|% per gold sample point (sim interpolated onto gold y-grid)."""
    latest = _latest_sample_iter(artifact_dir)
    y_sim, u_sim = _load_sample_xy(latest / "uCenterline.xy")
    y_sim_norm = y_sim / max(y_sim.max(), 1e-12)

    y_gold, u_gold, _ = _load_gold_ldc()
    if not y_gold:
        raise RenderError("no LDC gold reference_values")

    u_sim_interp = np.interp(np.array(y_gold), y_sim_norm, u_sim)
    # Guard against division by ~0.
    denom = np.where(np.abs(u_gold) < 1e-9, 1e-9, np.abs(u_gold))
    dev_pct = 100.0 * np.abs(u_sim_interp - np.array(u_gold)) / denom

    fig, ax = plt.subplots()
    # Color-code: green PASS (<5%), yellow WARN (5-10%), red FAIL (>10%).
    colors = ["#2ca02c" if d < 5 else ("#ff9900" if d < 10 else "#d62728")
              for d in dev_pct]
    ax.bar(range(len(y_gold)), dev_pct, color=colors, edgecolor="white", linewidth=0.5)
    ax.axhline(5, color="gray", linewidth=0.6, linestyle="--", alpha=0.6)
    ax.set_xticks(range(len(y_gold)))
    ax.set_xticklabels([f"{y:.3f}" for y in y_gold], rotation=45, ha="right", fontsize=8)
    ax.set_xlabel("Gold sample y/L")
    ax.set_ylabel("|dev|% vs Ghia 1982")
    ax.set_title(f"{case_id} — pointwise deviation (5% tolerance)")
    # Annotate PASS/FAIL count.
    n_pass = int((dev_pct < 5).sum())
    ax.text(
        0.98, 0.95, f"{n_pass}/{len(dev_pct)} PASS",
        transform=ax.transAxes, ha="right", va="top",
        fontsize=10, fontweight="bold",
        color="#2ca02c" if n_pass == len(dev_pct) else "#d62728",
    )
    out = renders_dir / "pointwise_deviation.png"
    fig.savefig(out)
    plt.close(fig)
    return out


def render_contour_u_magnitude_png(
    case_id: str,
    artifact_dir: Path,
    renders_dir: Path,
) -> Path:
    """LDC MVP contour: uses the sample/{iter}/uCenterline.xy which is a 1D profile
    along x=0.5 centerline. For a true 2D contour we'd need to parse the full VTK
    volume, which requires the `vtk` package — deferred to Phase 7b polish.

    Instead, render a stylized 1D heatmap strip showing U_x(y) along the centerline.
    This is honestly labeled as "centerline slice" not "full field contour".
    """
    latest = _latest_sample_iter(artifact_dir)
    y_sim, u_sim = _load_sample_xy(latest / "uCenterline.xy")
    y_norm = y_sim / max(y_sim.max(), 1e-12)

    fig, ax = plt.subplots(figsize=(4, 6))
    # Tile the 1D profile horizontally to make a strip heatmap visible.
    strip = np.tile(u_sim.reshape(-1, 1), (1, 20))
    im = ax.imshow(
        strip,
        aspect="auto",
        origin="lower",
        extent=[0, 1, float(y_norm.min()), float(y_norm.max())],
        cmap="RdBu_r",
        vmin=-1.0, vmax=1.0,
    )
    ax.set_xlabel("(tile axis)")
    ax.set_ylabel("y / L")
    ax.set_title(f"{case_id} — U_x centerline slice\n(Phase 7b MVP — full 2D VTK contour\ndeferred to 7b-polish)")
    cbar = fig.colorbar(im, ax=ax, fraction=0.08, pad=0.04)
    cbar.set_label("U_x / U_lid")
    out = renders_dir / "contour_u_magnitude.png"
    fig.savefig(out)
    plt.close(fig)
    return out


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def render_all(case_id: str, run_label: str = "audit_real_run") -> dict:
    """Render all 7b MVP figures for a given case/run. Returns {name: path, ...}."""
    if case_id not in RENDER_SUPPORTED_CASES:
        raise RenderError(
            f"case_id={case_id!r} not opted-in for Phase 7b rendering. "
            f"Supported: {sorted(RENDER_SUPPORTED_CASES)}. "
            f"Other cases unlock in Phase 7c Sprint-2."
        )
    timestamp = _resolve_run_timestamp(case_id, run_label)
    artifact_dir = _artifact_dir(case_id, timestamp)
    renders_dir = _renders_dir(case_id, timestamp)

    outputs: dict[str, Path] = {}
    renderers = [
        ("profile_png", render_profile_png),
        ("profile_plotly_json", render_profile_plotly_json),
        ("residuals_png", render_residuals_png),
        ("pointwise_deviation_png", render_pointwise_deviation_png),
        ("contour_u_magnitude_png", render_contour_u_magnitude_png),
    ]
    errors: dict[str, str] = {}
    for name, fn in renderers:
        try:
            outputs[name] = fn(case_id, artifact_dir, renders_dir)
        except Exception as e:  # noqa: BLE001  — keep batch alive
            errors[name] = f"{type(e).__name__}: {e}"
            print(f"[render] [WARN] {name} failed: {e}", file=sys.stderr)

    # Write per-run renders manifest (mirrors phase5_fields/{case}/runs/{label}.json).
    manifest_dir = RENDERS_ROOT / case_id / "runs"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "case_id": case_id,
        "run_label": run_label,
        "timestamp": timestamp,
        "renders_dir_rel": str(renders_dir.relative_to(REPO_ROOT)),
        "outputs": {k: str(p.relative_to(REPO_ROOT)) for k, p in outputs.items()},
        "errors": errors,
    }
    manifest_path = manifest_dir / f"{run_label}.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"[render] {case_id} → {len(outputs)}/{len(renderers)} outputs; manifest={manifest_path}")
    return {"manifest": manifest_path, **outputs}


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Phase 7b render pipeline for CFD audit artifacts")
    parser.add_argument("case_id", help="e.g. lid_driven_cavity")
    parser.add_argument("--run", dest="run_label", default="audit_real_run",
                        help="run_label (default: audit_real_run)")
    args = parser.parse_args(argv)
    try:
        render_all(args.case_id, args.run_label)
        return 0
    except RenderError as e:
        print(f"[render] FATAL {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

 succeeded in 0ms:
"""Phase 7c — CFD vs Gold comparison report service.

Renders an 8-section HTML report for a given (case_id, run_label), using:
- Phase 7a field artifacts at reports/phase5_fields/{case}/{ts}/
- Phase 7b rendered figures at reports/phase5_renders/{case}/{ts}/
- knowledge/gold_standards/{case}.yaml gold reference
- ui/backend/tests/fixtures/runs/{case}/mesh_{20,40,80,160}_measurement.yaml for grid convergence

Backend route: ui/backend/routes/comparison_report.py calls `render_report_html`
and `render_report_pdf` from this module. No DOM / no JS — static HTML + PNG
inlined assets referenced by file:// for WeasyPrint PDF, served via FileResponse
or embedded iframe on frontend.

Design: report_html is a self-contained string (no asset URLs pointing to
/api/... — uses file:// for PDF rendering and relative paths for HTML serving).
"""
from __future__ import annotations

import datetime
import json
import math
import subprocess
from pathlib import Path
from typing import Any, Optional

import numpy as np
import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape

_MODULE_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _MODULE_DIR.parents[2]
_TEMPLATES = _MODULE_DIR.parent / "templates"
_FIELDS_ROOT = _REPO_ROOT / "reports" / "phase5_fields"
_RENDERS_ROOT = _REPO_ROOT / "reports" / "phase5_renders"
_GOLD_ROOT = _REPO_ROOT / "knowledge" / "gold_standards"
_FIXTURE_ROOT = _REPO_ROOT / "ui" / "backend" / "tests" / "fixtures" / "runs"

_REPORT_SUPPORTED_CASES = frozenset({"lid_driven_cavity"})

_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATES)),
    autoescape=select_autoescape(["html", "htm"]),
)


class ReportError(Exception):
    """Recoverable — caller should 404 or return partial payload."""


# ---------------------------------------------------------------------------
# Data assembly
# ---------------------------------------------------------------------------


def _run_manifest_path(case_id: str, run_label: str) -> Path:
    return _FIELDS_ROOT / case_id / "runs" / f"{run_label}.json"


def _renders_manifest_path(case_id: str, run_label: str) -> Path:
    return _RENDERS_ROOT / case_id / "runs" / f"{run_label}.json"


def _load_run_manifest(case_id: str, run_label: str) -> dict:
    p = _run_manifest_path(case_id, run_label)
    if not p.is_file():
        raise ReportError(f"no run manifest for {case_id}/{run_label}")
    return json.loads(p.read_text(encoding="utf-8"))


def _load_renders_manifest(case_id: str, run_label: str) -> Optional[dict]:
    p = _renders_manifest_path(case_id, run_label)
    if not p.is_file():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def _load_ldc_gold() -> tuple[list[float], list[float], dict]:
    gold_path = _GOLD_ROOT / "lid_driven_cavity.yaml"
    if not gold_path.is_file():
        raise ReportError(f"gold file missing: {gold_path}")
    docs = list(yaml.safe_load_all(gold_path.read_text(encoding="utf-8")))
    u_doc = next(
        (d for d in docs if isinstance(d, dict) and d.get("quantity") == "u_centerline"),
        None,
    )
    if u_doc is None:
        raise ReportError("no u_centerline doc in LDC gold")
    ys: list[float] = []
    us: list[float] = []
    for entry in u_doc.get("reference_values", []):
        if isinstance(entry, dict):
            y = entry.get("y")
            u = entry.get("value") or entry.get("u")
            if y is not None and u is not None:
                ys.append(float(y))
                us.append(float(u))
    return ys, us, u_doc


def _load_sample_xy(path: Path) -> tuple[np.ndarray, np.ndarray]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        parts = s.split()
        try:
            rows.append([float(parts[0]), float(parts[1])])
        except (ValueError, IndexError):
            continue
    if not rows:
        raise ReportError(f"empty sample: {path}")
    arr = np.array(rows)
    return arr[:, 0], arr[:, 1]


def _latest_sample_iter(artifact_dir: Path) -> Path:
    sample_root = artifact_dir / "sample"
    if not sample_root.is_dir():
        raise ReportError(f"sample/ missing under {artifact_dir}")
    iters = sorted(
        (d for d in sample_root.iterdir() if d.is_dir() and d.name.isdigit()),
        key=lambda d: int(d.name),
    )
    if not iters:
        raise ReportError(f"no sample iter dirs under {sample_root}")
    return iters[-1]


def _compute_metrics(
    y_sim: np.ndarray, u_sim: np.ndarray,
    y_gold: list[float], u_gold: list[float],
    tolerance_pct: float,
) -> dict[str, Any]:
    """Compute L2/Linf/RMS + per-point |dev|% + pass count."""
    y_sim_norm = y_sim / max(float(y_sim.max()), 1e-12)
    u_sim_interp = np.interp(np.array(y_gold), y_sim_norm, u_sim)
    u_gold_arr = np.array(u_gold)
    diff = u_sim_interp - u_gold_arr

    denom = np.where(np.abs(u_gold_arr) < 1e-9, 1e-9, np.abs(u_gold_arr))
    dev_pct = 100.0 * np.abs(diff) / denom
    n_total = len(u_gold_arr)
    n_pass = int((dev_pct < tolerance_pct).sum())

    return {
        "l2": float(np.sqrt(np.mean(diff ** 2))),
        "linf": float(np.max(np.abs(diff))),
        "rms": float(np.sqrt(np.mean(diff ** 2))),  # alias
        "max_dev_pct": float(dev_pct.max()) if n_total else 0.0,
        "n_pass": n_pass,
        "n_total": n_total,
        "per_point_dev_pct": dev_pct.tolist(),
    }


def _parse_residuals_csv(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"total_iter": 0, "final_ux": None, "note": None}
    lines = path.read_text(encoding="utf-8").splitlines()
    if len(lines) < 2:
        return {"total_iter": 0, "final_ux": None, "note": None}
    header = [c.strip() for c in lines[0].split(",")]
    last = None
    count = 0
    for ln in lines[1:]:
        parts = [c.strip() for c in ln.split(",")]
        if len(parts) != len(header):
            continue
        last = parts
        count += 1
    final_ux = None
    if last is not None and len(last) > 1 and last[1].upper() != "N/A":
        try:
            final_ux = float(last[1])
        except ValueError:
            pass
    note = None
    if final_ux is not None and final_ux > 1e-3:
        note = (f"注意：Ux 终值 {final_ux:.2e} 大于 1e-3 — "
                f"收敛可能未达稳态。建议增加 endTime 或降低 residualControl。")
    return {"total_iter": count, "final_ux": final_ux, "note": note}


def _load_grid_convergence(case_id: str, gold_y: list[float], gold_u: list[float]) -> tuple[list[dict], str]:
    """Read mesh_20/40/80/160_measurement.yaml fixtures, build table rows."""
    rows: list[dict] = []
    # LDC fixtures compare at y≈0.0625 (first gold point >0).
    sample_y = 0.0625
    try:
        sample_gold = next(u for y, u in zip(gold_y, gold_u) if abs(y - sample_y) < 1e-3)
    except StopIteration:
        sample_gold = gold_u[1] if len(gold_u) > 1 else 0.0

    case_dir = _FIXTURE_ROOT / case_id
    meshes = [("mesh_20", 20), ("mesh_40", 40), ("mesh_80", 80), ("mesh_160", 160)]
    for name, _n in meshes:
        path = case_dir / f"{name}_measurement.yaml"
        if not path.is_file():
            continue
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        meas = doc.get("measurement", {}) if isinstance(doc, dict) else {}
        val = meas.get("value")
        if val is None:
            continue
        try:
            val_f = float(val)
        except (ValueError, TypeError):
            continue
        denom = abs(sample_gold) if abs(sample_gold) > 1e-9 else 1e-9
        dev_pct = 100.0 * abs(val_f - sample_gold) / denom
        if dev_pct < 5.0:
            verdict, cls = "PASS", "pass"
        elif dev_pct < 10.0:
            verdict, cls = "WARN", "warn"
        else:
            verdict, cls = "FAIL", "fail"
        rows.append({
            "mesh": name,
            "value": val_f,
            "dev_pct": dev_pct,
            "verdict": verdict,
            "verdict_class": cls,
        })
    if len(rows) < 2:
        return rows, "insufficient mesh data"
    devs = [r["dev_pct"] for r in rows]
    monotone = all(devs[i] >= devs[i + 1] for i in range(len(devs) - 1))
    note = "单调递减 ✓" if monotone else "非严格单调 — 检查 fixture"
    return rows, note


def _get_commit_sha() -> str:
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, cwd=_REPO_ROOT, timeout=5,
        )
        return r.stdout.strip() or "unknown"
    except (subprocess.SubprocessError, OSError):
        return "unknown"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def build_report_context(case_id: str, run_label: str = "audit_real_run") -> dict:
    """Assemble all template variables. Raises ReportError on missing data."""
    if case_id not in _REPORT_SUPPORTED_CASES:
        raise ReportError(
            f"case_id={case_id!r} not in Phase 7c MVP scope. "
            f"Supported: {sorted(_REPORT_SUPPORTED_CASES)}."
        )

    run_manifest = _load_run_manifest(case_id, run_label)
    timestamp = run_manifest["timestamp"]
    artifact_dir = _FIELDS_ROOT / case_id / timestamp
    if not artifact_dir.is_dir():

 succeeded in 0ms:
        raise ReportError(f"artifact dir missing: {artifact_dir}")

    # Load + compute
    gold_y, gold_u, gold_doc = _load_ldc_gold()
    tolerance = float(gold_doc.get("tolerance", 0.05)) * 100.0  # fraction → percent
    latest_sample = _latest_sample_iter(artifact_dir)
    y_sim, u_sim = _load_sample_xy(latest_sample / "uCenterline.xy")
    metrics = _compute_metrics(y_sim, u_sim, gold_y, gold_u, tolerance)

    residual_info = _parse_residuals_csv(artifact_dir / "residuals.csv")
    grid_conv_rows, grid_note = _load_grid_convergence(case_id, gold_y, gold_u)

    # Verdict logic: all-pass OR tolerance met.
    is_all_pass = metrics["n_pass"] == metrics["n_total"] and metrics["n_total"] > 0
    majority_pass = metrics["n_pass"] >= math.ceil(metrics["n_total"] * 0.6)
    if is_all_pass:
        verdict, verdict_gradient, subtitle = "PASS", "#059669 0%, #10b981 100%", (
            f"全部 {metrics['n_total']} 个 gold 点在 ±{tolerance:.1f}% 容差内。"
        )
    elif majority_pass:
        verdict, verdict_gradient, subtitle = "PARTIAL", "#d97706 0%, #f59e0b 100%", (
            f"{metrics['n_pass']}/{metrics['n_total']} 点通过；"
            f"{metrics['n_total'] - metrics['n_pass']} 点残差为已记录物理项 "
            f"(见 DEC-V61-030 关于 Ghia 非均匀网格 vs 均匀网格的插值误差)。"
        )
    else:
        verdict, verdict_gradient, subtitle = "FAIL", "#dc2626 0%, #ef4444 100%", (
            f"仅 {metrics['n_pass']}/{metrics['n_total']} 点通过 — "
            f"需要诊断 (solver, mesh, 或 gold 本身)。"
        )

    # Renders — use Phase 7b manifest if available; else None placeholders.
    renders_manifest = _load_renders_manifest(case_id, run_label)
    renders_dir = _RENDERS_ROOT / case_id / timestamp

    def _rel(key: str, default: str = "") -> str:
        if renders_manifest and key in renders_manifest.get("outputs", {}):
            return renders_manifest["outputs"][key]
        # Fallback: guess the conventional name
        guess = renders_dir / default
        return str(guess.relative_to(_REPO_ROOT)) if guess.is_file() else ""

    renders = {
        "profile_png_rel": _rel("profile_png", "profile_u_centerline.png"),
        "pointwise_png_rel": _rel("pointwise_deviation_png", "pointwise_deviation.png"),
        "contour_png_rel": _rel("contour_u_magnitude_png", "contour_u_magnitude.png"),
        "residuals_png_rel": _rel("residuals_png", "residuals.png"),
    }

    paper = {
        "title": gold_doc.get("source", "Ghia, Ghia & Shin 1982 — Lid-Driven Cavity benchmark"),
        "source": "J. Comput. Phys. 47, 387-411 (1982), Table I Re=100 column",
        "doi": gold_doc.get("literature_doi", "10.1016/0021-9991(82)90058-4"),
        "short": "Ghia 1982",
        "gold_count": metrics["n_total"],
        "tolerance_pct": tolerance,
    }

    now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")

    return {
        "case_id": case_id,
        "case_display_name": "Lid-Driven Cavity (Re=100)" if case_id == "lid_driven_cavity" else case_id,
        "run_label": run_label,
        "timestamp": timestamp,
        "verdict": verdict,
        "verdict_gradient": verdict_gradient,
        "verdict_subtitle": subtitle,
        "metrics": metrics,
        "paper": paper,
        "renders": renders,
        "contour_caption": (
            "Phase 7b MVP — 沿 x=0.5 中心线的 U_x 条带切片，后续 7b-polish 会用 VTK 体数据生成完整 2D contour。"
        ),
        "residual_info": residual_info,
        "grid_conv": grid_conv_rows,
        "grid_conv_note": grid_note,
        "meta": {
            "openfoam_version": "v10",
            "solver": "simpleFoam (SIMPLE, laminar)",
            "docker_image": "cfd-openfoam (local arm64 OpenFOAM v10)",
            "commit_sha": _get_commit_sha(),
            "mesh": "129×129 uniform",
            "tolerance": f"±{tolerance:.1f}%",
            "schemes": "steadyState + linearUpwind + Gauss linear corrected",
            "report_generated_at": now,
        },
    }


def render_report_html(case_id: str, run_label: str = "audit_real_run") -> str:
    """Return the full HTML string for the comparison report."""
    ctx = build_report_context(case_id, run_label)
    tmpl = _env.get_template("comparison_report.html.j2")
    return tmpl.render(**ctx)


def render_report_pdf(case_id: str, run_label: str = "audit_real_run",
                      output_path: Optional[Path] = None) -> Path:
    """Render HTML to PDF via WeasyPrint and write to disk. Returns the file Path.

    Asset resolution: WeasyPrint converts the HTML's relative img src paths.
    We pass base_url=_REPO_ROOT so /reports/phase5_renders/... resolves correctly.
    """
    # Import weasyprint lazily — heavy import, only when PDF actually needed.
    import weasyprint  # type: ignore

    html = render_report_html(case_id, run_label)
    if output_path is None:
        ctx = build_report_context(case_id, run_label)
        ts = ctx["timestamp"]
        out_dir = _REPO_ROOT / "reports" / "phase5_reports" / case_id / ts
        out_dir.mkdir(parents=True, exist_ok=True)
        output_path = out_dir / f"{run_label}_comparison_report.pdf"

    doc = weasyprint.HTML(string=html, base_url=str(_REPO_ROOT))
    doc.write_pdf(str(output_path))
    return output_path

exec
/bin/zsh -lc "sed -n '1,260p' ui/backend/routes/comparison_report.py" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
"""Phase 7c — CFD vs Gold comparison report route.

GET  /api/cases/{case_id}/runs/{run_label}/comparison-report         → HTML
GET  /api/cases/{case_id}/runs/{run_label}/comparison-report.pdf     → PDF
POST /api/cases/{case_id}/runs/{run_label}/comparison-report/build   → rebuild PDF + return manifest

Uses FileResponse pattern per Phase 7a user ratification #1 (no StaticFiles).
"""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

from ui.backend.services.comparison_report import (
    ReportError,
    build_report_context,
    render_report_html,
    render_report_pdf,
)
from ui.backend.services.run_ids import _validate_segment

router = APIRouter()


def _validate_ids(case_id: str, run_label: str) -> None:
    """Reuse Phase 7a traversal defense on case_id + run_label segments."""
    _validate_segment(case_id, "case_id")
    _validate_segment(run_label, "run_label")


@router.get(
    "/cases/{case_id}/runs/{run_label}/comparison-report",
    response_class=HTMLResponse,
    tags=["comparison-report"],
)
def get_comparison_report_html(case_id: str, run_label: str) -> HTMLResponse:
    """Return rendered HTML report (suitable for iframe embedding)."""
    _validate_ids(case_id, run_label)
    try:
        html = render_report_html(case_id, run_label)
    except ReportError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return HTMLResponse(html)


@router.get(
    "/cases/{case_id}/runs/{run_label}/comparison-report/context",
    tags=["comparison-report"],
)
def get_comparison_report_context(case_id: str, run_label: str) -> JSONResponse:
    """Return the raw template context as JSON (for frontend custom rendering
    if it wants to skip the server-rendered HTML and compose its own)."""
    _validate_ids(case_id, run_label)
    try:
        ctx = build_report_context(case_id, run_label)
    except ReportError as e:
        raise HTTPException(status_code=404, detail=str(e))
    # Strip non-JSON-serializable entries (e.g., numpy arrays).
    # per_point_dev_pct is already list(); metrics keys are all primitives.
    return JSONResponse(ctx)


@router.get(
    "/cases/{case_id}/runs/{run_label}/comparison-report.pdf",
    tags=["comparison-report"],
)
def get_comparison_report_pdf(case_id: str, run_label: str) -> FileResponse:
    """Render (or re-render) PDF and stream it back."""
    _validate_ids(case_id, run_label)
    try:
        path = render_report_pdf(case_id, run_label)
    except ReportError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ImportError:
        raise HTTPException(
            status_code=503,
            detail="WeasyPrint unavailable on this server; set DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib",
        )
    return FileResponse(
        path,
        media_type="application/pdf",
        filename=f"{case_id}__{run_label}__comparison_report.pdf",
    )


@router.post(
    "/cases/{case_id}/runs/{run_label}/comparison-report/build",
    tags=["comparison-report"],
)
def build_comparison_report(case_id: str, run_label: str) -> JSONResponse:
    """Force-rebuild HTML + PDF, return manifest."""
    _validate_ids(case_id, run_label)
    try:
        html = render_report_html(case_id, run_label)
        pdf_path = render_report_pdf(case_id, run_label)
    except ReportError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ImportError:
        raise HTTPException(status_code=503, detail="WeasyPrint unavailable")
    return JSONResponse({
        "case_id": case_id,
        "run_label": run_label,
        "pdf_path": str(pdf_path),
        "html_bytes": len(html),
    })

exec
/bin/zsh -lc "sed -n '1,260p' ui/backend/tests/test_comparison_report_route.py" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
"""Phase 7c — comparison report route tests.

Guards route-level behavior: 200 on valid case/run, 404 on missing, 400 on
traversal attempts. Actual HTML content is covered by unit tests of the
service module.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from ui.backend.main import app

client = TestClient(app)

# These tests run against the real reports/phase5_fields/lid_driven_cavity/
# artifact set which is .gitignored. In CI (no artifacts), they should 404 —
# which is fine, they'll be re-collected on developer machines.


def _has_ldc_artifacts() -> bool:
    from pathlib import Path
    manifest = Path("reports/phase5_fields/lid_driven_cavity/runs/audit_real_run.json")
    return manifest.is_file()


def test_html_200_when_artifacts_present() -> None:
    if not _has_ldc_artifacts():
        return  # skip silently on CI-style clean checkout
    r = client.get("/api/cases/lid_driven_cavity/runs/audit_real_run/comparison-report")
    assert r.status_code == 200, r.text
    body = r.text
    # 8 section markers from the Jinja template.
    for marker in [
        "参考文献",           # §2
        "中心线 profile",      # §3
        "逐点偏差分布",        # §4
        "流场 contour",        # §5
        "残差收敛历史",        # §6
        "网格收敛",            # §7
        "求解器元数据",        # §8
    ]:
        assert marker in body, f"missing section marker: {marker}"
    # Verdict card must be present.
    assert "verdict-card" in body


def test_context_200_when_artifacts_present() -> None:
    if not _has_ldc_artifacts():
        return
    r = client.get(
        "/api/cases/lid_driven_cavity/runs/audit_real_run/comparison-report/context",
    )
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["case_id"] == "lid_driven_cavity"
    assert d["run_label"] == "audit_real_run"
    assert "metrics" in d
    assert d["metrics"]["n_total"] > 0
    assert d["verdict"] in ("PASS", "PARTIAL", "FAIL")


def test_html_404_unknown_case() -> None:
    r = client.get("/api/cases/nonexistent_case/runs/audit_real_run/comparison-report")
    assert r.status_code == 404


def test_html_400_traversal_case_id() -> None:
    r = client.get("/api/cases/..__pwn/runs/audit_real_run/comparison-report")
    assert r.status_code == 400


def test_html_400_traversal_run_label() -> None:
    r = client.get("/api/cases/lid_driven_cavity/runs/..__pwn/comparison-report")
    assert r.status_code == 400


def test_context_400_urlencoded_traversal() -> None:
    r = client.get(
        "/api/cases/%2e%2e__pwn/runs/audit_real_run/comparison-report/context",
    )
    assert r.status_code == 400

exec
/bin/zsh -lc "sed -n '1,260p' ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
import { useQueries, useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";

import { api, ApiError } from "@/api/client";
import { CaseIllustration } from "@/components/learn/CaseIllustration";
import { getFlowFields } from "@/data/flowFields";
import { getLearnCase } from "@/data/learnCases";
import type {
  ContractStatus,
  RunCategory,
  RunDescriptor,
  ValidationReport,
} from "@/types/validation";

// Student-facing case detail. Four tabs:
//   Story    — default. physics, canonical reference, why validation matters
//   Compare  — gold vs measurement, tolerance band. Framed as a learning moment
//   Run      — residuals chart placeholder (real streaming lives in Pro Workbench)
//   Advanced — decision trail + link to audit package (the pro-evidence surface)
//
// The backend ValidationReport fetch is shared; sub-tabs derive their views
// from that single record so the student can flip between them without
// re-fetching.

type TabId = "story" | "compare" | "mesh" | "run" | "advanced";

const TABS: { id: TabId; label_zh: string; label_en: string }[] = [
  { id: "story", label_zh: "故事", label_en: "Story" },
  { id: "compare", label_zh: "对比", label_en: "Compare" },
  { id: "mesh", label_zh: "网格", label_en: "Mesh" },
  { id: "run", label_zh: "运行", label_en: "Run" },
  { id: "advanced", label_zh: "进阶", label_en: "Advanced" },
];

// Cases with a curated grid-convergence sweep (4 meshes each). Every
// case in the /learn catalog now has one. If a new case is added,
// author 4 mesh_N fixtures and register its density labels here.
const GRID_CONVERGENCE_CASES: Record<
  string,
  { meshLabel: string; densities: { id: string; label: string; n: number }[] }
> = {
  lid_driven_cavity: {
    meshLabel: "uniform grid N×N",
    densities: [
      { id: "mesh_20", label: "20²", n: 400 },
      { id: "mesh_40", label: "40²", n: 1600 },
      { id: "mesh_80", label: "80²", n: 6400 },
      { id: "mesh_160", label: "160²", n: 25600 },
    ],
  },
  turbulent_flat_plate: {
    meshLabel: "wall-normal cells",
    densities: [
      { id: "mesh_20", label: "20 y-cells", n: 20 },
      { id: "mesh_40", label: "40 y-cells", n: 40 },
      { id: "mesh_80", label: "80 y-cells + 4:1", n: 80 },
      { id: "mesh_160", label: "160 y-cells", n: 160 },
    ],
  },
  backward_facing_step: {
    meshLabel: "recirculation cells",
    densities: [
      { id: "mesh_20", label: "20 cells", n: 20 },
      { id: "mesh_40", label: "40 cells", n: 40 },
      { id: "mesh_80", label: "80 cells", n: 80 },
      { id: "mesh_160", label: "160 cells", n: 160 },
    ],
  },
  circular_cylinder_wake: {
    meshLabel: "azimuthal cells around cylinder",
    densities: [
      { id: "mesh_20", label: "20 azim", n: 20 },
      { id: "mesh_40", label: "40 azim", n: 40 },
      { id: "mesh_80", label: "80 azim", n: 80 },
      { id: "mesh_160", label: "160 azim", n: 160 },
    ],
  },
  duct_flow: {
    meshLabel: "cross-section cells",
    densities: [
      { id: "mesh_20", label: "20² uniform", n: 400 },
      { id: "mesh_40", label: "40² + 2:1", n: 1600 },
      { id: "mesh_80", label: "80² + 4:1", n: 6400 },
      { id: "mesh_160", label: "160²", n: 25600 },
    ],
  },
  differential_heated_cavity: {
    meshLabel: "square cavity N×N + wall grading",
    densities: [
      { id: "mesh_20", label: "20² uniform", n: 400 },
      { id: "mesh_40", label: "40² + 1.5:1", n: 1600 },
      { id: "mesh_80", label: "80² + 4:1", n: 6400 },
      { id: "mesh_160", label: "160² + 4:1", n: 25600 },
    ],
  },
  plane_channel_flow: {
    meshLabel: "isotropic cubed cells",
    densities: [
      { id: "mesh_20", label: "20³ RANS", n: 8000 },
      { id: "mesh_40", label: "40³ hybrid", n: 64000 },
      { id: "mesh_80", label: "80³ WR-LES", n: 512000 },
      { id: "mesh_160", label: "160³ DNS", n: 4096000 },
    ],
  },
  impinging_jet: {
    meshLabel: "radial cells in stagnation region",
    densities: [
      { id: "mesh_20", label: "20 rad", n: 20 },
      { id: "mesh_40", label: "40 rad + 2:1", n: 40 },
      { id: "mesh_80", label: "80 rad + 4:1", n: 80 },
      { id: "mesh_160", label: "160 rad", n: 160 },
    ],
  },
  naca0012_airfoil: {
    meshLabel: "surface cells per side",
    densities: [
      { id: "mesh_20", label: "20 surf + 8-chord", n: 20 },
      { id: "mesh_40", label: "40 surf + 15-chord", n: 40 },
      { id: "mesh_80", label: "80 surf + 40-chord", n: 80 },
      { id: "mesh_160", label: "160 surf", n: 160 },
    ],
  },
  rayleigh_benard_convection: {
    meshLabel: "square cavity + wall packing",
    densities: [
      { id: "mesh_20", label: "20² uniform", n: 400 },
      { id: "mesh_40", label: "40² + 2:1", n: 1600 },
      { id: "mesh_80", label: "80² + 4:1", n: 6400 },
      { id: "mesh_160", label: "160² + 4:1", n: 25600 },
    ],
  },
};

const STATUS_TEXT: Record<ContractStatus, string> = {
  PASS: "对齐黄金标准",
  HAZARD: "落入带内，但可能是 silent-pass",
  FAIL: "偏离了 tolerance band",
  UNKNOWN: "尚无可对比的测量值",
};

const STATUS_CLASS: Record<ContractStatus, string> = {
  PASS: "text-contract-pass",
  HAZARD: "text-contract-hazard",
  FAIL: "text-contract-fail",
  UNKNOWN: "text-surface-400",
};

const isTabId = (v: string | null): v is TabId =>
  v === "story" ||
  v === "compare" ||
  v === "mesh" ||
  v === "run" ||
  v === "advanced";

export function LearnCaseDetailPage() {
  const { caseId } = useParams<{ caseId: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const rawTab = searchParams.get("tab");
  const tab: TabId = isTabId(rawTab) ? rawTab : "story";
  const setTab = (next: TabId) => {
    const params = new URLSearchParams(searchParams);
    if (next === "story") params.delete("tab");
    else params.set("tab", next);
    setSearchParams(params, { replace: true });
  };

  const learnCase = caseId ? getLearnCase(caseId) : undefined;
  const runId = searchParams.get("run") || undefined;

  const { data: report, error } = useQuery<ValidationReport, ApiError>({
    queryKey: ["validation-report", caseId, runId ?? "default"],
    queryFn: () => api.getValidationReport(caseId!, runId),
    enabled: !!caseId,
    retry: false,
  });

  const { data: runs } = useQuery<RunDescriptor[], ApiError>({
    queryKey: ["case-runs", caseId],
    queryFn: () => api.listCaseRuns(caseId!),
    enabled: !!caseId,
    retry: false,
  });

  const setRunId = (nextRun: string | null) => {
    const params = new URLSearchParams(searchParams);
    if (nextRun) params.set("run", nextRun);
    else params.delete("run");
    setSearchParams(params, { replace: true });
  };

  if (!caseId || !learnCase) {
    return (
      <div className="mx-auto max-w-3xl px-6 py-16 text-center text-surface-400">
        <p>找不到这个案例。</p>
        <Link to="/learn" className="mt-4 inline-block text-sky-400 hover:text-sky-300">
          ← 回到目录
        </Link>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-4xl px-6 pt-8 pb-16">
      {/* Breadcrumb + case-export + Pro Workbench switch */}
      <nav className="mb-6 flex items-center justify-between gap-3 text-[12px] text-surface-500">
        <div>
          <Link to="/learn" className="hover:text-surface-300">
            目录
          </Link>
          <span className="mx-2 text-surface-700">/</span>
          <span className="mono text-surface-400">{caseId}</span>
        </div>
        <div className="flex items-center gap-2">
          <a
            href={`/api/cases/${caseId}/export`}
            download={`${caseId}_reference.zip`}
            className="group inline-flex items-center gap-1.5 rounded-sm border border-surface-800 bg-surface-900/60 px-2.5 py-1 text-[11px] text-surface-400 transition-colors hover:border-emerald-700/60 hover:bg-surface-900 hover:text-emerald-300"
            title="Download a reference bundle: gold standard YAML, validation contract, reproduction README"
          >
            <span>下载参考包</span>
            <span className="mono text-surface-600 group-hover:text-emerald-400">
              .zip ↓
            </span>
          </a>
          <Link
            to={`/audit-package?case=${encodeURIComponent(caseId ?? "")}&run=audit_real_run`}
            className="group inline-flex items-center gap-1.5 rounded-sm border border-surface-800 bg-surface-900/60 px-2.5 py-1 text-[11px] text-surface-400 transition-colors hover:border-amber-700/60 hover:bg-surface-900 hover:text-amber-300"
            title="Build a signed audit package from the real-solver audit_real_run fixture (HMAC-signed zip + manifest + html + pdf + sig)"
          >
            <span>签名审计包</span>
            <span className="mono text-surface-600 group-hover:text-amber-400">
              HMAC ↓
            </span>
          </Link>
          <Link
            to={`/cases/${caseId}/report`}
            className="group inline-flex items-center gap-1.5 rounded-sm border border-surface-800 bg-surface-900/60 px-2.5 py-1 text-[11px] text-surface-400 transition-colors hover:border-sky-700/60 hover:bg-surface-900 hover:text-sky-300"
            title="Switch to the evidence-heavy audit surface (Validation Report, Decisions Queue, Audit Package)"
          >
            <span>进入专业工作台</span>
            <span className="mono text-surface-600 group-hover:text-sky-400">
              Pro Workbench →
            </span>
          </Link>
        </div>
      </nav>

      {/* Hero */}
      <header className="mb-8 grid gap-6 md:grid-cols-[1fr_240px]">
        <div>
          <p className="text-[11px] font-medium uppercase tracking-[0.18em] text-surface-500">
            {learnCase.canonical_ref}
          </p>
          <h1 className="mt-1.5 text-3xl font-semibold leading-tight text-surface-100">
            {learnCase.headline_zh}
          </h1>
          <p className="mt-1 text-[13px] text-surface-400">
            {learnCase.displayName} · {learnCase.headline_en}
          </p>

codex
The backend pieces are straightforward; the remaining uncertainty is in the exact frontend hide/error behavior and whether the report template can be tricked into local-file reads through asset paths. I’m drilling into the specific JSX branch, the run-id validator, and the gold/fixture file shapes next.
exec
/bin/zsh -lc "sed -n '1,240p' ui/backend/services/run_ids.py" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
"""Phase 7a — run_id parsing helper.

Per user ratification #5 (2026-04-21): run_id = "{case_id}__{run_label}".
We use rpartition on the last "__" so case_ids with internal underscores
(e.g. 'lid_driven_cavity') still parse correctly (07a-RESEARCH.md §2.7).
"""
from __future__ import annotations

import re
from urllib.parse import unquote

from fastapi import HTTPException

# Identifier pattern for case_id and run_label segments.
# Allow alphanumerics, underscore, hyphen, dot. Explicitly REJECT path
# separators, '..', leading dots, and percent/url-encoded traversal markers.
# Codex round 1 HIGH #2 (2026-04-21): traversal via run_id reproduced with
# '..__pwn' AND '%2e%2e__pwn' — guard both decoded and raw forms.
_SEGMENT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_\-]*$")


def _validate_segment(name: str, kind: str) -> None:
    """Reject traversal markers before building filesystem paths.

    Rejects: empty, '.', '..', anything containing '/', '\\', '%', or not
    matching the strict identifier pattern. Also rejects URL-decoded forms
    (in case middleware forgot to decode) so '%2e%2e' → '..' is caught.
    """
    if not name or name in (".", ".."):
        raise HTTPException(status_code=400, detail=f"invalid {kind}")
    decoded = unquote(name)
    if decoded != name or decoded in (".", ".."):
        raise HTTPException(status_code=400, detail=f"invalid {kind}")
    if "/" in name or "\\" in name or ".." in name:
        raise HTTPException(status_code=400, detail=f"invalid {kind}")
    if not _SEGMENT_RE.match(name):
        raise HTTPException(status_code=400, detail=f"invalid {kind}")


def parse_run_id(run_id: str) -> tuple[str, str]:
    """Parse 'lid_driven_cavity__audit_real_run' → ('lid_driven_cavity', 'audit_real_run').

    Uses rpartition on '__' so the label is the LAST token; case_id keeps any
    internal underscores. Labels today are simple identifiers without '__';
    rpartition is resilient if that changes.

    Both case_id and run_label are validated against a strict identifier
    pattern to prevent path-traversal attacks (Codex round 1 HIGH #2).

    Raises HTTPException(400) on malformed input.
    """
    if "__" not in run_id:
        raise HTTPException(
            status_code=400,
            detail=f"run_id must match '{{case}}__{{label}}': got {run_id!r}",
        )
    case_id, _, run_label = run_id.rpartition("__")
    if not case_id or not run_label:
        raise HTTPException(
            status_code=400,
            detail=f"run_id has empty case_id or label: {run_id!r}",
        )
    _validate_segment(case_id, "case_id")
    _validate_segment(run_label, "run_label")
    return case_id, run_label

exec
/bin/zsh -lc "sed -n '260,620p' ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx" in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc 'rg -n "ScientificComparisonReportSection|comparison-report/context|sandbox=|Open in new window|Download PDF|return null|return None" ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx' in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
365:      <ScientificComparisonReportSection caseId={caseId} />
956:          if (s.value == null || !Number.isFinite(s.value)) return null;
1281:function ScientificComparisonReportSection({ caseId }: { caseId: string }) {
1289:        )}/comparison-report/context`,
1300:  if (isLoading) return null; // quiet during fetch
1301:  if (isError || !data) return null; // case not opted-in → silently hide
1394:          sandbox=""

 succeeded in 0ms:
          </p>
          <p className="mt-4 text-[15px] leading-relaxed text-surface-300">
            {learnCase.teaser_zh}
          </p>
        </div>
        <div className="flex items-center rounded-lg border border-surface-800 bg-gradient-to-br from-surface-900 to-surface-950 p-4">
          <CaseIllustration caseId={caseId} className="h-auto w-full text-surface-100" />
        </div>
      </header>

      {/* Tab nav */}
      <div className="sticky top-0 -mx-6 mb-8 border-b border-surface-800 bg-surface-950/80 px-6 py-2 backdrop-blur">
        <div className="flex gap-1">
          {TABS.map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={`rounded-sm px-3 py-1.5 text-[13px] transition-colors ${
                tab === t.id
                  ? "bg-surface-800 text-surface-100"
                  : "text-surface-400 hover:bg-surface-900 hover:text-surface-200"
              }`}
            >
              {t.label_zh}
              <span className="ml-1.5 text-[10px] uppercase tracking-wider text-surface-600">
                {t.label_en}
              </span>
            </button>
          ))}
        </div>
      </div>

      {/* Tab panels */}
      {tab === "story" && <StoryTab caseId={caseId} />}
      {tab === "compare" && (
        <CompareTab
          caseId={caseId}
          report={report}
          error={error}
          runs={runs ?? []}
          activeRunId={runId}
          onSelectRun={setRunId}
        />
      )}
      {tab === "mesh" && <MeshTab caseId={caseId} />}
      {tab === "run" && <RunTab caseId={caseId} />}
      {tab === "advanced" && <AdvancedTab caseId={caseId} report={report} />}
    </div>
  );
}

// --- Story tab ----------------------------------------------------------------

function StoryTab({ caseId }: { caseId: string }) {
  const learnCase = getLearnCase(caseId)!;
  const flowFields = getFlowFields(caseId);
  return (
    <div className="space-y-8">
      <section>
        <h2 className="card-title mb-3">这个问题是什么</h2>
        <ul className="space-y-2 text-[14px] leading-relaxed text-surface-200">
          {learnCase.physics_bullets_zh.map((b, i) => (
            <li key={i} className="flex gap-3">
              <span className="mt-2 h-1 w-1 shrink-0 rounded-full bg-sky-400" aria-hidden />
              <span>{b}</span>
            </li>
          ))}
        </ul>
      </section>

      {flowFields.length > 0 && (
        <section>
          <div className="mb-3 flex items-baseline justify-between">
            <h2 className="card-title">真实数据 · Data</h2>
            <p className="text-[11px] text-surface-500">
              每张图都直接来自文献精确解或公开实验表格
            </p>
          </div>
          <div className="space-y-4">
            {flowFields.map((ff) => (
              <figure
                key={ff.src}
                className="overflow-hidden rounded-md border border-surface-800 bg-surface-900/30"
              >
                <img
                  src={ff.src}
                  alt={ff.caption_zh}
                  className="w-full max-w-full"
                  loading="lazy"
                />
                <figcaption className="border-t border-surface-800 px-4 py-3">
                  <p className="text-[13px] text-surface-200">{ff.caption_zh}</p>
                  <p className="mono mt-1.5 text-[10px] leading-relaxed text-surface-500">
                    provenance: {ff.provenance}
                  </p>
                </figcaption>
              </figure>
            ))}
          </div>
        </section>
      )}

      {/* Phase 7f — live CFD-vs-Gold comparison report (if the case has a real
          audit_real_run artifact set from Phase 7a). Gracefully hidden for
          cases not yet opted-in. */}
      <ScientificComparisonReportSection caseId={caseId} />

      <section>
        <h2 className="card-title mb-3">为什么要做验证</h2>
        <p className="text-[14px] leading-relaxed text-surface-200">
          {learnCase.why_validation_matters_zh}
        </p>
      </section>

      <section>
        <h2 className="card-title mb-3 text-amber-300">常见陷阱</h2>
        <div className="rounded-md border border-amber-900/40 bg-amber-950/20 px-4 py-3">
          <p className="text-[14px] leading-relaxed text-amber-100/85">
            {learnCase.common_pitfall_zh}
          </p>
        </div>
      </section>

      <section>
        <h2 className="card-title mb-3">可观察量</h2>
        <div className="inline-flex items-center gap-2 rounded-md border border-surface-800 bg-surface-900/50 px-3 py-2">
          <span className="text-[11px] uppercase tracking-wider text-surface-500">
            canonical observable
          </span>
          <span className="mono text-[13px] text-surface-100">{learnCase.observable}</span>
        </div>
      </section>

      <section>
        <h2 className="card-title mb-3">参考文献</h2>
        <p className="mono text-[13px] text-surface-300">{learnCase.canonical_ref}</p>
      </section>
    </div>
  );
}

// --- Compare tab --------------------------------------------------------------

const RUN_CATEGORY_LABEL: Record<RunCategory, string> = {
  reference: "参考运行",
  real_incident: "真实故障",
  under_resolved: "欠分辨",
  wrong_model: "错模型",
  grid_convergence: "网格收敛",
};

const RUN_CATEGORY_COLOR: Record<RunCategory, string> = {
  reference: "bg-emerald-900/40 text-emerald-200 border-emerald-800/60",
  real_incident: "bg-amber-900/30 text-amber-200 border-amber-800/50",
  under_resolved: "bg-orange-900/30 text-orange-200 border-orange-800/50",
  wrong_model: "bg-rose-900/30 text-rose-200 border-rose-800/50",
  grid_convergence: "bg-sky-900/30 text-sky-200 border-sky-800/50",
};

function CompareTab({
  caseId,
  report,
  error,
  runs,
  activeRunId,
  onSelectRun,
}: {
  caseId: string;
  report: ValidationReport | undefined;
  error: ApiError | null;
  runs: RunDescriptor[];
  activeRunId: string | undefined;
  onSelectRun: (runId: string | null) => void;
}) {
  const learnCase = getLearnCase(caseId)!;

  if (error) {
    return (
      <ErrorCallout
        message={`后端没有为 ${caseId} 返回验证报告 (${error.status})`}
      />
    );
  }
  if (!report) {
    return <SkeletonCallout message="正在从后端取回验证报告…" />;
  }

  const { gold_standard, measurement, contract_status, deviation_pct, tolerance_lower, tolerance_upper } = report;

  // Which run is currently shown. If `activeRunId` is not set, the
  // backend resolved the default (first reference run, then fallback).
  // Highlight whichever run actually matches the loaded measurement.
  const resolvedRun = runs.find((r) => r.run_id === measurement?.run_id)
    ?? runs.find((r) => activeRunId ? r.run_id === activeRunId : r.category === "reference")
    ?? runs[0];

  return (
    <div className="space-y-6">
      {/* Run selector — only rendered when the case has curated runs */}
      {runs.length > 0 && (
        <section className="rounded-lg border border-surface-800 bg-surface-900/30 px-4 py-3">
          <div className="mb-2 flex items-baseline justify-between">
            <p className="text-[11px] uppercase tracking-[0.14em] text-surface-500">
              选择一条 run
            </p>
            <p className="text-[11px] text-surface-500">
              换一条运行 → 验证结果会不同 · 这就是"做对"和"数字碰巧对上"的区别
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            {runs.map((run) => {
              const isActive =
                (resolvedRun && resolvedRun.run_id === run.run_id) ||
                activeRunId === run.run_id;
              return (
                <button
                  key={run.run_id}
                  onClick={() => onSelectRun(run.run_id)}
                  className={`rounded-md border px-3 py-1.5 text-left text-[12px] transition-colors ${
                    isActive
                      ? "border-sky-500 bg-sky-950/40 text-surface-100"
                      : "border-surface-700 bg-surface-900/40 text-surface-300 hover:border-surface-600"
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <span
                      className={`inline-flex rounded-sm border px-1.5 py-0.5 text-[10px] uppercase tracking-wider ${RUN_CATEGORY_COLOR[run.category]}`}
                    >
                      {RUN_CATEGORY_LABEL[run.category]}
                    </span>
                    <span className="font-medium">{run.label_zh}</span>
                  </div>
                  <p className="mono mt-0.5 text-[10px] text-surface-500">
                    run_id={run.run_id} · 预期={run.expected_verdict}
                  </p>
                </button>
              );
            })}
          </div>
          {resolvedRun?.description_zh && (
            <p className="mt-3 text-[12px] leading-relaxed text-surface-400">
              {resolvedRun.description_zh}
            </p>
          )}
        </section>
      )}

      {/* Verdict line */}
      <section className="rounded-lg border border-surface-800 bg-surface-900/40 px-5 py-4">
        <div className="flex items-baseline justify-between">
          <p className="text-[11px] uppercase tracking-[0.14em] text-surface-500">结果</p>
          <span className={`mono text-[12px] ${STATUS_CLASS[contract_status]}`}>
            {contract_status}
          </span>
        </div>
        <p className={`mt-1 text-[18px] font-medium ${STATUS_CLASS[contract_status]}`}>
          {STATUS_TEXT[contract_status]}
        </p>
      </section>

      {/* Gold vs measured */}
      <section className="grid gap-4 md:grid-cols-2">
        <StatBlock
          label="黄金标准"
          subLabel={gold_standard.citation}
          value={gold_standard.ref_value}
          unit={gold_standard.unit}
          quantity={gold_standard.quantity}
        />
        <StatBlock
          label="你的测量"
          subLabel={measurement?.source ?? "—"}
          value={measurement?.value ?? null}
          unit={measurement?.unit ?? gold_standard.unit}
          quantity={gold_standard.quantity}
          accent
        />
      </section>

      {/* Tolerance band */}
      <section>
        <h3 className="card-title mb-2">容差带</h3>
        <ToleranceBand
          goldValue={gold_standard.ref_value}
          tolerancePct={gold_standard.tolerance_pct}
          lower={tolerance_lower}
          upper={tolerance_upper}
          measured={measurement?.value ?? null}
        />
        {deviation_pct !== null && (
          <p className="mt-3 text-[13px] text-surface-300">
            偏差 <span className={`mono ${STATUS_CLASS[contract_status]}`}>
              {deviation_pct > 0 ? "+" : ""}
              {deviation_pct.toFixed(2)}%
            </span>{" "}
            · 容差宽度 ±{(gold_standard.tolerance_pct * 100).toFixed(1)}%
          </p>
        )}
      </section>

      {/* Learning angle — reframe FAIL/HAZARD as a teaching moment */}
      <section className="rounded-md border border-sky-900/40 bg-sky-950/15 px-4 py-3">
        <p className="mb-1 text-[11px] uppercase tracking-[0.14em] text-sky-300">
          学习点 · Learning angle
        </p>
        <p className="text-[14px] leading-relaxed text-surface-200">
          {learnCase.why_validation_matters_zh}
        </p>
      </section>
    </div>
  );
}

function StatBlock({
  label,
  subLabel,
  value,
  unit,
  quantity,
  accent,
}: {
  label: string;
  subLabel: string;
  value: number | null;
  unit: string;
  quantity: string;
  accent?: boolean;
}) {
  return (
    <div
      className={`rounded-lg border px-5 py-4 ${
        accent ? "border-sky-800/60 bg-sky-950/20" : "border-surface-800 bg-surface-900/40"
      }`}
    >
      <p className="text-[11px] uppercase tracking-[0.14em] text-surface-500">{label}</p>
      <p className="mono mt-3 text-[28px] font-medium leading-none text-surface-100">
        {value === null ? "—" : value.toPrecision(4)}
      </p>
      <div className="mt-3 flex items-baseline justify-between text-[12px] text-surface-400">
        <span className="mono">{quantity}</span>
        <span>{unit || "—"}</span>
      </div>
      <p className="mt-2 text-[11px] leading-snug text-surface-500">{subLabel}</p>
    </div>
  );
}

function ToleranceBand({
  goldValue,
  lower,
  upper,
  measured,
}: {
  goldValue: number;
  tolerancePct: number;
  lower: number;
  upper: number;
  measured: number | null;
}) {
  // Compute a display range that includes gold, both tolerance bounds,
  // and measured — with sensible margin. Clamp width to avoid division

exec
/bin/zsh -lc "find ui/backend/tests/fixtures/runs/lid_driven_cavity -maxdepth 1 -type f -name 'mesh_*_measurement.yaml' -print | sort" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
ui/backend/tests/fixtures/runs/lid_driven_cavity/mesh_160_measurement.yaml
ui/backend/tests/fixtures/runs/lid_driven_cavity/mesh_20_measurement.yaml
ui/backend/tests/fixtures/runs/lid_driven_cavity/mesh_40_measurement.yaml
ui/backend/tests/fixtures/runs/lid_driven_cavity/mesh_80_measurement.yaml

exec
/bin/zsh -lc "ls -1 knowledge/gold_standards && echo '---' && sed -n '1,260p' knowledge/gold_standards/lid_driven_cavity.yaml" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
axisymmetric_impinging_jet.yaml
backward_facing_step.yaml
backward_facing_step_steady.yaml
circular_cylinder_wake.yaml
cylinder_crossflow.yaml
differential_heated_cavity.yaml
duct_flow.yaml
fully_developed_plane_channel_flow.yaml
impinging_jet.yaml
lid_driven_cavity.yaml
lid_driven_cavity_benchmark.yaml
naca0012_airfoil.yaml
plane_channel_flow.yaml
rayleigh_benard_convection.yaml
turbulent_flat_plate.yaml
---
# Gold Standard — Lid-Driven Cavity
# Based on Ghia, Ghia & Shin 1982, J. Comput. Phys. 47, 387-411 — Table I.
# Re = 100, square cavity, lid-driven top wall (u=1.0), all other walls no-slip (u=0).
# Steady-state, incompressible, structured grid.
#
# Q-5 Path A closure (2026-04-21, DEC-V61-030):
#   The prior u_centerline reference_values claimed Ghia 1982 authorship
#   but did NOT match the paper (old gold: u=+0.025 at y=0.5; Ghia actual:
#   -0.20581). Values were synthesized in Phase 0 (commit fc21f47d) without
#   cross-verifying the source. Phase 5a real-solver run first surfaced the
#   mismatch; Phase 5b confirmed simpleFoam produces genuine Ghia physics.
#   These values are now interpolated from Ghia 1982 Table I (Re=100 column)
#   to the harness's uniform 17-point y grid.
#
# Ghia 1982 Table I native (non-uniform) y points for Re=100:
#   0.0000  u=0.00000            | 0.5000  u=-0.20581 (matches target)
#   0.0547  u=-0.03717           | 0.6172  u=-0.13641
#   0.0625  u=-0.04192 (matches) | 0.7344  u=+0.00332 (u crosses zero)
#   0.0703  u=-0.04775           | 0.8516  u=+0.23151
#   0.1016  u=-0.06434           | 0.9531  u=+0.68717
#   0.1719  u=-0.10150           | 0.9609  u=+0.73722
#   0.2813  u=-0.15662           | 0.9688  u=+0.78871
#   0.4531  u=-0.21090 (min)     | 0.9766  u=+0.84123
#                                | 1.0000  u=+1.00000 (lid BC)
#
# v_centerline and primary_vortex_location blocks below are NOT corrected in
# this commit (Q-5 scope is u_centerline only). Both sections have suspected
# schema/value issues (v_centerline appears to be Ghia Table II indexed by x
# but labelled "y"; primary_vortex_location has vortex_center_y=0.7650 which
# disagrees with Ghia's Re=100 primary vortex at (0.6172, 0.7344)). These are
# not currently exercised by the audit-run comparator; flagged as follow-up
# work in Phase 5c (NON-LDC) or a dedicated audit pass.

quantity: u_centerline
reference_values:
  - y: 0.0000
    u: 0.00000
  - y: 0.0625
    u: -0.04192
  - y: 0.1250
    u: -0.07671
  - y: 0.1875
    u: -0.10936
  - y: 0.2500
    u: -0.14085
  - y: 0.3125
    u: -0.16648
  - y: 0.3750
    u: -0.18622
  - y: 0.4375
    u: -0.20597
  - y: 0.5000
    u: -0.20581
  - y: 0.5625
    u: -0.16880
  - y: 0.6250
    u: -0.12711
  - y: 0.6875
    u: -0.05260
  - y: 0.7500
    u: 0.03369
  - y: 0.8125
    u: 0.15538
  - y: 0.8750
    u: 0.33656
  - y: 0.9375
    u: 0.61714
  - y: 1.0000
    u: 1.00000
tolerance: 0.05
source: "Ghia, Ghia & Shin 1982, J. Comput. Phys. 47, 387-411 — Table I Re=100 column, linearly interpolated to uniform 17-point y grid"
literature_doi: "10.1016/0021-9991(82)90058-4"
mesh_info:
  cells: 16641  # 129×129 (Ghia mesh) — updated from Phase 0 placeholder 64800
  type: structured
solver_info:
  name: simpleFoam  # Phase 5b migration from icoFoam (transient PISO) to simpleFoam (steady SIMPLE)
  schemes: SIMPLE
case_info:
  id: lid_driven_cavity
  Re: 100
  flow_type: INTERNAL
  geometry_type: SIMPLE_GRID
  steady_state: STEADY
  boundary_conditions:
    top_wall_u: 1.0
    other_walls_u: 0.0

---
quantity: v_centerline
reference_values:
  - y: 0.1250
    v: -0.04939
  - y: 0.1875
    v: -0.06203
  - y: 0.2500
    v: -0.06904
  - y: 0.3125
    v: -0.07080
  - y: 0.3750
    v: -0.06629
  - y: 0.4375
    v: -0.05259
  - y: 0.5000
    v: 0.05454
  - y: 0.5625
    v: 0.06406
  - y: 0.6250
    v: 0.06920
  - y: 0.6875
    v: 0.06878
  - y: 0.7500
    v: 0.06021
  - y: 0.8125
    v: 0.04404
  - y: 0.8750
    v: 0.02429
tolerance: 0.05
source: "Ghia et al. 1982, J. Comput. Phys."
literature_doi: "10.1016/0021-9991(82)90058-4"
mesh_info:
  cells: 64800
  type: structured
solver_info:
  name: icoFoam
  schemes: PISO
case_info:
  id: lid_driven_cavity
  Re: 100
  flow_type: INTERNAL
  geometry_type: SIMPLE_GRID
  steady_state: STEADY
  boundary_conditions:
    top_wall_u: 1.0
    other_walls_u: 0.0

---
quantity: primary_vortex_location
reference_values:
  - name: vortex_center_x
    value: 0.5000
    unit: normalized
  - name: vortex_center_y
    value: 0.7650
    unit: normalized
  - name: u_min
    value: -0.03717
    unit: normalized
    location_y: 0.0625
tolerance: 0.05
source: "Ghia et al. 1982, J. Comput. Phys."
literature_doi: "10.1016/0021-9991(82)90058-4"
mesh_info:
  cells: 64800
  type: structured
solver_info:
  name: icoFoam
  schemes: PISO
case_info:
  id: lid_driven_cavity
  Re: 100
  flow_type: INTERNAL
  geometry_type: SIMPLE_GRID
  steady_state: STEADY

exec
/bin/zsh -lc 'for f in ui/backend/tests/fixtures/runs/lid_driven_cavity/mesh_*_measurement.yaml; do echo "FILE:$f"; sed -n '"'1,120p' \""'$f"; done' in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
FILE:ui/backend/tests/fixtures/runs/lid_driven_cavity/mesh_160_measurement.yaml
# Grid-convergence run for LDC — 160² uniform grid.
# Asymptotic convergence: u_centerline -0.0375 (+0.9%). Adding cells
# past 80² gives diminishing returns — Richardson-extrapolation would
# confirm h² convergence for the central-differencing scheme.
run_metadata:
  run_id: mesh_160
  label_zh: 网格 160² · 过收敛
  label_en: Mesh 160² (asymptotic)
  description_zh: >-
    160×160 网格。几乎等同 Ghia 129×129 原始 mesh；u_centerline≈-0.042（|dev|=0.2% vs Ghia -0.04192）。5% 容差内 PASS。
  category: grid_convergence
  expected_verdict: PASS
case_id: lid_driven_cavity
source: grid_convergence_study_synthetic
measurement:
  value: -0.042
  unit: dimensionless
  run_id: grid_ldc_n160
  commit_sha: null
  measured_at: null
  quantity: u_centerline[y=0.0625]
audit_concerns: []
decisions_trail: []
FILE:ui/backend/tests/fixtures/runs/lid_driven_cavity/mesh_20_measurement.yaml
# Grid-convergence run for LDC — 20² uniform grid.
# At this resolution, secondary vortex + corner singularities are
# under-resolved; u_centerline at y=0.0625 over-predicts magnitude
# by ~29% vs Ghia 1982 Re=100 tabulated value -0.03717.
run_metadata:
  run_id: mesh_20
  label_zh: 网格 20² · 粗糙
  label_en: Mesh 20² (coarse)
  description_zh: >-
    20×20 均匀网格。Re=100 下 secondary vortex 完全糊掉，u_centerline 被高估到 -0.055（|dev|=31% vs Ghia 1982 的 -0.04192）。5% 容差外 FAIL。
  category: grid_convergence
  expected_verdict: FAIL
case_id: lid_driven_cavity
source: grid_convergence_study_synthetic
measurement:
  value: -0.055
  unit: dimensionless
  run_id: grid_ldc_n20
  commit_sha: null
  measured_at: null
  quantity: u_centerline[y=0.0625]
audit_concerns:
  - concern_type: DEVIATION
    summary: 'Uniform grid; u_centerline=-0.055 vs Ghia -0.04192 (|dev|=31.2%).'
    detail: null
    decision_refs: []
decisions_trail: []
FILE:ui/backend/tests/fixtures/runs/lid_driven_cavity/mesh_40_measurement.yaml
# Grid-convergence run for LDC — 40² uniform grid.
# Secondary vortex barely captured; u_centerline -0.042 (+13% deviation).
# Still outside 5% tolerance.
run_metadata:
  run_id: mesh_40
  label_zh: 网格 40² · 过渡
  label_en: Mesh 40² (transitional)
  description_zh: >-
    40×40 网格。一次精度格式下数值扩散仍主导；u_centerline≈-0.048（|dev|=14.5%）。5% 容差外 FAIL。
  category: grid_convergence
  expected_verdict: FAIL
case_id: lid_driven_cavity
source: grid_convergence_study_synthetic
measurement:
  value: -0.048
  unit: dimensionless
  run_id: grid_ldc_n40
  commit_sha: null
  measured_at: null
  quantity: u_centerline[y=0.0625]
audit_concerns:
  - concern_type: DEVIATION
    summary: '40² grid; u_centerline=-0.042 vs Ghia -0.03717 (+13%).'
    detail: null
    decision_refs: []
decisions_trail: []
FILE:ui/backend/tests/fixtures/runs/lid_driven_cavity/mesh_80_measurement.yaml
# Grid-convergence run for LDC — 80² uniform grid.
# Secondary vortex cleanly resolved; u_centerline -0.038 (+2.2%).
# Inside 5% tolerance → PASS. This is the "sweet spot" where adding
# more cells no longer changes the answer meaningfully.
run_metadata:
  run_id: mesh_80
  label_zh: 网格 80² · 收敛
  label_en: Mesh 80² (converged)
  description_zh: >-
    80×80 网格。二次精度 + 数值收敛接近 Ghia 范围；u_centerline≈-0.044（|dev|=5%），刚好踩在 5% 容差边界。
  category: grid_convergence
  expected_verdict: FAIL
case_id: lid_driven_cavity
source: grid_convergence_study_synthetic
measurement:
  value: -0.044
  unit: dimensionless
  run_id: grid_ldc_n80
  commit_sha: null
  measured_at: null
  quantity: u_centerline[y=0.0625]
audit_concerns: []
decisions_trail: []

exec
/bin/zsh -lc "sed -n '1260,1425p' ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
  };
  paper: {
    title: string;
    source: string;
    doi?: string;
    short: string;
    gold_count: number;
    tolerance_pct: number;
  };
  renders: {
    profile_png_rel: string;
    pointwise_png_rel: string;
    contour_png_rel: string;
    residuals_png_rel: string;
  };
  meta: {
    commit_sha: string;
    report_generated_at: string;
  };
};

function ScientificComparisonReportSection({ caseId }: { caseId: string }) {
  const runLabel = "audit_real_run";
  const { data, isLoading, isError } = useQuery<ComparisonReportContext>({
    queryKey: ["comparison-report-ctx", caseId, runLabel],
    queryFn: async () => {
      const resp = await fetch(
        `/api/cases/${encodeURIComponent(caseId)}/runs/${encodeURIComponent(
          runLabel,
        )}/comparison-report/context`,
        { credentials: "same-origin" },
      );
      if (!resp.ok) throw new ApiError(resp.status, await resp.text());
      return (await resp.json()) as ComparisonReportContext;
    },
    retry: false,
    // 404 is expected for cases not yet Phase 7a opted-in; hide silently.
    staleTime: 60_000,
  });

  if (isLoading) return null; // quiet during fetch
  if (isError || !data) return null; // case not opted-in → silently hide

  const verdictColor =
    data.verdict === "PASS"
      ? "bg-contract-pass/15 border-contract-pass/40 text-contract-pass"
      : data.verdict === "PARTIAL"
      ? "bg-yellow-500/10 border-yellow-500/40 text-yellow-300"
      : "bg-contract-fail/15 border-contract-fail/40 text-contract-fail";

  const reportHtmlUrl = `/api/cases/${encodeURIComponent(caseId)}/runs/${encodeURIComponent(
    runLabel,
  )}/comparison-report`;
  const reportPdfUrl = `/api/cases/${encodeURIComponent(caseId)}/runs/${encodeURIComponent(
    runLabel,
  )}/comparison-report.pdf`;

  return (
    <section>
      <div className="mb-3 flex items-baseline justify-between">
        <h2 className="card-title">科研级 CFD vs Gold 验证报告</h2>
        <p className="text-[11px] text-surface-500">
          实际 OpenFOAM 真跑 · 8 sections · {data.meta.commit_sha}
        </p>
      </div>

      <div
        className={`mb-4 rounded-md border p-4 ${verdictColor}`}
        role="status"
      >
        <div className="flex items-center justify-between gap-4">
          <div>
            <div className="text-[11px] font-semibold uppercase tracking-wider opacity-85">
              Verdict
            </div>
            <div className="mt-1 text-[22px] font-bold leading-tight">
              {data.verdict}
            </div>
            <div className="mt-1 text-[12px] text-surface-200">
              {data.verdict_subtitle}
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3 text-right text-[12px]">
            <div>
              <div className="text-surface-400">max |dev|</div>
              <div className="mono text-surface-100">
                {data.metrics.max_dev_pct.toFixed(2)}%
              </div>
            </div>
            <div>
              <div className="text-surface-400">n_pass</div>
              <div className="mono text-surface-100">
                {data.metrics.n_pass} / {data.metrics.n_total}
              </div>
            </div>
            <div>
              <div className="text-surface-400">L²</div>
              <div className="mono text-surface-100">
                {data.metrics.l2.toFixed(4)}
              </div>
            </div>
            <div>
              <div className="text-surface-400">L∞</div>
              <div className="mono text-surface-100">
                {data.metrics.linf.toFixed(4)}
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="mb-3 flex flex-wrap gap-2 text-[12px]">
        <a
          href={reportHtmlUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="rounded border border-surface-700 bg-surface-800/60 px-3 py-1.5 text-surface-200 hover:bg-surface-700/60"
        >
          ↗ 新窗口打开完整报告
        </a>
        <a
          href={reportPdfUrl}
          download
          className="rounded border border-surface-700 bg-surface-800/60 px-3 py-1.5 text-surface-200 hover:bg-surface-700/60"
        >
          ↓ 下载 PDF
        </a>
      </div>

      <div className="overflow-hidden rounded-md border border-surface-800 bg-white">
        <iframe
          title="CFD vs Gold comparison report"
          src={reportHtmlUrl}
          className="h-[1400px] w-full border-0"
          sandbox=""
        />
      </div>
    </section>
  );
}

exec
/bin/zsh -lc "rg -n \"comparison_report|include_router\" ui/backend/main.py && sed -n '1,220p' ui/backend/main.py" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
51:    comparison_report,
82:app.include_router(health.router,       prefix="/api", tags=["health"])
83:app.include_router(cases.router,        prefix="/api", tags=["cases"])
84:app.include_router(case_editor.router,  prefix="/api", tags=["case-editor"])
85:app.include_router(validation.router,   prefix="/api", tags=["validation"])
86:app.include_router(decisions.router,    prefix="/api", tags=["decisions"])
87:app.include_router(run_monitor.router,  prefix="/api", tags=["runs"])
88:app.include_router(dashboard.router,    prefix="/api", tags=["dashboard"])
89:app.include_router(audit_package.router, prefix="/api", tags=["audit-package"])
90:app.include_router(case_export.router,  prefix="/api", tags=["case-export"])
91:app.include_router(field_artifacts.router, prefix="/api", tags=["field-artifacts"])
92:app.include_router(comparison_report.router, prefix="/api", tags=["comparison-report"])
"""FastAPI application entrypoint for the CFD Harness UI.

Run locally:
    uv pip install -e ".[ui]"
    uvicorn ui.backend.main:app --reload --host 127.0.0.1 --port 8000

Routes (Phase 0..4 — Path B MVP, per DEC-V61-002 + DEC-V61-003):

    Phase 0 — baseline read surfaces
        GET    /api/health                         → liveness probe
        GET    /api/cases                          → whitelist.yaml case index
        GET    /api/cases/{id}                     → single case definition
        GET    /api/validation-report/{id}         → Screen 4 payload

    Phase 1 — Case Editor
        GET    /api/cases/{id}/yaml                → source YAML + origin
        PUT    /api/cases/{id}/yaml                → save draft + lint
        POST   /api/cases/{id}/yaml/lint           → lint without saving
        DELETE /api/cases/{id}/yaml                → revert (delete draft)

    Phase 2 — Decisions Queue
        GET    /api/decisions                      → Kanban snapshot + gate queue

    Phase 3 — Run Monitor
        GET    /api/runs/{id}/stream               → SSE residual stream
        GET    /api/runs/{id}/checkpoints          → checkpoint snapshot

    Phase 4 — Dashboard
        GET    /api/dashboard                      → Screen 1 aggregate

    Phase 5 — Audit Package Builder (Screen 6)
        POST   /api/cases/{id}/runs/{rid}/audit-package/build
                                                    → build + sign a bundle
        GET    /api/audit-packages/{bundle_id}/manifest.json
        GET    /api/audit-packages/{bundle_id}/bundle.zip
        GET    /api/audit-packages/{bundle_id}/bundle.html
        GET    /api/audit-packages/{bundle_id}/bundle.pdf
        GET    /api/audit-packages/{bundle_id}/bundle.sig
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ui.backend.routes import (
    audit_package,
    case_editor,
    case_export,
    cases,
    comparison_report,
    dashboard,
    decisions,
    field_artifacts,
    health,
    run_monitor,
    validation,
)

app = FastAPI(
    title="CFD Harness UI Backend",
    version="0.5.0-phase-5",
    description=(
        "Path-B UI MVP — Agentic V&V-first workbench. "
        "Phase 0..5 surfaces: Validation Report, Case Editor, Decisions "
        "Queue, Run Monitor, Dashboard, Audit Package Builder. "
        "See docs/product_thesis.md + .planning/phase5_audit_package_builder_kickoff.md."
    ),
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

# CORS: local dev (Vite @ 5173) allowed; tightened / origin-bound in Phase 5.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(health.router,       prefix="/api", tags=["health"])
app.include_router(cases.router,        prefix="/api", tags=["cases"])
app.include_router(case_editor.router,  prefix="/api", tags=["case-editor"])
app.include_router(validation.router,   prefix="/api", tags=["validation"])
app.include_router(decisions.router,    prefix="/api", tags=["decisions"])
app.include_router(run_monitor.router,  prefix="/api", tags=["runs"])
app.include_router(dashboard.router,    prefix="/api", tags=["dashboard"])
app.include_router(audit_package.router, prefix="/api", tags=["audit-package"])
app.include_router(case_export.router,  prefix="/api", tags=["case-export"])
app.include_router(field_artifacts.router, prefix="/api", tags=["field-artifacts"])
app.include_router(comparison_report.router, prefix="/api", tags=["comparison-report"])

codex
I’ve narrowed the likely findings to two classes: manifest-derived filesystem trust in the backend/PDF path, and observability/testing gaps in the frontend+route layer. I’m pulling line-numbered snippets and the live manifest shape now so the final verdict is anchored to exact lines.
exec
/bin/zsh -lc "nl -ba ui/backend/tests/test_comparison_report_route.py | sed -n '1,220p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc "nl -ba ui/backend/templates/comparison_report.html.j2 | sed -n '1,240p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc "if [ -f reports/phase5_fields/lid_driven_cavity/runs/audit_real_run.json ]; then echo 'RUN_MANIFEST'; cat reports/phase5_fields/lid_driven_cavity/runs/audit_real_run.json; fi; if [ -f reports/phase5_renders/lid_driven_cavity/runs/audit_real_run.json ]; then echo 'RENDERS_MANIFEST'; cat reports/phase5_renders/lid_driven_cavity/runs/audit_real_run.json; fi" in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc "nl -ba ui/backend/services/comparison_report.py | sed -n '1,260p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
     1	"""Phase 7c — comparison report route tests.
     2	
     3	Guards route-level behavior: 200 on valid case/run, 404 on missing, 400 on
     4	traversal attempts. Actual HTML content is covered by unit tests of the
     5	service module.
     6	"""
     7	from __future__ import annotations
     8	
     9	from fastapi.testclient import TestClient
    10	
    11	from ui.backend.main import app
    12	
    13	client = TestClient(app)
    14	
    15	# These tests run against the real reports/phase5_fields/lid_driven_cavity/
    16	# artifact set which is .gitignored. In CI (no artifacts), they should 404 —
    17	# which is fine, they'll be re-collected on developer machines.
    18	
    19	
    20	def _has_ldc_artifacts() -> bool:
    21	    from pathlib import Path
    22	    manifest = Path("reports/phase5_fields/lid_driven_cavity/runs/audit_real_run.json")
    23	    return manifest.is_file()
    24	
    25	
    26	def test_html_200_when_artifacts_present() -> None:
    27	    if not _has_ldc_artifacts():
    28	        return  # skip silently on CI-style clean checkout
    29	    r = client.get("/api/cases/lid_driven_cavity/runs/audit_real_run/comparison-report")
    30	    assert r.status_code == 200, r.text
    31	    body = r.text
    32	    # 8 section markers from the Jinja template.
    33	    for marker in [
    34	        "参考文献",           # §2
    35	        "中心线 profile",      # §3
    36	        "逐点偏差分布",        # §4
    37	        "流场 contour",        # §5
    38	        "残差收敛历史",        # §6
    39	        "网格收敛",            # §7
    40	        "求解器元数据",        # §8
    41	    ]:
    42	        assert marker in body, f"missing section marker: {marker}"
    43	    # Verdict card must be present.
    44	    assert "verdict-card" in body
    45	
    46	
    47	def test_context_200_when_artifacts_present() -> None:
    48	    if not _has_ldc_artifacts():
    49	        return
    50	    r = client.get(
    51	        "/api/cases/lid_driven_cavity/runs/audit_real_run/comparison-report/context",
    52	    )
    53	    assert r.status_code == 200, r.text
    54	    d = r.json()
    55	    assert d["case_id"] == "lid_driven_cavity"
    56	    assert d["run_label"] == "audit_real_run"
    57	    assert "metrics" in d
    58	    assert d["metrics"]["n_total"] > 0
    59	    assert d["verdict"] in ("PASS", "PARTIAL", "FAIL")
    60	
    61	
    62	def test_html_404_unknown_case() -> None:
    63	    r = client.get("/api/cases/nonexistent_case/runs/audit_real_run/comparison-report")
    64	    assert r.status_code == 404
    65	
    66	
    67	def test_html_400_traversal_case_id() -> None:
    68	    r = client.get("/api/cases/..__pwn/runs/audit_real_run/comparison-report")
    69	    assert r.status_code == 400
    70	
    71	
    72	def test_html_400_traversal_run_label() -> None:
    73	    r = client.get("/api/cases/lid_driven_cavity/runs/..__pwn/comparison-report")
    74	    assert r.status_code == 400
    75	
    76	
    77	def test_context_400_urlencoded_traversal() -> None:
    78	    r = client.get(
    79	        "/api/cases/%2e%2e__pwn/runs/audit_real_run/comparison-report/context",
    80	    )
    81	    assert r.status_code == 400

 succeeded in 0ms:
RUN_MANIFEST
{
  "run_label": "audit_real_run",
  "timestamp": "20260421T082340Z",
  "case_id": "lid_driven_cavity",
  "artifact_dir_rel": "reports/phase5_fields/lid_driven_cavity/20260421T082340Z"
}
RENDERS_MANIFEST
{
  "case_id": "lid_driven_cavity",
  "run_label": "audit_real_run",
  "timestamp": "20260421T082340Z",
  "renders_dir_rel": "reports/phase5_renders/lid_driven_cavity/20260421T082340Z",
  "outputs": {
    "profile_png": "reports/phase5_renders/lid_driven_cavity/20260421T082340Z/profile_u_centerline.png",
    "profile_plotly_json": "reports/phase5_renders/lid_driven_cavity/20260421T082340Z/profile_u_centerline.plotly.json",
    "residuals_png": "reports/phase5_renders/lid_driven_cavity/20260421T082340Z/residuals.png",
    "pointwise_deviation_png": "reports/phase5_renders/lid_driven_cavity/20260421T082340Z/pointwise_deviation.png",
    "contour_u_magnitude_png": "reports/phase5_renders/lid_driven_cavity/20260421T082340Z/contour_u_magnitude.png"
  },
  "errors": {}
}

 succeeded in 0ms:
     1	<!DOCTYPE html>
     2	<html lang="zh-CN">
     3	<head>
     4	<meta charset="utf-8">
     5	<title>CFD vs Gold — {{ case_id }}</title>
     6	<style>
     7	  body { font-family: -apple-system, 'Segoe UI', 'Helvetica Neue', sans-serif;
     8	         color: #1f2937; max-width: 960px; margin: 2em auto; padding: 0 1.5em;
     9	         line-height: 1.55; }
    10	  h1 { color: #111; border-bottom: 3px solid #1f77b4; padding-bottom: 0.3em; }
    11	  h2 { color: #1f77b4; margin-top: 2em; font-size: 1.3em; }
    12	  .verdict-card { background: linear-gradient(135deg, {{ verdict_gradient }});
    13	                  color: white; padding: 1em 1.5em; border-radius: 10px; margin: 1em 0 2em 0;
    14	                  box-shadow: 0 2px 12px rgba(0,0,0,0.08); }
    15	  .verdict-card .verdict { font-size: 2em; font-weight: bold; letter-spacing: 1px; }
    16	  .verdict-card .sub { font-size: 0.95em; opacity: 0.92; margin-top: 0.3em; }
    17	  .metrics { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1em; margin-top: 1em; }
    18	  .metric { background: rgba(255,255,255,0.15); padding: 0.6em 0.8em; border-radius: 6px; }
    19	  .metric-label { font-size: 0.75em; opacity: 0.85; text-transform: uppercase; }
    20	  .metric-value { font-size: 1.3em; font-weight: bold; margin-top: 0.2em; }
    21	  .paper-cite { background: #f9fafb; border-left: 4px solid #374151;
    22	                padding: 0.8em 1em; margin: 1em 0; font-size: 0.92em; }
    23	  .paper-cite .title { font-weight: 600; color: #111; }
    24	  .paper-cite .doi { font-family: 'SF Mono', Consolas, monospace; font-size: 0.85em; color: #6b7280; }
    25	  figure { margin: 1.5em 0; text-align: center; }
    26	  figure img { max-width: 100%; border: 1px solid #e5e7eb; border-radius: 4px; }
    27	  figcaption { font-size: 0.88em; color: #6b7280; margin-top: 0.5em; font-style: italic; }
    28	  table { border-collapse: collapse; width: 100%; margin: 1em 0; font-size: 0.92em; }
    29	  th, td { padding: 0.5em 0.8em; text-align: left; border-bottom: 1px solid #e5e7eb; }
    30	  th { background: #f9fafb; font-weight: 600; color: #374151; }
    31	  td.num { text-align: right; font-variant-numeric: tabular-nums; }
    32	  td.pass { color: #059669; font-weight: bold; }
    33	  td.fail { color: #dc2626; font-weight: bold; }
    34	  td.warn { color: #d97706; font-weight: bold; }
    35	  .mono { font-family: 'SF Mono', Consolas, monospace; font-size: 0.88em;
    36	          background: #f3f4f6; padding: 0.1em 0.4em; border-radius: 3px; }
    37	  .residual-block { background: #fff7ed; border-left: 4px solid #f97316;
    38	                    padding: 0.8em 1em; margin: 1em 0; font-size: 0.9em; }
    39	  footer { margin-top: 3em; padding-top: 1em; border-top: 1px solid #e5e7eb;
    40	           font-size: 0.82em; color: #9ca3af; }
    41	</style>
    42	</head>
    43	<body>
    44	
    45	<h1>CFD vs Gold — {{ case_display_name }}</h1>
    46	<p style="color:#6b7280; margin-top:-0.5em;">
    47	  Case ID: <span class="mono">{{ case_id }}</span> ·
    48	  Run: <span class="mono">{{ run_label }}</span> ·
    49	  Timestamp: <span class="mono">{{ timestamp }}</span>
    50	</p>
    51	
    52	<!-- Section 1 — Verdict card -->
    53	<div class="verdict-card">
    54	  <div class="verdict">{{ verdict }}</div>
    55	  <div class="sub">{{ verdict_subtitle }}</div>
    56	  <div class="metrics">
    57	    <div class="metric"><div class="metric-label">max |dev|</div>
    58	         <div class="metric-value">{{ '%.2f'|format(metrics.max_dev_pct) }}%</div></div>
    59	    <div class="metric"><div class="metric-label">L² norm</div>
    60	         <div class="metric-value">{{ '%.4f'|format(metrics.l2) }}</div></div>
    61	    <div class="metric"><div class="metric-label">L∞ norm</div>
    62	         <div class="metric-value">{{ '%.4f'|format(metrics.linf) }}</div></div>
    63	    <div class="metric"><div class="metric-label">RMS</div>
    64	         <div class="metric-value">{{ '%.4f'|format(metrics.rms) }}</div></div>
    65	  </div>
    66	</div>
    67	
    68	<!-- Section 2 — Paper citation -->
    69	<h2>2. 参考文献 (Gold standard)</h2>
    70	<div class="paper-cite">
    71	  <div class="title">{{ paper.title }}</div>
    72	  <div>{{ paper.source }}</div>
    73	  {% if paper.doi %}<div class="doi">DOI: {{ paper.doi }}</div>{% endif %}
    74	  <div style="margin-top:0.6em; font-size:0.88em;">
    75	    Gold sample count: <strong>{{ paper.gold_count }}</strong> points ·
    76	    Tolerance: <strong>±{{ '%.1f'|format(paper.tolerance_pct) }}%</strong>
    77	  </div>
    78	</div>
    79	
    80	<!-- Section 3 — Profile overlay -->
    81	<h2>3. 中心线 profile 叠合对比</h2>
    82	<figure>
    83	  <img src="{{ renders.profile_png_rel }}" alt="U centerline profile overlay">
    84	  <figcaption>simpleFoam 实线 vs {{ paper.short }} 离散点，x=0.5 垂直中心线。</figcaption>
    85	</figure>
    86	
    87	<!-- Section 4 — Pointwise deviation heatmap -->
    88	<h2>4. 逐点偏差分布 (5% 容差)</h2>
    89	<figure>
    90	  <img src="{{ renders.pointwise_png_rel }}" alt="Pointwise deviation bar chart">
    91	  <figcaption>
    92	    沿 y/L 的逐 gold 点 |dev|%，绿色 &lt; 5% PASS，黄色 5-10% WARN，红色 &gt; 10% FAIL。
    93	    {{ metrics.n_pass }}/{{ metrics.n_total }} 点通过 5% 容差。
    94	  </figcaption>
    95	</figure>
    96	
    97	<!-- Section 5 — Full 2D field contour -->
    98	<h2>5. 流场 contour (中心线切片)</h2>
    99	<figure>
   100	  <img src="{{ renders.contour_png_rel }}" alt="U magnitude contour slice">
   101	  <figcaption>
   102	    {{ contour_caption }}
   103	  </figcaption>
   104	</figure>
   105	
   106	<!-- Section 6 — Residual convergence -->
   107	<h2>6. 残差收敛历史</h2>
   108	<figure>
   109	  <img src="{{ renders.residuals_png_rel }}" alt="Residual log convergence">
   110	  <figcaption>
   111	    SIMPLE 迭代下 U_x / U_y / p 初始残差对数。收敛到
   112	    {{ '%.1e'|format(residual_info.final_ux) if residual_info.final_ux else 'N/A' }}
   113	    （Ux 终值）经 {{ residual_info.total_iter }} 次迭代。
   114	  </figcaption>
   115	</figure>
   116	
   117	{% if residual_info.note %}
   118	<div class="residual-block">{{ residual_info.note }}</div>
   119	{% endif %}
   120	
   121	<!-- Section 7 — Grid convergence -->
   122	<h2>7. 网格收敛 (mesh_20 → mesh_160)</h2>
   123	{% if grid_conv %}
   124	<table>
   125	  <thead>
   126	    <tr><th>Mesh</th><th>u(y=0.0625)</th><th>|dev|% vs gold</th><th>verdict</th></tr>
   127	  </thead>
   128	  <tbody>
   129	    {% for row in grid_conv %}
   130	    <tr>
   131	      <td class="mono">{{ row.mesh }}</td>
   132	      <td class="num">{{ '%.4f'|format(row.value) }}</td>
   133	      <td class="num">{{ '%.2f'|format(row.dev_pct) }}%</td>
   134	      <td class="{{ row.verdict_class }}">{{ row.verdict }}</td>
   135	    </tr>
   136	    {% endfor %}
   137	  </tbody>
   138	</table>
   139	<p style="color:#6b7280; font-size:0.88em; margin-top:0.5em;">
   140	  单调收敛: {{ grid_conv_note }} · Richardson p_obs (观察阶数) 延后到 Phase 7d。
   141	</p>
   142	{% else %}
   143	<p style="color:#9ca3af; font-style:italic;">网格收敛数据暂未加载。</p>
   144	{% endif %}
   145	
   146	<!-- Section 8 — Solver metadata -->
   147	<h2>8. 求解器元数据</h2>
   148	<table>
   149	  <tbody>
   150	    <tr><th>OpenFOAM</th><td class="mono">{{ meta.openfoam_version }}</td></tr>
   151	    <tr><th>Solver</th><td class="mono">{{ meta.solver }}</td></tr>
   152	    <tr><th>Docker image</th><td class="mono">{{ meta.docker_image }}</td></tr>
   153	    <tr><th>Commit SHA</th><td class="mono">{{ meta.commit_sha }}</td></tr>
   154	    <tr><th>Mesh</th><td class="mono">{{ meta.mesh }}</td></tr>
   155	    <tr><th>Tolerance</th><td class="mono">{{ meta.tolerance }}</td></tr>
   156	    <tr><th>Schemes</th><td class="mono">{{ meta.schemes }}</td></tr>
   157	    <tr><th>Report generated</th><td class="mono">{{ meta.report_generated_at }}</td></tr>
   158	  </tbody>
   159	</table>
   160	
   161	<footer>
   162	  Report generated by Phase 7c comparison_report pipeline (DEC-V61-032, {{ meta.report_generated_at[:10] }}).
   163	  CFD harness unified · cfd-harness-unified @ <span class="mono">{{ meta.commit_sha }}</span>
   164	</footer>
   165	
   166	</body>
   167	</html>

 succeeded in 0ms:
     1	"""Phase 7c — CFD vs Gold comparison report service.
     2	
     3	Renders an 8-section HTML report for a given (case_id, run_label), using:
     4	- Phase 7a field artifacts at reports/phase5_fields/{case}/{ts}/
     5	- Phase 7b rendered figures at reports/phase5_renders/{case}/{ts}/
     6	- knowledge/gold_standards/{case}.yaml gold reference
     7	- ui/backend/tests/fixtures/runs/{case}/mesh_{20,40,80,160}_measurement.yaml for grid convergence
     8	
     9	Backend route: ui/backend/routes/comparison_report.py calls `render_report_html`
    10	and `render_report_pdf` from this module. No DOM / no JS — static HTML + PNG
    11	inlined assets referenced by file:// for WeasyPrint PDF, served via FileResponse
    12	or embedded iframe on frontend.
    13	
    14	Design: report_html is a self-contained string (no asset URLs pointing to
    15	/api/... — uses file:// for PDF rendering and relative paths for HTML serving).
    16	"""
    17	from __future__ import annotations
    18	
    19	import datetime
    20	import json
    21	import math
    22	import subprocess
    23	from pathlib import Path
    24	from typing import Any, Optional
    25	
    26	import numpy as np
    27	import yaml
    28	from jinja2 import Environment, FileSystemLoader, select_autoescape
    29	
    30	_MODULE_DIR = Path(__file__).resolve().parent
    31	_REPO_ROOT = _MODULE_DIR.parents[2]
    32	_TEMPLATES = _MODULE_DIR.parent / "templates"
    33	_FIELDS_ROOT = _REPO_ROOT / "reports" / "phase5_fields"
    34	_RENDERS_ROOT = _REPO_ROOT / "reports" / "phase5_renders"
    35	_GOLD_ROOT = _REPO_ROOT / "knowledge" / "gold_standards"
    36	_FIXTURE_ROOT = _REPO_ROOT / "ui" / "backend" / "tests" / "fixtures" / "runs"
    37	
    38	_REPORT_SUPPORTED_CASES = frozenset({"lid_driven_cavity"})
    39	
    40	_env = Environment(
    41	    loader=FileSystemLoader(str(_TEMPLATES)),
    42	    autoescape=select_autoescape(["html", "htm"]),
    43	)
    44	
    45	
    46	class ReportError(Exception):
    47	    """Recoverable — caller should 404 or return partial payload."""
    48	
    49	
    50	# ---------------------------------------------------------------------------
    51	# Data assembly
    52	# ---------------------------------------------------------------------------
    53	
    54	
    55	def _run_manifest_path(case_id: str, run_label: str) -> Path:
    56	    return _FIELDS_ROOT / case_id / "runs" / f"{run_label}.json"
    57	
    58	
    59	def _renders_manifest_path(case_id: str, run_label: str) -> Path:
    60	    return _RENDERS_ROOT / case_id / "runs" / f"{run_label}.json"
    61	
    62	
    63	def _load_run_manifest(case_id: str, run_label: str) -> dict:
    64	    p = _run_manifest_path(case_id, run_label)
    65	    if not p.is_file():
    66	        raise ReportError(f"no run manifest for {case_id}/{run_label}")
    67	    return json.loads(p.read_text(encoding="utf-8"))
    68	
    69	
    70	def _load_renders_manifest(case_id: str, run_label: str) -> Optional[dict]:
    71	    p = _renders_manifest_path(case_id, run_label)
    72	    if not p.is_file():
    73	        return None
    74	    return json.loads(p.read_text(encoding="utf-8"))
    75	
    76	
    77	def _load_ldc_gold() -> tuple[list[float], list[float], dict]:
    78	    gold_path = _GOLD_ROOT / "lid_driven_cavity.yaml"
    79	    if not gold_path.is_file():
    80	        raise ReportError(f"gold file missing: {gold_path}")
    81	    docs = list(yaml.safe_load_all(gold_path.read_text(encoding="utf-8")))
    82	    u_doc = next(
    83	        (d for d in docs if isinstance(d, dict) and d.get("quantity") == "u_centerline"),
    84	        None,
    85	    )
    86	    if u_doc is None:
    87	        raise ReportError("no u_centerline doc in LDC gold")
    88	    ys: list[float] = []
    89	    us: list[float] = []
    90	    for entry in u_doc.get("reference_values", []):
    91	        if isinstance(entry, dict):
    92	            y = entry.get("y")
    93	            u = entry.get("value") or entry.get("u")
    94	            if y is not None and u is not None:
    95	                ys.append(float(y))
    96	                us.append(float(u))
    97	    return ys, us, u_doc
    98	
    99	
   100	def _load_sample_xy(path: Path) -> tuple[np.ndarray, np.ndarray]:
   101	    rows = []
   102	    for line in path.read_text(encoding="utf-8").splitlines():
   103	        s = line.strip()
   104	        if not s or s.startswith("#"):
   105	            continue
   106	        parts = s.split()
   107	        try:
   108	            rows.append([float(parts[0]), float(parts[1])])
   109	        except (ValueError, IndexError):
   110	            continue
   111	    if not rows:
   112	        raise ReportError(f"empty sample: {path}")
   113	    arr = np.array(rows)
   114	    return arr[:, 0], arr[:, 1]
   115	
   116	
   117	def _latest_sample_iter(artifact_dir: Path) -> Path:
   118	    sample_root = artifact_dir / "sample"
   119	    if not sample_root.is_dir():
   120	        raise ReportError(f"sample/ missing under {artifact_dir}")
   121	    iters = sorted(
   122	        (d for d in sample_root.iterdir() if d.is_dir() and d.name.isdigit()),
   123	        key=lambda d: int(d.name),
   124	    )
   125	    if not iters:
   126	        raise ReportError(f"no sample iter dirs under {sample_root}")
   127	    return iters[-1]
   128	
   129	
   130	def _compute_metrics(
   131	    y_sim: np.ndarray, u_sim: np.ndarray,
   132	    y_gold: list[float], u_gold: list[float],
   133	    tolerance_pct: float,
   134	) -> dict[str, Any]:
   135	    """Compute L2/Linf/RMS + per-point |dev|% + pass count."""
   136	    y_sim_norm = y_sim / max(float(y_sim.max()), 1e-12)
   137	    u_sim_interp = np.interp(np.array(y_gold), y_sim_norm, u_sim)
   138	    u_gold_arr = np.array(u_gold)
   139	    diff = u_sim_interp - u_gold_arr
   140	
   141	    denom = np.where(np.abs(u_gold_arr) < 1e-9, 1e-9, np.abs(u_gold_arr))
   142	    dev_pct = 100.0 * np.abs(diff) / denom
   143	    n_total = len(u_gold_arr)
   144	    n_pass = int((dev_pct < tolerance_pct).sum())
   145	
   146	    return {
   147	        "l2": float(np.sqrt(np.mean(diff ** 2))),
   148	        "linf": float(np.max(np.abs(diff))),
   149	        "rms": float(np.sqrt(np.mean(diff ** 2))),  # alias
   150	        "max_dev_pct": float(dev_pct.max()) if n_total else 0.0,
   151	        "n_pass": n_pass,
   152	        "n_total": n_total,
   153	        "per_point_dev_pct": dev_pct.tolist(),
   154	    }
   155	
   156	
   157	def _parse_residuals_csv(path: Path) -> dict[str, Any]:
   158	    if not path.is_file():
   159	        return {"total_iter": 0, "final_ux": None, "note": None}
   160	    lines = path.read_text(encoding="utf-8").splitlines()
   161	    if len(lines) < 2:
   162	        return {"total_iter": 0, "final_ux": None, "note": None}
   163	    header = [c.strip() for c in lines[0].split(",")]
   164	    last = None
   165	    count = 0
   166	    for ln in lines[1:]:
   167	        parts = [c.strip() for c in ln.split(",")]
   168	        if len(parts) != len(header):
   169	            continue
   170	        last = parts
   171	        count += 1
   172	    final_ux = None
   173	    if last is not None and len(last) > 1 and last[1].upper() != "N/A":
   174	        try:
   175	            final_ux = float(last[1])
   176	        except ValueError:
   177	            pass
   178	    note = None
   179	    if final_ux is not None and final_ux > 1e-3:
   180	        note = (f"注意：Ux 终值 {final_ux:.2e} 大于 1e-3 — "
   181	                f"收敛可能未达稳态。建议增加 endTime 或降低 residualControl。")
   182	    return {"total_iter": count, "final_ux": final_ux, "note": note}
   183	
   184	
   185	def _load_grid_convergence(case_id: str, gold_y: list[float], gold_u: list[float]) -> tuple[list[dict], str]:
   186	    """Read mesh_20/40/80/160_measurement.yaml fixtures, build table rows."""
   187	    rows: list[dict] = []
   188	    # LDC fixtures compare at y≈0.0625 (first gold point >0).
   189	    sample_y = 0.0625
   190	    try:
   191	        sample_gold = next(u for y, u in zip(gold_y, gold_u) if abs(y - sample_y) < 1e-3)
   192	    except StopIteration:
   193	        sample_gold = gold_u[1] if len(gold_u) > 1 else 0.0
   194	
   195	    case_dir = _FIXTURE_ROOT / case_id
   196	    meshes = [("mesh_20", 20), ("mesh_40", 40), ("mesh_80", 80), ("mesh_160", 160)]
   197	    for name, _n in meshes:
   198	        path = case_dir / f"{name}_measurement.yaml"
   199	        if not path.is_file():
   200	            continue
   201	        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
   202	        meas = doc.get("measurement", {}) if isinstance(doc, dict) else {}
   203	        val = meas.get("value")
   204	        if val is None:
   205	            continue
   206	        try:
   207	            val_f = float(val)
   208	        except (ValueError, TypeError):
   209	            continue
   210	        denom = abs(sample_gold) if abs(sample_gold) > 1e-9 else 1e-9
   211	        dev_pct = 100.0 * abs(val_f - sample_gold) / denom
   212	        if dev_pct < 5.0:
   213	            verdict, cls = "PASS", "pass"
   214	        elif dev_pct < 10.0:
   215	            verdict, cls = "WARN", "warn"
   216	        else:
   217	            verdict, cls = "FAIL", "fail"
   218	        rows.append({
   219	            "mesh": name,
   220	            "value": val_f,
   221	            "dev_pct": dev_pct,
   222	            "verdict": verdict,
   223	            "verdict_class": cls,
   224	        })
   225	    if len(rows) < 2:
   226	        return rows, "insufficient mesh data"
   227	    devs = [r["dev_pct"] for r in rows]
   228	    monotone = all(devs[i] >= devs[i + 1] for i in range(len(devs) - 1))
   229	    note = "单调递减 ✓" if monotone else "非严格单调 — 检查 fixture"
   230	    return rows, note
   231	
   232	
   233	def _get_commit_sha() -> str:
   234	    try:
   235	        r = subprocess.run(
   236	            ["git", "rev-parse", "--short", "HEAD"],
   237	            capture_output=True, text=True, cwd=_REPO_ROOT, timeout=5,
   238	        )
   239	        return r.stdout.strip() or "unknown"
   240	    except (subprocess.SubprocessError, OSError):
   241	        return "unknown"
   242	
   243	
   244	# ---------------------------------------------------------------------------
   245	# Public API
   246	# ---------------------------------------------------------------------------
   247	
   248	
   249	def build_report_context(case_id: str, run_label: str = "audit_real_run") -> dict:
   250	    """Assemble all template variables. Raises ReportError on missing data."""
   251	    if case_id not in _REPORT_SUPPORTED_CASES:
   252	        raise ReportError(
   253	            f"case_id={case_id!r} not in Phase 7c MVP scope. "
   254	            f"Supported: {sorted(_REPORT_SUPPORTED_CASES)}."
   255	        )
   256	
   257	    run_manifest = _load_run_manifest(case_id, run_label)
   258	    timestamp = run_manifest["timestamp"]
   259	    artifact_dir = _FIELDS_ROOT / case_id / timestamp
   260	    if not artifact_dir.is_dir():

exec
/bin/zsh -lc "nl -ba ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx | sed -n '1270,1410p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
  1270	    profile_png_rel: string;
  1271	    pointwise_png_rel: string;
  1272	    contour_png_rel: string;
  1273	    residuals_png_rel: string;
  1274	  };
  1275	  meta: {
  1276	    commit_sha: string;
  1277	    report_generated_at: string;
  1278	  };
  1279	};
  1280	
  1281	function ScientificComparisonReportSection({ caseId }: { caseId: string }) {
  1282	  const runLabel = "audit_real_run";
  1283	  const { data, isLoading, isError } = useQuery<ComparisonReportContext>({
  1284	    queryKey: ["comparison-report-ctx", caseId, runLabel],
  1285	    queryFn: async () => {
  1286	      const resp = await fetch(
  1287	        `/api/cases/${encodeURIComponent(caseId)}/runs/${encodeURIComponent(
  1288	          runLabel,
  1289	        )}/comparison-report/context`,
  1290	        { credentials: "same-origin" },
  1291	      );
  1292	      if (!resp.ok) throw new ApiError(resp.status, await resp.text());
  1293	      return (await resp.json()) as ComparisonReportContext;
  1294	    },
  1295	    retry: false,
  1296	    // 404 is expected for cases not yet Phase 7a opted-in; hide silently.
  1297	    staleTime: 60_000,
  1298	  });
  1299	
  1300	  if (isLoading) return null; // quiet during fetch
  1301	  if (isError || !data) return null; // case not opted-in → silently hide
  1302	
  1303	  const verdictColor =
  1304	    data.verdict === "PASS"
  1305	      ? "bg-contract-pass/15 border-contract-pass/40 text-contract-pass"
  1306	      : data.verdict === "PARTIAL"
  1307	      ? "bg-yellow-500/10 border-yellow-500/40 text-yellow-300"
  1308	      : "bg-contract-fail/15 border-contract-fail/40 text-contract-fail";
  1309	
  1310	  const reportHtmlUrl = `/api/cases/${encodeURIComponent(caseId)}/runs/${encodeURIComponent(
  1311	    runLabel,
  1312	  )}/comparison-report`;
  1313	  const reportPdfUrl = `/api/cases/${encodeURIComponent(caseId)}/runs/${encodeURIComponent(
  1314	    runLabel,
  1315	  )}/comparison-report.pdf`;
  1316	
  1317	  return (
  1318	    <section>
  1319	      <div className="mb-3 flex items-baseline justify-between">
  1320	        <h2 className="card-title">科研级 CFD vs Gold 验证报告</h2>
  1321	        <p className="text-[11px] text-surface-500">
  1322	          实际 OpenFOAM 真跑 · 8 sections · {data.meta.commit_sha}
  1323	        </p>
  1324	      </div>
  1325	
  1326	      <div
  1327	        className={`mb-4 rounded-md border p-4 ${verdictColor}`}
  1328	        role="status"
  1329	      >
  1330	        <div className="flex items-center justify-between gap-4">
  1331	          <div>
  1332	            <div className="text-[11px] font-semibold uppercase tracking-wider opacity-85">
  1333	              Verdict
  1334	            </div>
  1335	            <div className="mt-1 text-[22px] font-bold leading-tight">
  1336	              {data.verdict}
  1337	            </div>
  1338	            <div className="mt-1 text-[12px] text-surface-200">
  1339	              {data.verdict_subtitle}
  1340	            </div>
  1341	          </div>
  1342	          <div className="grid grid-cols-2 gap-3 text-right text-[12px]">
  1343	            <div>
  1344	              <div className="text-surface-400">max |dev|</div>
  1345	              <div className="mono text-surface-100">
  1346	                {data.metrics.max_dev_pct.toFixed(2)}%
  1347	              </div>
  1348	            </div>
  1349	            <div>
  1350	              <div className="text-surface-400">n_pass</div>
  1351	              <div className="mono text-surface-100">
  1352	                {data.metrics.n_pass} / {data.metrics.n_total}
  1353	              </div>
  1354	            </div>
  1355	            <div>
  1356	              <div className="text-surface-400">L²</div>
  1357	              <div className="mono text-surface-100">
  1358	                {data.metrics.l2.toFixed(4)}
  1359	              </div>
  1360	            </div>
  1361	            <div>
  1362	              <div className="text-surface-400">L∞</div>
  1363	              <div className="mono text-surface-100">
  1364	                {data.metrics.linf.toFixed(4)}
  1365	              </div>
  1366	            </div>
  1367	          </div>
  1368	        </div>
  1369	      </div>
  1370	
  1371	      <div className="mb-3 flex flex-wrap gap-2 text-[12px]">
  1372	        <a
  1373	          href={reportHtmlUrl}
  1374	          target="_blank"
  1375	          rel="noopener noreferrer"
  1376	          className="rounded border border-surface-700 bg-surface-800/60 px-3 py-1.5 text-surface-200 hover:bg-surface-700/60"
  1377	        >
  1378	          ↗ 新窗口打开完整报告
  1379	        </a>
  1380	        <a
  1381	          href={reportPdfUrl}
  1382	          download
  1383	          className="rounded border border-surface-700 bg-surface-800/60 px-3 py-1.5 text-surface-200 hover:bg-surface-700/60"
  1384	        >
  1385	          ↓ 下载 PDF
  1386	        </a>
  1387	      </div>
  1388	
  1389	      <div className="overflow-hidden rounded-md border border-surface-800 bg-white">
  1390	        <iframe
  1391	          title="CFD vs Gold comparison report"
  1392	          src={reportHtmlUrl}
  1393	          className="h-[1400px] w-full border-0"
  1394	          sandbox=""
  1395	        />
  1396	      </div>
  1397	    </section>
  1398	  );
  1399	}

exec
/bin/zsh -lc "nl -ba scripts/render_case_report.py | sed -n '1,280p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
     1	#!/usr/bin/env python3
     2	"""Phase 7b — render_case_report.py
     3	
     4	Convert Phase 7a-captured field artifacts (reports/phase5_fields/{case}/{ts}/)
     5	into visual renders (reports/phase5_renders/{case}/{ts}/):
     6	
     7	- profile_u_centerline.png   — matplotlib static profile (sim vs gold)
     8	- profile_u_centerline.html  — Plotly JSON (for frontend interactive)
     9	- residuals.png              — log-y residual convergence history
    10	- contour_u_magnitude.png    — 2D U-magnitude contour from final sample iter
    11	- pointwise_deviation.png    — color heatmap of |dev|% per gold point
    12	
    13	LDC MVP: works today for case_id=lid_driven_cavity. Other 9 cases will be
    14	unlocked in Phase 7c Sprint-2 as their adapters emit Phase 7a function objects.
    15	
    16	Usage:
    17	    python scripts/render_case_report.py lid_driven_cavity
    18	    python scripts/render_case_report.py lid_driven_cavity --run audit_real_run
    19	
    20	Dependencies: matplotlib (2D plots), plotly (interactive JSON), numpy, PyYAML.
    21	No PyVista / no VTK parser needed for MVP — uses the sample CSV directly.
    22	"""
    23	from __future__ import annotations
    24	
    25	import argparse
    26	import json
    27	import sys
    28	from pathlib import Path
    29	from typing import Optional
    30	
    31	import matplotlib
    32	
    33	matplotlib.use("Agg")  # headless — CI-safe
    34	import matplotlib.pyplot as plt
    35	import numpy as np
    36	import plotly.graph_objects as go
    37	import yaml
    38	
    39	REPO_ROOT = Path(__file__).resolve().parent.parent
    40	FIELDS_ROOT = REPO_ROOT / "reports" / "phase5_fields"
    41	RENDERS_ROOT = REPO_ROOT / "reports" / "phase5_renders"
    42	GOLD_ROOT = REPO_ROOT / "knowledge" / "gold_standards"
    43	
    44	# Deterministic matplotlib style — locked for byte-reproducibility.
    45	plt.rcParams.update({
    46	    "figure.figsize": (8, 5),
    47	    "figure.dpi": 110,
    48	    "savefig.dpi": 110,
    49	    "savefig.bbox": "tight",
    50	    "font.family": "DejaVu Sans",
    51	    "font.size": 11,
    52	    "axes.grid": True,
    53	    "grid.alpha": 0.3,
    54	    "axes.spines.top": False,
    55	    "axes.spines.right": False,
    56	    "lines.linewidth": 1.8,
    57	})
    58	
    59	# Phase 7a opt-in mirror — matches scripts/phase5_audit_run.py::_PHASE7A_OPTED_IN.
    60	RENDER_SUPPORTED_CASES = frozenset({"lid_driven_cavity"})
    61	
    62	
    63	class RenderError(Exception):
    64	    """Non-fatal render failure — caller decides whether to abort the batch."""
    65	
    66	
    67	# ---------------------------------------------------------------------------
    68	# I/O helpers
    69	# ---------------------------------------------------------------------------
    70	
    71	
    72	def _resolve_run_timestamp(case_id: str, run_label: str) -> str:
    73	    """Read the per-run manifest written by phase5_audit_run.py and return its timestamp."""
    74	    manifest_path = FIELDS_ROOT / case_id / "runs" / f"{run_label}.json"
    75	    if not manifest_path.is_file():
    76	        raise RenderError(f"no run manifest: {manifest_path}")
    77	    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    78	    ts = data.get("timestamp")
    79	    if not ts:
    80	        raise RenderError(f"manifest missing timestamp: {manifest_path}")
    81	    return ts
    82	
    83	
    84	def _artifact_dir(case_id: str, timestamp: str) -> Path:
    85	    d = FIELDS_ROOT / case_id / timestamp
    86	    if not d.is_dir():
    87	        raise RenderError(f"artifact dir missing: {d}")
    88	    return d
    89	
    90	
    91	def _renders_dir(case_id: str, timestamp: str) -> Path:
    92	    d = RENDERS_ROOT / case_id / timestamp
    93	    d.mkdir(parents=True, exist_ok=True)
    94	    return d
    95	
    96	
    97	def _load_sample_xy(path: Path) -> tuple[np.ndarray, np.ndarray]:
    98	    """Load OpenFOAM `sample` output (.xy file, whitespace-separated).
    99	
   100	    Column layout for uCenterline: y  U_x  U_y  U_z  p.
   101	    Returns (y, U_x). Skips header lines starting with '#'.
   102	    """
   103	    rows: list[list[float]] = []
   104	    for line in path.read_text(encoding="utf-8").splitlines():
   105	        s = line.strip()
   106	        if not s or s.startswith("#"):
   107	            continue
   108	        parts = s.split()
   109	        # Accept either 5 (y Ux Uy Uz p) or 2 (y Ux) column variants.
   110	        try:
   111	            y = float(parts[0])
   112	            ux = float(parts[1])
   113	        except (ValueError, IndexError):
   114	            continue
   115	        rows.append([y, ux])
   116	    if not rows:
   117	        raise RenderError(f"empty sample file: {path}")
   118	    arr = np.array(rows)
   119	    return arr[:, 0], arr[:, 1]
   120	
   121	
   122	def _load_residuals_csv(path: Path) -> tuple[np.ndarray, dict[str, np.ndarray]]:
   123	    """Load residuals.csv written by _capture_field_artifacts.
   124	
   125	    Format: Time,Ux,Uy,p  — first data row may be "N/A" for iter 0.
   126	    Returns (iterations, {field_name: array}).
   127	    """
   128	    raw = path.read_text(encoding="utf-8").splitlines()
   129	    if not raw:
   130	        raise RenderError(f"empty residuals: {path}")
   131	    header = [c.strip() for c in raw[0].split(",")]
   132	    if header[0].lower() not in ("time", "iter", "iteration"):
   133	        raise RenderError(f"unexpected residuals header: {header}")
   134	    fields = header[1:]
   135	    iters: list[int] = []
   136	    data: dict[str, list[float]] = {f: [] for f in fields}
   137	    for line in raw[1:]:
   138	        parts = [c.strip() for c in line.split(",")]
   139	        if len(parts) != len(header):
   140	            continue
   141	        try:
   142	            iters.append(int(float(parts[0])))
   143	        except ValueError:
   144	            continue
   145	        for f, v in zip(fields, parts[1:]):
   146	            if v.upper() == "N/A" or v == "":
   147	                data[f].append(float("nan"))
   148	            else:
   149	                try:
   150	                    data[f].append(float(v))
   151	                except ValueError:
   152	                    data[f].append(float("nan"))
   153	    return np.array(iters), {k: np.array(v) for k, v in data.items()}
   154	
   155	
   156	def _load_gold_ldc() -> tuple[list[float], list[float], str]:
   157	    """Return (y_points, u_values, citation) from knowledge/gold_standards/lid_driven_cavity.yaml.
   158	
   159	    File is multi-document YAML (u_centerline, v_centerline, primary_vortex_location).
   160	    Iterate safe_load_all and pick the u_centerline document.
   161	    """
   162	    gold = GOLD_ROOT / "lid_driven_cavity.yaml"
   163	    if not gold.is_file():
   164	        raise RenderError(f"gold file missing: {gold}")
   165	    docs = list(yaml.safe_load_all(gold.read_text(encoding="utf-8")))
   166	    u_doc = next(
   167	        (d for d in docs if isinstance(d, dict) and d.get("quantity") == "u_centerline"),
   168	        None,
   169	    )
   170	    if u_doc is None:
   171	        raise RenderError("no quantity: u_centerline doc in LDC gold YAML")
   172	    refs = u_doc.get("reference_values", [])
   173	    ys: list[float] = []
   174	    us: list[float] = []
   175	    for entry in refs:
   176	        if isinstance(entry, dict):
   177	            y = entry.get("y")
   178	            u = entry.get("value") or entry.get("u")
   179	            if y is not None and u is not None:
   180	                ys.append(float(y))
   181	                us.append(float(u))
   182	    citation = u_doc.get("source") or u_doc.get("citation") or \
   183	        "Ghia, Ghia & Shin 1982 J. Comput. Phys. 47, 387-411 — Table I Re=100"
   184	    return ys, us, citation
   185	
   186	
   187	# ---------------------------------------------------------------------------
   188	# Renderers
   189	# ---------------------------------------------------------------------------
   190	
   191	
   192	def _latest_sample_iter(artifact_dir: Path) -> Path:
   193	    """Return the highest-iteration sample directory (e.g. .../sample/1000/)."""
   194	    sample_root = artifact_dir / "sample"
   195	    if not sample_root.is_dir():
   196	        raise RenderError(f"sample/ missing under {artifact_dir}")
   197	    iters = sorted(
   198	        (d for d in sample_root.iterdir() if d.is_dir() and d.name.isdigit()),
   199	        key=lambda d: int(d.name),
   200	    )
   201	    if not iters:
   202	        raise RenderError(f"no numeric iter subdirs under {sample_root}")
   203	    return iters[-1]
   204	
   205	
   206	def render_profile_png(
   207	    case_id: str,
   208	    artifact_dir: Path,
   209	    renders_dir: Path,
   210	) -> Path:
   211	    """Matplotlib PNG: sim U_x(y) solid line + Ghia 1982 scatter markers."""
   212	    latest = _latest_sample_iter(artifact_dir)
   213	    xy = latest / "uCenterline.xy"
   214	    y_sim, u_sim = _load_sample_xy(xy)
   215	
   216	    # LDC is stored in physical coords (convertToMeters 0.1 → y ∈ [0, 0.1]).
   217	    # Normalize to y_star ∈ [0, 1] for Ghia comparison.
   218	    y_norm = y_sim / max(y_sim.max(), 1e-12)
   219	
   220	    y_gold, u_gold, citation = _load_gold_ldc()
   221	
   222	    fig, ax = plt.subplots()
   223	    ax.plot(u_sim, y_norm, color="#1f77b4", label="simpleFoam (sim)")
   224	    ax.scatter(u_gold, y_gold, color="#d62728", s=36, zorder=5,
   225	               label="Ghia 1982 (Table I, Re=100)", edgecolor="white", linewidth=0.8)
   226	    ax.axvline(0, color="gray", linewidth=0.5, linestyle="--", alpha=0.5)
   227	    ax.set_xlabel(r"$U_x$ / $U_{\mathrm{lid}}$")
   228	    ax.set_ylabel(r"$y\,/\,L$")
   229	    ax.set_title(f"{case_id} — U centerline profile vs Ghia 1982")
   230	    ax.legend(loc="upper left", frameon=False)
   231	    ax.text(0.02, 0.02, citation[:80] + ("..." if len(citation) > 80 else ""),
   232	            transform=ax.transAxes, fontsize=8, color="gray", style="italic")
   233	    out = renders_dir / "profile_u_centerline.png"
   234	    fig.savefig(out)
   235	    plt.close(fig)
   236	    return out
   237	
   238	
   239	def render_profile_plotly_json(
   240	    case_id: str,
   241	    artifact_dir: Path,
   242	    renders_dir: Path,
   243	) -> Path:
   244	    """Plotly figure JSON (consumed by frontend for hover/zoom interactive)."""
   245	    latest = _latest_sample_iter(artifact_dir)
   246	    xy = latest / "uCenterline.xy"
   247	    y_sim, u_sim = _load_sample_xy(xy)
   248	    y_norm = y_sim / max(y_sim.max(), 1e-12)
   249	
   250	    y_gold, u_gold, citation = _load_gold_ldc()
   251	
   252	    fig = go.Figure()
   253	    fig.add_trace(go.Scatter(
   254	        x=u_sim, y=y_norm, mode="lines", name="simpleFoam",
   255	        line=dict(color="#1f77b4", width=2),
   256	        hovertemplate="U<sub>x</sub>=%{x:.4f}<br>y/L=%{y:.4f}<extra>sim</extra>",
   257	    ))
   258	    fig.add_trace(go.Scatter(
   259	        x=u_gold, y=y_gold, mode="markers", name="Ghia 1982",
   260	        marker=dict(color="#d62728", size=9, line=dict(color="white", width=1)),
   261	        hovertemplate="U<sub>x</sub>=%{x:.4f}<br>y/L=%{y:.4f}<extra>gold</extra>",
   262	    ))
   263	    fig.update_layout(
   264	        title=f"{case_id} — U centerline profile vs {citation[:60]}",
   265	        xaxis_title="U_x / U_lid",
   266	        yaxis_title="y / L",
   267	        template="plotly_white",
   268	        hovermode="closest",
   269	        margin=dict(l=50, r=20, t=50, b=50),
   270	    )
   271	    # Static JSON (no widget state). include_plotlyjs='cdn' on frontend side.
   272	    payload = fig.to_json()
   273	    out = renders_dir / "profile_u_centerline.plotly.json"
   274	    out.write_text(payload, encoding="utf-8")
   275	    return out
   276	
   277	
   278	def render_residuals_png(
   279	    case_id: str,
   280	    artifact_dir: Path,

exec
/bin/zsh -lc "nl -ba /Users/Zhuanz/.codex/memories/MEMORY.md | sed -n '356,366p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc "nl -ba scripts/render_case_report.py | sed -n '281,520p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
   356	# Task Group: cfd-harness-unified governance closeout and planning gates
   357	
   358	scope: Close out accepted phases in `cfd-harness-unified`, normalize Notion-vs-repo naming drift, and keep future phases planning-only until the explicit solver/routing gate is reviewed.
   359	applies_to: cwd=/Users/Zhuanz/Desktop/cfd-harness-unified; reuse_rule=safe for this repo’s Notion-governed phase/gate work, but phase/task IDs and review packets are rollout-specific.
   360	
   361	## Task 1: Close Phase 8 and reconcile stale governance evidence
   362	
   363	### rollout_summary_files
   364	
   365	- rollout_summaries/2026-04-16T17-04-02-U9ea-phase8_closeout_and_phase9_planning_gate_prep.md (cwd=/Users/Zhuanz/Desktop/cfd-harness-unified, rollout_path=/Users/Zhuanz/.codex/sessions/2026/04/17/rollout-2026-04-17T01-04-02-019d973f-efab-7132-bd99-5e0ebb839e12.jsonl, updated_at=2026-04-17T05:16:53+00:00, thread_id=019d973f-efab-7132-bd99-5e0ebb839e12, Phase 8 closeout and evidence normalization)
   366	

 succeeded in 0ms:
   281	    renders_dir: Path,
   282	) -> Path:
   283	    """Matplotlib PNG: log-y residual convergence for Ux, Uy, p."""
   284	    csv = artifact_dir / "residuals.csv"
   285	    if not csv.is_file():
   286	        raise RenderError(f"residuals.csv missing: {csv}")
   287	    iters, fields = _load_residuals_csv(csv)
   288	
   289	    fig, ax = plt.subplots()
   290	    palette = {"Ux": "#1f77b4", "Uy": "#2ca02c", "p": "#d62728"}
   291	    for name, series in fields.items():
   292	        color = palette.get(name, "#7f7f7f")
   293	        # Use NaN-safe masking so iter-0 'N/A' doesn't break log plot.
   294	        mask = np.isfinite(series) & (series > 0)
   295	        ax.semilogy(iters[mask], series[mask], color=color, label=name)
   296	    ax.set_xlabel("Iteration")
   297	    ax.set_ylabel("Initial residual (log)")
   298	    ax.set_title(f"{case_id} — solver residual convergence")
   299	    ax.legend(loc="upper right", frameon=False)
   300	    out = renders_dir / "residuals.png"
   301	    fig.savefig(out)
   302	    plt.close(fig)
   303	    return out
   304	
   305	
   306	def render_pointwise_deviation_png(
   307	    case_id: str,
   308	    artifact_dir: Path,
   309	    renders_dir: Path,
   310	) -> Path:
   311	    """Bar chart of |dev|% per gold sample point (sim interpolated onto gold y-grid)."""
   312	    latest = _latest_sample_iter(artifact_dir)
   313	    y_sim, u_sim = _load_sample_xy(latest / "uCenterline.xy")
   314	    y_sim_norm = y_sim / max(y_sim.max(), 1e-12)
   315	
   316	    y_gold, u_gold, _ = _load_gold_ldc()
   317	    if not y_gold:
   318	        raise RenderError("no LDC gold reference_values")
   319	
   320	    u_sim_interp = np.interp(np.array(y_gold), y_sim_norm, u_sim)
   321	    # Guard against division by ~0.
   322	    denom = np.where(np.abs(u_gold) < 1e-9, 1e-9, np.abs(u_gold))
   323	    dev_pct = 100.0 * np.abs(u_sim_interp - np.array(u_gold)) / denom
   324	
   325	    fig, ax = plt.subplots()
   326	    # Color-code: green PASS (<5%), yellow WARN (5-10%), red FAIL (>10%).
   327	    colors = ["#2ca02c" if d < 5 else ("#ff9900" if d < 10 else "#d62728")
   328	              for d in dev_pct]
   329	    ax.bar(range(len(y_gold)), dev_pct, color=colors, edgecolor="white", linewidth=0.5)
   330	    ax.axhline(5, color="gray", linewidth=0.6, linestyle="--", alpha=0.6)
   331	    ax.set_xticks(range(len(y_gold)))
   332	    ax.set_xticklabels([f"{y:.3f}" for y in y_gold], rotation=45, ha="right", fontsize=8)
   333	    ax.set_xlabel("Gold sample y/L")
   334	    ax.set_ylabel("|dev|% vs Ghia 1982")
   335	    ax.set_title(f"{case_id} — pointwise deviation (5% tolerance)")
   336	    # Annotate PASS/FAIL count.
   337	    n_pass = int((dev_pct < 5).sum())
   338	    ax.text(
   339	        0.98, 0.95, f"{n_pass}/{len(dev_pct)} PASS",
   340	        transform=ax.transAxes, ha="right", va="top",
   341	        fontsize=10, fontweight="bold",
   342	        color="#2ca02c" if n_pass == len(dev_pct) else "#d62728",
   343	    )
   344	    out = renders_dir / "pointwise_deviation.png"
   345	    fig.savefig(out)
   346	    plt.close(fig)
   347	    return out
   348	
   349	
   350	def render_contour_u_magnitude_png(
   351	    case_id: str,
   352	    artifact_dir: Path,
   353	    renders_dir: Path,
   354	) -> Path:
   355	    """LDC MVP contour: uses the sample/{iter}/uCenterline.xy which is a 1D profile
   356	    along x=0.5 centerline. For a true 2D contour we'd need to parse the full VTK
   357	    volume, which requires the `vtk` package — deferred to Phase 7b polish.
   358	
   359	    Instead, render a stylized 1D heatmap strip showing U_x(y) along the centerline.
   360	    This is honestly labeled as "centerline slice" not "full field contour".
   361	    """
   362	    latest = _latest_sample_iter(artifact_dir)
   363	    y_sim, u_sim = _load_sample_xy(latest / "uCenterline.xy")
   364	    y_norm = y_sim / max(y_sim.max(), 1e-12)
   365	
   366	    fig, ax = plt.subplots(figsize=(4, 6))
   367	    # Tile the 1D profile horizontally to make a strip heatmap visible.
   368	    strip = np.tile(u_sim.reshape(-1, 1), (1, 20))
   369	    im = ax.imshow(
   370	        strip,
   371	        aspect="auto",
   372	        origin="lower",
   373	        extent=[0, 1, float(y_norm.min()), float(y_norm.max())],
   374	        cmap="RdBu_r",
   375	        vmin=-1.0, vmax=1.0,
   376	    )
   377	    ax.set_xlabel("(tile axis)")
   378	    ax.set_ylabel("y / L")
   379	    ax.set_title(f"{case_id} — U_x centerline slice\n(Phase 7b MVP — full 2D VTK contour\ndeferred to 7b-polish)")
   380	    cbar = fig.colorbar(im, ax=ax, fraction=0.08, pad=0.04)
   381	    cbar.set_label("U_x / U_lid")
   382	    out = renders_dir / "contour_u_magnitude.png"
   383	    fig.savefig(out)
   384	    plt.close(fig)
   385	    return out
   386	
   387	
   388	# ---------------------------------------------------------------------------
   389	# Orchestration
   390	# ---------------------------------------------------------------------------
   391	
   392	
   393	def render_all(case_id: str, run_label: str = "audit_real_run") -> dict:
   394	    """Render all 7b MVP figures for a given case/run. Returns {name: path, ...}."""
   395	    if case_id not in RENDER_SUPPORTED_CASES:
   396	        raise RenderError(
   397	            f"case_id={case_id!r} not opted-in for Phase 7b rendering. "
   398	            f"Supported: {sorted(RENDER_SUPPORTED_CASES)}. "
   399	            f"Other cases unlock in Phase 7c Sprint-2."
   400	        )
   401	    timestamp = _resolve_run_timestamp(case_id, run_label)
   402	    artifact_dir = _artifact_dir(case_id, timestamp)
   403	    renders_dir = _renders_dir(case_id, timestamp)
   404	
   405	    outputs: dict[str, Path] = {}
   406	    renderers = [
   407	        ("profile_png", render_profile_png),
   408	        ("profile_plotly_json", render_profile_plotly_json),
   409	        ("residuals_png", render_residuals_png),
   410	        ("pointwise_deviation_png", render_pointwise_deviation_png),
   411	        ("contour_u_magnitude_png", render_contour_u_magnitude_png),
   412	    ]
   413	    errors: dict[str, str] = {}
   414	    for name, fn in renderers:
   415	        try:
   416	            outputs[name] = fn(case_id, artifact_dir, renders_dir)
   417	        except Exception as e:  # noqa: BLE001  — keep batch alive
   418	            errors[name] = f"{type(e).__name__}: {e}"
   419	            print(f"[render] [WARN] {name} failed: {e}", file=sys.stderr)
   420	
   421	    # Write per-run renders manifest (mirrors phase5_fields/{case}/runs/{label}.json).
   422	    manifest_dir = RENDERS_ROOT / case_id / "runs"
   423	    manifest_dir.mkdir(parents=True, exist_ok=True)
   424	    manifest = {
   425	        "case_id": case_id,
   426	        "run_label": run_label,
   427	        "timestamp": timestamp,
   428	        "renders_dir_rel": str(renders_dir.relative_to(REPO_ROOT)),
   429	        "outputs": {k: str(p.relative_to(REPO_ROOT)) for k, p in outputs.items()},
   430	        "errors": errors,
   431	    }
   432	    manifest_path = manifest_dir / f"{run_label}.json"
   433	    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
   434	    print(f"[render] {case_id} → {len(outputs)}/{len(renderers)} outputs; manifest={manifest_path}")
   435	    return {"manifest": manifest_path, **outputs}
   436	
   437	
   438	def main(argv: Optional[list[str]] = None) -> int:
   439	    parser = argparse.ArgumentParser(description="Phase 7b render pipeline for CFD audit artifacts")
   440	    parser.add_argument("case_id", help="e.g. lid_driven_cavity")
   441	    parser.add_argument("--run", dest="run_label", default="audit_real_run",
   442	                        help="run_label (default: audit_real_run)")
   443	    args = parser.parse_args(argv)
   444	    try:
   445	        render_all(args.case_id, args.run_label)
   446	        return 0
   447	    except RenderError as e:
   448	        print(f"[render] FATAL {e}", file=sys.stderr)
   449	        return 1
   450	
   451	
   452	if __name__ == "__main__":
   453	    sys.exit(main())

codex
I’ve got the line-level evidence. One last verification pass: I’m checking whether the current Matplotlib outputs are actually byte-stable on this machine across immediate re-runs, since that claim is specifically called out in 7b.
exec
/bin/zsh -lc "cat /tmp/phase7_render_run1.log; printf '\\n---\\n'; cat /tmp/phase7_render_run2.log" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:

---

exec
/bin/zsh -lc 'python3 scripts/render_case_report.py lid_driven_cavity --run audit_real_run >/tmp/phase7_render_run1.log 2>&1; shasum -a 256 reports/phase5_renders/lid_driven_cavity/20260421T082340Z/pointwise_deviation.png reports/phase5_renders/lid_driven_cavity/20260421T082340Z/profile_u_centerline.png reports/phase5_renders/lid_driven_cavity/20260421T082340Z/residuals.png reports/phase5_renders/lid_driven_cavity/20260421T082340Z/contour_u_magnitude.png' in /Users/Zhuanz/Desktop/cfd-harness-unified
exec
/bin/zsh -lc 'python3 scripts/render_case_report.py lid_driven_cavity --run audit_real_run >/tmp/phase7_render_run2.log 2>&1; shasum -a 256 reports/phase5_renders/lid_driven_cavity/20260421T082340Z/pointwise_deviation.png reports/phase5_renders/lid_driven_cavity/20260421T082340Z/profile_u_centerline.png reports/phase5_renders/lid_driven_cavity/20260421T082340Z/residuals.png reports/phase5_renders/lid_driven_cavity/20260421T082340Z/contour_u_magnitude.png' in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 537ms:
4e20e7743de2f5fd024103f2e5838d3aa856021a2be4a846550f652fb08ebe2f  reports/phase5_renders/lid_driven_cavity/20260421T082340Z/pointwise_deviation.png
4d29cd61babefa233508f230fba7e162b95d2edf4ed015d71ae83b798f5e3290  reports/phase5_renders/lid_driven_cavity/20260421T082340Z/profile_u_centerline.png
c84f54eb8479d38ac91c153c98ce0fb178ca21833b904d8a752a24dcc8fa18e4  reports/phase5_renders/lid_driven_cavity/20260421T082340Z/residuals.png
8ea80d21a56f799a1d5e89e8189d6b091cd17d35efbf006b771dfb4db3bc917f  reports/phase5_renders/lid_driven_cavity/20260421T082340Z/contour_u_magnitude.png

 succeeded in 504ms:
4e20e7743de2f5fd024103f2e5838d3aa856021a2be4a846550f652fb08ebe2f  reports/phase5_renders/lid_driven_cavity/20260421T082340Z/pointwise_deviation.png
4d29cd61babefa233508f230fba7e162b95d2edf4ed015d71ae83b798f5e3290  reports/phase5_renders/lid_driven_cavity/20260421T082340Z/profile_u_centerline.png
c84f54eb8479d38ac91c153c98ce0fb178ca21833b904d8a752a24dcc8fa18e4  reports/phase5_renders/lid_driven_cavity/20260421T082340Z/residuals.png
8ea80d21a56f799a1d5e89e8189d6b091cd17d35efbf006b771dfb4db3bc917f  reports/phase5_renders/lid_driven_cavity/20260421T082340Z/contour_u_magnitude.png

exec
/bin/zsh -lc "rg -n \"comparison_report\" ui/backend/tests -g '*.py'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 exited 1 in 0ms:
exec
/bin/zsh -lc "nl -ba ui/backend/services/comparison_report.py | sed -n '257,390p'" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
   257	    run_manifest = _load_run_manifest(case_id, run_label)
   258	    timestamp = run_manifest["timestamp"]
   259	    artifact_dir = _FIELDS_ROOT / case_id / timestamp
   260	    if not artifact_dir.is_dir():
   261	        raise ReportError(f"artifact dir missing: {artifact_dir}")
   262	
   263	    # Load + compute
   264	    gold_y, gold_u, gold_doc = _load_ldc_gold()
   265	    tolerance = float(gold_doc.get("tolerance", 0.05)) * 100.0  # fraction → percent
   266	    latest_sample = _latest_sample_iter(artifact_dir)
   267	    y_sim, u_sim = _load_sample_xy(latest_sample / "uCenterline.xy")
   268	    metrics = _compute_metrics(y_sim, u_sim, gold_y, gold_u, tolerance)
   269	
   270	    residual_info = _parse_residuals_csv(artifact_dir / "residuals.csv")
   271	    grid_conv_rows, grid_note = _load_grid_convergence(case_id, gold_y, gold_u)
   272	
   273	    # Verdict logic: all-pass OR tolerance met.
   274	    is_all_pass = metrics["n_pass"] == metrics["n_total"] and metrics["n_total"] > 0
   275	    majority_pass = metrics["n_pass"] >= math.ceil(metrics["n_total"] * 0.6)
   276	    if is_all_pass:
   277	        verdict, verdict_gradient, subtitle = "PASS", "#059669 0%, #10b981 100%", (
   278	            f"全部 {metrics['n_total']} 个 gold 点在 ±{tolerance:.1f}% 容差内。"
   279	        )
   280	    elif majority_pass:
   281	        verdict, verdict_gradient, subtitle = "PARTIAL", "#d97706 0%, #f59e0b 100%", (
   282	            f"{metrics['n_pass']}/{metrics['n_total']} 点通过；"
   283	            f"{metrics['n_total'] - metrics['n_pass']} 点残差为已记录物理项 "
   284	            f"(见 DEC-V61-030 关于 Ghia 非均匀网格 vs 均匀网格的插值误差)。"
   285	        )
   286	    else:
   287	        verdict, verdict_gradient, subtitle = "FAIL", "#dc2626 0%, #ef4444 100%", (
   288	            f"仅 {metrics['n_pass']}/{metrics['n_total']} 点通过 — "
   289	            f"需要诊断 (solver, mesh, 或 gold 本身)。"
   290	        )
   291	
   292	    # Renders — use Phase 7b manifest if available; else None placeholders.
   293	    renders_manifest = _load_renders_manifest(case_id, run_label)
   294	    renders_dir = _RENDERS_ROOT / case_id / timestamp
   295	
   296	    def _rel(key: str, default: str = "") -> str:
   297	        if renders_manifest and key in renders_manifest.get("outputs", {}):
   298	            return renders_manifest["outputs"][key]
   299	        # Fallback: guess the conventional name
   300	        guess = renders_dir / default
   301	        return str(guess.relative_to(_REPO_ROOT)) if guess.is_file() else ""
   302	
   303	    renders = {
   304	        "profile_png_rel": _rel("profile_png", "profile_u_centerline.png"),
   305	        "pointwise_png_rel": _rel("pointwise_deviation_png", "pointwise_deviation.png"),
   306	        "contour_png_rel": _rel("contour_u_magnitude_png", "contour_u_magnitude.png"),
   307	        "residuals_png_rel": _rel("residuals_png", "residuals.png"),
   308	    }
   309	
   310	    paper = {
   311	        "title": gold_doc.get("source", "Ghia, Ghia & Shin 1982 — Lid-Driven Cavity benchmark"),
   312	        "source": "J. Comput. Phys. 47, 387-411 (1982), Table I Re=100 column",
   313	        "doi": gold_doc.get("literature_doi", "10.1016/0021-9991(82)90058-4"),
   314	        "short": "Ghia 1982",
   315	        "gold_count": metrics["n_total"],
   316	        "tolerance_pct": tolerance,
   317	    }
   318	
   319	    now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
   320	
   321	    return {
   322	        "case_id": case_id,
   323	        "case_display_name": "Lid-Driven Cavity (Re=100)" if case_id == "lid_driven_cavity" else case_id,
   324	        "run_label": run_label,
   325	        "timestamp": timestamp,
   326	        "verdict": verdict,
   327	        "verdict_gradient": verdict_gradient,
   328	        "verdict_subtitle": subtitle,
   329	        "metrics": metrics,
   330	        "paper": paper,
   331	        "renders": renders,
   332	        "contour_caption": (
   333	            "Phase 7b MVP — 沿 x=0.5 中心线的 U_x 条带切片，后续 7b-polish 会用 VTK 体数据生成完整 2D contour。"
   334	        ),
   335	        "residual_info": residual_info,
   336	        "grid_conv": grid_conv_rows,
   337	        "grid_conv_note": grid_note,
   338	        "meta": {
   339	            "openfoam_version": "v10",
   340	            "solver": "simpleFoam (SIMPLE, laminar)",
   341	            "docker_image": "cfd-openfoam (local arm64 OpenFOAM v10)",
   342	            "commit_sha": _get_commit_sha(),
   343	            "mesh": "129×129 uniform",
   344	            "tolerance": f"±{tolerance:.1f}%",
   345	            "schemes": "steadyState + linearUpwind + Gauss linear corrected",
   346	            "report_generated_at": now,
   347	        },
   348	    }
   349	
   350	
   351	def render_report_html(case_id: str, run_label: str = "audit_real_run") -> str:
   352	    """Return the full HTML string for the comparison report."""
   353	    ctx = build_report_context(case_id, run_label)
   354	    tmpl = _env.get_template("comparison_report.html.j2")
   355	    return tmpl.render(**ctx)
   356	
   357	
   358	def render_report_pdf(case_id: str, run_label: str = "audit_real_run",
   359	                      output_path: Optional[Path] = None) -> Path:
   360	    """Render HTML to PDF via WeasyPrint and write to disk. Returns the file Path.
   361	
   362	    Asset resolution: WeasyPrint converts the HTML's relative img src paths.
   363	    We pass base_url=_REPO_ROOT so /reports/phase5_renders/... resolves correctly.
   364	    """
   365	    # Import weasyprint lazily — heavy import, only when PDF actually needed.
   366	    import weasyprint  # type: ignore
   367	
   368	    html = render_report_html(case_id, run_label)
   369	    if output_path is None:
   370	        ctx = build_report_context(case_id, run_label)
   371	        ts = ctx["timestamp"]
   372	        out_dir = _REPO_ROOT / "reports" / "phase5_reports" / case_id / ts
   373	        out_dir.mkdir(parents=True, exist_ok=True)
   374	        output_path = out_dir / f"{run_label}_comparison_report.pdf"
   375	
   376	    doc = weasyprint.HTML(string=html, base_url=str(_REPO_ROOT))
   377	    doc.write_pdf(str(output_path))
   378	    return output_path

exec
/bin/zsh -lc "python3 - <<'PY'
from pathlib import Path
repo = Path('/Users/Zhuanz/Desktop/cfd-harness-unified')
for ts in ['../../../../tmp/x', '../../../../../../tmp/x']:
    out = repo / 'reports' / 'phase5_reports' / 'lid_driven_cavity' / ts / 'audit_real_run_comparison_report.pdf'
    art = repo / 'reports' / 'phase5_fields' / 'lid_driven_cavity' / ts
    print(ts)
    print('  out ->', out.resolve(strict=False))
    print('  art ->', art.resolve(strict=False))
PY" in /Users/Zhuanz/Desktop/cfd-harness-unified
 succeeded in 0ms:
../../../../tmp/x
  out -> /Users/Zhuanz/Desktop/tmp/x/audit_real_run_comparison_report.pdf
  art -> /Users/Zhuanz/Desktop/tmp/x
../../../../../../tmp/x
  out -> /Users/tmp/x/audit_real_run_comparison_report.pdf
  art -> /Users/tmp/x

codex
CHANGES_REQUIRED

1. HIGH — Manifest-derived filesystem paths are trusted without containment checks, and the PDF path makes that trust exploitable. [`comparison_report.py:257`](</Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/comparison_report.py:257>) takes `run_manifest["timestamp"]` verbatim, [`comparison_report.py:296`](</Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/comparison_report.py:296>) returns `renders_manifest["outputs"][key]` verbatim, and [`comparison_report.py:376`](</Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/comparison_report.py:376>) renders the HTML with `base_url=_REPO_ROOT`. That means a tampered `runs/{label}.json` can steer reads outside `reports/phase5_fields`, a tampered renders manifest can point `<img src>` at arbitrary local image/SVG paths for WeasyPrint to load, and [`comparison_report.py:372`](</Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/comparison_report.py:372>) can write the generated PDF outside `reports/phase5_reports`. The same timestamp trust exists on the render side in [`render_case_report.py:72`](</Users/Zhuanz/Desktop/cfd-harness-unified/scripts/render_case_report.py:72>) and [`render_case_report.py:91`](</Users/Zhuanz/Desktop/cfd-harness-unified/scripts/render_case_report.py:91>). This needs strict segment validation or `resolve()` + root-prefix checks before approval.

2. MEDIUM — The `/learn` embed hides real backend failures as if the case were simply “not opted in.” [`LearnCaseDetailPage.tsx:1283`](</Users/Zhuanz/Desktop/cfd-harness-unified/ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:1283>) throws on any non-200, but [`LearnCaseDetailPage.tsx:1300`](</Users/Zhuanz/Desktop/cfd-harness-unified/ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:1300>) returns `null` for all errors. So a 500, malformed JSON, or regression in the report service silently removes the section from `/learn`, which is the opposite of the “scientific-grade evidence surface” honesty this phase is trying to provide. Hide only 404/unsupported-case; show an explicit error state for other statuses.

3. LOW — The new route tests do not actually protect this surface in a clean checkout/CI, and I could not find any service-level `comparison_report` tests to cover the gap. [`test_comparison_report_route.py:15`](</Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/tests/test_comparison_report_route.py:15>) documents that the success path depends on `.gitignored` local artifacts, and [`test_comparison_report_route.py:26`](</Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/tests/test_comparison_report_route.py:26>) plus [`test_comparison_report_route.py:47`](</Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/tests/test_comparison_report_route.py:47>) just `return` when those artifacts are absent. So the automation does not exercise the successful HTML/context path, template rendering, or manifest-path handling.

Comments:
- I did not find an iframe XSS issue in the current 7f/7c implementation. `sandbox=""` is the strict setting you want here, and the template does not use `|safe`; the main trust boundary is filesystem path handling, not HTML escaping.
- `yaml.safe_load` in `_load_grid_convergence` is fine for the checked `mesh_{20,40,80,160}_measurement.yaml` fixtures; they are single-document files.
- I re-ran `python3 scripts/render_case_report.py lid_driven_cavity --run audit_real_run` twice and the SHA-256 of the four PNG outputs matched both times on this machine, so I did not find a current 7b determinism failure. That is local evidence, not a cross-platform guarantee.


tokens used
128,938
CHANGES_REQUIRED

1. HIGH — Manifest-derived filesystem paths are trusted without containment checks, and the PDF path makes that trust exploitable. [`comparison_report.py:257`](</Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/comparison_report.py:257>) takes `run_manifest["timestamp"]` verbatim, [`comparison_report.py:296`](</Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/comparison_report.py:296>) returns `renders_manifest["outputs"][key]` verbatim, and [`comparison_report.py:376`](</Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/comparison_report.py:376>) renders the HTML with `base_url=_REPO_ROOT`. That means a tampered `runs/{label}.json` can steer reads outside `reports/phase5_fields`, a tampered renders manifest can point `<img src>` at arbitrary local image/SVG paths for WeasyPrint to load, and [`comparison_report.py:372`](</Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/comparison_report.py:372>) can write the generated PDF outside `reports/phase5_reports`. The same timestamp trust exists on the render side in [`render_case_report.py:72`](</Users/Zhuanz/Desktop/cfd-harness-unified/scripts/render_case_report.py:72>) and [`render_case_report.py:91`](</Users/Zhuanz/Desktop/cfd-harness-unified/scripts/render_case_report.py:91>). This needs strict segment validation or `resolve()` + root-prefix checks before approval.

2. MEDIUM — The `/learn` embed hides real backend failures as if the case were simply “not opted in.” [`LearnCaseDetailPage.tsx:1283`](</Users/Zhuanz/Desktop/cfd-harness-unified/ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:1283>) throws on any non-200, but [`LearnCaseDetailPage.tsx:1300`](</Users/Zhuanz/Desktop/cfd-harness-unified/ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:1300>) returns `null` for all errors. So a 500, malformed JSON, or regression in the report service silently removes the section from `/learn`, which is the opposite of the “scientific-grade evidence surface” honesty this phase is trying to provide. Hide only 404/unsupported-case; show an explicit error state for other statuses.

3. LOW — The new route tests do not actually protect this surface in a clean checkout/CI, and I could not find any service-level `comparison_report` tests to cover the gap. [`test_comparison_report_route.py:15`](</Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/tests/test_comparison_report_route.py:15>) documents that the success path depends on `.gitignored` local artifacts, and [`test_comparison_report_route.py:26`](</Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/tests/test_comparison_report_route.py:26>) plus [`test_comparison_report_route.py:47`](</Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/tests/test_comparison_report_route.py:47>) just `return` when those artifacts are absent. So the automation does not exercise the successful HTML/context path, template rendering, or manifest-path handling.

Comments:
- I did not find an iframe XSS issue in the current 7f/7c implementation. `sandbox=""` is the strict setting you want here, and the template does not use `|safe`; the main trust boundary is filesystem path handling, not HTML escaping.
- `yaml.safe_load` in `_load_grid_convergence` is fine for the checked `mesh_{20,40,80,160}_measurement.yaml` fixtures; they are single-document files.
- I re-ran `python3 scripts/render_case_report.py lid_driven_cavity --run audit_real_run` twice and the SHA-256 of the four PNG outputs matched both times on this machine, so I did not find a current 7b determinism failure. That is local evidence, not a cross-platform guarantee.


