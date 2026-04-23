// Real flow-field visualisations per case, generated from literature /
// analytical sources by scripts/flow-field-gen/generate_contours.py.
//
// Each entry is a static PNG under public/flow-fields/{case_id}/ + a
// provenance string naming the original source (paper + equation / table).
// These are NOT fake mockups — every figure is traceable to the same
// authoritative data the validation contract uses.

export interface FlowFieldAsset {
  /** PNG path relative to the frontend public root. */
  src: string;
  /** Short Chinese caption shown below the figure. */
  caption_zh: string;
  /** Provenance line — exact paper + equation / table. */
  provenance: string;
  /**
   * Data-source classification for honest real-vs-synthetic labeling.
   * - `literature_data`: points/curves traced directly from a published
   *   table / figure (e.g., Ghia 1982 Table I tabulated u values). The
   *   figure's numbers match the gold contract's reference values.
   * - `analytical_visual`: analytical or ansatz reconstruction for
   *   mental-model pedagogy — the shape is correct, but the numbers
   *   are NOT a solver output and MAY diverge from a live OpenFOAM
   *   run. Must be labeled so students don't cite it as validation.
   * - `solver_output`: rendered from an actual OpenFOAM run on this
   *   repo's adapter. Lives under reports/ not public/ in current
   *   architecture; included in the enum for future use.
   * DEC-V61-049 batch D.
   */
  kind: "literature_data" | "analytical_visual" | "solver_output";
}

