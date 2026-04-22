# DEC-V61-047 Round 1 Findings

Method
- Static code/fixture review only. I did not launch the frontend in a browser in this round, so rendering claims below are inferred from component code, backend report plumbing, and checked fixtures.
- I trusted the shared tab structure recon and verified the repo evidence behind it.

Fairness correction
- The sub-claim "真实仿真流场云图严重不足 / 完全没有真实云图" is no longer fully true. `/learn` now mounts real OpenFOAM `contour_u_magnitude.png` + `residuals.png` in Story via `ScientificComparisonReportSection` for the non-LDC cases, and LDC has the full overlay branch [ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:352-356,1437-1533; ui/backend/services/comparison_report.py:45-61,329-390]. The real problem is that the evidence is under-explained, often status-inconsistent, and only one case has the richer textbook-style overlay.

## LDC
### Persona 1 (expert)
- 🟠 Story still is not textbook-grade because it does not surface the actual reproducibility setup already present in gold YAML: `129x129` mesh, `simpleFoam/SIMPLE`, and explicit lid/no-slip BCs [ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:340-419; knowledge/gold_standards/lid_driven_cavity.yaml:98-113].
- 🟠 `/run` teaches a generic residual-decay picture, not this case's actual residual history; the chart is generated locally in the component and shown under "你大概会看到" [ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:1171-1203].

### Persona 2 (novice)
- 🟡 第一屏能看出“顶盖驱动腔体”，但 `u_centerline velocity profile at x=0.5` 只是一个 token，没有告诉我这条曲线从哪里取、为什么是 `x=0.5`、怎么从场图走到对比曲线 [ui/frontend/src/data/learnCases.ts:40-50; ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:406-413].
- 🟡 我知道有 `Re=100/400/1000`，但页面没有解释为什么当前教学主线盯住 `Re=100`，也没有让我看到真实网格长什么样 [ui/frontend/src/data/learnCases.ts:45-49; ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:903-999].

## Backward-Facing Step
### Persona 1 (expert)
- 🟠 真正关键的工程折中都藏在 gold contract 里，没有变成学生可读的教学叙事：`kEpsilon` 对 DNS 的妥协、`36000` cells authoritative mesh、以及 residual/gate 敏感性 [knowledge/gold_standards/backward_facing_step.yaml:34-43,54-59; ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:340-419].
- 🟠 Mesh tab 把 BFS 网格策略压扁成 `20/40/80/160 cells`，没有教 shear layer / reattachment region 该如何分辨率设计 [ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:62-69,903-999].

### Persona 2 (novice)
- 🔴 `why_validation_matters_zh` 一段里同时塞了 DNS、实验、plateau、tolerance、`2D empty-patch`，更像审计注释，不像教材讲解 [ui/frontend/src/data/learnCases.ts:58-67].
- 🟠 我知道要看 `reattachment_length / step_height`，但页面没有教“回附点在图上怎么看、为什么零速交点就是它” [ui/frontend/src/data/learnCases.ts:59-67; ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:406-413].

## Circular Cylinder Wake
### Persona 1 (expert)
- 🔴 Story visual-only banner 把这个 case 的 `audit_real_run` 写死成 `FAIL`，但真实 fixture 的 `expected_verdict` 是 `PASS`；这是 first-screen status inversion [ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:1500-1507; ui/backend/services/comparison_report.py:372-380; ui/backend/tests/fixtures/runs/circular_cylinder_wake/audit_real_run_measurement.yaml:15-32].
- 🟠 Gold YAML 已经承认 `strouhal_number` 还带 shortcut/silent-pass hazard，但 `/learn` 没有把“频率怎么从真实时间序列量出来”教给学生，只给 contour + residual [knowledge/gold_standards/circular_cylinder_wake.yaml:18-23,34-39; ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:1476-1533].

### Persona 2 (novice)
- 🟠 页面告诉我 `St = fD/U`，但没有任何地方告诉我 `f` 是从什么时间信号量出来的；我只看到一张 contour 和一张 residual [ui/frontend/src/data/learnCases.ts:74-84; ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:1476-1525].
- 🟠 Story 写 FAIL，Compare 默认又优先 `audit_real_run`，我不知道该信哪个 verdict [ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:592-600,1500-1507; ui/backend/tests/fixtures/runs/circular_cylinder_wake/audit_real_run_measurement.yaml:15-32].

## Turbulent Flat Plate
### Persona 1 (expert)
- 🔴 这个 case 仍然被命名为 `Turbulent Flat Plate`，但当前 physics contract 已明确改成 laminar Blasius benchmark；这不是 nuance，是教学主线误标 [ui/frontend/src/data/learnCases.ts:87-100; knowledge/gold_standards/turbulent_flat_plate.yaml:6-20].
- 🟠 页面提到 `y+` 敏感，却没有 surface 出 gold contract 依赖的 wall grading、`delta_99` 分辨率和 extractor 约束 [ui/frontend/src/data/learnCases.ts:100-101; knowledge/gold_standards/turbulent_flat_plate.yaml:21-29; ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:903-999].

