---
decision_id: DEC-V61-047
title: CFD 教学质量专项 — 每 case 仿真/网格/云图/分析/全流程升级 · 2-persona (expert + novice) 迭代
status: IN_PROGRESS (round 1 codex review pending 2026-04-23T00:45)
commits_in_scope:
  - (none yet — scaffold phase; remediation commits will land per round)
codex_verdict: PENDING (round 1 not yet launched)
autonomous_governance: true
autonomous_governance_counter_v61: 34 (34th +1 entry since RETRO-V61-001 counter reset; next retro trigger at ≥20 arc-size → already past, retro owed)
external_gate_self_estimated_pass_rate: 0.50
codex_tool_report_path: .planning/reviews/pedagogy_round_1_findings.md (pending codex write)
notion_sync_status: synced 2026-04-23T00:50 (page_id=34ac6894-2bed-8186-8028-c1a4aea5d6bf, Status=Proposed, https://www.notion.so/DEC-V61-047-CFD-10-case-2-persona-expert-novice-34ac68942bed81868028c1a4aea5d6bf)
github_sync_status: local-only (scaffold commit pending)
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

### Round 1 — TBD (prompt authoring + codex launch pending)
- **Codex exec PID**: TBD
- **Prompt**: `.planning/reviews/pedagogy_round_1_prompt.md`
- **Findings**: `.planning/reviews/pedagogy_round_1_findings.md` (pending)
- **Verdict**: TBD
- **Findings addressed**: (list with commit sha)
- **Findings deferred**: (list with rationale)
- **New commits**: TBD
- **Test suite**: baseline 791 passed / 2 skipped
- **Notion sync**: pending
- **GitHub sync**: pending

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