export const FLOW_FIELDS: Record<string, FlowFieldAsset[]> = {
  lid_driven_cavity: [
    {
      src: "/flow-fields/lid_driven_cavity/centerline_profiles.png",
      caption_zh: "Ghia 1982 Re=100 表格数据：x=0.5 垂直中线 u 剖面 · y=0.5 水平中线 v 剖面（页面的 gold 契约上，当前 audit comparator 只跑 u 这一条，v 存在 gold 但 physics_contract 里标 suspect）",
      provenance:
        "Ghia, Ghia & Shin (1982) Table I — 17 tabulated points each on x=0.5 and y=0.5.",
      kind: "literature_data",
    },
    {
      src: "/flow-fields/lid_driven_cavity/stream_function.png",
      caption_zh: "流函数 ψ(x,y) · simpleFoam Re=100 真实解 · 主涡中心标注 (0.6172, 0.7344)，ψ_min=-0.1032（与 Ghia 1982 Table III 偏差 0.23%） · BL/BR 角涡位置也标出",
      provenance:
        "Real ψ(x,y) from simpleFoam audit VTK (20260421T082340Z, 129² grid). ψ = ∫₀^y U_x dy' computed via ui/backend/services/psi_extraction.py. DEC-V61-050 batch 2/3 closure (2026-04-23) — replaced the prior tensor-product ansatz with genuine OpenFOAM-derived stream function. Primary vortex matches Ghia 1982 Table III to grid quantization.",
      kind: "solver_output",
    },
  ],
  turbulent_flat_plate: [
    {
      src: "/flow-fields/turbulent_flat_plate/blasius_profile.png",
      caption_zh: "Blasius 相似解 · 2f''' + f f'' = 0 数值积分 · shooting on f''(0) 收敛到 0.33206",
      provenance:
        "Blasius (1908) similarity equation integrated via scipy solve_ivp + brentq shooting.",
      kind: "literature_data",
    },
    {
      src: "/flow-fields/turbulent_flat_plate/cf_comparison.png",
      caption_zh: "Cf(x) 三条 run：Blasius gold · 欠分辨估算 · Spalding fallback 错用",
      provenance:
        "Blasius exact 0.664/√Re_x; mesh-starvation envelope synthetic; Spalding 0.0576/Re_x^0.2 wrong-regime overlay.",
      kind: "analytical_visual",
    },
  ],
  circular_cylinder_wake: [
    {
      src: "/flow-fields/circular_cylinder_wake/strouhal_curve.png",
      caption_zh: "St(Re) · Williamson 1996 实验拟合 · 红带显示 canonical-band shortcut 区域",
      provenance:
        "Williamson (1996) eqn (1) St = 0.2175 - 5.1064/Re for Re ∈ [49, 180]; saturates to ~0.21 above Re=300.",
      kind: "literature_data",
    },
  ],
  plane_channel_flow: [
    {
      src: "/flow-fields/plane_channel_flow/wall_profile.png",
      caption_zh: "u+ 随 y+ · 近壁通用 profile · viscous / buffer / log 三段",
      provenance:
        "Spalding (1961) single-formula composite wall profile; κ=0.41, B=5.0.",
      kind: "literature_data",
    },
  ],
  rayleigh_benard_convection: [
    {
      src: "/flow-fields/rayleigh_benard_convection/nu_ra_scaling.png",
      caption_zh: "Nu(Ra) 对流标度率 · 经典 Ra^(1/4) 到硬湍流 Ra^(1/3) 过渡",
      provenance:
        "Grossmann & Lohse (2000) piecewise regime predictions; experimental envelope at Ra=10^10 spans Nu=100-160.",
      kind: "literature_data",
    },
  ],
  impinging_jet: [
    {
      src: "/flow-fields/impinging_jet/nu_radial.png",
      caption_zh:
        "Nu(r/D) · H/D=2, Re=10000 · Cooper 1984 实验 vs. k-ε 驻点过高 (+52%) vs. k-ω SST (+8%)",
      provenance:
        "Cooper 1984 / Behnad 2013 anchors Nu(0)=25, Nu(1)=12; k-ε +52% and k-ω SST +8% overlays match this case's wrong_model and real_incident teaching runs.",
      kind: "literature_data",
    },
  ],
  backward_facing_step: [
    {
      src: "/flow-fields/backward_facing_step/xr_vs_re.png",
      caption_zh:
        "Xr/H(Re_h) · Armaly 1983 低 Re 段 + Driver 1985 Re_h=37500 湍流平台 · 教学 run 在 Re=7600 处标注",
      provenance:
        "Armaly 1983 low-Re regime + Driver & Seegmiller 1985 Xr/H=6.26 at Re_h=37500 turbulent plateau; envelope interpolation with MVP teaching-run anchor points at Re=7600 overlaid.",
      kind: "analytical_visual",
    },
  ],
  naca0012_airfoil: [
    {
      src: "/flow-fields/naca0012_airfoil/cp_distribution.png",
      caption_zh:
        "Cp(x/c) · NACA 0012, Re=3×10⁶, α=0° · Ladson 1987 exact-surface + reference_pass + wrong_model laminar 三线对比",
      provenance:
        "Thomas 1979 / Ladson 1987 exact-surface Cp at 6 tabulated stations; quartic polynomial fit for shape context; reference_pass -2% stagnation attenuation (cell averaging), laminar wrong_model over-sharpens Cp_le to 1.3 (missing BL displacement).",
      kind: "literature_data",
    },
  ],
  differential_heated_cavity: [
    {
      src: "/flow-fields/differential_heated_cavity/nu_ra_scaling.png",
      caption_zh:
        "Nu(Ra) · 差热腔 · de Vahl Davis 1983 Table IV + Berkovsky-Polevikov 标度 + MVP runs @ Ra=10⁶",
      provenance:
        "de Vahl Davis 1983 Table IV Nu at Ra ∈ {1e3,1e4,1e5,1e6} (laminar natural convection); Berkovsky-Polevikov Nu~0.142·Ra^0.30 overlay. Reference_pass -0.6% of gold; under_resolved -20% from truncated wall gradient.",
      kind: "literature_data",
    },
  ],
  duct_flow: [
    {
      src: "/flow-fields/duct_flow/f_vs_re.png",
      caption_zh:
        "Darcy f(Re_h) · 方管 vs 圆管 · Jones 1976 方管修正 · gold 0.0185 @ Re=50000 +  teaching runs",
      provenance:
        "Colebrook smooth-pipe equation iteratively solved; Jones 1976 square-duct correction f_duct ≈ 0.88·f_pipe on hydraulic-diameter basis. Reference_pass on-target, under_resolved -16% from log-layer under-resolution (y+ ≈ 80).",
      kind: "literature_data",
    },
  ],
};

export function getFlowFields(caseId: string): FlowFieldAsset[] {
  return FLOW_FIELDS[caseId] ?? [];
}