### Persona 2 (novice)
- 🔴 我会直接困惑：标题说“湍流平板”，正文又说“湍流假设不成立，要回到 Blasius 层流”。这会让我怀疑整个页面到底在教什么 [ui/frontend/src/data/learnCases.ts:87-101; knowledge/gold_standards/turbulent_flat_plate.yaml:6-20].
- 🟠 `Cf(x)`、`y+`、`Blasius` 都出现了，但没有一张图教我 wall shear 是怎么从边界层里取出来的 [ui/frontend/src/data/learnCases.ts:91-101; ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:406-413,903-999].

## Plane Channel Flow
### Persona 1 (expert)
- 🔴 Story copy 把它讲成 fully developed turbulence / RANS-vs-DNS benchmark，但当前 gold contract 明确写的是 laminar `icoFoam` path and literature-incompatible；第一屏物理叙事自相矛盾 [ui/frontend/src/data/learnCases.ts:104-118; knowledge/gold_standards/plane_channel_flow.yaml:7-26,46-57].
- 🔴 Story visual-only banner 再次把这个 case 写死成 `FAIL`，但真实 fixture 的 `expected_verdict` 是 `PASS`；无论哪一边更 physics-honest，学生看到的都是 split-brain UI [ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:1500-1507; ui/backend/services/comparison_report.py:372-380; ui/backend/tests/fixtures/runs/plane_channel_flow/audit_real_run_measurement.yaml:15-32].

### Persona 2 (novice)
- 🔴 我会同时读到“这是湍流 channel”“用它看 RANS 贴不贴 DNS”“audit_real_run 是 PASS”“physics contract 说根本不兼容”。这不是困难，是信息互相打架 [ui/frontend/src/data/learnCases.ts:104-118; ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:592-600,1500-1507; knowledge/gold_standards/plane_channel_flow.yaml:10-26].
- 🟠 `u+`、`y+`、driving pressure gradient 都没有中文解释，新手只能硬啃术语 [ui/frontend/src/data/learnCases.ts:110-118; ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:406-413].

## Impinging Jet
### Persona 1 (expert)
- 🔴 页面把它教成 canonical axisymmetric jet benchmark，但当前 contract 明确说明 adapter 实际是 2D planar slice，不是 wedge，而且 solver 还 under-converged；这是 case-definition mismatch [ui/frontend/src/data/learnCases.ts:121-135; knowledge/gold_standards/impinging_jet.yaml:8-27,41-46].
- 🟠 这个 case 真正需要讲清的 solver/turbulence/geometry 问题是 `axis/wedge`, `p_rgh` convergence, `kEpsilon` partial，但 Story 只给 contract prose + contour/residual，没有 `Nu(r/D)` 提取流程 [knowledge/gold_standards/impinging_jet.yaml:15-23; ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:1476-1533].

### Persona 2 (novice)
- 🔴 PhysicsContractPanel 直接把 `empty`, `wedge`, `A4 solver_iteration_cap`, `kEpsilon` 这类 reviewer-grade 证据扔在学生 UI 里，没有翻译层 [ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:505-529; knowledge/gold_standards/impinging_jet.yaml:12-23].
- 🟠 我知道要看 `Nu(r)`，但页面没有告诉我驻点 Nu 为什么最高、半径曲线是怎么从壁面热流算出来的 [ui/frontend/src/data/learnCases.ts:125-135; ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:406-413,1476-1525].

## NACA 0012 Airfoil
### Persona 1 (expert)
- 🟠 Gold contract 里已经有真实 solver setup (`simpleFoam + kOmegaSST`, URF, near-surface sampling caveat)，但 Story 没把这些变成学生可用的教学卡片 [knowledge/gold_standards/naca0012_airfoil.yaml:5-28; ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:340-419].
- 🟠 页面提醒 far-field 不能太近，却没有任何 BC/mesh card 展示外边界距离、wall treatment、或为什么 Cp 取样是 near-surface band 而不是 exact surface [ui/frontend/src/data/learnCases.ts:146-152; knowledge/gold_standards/naca0012_airfoil.yaml:6-10,21-27].

### Persona 2 (novice)
- 🟠 `Cp distribution along chord` 只是一个 token；我没有被教会怎样读 upper/lower surface 压强，也不知道“cell-average vs exact surface”为什么会改变曲线 [ui/frontend/src/data/learnCases.ts:142-152; ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:406-413; knowledge/gold_standards/naca0012_airfoil.yaml:24-27].
- 🟠 我听到了“远场边界不能太近”，但 UI 没有任何一张网格/边界图把这件事画出来 [ui/frontend/src/data/learnCases.ts:152; ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:903-999].

