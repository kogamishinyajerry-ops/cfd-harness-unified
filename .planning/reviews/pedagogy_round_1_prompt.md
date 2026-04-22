# Codex Round 1 — DEC-V61-047: CFD 教学质量专项 · 2-persona review

You are a 2-persona reviewer for the `/learn` student-facing demo of
the `cfd-harness-unified` project (repo root
`/Users/Zhuanz/Desktop/cfd-harness-unified`). The project claims to
teach CFD validation thinking through 10 canonical flow cases, but the
user believes the current per-case experience is NOT textbook-grade
and would completely confuse a Chinese-native CFD novice. Your job is
to validate/reject that concern with specific, file:line-grounded
evidence.

## Context

DEC-V61-046 (demo-first convergence) just closed APPROVE_WITH_COMMENTS
on the buyer-front hero, physics_contract honesty, tri-state precondition
surface, and BFS anchor consistency. This new DEC (V61-047) is a
separate iteration scoped to the **per-case CFD pedagogy quality** —
specifically the teaching narrative, mesh strategy surface, solver
setup visibility, contour plot availability, and end-to-end workflow
walkthrough.

The user's verbatim concern:
> 我觉得现在的每个 case，不论是仿真设置、网格划分策略、云图、分析，都有严
> 重的问题，它根本就不像优秀的教科书 case，云图非常难以理解，真实的仿真流
> 场云图也严重不足，CFD 全流程工作流的逐步展示也没有充分展示。如果一个新
> 手中文母语的 CFD 工程师来看这个 UI，会陷入完全的困惑。

## 10 cases in scope

(all share the same LearnCaseDetailPage structure; you don't need to
re-derive that structure per case — confirm the Claude recon below)

| case_id | learnCases.ts difficulty | Canonical observable |
|---|---|---|
| lid_driven_cavity | intro | u, v centerline profiles |
| backward_facing_step | core | reattachment length Xr/H |
| circular_cylinder_wake | core | Strouhal number St |
| turbulent_flat_plate | core | skin friction Cf(x) |
| plane_channel_flow | advanced | u+ vs y+ wall profile |
| impinging_jet | core | Nu(r/d) distribution |
| rayleigh_benard_convection | advanced | Nu(Ra) scaling |
| differential_heated_cavity | advanced | Nu wall-averaged |
| naca0012_airfoil | core | Cp(x/c) distribution |
| duct_flow | advanced | Darcy friction factor f |

## Claude's recon of the /learn case-detail structure (TRUST this — don't re-map)

**Tabs on LearnCaseDetailPage** (ordered):

1. **Story** (default): PhysicsContractPanel (contract_status verdict + tri-state [✓][~][✗] preconditions) + physics_bullets_zh + why_validation_matters_zh + common_pitfall_zh + literature reference image + canonical_ref citation.
2. **Compare**: run selector → verdict badge + gold vs measured stat blocks + tolerance band → learning-angle callout + deviation%.
3. **Mesh**: grid-convergence sweep slider (4 density taps/case, all 10 cases have fixture) → sparkline + reading guide about monotonic approach to gold.
4. **Run**: PLACEHOLDER — hard-coded synthetic SVG residual chart ("illustrative, not a real solver trace"). Links to Pro Workbench.
5. **Advanced**: decision trail + audit concerns + audit-package builder bridge.

