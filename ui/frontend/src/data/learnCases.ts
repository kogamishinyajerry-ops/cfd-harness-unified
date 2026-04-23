// Student-facing learning metadata — a narrative layer on top of the
// backend's authoritative whitelist + gold_standard records.
//
// Ordering in the catalog is pedagogical (easy → hard, not alphabetical).
// Every case_id MUST exist in knowledge/whitelist.yaml or the detail
// route will 404 when it tries to fetch /api/cases/:id.

import { LDC_REPRODUCTION_BUNDLE, type ReproductionBundle } from "./reproductionBundles/lidDrivenCavity";

export interface LearnCase {
  id: string;
  // Name shown in catalog cards (kept terse). Detail header uses the real
  // name from the backend CaseDetail.name to avoid drift.
  displayName: string;
  // Chinese headline — primary. 3-6 chars, like a book chapter title.
  headline_zh: string;
  // English subhead — secondary (one line under the headline).
  headline_en: string;
  // 1-sentence teaser shown on the catalog card (Chinese).
  teaser_zh: string;
  // Canonical historical reference. Used as a trust anchor on the card
  // (a citation reads better than a raw ref_value number).
  canonical_ref: string;
  // Which canonical observable this case measures.
  observable: string;
  // Difficulty for beginner routing — affects card border hint only.
  difficulty: "intro" | "core" | "advanced";
  // The physics the student will encounter (2-4 bullet items, Chinese).
  physics_bullets_zh: string[];
  // What the validation produces — 1 paragraph narrative (Chinese).
  why_validation_matters_zh: string;
  // Common pitfall for students — highlighted in a callout (Chinese).
  common_pitfall_zh: string;

  // ===== DEC-V61-047 round-1 F4 teaching cards ==========================
  // Four short pedagogical paragraphs that surface the reproducibility
  // path (solver / mesh / BC / observable-extraction) directly on the
  // Story tab, so a novice does not need to open gold YAML or Pro
  // Workbench to understand how this case is actually set up and run.
  // DEC-V61-048 batch 2 (planned): bodies will expand from 2-4 sentences
  // to 5-8 sentences with 4 structured slots (why-this-choice /
  // main-alternative / when-it-breaks / what-to-inspect).
  // ======================================================================
  solver_setup_zh: string;
  mesh_strategy_zh: string;
  boundary_conditions_zh: string;
  observable_extraction_zh: string;

  // ===== DEC-V61-048 round-1 batch 1 (A) benchmark lineage ==============
  // Codex deep-dive: every case今 only carries a single `canonical_ref`
  // citation string, with no narrative of "why this paper, not another"
  // or "what to read next". For graduate-course reading value, each case
  // needs a benchmark lineage block so the student can (1) understand
  // why the chosen paper is the teaching anchor, (2) discover parallel
  // or competing benchmarks, (3) know the next paper to read after
  // finishing this case.
  // Schema:
  //   why_primary: 2-4 sentence Chinese explanation of why THIS paper
  //                was chosen as the harness's gold anchor — not just
  //                repeating author names, but explaining the author's
  //                contribution and why it is the teaching pivot.
  //   secondary: 1-4 parallel or competing benchmark citations — each
  //              one is a short Chinese string "author year · usage"
  //              pointing the reader at complementary literature.
  //   next_reading: 2-3 sentence Chinese explanation of what to read
  //                 after finishing this case — specific paper / book
  //                 chapter / review pointer.
  // ======================================================================
  benchmark_lineage_zh: {
    why_primary: string;
    secondary: string[];
    next_reading: string;
  };

  // ===== DEC-V61-048 round-1 batch 3 (B) reproducibility + diagnostics ==
  // Codex deep-dive D-axis: every case lacked a "from zero" pipeline
  // walk — what OpenFOAM commands to run, in what order, with what
  // expected artifact per step. F-axis: every case also lacked a
  // troubleshooting checklist showing symptom → likely cause → fix so
  // students can diagnose their own run when it diverges. Without these
  // the page is a description of a result, not a chapter the student
  // can follow.
  // Schema:
  //   workflow_steps_zh: ordered array of {step, command?, detail}.
  //     Each step is one line of a reproducibility runbook. command is
  //     the literal OpenFOAM or shell command (optional — some steps
  //     are "edit this file" not "run this utility"). detail is 1-3
  //     sentences of Chinese explaining what happens and what to
  //     inspect after that step.
  //   troubleshooting_zh: array of {symptom, likely_cause, fix} triples
  //     covering the 4-6 highest-likelihood failure modes for this
  //     specific case. Ordered by likelihood (most common first).
  // ======================================================================
  workflow_steps_zh: {
    step: string;
    command?: string;
    detail: string;
  }[];
  troubleshooting_zh: {
    symptom: string;
    likely_cause: string;
    fix: string;
  }[];

  // ===== DEC-V61-049 pilot batch B (reproduction bundle) ================
  // Codex CFD-novice walk Step 2 findings: workflow_steps_zh told the
  // student "edit system/blockMeshDict" without providing its contents,
  // and the prose claimed patch/URF/nu values that drifted from the
  // generator. Without complete dictionary text a novice cannot
  // reproduce the run from the page alone. Bundle exposes the 8 core
  // OpenFOAM files (plus optional sampleDict) byte-for-byte matching
  // src/foam_agent_adapter.py:_generate_lid_driven_cavity. Optional
  // field, populated only for LDC in the V61-049 pilot; other cases
  // will receive their own bundles if the pattern rolls.
  // ======================================================================
  reproduction_bundle_zh?: ReproductionBundle;

  // ===== DEC-V61-048 round-1 batch 4 (flagship deep-dive) ===============
  // Codex deep-dive B-axis (physical intuition) + regime transitions:
  // even with lineage + teaching cards + runbook, the 3 lowest-scoring
  // cases (LDC, RBC, duct) still lack "what does this flow actually look
  // like if you stood inside it, and how does it change across regimes"
  // narrative. Optional field populated only for flagship cases — other
  // 7 cases already carry enough description in the other blocks.
  // Schema:
  //   physics_intuition_zh: 2-4 paragraph Chinese prose describing (1)
  //     the mental model / visual anchor for the flow, (2) regime
  //     transitions with specific control parameter thresholds, and (3)
  //     the unique pedagogy value this case carries that the student
  //     cannot get from the other 9 cases.
  // ======================================================================
  physics_intuition_zh?: string;
}