## Rayleigh-Benard Convection
### Persona 1 (expert)
- 🟠 Story 把这个 case 讲成 `Nu ~ Ra^alpha` 标度问题，但当前 gold contract 实际上只是一个 `Ra=1e6, Nu≈10.5` benchmark point；叙事 scope 超过了实现 scope [ui/frontend/src/data/learnCases.ts:155-169; knowledge/gold_standards/rayleigh_benard_convection.yaml:5-22].
- 🟠 作为 9 个 visual-only case 之一，它有真实 contour/residual，但没有 Story-side gold-overlay / metrics / GCI context [ui/backend/services/comparison_report.py:45-50,372-390; ui/backend/tests/test_comparison_report_visual_only.py:74-82].

### Persona 2 (novice)
- 🟠 我会以为这里要学“标度率 `alpha` 怎么测”，但页面没有从温度场走到 `Nu(Ra)` 提取的步骤 [ui/frontend/src/data/learnCases.ts:159-168; ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:1476-1525].
- 🟠 `Boussinesq` 被提到但没有解释；这已经足够打断新手理解链 [ui/frontend/src/data/learnCases.ts:169].

## Differential Heated Cavity
### Persona 1 (expert)
- 🔴 Student-facing narrative is stale relative to the actual benchmark. Story 仍在讲已被退役的高 `Ra=1e10` 不可分辨故事，但 gold contract 已经明确降到 `Ra=1e6`，就是为了让 case physically honest and teachable [ui/frontend/src/data/learnCases.ts:176-186; knowledge/gold_standards/differential_heated_cavity.yaml:7-26].
- 🟠 由于 narrative 还停留在高 `Ra`，学生没有真正学到当前 UI 在验证的 solver/mesh regime [ui/frontend/src/data/learnCases.ts:176-186; knowledge/gold_standards/differential_heated_cavity.yaml:18-25].

### Persona 2 (novice)
- 🔴 我会带着“这个 case 就是 `Ra=10^10`、必须千层网格”的错误印象离开页面，但当前 repo 真正在教的是 `Ra=10^6` de Vahl Davis benchmark [ui/frontend/src/data/learnCases.ts:181-186; knowledge/gold_standards/differential_heated_cavity.yaml:7-26].
- 🟠 页面没有把“为什么这次降到 `Ra=10^6` 反而更像教科书”说清楚 [knowledge/gold_standards/differential_heated_cavity.yaml:18-25; ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:390-401].

## Duct Flow
### Persona 1 (expert)
- 🟠 Story 在讲角区二次流和非线性湍流模型，但 student-facing evidence 还是 Darcy `f` + `|U|` contour；现象与观测量没有被接起来 [ui/frontend/src/data/learnCases.ts:193-203; ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:1476-1525].
- 🟠 页面没有教这条 case 最重要的 honesty pivot：它是 duct 不是 pipe；这个修正只在 gold file 里 [knowledge/gold_standards/duct_flow.yaml:11-20,22-48; ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:340-419].

### Persona 2 (novice)
- 🟠 我被告知“角区二次流很重要”，但在 `/learn` 里既看不到二次流图，也看不到它如何影响 Darcy `f`，故事和证据断开了 [ui/frontend/src/data/learnCases.ts:193-203; ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:1476-1525].
- 🟡 `Darcy friction factor f` 也没有中文解释，只有一个 observable token [ui/frontend/src/data/learnCases.ts:195-203; ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:406-413].