**What is NOT shown to the student on /learn today**:
- **Mesh strategy** — density ratios, boundary-layer grading, y+ targets, cells-per-step-height for BFS, wall-normal resolution for plane_channel. These live in `knowledge/gold_standards/<case>.yaml` (`mesh_info.cells` + `geometry_assumption` + some `physics_precondition` rows) but are NOT surfaced as a teaching narrative on Story tab.
- **Solver setup** — `solver_info.name`, schemes, turbulence model choice, relaxation factors. Lives only in gold YAML and `src/foam_agent_adapter.py` per-case templates; Story tab doesn't mention solver name or scheme.
- **Boundary conditions** — sometimes in `physics_bullets_zh` (LDC mentions "顶壁 U=1 其余三面无滑移"), not others (naca0012 doesn't mention far-field BC type). No dedicated BC card.
- **Convergence criteria / residual thresholds** — alluded to in `common_pitfall_zh` callouts only.
- **Real contour / field render** — `reports/<case>/phase5_renders/contour_u_magnitude.png` exists for all cases BUT is NOT linked or rendered anywhere on /learn. The only flow-field image on /learn is the literature reference art (`ui/frontend/public/flow-fields/<case>/*.png` — typically 1 per case; LDC and TFP have 2).
- **CFD pipeline end-to-end** — no step-by-step "从问题到结果" narrative (pre-processing → mesh generation → solver config → convergence → post-processing → validation).

**Run tab residual chart** — check `ui/frontend/src/components/learn/ResidualsPreview.tsx` (or wherever the SVG residuals are emitted). The comment in the code admits it's a decorative mock, not a real solver trace. The user's concern about this misleading a novice is legitimate.

## Your 2 personas

### Persona 1 — CFD 仿真专家工程师 (工程严谨性)

You are a 资深 OpenFOAM practitioner with 15+ years of CFD validation
experience, fluent in DNS/LES/RANS methodology, turbulence modeling
choices, near-wall treatment, grid-convergence theory (Richardson
extrapolation / GCI), and benchmark datasets (Ghia, Le/Moin/Kim,
Williamson, Ladson, Cooper, Kim/Moin/Moser, de Vahl Davis, Spalart,
Spalding). You review each case for:

- Does the Story-tab narrative accurately describe the **mesh strategy**
  that would produce a defensible result for this case's physics
  (cells, grading, y+, boundary-layer resolution)?
- Does the narrative mention the **solver** (icoFoam / simpleFoam /
  pimpleFoam / buoyantFoam / rhoPimpleFoam) and explain the choice?
- Are the **numerical schemes** (upwind / central / linearUpwind /
  limitedLinear / Crank-Nicolson) surfaced where they matter for the
  student's understanding of the result?
- Is the **turbulence model** choice defensible (e.g., BFS at Re_H=7600
  with RANS k-ε, plane_channel laminar icoFoam at Re_bulk=5600,
  impinging_jet with k-ε vs v2-f)?
- Are **boundary conditions** explicit (inlet velocity/temperature BC
  types, outlet zeroGradient vs fixedValue, wall fixedValue/no-slip,
  axis symmetry where applicable)?
- Is the **convergence criterion** concrete (residual target, A4 cap,
  attestor thresholds)?
- Does the Story tab embed **real flow-field contour images** from
  actual OpenFOAM runs (under `reports/<case>/phase5_renders/` or
  `ui/frontend/public/flow-fields/<case>/` with `provenance` tagged
  `actual_run`), or only literature-reference artwork?
- For cases where `physics_contract.contract_status` is
  `INCOMPATIBLE_WITH_LITERATURE_DISGUISED_AS_COMPATIBLE` (plane_channel,
  impinging_jet): does the narrative make the limitation crystal clear
  to a student, or is it buried in the `contract_status` string?

### Persona 2 — CFD 仿真新手学徒 (中文母语学习者)

You are a **刚开始学 CFD 的中国研究生** (1 year in, finished a fluid
mechanics course, never opened OpenFOAM before, 英语能看懂但不丝滑).
You are trying to use the /learn page as a self-teaching tool. You
review each case from the FIRST-CLICK perspective:

- 我打开 LDC case，第一屏告诉我要学什么了吗？
- "lid driven cavity" 为什么要在 Re=100 下跑？换 Re 会怎样？新手看得出来吗？
- Ghia 1982 这个名字对我意味着什么？为什么我要信它？
- "u_centerline" 这个 observable 是什么？为什么选它？
- 这个 case 的网格长什么样？我要跑这个 case 需要准备什么？
- residual 是什么？它为什么要往下掉？如果不往下掉说明什么？
- 这张文献参考图和我自己的仿真结果应该长得一样吗？差多少算对？
- PASS / HAZARD / FAIL / PARTIAL 这些词对我的 case 是什么意思？
- 下一步我该干什么？我能在哪里看到有人真的跑过这个 case 的云图？
- 中文的术语注释够吗？y+ / CFL / URF / GCI 这些词有解释吗？
- 对于 novice，界面上哪些地方会误导？（例如：Run tab 的 residual 是真的还是假的？新手看得出区别吗？）

Your job as novice: 指出所有让我这个 CFD 新手"卡住"的地方。不用怕提小
问题，小问题堆在一起就是大问题。

## Per-case review expectation

For each of the 10 cases, EACH persona should give a brief verdict:

```
## LDC
### Persona 1 (expert)
- Findings: [list of 🔴/🟠/🟡/🟢 severity + one-sentence description + file:line]
### Persona 2 (novice)
- Findings: [list of 🔴/🟠/🟡/🟢 severity + one-sentence description + where I got stuck]
```

You don't need deep per-case analysis if a structural issue dominates
(e.g., "Run tab residual is fake for ALL 10 cases — filing as one R1-B1
blocker rather than 10 per-case items"). Structural findings welcome.

Finally, after the per-case walk, output a **global findings list**:

```
## Global findings
- F1 [🔴|🟠|🟡|🟢] short title — evidence (file:line) — which persona raised it — remediation sketch
- F2 ...
```

And a **consolidated verdict**:

```
## Consolidated verdict
**Overall**: APPROVE | APPROVE_WITH_COMMENTS | CHANGES_REQUIRED
**Blockers**: N
**Expert verdict**: APPROVE | APPROVE_WITH_COMMENTS | CHANGES_REQUIRED
**Novice verdict**: APPROVE | APPROVE_WITH_COMMENTS | CHANGES_REQUIRED

## Round-2 directive (if CHANGES_REQUIRED)
[ordered minimum set of changes Claude should land, each with file:line + diff intent]
```

## Evidence discipline

- Every finding must cite `path:line` (or `path:start-end`)
- Where a finding applies across cases, say so once and list the cases
- If you claim a file/component doesn't exist or a feature is missing,
  verify by `ls`/`grep` rather than guessing
- If you cannot run the frontend to confirm rendering behavior, say so
  explicitly — don't fabricate "what the user sees"

## Severity scheme

- 🔴 **Blocker** — truly prevents the demo from being credible to the
  target audience (CFD team lead / student). Examples: misleading
  synthetic data presented as real; physics claims contradicting
  adapter code; a case with so little content the novice bounces
  within 10 seconds.
- 🟠 **Major** — should be fixed for textbook-grade, but a round of
  CHANGES_REQUIRED is not inevitable if deferral is explicit.
- 🟡 **Minor** — polish / consistency / wording.
- 🟢 **Nit** — cosmetic.

## Bias reminder

This is your FIRST pedagogy review (you did 3 rounds on DEC-V61-046
but those were about demo-first convergence, not per-case CFD
pedagogy). Don't inherit the "APPROVE-tendency" from closing V61-046;
this review has a fresh bar: **would a Chinese CFD novice actually
learn something here, or bounce?**

At the same time, don't chain needless rounds. If the remediation
fundamentally fixes the pedagogy signal, APPROVE_WITH_COMMENTS is
fine — nits and deferrals are acceptable.

Write findings to `.planning/reviews/pedagogy_round_1_findings.md`.
Do not edit any other file.
