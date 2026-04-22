// Student-facing learning metadata — a narrative layer on top of the
// backend's authoritative whitelist + gold_standard records.
//
// Ordering in the catalog is pedagogical (easy → hard, not alphabetical).
// Every case_id MUST exist in knowledge/whitelist.yaml or the detail
// route will 404 when it tries to fetch /api/cases/:id.

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
    common_pitfall_zh: `角点处的速度奇异性（顶角 U=1、侧壁 U=0 同一个点）会让发散。解决办法：网格稍稍加密、放宽残差判据、或者接受角点上的小误差。`,
    solver_setup_zh: `simpleFoam (稳态 SIMPLE 算法) + turbulenceProperties=laminar。SIMPLE 迭代把动量和连续性方程耦合求解，每步更新压力修正。时间项不出现，因此不需要 CFL 条件；控制收敛的是 under-relaxation factors (U≈0.7, p≈0.3)。不压求无脑追求 pimpleFoam 瞬态，对 Re=100 稳态腔体流 simpleFoam 是最合适的。`,
    mesh_strategy_zh: `blockMesh 生成结构化均匀网格，ncx=ncy=40 (~1600 cells) 是对比 Ghia 1982 129×129 的教学级够用的分辨率。重点不是"像 Ghia 一样密"，而是"网格能不能把顶盖带下来的主涡和二级涡分辨出来"——你可以在 Mesh tab 的 convergence sweep 里看不同密度对 u_centerline 的影响。无需边界层加密，因为雷诺数低，边界层相对腔尺寸不算薄。`,
    boundary_conditions_zh: `四面边界：顶壁 (movingWall) fixedValue U=(1,0,0) + p zeroGradient；左右底三面 (fixedWalls) fixedValue U=(0,0,0) + p zeroGradient（no-slip）；压力在一个点固定为 0 作为参考 (referencePressure)。OpenFOAM 的 boundary 文件写法完全 symmetric，新手最易错是把 movingWall 写成 wall (OpenFOAM 会拒绝某些 BC 组合)。`,
    observable_extraction_zh: `u_centerline 剖面：沿 x=0.5 这条竖线从 y=0 到 y=1 采样 U 分量，和 Ghia 表 II 的 17 个纵坐标点对齐比较。extractor 在 src/foam_agent_adapter.py 里用 sample utility 沿线抽点，生成 (y, U_x) 列表；然后 comparator 计算 L2/max 偏差百分比 vs Ghia 基准。primary_vortex_location 另外用 streamFunction 找零点做第二道验证。`,
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
    solver_setup_zh: `simpleFoam (稳态) + turbulenceProperties=RAS/kEpsilon。选 k-ε 而不是 kOmegaSST 是教学上的折中：k-ε 在 BFS 基准里被用了 40 年，会系统性地低估 Xr/H ~5%（比 DNS 偏小），kOmegaSST 贴 DNS 更好但初学者接触 k-ε 更多。RANS-vs-DNS 的方法学 gap 由 10% 容差吸收——RANS 跑通不等于 DNS-grade。`,
    mesh_strategy_zh: `SIMPLE_GRID adapter 路径：blockMesh 生成 2D 结构网格，authoritative 运行 36000 cells；quick-run 默认用 ncx=40, ncy=20 约 800 cells 做网格敏感性测试。剪切层和再附着区需要额外的 x 向分辨率（DEC-V61-036 G5 gate 捕捉 under-resolved quick-run）。front/back patch 是 empty（伪 2D），扩张比 1.125 (channel_height / step_height)。`,
    boundary_conditions_zh: `inlet (x=入口) fixedValue U=(1,0,0) 均匀来流，outlet (x=出口) zeroGradient U + fixedValue p=0；上下壁 no-slip；台阶面 no-slip；front/back 是 empty 模拟 2D。Re_H=7600 由 nu=1/7600 设定，U_bulk=1. 学生易错：忘记 outlet pressure reference 导致系统欠定。`,
    observable_extraction_zh: `沿下壁 y=0 从 x=0 到 x=8·H 扫描 wall shear / near-wall U_x 的零点交叉，找 Xr——这就是"再附着点"。算法在 src/foam_agent_adapter.py 里，先用采样 u_x @ y=0.01·H（防壁面 degen）找第一个由负变正的 x 值。Xr/H 无量纲后和 gold 6.26 比。`,
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
    solver_setup_zh: `pimpleFoam (瞬态 PIMPLE) + turbulenceProperties=laminar。Re=100 层流区涡脱本质是二维非稳态，必须 transient。时间步由 CFL<1 约束，典型 Δt≈0.01 (D/U 量纲)。需要跑到稳定 limit cycle (约 20-30 个涡脱周期) 再做 FFT 提频。`,
    mesh_strategy_zh: `blockMesh + 圆柱周围网格 graduation 到远场。上游 10·D、下游 30·D、横向 ±10·D 是对 Re=100 足够的 computational domain（domain truncation 会明显影响 St）。圆柱表面近场网格最小特征长度 ~0.02·D，远场 ~0.5·D。front/back empty patch 做 2D。`,
    boundary_conditions_zh: `inlet fixedValue U=(1,0,0) + 一个微小 non-symmetric 初始扰动；outlet zeroGradient U + fixedValue p=0；上下侧壁 slip (symmetry) 避免反射；圆柱表面 no-slip U=(0,0,0) + p zeroGradient。Re 由 nu=1/Re, D=1, U_∞=1 定义。`,
    observable_extraction_zh: `St = f·D/U：在圆柱尾迹里放一个 probe 采样 U_y(t) 时间序列，FFT 找主频 f。src/cylinder_strouhal_fft.py 在 limit cycle 稳定后（丢弃前 25% 瞬态）做 Hann 窗 FFT，取 amplitude 峰值作为 f。⚠ Silent-pass hazard：如果 extractor bug 让 f 永远落在 0.18-0.22，canonical-band 验证会假通过——physics_contract 显式标记这个风险。`,
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
    solver_setup_zh: `simpleFoam (稳态 SIMPLE) + turbulenceProperties=laminar，无 k/ε/ω 方程。Re=50000 基于板长 L=1m 和 U_∞=1，所以 ν=1/50000。虽然名字带 "turbulent"，但这里的 solver 配置和实际 Re_x 都是严格层流——诚实的命名重置是 B-class 修订的一部分。`,
    mesh_strategy_zh: `blockMesh 2D 平板 domain，L×H = 1×1，y 方向 80 cells 做 4:1 wall grading（近壁密、远壁疏）。Blasius δ_99 @ Re_x=25000 约为 0.022·L，80 cells 里有 ~50 cells 落在 δ_99 内——足够解析层流边界层。front/back empty patch。`,
    boundary_conditions_zh: `inlet fixedValue U=(1,0,0) 均匀来流；outlet zeroGradient；下壁 no-slip U=(0,0,0)（Blasius 边界层发育的 wall）；上壁 slip (symmetry) 避免上方 BL 干扰；front/back empty。压力在 outlet 固定为 0。`,
    observable_extraction_zh: `Cf(x) = 2·τ_w/(ρ·U_∞²)。在 x=0.5m 处 sample wall shear stress：src/foam_agent_adapter.py 的 _compute_wall_gradient 用第一二个 interior cell (避免 wall-cell 退化) 算 dU/dy|_wall，乘 μ 得 τ_w。一票就够：x=0.5 处 Blasius 解析给 Cf=0.00420，扩展 ±10% 容差。`,
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
    solver_setup_zh: `icoFoam (瞬态 PISO, incompressible 层流 N-S) + Re_bulk=5600 通过 ν=1/5600 设定。⚠ 这里的不兼容是 solver-level 的：要跑 Moser DNS 应该用 LES/DNS (pisoFoam + LES model 或直接 DNS 方程)，或者用 RANS (simpleFoam + kOmegaSST)；当前的 icoFoam 层流只能收敛到 Poiseuille 平滑抛物线。Phase 9 solver-routing 会迁到 pimpleFoam + 真湍流模型。`,
    mesh_strategy_zh: `blockMesh 2D channel slab，半高 D/2=0.5m，流向 2·L=30m（伪长通道），front/back empty。如果真要做 Re_τ=180 DNS，y 方向至少需要上千层网格 + 超细 wall cell (y+_wall ≈ 0.5)；当前 mesh 是给层流 Poiseuille 用的，远远不够湍流 DNS。这也是"solver + mesh + 模型"三层不兼容的 case。`,
    boundary_conditions_zh: `inlet fixedValue U=(1,0,0)；outlet 压力参考；上下壁 no-slip；front/back empty。真正的 Moser DNS 要用周期 BC (streamwise cyclic) + driving pressure gradient 维持稳态湍流，当前 adapter 用 inlet-outlet 是另一层 mismatch。`,
    observable_extraction_zh: `src/plane_channel_uplus_emitter.py 从壁面 shear 算 u_τ=√(τ_w/ρ)，再换算 u+=U/u_τ, y+=y·u_τ/ν。问题：τ_w 此刻来自层流 Poiseuille 解，u_τ 的数字是"自洽但物理错"的——comparator 照常读 u+/y+ 并 tolerance-比较，得出 PASS，这就是 silent-pass hazard。physics_contract 层的 precondition check 把它显性降级到 FAIL。`,
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
    solver_setup_zh: `buoyantBoussinesqSimpleFoam (稳态浮力耦合 SIMPLE) + turbulenceProperties=RAS/kEpsilon，Re=10000 (基于喷嘴直径 D=0.05m 和入口速度)。p_rgh 的 GAMG 求解器在当前配置下持续打到 1000 iter cap 而没收敛——是 URF/p-v coupling/thermal BC 几件事叠加的症状，不是单一参数错。Phase 9 solver-config audit 会做 root-cause.`,
    mesh_strategy_zh: `blockMesh 生成 r-z 矩形域，r=[0, 5·D], z=[-D/2, H+D/2]。axis patch 是 <strong>empty</strong> 而非 <strong>wedge</strong>——这使得几何是 2D 平面，不是 axisymmetric。想真正 axisymmetric 需要 wedge + rotational axis，mesh 生成阶段就不同。约 4800 cells 结构网格；近壁没有刻意加密。`,
    boundary_conditions_zh: `inlet 是喷嘴出口 fixedValue U (射流速度 + Re=10000 定义)；impingement plate z=z_max fixedValue T=T_hot (加热壁)，其余壁 fixedValue T=T_cold + no-slip；axis r=0 <strong>本该是 wedge 但用了 empty</strong>——这是最大的 silent 简化。`,
    observable_extraction_zh: `Nu(r/D) = -D·∂T/∂n|_wall / (T_hot - T_ref)，沿加热板从 r=0 到 r=5·D 扫描。驻点 (r=0) Nu 最大（文献 25），径向衰减。src/wall_gradient.py 在有温度场时做 wall-normal gradient；当前 case A4 没收敛就没有稳定的温度场可用——ATTEST_FAIL 早于 comparator 停住，没有假 Nu 输出的机会。`,
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
    solver_setup_zh: `simpleFoam (稳态 SIMPLE) + RAS kOmegaSST。Re=3e6 基于弦长 c=1m，α=0°（对称翼型，符合 physics_contract 的 precondition "flow attached and steady at α=0°"）。URF: p=0.3（GAMG 求解，relTol=0.05, tolerance=1e-6）; U/k/ω=0.5 each（见 knowledge/gold_standards/naca0012_airfoil.yaml:5-14）. 收敛到 p residual ≤ 1e-6 且 Cp 稳态。`,
    mesh_strategy_zh: `blockMesh 直接围绕 NACA0012 OBJ 生成 x-z 平面（z 法向 80 cells，y 薄展向 ±0.001 + empty side patches，伪 2D）。远场至少 15-20·c 距离。kOmegaSST 在 OpenFOAM 2.x+ 能 blended 处理 y+<1 (低雷诺数修正) 和 y+>30 (wall function)；当前 mesh 的 surface_band=max(8·dz_min, 0.02·c) 让 Cp 提取在 y+<5 区间平滑。`,
    boundary_conditions_zh: `上游 + 横向 inlet/freestream fixedValue U=(U_∞, 0, 0)（α=0°，无 sin α 分量）；下游 outlet 压力 zeroGradient + U inletOutlet；翼型表面 no-slip U=(0,0,0) + k/ω wall functions；展向 front/back 为 empty 模拟 2D。远场 < 15·c 会显著 shift 整个 Cp 分布；> 20·c 后增益递减。`,
    observable_extraction_zh: `Cp(x/c) = (p - p_∞) / (0.5·ρ·U_∞²)。src/foam_agent_adapter.py:7068 的 extractor 在翼型表面上方 surface_band=max(8·dz_min, 0.02·c) 厚度带里取 cell-center 做 patchAverage，然后按 x/c 分 upper/lower。精确文献 Cp 是 exact surface 点，adapter 是 near-surface cell average → 形状正确但幅值系统衰减 ~30-50%（physics_contract precondition #3 明确标 satisfied=false）。容差 20%、verdict PASS_WITH_DEVIATIONS 就是为此。`,
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
    common_pitfall_zh: `Boussinesq 近似（密度只随温度变化、其余性质不变）是这个案例的标配，但它只在温差较小的时候成立。如果你在 ΔT/T0 > 0.1 的条件下还用 Boussinesq，预测会系统偏，而且很难 debug。`,
    solver_setup_zh: `buoyantBoussinesqSimpleFoam (稳态浮力 SIMPLE) + turbulenceProperties=laminar（Ra 取 ~1e6 教学区间，低于湍流对流过渡）。Boussinesq：ρ 只在浮力项里随 T 线性变，黏性/热扩散保持 constant。关键在于 gravity vector 方向和 T_reference 的设定。`,
    mesh_strategy_zh: `blockMesh 方腔 2D，结构均匀网格 40-80 cells per side (~1600-6400 cells 2D)。热边界层厚度 δ_T/L ≈ Ra^(-1/4)，在 Ra=1e6 约为 0.032，5-10 层网格覆盖 δ_T 就够。扩到 Ra=1e8+ 需要边界层加密（壁面 graduation）。front/back empty。`,
    boundary_conditions_zh: `下壁 fixedValue T=T_hot，上壁 fixedValue T=T_cold；侧壁 zeroGradient T (adiabatic)；所有四壁 no-slip U=(0,0,0)；压力在中心/任一角固定为 0 参考。gravity 指向 -z，温差驱动浮力 = Ra·ν·α/L³。`,
    observable_extraction_zh: `Nu(Ra) = q_avg·L / (k·ΔT)，其中 q_avg 是热壁平均壁面热流。extractor 在 hot-wall patch 上做 surfaceIntegrate(∂T/∂n)·k/(L·A_wall)，换算成 Nu。Grossmann-Lohse 2000 给出 Nu ~ Ra^(2/7) 的 theoretical scaling（α≈0.286），文献实验在 α=0.28-0.33 之间。`,
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
    solver_setup_zh: `buoyantBoussinesqSimpleFoam (稳态 SIMPLE + 浮力耦合) + turbulenceProperties=laminar。Ra=10⁶ 属于层流稳态对流区 (湍流对流过渡 ~Ra=1.5×10⁸)。Pr=0.71 (空气)。SIMPLE URF: U≈0.7, T≈0.5, p≈0.3，收敛到 residual ≤ 1e-6。`,
    mesh_strategy_zh: `blockMesh 方腔 AR=1 (L×L)，40-80 cells per side，可以 uniform 也可以在两侧加密。Ra=10⁶ 热边界层 δ_T/L ≈ 0.032，40 cells uniform 下有 ~1-2 cells 在 δ_T 里（quick run），80 cells 下有 2-3 cells——边缘够用。Ra 扩到 10⁸ 需要 grading 或 160+ cells 边界层才能撑住。`,
    boundary_conditions_zh: `左右壁 fixedValue T (T_hot=1, T_cold=0)，上下壁 zeroGradient T (adiabatic)；四壁均 no-slip U=(0,0,0)；压力在某点固定 0 参考；gravity=(0,-9.81,0) (或无量纲 gβΔT)。ΔT/T_ref=1 但在方程里只通过浮力项影响 —— Boussinesq 近似成立。`,
    observable_extraction_zh: `Nu_avg = ∫₀ᴸ Nu(y)·dy / L = L/(k·ΔT) · <q_wall> over hot wall。extractor 在 hot-wall patch 上对 ∂T/∂n 做 surface integral，再除 ΔT 得 Nu。de Vahl Davis Table IV 给 Nu=8.800 at Ra=10⁶，容差 ±10%。`,
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
    common_pitfall_zh: `二次流在方管里是真实的、可测量的现象。线性涡粘模型（k-ε、k-ω）根本预测不到它——你得用 RSM 或 v2-f 这类更贵的模型。验证会告诉你这个模型选择的代价。`,
    solver_setup_zh: `simpleFoam (稳态) + turbulenceProperties=RAS/kEpsilon。⚠ 注意：方管 corner secondary flow 各向异性，线性涡粘 RANS (k-ε / kOmegaSST) 会漏掉它——RSM/v2-f 才能捕捉。当前用 kEpsilon 是工程折中：能估出主流和 f，但二次流细节不准。教训：模型选择写在 turbulenceProperties 里，validation 告诉你代价。`,
    mesh_strategy_zh: `blockMesh 正方形截面 + 流向周期或长直通道 (50·D_h 让流动充分发展)。截面 60×60 uniform 结构网格 (3600 cells 每切片) 够估 f；真要看 corner 二次流强度要 100×100 + wall graduation。Re=40000 要 y+<30 (wall function 区域) 或 y+<1 (低雷诺数修正)。`,
    boundary_conditions_zh: `streamwise inlet + outlet 或周期 cyclic (更准，维持 driving pressure gradient)；四个侧壁 no-slip + wall functions (k/ε)；截面内压力参考。Re 由 ν 和 D_h (水力直径 = 4·A/P) 定义。`,
    observable_extraction_zh: `Darcy f = (2·ΔP/L) · (D_h / (ρ·U_bulk²))，从流向压降和截面平均速度算。extractor 在长管内取两个截面 A, B 上做压力和速度的 surfaceAverage，计算 f。文献 Jones 1976 在 Re=40000 给 f≈0.022；和 Colebrook/Moody chart 比对。`,
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
