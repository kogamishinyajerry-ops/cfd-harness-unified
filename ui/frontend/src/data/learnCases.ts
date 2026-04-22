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
  },
];

export function getLearnCase(id: string): LearnCase | undefined {
  return LEARN_CASES.find((c) => c.id === id);
}