## Global findings
- F1 🔴 Hardcoded FAIL banner on Story visual-only branch — `LearnCaseDetailPage` unconditionally says the case's `audit_real_run` verdict is `FAIL`, but visual-only backend context returns `verdict=None`, and at least `plane_channel_flow` / `circular_cylinder_wake` fixtures are explicitly `expected_verdict: PASS` [ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:1490-1507; ui/backend/services/comparison_report.py:372-390; ui/backend/tests/fixtures/runs/plane_channel_flow/audit_real_run_measurement.yaml:15-32; ui/backend/tests/fixtures/runs/circular_cylinder_wake/audit_real_run_measurement.yaml:15-32] — raised by expert + novice — remediation: derive status honestly from `ValidationReport` / actual run fixture, or remove verdict copy entirely in visual-only mode.
- F2 🔴 Synthetic residual pedagogy on `/run` — Run tab shows a locally synthesized SVG decay curve under "你大概会看到"; the code comment admits it is a "hint like a real simpleFoam log", but the student UI does not clearly mark it as synthetic [ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:1171-1203] — raised by expert + novice — remediation: replace with per-case real residual PNG when available, or add an explicit `示意图 / not real solver trace` badge and keep the real residual below it.
- F3 🟠 9/10 cases are still Tier-C visual-only, not textbook walkthroughs — only `lid_driven_cavity` is in `_GOLD_OVERLAY_CASES`; the other 9 cases intentionally skip gold overlay, verdict, metrics, paper, GCI, and grid-convergence context in the comparison-report service [ui/backend/services/comparison_report.py:45-61,329-390; ui/backend/tests/test_comparison_report_visual_only.py:74-82] — raised by expert + novice — remediation: upgrade the 9 visual-only cases to a minimal teaching report: real field, how to read it, how the observable is extracted, and why the run passes/fails.
- F4 🟠 Story/Mesh omit the reproducibility path even though the repo already has it — Story only renders physics bullets, reference art, pitfall, observable, and reference; Mesh only renders measurement-vs-mesh slider + generic Richardson note. The concrete solver, mesh, BC, and scheme choices already exist in gold YAML but are not surfaced as student teaching content [ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:340-419,843-999; knowledge/gold_standards/lid_driven_cavity.yaml:98-113; knowledge/gold_standards/backward_facing_step.yaml:34-59; knowledge/gold_standards/naca0012_airfoil.yaml:5-28] — raised by expert primarily, novice secondarily — remediation: add per-case cards for geometry/BC, mesh strategy, solver/model/schemes, and observable extraction.
- F5 🔴 Several case narratives are materially out of sync with current physics contracts — `turbulent_flat_plate` is still branded turbulent after laminar Blasius correction; `plane_channel_flow` still sells a turbulent benchmark while the gold contract says laminar `icoFoam` is incompatible; `impinging_jet` still reads as canonical axisymmetric while the contract says planar slice + under-converged; `differential_heated_cavity` story still teaches retired `Ra=1e10` while gold is now `Ra=1e6` [ui/frontend/src/data/learnCases.ts:87-118,121-135,176-186; knowledge/gold_standards/turbulent_flat_plate.yaml:6-20; knowledge/gold_standards/plane_channel_flow.yaml:7-26; knowledge/gold_standards/impinging_jet.yaml:8-27; knowledge/gold_standards/differential_heated_cavity.yaml:7-26] — raised by expert + novice — remediation: rewrite the case copy to match the current benchmark truth before adding more polish.
- F6 🟠 PhysicsContractPanel is reviewer-grade, not student-grade — the component prints raw `evidence_ref` strings from YAML directly into the student UI, including file paths, adapter jargon, and attestor codes [ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:505-529; knowledge/gold_standards/impinging_jet.yaml:12-23] — raised mostly by novice — remediation: keep raw evidence collapsible, but add a plain-Chinese one-sentence teaching summary per precondition.

## Consolidated verdict
The user's concern is substantially valid. One point needs correction: `/learn` is no longer missing real OpenFOAM field evidence altogether. The deeper problem is that the evidence is inconsistently narrated, sometimes mislabeled, and rarely turned into a novice-usable CFD workflow.

**Overall**: CHANGES_REQUIRED  
**Blockers**: 4  
**Expert verdict**: CHANGES_REQUIRED  
**Novice verdict**: CHANGES_REQUIRED

## Round-2 directive
1. Fix the Story visual-only branch so it does not hardcode `FAIL`; derive the displayed status from the actual `ValidationReport` / run fixture, or remove verdict text entirely in visual-only mode [ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:1490-1507; ui/backend/services/comparison_report.py:372-390].
2. Replace the synthetic `/run` residual preview with real per-case residual artifacts when available; if the synthetic preview must stay, label it explicitly as synthetic and subordinate it to the real residual plot [ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:1171-1203].
3. Rewrite the stale case copy for `turbulent_flat_plate`, `plane_channel_flow`, `impinging_jet`, and `differential_heated_cavity` so the first-screen teaching narrative matches today's physics contracts and benchmark regimes [ui/frontend/src/data/learnCases.ts:87-118,121-135,176-186].
4. Add student-facing cards for `geometry/BC`, `mesh strategy`, `solver/model/schemes`, and `observable extraction` by reusing the existing gold YAML fields instead of forcing students into raw contract prose [ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:340-419,843-999; knowledge/gold_standards/lid_driven_cavity.yaml:98-113; knowledge/gold_standards/backward_facing_step.yaml:34-59; knowledge/gold_standards/naca0012_airfoil.yaml:5-28].
5. Promote the remaining 9 visual-only cases from Tier C to a minimal teaching report that connects real field evidence to the benchmark observable and the pass/fail logic, rather than showing only contour + residual + literature art [ui/backend/services/comparison_report.py:45-61,329-390; ui/backend/tests/test_comparison_report_visual_only.py:74-82].
6. Keep `PhysicsContractPanel` honest, but split it into a student summary and an expandable raw evidence block so source paths / attestor jargon stop front-running the lesson [ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx:505-529].
