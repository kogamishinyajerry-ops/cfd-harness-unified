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
}

export const FLOW_FIELDS: Record<string, FlowFieldAsset[]> = {
  lid_driven_cavity: [
    {
      src: "/flow-fields/lid_driven_cavity/centerline_profiles.png",
      caption_zh: "Ghia 1982 Re=100 表格数据：x=0.5 垂直中线 u 剖面 · y=0.5 水平中线 v 剖面",
      provenance:
        "Ghia, Ghia & Shin (1982) Table I — 17 tabulated points each on x=0.5 and y=0.5.",
    },
    {
      src: "/flow-fields/lid_driven_cavity/stream_function.png",
      caption_zh: "流函数分布示意（shape calibrated to Ghia 中线数据）",
      provenance:
        "Tensor-product ansatz ψ(x,y) calibrated to reproduce Ghia 1982 centerline profiles. Shown for pedagogical geometry context; not a full DNS.",
    },
  ],
  turbulent_flat_plate: [
    {
      src: "/flow-fields/turbulent_flat_plate/blasius_profile.png",
      caption_zh: "Blasius 相似解 · 2f''' + f f'' = 0 数值积分 · shooting on f''(0) 收敛到 0.33206",
      provenance:
        "Blasius (1908) similarity equation integrated via scipy solve_ivp + brentq shooting.",
    },
    {
      src: "/flow-fields/turbulent_flat_plate/cf_comparison.png",
      caption_zh: "Cf(x) 三条 run：Blasius gold · 欠分辨估算 · Spalding fallback 错用",
      provenance:
        "Blasius exact 0.664/√Re_x; mesh-starvation envelope synthetic; Spalding 0.0576/Re_x^0.2 wrong-regime overlay.",
    },
  ],
  circular_cylinder_wake: [
    {
      src: "/flow-fields/circular_cylinder_wake/strouhal_curve.png",
      caption_zh: "St(Re) · Williamson 1996 实验拟合 · 红带显示 canonical-band shortcut 区域",
      provenance:
        "Williamson (1996) eqn (1) St = 0.2175 - 5.1064/Re for Re ∈ [49, 180]; saturates to ~0.21 above Re=300.",
    },
  ],
  plane_channel_flow: [
    {
      src: "/flow-fields/plane_channel_flow/wall_profile.png",
      caption_zh: "u+ 随 y+ · 近壁通用 profile · viscous / buffer / log 三段",
      provenance:
        "Spalding (1961) single-formula composite wall profile; κ=0.41, B=5.0.",
    },
  ],
  rayleigh_benard_convection: [
    {
      src: "/flow-fields/rayleigh_benard_convection/nu_ra_scaling.png",
      caption_zh: "Nu(Ra) 对流标度率 · 经典 Ra^(1/4) 到硬湍流 Ra^(1/3) 过渡",
      provenance:
        "Grossmann & Lohse (2000) piecewise regime predictions; experimental envelope at Ra=10^10 spans Nu=100-160.",
    },
  ],
  impinging_jet: [
    {
      src: "/flow-fields/impinging_jet/nu_radial.png",
      caption_zh:
        "Nu(r/D) · H/D=2, Re=10000 · Cooper 1984 实验 vs. k-ε 驻点过高 (+52%) vs. k-ω SST (+8%)",
      provenance:
        "Cooper 1984 / Behnad 2013 anchors Nu(0)=25, Nu(1)=12; k-ε +52% and k-ω SST +8% overlays match this case's wrong_model and real_incident teaching runs.",
    },
  ],
};

export function getFlowFields(caseId: string): FlowFieldAsset[] {
  return FLOW_FIELDS[caseId] ?? [];
}
