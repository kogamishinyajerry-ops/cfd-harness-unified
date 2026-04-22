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
  // Each paragraph: 2-4 sentences, Chinese, concrete numbers where
  // available, avoids jargon without deleting technical terms.
  // ======================================================================
  solver_setup_zh: string;
  mesh_strategy_zh: string;
  boundary_conditions_zh: string;
  observable_extraction_zh: string;
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
    physics_bullets_zh: [
      `小攻角（~5°）下近似线性`,
      `失速攻角（~15°）附近非线性剧增`,
      `远场边界距离直接影响解`,
    ],
    why_validation_matters_zh: `Ladson 的风洞数据是 NASA 开放的公共基准。你的 CFD 如果要拿来做航空类预测，必须在 NACA 0012 上通过——否则别的任何几何都不用谈。Cp 对比不仅验证压强场，还隐含验证了湍流模型在过渡流动下的行为。`,
    common_pitfall_zh: `远场边界放得太近（<15 倍弦长）是最常见的新手错误。环流效应会让升力系数 Cl 被压低 10%+，而且网格无关性测试抓不到这个问题。`,
    solver_setup_zh: `simpleFoam (稳态) + RAS kOmegaSST (航空默认湍流模型)。Re=6e6 基于弦长 c=1m 和 M∞ (assumed incompressible here)。small angle attack (α≈4°) 接近线性区。URF: U≈0.7, p≈0.3。收敛需要足够的 iterations (≥1000)，尤其是 Cl 积分值要稳定。`,
    mesh_strategy_zh: `C-grid 或 O-grid 贴翼型表面，远场至少 15-20·c 距离（防止伪 blockage）。壁面第一层 cell 目标 y+≈1 让 kOmegaSST 低雷诺数修正正确工作；典型第一层厚度 10⁻⁵·c。约 5-10 万 cells 二维结构网格。Cp 采样是 near-surface band (不是 exact surface)，所以 y+<5 区间内 cells 的密度直接影响 Cp 曲线平滑度。`,
    boundary_conditions_zh: `inlet (upstream + lateral far-field) fixedValue U=(U∞·cos α, U∞·sin α, 0)；outlet (downstream) 压力 zeroGradient + U inletOutlet；翼型表面 no-slip U=(0,0,0)，k/ω wall functions。远场边界要够远：<15·c 会产生虚假 blockage，Cl 系统偏低。`,
    observable_extraction_zh: `Cp(x/c) = (p - p_∞) / (0.5·ρ·U_∞²)。沿翼型表面从 x/c=0 (leading edge) 到 x/c=1 (trailing edge) 采样，分 upper/lower surface。extractor 用 patchAverage 在 airfoil patch 上做 sample，生成 (x/c, Cp) 列表，和 Ladson 风洞数据（NASA TM 1996）对齐比。Cp 对 mesh 的 near-wall 分辨率敏感，y+ 变化 2× 可能让曲线轻微偏。`,
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
  },
];

export function getLearnCase(id: string): LearnCase | undefined {
  return LEARN_CASES.find((c) => c.id === id);
}
