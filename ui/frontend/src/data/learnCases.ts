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
    canonical_ref: "Armaly et al. · 1983",
    observable: "reattachment_length / step_height",
    difficulty: "core",
    physics_bullets_zh: [
      `分离流的教科书算例`,
      `Reattachment length 随 Re 变化，不是单调的`,
      `低 Re 时解析稳态；高 Re 时需要非稳态/湍流建模`,
    ],
    why_validation_matters_zh: `反附着长度 L/h 是这个问题唯一的"外部可测量"。Armaly 的实验值在不同 Re 下都被多个独立代码复现过。你的代码如果把 L/h 算偏太多，八成是分离点附近网格不够、或者湍流模型不合适——这是验证比自检更有用的典型场景。`,
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
    displayName: "Turbulent Flat Plate",
    headline_zh: `边界层入门`,
    headline_en: "Boundary layer 101",
    teaser_zh: `平板上的边界层——层流就是 Blasius 相似解，湍流就需要壁面模型。你的 Cf 能不能对上，取决于这个判断。`,
    canonical_ref: "Blasius 1908 / Schlichting",
    observable: "skin-friction coefficient Cf(x)",
    difficulty: "core",
    physics_bullets_zh: [
      `Re_x = Ux/ν 决定层流或湍流`,
      `转捩 Re_x ~ 3×10⁵ - 5×10⁵`,
      `层流 Blasius: Cf = 0.664/√Re_x`,
    ],
    why_validation_matters_zh: `Cf 这个量对网格的 y+ 特别敏感。如果你声称跑湍流模型但 y+ 没拉到合适范围，Cf 会系统偏。我们这个案例把 gold 从 Spalding-fit 改回 Blasius（laminar contract），就是因为 Re_x 实在太低，湍流假设不成立——诚实比"跟前人一样做"重要。`,
    common_pitfall_zh: `Spalding fallback 这种"工程经验公式"在参数外推时会产生和 Re 解耦的假值。两个不同的问题（TFP + duct_flow）如果同一个 Re，Spalding 会给你完全一样的 Cf——看似吻合，其实 shortcut。`,
  },
  {
    id: "plane_channel_flow",
    displayName: "Plane Channel Flow",
    headline_zh: `充分发展湍流`,
    headline_en: "Fully developed turbulence",
    teaser_zh: `两块无限平板之间充分发展的湍流。只有一个方向（主流）非零平均速度，其余全部靠模型封闭。`,
    canonical_ref: "Moser, Kim & Mansour · 1999 DNS",
    observable: "u_mean profile at y+ grid",
    difficulty: "advanced",
    physics_bullets_zh: [
      `Re_τ 通常取 180 / 395 / 590`,
      `靠 DNS 数据做对比（非实验）`,
      `检验 k-ε/ k-ω SST 等 RANS 在近壁的行为`,
    ],
    why_validation_matters_zh: `Moser 1999 的 DNS 数据被整个湍流建模社区当作"对照组"。你的 RANS 模型跑出来的 u+ vs y+ 曲线能不能贴住 DNS，直接告诉你这个湍流模型够不够用。这也是为什么工业项目里即使用了 k-ε，还是要跑一遍 channel flow 校验——模型漂移很容易悄悄发生。`,
    common_pitfall_zh: `周期边界条件是这个算例的核心，但很多新手会漏掉"driving pressure gradient"这一项——少了这一项流动就会慢慢停下来，而不是稳态维持。`,
  },
  {
    id: "impinging_jet",
    displayName: "Axisymmetric Impinging Jet",
    headline_zh: `冲击射流传热`,
    headline_en: "Impingement heat transfer",
    teaser_zh: `垂直射流撞到底板，驻点附近传热最强，径向往外 Nu 数衰减。工业冷却的原型问题。`,
    canonical_ref: "Baughn & Shimizu · 1989",
    observable: "Nusselt number distribution Nu(r)",
    difficulty: "core",
    physics_bullets_zh: [
      `射流 Re 与距板高 H/D 双参数`,
      `近壁传热由热边界层厚度主导`,
      `标准 k-ε 会在驻点过高预测 Nu`,
    ],
    why_validation_matters_zh: `Baughn 的实验给出了清晰的 Nu(r) 曲线，是 impingement 热交换器类问题的基准。CFD 在这个问题上"最容易打脸"——因为驻点传热的预测涉及湍流各向异性，RANS 模型普遍不擅长。做验证会迫使你认清模型的局限。`,
    common_pitfall_zh: `如果你直接用 k-ε 预测驻点 Nu，会比实验值高 50%-100%。这不是 bug，是模型固有的限制——这种情况下验证的意义就是"知道别信这个数字"。`,
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
    displayName: "Differential Heated Cavity",
    headline_zh: `侧加热腔`,
    headline_en: "Side-heated cavity",
    teaser_zh: `一侧热壁、一侧冷壁、上下绝热。低 Ra 下稳态、高 Ra 下湍流对流，Nu 的演化是教科书数据。`,
    canonical_ref: "Ampofo & Karayiannis · 2003",
    observable: "wall-averaged Nusselt number",
    difficulty: "advanced",
    physics_bullets_zh: [
      `Ra 从 10⁶ 层流到 10¹⁰ 湍流`,
      `高 Ra 下边界层薄到需要几千层网格`,
      `Nu 随 Ra 的依赖非单调`,
    ],
    why_validation_matters_zh: `这个案例在我们代码里展示了一个非常重要的现实：你声称 Ra=10¹⁰ 但网格撑不起这种雷诺数——结果会看起来像是通过了（Nu 数字合理），但它其实是低分辨率伪像。我们的规则引擎会把这种情况标成 FAIL，不是为了刁难你，而是提醒：算出来不等于算对了。`,
    common_pitfall_zh: `边界层厚度 δ ~ Ra^(-1/4)，在 Ra=10¹⁰ 时 δ 大约只有腔高的 0.3%。没有千层级网格加密，你会在"解算出了一个数"和"解算对"之间产生系统性混淆。`,
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
