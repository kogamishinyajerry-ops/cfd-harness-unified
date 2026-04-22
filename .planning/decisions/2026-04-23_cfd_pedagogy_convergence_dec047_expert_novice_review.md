---
decision_id: DEC-V61-047
title: CFD 教学质量专项 — 每 case 仿真/网格/云图/分析/全流程升级 · 2-persona (expert + novice) 迭代
status: IN_PROGRESS (round 2 remediation landed 2026-04-23T01:30; round 3 pending)
commits_in_scope:
  - 09a4975 docs(dec): DEC-V61-047 PROPOSAL — CFD 教学质量专项 2-persona iteration
  - 9d43d6a fix(learn): round-1 batch 1 — narrative truth alignment (F5 blocker)
  - 958d85d fix(learn): round-1 batches 2+3 — visual-only verdict honesty + synthetic residual guard (F1+F2 blockers)
  - 10a3463 feat(learn): round-1 batches 4+5 — teaching cards + evidence collapse (F4+F6 majors)
  - 51c7198 docs(dec): round-1 SYNC COMPLETE + round-2 prompt authored
  - 196fb94 fix(learn): round-2 batch 6 — naca0012 truth alignment (N1)
codex_verdict: CHANGES_REQUIRED (round 2 — 0 blockers + 1 major N1 naca0012 setup drift; remediated in batch 6; F1/F2/F5/F6 CLOSED, F3 deferral ACCEPTED, F4 was PARTIAL due to N1 now fixed)
autonomous_governance: true
autonomous_governance_counter_v61: 34 (34th +1 entry since RETRO-V61-001 counter reset; next retro trigger at ≥20 arc-size → already past, retro owed)
external_gate_self_estimated_pass_rate: 0.50
codex_tool_report_path: .planning/reviews/pedagogy_round_2_findings.md (7.2 KB, authored 2026-04-23T01:22; CHANGES_REQUIRED · 0 blockers · F1/F2/F5/F6 CLOSED · F3 deferral accepted · F4 PARTIAL → N1 naca0012 drift · N1 remediated in 196fb94. Round 1 findings retained at pedagogy_round_1_findings.md for arc audit.)
notion_sync_status: synced 2026-04-23T01:32 (round-2 remediation summary appended as 5 page children; Status=Accepted; https://www.notion.so/DEC-V61-047-CFD-10-case-2-persona-expert-novice-34ac68942bed81868028c1a4aea5d6bf)
github_sync_status: pushed 2026-04-23T01:30 (196fb94 on origin/main; scaffold + 3 round-1 remediation + round-1 sync-complete + round-2 batch 6 N1 fix)
related:
  - DEC-V61-046 (prior iteration pattern; demo-first convergence; closed APPROVE_WITH_COMMENTS 2026-04-23T00:35 · this DEC inherits the iteration discipline)
  - DEC-V61-040 (UI 3-tier UNKNOWN surface · underpins the Story tab)
  - DEC-V61-045 (full blocker-fix iteration reference)
timestamp: 2026-04-23T00:45 local
author: Claude Opus 4.7 (1M context, v6.2 Main Driver)
---

## Why this DEC exists

User deep-review of the /learn demo (post-DEC-V61-046 closeout):

> 我觉得现在的每个 case，不论是仿真设置、网格划分策略、云图、分析，都有严重
> 的问题，它根本就不像优秀的教科书 case，云图非常难以理解，真实的仿真流场云
> 图也严重不足，CFD 全流程工作流的逐步展示也没有充分展示。如果一个新手中文
> 母语的 CFD 工程师来看这个 UI，会陷入完全的困惑。

Claude recon confirms the concern is factual, not opinion:

1. **Story tab 没有 mesh 策略叙事** — geometry_assumption + mesh_info.cells 藏在 gold YAML，学生看不到；Mesh tab 只呈现 grid-convergence slider，不解释"这个 case 为什么需要这个 mesh 密度"。
2. **Solver setup 完全不出现在 /learn** — solver name / schemes / 湍流模型 / relaxation factors 只在 Pro 工作台 + YAML 编辑器里可见；/learn Story tab 无任何 solver 教学。
3. **真实 contour 云图没接入 /learn** — `reports/<case>/phase5_renders/contour_u_magnitude.png` 存在但未在 UI 上出现；/learn 目前只渲染 `ui/frontend/public/flow-fields/<case>/*.png` 的文献参考图（LDC 只有 2 张，多数 case 只 1 张）。
4. **Run tab 残差是 synthetic mock** — `ResidualsPreview` SVG 是装饰性的假曲线，不是真实 solver 运行的残差 trace，对新手有误导风险。
5. **BC / 数值方案 / 收敛判据没有专门的卡片** — 零散提及在 `physics_bullets_zh` 中，不一致、不完整。
6. **CFD 全流程（pre-processing → meshing → solver → post-processing）没有 step-by-step 展示** — 新手没法理解"从问题到结果"的 pipeline。

User 指定 2 个评审 persona（不含 senior code reviewer，这轮不是代码审查）：

1. **CFD 仿真专家工程师** — 从工程严谨性看：每 case 的仿真/网格/云图/分析是否达到"教科书级"？物理契约的 precondition 与实际的 mesh/solver/schemes 选择是否内恰一致？
2. **CFD 仿真新手学徒（中文母语）** — 从学习者体验看：一个刚开始学 CFD 的中国工程师点进任何一个 case，能不能理解这是什么问题、怎么建的网格、怎么跑的、结果怎么看、为什么这些验证指标重要？哪里会卡住？哪里会误解？哪里会"不得其门而入"？

两个 persona 轮流提 findings，要 file:line 证据，分 🔴/🟠/🟡/🟢 4 档。Claude 按优先级批量修，push + Notion sync 每轮闭环。

## Scope

- **In**:
  - 每 10 case 的 Story tab 教学叙事（mesh 策略、solver setup、BC 完整性、收敛判据）
  - 真实 contour 云图（`reports/<case>/phase5_renders/`）接入 /learn 的可见路径
  - Run tab 残差改造 —— 要么用真实运行的 residual 数据，要么清楚标注 illustrative
  - CFD 全流程 step-by-step 的学习者叙事（pre-processing / meshing / solver / post-processing）
  - 中文新手可读性 —— 术语注释、单位注解、"为什么这么做"的 rationale
- **Out**:
  - 代码审查（本轮 review 聚焦 UX + pedagogy，不是 OOP 代码卫生）
  - 后端 API 契约大改动（tri-state 已经在 V61-046 round-3 做了，本轮不再动）
  - 新增 case（不扩 whitelist 规模，只升级现有 10 case 的教学质量）
  - 代码 split / bundle 优化（非教学问题）
- **Deferrals that might emerge but shouldn't block**:
  - 前端组件重构（只要不阻碍教学叙事，现有组件可先 patch）
  - Mesh 生成工具集成（如 Gmsh 教学）—— 说明当前 adapter 用 blockMesh 的简化路径即可

## Round log (updated per round)

### Round 1 — 2026-04-23T00:51 → T01:20 (remediation landed)
- **Codex exec PID**: 36085 (log `.planning/reviews/pedagogy_round_1_codex.log`)
- **Prompt**: `.planning/reviews/pedagogy_round_1_prompt.md`
- **Findings**: `.planning/reviews/pedagogy_round_1_findings.md` (19 KB)
- **Verdict**: CHANGES_REQUIRED across both personas · 4 blockers + 2 majors
  - Fairness correction codex volunteered: real OpenFOAM contours ARE now mounted via ScientificComparisonReportSection; user's "完全没有真实云图" read is partially out of date. The real problem is that evidence is **under-explained, inconsistently narrated, and often status-contradictory**, not missing.
  - Blockers: F1 hardcoded Story-visual-only FAIL banner (contradicts cylinder/plane_channel fixtures that declare `expected_verdict: PASS`); F2 synthetic /run residual shown as "你大概会看到" without clear mock signal; F5 stale case narratives on TFP/plane_channel/impinging_jet/DHC disagree with current gold contracts.
  - Majors: F3 9/10 cases still Tier-C visual-only in `comparison_report.py`; F4 solver/mesh/BC/observable-extraction live only in gold YAML, never surfaced as student cards; F6 PhysicsContractPanel reviewer-grade evidence_ref jargon confuses novice (impinging_jet 🔴).
- **Findings addressed** (5 atomic commits):
  - Batch 1 (F5 blocker) `9d43d6a` — rewrote 4 stale learnCases.ts entries to match current gold contracts: TFP labeled laminar Blasius not turbulent; plane_channel labeled as "disguised incompatibility" teaching case; impinging_jet labeled 2-layer (geometry+solver) gap; DHC rewritten from retired Ra=1e10 to Ra=1e6 de Vahl Davis benchmark.
  - Batches 2+3 (F1+F2 blockers) `958d85d` — removed hardcoded "audit_real_run verdict FAIL" copy from visual-only Tier-C branch (backend sends verdict=None; fixtures may say PASS); reframed as honest "Tier C · 过程证据，未做自动化金标准比对". Wrapped /run residual in new RunResidualsCard that tries real `audit_real_run/renders/residuals.png` first, falls back to synthetic SVG only with prominent "⚠ 示意图 · illustrative only" warning.
  - Batches 4+5 (F4+F6 majors) `10a3463` — extended LearnCase type with 4 new Chinese teaching fields (solver_setup_zh / mesh_strategy_zh / boundary_conditions_zh / observable_extraction_zh); populated all 10 cases with concrete content pulled from gold YAML + foam_agent_adapter; added TeachingCard component rendering 4 color-coded cards (sky/emerald/violet/amber) on Story tab under new "CFD 全流程" section. Collapsed PhysicsContractPanel evidence_ref into `<details>` so novice sees condition + consequence_if_unsatisfied by default, expandable for raw audit evidence.
- **Findings deferred with rationale**:
  - F3 (9/10 cases Tier-C) — upgrading `_VISUAL_ONLY_CASES` in `ui/backend/services/comparison_report.py` to include gold overlay + verdict + metrics for more cases is a backend service refactor that ripples through tier-B report assembly + HTML iframe rendering + test fixtures. The round-1 blockers (F1/F2/F5 + majors F4/F6) were the more urgent cognitive blockers for the novice persona. F3 deserves its own scoped batch or round.
- **New commits**: 9d43d6a, 958d85d, 10a3463 (all on origin/main).
- **Test suite**: 791 passed / 2 skipped (no change, no regressions).
- **Frontend**: typecheck clean; build 1.30-1.33s; bundle 803 KB / 259 KB gzip (unchanged modulo string bytes).
- **GitHub sync**: pushed 2026-04-23T01:20 (10a3463 on origin/main; scaffold 09a4975 + 3 remediation commits).
- **Notion sync**: synced 2026-04-23T01:25 — Status=Accepted; 6 page children covering the round-1 arc (fairness correction + 3 remediation batches + deferral rationale + round-2 next-step).

### Round 2 — 2026-04-23T01:15 → T01:30 (remediation landed)
- **Codex exec PID**: 40409 (log `.planning/reviews/pedagogy_round_2_codex.log`)
- **Prompt**: `.planning/reviews/pedagogy_round_2_prompt.md`
- **Findings**: `.planning/reviews/pedagogy_round_2_findings.md` (7.2 KB)
- **Verdict**: CHANGES_REQUIRED · **0 blockers** · 1 major (N1)
  - F1 CLOSED (visual-only FAIL banner removed, matches backend verdict=None)
  - F2 CLOSED (RunResidualsCard tries real PNG first, synthetic labeled 示意图)
  - F5 CLOSED (TFP / plane_channel / impinging_jet / DHC narratives all aligned to gold — per-case cites verified)
  - F4 PARTIAL — naca0012 teaching card cites Re=6e6 + α≈4°, repo truth is Re=3e6 + α=0° (flagged as N1)
  - F6 CLOSED (evidence_ref `<details>` correctly hides reviewer jargon on impinging_jet)
  - F3 DEFERRAL ACCEPTED — codex: "After F1/F2/F4/F5/F6, the frontend Story tab now provides an honest novice teaching path, so the missing Tier-B overlay is backlog, not the thing that should fail this round."
- **Findings addressed** (1 atomic commit):
  - Batch 6 (N1) `196fb94` — rewrote naca0012_airfoil's 4 teaching cards + physics_bullets + why_validation_matters + common_pitfall to match authoritative Re=3e6 + α=0° attached-flow symmetric-airfoil regime. Pulled URF from foam_agent_adapter (p=0.3, U/k/ω=0.5), mesh from gold YAML (blockMesh around OBJ, 80 z-cells, empty y-side), BC from physics_contract precondition #1 (α=0° → U_inlet has no sin α), Cp extraction from precondition #3 (surface_band = max(8·dz_min, 0.02·c) → 30-50% magnitude attenuation is the PASS_WITH_DEVIATIONS rationale).
- **New commits**: 196fb94 (on origin/main).
- **Test suite**: `pytest ui/backend/tests/test_comparison_report_visual_only.py` 10/10 passed (codex's suggested minimum verify).
- **Frontend**: typecheck clean; build 1.33s.
- **GitHub sync**: pushed 2026-04-23T01:30 (196fb94 on origin/main; scaffold + round-1 3 commits + round-1 sync-complete + round-2 remediation).
- **Notion sync**: synced 2026-04-23T01:32 — 5 page children covering N1 problem + batch 6 fix + sanity checks + round-3 next-step.

### Round 3 — TBD
Codex re-review after round-2 N1 remediation. Expected: naca0012 factual fix verified; F3 deferral remains accepted; no new findings; ideal verdict **APPROVE / APPROVE_WITH_COMMENTS** under both personas — closing the pedagogy iteration.

### Round N+1 — template
(Fill after round N codex verdict)

## Exit criteria

- Codex consolidated verdict: **APPROVE** or **APPROVE_WITH_COMMENTS** (only nits) across BOTH personas
- Per-case content: Mesh 策略 + solver setup + BC + 收敛判据 在 Story tab 有教学叙事（≥ 1 paragraph per topic per case 或复用的全局 pedagogy block）
- 真实 contour 云图：reports/<case>/phase5_renders/ 里的 contour_u_magnitude.png 能在 /learn 某个 tab 上访问到，不再被藏起
- Run tab 残差：要么用真实 solver 数据，要么旁边清楚标注 "illustrative only — see /pro for real residuals"
- CFD 全流程 step-by-step 叙事：在 /learn 首页或每 case 内有"从 0 到 1"的导航
- pytest tests/ ui/backend/tests/ 保持绿（≥791 passed）
- npm run typecheck + npm run build 绿
- GitHub: 所有 iteration commits 推到 origin/main
- Notion: DEC-V61-047 row Status=Done with 最终 verdict + codex_tool_report_path

## Sync discipline (per round boundary, same as DEC-V61-046)

1. Local commits
2. `git push origin main`
3. Update DEC frontmatter (verdict / report path / github+notion sync status)
4. Append round block to Round log
5. Notion sync (page children + Status property)
6. Only then launch next round

违反 1→6 顺序（例如 round N+1 在 round N 未推送时启动）会让 DEC 和 code drift —— 双向同步必须在每个 cycle 闭环。