export const LEARN_CASES: LearnCase[] = [
  {
    id: "lid_driven_cavity",
    displayName: "Lid-Driven Cavity",
    headline_zh: `经典起点`,
    headline_en: "Where CFD began",
    teaser_zh: `正方形腔体、顶盖拖动、里面形成稳态涡。几乎每一本 CFD 教材的第一个算例。`,
    canonical_ref: "Ghia, Ghia & Shin · 1982",
    observable: "u_centerline velocity profile at x=0.5",
    difficulty: "intro",
    physics_bullets_zh: [
      `二维稳态不可压缩 Navier-Stokes`,
      `顶壁速度 U=1，其余三面无滑移`,
      `Re = UL/ν，典型 Re=100 / 400 / 1000`,
    ],
    why_validation_matters_zh: `Ghia 1982 给出的 129×129 网格数据是这个问题的黄金标准，后来几乎每一个 CFD 代码入门都会跑它。你算的中心线速度剖面能不能对齐 Ghia 的表格，决定了你"第一次 CFD"这一关有没有过。`,
    physics_intuition_zh: `站在腔体里看这个流动：头顶是一块以 U=1 向右匀速拖动的盖子，另外三面静止的墙把你圈住。盖子黏住紧贴它的那层流体，把它们也拖向右；这层流体又粘连下面的流体，一层层传下去——但左墙和底墙又拦着不让右行，流体只能在腔体里打转。于是形成一个占据腔体大部分体积的顺时针大主涡 (primary vortex)，它的中心在 Re=100 时大约在 (0.62, 0.74)——偏右偏上，因为顶盖把能量输入集中在右上角。右下角和左下角会看到两个反向转动的小二级涡 (secondary vortices)，它们是主涡下洗流撞到底墙后被迫反转产生的——这两个小涡的大小和清晰程度是"你的代码和网格够不够细"的 litmus test，粗网格会把它们抹平。\n\n当你把 Re 从 100 推到 400、1000、5000，这个流场逐渐演化：Re=400 主涡中心移到 (0.55, 0.61) 更向腔体几何中心靠；Re=1000 主涡拖成椭圆、二级涡变大并出现**三级涡**在左下角内部嵌套；Re=5000 以后 2D 稳态解开始变得物理不稳定，真正的 3D 实验会看到沿深度方向的 Taylor-Görtler 螺旋涡（2D 模拟看不到，这是 2D 理想化的边界）；Re≈10000 附近流动进入弱湍流 regime，稳态解仍然数学存在但实验里看到的是时均场，瞬时场已是涡脱 + chaos。本 case 跑 Re=100 深意在此：它是 2D 稳态 laminar 假设**完全正确**的少数几个 Re 之一，你看到的网格独立解就是真解。\n\n这个问题最深的教学点不是"顶盖拖流体"这么简单，而是它是整个 CFD 验证文化的起点——Burggraf 1966 第一次用流函数-涡量公式在 Re=400 证明数值 N-S 可解，Ghia 1982 用 multigrid + FMG 第一次把 Re=10000 压到完全收敛，这两次工作定义了 "benchmark" 这个词在计算流体力学里的含义：不只是一个数字，而是一整套（几何 + BC + observable + 容差）可被下一代代码重复验证的协议。你在这里学的不是腔体流动本身，是"如何可信地主张一个代码算对了"这套方法论。`,
    common_pitfall_zh: `角点处的速度奇异性（顶角 U=1、侧壁 U=0 同一个点）会让发散。本仓库 generator 在 fvSolution 的 SIMPLE 块里写 residualControl {p 1e-5; U 1e-5;} — 到 1e-5 会自动停。**report-grade 验证必须达到 1e-5 基线**；探索阶段把判据放宽到 1e-3 是可以的但必须显式标 non-validation run，不能把一个 stall 在 1e-3 的解当 "收敛" 提交报告。网格加密 + 接受角点 Gibbs-type overshoot 是更诚实的路径。`,
    solver_setup_zh: `<strong>Why this choice</strong>: simpleFoam (稳态 SIMPLE) + constant/momentumTransport::simulationType=laminar（OpenFOAM 10；OF<=9 里对应的是 turbulenceProperties/RASModel=laminar）。SIMPLE 用 pressure-correction 迭代耦合动量和连续性方程，每步松弛更新 U 和 p；本仓库 generator 实际写 <strong>U=0.9, p=0.3</strong> 并打开 SIMPLE::consistent=yes（SIMPLEC 变种更稳），配 residualControl { p 1e-5; U 1e-5; } 在达到时自动停。Re=100 层流腔体流本质稳态，用稳态 solver 比瞬态更直接、更省算力。<strong>Main alternative</strong>: pimpleFoam (瞬态 PIMPLE) 可以跑时间推进直到 d/dt≈0，但对 Re=100 纯粹浪费——唯一合理用瞬态的情况是 Re≥5000 时涡脱开始非稳态。<strong>When it breaks</strong>: URF 调太激进（p>0.5）会让 pressure 震荡不收敛；调太保守（p<0.1）会跑几千步才够深。<strong>What to inspect</strong>: system/controlDict 的 endTime（SIMPLE 里是 iteration count），system/fvSolution 的 p solver（GAMG + tolerance=1e-6 + relTol=0.1）和 relaxationFactors（U=0.9 field、p=0.3 field），system/fvSchemes 的 div(phi,U) = <code>bounded Gauss limitedLinearV 1</code>（本仓库实际写法，不是 linearUpwind——早期 commit 里 prose 对不上 generator 的 drift，当前已对齐）。`,
    mesh_strategy_zh: `<strong>Why this choice</strong>: blockMesh 生成结构化均匀方格网格。**本仓库 audit 路径 = 129×129×1 (16641 cells)** — 直接对齐 Ghia 1982 的 benchmark 网格，blockMeshDict 首行 <code>convertToMeters 0.1</code>（物理 domain 0.1m × 0.1m，不是单位方腔），生成时 nCells 日志 = 16641。Mesh tab 的 convergence sweep 额外跑 mesh_20 / 40 / 80 / 160 (400~25600 cells) 作为网格独立性 evidence；**teaching-quick 20×20 / 40×40 不得用于最终验证报告**，它们只用于 "< 10 秒跑完看看流场大致对不对" 的探索。<strong>Main alternative</strong>: O-grid / C-grid 对腔体没有好处（几何是直角方腔，uniform 最省心）；边界层 graduation 在 Re=100 可以省（边界层相对腔尺度不薄）。如需 scan Re→1000 则要 grading（角点速度梯度变陡）。<strong>When it breaks</strong>: 网格太粗（<65² cells）会抹掉二级涡 + 把主涡中心拖向几何中心；Ghia 的 primary_vortex_location=(0.6172, 0.7344) 被你拖偏 5% 以上就是这个症状。<strong>What to inspect</strong>: blockMesh log 末尾的 nCells；Mesh tab 的 convergence sweep 应显示 u_centerline L2 deviation 从 mesh_20 单调降到 mesh_160 且 <1%——这是 Richardson extrapolation 的 visual 验证。`,
    boundary_conditions_zh: `<strong>Why this choice</strong>: 四面 BC 的对称性很重要。**本仓库 generator 的 patch 名是 <code>lid / wall1 / wall2 / bottom / frontAndBack</code>**（不是常见教材里的 movingWall/fixedWalls）：<code>lid</code>（顶）fixedValue U=(1,0,0)，是问题的唯一 momentum source；<code>wall1 / wall2 / bottom</code>（左/右/底）fixedValue U=(0,0,0) no-slip 把动量传到内部流体；<code>frontAndBack</code> empty 伪 2D。所有 wall 的 p 都是 zeroGradient。压力在 <code>fvSolution::SIMPLE { pRefCell 0; pRefValue 0; }</code> 锚定（不是独立 referencePressure block）——不可压 N-S 里只有 pressure gradient 有意义，绝对值要锚定。<strong>Main alternative</strong>: 用 cyclic 周期 BC 做无限长 cavity → 变成 Couette flow (完全不同的问题)；lid 换成 slip wall → 没有 lid-driven momentum，流体纹丝不动。<strong>When it breaks</strong>: 漏掉 pRefCell/pRefValue 导致 p 漂移不收敛；lid patch type 写成 patch 而非 wall，OpenFOAM 会在 0/U 上报 "fixedValue not allowed"；顶角（U=1 和侧壁 U=0 同一个点）是数学奇点，但 OpenFOAM cell-center 值不落在角上，物理上是 paper-thin discontinuity。<strong>What to inspect</strong>: constant/polyMesh/boundary 里 5 个 patch 的 type（lid/wall1/wall2/bottom 都是 wall，frontAndBack 是 empty），0/U 和 0/p 里每个 patch 写法一致，fvSolution::SIMPLE 块的 pRefCell/pRefValue。`,
    observable_extraction_zh: `<strong>Why this choice</strong>: u_centerline 沿 x=0.5 竖线从 y=0 到 y=1 抽 17 点 U_x 值——这是 <strong>Ghia 1982 Table I</strong>（Re=100 列）的 canonical sampling scheme（Table I 是 u(y)；Table II 是 v(x)，两者不要搞混——gold YAML 第 2、12 行明确记载"reference values are Ghia Table I interpolated to 17 y points"）。选 x=0.5 (腔体中线) 是因为它穿过主涡中心，信号幅值最大、分辨率对它最敏感。<strong>诚实声明 · 当前自动 comparator 只做 u_centerline 一维</strong>: v_centerline 和 primary_vortex_location 的 gold block 存在于 YAML 里但 <code>physics_contract.physics_precondition</code> 明确标 <code>satisfied_by_current_adapter=false</code>——v_centerline 可能误用了 Table II 的 x-indexed 数据当成 y-indexed；primary_vortex_location 存成 y=0.7650，和 Ghia 的 0.7344 差 4%，也没存 x_c。这两项当前不被 audit comparator 调用，属于 <strong>planned 但 not validated</strong>；将来升级需要独立 gold 重审（不在本 pilot 范围）。<strong>Main alternative</strong>: 升级到真正的 5 维对比需要同时扩 extractor (算 v_centerline / ψ_min / vortex center) + 修 gold YAML + 升级 Compare tab；升级到 streamFunction 需要对 velocity field 做 ∮ integration 或解 ∇²ψ=−ω。<strong>When it breaks</strong>: sample 线取错位置 (x=0.25 而不是 0.5) → 幅值偏低；extractor 对 uniform mesh 容易，non-uniform mesh 要 OpenFOAM sample utility 插值，cellPointFace 在 boundary 附近会有 artifact。<strong>What to inspect</strong>: system/controlDict 里 <code>functions { sample { type sets; sets ( uCenterline { type lineUniform; axis y; start (0.05 0.0 0.005); end (0.05 0.1 0.005); nPoints 129; } ); } }</code> block 跑完写 <code>postProcessing/sets/&lt;time&gt;/uCenterline_U.xy</code>；comparator 读的是 system/sampleDict 的 17 点 gold-anchored 输出；Compare tab 目前只渲染 scalar tolerance 带，详细 profile + pointwise deviation 见 Story 里的 scientific report iframe（这个 UI split 将在后续 batch 升级）。`,
    workflow_steps_zh: [
      { step: `准备 case 骨架`, command: `cp -r $FOAM_TUTORIALS/incompressible/simpleFoam/pitzDaily ldc_re100 && cd ldc_re100 && rm -rf 0/ constant/* system/*`, detail: `起手最干净的办法是复制一个 simpleFoam 的 tutorial 当目录模板，然后清空 0/ constant/ system/ 内容（保留三个空目录），接下来每个文件都从本 case 的 "复现 bundle" 粘过来。不要用 foamNewCase（这个命令在部分发行版里不存在）。`},
      { step: `写 blockMeshDict`, command: `$EDITOR system/blockMeshDict`, detail: `本仓库 generator 实际写的是 <code>convertToMeters 0.1</code>（物理 domain 0.1m × 0.1m，不是单位方腔），vertices 在单位立方顶点，blocks 的 cells <strong>(129 129 1)</strong>（audit canonical），boundary 5 个 patch: <code>lid</code>(type wall, faces=顶面) / <code>wall1</code>(wall, 左面) / <code>wall2</code>(wall, 右面) / <code>bottom</code>(wall, 底面) / <code>frontAndBack</code>(empty, 前后两面伪 2D)。完整 dictionary 见后续 batch B 会在 Story tab 新增的 "复现 bundle" 折叠块。`},
      { step: `生成网格`, command: `blockMesh | tee log.blockMesh && checkMesh | tee log.checkMesh`, detail: `成功日志末尾打印 <strong>nCells = 16641</strong>（= 129×129×1，教学 quick 也可 40×40=1600 但不能作为 report mesh）+ 5 patches。checkMesh 应打 "Mesh OK"；方腔均匀网格 max non-orthogonality = 0，无 warning。`},
      { step: `设置 BC 与 Re`, detail: `0/U: <code>lid</code> type=fixedValue value=(1 0 0); <code>wall1/wall2/bottom</code> type=fixedValue value=(0 0 0); <code>frontAndBack</code> type=empty。0/p: 所有 wall type=zeroGradient; frontAndBack type=empty。<strong>constant/physicalProperties</strong>（OpenFOAM 10 用 physicalProperties，不是 transportProperties）里 <code>nu [0 2 -1 0 0 0 0] 0.001</code> — 因为 convertToMeters=0.1 让物理 L=0.1m，U_lid=1m/s，所以 Re=U·L/ν=0.1/ν；ν=0.001 给 Re=100。<strong>constant/momentumTransport</strong>（OF10）或 <strong>constant/turbulenceProperties</strong>（OF≤9）里 simulationType=laminar。`},
      { step: `启动 solver`, command: `simpleFoam | tee log.simpleFoam`, detail: `controlDict::endTime=2000, deltaT=1（SIMPLE 里 deltaT 是 iter 计数），fields writeInterval=2000（末态写 2000/），sample function object 独立设 writeInterval=500（每 500 iter 写 postProcessing/sets/&lt;time&gt;/）。residualControl { p 1e-5; U 1e-5; } 命中后 solver 自动停；典型在 1000-1500 iter 之间。`},
      { step: `抽取 u-centerline`, detail: `sampling 由 controlDict::functions::sample 自动执行（generator 已埋）—不需要手跑 postProcess。产物路径 <code>postProcessing/sets/&lt;time&gt;/uCenterline_U.xy</code>（129 点 lineUniform）以及 <code>postProcessing/sets/&lt;time&gt;/uCenterline_U.xy</code> 对应的 17 点 gold-anchored 版本（由 system/sampleDict + <code>postProcess -func sampleDict -time &lt;time&gt;</code> 生成，17 y 值与 gold YAML 的 <code>reference_values</code> 逐点对齐 Ghia 1982 Table I）。comparator 读 17 点版本做 point-by-point L2 + max deviation；L2 &lt; 5% 视为 PASS。`},
    ],
    troubleshooting_zh: [
      { symptom: `Residuals 震荡不收敛（每 100 步大跳跃）`, likely_cause: `under-relaxation factors 太激进，p>0.5 让 pressure correction 被过度 amplified（本仓库默认 p=0.3, U=0.9 + SIMPLEC consistent=yes 已调过；若你手动改过要检查）。`, fix: `fvSolution::relaxationFactors 恢复到 p=0.3 / U=0.9，保留 SIMPLE::consistent yes。若仍震荡，检查 fvSchemes 的 div(phi,U) 是 <code>bounded Gauss limitedLinearV 1</code>（默认）还是被改成 unbounded linear 之类——后者在 SIMPLE 下本身就不稳。`},
      { symptom: `u_centerline 幅值对但位置偏 5%`, likely_cause: `网格太粗未分辨主涡中心位置，primary_vortex_location 被拖向腔体几何中心（Ghia Re=100 真值 x_c=0.6172, y_c=0.7344，粗网格会拖向 0.5, 0.5）。`, fix: `blockMeshDict 把 cells 回到 audit canonical (129 129 1)——千万别把 40×40 的 quick-run 数字写进 report；Mesh tab convergence sweep 应显示 L2 从 mesh_20 单调降到 mesh_160 < 1%。`},
      { symptom: `顶角附近出现 U>1 的 overshoot`, likely_cause: `顶角 (U=1 和侧壁 U=0 同一点) 的 paper-thin discontinuity 触发的数值 Gibbs 现象。`, fix: `物理允许的 artifact——加密角点网格 + 接受 max deviation 在 y=1 附近有个 outlier；comparator 的 L2 对此不敏感，max 容限可放宽到 3%。`},
      { symptom: `solver 初始几步 p residual = NaN`, likely_cause: `遗漏 fvSolution::SIMPLE::pRefCell / pRefValue，不可压 N-S 的 pressure 无约束 → drift。`, fix: `fvSolution 的 SIMPLE 块加 <code>pRefCell 0; pRefValue 0;</code>（注意是 SIMPLE 块内，不是顶层），重跑。NaN 通常第一步就出现，检查 log.simpleFoam 前 10 行。`},
      { symptom: `二级涡（底角）消失`, likely_cause: `网格分辨率不足（<65×65 cells），二级涡尺度小于 cell 尺度被数值耗散抹平。`, fix: `加密到 audit 129×129 或更密；fvSchemes 的 div(phi,U) 保持 <code>bounded Gauss limitedLinearV 1</code>（二阶有限制）而不是 upwind（一阶，过度耗散）。`},
    ],
    reproduction_bundle_zh: LDC_REPRODUCTION_BUNDLE,
    benchmark_lineage_zh: {
      why_primary: `Ghia, Ghia & Shin 1982 成为课堂共同语言的原因有三。一，他们用 multigrid + FMG 在 129×129 uniform grid 上对 Re=100/400/1000/3200/5000/7500/10000 全部跑到完全收敛，这是当时最彻底的系统扫描，后续文献都以它为回归测试的基准。二，他们列了 u-centerline 和 v-centerline 的数值表 (Table I/II)，而不只是印图——这让任何后续代码都能做逐点误差比较，不用 digitize 曲线。三，他们提供了主涡和二级涡中心位置，成为"网格是否分辨出二次涡"的 discriminator。早期 Burggraf 1966 只到 Re=400，高精度的 Botella-Peyret 1998 用 spectral collocation 达到 10⁻¹⁴ 精度但只做 Re=1000。Ghia 的甜点是"够高精度 + 够宽参数扫描 + 数值表形式"。`,
      secondary: [
        `Burggraf 1966 · J. Fluid Mech. · 早期流函数-涡量方法 Re≤400 · 用作历史起点`,
        `Botella & Peyret 1998 · Comput. Fluids · spectral Chebyshev collocation Re=1000 · 用作高精度交叉验证`,
        `Shankar & Deshpande 2000 · Annu. Rev. Fluid Mech. · cavity flow 综述 · 用作延伸阅读`,
      ],
      next_reading: `学完 Re=100 之后应往两个方向走：(1) 上 Re — 读 Ghia 1982 的 Re=1000/3200 段，看二级涡如何出现，以及 3D effects 开始介入（2D 假设从什么时候开始失效）；(2) 换几何 — 读 Shankar-Deshpande 2000 综述中的 driven cavity with obstacles，理解"基准问题"如何从 square 演化成更复杂配置。最后若想做 pure-spectral 验证，去读 Botella-Peyret 1998 的 Chebyshev 数据。`,
    },
  },
  {
    id: "backward_facing_step",
    displayName: "Backward-Facing Step",
    headline_zh: `流动分离`,
    headline_en: "Separation & reattachment",
    teaser_zh: `流到台阶后面突然"掉下来"，形成回流区，最终在下游某个 x 位置重新贴壁。`,
    canonical_ref: "Le, Moin & Kim · 1997 (DNS) + Armaly 1983 (experiment)",
    observable: "reattachment_length / step_height",
    difficulty: "core",
    physics_bullets_zh: [
      `分离流的教科书算例`,
      `Reattachment length 随 Re 变化，不是单调的`,
      `低 Re 时解析稳态；高 Re 时需要非稳态/湍流建模`,
    ],
    why_validation_matters_zh: `反附着长度 L/h 是这个问题唯一的"外部可测量"。两个文献共同锚定这个值：Le/Moin/Kim 1997 DNS 在 Re_H=5100 给出 Xr/H=6.28，Driver & Seegmiller 1985 实验在 Re_H≈37500 给出 6.26——我们在 Re_H=7600 的 post-transition 平台区里，两个数把我们的 tolerance 带从两侧夹住。本仓库把 6.26 作为一个融合的 engineering anchor 保留（见 gold-file header），0.02 的差距由 10% 容差吸收，而不是一个紧致的<2%声明——真实的 Re 敏感度取决于扩张比、入口边界层、以及 2D/3D 效应，adapter 走的是 2D empty-patch 这条简化路径。`,
    common_pitfall_zh: `在 Re=100 左右就容易出现的物理伪像：如果解欠收敛，零速交点会落在台阶上游（x<0），对应回流区"穿墙"——这物理上不可能。我们在采集器里加了 x>0 的保险。`,
    solver_setup_zh: `<strong>Why this choice</strong>: simpleFoam (稳态 SIMPLE) + RAS/kEpsilon。BFS 在 Re_H=7600 处于 post-transition plateau，Xr/H 弱 Re-敏感，稳态 RANS 合理；kEpsilon 被 BFS benchmark 社区用了 40 年是因为计算便宜 + 对 f 类全局量足够准。<strong>Main alternative</strong>: kOmegaSST 贴 Le-Moin-Kim DNS 更好（Xr/H 偏差从 k-ε 的 ~5% 降到 ~2%），但近壁 y+ 要求更严；真正贴 DNS 要上 LES (pimpleFoam + dynamicKEqn) 或直接 DNS (incompact3d 类代码)。<strong>When it breaks</strong>: Re<1000 laminar 区用 k-ε 会在层流段硬给湍流扩散，Xr/H 偏高；URF p>0.5 会让 pressure field 震荡不收敛。<strong>What to inspect</strong>: fvSolution 的 p solver (GAMG + tolerance=1e-6)、nOuterCorrectors (SIMPLE 里 =1 不叠)、residual log (U, k, ε, p 都要掉到 1e-5 以下)。`,
    mesh_strategy_zh: `<strong>Why this choice</strong>: BFS 的关键 flow features 都在 reattachment 下游 (x=0~10·H) 和分离剪切层 (y≈0~1.5·H) 的交叉区。Authoritative run 36000 cells 在这一区做 ≥80×45 的分辨率；quick-run 800 cells (40×20) 是 teaching-grade，用于展示网格敏感性。<strong>Main alternative</strong>: 非结构 mesh (snappyHexMesh) 可以在 step lip 加密但对 structured shear layer 无额外好处；全场均匀细 mesh 会把计算量翻 10 倍而 Xr/H 精度提升 <1%。<strong>When it breaks</strong>: quick-run 800 cells 会让 reattachment zone 分辨率不足，DEC-V61-036 的 G5 gate 专门捕捉这个 — under-resolved shear layer 让 Xr/H 偏差 >10% 时 ATTEST_HAZARD。<strong>What to inspect</strong>: Mesh tab 的 convergence sweep — 800 (quick) → 3200 → 12800 → 36000 cells，看 Xr/H 是否单调趋近 6.26 ±10%；如果 mesh_20 和 mesh_160 差距仍 >5% 说明 reattachment zone 还没收敛。`,
    boundary_conditions_zh: `<strong>Why this choice</strong>: inlet fixedValue U=(1,0,0) 给干净的 uniform 来流 (简化 boundary layer history)；outlet zeroGradient U + fixedValue p=0 允许回流自然出去；上下壁 no-slip 产生边界层；step face no-slip 触发分离；front/back empty 做伪 2D。<strong>Main alternative</strong>: 给 inlet 一个真实发展的 boundary layer profile (从前置 channel 跑一段稳态)，能减小 5-10% 的 Xr/H 偏差——但引入额外 setup 复杂度。outlet 改 inletOutlet 可以防回流污染但也会悄悄改变 downstream recovery。<strong>When it breaks</strong>: 忘记 outlet pressure reference → 整个 pressure field 漂移；inlet 太近 step (< 5·H) → inflow boundary 污染 separation point。<strong>What to inspect</strong>: polyMesh/boundary 里 inletPatch type=patch、outletPatch type=patch、frontAndBack type=empty；0/U 里 inlet fixedValue=(1,0,0)，outlet zeroGradient；0/p 里 outlet fixedValue=0。`,
    observable_extraction_zh: `<strong>Why this choice</strong>: Xr 是 "下壁第一个由负变正的 x 值"——即 reattachment point。extractor 在 y=0.01·H 处 sample U_x (避免 wall-cell degenerate) 从 x=0 扫到 8·H，线性插值找零点。y=0.01·H 比 exact wall 更稳，因为 wall-cell 的 U_x 总是 0（no-slip），信息来自 near-wall cell 的 gradient。<strong>Main alternative</strong>: 用 wallShearStress (τ_w) 的零点更精确但要 OpenFOAM 的 postProcess wallShearStress function；用 oilFlow visualization 模式 (static/post-processing) 目视找 reattachment。<strong>When it breaks</strong>: quick-run residual 没完全收敛时 U_x(x, y=0.01·H) 还在震荡，零点位置可能不稳定；如果解欠收敛，零点交点会落在 step 上游 (x<0) 对应 "回流区穿墙"，物理不可能——adapter 加了 x>0 的保险。<strong>What to inspect</strong>: sample line 采样结果 postProcessing/sample/lineX0 (y=0.01·H 剖面)；comparator output 的 Xr_H_numeric vs gold 6.26；如果偏差 >10% 先看 grid convergence (mesh_80 vs mesh_160) 再怀疑 solver/model。`,
    workflow_steps_zh: [
      { step: `写 blockMeshDict 扩口几何`, detail: `vertices 画 L-shape: 入口段 (−5·H→0, 0→H) + 扩张段 (0→20·H, 0→2·H)；cells 在 quick-run 走 40×20 (~800)，在 authoritative 走 160×90 (~36000)，在 step lip 局部 graduation (expansionRatio=0.3 向 x=0 靠拢) 提升剪切层分辨率。`},
      { step: `生成并检查网格`, command: `blockMesh && checkMesh`, detail: `checkMesh 应看到 max non-orthogonality <30、max aspect ratio <50 且无 highly skewed cells；如果 step lip 附近有 warning 说明 graduation 过度，回调 expansionRatio。`},
      { step: `配置 RANS 模型和 Re`, detail: `constant/turbulenceProperties 的 RAS:RASModel kEpsilon；constant/transportProperties 的 nu = U·H/Re = 1·1/7600 = 1.316e-4。0/k 初值给 1.5·(U·0.05)² (5% turbulent intensity)，0/epsilon 给 C_mu^0.75·k^1.5/L (L=0.07·H mixing length)。`},
      { step: `设置 inlet BL profile (可选)`, detail: `Authoritative run 用 codedFixedValue 给 inlet power-law BL (U/U_0=(y/δ)^(1/7))；quick-run 允许 uniform fixedValue 简化。简化版对 Xr/H 会引入 ~5-8% 系统误差，是 teaching-grade 折中。`},
      { step: `启动稳态 solver`, command: `simpleFoam > log.simpleFoam &`, detail: `controlDict::endTime=3000。foamLog 抽 U、p、k、ε 四条 residual 曲线，全部 drop 到 1e-5 以下才算收敛；post-transition 区典型 2000-2500 iteration 够用。`},
      { step: `抽取 reattachment`, detail: `extractor 在 y=0.01·H (near-wall, 非 wall-face) 从 x=0 sample U_x 到 x=8·H，找第一个 U_x 由负转正的 x 值作为 Xr。comparator 与 gold 6.26 比对，偏差 ≤10% 视为 PASS。`},
    ],
    troubleshooting_zh: [
      { symptom: `Xr/H 落在 0-2 之间，偏差 >50%`, likely_cause: `extractor sample line 取在 wall cell 中心 (y=0)，U_x=0 永远是 no-slip 值，零点位置没意义。`, fix: `确保 sample 线偏离 wall 至少 0.01·H (≈1 cell height)，位于 near-wall cell 中心上方；修 foam_agent_adapter.py 的 sample_line_y_offset 参数。`},
      { symptom: `Xr/H 在不同 mesh 分辨率下单调增大不收敛`, likely_cause: `quick-run 800 cells 对 shear layer 欠分辨，数值扩散把 reattachment 人为推远。`, fix: `Mesh tab 切到 authoritative 36000 cells；若仍然漂移 >10% 说明 kEpsilon 的各向同性假设不足，换 kOmegaSST 重跑。`},
      { symptom: `Residual 卡在 1e-3 再也不降`, likely_cause: `inlet k/ε 初值太小（<0.001），k-ε 方程在低湍流极限下自我耗散，流场被 "frozen"。`, fix: `把 inlet k 提升到 1e-3 以上 (I=5% of U²)，对应 ε≈0.001，重跑；注意 ε 也要相应拉高否则 ν_t 爆。`},
      { symptom: `零点出现在 x<0（台阶上游）`, likely_cause: `解欠收敛时 near-wall U_x 还在震荡，adapter 的 sign-change finder 把震荡点误认作 reattachment。`, fix: `extractor 加 x>0 筛选（本仓库已加），同时 solver 再跑 1000 步；物理上台阶上游是正压 boundary layer，U_x 一直>0。`},
      { symptom: `log.simpleFoam 末尾 "bounding epsilon" 持续出现`, likely_cause: `ε 在某些 cell 接近负值被 OpenFOAM 的 bounding 强制拉回到 SMALL，通常因为 kEpsilon 在分离区的 near-wall 行为不物理。`, fix: `换 kOmegaSST（无 ε 方程、自动处理 near-wall）或给 ε walls 用 epsilonWallFunction 显式 BC；忽略偶发 bounding 是实践默认。`},
    ],
    benchmark_lineage_zh: {
      why_primary: `BFS 不止一个 "gold"，它有一族互相制衡的 anchors。本 harness 最终选 Xr/H=6.26 作为 blended engineering anchor，是因为在 Re_H=7600 的 post-transition plateau 上，Le/Moin/Kim 1997 DNS (Re_H=5100, Xr/H=6.28) 和 Driver & Seegmiller 1985 experiment (Re_H≈37500, Xr/H=6.26) 双边夹住我们 ±10% 容差带。单独用任何一篇都不合适——Le-Moin-Kim 是 DNS 但 Re 偏低 + expansion ratio 不同；Driver-Seegmiller 是 experiment 但 Re 偏高 + 可能有 3D effects。把 6.26 明说成 blended anchor 比伪装成 "pure DNS gold" 更诚实。`,
      secondary: [
        `Le, Moin & Kim 1997 · J. Fluid Mech. · DNS at Re_H=5100, expansion 1.2 · Xr/H=6.28`,
        `Driver & Seegmiller 1985 · AIAA J. · fully-turbulent experiment at Re_H≈37500 · Xr/H=6.26`,
        `Armaly et al. 1983 · J. Fluid Mech. · laminar→transitional envelope Re 100-8000 · 用作低-Re 扩展`,
        `Jovic & Driver 1994 · NASA TM · low-Re experiment at Re_H=5000 · 和 Le-Moin-Kim 的 DNS 对位交叉验证`,
      ],
      next_reading: `学完 Re=7600 稳态 RANS 之后向两个方向走：(1) 换 solver — 读 Le-Moin-Kim 1997 的 DNS 细节，理解 shear layer Kelvin-Helmholtz instability 如何推动 reattachment 周期性振荡（稳态 RANS 抹掉了这个信息）；(2) 换 regime — 读 Armaly 1983 在 Re<1000 的 laminar 分支，看多个二级分离泡如何出现，是理解 "Xr/H vs Re" 非单调曲线的前提。想做工业 CFD 可以进一步读 Kaltenbach 1999 的 LES。`,
    },
  },
  {
    id: "circular_cylinder_wake",
    displayName: "Circular Cylinder Wake",
    headline_zh: `涡街与频率`,
    headline_en: "Vortex shedding",
    teaser_zh: `经典 Kármán 涡街。涡脱频率 f 和来流速度 U、直径 D 之间存在近乎普世的 Strouhal 关系 St ≈ 0.2。`,
    canonical_ref: "Williamson · 1996 (review)",
    observable: "Strouhal number St = f·D/U",
    difficulty: "core",
    physics_bullets_zh: [
      `二维非稳态 Navier-Stokes`,
      `Re=200 附近开始规则涡脱`,
      `Re~10⁵ 范围内 St 近似为常数 ≈ 0.20`,
    ],
    why_validation_matters_zh: `Strouhal 数是一个"canonical band"——不同文献、不同雷诺数、不同湍流模型，都落在 0.18-0.22 这个窄带里。你的代码只要算出"属于这个带"就算合格；但这里有一个陷阱：如果你直接用 canonical-band 作为通过判据，那就是"silent-pass hazard"——任何 bug 都会假装通过。`,
    common_pitfall_zh: `涡脱需要非对称扰动才能启动。用完全对称的初始场 + 对称网格，涡脱可能要跑几万步才出现，甚至永远不出现。标准做法是在来流里加一个几个百分点的瞬时扰动。`,
    solver_setup_zh: `<strong>Why this choice</strong>: pimpleFoam (瞬态 PIMPLE) + turbulenceProperties=laminar。Re=100 涡脱本质是 2D 非稳态周期性行为——稳态 solver 会收敛到对称死解 (unstable fixed point)，必须 transient。layer=laminar 因为 Re=100 远低于湍流转捩。Δt 由 CFL<1 约束：near-cylinder 最密网格 + U_max≈1.5 U_∞ → Δt≈0.005~0.01。<strong>Main alternative</strong>: PISO 纯 (nOuterCorrectors=1) 比 PIMPLE 快但对大 Δt 容错差；对 Re>300 二维已失效要切 3D + LES (pimpleFoam + dynamicKEqn) 或 DNS。<strong>When it breaks</strong>: 对称网格 + 对称初场 → 涡脱可能要几万步才起步或根本不起步；Δt>0.02 在 CFL=1.5 附近 → 时间积分精度降到一阶，St 数值偏高。<strong>What to inspect</strong>: controlDict 的 adjustTimeStep=yes + maxCo=0.8；residual log 里 U+p 每 time step 收敛到 1e-5；probe 信号用 paraFoam 看 U_y(t) 是否进入周期 limit cycle。`,
    mesh_strategy_zh: `<strong>Why this choice</strong>: domain truncation 是 cylinder wake 最容易踩的坑。上游 10·D (inlet 放得够远避免干扰 stagnation) + 下游 30·D (wake 完全发展完) + 横向 ±10·D (侧壁 slip 条件对尾迹无反射) 是 Re=100 安全值。近壁 cell 特征长度 ~0.02·D，远场 ~0.5·D，O-grid 贴 cylinder 表面 30° graduation。<strong>Main alternative</strong>: 下游截到 15·D 会让涡尾附近 probe 受 outlet 影响 (inletOutlet BC 反射)；C-grid 贴 airfoil-style 网格需要多 block manipulation 对 cylinder 过度复杂。<strong>When it breaks</strong>: 上游 <5·D → inlet 被 upstream blockage 污染；下游 <20·D → 涡脱频率偏 (outlet BC 反馈)；壁面网格不够密 → 剪切层分离点不稳定。<strong>What to inspect</strong>: constant/polyMesh/ 的 cells 总数 (2D 结构 ~20000-40000 cells 够 Re=100)；probe 应该放在 x=5·D 下游尾迹核心处；grading ratio 从近壁 0.02·D 平滑到远场 0.5·D。`,
    boundary_conditions_zh: `<strong>Why this choice</strong>: inlet fixedValue U=(1,0,0) + 一个微小非对称扰动 (e.g. 初始 U_y 在某 cell 给 0.01) 是触发涡脱的关键——完全对称初场 + 对称网格会让解停在 unstable fixed point。outlet zeroGradient U + fixedValue p=0 允许回流；上下侧壁 slip (symmetry) 避免 blockage 反射；圆柱 no-slip 触发剪切层分离。<strong>Main alternative</strong>: 给 inlet 明显的不对称扰动（U_y=0.1 sin(πy/H)）会加速 startup 但短期污染信号；上下壁改 no-slip 会让 domain 变成 constrained channel，改变 pressure field。<strong>When it breaks</strong>: 完全对称配置 → 涡脱永远不起动；inlet 扰动太大 → 干扰 limit cycle 稳定性；outlet fixedValue U 而非 zeroGradient → 人为 block 回流。<strong>What to inspect</strong>: 0.org/U 里 internalField 是否有一个小幅度 non-uniform perturbation；probe U_y(t) 信号从 startup 到 limit cycle 的过渡（一般前 10% 时间是 transient 要丢弃）。`,
    observable_extraction_zh: `<strong>Why this choice</strong>: St = f·D/U 用频率而非振幅定义，是因为振幅对 mesh、time step、probe 位置敏感，频率是 intrinsic 物理不变量。src/cylinder_strouhal_fft.py 在 probe U_y(t) 时间序列上先丢前 25% transient，再 Hann 窗 FFT 求幅值谱峰 → 主频 f。<strong>Main alternative</strong>: autocorrelation 0-crossing 法 (直接数过零次数 / 时间) 更快但噪声敏感；lift coefficient C_L(t) FFT 比 probe U_y 更好 (积分量抗噪声) 但需要 wallShearStress + patchAverage 后处理。<strong>When it breaks</strong>: 采样时长 <20 个涡脱周期 → FFT 分辨率不够识别主频；Δt 大 (>0.02) → Nyquist 不够涵盖 2·f_shedding；⚠ silent-pass hazard — 如果 extractor bug 让 f 永远落在 canonical-band 0.18-0.22 (例如 FFT 默认返回某个固定值)，comparator 会假通过——physics_contract 显式标记这个风险为 precondition "extractor reflects actual solver physics" = false。<strong>What to inspect</strong>: probe 文件 postProcessing/probes/0/U (位置应该在尾迹 5·D 处)，python 画 U_y(t) 看 limit cycle 稳不稳；FFT 输出的峰值 f 是否 ±10% 落在 0.163-0.167 (Williamson 1996 Re=100 值)。`,
    workflow_steps_zh: [
      { step: `画 O-grid 圆柱域`, detail: `snappyHexMesh 或 blockMesh multi-block O-grid：上游 10·D、下游 30·D、横向 ±10·D 矩形外域 + 内嵌 cylinder patch D=1。壁面 y+<1 要求 first-cell 高度 ≈0.01·D；远场 cell ~0.5·D。`},
      { step: `生成网格`, command: `blockMesh && checkMesh`, detail: `2D 结构网格 ~20000-40000 cells 对 Re=100 够用。检查 cylinder 面 aspect ratio <20、max non-orthogonality <45；front/back 做 empty patch 让 2D。`},
      { step: `打破对称初场`, detail: `0/U 的 internalField 给 uniform (1 0 0) 但在任意一个 cell 加 (0 0.01 0) 小扰动，或 inlet BC 加 codedFixedValue 给 U_y=0.001·sin(πy/H) — 关键是让解脱离 unstable symmetric fixed point。`},
      { step: `配置瞬态 solver`, detail: `controlDict: application pimpleFoam, startTime 0, endTime 200, deltaT 0.005, adjustTimeStep yes, maxCo 0.8, writeInterval 1。fvSolution::PIMPLE nOuterCorrectors 2, nCorrectors 1 对 Re=100 够用。`},
      { step: `放 probe 并启动`, command: `simpleFoam 替换为 pimpleFoam >log.pimpleFoam &`, detail: `system/probes 加 probe at (5 0 0)（wake core, 5·D downstream）记 U。解前 25% 时间 (t<50) 是 startup transient，后面进 limit cycle。`},
      { step: `FFT 求 Strouhal`, detail: `src/cylinder_strouhal_fft.py 读 postProcessing/probes/0/U，丢前 25%，Hann 窗 FFT 求 U_y 主频 f，St = f·D/U。comparator 比 Williamson Re=100 的 0.165，±10% 视为 PASS。`},
    ],
    troubleshooting_zh: [
      { symptom: `probe U_y(t) 信号是一条近零直线，无涡脱`, likely_cause: `初场完全对称，解停在 unstable symmetric fixed point。`, fix: `0/U 手动改一个 cell 的 internalField 给 (0 0.01 0)，或 inlet BC 用 codedFixedValue 给 sinusoidal perturbation；重启 solver 应在 ~20 个 Δt 内看到 U_y 开始振荡。`},
      { symptom: `St 偏高 20% (接近 0.20)`, likely_cause: `Δt 过大，CFL 接近 1.5，时间积分一阶精度把高频信号人为放大。`, fix: `controlDict maxCo 从 0.8 降到 0.4，让 adjustTimeStep 自动缩 Δt；重跑后 St 应落回 0.163-0.167 带内。`},
      { symptom: `limit cycle 振幅缓慢衰减到 0`, likely_cause: `outlet BC 用 fixedValue U 而非 zeroGradient，人为 block 回流，把能量从 wake 抽走。`, fix: `0/U outlet 改为 inletOutlet 或 zeroGradient，0/p outlet fixedValue=0；重跑确认 limit cycle 稳定。`},
      { symptom: `FFT 谱出现两个同幅值峰`, likely_cause: `采样时长 <20 周期或 startup transient 没丢干净，频谱泄漏。`, fix: `跑到 endTime≥200 (至少 30 涡脱周期)，FFT 前把前 25% (t<50) 显式舍弃；Hann 窗也帮助降低 leakage。`},
      { symptom: `下游 probe 的频率比上游 probe 慢 10%`, likely_cause: `domain 下游边界 <20·D，outlet BC 反射波污染尾迹频率。`, fix: `blockMeshDict 把 downstream 延长到 30·D 或 40·D，重生成网格重跑；这是 cylinder wake 最常见的 subtle 域截断失败。`},
    ],
    benchmark_lineage_zh: {
      why_primary: `Williamson 1996 是 cylinder wake 领域的"共识综述"——它把 1960 年代到 1990 年代的实验、DNS、LES 结果统合成一条 St-Re 曲线，明确标出 Re≈47 周期性脱落起点、Re≈180 3D mode-A 出现、Re≈260 mode-B 接管，以及 Re=10⁴-10⁵ 的 subcritical plateau (St≈0.21)。选它而不是选某一篇原始实验，是因为 cylinder wake 的 canonical observable 不是某一个 "正确数字"，而是一段"regime vs St"的映射——graduate student 应该先读综述建立全景，再下钻到原始实验。`,
      secondary: [
        `Roshko 1954 · NACA TN · 首篇系统测 St(Re) 的风洞实验 · 低-中 Re 原始数据源`,
        `Henderson 1997 · Phys. Fluids · 2D 稳定性分析 + 3D mode 转变预测 · 理解 Re=180 transition`,
        `Barkley & Henderson 1996 · J. Fluid Mech. · Floquet 稳定性 · 为 mode-A/B 转变提供理论`,
        `Norberg 2003 · J. Fluids Struct. · 大 Re 区 fluctuating lift 综述 · 工业应用向延伸`,
      ],
      next_reading: `读完 Re=100 稳定 limit cycle 之后：(1) 上 Re 到 Re=200 — 读 Henderson 1997 看 3D 失稳如何改变尾迹结构，2D 假设从 Re=190 附近开始失效；(2) 读 Norberg 2003 理解 Re=10⁵-10⁶ 工业 Re 下的 transition crisis（Strouhal 突然跌到 0.4+ 再回归）；(3) 去读 Roshko 1954 原始论文——这是那种教你"一个人用风洞 + 热线就能测出关键物理量"的经典工作。`,
    },
  },
  {
    id: "turbulent_flat_plate",
    // DEC-V61-047 round-1 F5: case_id 保留为 turbulent_flat_plate（稳定性）
    // 但物理现在是 laminar Blasius —— displayName 与叙事都必须诚实映射。
    // 详见 knowledge/gold_standards/turbulent_flat_plate.yaml 头部的 REGIME
    // CORRECTION 块：Re=50000 + plate_length=1.0m → Re_x 最大 5×10⁴，比转捩
    // 下限 3×10⁵ 还差 6 倍，湍流假设根本不成立。把"turbulent"当教学主线会
    // 把新手引入错误回路。
    displayName: "Flat Plate (laminar Blasius regime)",
    headline_zh: `层流边界层：Blasius`,
    headline_en: "Laminar boundary layer (Blasius)",
    teaser_zh: `平板上的边界层。我们把这一 case 诚实地放在层流 Blasius 区（Re_x=2.5×10⁴~5×10⁴，远低于转捩），用解析相似解 Cf=0.664/√Re_x 当 gold。之前按"湍流平板"标错了，本仓库把它改回层流——这是一个关于"命名诚实"的案例。`,
    canonical_ref: "Blasius 1908 / Schlichting",
    observable: "skin-friction coefficient Cf(x), laminar Blasius gold",
    difficulty: "intro",
    physics_bullets_zh: [
      `Re_x = Ux/ν 决定流态：转捩大约在 3×10⁵–5×10⁵`,
      `本 case Re_x ≤ 5×10⁴，处于层流区 → Blasius 相似解精确成立`,
      `Cf(x) = 0.664 / √Re_x；solver 用 simpleFoam + laminar（无湍流方程）`,
    ],
    why_validation_matters_zh: `这个 case 的教学意义是"验证思维的诚实性"。早期版本把 gold 写成 Spalding 1/7 次幂的湍流工程公式 Cf=0.0576/Re_x^0.2，结果在低 Re 下系统偏高。B-class 修订（DEC-V61-006）把 gold 改回 Blasius 解析解，因为 Re_x 实在够不着湍流。教训：一个 case 叫什么名字 ≠ 它实际在算什么物理，名字错了 gold 也就跟着错。`,
    common_pitfall_zh: `新手最容易中的陷阱：看到 "turbulent_flat_plate" 就想当然去跑 k-ε / k-ω 湍流模型——在 Re_x=2.5×10⁴ 的层流里套湍流模型，会在近壁处给出虚假的 Cf。Spalding fallback 作为工程经验公式在参数外推时也会生成和 Re 解耦的数字（两个不同 case 同 Re → 同 Cf），看似 match 其实 shortcut。`,
    solver_setup_zh: `<strong>Why this choice</strong>: simpleFoam (稳态 SIMPLE) + turbulenceProperties=laminar——严格层流 N-S 无湍流方程。Re=50000 基于 plate 长 L=1m、U_∞=1；ν=1/50000。名字里的 "turbulent" 是历史 case_id 稳定性保留，实际物理和 solver 都是层流（DEC-V61-006 B-class 修订）。稳态合理因为 Blasius 本身是 similarity 稳态解。<strong>Main alternative</strong>: 若真要模拟 turbulent BL (Re_x>3×10⁵) 需要 RAS kOmegaSST 或 LES，BL thickness 公式从 δ_99=5√(νx/U) 改为 δ_99∝x·(0.37/Re_x^0.2) — 完全不同的 scaling。用 laminar 解析解法不需要 solver. <strong>When it breaks</strong>: 错启用 k-ε 在 Re_x=25000 层流 regime → wall functions 引入假 turbulent viscosity → Cf 系统偏高；Spalding fallback 在代码里是经验外推，参数相同的两个不同 case 会给相同 Cf (shortcut, 不是真实提取)。<strong>What to inspect</strong>: turbulenceProperties 必须是 simulationType=laminar 而非 RASModel；fvSolution 的 relax factors U=0.7, p=0.3；residual 收敛到 1e-6 量级。`,
    mesh_strategy_zh: `<strong>Why this choice</strong>: 2D 薄切片 (L×H=1×1)，y 方向 80 cells + 4:1 wall grading 是关键——近壁密疏比 4:1 让第一层 cell 厚度 y₁≈0.001·H，足够捕捉 Blasius δ_99≈0.022·L 的边界层 profile。80 cells 里有 ~50 cells 落在 δ_99 内。<strong>Main alternative</strong>: 等距 uniform mesh 需要 10× cells 才达到同 wall 分辨率，浪费算力；wall-function mesh (y+>30) 在层流里没意义 (wall functions 是湍流 model 组件)；non-conformal / adaptive refinement 对此简单几何 overkill。<strong>When it breaks</strong>: grading 方向错 (远壁变密、近壁变疏) → wall gradient 抓不住；cells 太少 (<40 y-cells) → δ_99 里只有 2-3 cells，Cf 偏低 10%+。<strong>What to inspect</strong>: blockMeshDict 里的 grading vector (应该是 1 4 1 形式：streamwise uniform, wall-normal 4:1)；postProcess 用 y+=sqrt(τ_w/ρ)·y/ν 检查第一 cell y+<1 (层流里也有意义，值 <<1 说明 wall-adjacent cell 够密)。`,
    boundary_conditions_zh: `<strong>Why this choice</strong>: inlet fixedValue U=(1,0,0) 给均匀来流 → Blasius leading-edge 从 x=0 开始 BL 发育；下壁 no-slip 产生 Blasius BL；上壁 slip (symmetry) 避免上方 BL 干扰；outlet zeroGradient U + fixedValue p=0 允许 BL 自然出去；front/back empty 伪 2D。<strong>Main alternative</strong>: 上壁 no-slip 会在 channel flow 里产生两条 BL 并可能合并 — 完全不同的问题；domain height H 改到 5·δ_99≈0.11·L 可节省算力 (现在 H=L=1 是保守)。<strong>When it breaks</strong>: 上壁改 no-slip 或 fixedValue → 你测到的 Cf 是 channel not BL；inlet 太贴近 x=0.5 measuring station → inflow profile 还没发展到 Blasius similarity。<strong>What to inspect</strong>: 0/U 里 topPatch type=slip; 0/p 里 outlet fixedValue=0。`,
    observable_extraction_zh: `<strong>Why this choice</strong>: Cf(x) = 2·τ_w/(ρ·U_∞²) 是局部 skin friction coefficient；选 x=0.5m 作为 canonical sample station 因为此处 Re_x=25000 安全处于层流区（转捩 Re_x>3×10⁵），Blasius 解给 Cf=0.00420 作为 exact reference。extractor 用 _compute_wall_gradient (src/foam_agent_adapter.py) 在 y₁+y₂ interior-cell 做 dU/dy finite difference (避开 wall cell 的 degenerate U=0)，乘 μ 得 τ_w。<strong>Main alternative</strong>: 用 OpenFOAM 的 wallShearStress functionObject 直接输出 τ_w field — 更 canonical 但和当前 extractor 的 interior-cell 方法比可能在第一层 cell 处有 1-2% 偏差；用 Cf(x) 全场曲线比单点 x=0.5 信息多但对 benchmark 单点足够。<strong>When it breaks</strong>: Spalding fallback 触发 → 返回 Cf=0.0076 (1/7-power turbulent 经验公式) 而非 interior-cell 真实 gradient — 在 laminar contract 下这应该 hazard；wall-cell degenerate (U=0 at wall) 给 zero gradient 错觉。<strong>What to inspect</strong>: postProcess 的 sample 文件应包含 x=0.5 处 (y, U_x) 数对；comparator output 的 Cf=measurement vs gold=0.00420 差值应 <10%。`,
    workflow_steps_zh: [
      { step: `写 2D 扁薄板几何`, detail: `blockMeshDict vertices 画 L×H=1×1 的 2D 切片；cells 沿 x 方向 200 uniform (5e-3·L 够分辨 Blasius x=0.5 附近)，沿 y 方向 80 cells + grading (1 4 1) — wall-normal 4:1 graduation 让 near-wall y₁≈0.001·H。`},
      { step: `生成并检查网格`, command: `blockMesh && checkMesh`, detail: `check 过关后跑 yPlus 初估：τ_w≈0.5·ρ·U²·Cf≈0.0021N/m²，第一层 y+ = y₁·√(τ_w/ρ)/ν ≈ 0.003·√0.0021/(1/50000) ≈ 0.5，层流模式下的"y+ 有意义"比湍流 wall-function 要求松很多。`},
      { step: `设 laminar BC 与 ν`, detail: `constant/turbulenceProperties::simulationType laminar（不是 RASModel 任何湍流模型）。constant/transportProperties::nu = 1/50000 = 2e-5（让 Re_L=50000）。0/U inlet fixedValue=(1 0 0)、下壁 fixedValue=(0 0 0)、上壁 slip、outlet zeroGradient。`},
      { step: `启动 solver`, command: `simpleFoam > log.simpleFoam &`, detail: `controlDict::endTime 2000、fvSolution 的 p 用 GAMG tolerance 1e-7 (Blasius solution 对 residual level 敏感)。foamLog 检查 U、p residual 降到 1e-6 以下；关掉任何湍流 functionObject 否则可能误报 k/ε 残差。`},
      { step: `抽取 wall gradient`, detail: `用 sample 在 x=0.5m 竖线取 y=[0, 0.001, 0.002, ...] 的 U_x profile；extractor 在 y₁+y₂ 两点做 finite-difference 求 dU/dy，乘 μ=ρ·ν 得 τ_w，再算 Cf=2·τ_w/(ρ·U²)。避开 wall cell 本身（U=0 永远给零梯度错觉）。`},
      { step: `对比 Blasius`, detail: `Cf_gold = 0.664/√Re_x = 0.664/√25000 = 0.00420。comparator 看 |Cf_measured − 0.00420|/0.00420 < 10%为 PASS；若 adapter 触发 Spalding fallback 返回 Cf=0.0076，合同是 physics_contract::extractor_reflects_actual_physics=false → hazard.`},
    ],
    troubleshooting_zh: [
      { symptom: `Cf 返回 0.0076，恰好匹配 Spalding 湍流经验公式`, likely_cause: `adapter 的 extractor 在无法读到 wall gradient 时 fallback 到 Spalding 1/7-power empirical Cf=0.0576·Re_x^-0.2, 与实际 solver 物理脱钩。`, fix: `检查 foam_agent_adapter.py::_compute_wall_gradient 是否在 sample 数据不足时触发 fallback；让它在 laminar contract 下 raise 而非 fallback，保留 physics_contract::extractor_reflects_actual_physics 的诚实信号。`},
      { symptom: `Cf ~0.008 系统偏高 2×`, likely_cause: `不小心激活了 RAS kEpsilon 或 kOmegaSST，wall function 在层流 Re_x=25000 下仍强行 impose turbulent wall shear。`, fix: `constant/turbulenceProperties 改为 simulationType laminar；删除 0/k 0/epsilon 0/nut 文件；重生 case 重跑。`},
      { symptom: `BL profile 在 x=0.5 处未达 Blasius similarity`, likely_cause: `domain 太短，inlet 离 x=0.5 太近（<0.3·L），BL 还没充分发育成 similarity 解。`, fix: `blockMeshDict 延长 upstream 让 inlet 在 x=−0.2（或把 plate leading edge 放在 x=0，测量点在 x=0.5），保证 BL 有 0.5 单位长度的发展段。`},
      { symptom: `wall cell 首层给的 U_x 是 0，数值 dU/dy=0 → Cf=0`, likely_cause: `extractor 在 wall face 而非 near-wall cell center 取值；no-slip 下 wall face U=0 永远成立。`, fix: `extractor 从 y=y₁（first interior cell center, ~0.0005·H）取 U_x, y=y₂ 取第二层，做中心差分；本仓库的 _compute_wall_gradient 已如此实现。`},
      { symptom: `residuals 卡在 1e-4 下不去`, likely_cause: `grading 过激进（比如 10:1）在 wall cell 造成 aspect ratio>100，数值刚性使 p solver 收敛缓慢。`, fix: `grading 降回 4:1；或 fvSolution 的 p solver 换为 PCG + diagonal preconditioner + tolerance 1e-8；层流 Blasius 需要比湍流 case 更严的 residual level。`},
    ],
    benchmark_lineage_zh: {
      why_primary: `本 case 选 Blasius 1908 解析相似解作为 gold，不是选更"现代"的湍流经验公式（如 Spalding 1/7 次幂 Cf=0.0576/Re_x^0.2），是因为 Re_x 在本 case 范围内（2.5×10⁴~5×10⁴）深在层流区。Blasius 解在此 regime 里是**精确解**，误差只来自 solver 和 mesh，不来自公式本身——这就比任何经验公式更干净作为 teaching anchor。选 Schlichting Boundary Layer Theory (7th ed.) 作 secondary 是因为它把 Blasius 推导写透，graduate student 需要知道 0.664/√Re_x 是从相似变量 η=y√(U/νx) 约简 Prandtl BL 方程得来的，不是从实验拟合。`,
      secondary: [
        `Schlichting 2017 · Boundary Layer Theory 9th ed. Ch.7 · Blasius 相似解完整推导`,
        `Spalart 1988 · J. Fluid Mech. · turbulent BL DNS at Re_θ≤1410 · 若切换到 turbulent regime 的教科级参考`,
        `White 2006 · Viscous Fluid Flow 3rd ed. · 层流-转捩-湍流 BL 全景教材`,
      ],
      next_reading: `学完层流 Blasius 之后：(1) 上 Re 到 Re_x>10⁶ — 读 Spalart 1988 DNS 或 Coles 1956 law of the wake 看湍流 BL 的 u+ vs y+ 结构，这是下一 case (plane_channel_flow) 的前提；(2) 研究转捩 — 读 Schubauer & Skramstad 1948 NACA 报告讨论 Tollmien-Schlichting wave 如何触发 Re_x≈3×10⁵ 处的 laminar→turbulent transition；(3) 若做压力梯度效应 — 读 Falkner-Skan 相似解（课程下一章）。`,
    },
  },
  {
    id: "plane_channel_flow",
    // DEC-V61-047 round-1 F5: contract_status =
    //   INCOMPATIBLE_WITH_LITERATURE_DISGUISED_AS_COMPATIBLE
    // 当前 adapter 是 icoFoam 层流，在 Re_bulk=5600 只能给出 Poiseuille 抛
    // 物线速度剖面，无法复现 Moser 1999 Re_τ=180 的湍流对数律 u+。这个 case
    // 反而成为"为什么 ATTEST_PASS 可能是 comparator 假象"的最佳教学样本。
    displayName: "Plane Channel (incompatibility teaching case)",
    headline_zh: `"看似通过其实不兼容"的教学样本`,
    headline_en: "Disguised incompatibility (teaching case)",
    teaser_zh: `这个 case 当前的 contract_status 是 INCOMPATIBLE_WITH_LITERATURE_DISGUISED_AS_COMPATIBLE——当前 solver 跑的是 icoFoam 层流，但文献 gold 用的是 Moser 1999 的湍流 DNS。两者在 Re_bulk=5600 一 对比，从数字上可能"看着对"，从物理上完全不是一回事。这是新手最容易被坑的类型。`,
    canonical_ref: "Moser/Kim/Mansour 1999 DNS (Re_τ=180, turbulent)",
    observable: "u+ vs y+ 对数律（当前 solver 无法产生，会落成 Poiseuille）",
    difficulty: "advanced",
    physics_bullets_zh: [
      `文献 gold：Moser 1999 DNS，Re_τ=180 的湍流对数律 u+(y+)`,
      `当前 adapter：icoFoam 层流 PISO，Re_bulk=5600 → Poiseuille 抛物线`,
      `物理上：层流 N-S 收敛到抛物线，不是对数律——无法靠调参弥合`,
    ],
    why_validation_matters_zh: `这个 case 是本仓库 physics_contract 层的压力测试：如果只看 comparator 的数字（u+ 和 y+ 数值范围巧合），ATTEST 会给出 PASS——但物理上不兼容。诚实的 verdict 是 FAIL。教学意义：一个 CFD pipeline 如果没有 physics_contract / precondition 检查层，仅靠"数字跟文献接近"判定通过，就会把层流解包装成"通过湍流 DNS 对照"——这是工业 CFD 最危险的假阳性模式。`,
    common_pitfall_zh: `新手常问："我的 solver 选错了吗？" 是的——但更深的陷阱是：当 comparator 读取 u+/y+ 数字没报错、tolerance 范围也没超，你会以为 case 通过了。修复方向需要切换到 pimpleFoam + 湍流模型（或 LES），但这个 case 目前的意义就是展示 gap。Phase 9 solver-routing 工作会把这个 case 迁到真正能跑湍流 DNS 的路径上。`,
    solver_setup_zh: `<strong>Why this choice (本 case 的 solver 故意错)</strong>: icoFoam 是 incompressible 层流 PISO 瞬态 solver，在 Re_bulk=5600 只能收敛到 Poiseuille 抛物线——这是当前 adapter 的真实设定，也是 physics_contract precondition #1 显式标 false 的原因。选它作为"disguised incompatibility"的教学展示，不是因为这是正确路径。<strong>Main alternative (真正正确的路径)</strong>: 要复现 Moser 1999 Re_τ=180 turbulent DNS 有两条路 — (a) pisoFoam/pimpleFoam + LES (dynamicKEqn / WALE) + ≥百万 cells；(b) 直接 DNS 代码 (incompact3d 或 Nek5000)。RANS 的 simpleFoam + kOmegaSST 是工程折中，能给平均 u+ 但抓不住 turbulent statistics。<strong>When it breaks (当前 "wrong path" 的症状)</strong>: comparator 读 u+/y+ 数字没报错、tolerance 范围内 → ATTEST_PASS，但物理上是层流 Poiseuille 穿了一件 turbulent DNS 的外壳。physics_contract 的 precondition check 层把它显性降级到 FAIL；没有这层防线就是经典的 silent pass hazard。<strong>What to inspect</strong>: /constant/turbulenceProperties 里 simulationType=laminar (就是这个错)；/system/fvSolution 用 PISO + 层流方案；如果你看到 residuals 平滑下掉到 1e-8，这个 "收敛" 是层流解的收敛，不是湍流解。`,
    mesh_strategy_zh: `<strong>Why this choice (当前 mesh 对层流 Poiseuille 够, 对湍流 DNS 远远不够)</strong>: blockMesh 2D channel slab，半高 D/2=0.5m，流向 2·L=30m (伪长通道做 streamwise development)，typical 40×80 cells 给层流解析。<strong>Main alternative (Re_τ=180 DNS 需要的真实 mesh)</strong>: y 方向需要 ≥192 cells with wall-normal graduation 把第一 cell y+_wall<1 做到；流向要 ≥512 cells (periodic)；spanwise ≥192 cells (湍流是 3D)——合共 ~10⁷ cells 才能做 DNS. <strong>When it breaks (mesh-physics 不匹配的症状)</strong>: 当前 mesh 根本分辨不出 viscous sublayer (y+<5) / buffer layer (5<y+<30) / log region，所以任何 u+(y+) 数字都是层流解包装的，不是湍流 profile。<strong>What to inspect</strong>: blockMeshDict 里 cells 总数 (~3000-5000 for 2D laminar teaching)；如果你改成 Re_τ=180 真实 DNS setup，cells 会从几千暴涨到 ~10⁷。`,
    boundary_conditions_zh: `<strong>Why this choice (当前 BC 和 Moser DNS 也不兼容)</strong>: inlet fixedValue U=(1,0,0) + outlet 压力参考是 "developing channel" 的 BC，让流在 streamwise 方向发展；上下壁 no-slip；front/back empty 伪 2D。<strong>Main alternative (Moser DNS 的正确 BC)</strong>: 上下壁 no-slip + streamwise cyclic (periodic) + 用 fvOptions 给 driving pressure gradient 维持稳态 u_τ——这才是 "fully developed" 湍流 channel 的 canonical setup。当前的 inlet-outlet 路径让 streamwise development 永远不完成 true periodic state。<strong>When it breaks (和 Moser 对照不上的双重原因)</strong>: 即使 solver 换成 DNS，inlet-outlet BC 也不能给你 "fully developed" 状态；必须同时改 periodic + driving pressure。<strong>What to inspect</strong>: polyMesh/boundary 里 inlet+outlet patch types，如果真要 Moser-style 要改成 cyclic inlet-outlet 并在 constant/fvOptions 加 momentumSource。`,
    observable_extraction_zh: `<strong>Why this choice (observable math 正确但数据物理错)</strong>: src/plane_channel_uplus_emitter.py 从壁面 shear 算 u_τ=√(τ_w/ρ)，再换算 u+=U/u_τ 和 y+=y·u_τ/ν。这套 math 本身在湍流里是 canonical wall scaling——问题是当前 τ_w 来自层流 Poiseuille，产生的 u_τ 数字自洽但物理上不是 turbulent friction velocity。<strong>Main alternative (真正的 Moser 提取)</strong>: 对 DNS 场做 time-averaging + spanwise-averaging → mean profile ⟨U⟩(y)；再用 wall units 换算。核心差别：DNS 里 u_τ 是 statistical quantity 来自 ensemble average，不是单次稳态解的梯度。<strong>When it breaks (silent-pass 的发生机制)</strong>: comparator 不知道 "u_τ 来自层流还是湍流"，它只比数字大小。如果层流解给的 u_τ 和 turbulent u_τ 数值接近 (凑巧在 tolerance 里)，comparator 返回 PASS。physics_contract precondition #1 "flow is turbulent" = false 是 gate，把它从 ATTEST_PASS 降级到 physics-FAIL。<strong>What to inspect</strong>: postProcessing/ 里有没有 wallShearStress (若没有，emitter 是从 U 场自己算的)；comparator 的 verdict 如果是 PASS，一定要同时看 contract_status——只要 preconditions 有 false 就不是真通过。`,
    workflow_steps_zh: [
      { step: `(当前 "不兼容" 路径) 准备 icoFoam case`, detail: `foamNewCase 从 tutorials/incompressible/icoFoam/channel 起手，constant/transportProperties 设 nu=1.79e-4 给 Re_bulk=U·D/ν=1·1/1.79e-4≈5600。turbulenceProperties 不设（icoFoam 不读湍流模型）。`},
      { step: `2D channel 网格`, command: `blockMesh`, detail: `半高 D/2=0.5m, 流向 30·D, y-cells 80 + wall-grading 4:1, x-cells 40 uniform — 这 mesh 对层流 Poiseuille 够但远低于 Moser DNS 需要的 ~10⁷ cells (y-cells ≥192, spanwise ≥192)。`},
      { step: `BC 设置 inlet-outlet`, detail: `0/U inlet fixedValue=(1 0 0), outlet zeroGradient, 上下壁 fixedValue=(0 0 0), front/back empty。这是 developing channel 的 BC — Moser DNS 的正确 setup 是 streamwise cyclic + fvOptions momentumSource 驱动稳态 u_τ。`},
      { step: `启动 icoFoam 瞬态`, command: `icoFoam > log.icoFoam &`, detail: `controlDict::endTime 30 (≈30·D/U eddy turnover time)，deltaT 0.01。residual 降到 1e-8 后解进入 Poiseuille 抛物线稳态。`},
      { step: `emitter 抽 u+ y+`, detail: `src/plane_channel_uplus_emitter.py 在 x=15·D (developing 段中部) 取 y 方向 80 点 U_x profile, 用 wall stress 算 u_τ=√(τ_w/ρ), 再换算 u+=U/u_τ, y+=y·u_τ/ν。math 合法，但数据源是层流 Poiseuille，u+ 数字自洽但物理非湍流。`},
      { step: `comparator + precondition gate`, detail: `comparator 若只比数字可能返回 tolerance-within-band 的"通过"；physics_contract::precondition "flow is turbulent" = false，verdict aggregator 把 ATTEST_PASS 强制降到 FAIL/DISGUISED — 这是本 case 教学点：comparator 要配合 precondition gate 才能给诚实的 verdict。`},
    ],
    troubleshooting_zh: [
      { symptom: `comparator 返回 PASS 但 physics_contract 标 FAIL`, likely_cause: `这是本 case 设计的"disguised incompatibility"教学情景 — 数字在 tolerance 内但 preconditions 有 false。`, fix: `不是 bug — 是 feature。读 physics_contract::preconditions 确认 "flow is turbulent"=false，理解为什么 comparator 数字通过 ≠ case 通过；修复方向是切到 pimpleFoam+LES（Phase 9 工作）。`},
      { symptom: `解始终是 Poiseuille 抛物线，没有 turbulent fluctuation`, likely_cause: `solver 是 icoFoam 层流 PISO，Re_bulk=5600 虽已超过理论 transition Re≈2000-3000，但 2D + 光滑初场 + 无扰动 → 数值上稳定在 Poiseuille 不触发 transition。`, fix: `要真跑湍流必须换 pimpleFoam + LES + 3D domain + spanwise periodic + 初场加 0.1·U 随机扰动；单独调 icoFoam 参数换不出湍流。`},
      { symptom: `u+(y+) 曲线不是对数律`, likely_cause: `层流 Poiseuille 的 wall-unit 换算结果是 U=u_τ·y+/(1+linearish correction)，完全没有 viscous sublayer → buffer layer → log layer 的三段结构。`, fix: `预期行为 — 这是本 case 证明 "数字在 wall units 里依然可算出来但 physics 不对"。如要看真正对数律必须上 DNS/LES。`},
      { symptom: `想修成真湍流但 mesh 爆内存`, likely_cause: `Re_τ=180 DNS 对 3D domain 需要 ~10⁷ cells + 所有 spanwise + streamwise 点，单机内存容易撑爆 32GB。`, fix: `先把目标降到 LES 模式 (x-cells 256, y-cells 128, z-cells 128 ~4M cells)，用 dynamicKEqn LES model；DNS 交给 incompact3d/Nek5000 专业代码。`},
      { symptom: `residual 降到 1e-8 但图形看上去是层流`, likely_cause: `low residual 只说明数值收敛，不说明 physics 对。层流 Poiseuille 的稳态解给 residual 可以任意低。`, fix: `不要把 residual level 当 physics validity 指标；用 physics_contract::preconditions 作为独立的 gate 层，这就是 DEC-V61-046 tri-state verdict 的设计点。`},
    ],
    benchmark_lineage_zh: {
      why_primary: `Moser/Kim/Mansour 1999 是 turbulent channel DNS 的 "citation standard"——继承自 Kim/Moin/Moser 1987 在 Re_τ=180 的开创性 DNS，1999 年扩到 Re_τ=395/590，数据集对整个湍流建模社区公开。选它作为 gold 有两层价值：(a) DNS 意味着无湍流模型假设，是 RANS/LES 真正的 ground truth；(b) Re_τ=180 是"够充分发展 + 计算可行"的甜点，后续几乎所有 wall-bounded turbulence 建模论文都先在 180 通过。本 case 的诚实点在于：我们跑 icoFoam laminar 是故意不兼容，让学生看到"comparator 数字通过但物理错"是什么样——真正用 Moser 数据做 RANS 验证需要切换到 pimpleFoam/LES pipeline (Phase 9 规划)。`,
      secondary: [
        `Kim, Moin & Moser 1987 · J. Fluid Mech. · 首篇 Re_τ=180 channel DNS · 开创 wall-bounded 湍流 DNS 时代`,
        `Hoyas & Jiménez 2006 · Phys. Fluids · DNS at Re_τ=2000 · 高 Re 扩展数据`,
        `Lee & Moser 2015 · J. Fluid Mech. · DNS at Re_τ=5200 · 当前 state-of-the-art`,
        `Dean 1978 · J. Fluids Eng. · pressure drop 经验关系 f_Darcy(Re_bulk) · 工程估算基准`,
      ],
      next_reading: `学完 "ATTEST_PASS ≠ physics-compatible" 这一诚实性 lesson 之后：(1) 去 Kim-Moin-Moser 1987 读 Re_τ=180 DNS 原始论文，理解 wall-unit scaling 为什么是湍流湍流建模的语言；(2) 读 Pope 2000《Turbulent Flows》第 7 章 channel & pipe flow 教材化处理；(3) 做 hands-on：在 Hoyas-Jiménez 2006 提供的数据上试一次 RANS k-ω SST 对比，观察 log-law region 是否对得上——这才是"真正 RANS vs DNS 验证"的入门。`,
    },
  },
  {
    id: "impinging_jet",
    // DEC-V61-047 round-1 F5: 两个独立 hazard：(1) adapter 是 2D planar 切片，
    // 不是 axisymmetric wedge；(2) buoyantFoam p_rgh 没收敛（A4 iteration cap）。
    // contract_status = INCOMPATIBLE_WITH_LITERATURE_DISGUISED_AS_COMPATIBLE。
    // 先讲清 gap，再讲物理。
    displayName: "Impinging Jet (geometry + solver gap teaching)",
    headline_zh: `冲击射流：几何简化 + 收敛 gap 的双层教学`,
    headline_en: "Impinging jet · two-layer gap teaching",
    teaser_zh: `典型工业冷却问题：射流撞底板，驻点传热最强。但本仓库这 case 故意保留两个诚实的 gap：adapter 跑的是 2D 平面切片（不是 axisymmetric 楔形）；solver p_rgh 迭代到帽也没收敛。两件事叠加——学生能看到"物理在说什么"和"代码实际算什么"之间的距离。`,
    canonical_ref: "Cooper 1984 / Behnad 2013 (axisymmetric experiment + RANS)",
    observable: "Nu(r/D) 驻点传热分布（文献预期 Nu_peak=25）",
    difficulty: "advanced",
    physics_bullets_zh: [
      `文献 gold：真正的 axisymmetric 射流，驻点 Nu=25（径向汇聚）`,
      `当前 adapter：axis 是 empty patch 不是 wedge → 只是 2D 平面`,
      `湍流模型 kEpsilon：在驻点各向异性下系统偏（v2f 更合适）`,
    ],
    why_validation_matters_zh: `这个 case 教的是"几何简化会不会悄悄作用在结果上"。2D 平面切片把径向汇聚效应拿掉了——驻点 Nu 物理上就不应该那么高。 即使换 solver 收敛了，2D-vs-axisymmetric 的差距也不会消失。验证思维的第一步：先看 adapter 实际建的 geometry，再看 solver 跑没跑收敛，再看 model 选得是否合理。三层 gap 叠加时，"PASS" 完全是假的。`,
    common_pitfall_zh: `新手常以为"label 说 axisymmetric 就是 axisymmetric"。要确认 axis patch 类型 (OpenFOAM 里 wedge vs empty 是完全不同的)。另一个坑：看到 Nu 数值接近文献就以为 case 通过——但如果驻点 Nu 值是 0.0042 (Cf 量纲不是 Nu 量纲)，说明 extractor 把完全错的 quantity 当 Nu 输出了，这种 silent 错误比不收敛还危险。`,
    solver_setup_zh: `<strong>Why this choice</strong>: buoyantBoussinesqSimpleFoam (稳态浮力耦合 SIMPLE) + RAS kEpsilon，Re=10000 基于 D=0.05m 和入口速度 U_jet 设定。稳态选择因为 canonical Cooper 1984 experiment 在 steady regime；Boussinesq 因为温差 ΔT/T_ref 足够小；kEpsilon 是 40 年 jet benchmark 的历史默认。<strong>Main alternative</strong>: v2-f (Durbin 1991) 和 kOmegaSST 在 stagnation heat transfer 上比 k-ε 更准 (系统偏差从 k-ε 的 50-100% 降到 10-30%)，因为它们对 stagnation streamline 的 anisotropic turbulence 有特殊处理；LES (WALE) 给 time-resolved Nu(r) 但算力 ×100. <strong>When it breaks (当前症状)</strong>: p_rgh 的 GAMG solver 持续打到 1000 iter cap 而没收敛——composite 症状：URF 太激进 (T=0.7 在 buoyant coupling 里过高)、p-v coupling 不够紧、thermal BC 与 Boussinesq reference 不兼容、axis patch 处理错 (empty 而非 wedge)。<strong>What to inspect</strong>: fvSolution 的 p_rgh solver 是否是 GAMG+nSweeps=2、T URF 是否 <0.4、residual log 看 p_rgh 是否震荡不降；Phase 9 solver-config audit 专门解这套 multi-factor root cause。`,
    mesh_strategy_zh: `<strong>Why this choice (当前 mesh 的简化诚实)</strong>: blockMesh 生成 r-z 矩形域，r=[0, 5·D], z=[-D/2, H+D/2]，约 4800 cells 结构网格。axis patch 在 OpenFOAM 的 boundary file 里标为 "empty"——这不是 axisymmetric wedge，是 2D 平面切片。<strong>Main alternative (真实 axisymmetric 的 mesh)</strong>: 需要 wedge boundary (type wedge + 专用 rotational-axis treatment)；blockMesh 做 2° 楔形+ 周期对称+ axis line 在 z=0 上。几何本质是 r-z 轴对称 → 真实 Nu_peak 来自径向汇聚的 thermodynamic concentration，2D 平面切片把这个效应直接拿掉。<strong>When it breaks</strong>: 2D-planar 会 under-predict 驻点 Nu (文献 25 vs 2D 预测可能 15-18)；近壁 y+ 对 k-ε wall functions 要 >30 (vs 低雷诺数 modification 要 <1)。<strong>What to inspect</strong>: constant/polyMesh/boundary 里 axisPatch 的 type (当前 empty, 正确 axisymmetric 应该是 wedge)；cells 里径向分辨率 (near-axis 需要额外加密)。`,
    boundary_conditions_zh: `<strong>Why this choice (BC 设计符合 steady RANS 但几何简化)</strong>: inlet (nozzle 出口) fixedValue U 给定射流速度 + 由 Re=10000 反推；impingement plate (z=z_max) fixedValue T=T_hot (加热壁) + no-slip U；其余壁 fixedValue T=T_cold + no-slip；axis r=0 用 empty (伪 2D)；outlet (r=r_max) zeroGradient。<strong>Main alternative (canonical axisymmetric BC)</strong>: axis 改为 wedge 配合 wedge mesh — 给真实轴对称；若做 LES，outlet 改为 convective BC 防止反射；inlet 给带湍流扰动的 turbulent intensity 5-10% 而不是 uniform。<strong>When it breaks</strong>: axis empty 而非 wedge → 径向汇聚物理不成立；outlet 太近 (<3·D) → impingement wake 被出口反射；nozzle-to-plate 距离 H/D 错 (应该是 2.0，若写成 4.0 流动是 free jet impingement 完全不同 regime)。<strong>What to inspect</strong>: polyMesh/boundary 里 axisPatch 类型；0/T 里 impingement plate T_hot vs cold walls T_cold 的差值；constant 里 transportProperties 的 thermal diffusivity α。`,
    observable_extraction_zh: `<strong>Why this choice</strong>: Nu(r/D) = -D·∂T/∂n|_wall / (T_hot - T_ref) 是 Cooper 1984 的 canonical observable。沿 impingement plate 从 r=0 (stagnation) 到 r=5·D 扫描 — 驻点 Nu 最大 (文献 25)，径向衰减到 r/D≈3 处 Nu≈10。src/wall_gradient.py 在有温度场时做 wall-normal gradient (用 interior cells 避免 wall degeneracy)。<strong>Main alternative</strong>: 若做 LES 要 time-average Nu_inst(r, t) ≥10 个 flow-through times 得稳态 Nu；若做 heat flux 直接 fixedHeatFlux BC (wall heat flux 已知) 反算 T_wall，这是工业 heat exchanger 设计的常用路径。<strong>When it breaks (当前的保护机制)</strong>: 当前 p_rgh 没收敛 → ATTEST_FAIL 触发于 A4 stage 早于 comparator 调用 → 没有假 Nu 数字输出的机会。历史上曾经 extractor bug 让 ref_value=0.0042 (Cf 量纲) 被当作 Nu 输出，这是 silent quantity leakage，是物理 contract 层存在的原因之一。<strong>What to inspect</strong>: postProcessing 里 wallHeatFlux functionObject 的输出 (q_wall field)；comparator output 的 Nu_peak (r=0) 应在 10-25 之间，数字低于 10 说明 stagnation zone 没正确算。`,
    workflow_steps_zh: [
      { step: `(当前 2D 简化) 画 r-z 矩形域`, detail: `blockMesh 做 r=[0, 5·D], z=[-D/2, H+D/2] 的 2D 矩形，h/D=2.0 让 nozzle-to-plate 距离满足 Cooper setup。~4800 cells 结构网格，plate 上 wall-grading 4:1 让 y+<30 满足 kEpsilon wall-function。`},
      { step: `关键诚实：axis 设 empty (不是 wedge)`, detail: `constant/polyMesh/boundary 里 axisPatch type=empty — 这明确告诉 OpenFOAM 这是 2D 平面切片。真 axisymmetric 要 type=wedge + blockMeshDict 做 2° 楔形 + axis line 在 z=0；当前 setup 诚实地不装假。`},
      { step: `设置 thermal BC + Boussinesq`, detail: `constant/transportProperties 给 nu, beta (thermal expansion), rho_0, T_ref；0/T 在 impingement plate fixedValue=T_hot, 其他壁 T_cold；0/U inlet fixedValue=U_jet 由 Re=10000 反推；outlet zeroGradient。`},
      { step: `配置 buoyantBoussinesqSimpleFoam`, detail: `turbulenceProperties RAS kEpsilon；fvSolution 的 p_rgh 用 GAMG tolerance 1e-6 + nSweeps 2；T URF ≤0.4（降低 thermal coupling 的刚性）；U URF 0.5, p_rgh URF 0.3。`},
      { step: `启动 + 观察 p_rgh 收敛`, command: `buoyantBoussinesqSimpleFoam > log.solve &`, detail: `controlDict endTime 2000 (SIMPLE 里是 iter cap)。foamLog 关键看 p_rgh_0 曲线：若 A4 stage 到 iter cap 1000 仍 >1e-3 就是 "disguised incompatibility" 的 solver 症状 — 本 case 目前就是这个状态。`},
      { step: `抽 Nu(r/D)`, detail: `wall_gradient.py 沿 impingement plate 从 r=0 到 r=5·D 取 ∂T/∂z, 算 Nu(r/D)=-D·∂T/∂z|_wall/(T_hot−T_ref)。预期峰值 Cooper Nu=25 — 2D 平面切片 + kEpsilon 下预测 Nu_peak 15-18 (低 30%)；配合 p_rgh 不收敛的 gap 叠加 → contract_status=disguised.`},
    ],
    troubleshooting_zh: [
      { symptom: `p_rgh residual 打到 iter cap 1000 仍 >1e-3`, likely_cause: `composite root cause：T URF 太高（>0.4）+ GAMG nSweeps 太少（=1）+ axis patch 是 empty 破坏 r=0 附近的 pressure-velocity coupling 规整性。`, fix: `三步依次试：(1) T URF 降到 0.2；(2) GAMG nSweeps 升到 3；(3) 若仍不收敛，这是 Phase 9 solver-routing 要重建 axisymmetric_wedge 路径的 root cause，承认当前 case 无法单靠调参修好。`},
      { symptom: `Nu_peak 算出来是 0.0042`, likely_cause: `extractor bug 把 Cf (skin friction) 当 Nu 输出，单位 quantity leakage — 历史上出现过。`, fix: `检查 wall_gradient.py 是否在 temperature-field-available 时优先用 ∂T/∂n，否则会 fallback 到 velocity gradient 给 Cf-量纲数字；本仓库已加保护。若你改了 extractor 必须单元测试这个 fallback 路径。`},
      { symptom: `Nu_peak ≈ 15-18, 显著低于 Cooper 25`, likely_cause: `2D planar slice 几何没有径向汇聚效应 + kEpsilon 在 stagnation anisotropy 下系统低估 turbulent transport。`, fix: `不是 bug — 这是 "几何简化 + 模型选择" 两层叠加的可预期偏差。修方向：mesh 改 axisymmetric wedge + 湍流模型换 v2-f 或 kOmegaSST；预期 Nu_peak 升到 20-23 接近 Cooper。`},
      { symptom: `driving pressure 源项造成 buoyant 场震荡`, likely_cause: `Boussinesq reference T_ref 选错（比如选了 T_hot 而非 (T_hot+T_cold)/2），导致浮力项大小严重偏差。`, fix: `constant/transportProperties::TRef 设为 case 平均温度；beta 用 1/T_ref (ideal gas)；重启 solver，p_rgh residual 应比之前低一到两个 order。`},
      { symptom: `comparator 返回数字 PASS 但 Nu_peak=0`, likely_cause: `某些 subversion 的 extractor 在 "未收敛" 状态抽 wall temperature gradient 得到 ≈0 (稳态未建立)，comparator tolerance 过松被骗过。`, fix: `verdict 分层：ATTEST 层先检查 solver convergence (p_rgh level)，再调 comparator；一定同时查 contract_status — preconditions 标 false 就不算真通过。`},
    ],
    benchmark_lineage_zh: {
      why_primary: `Cooper 1984 (Cooper, Jackson, Launder & Liao) 是 axisymmetric impinging jet 的经典基准实验，在 Re=10000 给出驻点 Nu=25 + 径向 Nu(r/D) 分布。选它作为 gold 不是因为它最新，而是因为：(a) 几何干净 (D=0.05m 喷嘴、h/D=2.0、加热平板)，复现实验条件简单；(b) 数据表 + 图全公开，后续研究普遍以它做回归；(c) Baughn & Shimizu 1989 用类似几何更仔细地量测了 Nu(r/D)，但 Cooper 的 Re=10000 正好在"RANS 应该能对付"和"RANS 开始吃力"的分界线上，对教学 k-ε vs v2f 的区别特别合适。当前 adapter 的 2D planar slice 简化是承认"还没做到 axisymmetric wedge"的诚实声明。`,
      secondary: [
        `Baughn & Shimizu 1989 · J. Heat Transfer · Nu(r/D) 精细实验 at Re=23750 · 现代标准参考`,
        `Behnad et al. 2013 · Int. J. Heat Fluid Flow · Cooper benchmark 的 v2-f RANS 再验证 · 模型选择参考`,
        `Hofmann et al. 2007 · Int. J. Heat Fluid Flow · impinging jet 综述 · 建立 parameter space 全景`,
        `Jaramillo et al. 2008 · Int. J. Heat Mass Transfer · v2-f 在 stagnation heat transfer 上系统评估 · 支持 "为什么 k-ε 系统偏 50-100%"`,
      ],
      next_reading: `学完"几何简化 + 收敛 gap 双层教学"之后：(1) 读 Baughn-Shimizu 1989 看 Nu(r/D) 精细实验应该什么样——这能告诉你峰值真实高度；(2) 读 Behnad 2013 + Jaramillo 2008 理解为什么 v2-f 比 k-ε 在 stagnation region 更准，这是 RANS 湍流建模里 "anisotropy" 真正决定预测精度的罕见案例；(3) 想做真正 axisymmetric OpenFOAM 案例可以读 OpenFOAM Foundation tutorials 里的 axisymmetric_wedge 示例，把当前 empty patch 换成真 wedge。`,
    },
  },
  {
    id: "naca0012_airfoil",
    displayName: "NACA 0012 Airfoil",
    headline_zh: `翼型与压强`,
    headline_en: "Airfoil pressure distribution",
    teaser_zh: `对称翼型的表面压强系数 Cp 分布。入门外流问题，航空界最常用的验证基准之一。`,
    canonical_ref: "Ladson et al. · NASA TM 1996",
    observable: "Cp distribution along chord",
    difficulty: "core",
    // DEC-V61-047 round-2 N1: Authoritative setup per knowledge/whitelist.yaml
    // + knowledge/gold_standards/naca0012_airfoil.yaml + src/foam_agent_adapter.py:
    // Re=3e6 (NOT 6e6), α=0° (NOT ≈4°) — symmetric airfoil at zero incidence
    // gives attached flow + zero lift. Earlier round-1 solver card mis-cited
    // α≈4°/Re=6e6, which would teach the wrong canonical setup to a novice.
    physics_bullets_zh: [
      `0° 攻角下对称翼型——attached flow，零升力`,
      `Cp 分布沿弦长是 canonical 压强场验证量`,
      `远场边界距离直接影响解（< 15 倍弦长会产生伪 blockage）`,
    ],
    why_validation_matters_zh: `Ladson / Thomas 的 NASA 风洞数据是公开基准之一，对称翼型 α=0° 是入门验证：attached flow、无分离、压强分布可由简单 RANS 稳态收敛。你的 CFD 要做更复杂的外流（带攻角、带分离、机翼、螺旋桨），必须先在 NACA 0012 零度这一关拿到可控误差——这是航空 CFD 验证流水线的"第一道门"。`,
    common_pitfall_zh: `远场边界放得太近（<15 倍弦长）是最常见的新手错误——虚假 blockage 让整个压强场 shifted，网格无关性测试抓不到。另一个陷阱：本 case 的 Cp 提取是 near-surface band 平均（adapter 在壁面上方 ~2% 弦长厚度带里取 cell-center 均值），与文献的"exact surface"定义相比系统性衰减 30-50%，形状对、幅值小——这也是 gold 容差设为 20% 并用 PASS_WITH_DEVIATIONS 的原因。`,
    solver_setup_zh: `<strong>Why this choice</strong>: simpleFoam (稳态 SIMPLE) + RAS kOmegaSST。α=0° 对称翼型是 attached flow (符合 physics_contract precondition #1 "steady at α=0")，稳态合理；kOmegaSST 是航空 RANS 默认选择 (Menter 1994)，它融合了 k-ω 近壁精度和 k-ε 远场稳定性，是 NACA benchmark 社区公认。URF: p=0.3 (GAMG, relTol=0.05, tolerance=1e-6); U/k/ω=0.5 each。<strong>Main alternative</strong>: Spalart-Allmaras (1 equation 更稳、更便宜，但驻点 heat transfer / separation 精度略低)；inviscid Euler 解析 (忽略 BL 时适用于外流 Cp 估算)；XFOIL 面板法 (2D 势流 + integral BL model，不跑 CFD 但出 Cp 曲线)。<strong>When it breaks</strong>: URF p>0.5 → pressure field 在 leading-edge stagnation 震荡；iterations <1000 → Cp 还没稳态；kOmegaSST 在 y+=15-30 之间的 transitional region 会有 blended-function artifacts。<strong>What to inspect</strong>: fvSolution 的 p relax factor；residual log 里 p 掉到 1e-6、U/k/ω 到 1e-5 才算收敛；time/controlDict 里 endTime ≥1000 iterations。`,
    mesh_strategy_zh: `<strong>Why this choice (adapter 的 blockMesh 路径)</strong>: adapter 直接用 OBJ geometry 生成 x-z 平面 blockMesh — z (wall-normal) 方向 80 cells + graduation 贴翼型表面；y (展向) 薄 ±0.001 + empty side patches 做伪 2D。远场至少 15·c 距离避免 blockage。<strong>Main alternative</strong>: C-grid 或 O-grid (snappyHexMesh + topoSet) 能更好贴 airfoil curvature 但对 teaching case blockMesh 已够；不连续 surface-conformal refinement (foamMeshTools) 能做得更精细但调参复杂。<strong>When it breaks</strong>: 远场 <15·c → 虚假 blockage 让整个 Cp 曲线上下平移；第一 cell y+_wall 超出 kOmegaSST 的 blended-function 工作区 (y+=15 附近) → Cp 曲线震荡；surface_band=max(8·dz_min, 0.02·c) 厚度不够 → 采样 cells 进到自由流区。<strong>What to inspect</strong>: blockMeshDict 里 cells 总数 (2D 结构 ~10000-30000 for teaching)；y+_wall 用 postProcess yPlus function object 检查 (应该 <5 或 >30，不要在 transition zone)；远场距离量一下 domain.stl 的 bbox。`,
    boundary_conditions_zh: `<strong>Why this choice (α=0° 的精简 BC)</strong>: 上游 + 横向 inlet/freestream fixedValue U=(U_∞, 0, 0) (零攻角 → 无 sin α 分量)；下游 outlet 压力 zeroGradient + U inletOutlet (允许回流自然出去)；翼型表面 no-slip U=(0,0,0) + k/ω wall functions；展向 front/back empty 模拟 2D。<strong>Main alternative (α>0 的 BC)</strong>: inlet U=(U_∞·cos α, U_∞·sin α, 0) + 远场外侧 freestreamVelocity 自适应(根据当地流速选 inlet 或 outlet)；α>10° 接近 stall 要 transient + LES；转捩敏感 angle 加 k-omega-SST + γ-Re_θ 转捩 model。<strong>When it breaks</strong>: 远场 <15·c → 虚假 blockage，升力系数 C_l 被压低 10%+ 而且网格无关性测试抓不到；inlet 改成 freestream + outlet fixedValue 反而更稳但配置复杂。<strong>What to inspect</strong>: 0/U 里 freestream U=(1,0,0) (注意：不是 (1,0.087,0) 那种 5° 攻角 setup)；0/k, 0/omega 用 kqRWallFunction, omegaWallFunction 匹配 kOmegaSST；0/p outlet fixedValue=0 做 reference。`,
    observable_extraction_zh: `<strong>Why this choice (near-surface band 的诚实缺陷)</strong>: Cp(x/c) = (p - p_∞) / (0.5·ρ·U_∞²)。src/foam_agent_adapter.py:7068 的 extractor 在翼型表面上方 surface_band=max(8·dz_min, 0.02·c) 厚度带里取 cell-center 做 patchAverage，按 x/c 分 upper/lower surface。band 做 0.02·c (~2% 弦长) 是因为 surface cells 太接近 boundary 会 degenerate；这不得不平均一个 layer 的 cells。<strong>Main alternative</strong>: 用 patchField sampling 直接在 wall patch 上 extract (canonical method) — 更精确但 OpenFOAM 的 pressure field 在 no-slip wall 上是 zeroGradient，与 freestream reference 有 cell-center offset；用 wall-normal probes array 一点一点采样是第三种路径。<strong>When it breaks (PASS_WITH_DEVIATIONS 的根源)</strong>: 精确文献 Cp 是 exact surface 点值，adapter 是 near-surface cell average → 形状正确但幅值系统衰减 ~30-50% (physics_contract precondition #3 明确标 satisfied=false)。容差设 20%、verdict PASS_WITH_DEVIATIONS 就是承认这个系统误差是 extraction-level 而非 solver-level。<strong>What to inspect</strong>: postProcessing 里 sample cp_upper.csv 和 cp_lower.csv (x/c, Cp 对)；对比 Ladson 1996 数据时直接 shape 对齐，不要对绝对 Cp 值做严格 tolerance。`,
    workflow_steps_zh: [
      { step: `载入 NACA 0012 几何`, detail: `从 airfoiltools.com 下载或用 NACA 4-digit 生成器输出 OBJ/STL：y/c = 0.594·(√(x/c) − 0.126·x/c − 0.358·(x/c)² + 0.291·(x/c)³ − 0.103·(x/c)⁴)，chord c=1m，200 discretization 点够教学。`},
      { step: `blockMesh 生成远场`, detail: `x-z domain 外框 [-15·c, 20·c] × [-15·c, 15·c]，z 方向 80 cells + wall-graduation 4:1 贴 airfoil 表面；y 方向薄 ±0.001 + empty 做伪 2D。adapter 用 blockMesh 路径（非 snappyHexMesh）。`},
      { step: `配置稳态 RANS + α=0°`, detail: `constant/turbulenceProperties RAS kOmegaSST；0/U freestream fixedValue=(1 0 0)（注意零攻角，不是 (1 0.087 0)）；Re=3e6 ⇒ ν=1/3e6=3.33e-7；翼型表面 no-slip + k/ω wall functions (kqRWallFunction, omegaWallFunction)。`},
      { step: `残差设置`, detail: `fvSolution 的 p solver GAMG + tolerance 1e-6 + relTol 0.05；p URF 0.3，U/k/ω URF 0.5；controlDict endTime 2000 (SIMPLE iteration cap)，residualControl::p 1e-6 自动停止。`},
      { step: `启动并检查 y+`, command: `simpleFoam > log.simpleFoam &`, detail: `跑 500 iter 后用 postProcess -func yPlus 快速扫 y+_wall，保证在 <5 (kOmegaSST 低 y+ 支路) 或 >30 (log-law 支路)；落在 5-30 blended-function transition zone 会让 Cp 曲线震荡。`},
      { step: `抽取 near-surface Cp`, detail: `extractor 在翼型表面上方 surface_band=max(8·dz_min, 0.02·c) 厚度带里取 cell-center 做 patchAverage 按 x/c 分 upper/lower surface。comparator 比 Thomas/Lada gold 做 shape alignment，容差 20% 的原因是 near-surface band 对 exact surface 系统衰减 30-50%。`},
    ],
    troubleshooting_zh: [
      { symptom: `Cp 曲线整体上下平移 0.1`, likely_cause: `远场边界 <15·c，虚假 blockage 把 p_∞ 参考值偏了。`, fix: `blockMeshDict 把外框扩到 ≥15·c × ≥15·c；重生成网格重跑；网格无关性测试无法抓到这类 domain-size 引起的 shift，必须用经验规则。`},
      { symptom: `Cp 在 x/c=0.05 (leading edge 下游) 剧烈震荡`, likely_cause: `y+_wall 落在 kOmegaSST 的 blended-function transition 区 (5<y+<30)。`, fix: `调 wall-normal grading 让 first cell y+ 明确 <5 (低 y+ 支路) 或 >30 (log-law 支路)；用 postProcess -func yPlus 确认分布。`},
      { symptom: `comparator verdict 是 FAIL 但 Cp 曲线形状看起来对`, likely_cause: `adapter 的 near-surface band 采样让幅值系统衰减 30-50%；tolerance 如果按 "per-point 10% absolute" 会失败。`, fix: `physics_contract precondition #3 (exact-surface extraction) 标 false + 容差设 20% + verdict 允许 PASS_WITH_DEVIATIONS —— 本仓库已如此；修 comparator 让它做 shape correlation 而非 per-point tolerance。`},
      { symptom: `solver 跑了 2000 iter p residual 仍 >1e-3`, likely_cause: `URF p 设太高（0.5+），leading-edge stagnation 的 pressure peak 被过度放大。`, fix: `fvSolution relaxationFactors p 0.3；同时 nNonOrthogonalCorrectors 加到 2；翼型附近 mesh 非正交性高时 (max non-orthogonality>60) 一定要开这个。`},
      { symptom: `Cl 明显非零 (α=0° 对称翼型)`, likely_cause: `mesh 或 BC 存在上下不对称（常见：graduation ratio 上下不一致，或 inlet U 写成 (1 0.087 0) 带了 5° 攻角）。`, fix: `检查 0/U freestream 向量（应精确为 (U_∞, 0, 0)）+ blockMeshDict 上下 blocks 的 cells/graduation 完全镜像；对称翼型 α=0° 零升力是 physics benchmark，Cl>0.01 就是 setup bug。`},
    ],
    benchmark_lineage_zh: {
      why_primary: `NACA 0012 的 Cp 分布有三组常被引用的数据源：(1) Thomas 1979 (AIAA 79-1466) 的早期风洞 + CFD 对比；(2) Ladson 1996 NASA TM 4074 的系统性风洞实验（多攻角 + 多 Re）；(3) Lada & Gostling 2007 的 engineering fit。本 harness 的 gold YAML header 注明 source 是 "Thomas 1979 / Lada & Gostling 2007"——选 Thomas 是因为它是 historical anchor，选 Lada 是因为它把 Thomas 的 exact surface 数据整理成可用表格。把 Ladson 1996 作为 canonical_ref 字符串是 display 层的简写——graduate student 应该知道 三者都存在，且本 case 的 gold 数字取自 Thomas/Lada 的 α=0° 段。`,
      secondary: [
        `Thomas 1979 · AIAA 79-1466 · 首组 NACA 0012 系统 Cp 风洞实验`,
        `Ladson 1996 · NASA TM 4074 · 多-α 多-Re 现代风洞数据库 · 更宽 parameter space`,
        `Lada & Gostling 2007 · NAG report · 把 Thomas 数据整理成 ref 表格 · gold 直接数据源`,
        `Anderson 2010 · Fundamentals of Aerodynamics 5th ed. Ch.4 · Cp 分布的 textbook 推导`,
      ],
      next_reading: `学完 α=0° 对称翼型 Cp 之后：(1) 上攻角 — 读 Ladson 1996 的 α=5°/10° 数据看 upper suction peak 如何演化，以及 Cl 开始线性；(2) 读 Anderson 《Fundamentals of Aerodynamics》第 4 章理解 Kutta condition 和 thin airfoil theory 如何解释 Cp 形状；(3) 若做 CFD 精度升级 — 读 Rumsey & Vatsa 1995 NASA TM 对 NACA 0012 的 Navier-Stokes vs Euler vs panel-method 系统比较，看 near-surface 提取误差如何量化。`,
    },
  },
  {
    id: "rayleigh_benard_convection",
    displayName: "Rayleigh-Bénard Convection",
    headline_zh: `对流不稳定性`,
    headline_en: "Convective instability",
    teaser_zh: `下热上冷的流体层，在 Rayleigh 数超过临界值后自发形成周期性对流胞。漂亮而深刻。`,
    canonical_ref: "Chandrasekhar 1961 / Grossmann-Lohse 2000",
    observable: "Nusselt number Nu(Ra)",
    difficulty: "advanced",
    physics_bullets_zh: [
      `Ra_c ≈ 1708 是临界值`,
      `Ra > Ra_c 后出现 Bénard cells`,
      `Nu 随 Ra 的标度率是湍流建模的试金石`,
    ],
    why_validation_matters_zh: `Nu ~ Ra^α 这个标度率的指数 α 是 CFD 最经典的"硬问题"之一——湍流对流传热研究了几十年，不同文献给不同的 α（0.28-0.33）。你的数值 α 落在哪个区间，直接揭示了你用的数值方案和网格的极限。`,
    physics_intuition_zh: `想象一层水，底下一块加热板，顶上一块冷却板，温差 ΔT 很小。底层流体被加热后密度变小想往上浮，顶层流体被冷却后密度变大想下沉——但这种浮力要克服两件事才能真正动起来：黏性粘滞（流体粘在自己身上拒绝流动）和热扩散（温差在没流动的情况下通过传导直接抹平）。三者的比值正是 Rayleigh 数 Ra = g·β·ΔT·L³ / (ν·α)；它必须超过一个临界值 Ra_c=1708（Rayleigh 1916 理论 + Chandrasekhar 1961 推到可计算形式）才有对流出现。低于 Ra_c，整层流体静止不动，热量只靠传导从底走到顶，看上去就是一条线性 T 剖面；一旦 Ra 越过 1708，突然出现周期性的上升-下降条带——Bénard cells——底热上冷的热斑由 plume 形式向上贯穿，冷的从反方向下沉，形成一对对垂直循环。\n\n继续增大 Ra，这个物理演化经过至少四段：(1) Ra=10³-10⁴ 近临界区，cells 几乎对称正六边形（若 3D）或平行长条（若 2D），Nu~Ra 线性；(2) Ra=10⁴-10⁷ soft turbulence 区，cells 开始时间演化、plume 和 thermal layer 结构化，Nu~Ra^(1/4) 左右；(3) Ra~10⁷-10¹¹ hard turbulence / ultimate regime 过渡区，Nu~Ra^(2/7)=0.286 (Grossmann-Lohse 2000 给这个 scaling 的严格理论框架，融合之前几十年经验规律); (4) Ra>10¹² 推测的 ultimate regime Nu~Ra^(1/2)（Kraichnan 1962 预测，至今实验未完全证实）。指数 α 的"不确定性"不是测量精度问题，是 regime 本身在变化；你选 Ra=10⁶ 跑出 Nu≈8.3、α≈0.27，落在 (2) 的甜点上。\n\n本 case 在教学上罕见的价值是：它让学生直接看到"bifurcation"在 CFD 里是什么意思——同一组 BC、同一个方程、不同的 control parameter Ra 给出**质变**不同的解。当你把 Ra 从 1500 慢慢推到 1710，解不是连续变化 1% → 2%，而是突然从"绝对静止 + 线性 T 剖面"跳到"有方向的 circulation"；这是非线性 dynamics 在一个可解析 PDE 里最干净的展示。你的工业 CFD 任何时候遇到 "Re / Gr / Ra 附近有 regime 转换" 的工况，请回到 RBC 的 bifurcation 图上想想 — 那是所有 CFD "参数附近解突变" 的母问题。`,
    common_pitfall_zh: `Boussinesq 近似（密度只随温度变化、其余性质不变）是这个案例的标配，但它只在温差较小的时候成立。如果你在 ΔT/T0 > 0.1 的条件下还用 Boussinesq，预测会系统偏，而且很难 debug。`,
    solver_setup_zh: `<strong>Why this choice</strong>: buoyantBoussinesqSimpleFoam (稳态浮力 SIMPLE) + turbulenceProperties=laminar。Ra~1e6 介于 soft turbulence 与强层流对流之间 (湍流对流过渡 ~Ra=1.5e8)，稳态 laminar 是合理初阶。Boussinesq：ρ 只在浮力项里随 T 线性变，黏性/热扩散保持 constant，在 ΔT/T_ref<0.1 精确。<strong>Main alternative</strong>: pimpleFoam + LES (WALE) 在 Ra>1e7 必要 (RBC 进入 oscillating)；compressible rhoPimpleFoam 在 ΔT/T_ref>0.1 时替代 Boussinesq；非结构 adaptive refinement 对 plume-tracking 可能更精 (但复杂度 ×5)。<strong>When it breaks</strong>: Ra>1e7 用 laminar → Nu 数字对，但 solution 其实在 oscillating (gold YAML 记录 "OSCILLATING but Nu stable"); gravity 方向反 (+z) → 重流体在上 stable stratification 对流不起；T URF>0.6 → T 场在 plume 形成区震荡。<strong>What to inspect</strong>: constant/g 里 gravity vector；constant/transportProperties 里 beta (thermal expansion), TRef, Pr=0.71；residual log 里 T 是否单调减或 oscillating。`,
    mesh_strategy_zh: `<strong>Why this choice</strong>: blockMesh 方腔 2D 结构均匀网格 40-80 cells per side (1600-6400 cells)。Ra=1e6 的对流 cells 尺度 ~ 0.5·H (domain half-height)，uniform 40-80 cells 足够分辨 cell 结构；热边界层 δ_T/L ≈ Ra^(-1/4) ≈ 0.032，5-10 层 cells 落在 δ_T 内。<strong>Main alternative</strong>: wall-graded mesh (壁面密、中心疏) 对 Ra=1e8+ 湍流 essential (δ_T 退到 0.006·L)；非结构 mesh (snappyHexMesh) 对方腔 overkill；AMR (动态加密 plume) 可追踪瞬时 plume 但当前稳态解不需要。<strong>When it breaks</strong>: <20 cells/side → Bénard cells 不成形，Nu 可能 spurious；等距 mesh 在 Ra>1e7 → δ_T 里 cells 过少，Nu 系统偏低 20%+；front/back empty 展向错 (不是 empty) → 伪 2D 失效。<strong>What to inspect</strong>: blockMeshDict 里 cells (40 40 1 or 80 80 1 2D)；hexes grading 向量 (均匀 1 1 1 or 壁面加密 3 1 3)。`,
    boundary_conditions_zh: `<strong>Why this choice (RBC 的经典 BC)</strong>: 下壁 fixedValue T=T_hot (浮力源)；上壁 fixedValue T=T_cold (sink)；侧壁 zeroGradient T (绝热避免侧向传热)；四壁 no-slip U=(0,0,0) (典型 closed box)；gravity=(0,0,-g) 指向 -z (向下)；referencePressure 在任一角固定为 0 做锚。<strong>Main alternative</strong>: 上下壁改 fixedHeatFlux q_wall 而非 T boundary → 对应 Niemela 2000 cryogenic helium 实验 class (heating by dissipation)；侧壁 conducting (线性温度分布) 而非 adiabatic → RBC with heat-conducting sidewalls，边界层结构不同；open cavity (去掉上壁，流体和 ambient 交换) → 室内通风类问题。<strong>When it breaks</strong>: 侧壁 fixedValue T (非 adiabatic) → 引入侧向 heat loss 改变 Nu；gravity 方向反 → stable stratification (no convection)；漏掉 referencePressure → p_rgh 漂移。<strong>What to inspect</strong>: 0/T 里 bottom T_hot 上 T_cold，sidewalls zeroGradient；constant/g 里 (0 0 -9.81) 或无量纲；fvSolution 里 p_rgh reference cell 位置。`,
    observable_extraction_zh: `<strong>Why this choice</strong>: Nu(Ra) = q_avg·L / (k·ΔT), q_avg = hot-wall 平均壁面热流。extractor 在 hot-wall patch 做 surfaceIntegrate(-k·∂T/∂n) / A_wall = q_avg，再换算 Nu。Grossmann-Lohse 2000 给理论 α≈2/7=0.286；文献实验 α=0.28-0.33 视 regime。<strong>Main alternative</strong>: Nu_local(x) 是更细粒度 — 看 plume 冲击热壁时局部 Nu spike (对 plume dynamics 研究必要)；time-average Nu_inst(t) 对 oscillating regime 是必须，不然瞬时值振幅 10% 会误导 verdict；volumetric 方法 Nu = 1 + <uT>/(α·ΔT/L) 用 internal field 而不是 wall 梯度，对 mesh degeneracy 抗性更好。<strong>When it breaks</strong>: 没 time-average 在 oscillating 区 → 瞬时 Nu 震荡 10%；仅测 Nu_avg 不看 Nu(x,t) → 错失 "Nu 稳定但 flow 震荡" 的 regime 信号；extractor 用 wall-adjacent cell gradient 而非 patchField gradient → 第一 cell 厚度影响 5-10%。<strong>What to inspect</strong>: postProcessing 里 wallHeatFlux output 和 Nu_inst(t) 曲线；comparator output 的 Nu_avg vs Grossmann-Lohse Nu=C·Ra^α 拟合。`,
    workflow_steps_zh: [
      { step: `画 2D 方腔`, detail: `blockMeshDict vertices 画 1×1 方腔（x=[0,1], z=[0,1]），cells (40 40 1) teaching / (80 80 1) 更准；front/back empty 伪 2D。若 Ra→1e7 要 wall-graded (3 1 3) 把 δ_T≈Ra^-0.25 里塞 5-10 层。`},
      { step: `配置 Boussinesq 物性`, detail: `constant/transportProperties: nu=1e-4, Pr=0.71 (空气), beta=0.0034 (1/T_ref for ideal gas, T_ref=293K), TRef=293。Ra=g·β·ΔT·L³/(ν·α) 由 g=9.81, L=1, ΔT=T_hot-T_cold 反推 → 要 Ra=1e6 得 ΔT≈0.3K (非常小, Boussinesq 精确成立).`},
      { step: `设 gravity 和 BC`, detail: `constant/g 写 (0 0 -9.81)；0/T 底壁 fixedValue=293.15K, 顶壁 fixedValue=292.85K (ΔT=0.3K)，侧壁 zeroGradient 绝热；0/U 四壁 fixedValue=(0 0 0)；0/p_rgh 任一角 pRefCell + pRefValue=0。`},
      { step: `配置 laminar steady solver`, detail: `constant/turbulenceProperties simulationType laminar (Ra=1e6 未到湍流)；fvSolution 的 T URF 0.3 (防 plume 震荡), U URF 0.5, p_rgh URF 0.3；p_rgh solver GAMG + nSweeps 2 + tolerance 1e-6。`},
      { step: `启动并判 OSCILLATING`, command: `buoyantBoussinesqSimpleFoam > log.solve &`, detail: `controlDict endTime 5000 iter。foamLog 看 T 的 residual 曲线若单调下掉到 1e-5 是稳态 laminar；若从 2000 iter 起震荡但 平均值稳定 (±2%)，physics_contract status = OSCILLATING_BUT_NU_STABLE — 这也可接受。`},
      { step: `抽取 Nu_avg`, detail: `extractor 在 hot-wall patch 做 surfaceIntegrate(-k·∂T/∂z) / A_wall = q_avg, Nu = q_avg·L/(k·ΔT)。若 oscillating 做 time-average over 最后 2000 iter。comparator 比 Grossmann-Lohse 2000 给的 Ra=1e6 Nu≈8.3，容差 10% 视为 PASS。`},
    ],
    troubleshooting_zh: [
      { symptom: `T 场无 cell 结构，只有 conductive linear 温度分布`, likely_cause: `Ra < Ra_c=1708，浮力不足以克服黏性耗散 — 可能 ΔT 设太小或 β 太小。`, fix: `transportProperties::TRef 确认 293K, beta=0.0034 (1/T)；ΔT 从 0.1K 提到 0.3-1K 保证 Ra≥1e6；不是 bug — 是 subcritical 的物理预期。`},
      { symptom: `Nu 持续震荡，范围 7-11 不稳`, likely_cause: `Ra=1e6 在 oscillating 边缘，稳态 laminar 捕不到稳定极限环；或 T URF 太高（>0.5）放大数值震荡。`, fix: `T URF 降到 0.3；跑 endTime 10000 让平均值稳定；time-average 最后 5000 iter 的 Nu 得稳定值；contract_status 标 OSCILLATING_BUT_NU_STABLE 是可接受状态。`},
      { symptom: `Nu_computed = 1.0 或非常低`, likely_cause: `gravity 方向弄反 (+z 指向上) 或 bottom/top 的 T_hot/T_cold 设反 → stable stratification, 没有对流。`, fix: `constant/g 必须 (0 0 -9.81)；0/T 底壁 T_hot > 顶壁 T_cold；反过来是 stable 配置对流不起。`},
      { symptom: `p_rgh residual 每 500 iter 大跳`, likely_cause: `pRefCell 在 convection 活跃区域（plume 路径）而非 "静止角"，pressure 参考被实际压力场拉动。`, fix: `fvSolution 里 pRefCell 移到 top-left 或 top-right 角（y_max, 远离 plume 中心），pRefValue 0；重跑 residual 应 smooth decreasing。`},
      { symptom: `solver 告警 "bounding T"`, likely_cause: `某些 cell 的 T 计算值超出 initialT+[T_min, T_max]，通常是 URF 激进 + 大 source/sink term 冲突。`, fix: `T URF 降到 0.2；fvSchemes 的 div(phi,T) 用 Gauss upwind 替 linearUpwind（更稳定但略耗散）；bounding 偶发可忽略，持续出现要查 BC。`},
    ],
    benchmark_lineage_zh: {
      why_primary: `Rayleigh-Bénard convection 的 benchmark 谱系非常长——从 Rayleigh 1916 线性稳定性分析到 Malkus 1954 湍流 scaling 到 Grossmann-Lohse 2000 现代理论。选 Chandrasekhar 1961《Hydrodynamic and Hydromagnetic Stability》作为历史 anchor 是因为它把 Rayleigh 的线性理论推到 Ra_c=1708 的可计算形式，成为"临界值存在"的 textbook standard。选 Grossmann-Lohse 2000 作为现代 scaling 是因为它统一了之前几十年互相矛盾的 Nu(Ra) 幂律（0.28-0.33 之间）成一个 regime-dependent 理论框架。Chaivat 2006 (若作 gold 数字源) 在 Ra=10⁴-10⁷ 给出 DNS 表格数据，适合 RANS 验证。`,
      secondary: [
        `Rayleigh 1916 · Phil. Mag. · 首篇线性稳定性分析 · Ra_c 概念起点`,
        `Malkus 1954 · Proc. R. Soc. · 湍流 scaling Nu~Ra^(1/3) 猜想 · 长期争议起源`,
        `Grossmann & Lohse 2000 · J. Fluid Mech. · 统一理论 · 当前 RBC 建模共识`,
        `Ahlers, Grossmann & Lohse 2009 · Rev. Mod. Phys. · 综述 · 建立全景`,
      ],
      next_reading: `学完 Ra=10⁶ 层流 Bénard cells 之后：(1) 读 Chandrasekhar 1961 Ch.II 理解 Ra_c=1708 的 Fourier-Bessel 推导——这是 CFD 验证里少数可以纯纸笔推出临界条件的案例；(2) 读 Ahlers-Grossmann-Lohse 2009 综述理解 Nu(Ra) scaling 的 regime 分割：<Ra≈10⁸ 为"soft turbulence"，>10⁸ 转向"hard turbulence"；(3) 做 hands-on — 在 Chaivat 2006 DNS 数据上跑 RANS buoyantFoam 对比，看你选的 turbulence model 在 Ra=10⁸ 前后哪里开始偏。`,
    },
  },
  {
    id: "differential_heated_cavity",
    // DEC-V61-047 round-1 F5: B-class 修订 (DEC-V61-006 Path P-2) 已经把目标
    // regime 从不可解析的 Ra=1e10 降到经典 de Vahl Davis 1983 的 Ra=1e6。
    // 当前 narrative 停留在旧 Ra=1e10 会让新手带错误印象离开。
    displayName: "Differential Heated Cavity (Ra=1e6 benchmark)",
    headline_zh: `侧加热方腔 · Ra=10⁶ 基准`,
    headline_en: "Side-heated cavity · Ra=1e6 benchmark",
    teaser_zh: `一侧热壁、一侧冷壁、上下绝热的方腔。本仓库采用 de Vahl Davis 1983 Table IV 的 Ra=10⁶ 基准，Nu_avg=8.80。之前目标过 Ra=10¹⁰（湍流对流，需要上千层壁面网格），无法诚实跑通——Path P-2 修订主动降到层流可解析区间，让 case 真正"算得出+算得对"。`,
    canonical_ref: "de Vahl Davis 1983 · J. Numer. Methods Fluids Table IV",
    observable: "wall-averaged Nusselt number (Nu=8.80 at Ra=10⁶)",
    difficulty: "core",
    physics_bullets_zh: [
      `Ra=10⁶, Pr=0.71, AR=1.0 层流稳态对流`,
      `热边界层 δ/L ≈ Ra^(-1/4) ≈ 0.032 → 只需 5~10 层网格`,
      `buoyantBoussinesqSimpleFoam + 层流 SIMPLE，无湍流模型`,
    ],
    why_validation_matters_zh: `这个 case 是一个"诚实 > 野心"的教学样本。之前硬要追 Ra=10¹⁰，网格永远撑不起来，Nu 数字看着合理但全是低分辨率伪像（算出来 ≠ 算对）。B-class 修订把目标 regime 降到 Ra=10⁶ 层流区间，40-80 层网格就能稳定解析，gold 有 40+ 篇后续研究在 ±0.2% 区间内验证 Nu=8.80。当你能选一个"网格撑得起"的 regime 时，选它，不要为了"像高端"去追一个跑不动的数。`,
    common_pitfall_zh: `新手最大的陷阱是"把 Ra 越堆越高觉得越像真实工况"。但 Ra=10¹⁰ 的热边界层 δ≈0.3% 腔高，没有几千层壁面加密你看到的只是解算器的插值伪像——Nu 可能还落在"合理范围"但完全是网格 artefact。先在 Ra=10⁶ 把 case 跑对，再谈扩到 Ra=10⁸、10¹⁰；每提一个量级，先验证网格能撑。`,
    solver_setup_zh: `<strong>Why this choice</strong>: buoyantBoussinesqSimpleFoam (稳态 SIMPLE + 浮力耦合) + turbulenceProperties=laminar。Ra=10⁶ 稳态层流对流 (turbulent onset ~Ra=1.5e8)，laminar 稳态准确；Pr=0.71 (空气)；URF U=0.7, T=0.5, p=0.3 收敛到 residual ≤1e-6。de Vahl Davis 1983 benchmark 本身是稳态数据。<strong>Main alternative</strong>: Ra>1e8 必须 pimpleFoam + LES 或 RANS kOmegaSST buoyancy-modified；transient startup (从均匀 T 出发到稳态) 要 pimpleFoam；ΔT/T_ref>0.1 时 non-Boussinesq rhoPimpleFoam 替代。<strong>When it breaks</strong>: URF T>0.6 在 Ra=10⁶ 让 T 场震荡；推到 Ra>1e7 用 laminar → 解在 oscillating 但 Nu 数字看似稳；漏掉 referencePressure → p_rgh 漂移不收敛。<strong>What to inspect</strong>: residual log T 单调降；transportProperties 的 beta, Pr, TRef；fvSolution 的 p_rgh GAMG solver + nSweeps≥1。`,
    mesh_strategy_zh: `<strong>Why this choice</strong>: blockMesh 方腔 AR=1 (L×L)，40-80 cells per side (1600-6400 cells)。Ra=10⁶ 热边界层 δ_T/L ≈ 0.032；40 uniform cells 有 1-2 cells 在 δ_T (quick), 80 有 2-3 cells (teaching 够用)。<strong>Main alternative</strong>: wall grading (壁面密中心疏) 对 Ra>1e7 是刚需 (δ_T 退到 0.018·L)；非结构 mesh 对矩形 cavity 冗余；Ra=1e9 湍流需要 160+ cells/side + RANS buoyancy model。<strong>When it breaks</strong>: <20 cells/side → δ_T 无分辨率 Nu 系统偏低 20%+；等距 mesh 在 Ra>1e7 → 近壁 plume 宽度 cells 不够；mesh 两方向 cells 数不对称 → 改变 circulation pattern。<strong>What to inspect</strong>: blockMeshDict 里 cells (40 40 1 or 80 80 1)；grading (均匀 1 1 1, 壁面加密类似 simpleGrading 带双侧 grading)；Mesh tab convergence sweep 看 mesh_40/80/160 的 Nu 单调趋近。`,
    boundary_conditions_zh: `<strong>Why this choice (DHC 经典 BC)</strong>: 左右壁 fixedValue T (T_hot=1, T_cold=0) 驱动水平温差；上下壁 zeroGradient T (adiabatic，避免干扰水平循环)；四壁 no-slip U=(0,0,0)；gravity=(0,-9.81,0) 指向 -y；referencePressure 在某角点固定 0。ΔT/T_ref=1 无量纲；Boussinesq 只通过浮力项影响方程。<strong>Main alternative</strong>: 上下壁 conducting (linearly-interpolated T) 而非 adiabatic → 改变 sidewall BL structure (Tian-Karayiannis 的真实实验更像)；侧壁 fixedHeatFlux q_wall 而非 T → 对应 Ampofo-Karayiannis class；加绝缘层 → building-integrated 问题。<strong>When it breaks</strong>: 上下壁 fixedValue T → 引入竞争 circulation 改变 Nu；gravity +y 反转 → 重流体在上 stable stratification；ΔT 压太小 → Ra 降到 sub-critical 对流不起。<strong>What to inspect</strong>: 0/T 左 fixedValue=1 右=0 上下 zeroGradient；constant/g (0 -9.81 0)；transportProperties 的 beta×ΔT×g×L³/(ν·α)=Ra=1e6 反推验证。`,
    observable_extraction_zh: `<strong>Why this choice</strong>: Nu_avg = ∫₀ᴸ Nu(y)·dy / L = (L/(k·ΔT)) · <q_wall> over hot wall。extractor 在 hot-wall patch 对 ∂T/∂n 做 surfaceIntegrate，再除 ΔT 得 Nu_avg。de Vahl Davis Table IV Ra=10⁶ 给 Nu_avg=8.800，容差 ±10%。<strong>Main alternative</strong>: Nu_local(y) 沿 hot-wall 分布 (plume-wall 交互细节)；u_max, v_max (内部 peak velocity) 是 de Vahl Davis Table IV 其他两个 gold 量；stream function ψ_max 是第四个。<strong>When it breaks</strong>: 只用 Nu_avg 无法区分 mesh-converged + physics-correct vs mesh-insufficient + spurious；建议同时 check u_max≈64.63, v_max≈219.36 (de Vahl Davis Ra=1e6 数字)；wall-cell 太粗会让 ∂T/∂n 偏差 5-10%。<strong>What to inspect</strong>: postProcessing 的 wallHeatFlux function object (q_wall field) 和 fieldMinMax (U peak)；comparator 比 Nu vs 8.80、u_max vs 64.63、v_max vs 219.36 三票交叉验证。`,
    workflow_steps_zh: [
      { step: `画 AR=1 方腔`, detail: `blockMeshDict vertices (0 0 0)-(1 1 0.01)，cells (40 40 1) teaching 或 (80 80 1) 更精；front/back empty 伪 2D；若 Ra→1e7 要 wall-grading 让近壁 cells 厚度 <0.002·L (δ_T/5)。`},
      { step: `配置 Boussinesq 物性`, detail: `constant/transportProperties: nu=1e-3, Pr=0.71, beta=1.0 (无量纲), TRef=0.5 (冷热壁中点)；ΔT=T_hot−T_cold=1; L=1; g=9.81 → Ra=β·ΔT·g·L³/(ν·α)=9.81/(1e-3·1e-3·(1/0.71))≈1.39e7 — 调 nu 到 1.3e-3 让 Ra=1e6 精确匹配 de Vahl Davis Table IV。`},
      { step: `侧壁 T + 上下绝热 BC`, detail: `0/T: 左壁 fixedValue=1, 右壁 fixedValue=0, 上下壁 zeroGradient (adiabatic)；0/U 四壁 no-slip (0 0 0)；0/p_rgh 任一角 pRefCell + pRefValue=0。constant/g (0 -9.81 0)（向下）。`},
      { step: `配置 laminar steady`, detail: `constant/turbulenceProperties simulationType laminar；fvSolution T URF 0.5, U URF 0.7, p_rgh URF 0.3；p_rgh GAMG + tolerance 1e-6 + nSweeps 2；Ra=1e6 是稳态层流，residual 单调下掉为正常。`},
      { step: `启动 solver`, command: `buoyantBoussinesqSimpleFoam > log.solve &`, detail: `controlDict endTime 3000 iter。foamLog 看 T, U, p_rgh residuals 全部掉到 <1e-6；Ra=1e6 典型在 1500-2500 iter 收敛；residualControl::T 1e-6 自动停止。`},
      { step: `抽 Nu + u_max + v_max`, detail: `extractor 在 hot-wall 做 surfaceIntegrate(-k·∂T/∂x)/A/ΔT = Nu_avg (gold 8.80)；postProcess fieldMinMax 给 u_max (gold 64.63) 和 v_max (gold 219.36)；三票同时对得上才算真通过，单 Nu 容易是网格 artefact 蒙混。`},
    ],
    troubleshooting_zh: [
      { symptom: `Nu_avg = 7.5 系统偏低 ~15%`, likely_cause: `mesh 太粗 (40×40 uniform)，热边界层 δ_T≈0.032·L 里只有 1-2 cells，壁面温度梯度欠解析。`, fix: `blockMeshDict cells 加到 (80 80 1) uniform 或 (60 60 1) + wall grading 3:1；Mesh tab convergence sweep 应显示 Nu 单调趋近 8.80；40→80→160 cells 差距 <1% 算网格独立。`},
      { symptom: `u_max 对但 v_max 明显偏低 50%`, likely_cause: `mesh 两方向 cells 不对称（例如 x=80, y=40），vertical circulation 被 aspect ratio 拖歪。`, fix: `blockMeshDict cells 两方向同 (80 80 1)；对方腔 AR=1 问题任何非对称 cells 都会扭曲结果；三票交叉验证（Nu, u_max, v_max）可抓这类 mesh asymmetry。`},
      { symptom: `p_rgh residual 掉不到 1e-4`, likely_cause: `pRefCell 位置放在 circulation 活跃区（中心或近壁），压力参考随流动漂移。`, fix: `fvSolution 的 pRefCell 放 top-right 角（冷壁顶角，流动最静区），pRefValue 0；重跑 residual 应顺利下掉。`},
      { symptom: `T 场看起来对但 Nu=5 偏低 40%`, likely_cause: `extractor 在 wall face 直接取 ∂T/∂n 但 wall 是 fixedValue，cell-center 梯度被 zeroGradient 假象抹平。`, fix: `用 wallHeatFlux functionObject 明确输出 q_wall field，再 surfaceIntegrate；或 extractor 取第一/第二 interior cell 的 T 做 finite-difference。`},
      { symptom: `Ra 计算出来是 1e7 不是 1e6`, likely_cause: `transportProperties 的 ν, α (Pr=ν/α)，beta, g, L, ΔT 某项单位错 — 最常见是 ν 写成 1e-4 而不是 1e-3。`, fix: `手算 Ra=β·ΔT·g·L³/(ν·α)=1·1·9.81·1³/(1e-3·1.41e-3)=6.96e6 偏；把 ν 改到 1.3e-3 让 Ra 精准落在 1e6。若 β 用了 1/T_ref 换算而 T_ref 设 293 则要补乘 293 修正。`},
    ],
    benchmark_lineage_zh: {
      why_primary: `de Vahl Davis 1983 (Int. J. Numer. Methods Fluids) 是 buoyancy-driven square cavity 的公认 gold——他用二阶 FVM 在多种网格 (11² 到 81²) 跑 Ra=10³ 到 10⁶，给出 Nu_avg、u_max、v_max 的 Richardson-extrapolated 数值 + Table IV 的规范化表格。后续至少 40 篇 CFD 验证论文以它作为 benchmark。选它而不是选"更现代的 DNS"是因为：(a) 它的 Table IV 数据被整个社区当成"通过率标杆"，你的新 RANS/LES 代码只要能对上 Ra=10⁶ Nu=8.80 就算基础过关；(b) Ra=10⁶ 层流，可解析，没有湍流 closure 干扰。本 harness 从不可解析的 Ra=10¹⁰ 降到 Ra=10⁶ 就是为了和这份 gold 对齐。`,
      secondary: [
        `Ampofo & Karayiannis 2003 · Int. J. Heat Mass Transfer · 高-Ra 湍流实验 Ra=1.58×10⁹ · 工业场景延伸`,
        `Quere 1991 · Comput. Fluids · 高 Ra pseudo-spectral DNS · 跨 Ra=10⁶-10⁸ 精度基准`,
        `Tian & Karayiannis 2000 · Int. J. Heat Mass Transfer · side-heated cavity 实验系列 · 对位验证 de Vahl Davis`,
        `Hortmann, Perić & Scheuerer 1990 · Int. J. Numer. Methods Fluids · multigrid 版 cavity benchmark · 数值方法参考`,
      ],
      next_reading: `学完 Ra=10⁶ 层流 de Vahl Davis benchmark 之后：(1) 上 Ra 到 10⁸ — 读 Quere 1991 pseudo-spectral DNS，看层流-过渡区对 Nu 的影响；(2) 上 Ra 到 10⁹ 湍流 — 读 Ampofo-Karayiannis 2003 实验看真实工业级 Ra 下 turbulence model 选择（kOmegaSST / Reynolds-stress）对 Nu_avg 的影响；(3) 做对比 — 回到 RBC case 读 Grossmann-Lohse，理解 "bottom-heated 和 side-heated" 两种 natural convection 为什么都是 Nu(Ra) 但 regime 完全不同（前者有临界 Ra_c=1708，后者 Ra>0 就有 circulation）。`,
    },
  },
  {
    id: "duct_flow",
    displayName: "Fully Developed Turbulent Square Duct",
    headline_zh: `方截面管道`,
    headline_en: "Square duct turbulence",
    teaser_zh: `方形截面的湍流管道，角区会形成二次流——各向异性湍流的经典问题。`,
    canonical_ref: "Jones · 1976 / Gessner 1973",
    observable: "Darcy friction factor f",
    difficulty: "advanced",
    physics_bullets_zh: [
      `核心观察量是 Darcy-Weisbach 摩擦因子 f，不是 Cf`,
      `角区二次流需要非线性湍流模型才能捕捉`,
      `f ≈ 0.88 · f_pipe(Re) 经验关系`,
    ],
    why_validation_matters_zh: `方管和平板看起来都是"内部湍流"，但 canonical observable 完全不同：平板看 skin-friction Cf，方管看 Darcy f。把它们当同一类是采集器开发里最容易犯的错——两个问题共享 Re 时，Spalding fallback 会给两边一模一样的 Cf 数字，看起来像对上了其实根本用错公式。`,
    physics_intuition_zh: `想象一根长方形截面的管子，你把空气以 Re=40000 推过去。粗看起来它就是"圆管 Moody chart 减 10%"——方管的 Darcy 摩擦因子 f≈0.022 比同 Re 的圆管 Colebrook 曲线低一点，大致线性关系就讲完了。但如果你真钻进管子截面看流场，会发现一个让人意外的图景：主流向 U_x 沿流向匀速前进是没错，但**截面内**的 U_y 和 U_z 并不是零——它们是主流速度的 1-3%，组织成 8 个小涡（每个角落 2 个，共 4 对），把流体从角区"泵"向壁面中线。这就是 Prandtl 1926 命名的 "secondary flow of the second kind"，Nikuradse 1926 的博士论文第一次用热线测量确认了它的存在。\n\n为什么方管有二次流而圆管没有？答案藏在 Reynolds 应力张量的各向异性里。在 fully-developed 段，流向动量方程里的主导源项是 ∂(u'v') / ∂y + ∂(u'w') / ∂z（Reynolds 剪应力散度）。对圆管 axisymmetric，这两项对称相消；但对方管，角区边界抑制了某方向的 turbulent fluctuation，让 normal-stress 的差 (v'² − w'²) 和剪切 u'w' 在角区非零——这个非零散度正是二次流的驱动力。所以方管二次流的物理本质是"湍流不再是各向同性的"，而这恰好是线性 eddy-viscosity 假设 (k-ε, k-ω) 明确禁止的——这类模型把 Reynolds 应力主轴强制对齐到 strain-rate 主轴，在角区物理上就是错的。结果是 k-ε 给你 f 对但 secondary flow 完全消失，这是"数字通过但物理错"最经典的案例之一。\n\n本 case 在 CFD 教学里的独特价值是：它证明 canonical observable 的选择决定了一个 benchmark 的 sharpness。如果你只比 scalar f，几乎任何模型都能过 ±10% 容差 — 这是本 harness gold YAML 当前的 observable 层。但如果你把 observable 升级到"截面 secondary velocity 强度"，k-ε 给你~0、RSM 给你 1-3%、LES (Huser-Biringen 1993) 给你和实验一致的 2% — 这个 observable 能干净区分三代湍流 closure。教学点：一个"容易过关"的 observable 隐藏了模型物理正确性；一个"苛刻"的 observable 才是真正的 benchmark。Demuren-Rodi 1984 第一篇用 RSM 在方管上预测出 secondary flow 是湍流建模史的里程碑，这是你读完 k-ε 之后应该读的下一篇。`,
    common_pitfall_zh: `二次流在方管里是真实的、可测量的现象。线性涡粘模型（k-ε、k-ω）根本预测不到它——你得用 RSM 或 v2-f 这类更贵的模型。验证会告诉你这个模型选择的代价。`,
    solver_setup_zh: `<strong>Why this choice</strong>: simpleFoam (稳态 SIMPLE) + turbulenceProperties=RAS/kEpsilon。kEpsilon 是 40 年 industry baseline — 便宜、收敛稳定、对 fully-developed 段的 f(Re) 估算在 ±10% 以内，对"工程要一个 Darcy f 数字"够用。方管 fully-developed 段本身稳态，没必要跑瞬态。<strong>Main alternative</strong>: RSM (launderGibsonRSTM) 或 v2-f (elliptic relaxation) — 这些模型解 Reynolds-stress anisotropy，是唯一能预测角区 secondary flow of Prandtl's second kind 的 RANS 路径；代价是收敛难、要调的参数多。LES 可以给 DNS-grade 二次流 (Huser-Biringen 1993)，但网格量级 10× 起。<strong>When it breaks</strong>: 用 kEpsilon/kOmegaSST 这种 linear eddy-viscosity 模型时，Reynolds-stress 主轴被强制 align with strain rate — 在角区这个假设物理上不成立，二次流直接消失。结果是 "f 对，flow pattern 错"——最阴险的一类失败，看数字像收敛了但整张 secondary velocity 场全错。<strong>What to inspect</strong>: constant/turbulenceProperties 的 RASModel；fvSolution 对 p 用 GAMG + tolerance=1e-6；跑完抽截面 secondary velocity (U_y, U_z) 看有没有 4 个 corner vortex — 没有就是模型不对。`,
    mesh_strategy_zh: `<strong>Why this choice</strong>: blockMesh 正方形截面 + 流向长直段 (50·D_h 充分发展) 或 cyclic 周期 BC。截面 60×60 uniform 结构网格 (3600 cells/切片) 是 f(Re) 估算的 minimum；真要解 secondary flow 要 100×100 + wall graduation 拉到 y+<1。Re=40000 在 wall-function 模式下要 y+≈30（first-cell 中心落在 log layer），低雷诺数修正要 y+<1。<strong>Main alternative</strong>: streamwise cyclic + driving pressure gradient (constant/fvOptions 里 momentumSource) 只需要 1-2·D_h 长度，网格量省一个 order；代价是"长度无关"假设要 valid，Re 太低 (≤2000 laminar) 或入口段不充分发展时不能用。hex O-grid 对方管相比 Cartesian 意义不大，O-grid 主要是圆管用。<strong>When it breaks</strong>: 截面 cells 太少 (<40×40)，corner vortex 被数值耗散抹平；长度不够 (<20·D_h inlet + outlet 模式)，测得的 ΔP/L 含入口发展段污染，f 偏大。y+ 搞错 (wall-function 模型用 y+<1 或 低Re模型用 y+=30) — wall shear stress 直接差 2× 以上。<strong>What to inspect</strong>: system/blockMeshDict 的 blocks + simpleGrading；log.checkMesh 的 max aspect ratio <100；solver 初跑后 yPlusRAS 场图看四个壁面 y+ 分布是否在模型要求区间。`,
    boundary_conditions_zh: `<strong>Why this choice</strong>: streamwise cyclic (cyclic inlet↔outlet) + fvOptions 加 meanVelocityForce / pressureGradientExplicitSource 维持 U_bulk；四个侧壁 fixedValue U=0 + wall functions kqRWallFunction / epsilonWallFunction / nutkWallFunction (wall-function 模式)。cyclic + 源项是 fully-developed 通道流的标准写法，维持恒定 driving pressure gradient 的同时让 U/k/ε 场周期稳态收敛。<strong>Main alternative</strong>: 长 inlet-outlet 通道 (50·D_h inlet + 100·D_h body + 20·D_h outlet)，inlet 用 fixedValue U_bulk + turbulentIntensityKineticEnergyInlet / mixingLengthDissipationRateInlet，outlet 用 zeroGradient。物理更干净但网格量 5× 起，常用于"入口段发展长度本身是研究对象"的情况。<strong>When it breaks</strong>: cyclic 加反了 (inletDesignation 弄错 master/slave 面) → 流动驻死、ΔP 源项不起作用；wall-function 模型下 y+ 低于 30 → wall shear 用 log-law 强行外推，结果 f 系统性偏低；Re 定义用错 (hydraulic diameter D_h 写成 edge length a，实际 D_h=a 对正方形但梯形/矩形不同)。<strong>What to inspect</strong>: 0/U 的 cyclic patch pair + fvOptions 的 momentum source 值；constant/transportProperties 的 ν 和 U_bulk 推出来的 Re=U·D_h/ν 是否对目标 Re 匹配。`,
    observable_extraction_zh: `<strong>Why this choice</strong>: Darcy-Weisbach f = (2·ΔP/L) · (D_h/(ρ·U_bulk²))，是 duct flow 的 canonical observable。cyclic 模式下 ΔP/L 直接读 fvOptions 源项，U_bulk 来自截面 surfaceIntegrate(U)/A。对长 inlet-outlet 模式，extractor 在 fully-developed 区取截面 A (x=30·D_h) 和 B (x=80·D_h) 的 surfaceAverage(p) 算 ΔP，surfaceAverage(U_x) 算 U_bulk。Jones 1976 在 Re=40000 给 f≈0.022，和 Colebrook-White 圆管公式 乘以 ~0.88 形状修正基本吻合。<strong>Main alternative</strong>: 把 observable 从 "scalar f" 升级到 "截面 secondary velocity field 强度" — 取截面上 max|U_y|, |U_z| 或 secondary KE (integrate(0.5·(U_y²+U_z²))/A) 除以 U_bulk²，这个观测量对模型各向异性敏感，能区分 k-ε (≈0) 和 RSM (~1-3%)。更 sharp 但也更难和文献数字直接比对。<strong>When it breaks</strong>: 截面位置取在 entry region (x<30·D_h) → ΔP 含入口段污染，f 偏大 10-30%；压力用 "绝对压力" 而不是 OpenFOAM 的 kinematic pressure p/ρ → 公式里的 ρ 忘了乘回去，f 错一个 factor。<strong>What to inspect</strong>: system/controlDict 里 functionObjects 的 surfaceFieldValue (type patchAverage, operation areaAverage, fields p U)；postProcessing/surface/p_A, p_B 的时间序列是否到 fully-developed 稳态。`,
    workflow_steps_zh: [
      { step: `画方管截面 + 流向`, detail: `blockMeshDict vertices 方截面 (y=[0,1], z=[0,1])，流向 streamwise 1-2·D_h 若走 cyclic 路径 或 50·D_h 若走 inlet-outlet；cyclic 路径网格量省一个 order；cells 截面 60×60 (3600/切片) 给 f 估算 minimum，100×100 看 secondary flow。`},
      { step: `生成网格`, command: `blockMesh && checkMesh`, detail: `checkMesh 看 max non-orthogonality <15 (方管 Cartesian 理想值 0)、aspect ratio 截面均匀时 ~1、流向 cells 拉长可以到 10。hydraulic diameter D_h=4A/P，方管边长 a 时 D_h=a。`},
      { step: `配置 cyclic + momentum source`, detail: `constant/polyMesh/boundary 把 inlet 和 outlet 配为 type cyclic + neighbourPatch pair；constant/fvOptions 加 meanVelocityForce {Ubar (1 0 0);} 维持 U_bulk=1；ν 由 Re=U_bulk·D_h/ν 反推，Re=40000 时 ν=2.5e-5。`},
      { step: `设置 kEpsilon RANS`, detail: `constant/turbulenceProperties RAS kEpsilon; 0/U 四侧壁 no-slip, cyclic pair；0/k 初值 1e-3, 侧壁 kqRWallFunction；0/epsilon 初值 C_mu^0.75·k^1.5/L, 侧壁 epsilonWallFunction；0/nut 侧壁 nutkWallFunction。`},
      { step: `启动 solver`, command: `simpleFoam > log.simpleFoam &`, detail: `controlDict endTime 2000。cyclic 路径下 U、k、ε、p 场在 ~1000 iter 达周期稳态；foamLog 四个 residual 都要 <1e-5；fvOptions 的 momentum source 值会稳定在某个 ∇p (Pa/m)。`},
      { step: `抽 Darcy f`, detail: `cyclic 模式：f = 2·(source ∇p)·D_h / (ρ·U_bulk²)，直接从 fvOptions 日志读。长 inlet-outlet 模式：extractor 在 x=30·D_h 和 x=80·D_h 取截面 surfaceAverage(p) 算 ΔP/L；Jones 1976 Re=40000 给 f≈0.022。comparator 容差 10%。`},
    ],
    troubleshooting_zh: [
      { symptom: `f 值对但 cross-section secondary velocity 近零`, likely_cause: `kEpsilon / kOmegaSST 线性涡粘模型本质抓不到 Prandtl 第二类 secondary flow。`, fix: `不是 bug — 是 turbulence model 的已知限制 "f 对 flow pattern 错"。要解 secondary flow 得换 RSM (launderGibsonRSTM) 或 v2-f，代价是参数多收敛慢；或直接上 LES。教学点：k-ε 在 duct flow 的角区永远平庸。`},
      { symptom: `cyclic 模式下 U 停滞在 0`, likely_cause: `cyclic pair 配置错误 (inletDesignation 或 neighbourPatch 漏)，momentum source 只作用于某一面没形成闭环。`, fix: `constant/polyMesh/boundary 里 inlet 和 outlet 的 neighbourPatch 互指，type 都设 cyclic；checkMesh 后 paraView 看 "cyclic" 两面是否匹配；source 和 mean velocity 都要激活才能维持 U_bulk。`},
      { symptom: `f 偏高 30%`, likely_cause: `长 inlet-outlet 模式下测量截面在 entry region (x<30·D_h)，BL 还在发展，ΔP 包含不稳态耗散。`, fix: `把 surfaceFieldValue 两截面移到 x=30·D_h 和 80·D_h (确保 fully-developed 区)；或切 cyclic 路径彻底消除 development 问题。`},
      { symptom: `wall y+ 在 10-20 之间`, likely_cause: `first-cell 高度既不满足 wall-function (y+>30) 也不满足 low-Re (y+<1)，kEpsilon 的 blended function 行为不良。`, fix: `wall-graduation 拉开：要么把 first-cell 做薄 (aspect ratio 高) 让 y+<1 且用 low-Re k-omega-SST 模型；要么拉粗 (y+>30) 保留 wall-function；不要落在 5-30 transition zone。`},
      { symptom: `Re 计算出来是 目标的 1/4 (取 edge length 误当 D_h)`, likely_cause: `对非方形截面 D_h=4A/P 不等于 edge length；但对正方形 a×a 截面 D_h=a 是对的，这个坑出现在把方管公式套到矩形/梯形管时。`, fix: `手算 D_h=4·A/P 验证：正方形 a×a 给 D_h=4·a²/(4·a)=a；长方形 a×b 给 D_h=2·a·b/(a+b)。constant/transportProperties 里 ν 由 Re·D_h/U_bulk 反推。`},
    ],
    benchmark_lineage_zh: {
      why_primary: `Square duct 是 "形状看起来简单、物理其实复杂" 的经典 — 直管 fully-developed turbulent 区里，角区二次流 (corner secondary flow of Prandtl's second kind) 约为主流强度的 1-3%，但它决定了局部 heat/mass transfer 分布。本 harness 的 gold YAML 选 Jones 1976 作为主 anchor 是因为他的 Re=40000 实验给出 Darcy f 以及系统化测量的 secondary velocity distribution，是后续 anisotropic turbulence model 验证的 reference。Gessner 1973 作为 secondary 是因为他的早期实验首次明确展示 "为什么 linear eddy-viscosity k-ε 本质上抓不到这个现象"（线性涡粘假设要求 Reynolds stress 主轴 align with strain rate，这在角区不成立）。Nikuradse 1930 的 圆管 pipe flow 数据虽然不是 duct，但 "Moody chart" 的核心 f(Re) 曲线是理解 "duct f 为什么比 pipe f 大 ~10%" 的前提。`,
      secondary: [
        `Gessner 1973 · J. Fluid Mech. · 首组 square duct secondary flow 精细测量 · 各向异性湍流物理起点`,
        `Jones 1976 · 实验 · Darcy f at Re=40000 · gold 数字直接来源`,
        `Nikuradse 1930 · VDI · 圆管 turbulent f(Re) · 理解 "为什么 duct ≠ pipe"`,
        `Demuren & Rodi 1984 · J. Fluid Mech. · RSM turbulence model 对 square duct 的首次预测 · 模型选择参考`,
        `Huser & Biringen 1993 · J. Fluid Mech. · square duct LES at Re_τ=300 · secondary flow DNS-grade 数据`,
      ],
      next_reading: `学完 Jones 1976 + 线性 k-ε 的 f 估算之后：(1) 读 Gessner 1973 看 secondary flow 实验测量长什么样——这是 "f 对但 flow pattern 错" 的具体证据；(2) 读 Demuren-Rodi 1984 或 Launder-Reece-Rodi 1975 了解 Reynolds-stress model (RSM) 为什么能抓到角区二次涡，这是湍流建模史里 "模型复杂度 vs 物理预测能力" 的经典取舍；(3) 做 DNS 对比 — Huser-Biringen 1993 给出 Re_τ=300 的 LES 数据可以作为你 RANS 结果的 ground truth。`,
    },
  },
];

export function getLearnCase(id: string): LearnCase | undefined {
  return LEARN_CASES.find((c) => c.id === id);
}
