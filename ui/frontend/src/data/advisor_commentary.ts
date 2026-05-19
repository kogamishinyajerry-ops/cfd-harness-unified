/**
 * V80.3 · advisor commentary corpus · human-curated text snippets
 *
 * Per .planning/decisions/2026-05-17_v80_charter_dec.md §4 + §6 reverse-stop #7:
 *   ALL text in this file is human-curated.
 *   NO runtime LLM call is permitted to generate or fill these fields.
 *   The V130/V132 invariants ("advisor advises · human drives") are upheld
 *   precisely because this corpus is static, reviewable, and version-controlled.
 *
 * Keyed by (case_id, step) → 3 commentary kinds:
 *   - mesh-quality        · skewness / aspect ratio / cell-count reasoning
 *   - convergence         · residual decay shape / oscillation / stalling reading
 *   - result-interpretation · physical-quantity sanity / gold reference delta
 *
 * Default ("__default__") fallback applies when no case-specific entry exists.
 * UI surface MUST always render 3 cards · empty cells become "no commentary
 * curated for this case at this step" rather than disappearing — predictable
 * shape over conditional rendering.
 */
import type { StepId } from "../pages/workbench/v3/WorkbenchShellV3";

export type CommentaryKind =
  | "mesh-quality"
  | "convergence"
  | "result-interpretation";

export interface CommentaryEntry {
  kind: CommentaryKind;
  headline: string;
  body: string;
  citation: {
    source: "corpus" | "gold-reference" | "best-practice";
    label: string;
  };
}

export interface CommentarySet {
  "mesh-quality": CommentaryEntry;
  convergence: CommentaryEntry;
  "result-interpretation": CommentaryEntry;
}

const empty = (kind: CommentaryKind, step: StepId): CommentaryEntry => ({
  kind,
  headline: "no commentary curated",
  body: `No human-curated ${kind} commentary exists for this case at step ${step}. ` +
    "Curation lands per-case in advisor_commentary.ts; meanwhile the rule-based " +
    "advisor below still runs.",
  citation: {
    source: "best-practice",
    label: "corpus default",
  },
});

const defaultSet: Record<StepId, CommentarySet> = {
  1: {
    "mesh-quality": {
      kind: "mesh-quality",
      headline: "geometry stage — mesh commentary pending",
      body: "Mesh quality commentary becomes meaningful at Step 2 once snappyHexMesh has run. " +
        "At Step 1 the advisor focuses on watertightness + characteristic length-scale review.",
      citation: { source: "best-practice", label: "OpenFOAM User Guide §5.4" },
    },
    convergence: {
      kind: "convergence",
      headline: "no convergence data yet",
      body: "Residual streams are emitted only by the solver (Step 4). " +
        "Step 1 commentary remains geometry-bounded.",
      citation: { source: "best-practice", label: "OpenFOAM User Guide §6.1" },
    },
    "result-interpretation": {
      kind: "result-interpretation",
      headline: "no field data yet",
      body: "Result interpretation activates after Step 4. " +
        "At Step 1, sanity is bounded by bbox + characteristic length consistency.",
      citation: { source: "best-practice", label: "Ferziger & Perić §1.3" },
    },
  },
  2: {
    "mesh-quality": {
      kind: "mesh-quality",
      headline: "skewness > 0.85 in any cell warrants attention",
      body: "Tetrahedral cells with skewness > 0.85 cause finite-volume gradient " +
        "reconstruction error to dominate. snappyHexMesh's iterativeSnap routine " +
        "drops below 0.85 reliably for canonical cases; persistent high-skewness " +
        "patches usually indicate the surface-feature edge wasn't captured. " +
        "Consider raising 'minRefinementCells' for the offending region.",
      citation: {
        source: "best-practice",
        label: "snappyHexMeshDict mesh-quality controls",
      },
    },
    convergence: {
      kind: "convergence",
      headline: "no convergence data yet",
      body: "Mesh-stage advisor commentary doesn't carry residual reasoning; " +
        "wait until Step 4 (solver) for live convergence interpretation.",
      citation: { source: "best-practice", label: "OpenFOAM User Guide §6.1" },
    },
    "result-interpretation": {
      kind: "result-interpretation",
      headline: "no field data yet",
      body: "Field interpretation becomes meaningful at Step 5 (postprocess). " +
        "Step 2 emphasis is mesh-quality readiness.",
      citation: { source: "best-practice", label: "Ferziger & Perić §3.10" },
    },
  },
  3: {
    "mesh-quality": empty("mesh-quality", 3),
    convergence: {
      kind: "convergence",
      headline: "no convergence data yet",
      body: "Wait until Step 4 for solver residuals. " +
        "Physics stage commentary is BC-application focused.",
      citation: { source: "best-practice", label: "OpenFOAM User Guide §5.3" },
    },
    "result-interpretation": empty("result-interpretation", 3),
  },
  4: {
    "mesh-quality": empty("mesh-quality", 4),
    convergence: {
      kind: "convergence",
      headline: "log-linear residual decay is healthy",
      body: "For steady incompressible flow with simpleFoam, residuals for p/U/k/omega " +
        "should drop log-linearly (one decade per ~100-200 iterations after the first " +
        "decade). Plateaus + oscillation after iteration 500 typically signal: " +
        "(a) under-relaxation too aggressive — drop p relax to 0.3, U relax to 0.7; " +
        "(b) mesh skewness limiting reconstruction; (c) boundary-condition transient " +
        "if you mixed steady solver + transient BC.",
      citation: {
        source: "best-practice",
        label: "Versteeg & Malalasekera §4.5",
      },
    },
    "result-interpretation": empty("result-interpretation", 4),
  },
  5: {
    "mesh-quality": empty("mesh-quality", 5),
    convergence: {
      kind: "convergence",
      headline: "post-run convergence summary",
      body: "Final residuals + state badge are persisted; revisit Step 4 for the " +
        "full live stream. Step 5 commentary leans on result-interpretation.",
      citation: { source: "best-practice", label: "OpenFOAM Tutorial Guide" },
    },
    "result-interpretation": {
      kind: "result-interpretation",
      headline: "compare against gold reference before interpreting",
      body: "Postprocess values become physically meaningful only after the gold-vs-" +
        "actual comparator (V80.4) shows ≤5% deviation on the chosen quantity. " +
        "Above 5%, treat the result as 'fit for trend' — the integrated quantity is " +
        "directionally right but local fields may diverge.",
      citation: {
        source: "gold-reference",
        label: "Ghia 1982 + AGARD validation manuals",
      },
    },
  },
};

const lidDrivenCavity: Record<StepId, CommentarySet> = {
  ...defaultSet,
  2: {
    ...defaultSet[2],
    "mesh-quality": {
      kind: "mesh-quality",
      headline: "uniform 128×128 cartesian mesh — skewness ≈ 0",
      body: "Lid-driven cavity at Re=100 needs cell-Reynolds < 2 in the core, " +
        "which 128×128 hits comfortably (Δx ≈ 0.0078 in unit cavity). Wall-clustering " +
        "via simpleGrading 2..1..2 keeps y+ < 1 without sacrificing core resolution. " +
        "Skewness is essentially zero on a cartesian mesh — focus instead on aspect " +
        "ratio along walls (< 50 stays inside the second-order accurate regime).",
      citation: {
        source: "gold-reference",
        label: "Ghia 1982 Table I (128×128 reference)",
      },
    },
  },
  4: {
    ...defaultSet[4],
    convergence: {
      kind: "convergence",
      headline: "lid-driven cavity Re=100 converges in ~600 iterations",
      body: "Steady simpleFoam at Re=100 on a clean 128×128 mesh should drop the U " +
        "residual to 1e-5 by iteration ~600 and p to 1e-4 by ~800. Faster convergence " +
        "(< 300 iters) typically means under-relaxation is wasting work; slower (> 1500) " +
        "means the secondary corner vortex is being underresolved.",
      citation: {
        source: "best-practice",
        label: "simpleFoam tutorial cavity reference run",
      },
    },
  },
  5: {
    ...defaultSet[5],
    "result-interpretation": {
      kind: "result-interpretation",
      headline: "Ghia 1982 u-centerline is the canonical benchmark",
      body: "Compare U.x(y) along the vertical centerline (x=0.5) at y ∈ {0.0625, " +
        "0.125, ..., 0.9688} against Ghia Table I. Within ±5% on all 17 points and " +
        "the case passes the canonical regression. The primary vortex center (≈ 0.6172, " +
        "0.7344) is a sharper geometric check — if your peak U.x position deviates by " +
        "more than 2% of the cavity edge length, mesh resolution is the most likely " +
        "cause before solver settings.",
      citation: {
        source: "gold-reference",
        label: "Ghia, Ghia & Shin 1982 — JCP 48",
      },
    },
  },
};

// V81.1 · NACA 0012 airfoil · 2D external aerodynamics canonical
const naca0012Airfoil: Record<StepId, CommentarySet> = {
  ...defaultSet,
  2: {
    ...defaultSet[2],
    "mesh-quality": {
      kind: "mesh-quality",
      headline: "C-mesh or O-mesh · y+ < 1 at the leading edge is non-negotiable",
      body: "NACA 0012 at chord-Reynolds 6×10⁶ (AGARD AR-138 canonical) needs " +
        "first-cell y+ < 1 across the entire upper surface for accurate Cp + " +
        "trailing-edge separation. A 257×129 C-mesh with 50 wake cells + " +
        "growth ratio 1.15 is the entry-level target. Watch the leading edge: " +
        "skewness can spike there on auto-generated meshes — manual feature edge " +
        "capture earns the trailing decimal of Cl accuracy.",
      citation: {
        source: "gold-reference",
        label: "AGARD AR-138 + NASA TM 4741 (NACA 0012 validation data)",
      },
    },
  },
  4: {
    ...defaultSet[4],
    convergence: {
      kind: "convergence",
      headline: "α = 10° fully attached · simpleFoam k-ω SST converges in ~2000 iters",
      body: "At α = 10° (sub-stall) the flow stays attached, so simpleFoam with " +
        "k-ω SST converges cleanly: U residual to 1e-5 by ~1500 iters, lift " +
        "coefficient stable to ±0.001 by ~2000. Stall-side cases (α ≥ 16°) need " +
        "URANS or pseudo-transient runs — steady simpleFoam will oscillate on Cl " +
        "and never converge in residual norm. Use 'forceCoeffs' function object " +
        "and watch Cl convergence directly, not just residuals.",
      citation: {
        source: "best-practice",
        label: "OpenFOAM airFoil2D tutorial + Menter 1994 k-ω SST original paper",
      },
    },
  },
  5: {
    ...defaultSet[5],
    "result-interpretation": {
      kind: "result-interpretation",
      headline: "Cl + Cp distribution are the canonical validation observables",
      body: "Compare Cl(α) vs AGARD AR-138 across α ∈ {0°, 4°, 8°, 10°, 12°}. " +
        "Within ±3% on Cl across the linear range and the case clears validation. " +
        "Cp distribution at α = 10° upper surface should match the experimental " +
        "data within ±5% from x/c = 0.05 to x/c = 0.9 (leading/trailing edge " +
        "have larger experimental scatter). Pitching moment Cm,c/4 is sensitive " +
        "to mesh quality at the trailing edge — treat that as a mesh-dependence " +
        "diagnostic rather than a primary validation target.",
      citation: {
        source: "gold-reference",
        label: "AGARD AR-138 NACA 0012 wind-tunnel reference",
      },
    },
  },
};

// V81.1 · Backward-facing step · separated flow + reattachment canonical
const backwardFacingStep: Record<StepId, CommentarySet> = {
  ...defaultSet,
  2: {
    ...defaultSet[2],
    "mesh-quality": {
      kind: "mesh-quality",
      headline: "step + reattachment zone need ≥40 cells across step height h",
      body: "Driver & Seegmiller 1985 (Re_h = 5000, h = step height) is the " +
        "canonical reference. Mesh discipline: ≥40 cells across h, ≥20 cells " +
        "between step and reattachment (~6h downstream), wall y+ < 1 on the " +
        "lower wall through the entire reattachment zone. Coarse meshes will " +
        "predict reattachment at 5h instead of 6.1h — a systematic 17% bias " +
        "that no amount of solver tuning recovers.",
      citation: {
        source: "gold-reference",
        label: "Driver & Seegmiller 1985 (NASA TM-85961)",
      },
    },
  },
  4: {
    ...defaultSet[4],
    convergence: {
      kind: "convergence",
      headline: "k-ω SST steady · monitor reattachment-length convergence, not just residuals",
      body: "Steady simpleFoam with k-ω SST should reach U residual 1e-5 by " +
        "iter ~1500. But the diagnostic that actually matters is reattachment " +
        "length (x_r/h): inject a 'fieldMinMax' or 'streamLines' function object " +
        "tracking the lower-wall shear sign change, and stop when x_r/h stabilizes " +
        "to ±0.05. Residual convergence WITHOUT reattachment stability is a " +
        "false-positive — common when secondary corner vortices are still " +
        "evolving.",
      citation: {
        source: "best-practice",
        label: "Versteeg & Malalasekera §11 + OpenFOAM pitzDaily tutorial",
      },
    },
  },
  5: {
    ...defaultSet[5],
    "result-interpretation": {
      kind: "result-interpretation",
      headline: "reattachment length x_r/h ≈ 6.1 is the single most diagnostic number",
      body: "Driver & Seegmiller 1985 reports x_r/h = 6.1 ± 0.1 at Re_h = 5000. " +
        "If your run gives 5.5–5.7, your mesh is too coarse OR k-ε is being used " +
        "(k-ε systematically underpredicts reattachment by ~15% on this geometry). " +
        "Above 6.5 typically means upstream channel-flow isn't fully developed — " +
        "extend the inlet runup. Cp recovery downstream of reattachment is the " +
        "secondary validation observable (within ±5% of Driver-Seegmiller from " +
        "x/h = 8 to x/h = 20).",
      citation: {
        source: "gold-reference",
        label: "Driver & Seegmiller 1985 (NASA TM-85961) Cp + x_r data",
      },
    },
  },
};

// V82.1 · Circular cylinder wake · vortex-shedding canonical
const circularCylinderWake: Record<StepId, CommentarySet> = {
  ...defaultSet,
  2: {
    ...defaultSet[2],
    "mesh-quality": {
      kind: "mesh-quality",
      headline: "wake-zone refinement matters more than near-cylinder y+",
      body: "At Re_D = 100 (laminar vortex shedding regime), the canonical " +
        "Strouhal number St ≈ 0.165 (Williamson 1989) is sensitive to wake mesh " +
        "resolution out to ≥20D downstream. First-cell y+ < 1 is necessary but " +
        "not sufficient — without ≥30 cells per shedding wavelength in the wake, " +
        "St gets damped by numerical diffusion. Aim for an O-mesh with 80+ " +
        "circumferential cells + structured wake block to 25D.",
      citation: {
        source: "gold-reference",
        label: "Williamson 1989 + Norberg 2003 cylinder review",
      },
    },
  },
  4: {
    ...defaultSet[4],
    convergence: {
      kind: "convergence",
      headline: "pisoFoam · transient · monitor Strouhal, not residual norm",
      body: "Vortex shedding is INHERENTLY unsteady — steady simpleFoam will " +
        "either not converge OR converge to a symmetric (non-physical) solution. " +
        "Use pisoFoam with adjustable timestep + max Co=1.0. The diagnostic that " +
        "matters: Strouhal number computed from lift-coefficient FFT after the " +
        "wake spans 5+ shedding cycles (~50-100 time units at U_inf=1). St should " +
        "stabilize to ±0.005 across 10 cycles before declaring convergence.",
      citation: {
        source: "best-practice",
        label: "OpenFOAM pitzDailyDyMFoam + Williamson 1989 St data",
      },
    },
  },
  5: {
    ...defaultSet[5],
    "result-interpretation": {
      kind: "result-interpretation",
      headline: "Strouhal 0.165 + Cd 1.32 (Re=100) are the canonical numbers",
      body: "Williamson 1989 reports St = 0.166 ± 0.002 at Re=100; Henderson " +
        "1995 gives mean Cd = 1.32 ± 0.05. Within ±3% on both = canonical PASS. " +
        "If St is high (~0.18+), wake mesh is too coarse OR domain too short " +
        "(downstream boundary back-reflecting). If Cd is low (~1.1), upstream " +
        "stretching is creating spurious blockage correction.",
      citation: {
        source: "gold-reference",
        label: "Williamson 1989 + Henderson 1995 cylinder Cd compilation",
      },
    },
  },
};

// V82.1 · Turbulent flat plate · law-of-the-wall canonical
const turbulentFlatPlate: Record<StepId, CommentarySet> = {
  ...defaultSet,
  2: {
    ...defaultSet[2],
    "mesh-quality": {
      kind: "mesh-quality",
      headline: "first-cell y+ in {0.5, 30-300} depending on wall treatment",
      body: "Two valid mesh strategies for ZPG turbulent flat plate (Re_x = 10⁷, " +
        "ERCOFTAC T3A): (1) wall-resolved — first-cell y+ ≤ 1, ~30 prism layers, " +
        "growth ratio 1.15 · (2) wall-function — first-cell y+ in 30-300 range, " +
        "fewer layers · NEVER mix the two: y+ in 1-30 (the buffer region) gives " +
        "the worst of both worlds. Pick one and validate skin-friction Cf against " +
        "the Spalding/Coles law accordingly.",
      citation: {
        source: "best-practice",
        label: "Pope §7 + ERCOFTAC T3A flat plate validation",
      },
    },
  },
  4: {
    ...defaultSet[4],
    convergence: {
      kind: "convergence",
      headline: "Cf is the convergence diagnostic, not the U residual",
      body: "Steady simpleFoam with k-ω SST or Spalart-Allmaras converges U " +
        "residual fast (1e-5 by ~800 iters), but Cf along the wall continues to " +
        "evolve until ~2000 iters as the boundary layer thickens. Inject a " +
        "'wallShearStress' function object and watch the SHAPE of Cf(x) — when " +
        "Cf(x=L/2) stabilizes to ±0.5% across 200 iters, the case is converged.",
      citation: {
        source: "best-practice",
        label: "Versteeg & Malalasekera §3.7 + NASA Turbulence Modeling Resource",
      },
    },
  },
  5: {
    ...defaultSet[5],
    "result-interpretation": {
      kind: "result-interpretation",
      headline: "log-law slope κ ≈ 0.41 + Cf ≈ 0.0027 at Re_x = 10⁷",
      body: "Plot U+ vs y+ at multiple x stations · the log-law region (y+ in " +
        "30-300) should show U+ = (1/0.41) ln(y+) + 5.0 within ±5% of the von " +
        "Karman constant. Cf(x) along the plate should follow Schlichting's " +
        "empirical fit Cf = 0.026/Re_x^(1/7) within ±5%; values significantly " +
        "above suggest insufficient near-wall resolution; below suggests over-" +
        "production of turbulent kinetic energy at the leading edge.",
      citation: {
        source: "gold-reference",
        label: "Schlichting Boundary Layer Theory + Spalding 1961 universal law",
      },
    },
  },
};

// V82.1 · Plane channel flow · Moser-Kim-Mansour DNS canonical
const planeChannelFlow: Record<StepId, CommentarySet> = {
  ...defaultSet,
  2: {
    ...defaultSet[2],
    "mesh-quality": {
      kind: "mesh-quality",
      headline: "Re_τ = 180 needs Δx+ ≈ 18 · Δz+ ≈ 6 · ≥10 cells in y+ < 10",
      body: "Moser-Kim-Mansour 1999 (Re_τ = 180) is THE DNS reference for " +
        "wall-bounded turbulence. For RANS validation: Δx+ ≈ 18, Δz+ ≈ 6 are the " +
        "minimum spans · in wall-normal, ≥10 cells inside y+ < 10 (use simpleGrading " +
        "to cluster). Domain length: ≥4πδ streamwise, ≥2πδ spanwise (Lozano-Durán " +
        "& Jiménez 2014 confirms these minima for low-order statistics).",
      citation: {
        source: "gold-reference",
        label: "Moser-Kim-Mansour 1999 DNS database (Re_τ=180/395/590)",
      },
    },
  },
  4: {
    ...defaultSet[4],
    convergence: {
      kind: "convergence",
      headline: "periodic streamwise · pressure-driven · check bulk Reynolds",
      body: "Set inlet/outlet to cyclic (streamwise periodic) + driven by a " +
        "constant body-force OR adjusted pressure-drop. Convergence diagnostic = " +
        "bulk Reynolds Re_b based on Re_τ + the law-of-the-wall integral; for " +
        "Re_τ = 180, Re_b ≈ 5600 (Moser-Kim-Mansour). Drift > 2% means the body-" +
        "force/pressure drive isn't balanced with wall friction yet.",
      citation: {
        source: "best-practice",
        label: "OpenFOAM channel395 + Moser-Kim-Mansour 1999 bulk values",
      },
    },
  },
  5: {
    ...defaultSet[5],
    "result-interpretation": {
      kind: "result-interpretation",
      headline: "Reynolds stress profiles are the canonical validation observable",
      body: "Compare ⟨u'u'⟩/u_τ², ⟨v'v'⟩/u_τ², ⟨w'w'⟩/u_τ², ⟨u'v'⟩/u_τ² vs " +
        "MKM 1999 Re_τ = 180 reference. RANS models predict the DIAGONAL components " +
        "well (within ±10%) but ⟨u'v'⟩ shear-stress peak placement near y+ ≈ 30 " +
        "is harder — k-ω SST tends to underpredict the peak by ~15%. This is a " +
        "known model-limitation, not a mesh defect; document the deviation.",
      citation: {
        source: "gold-reference",
        label: "Moser-Kim-Mansour 1999 Re_τ=180 Reynolds stress tables",
      },
    },
  },
};

// V82.1 · Impinging jet · heat-transfer canonical
const impingingJet: Record<StepId, CommentarySet> = {
  ...defaultSet,
  2: {
    ...defaultSet[2],
    "mesh-quality": {
      kind: "mesh-quality",
      headline: "stagnation point y+ < 0.5 · radial spread to ≥5D",
      body: "Cooper et al 1993 jet (Re = 23,000, H/D = 2) sets the canonical " +
        "Nusselt distribution target. Stagnation-point heat transfer is sensitive " +
        "to y+ — first-cell y+ < 0.5 is required for k-ω SST to capture peak Nu_0. " +
        "Radially, mesh must extend ≥5D from the centerline with adequate cells " +
        "across the wall jet region (r/D 1 to 3) — Nu drops by 50% across that " +
        "range and undermeshed cases miss the secondary peak at r/D ≈ 2.",
      citation: {
        source: "gold-reference",
        label: "Cooper, Jackson, Launder, Liao 1993 jet impingement data",
      },
    },
  },
  4: {
    ...defaultSet[4],
    convergence: {
      kind: "convergence",
      headline: "k-ω SST stagnation-point heat transfer needs T-residual to 1e-7",
      body: "Standard steady simpleFoam + buoyantSimpleFoam variants drop U/p " +
        "to 1e-5 by ~1500 iters · but the energy equation residual needs 1e-7 for " +
        "stable Nu(r). Heat-transfer cases are notoriously residual-tight; treat " +
        "Nu at stagnation (Nu_0) as the convergence diagnostic — when Nu_0 drifts " +
        "< 0.5% across 200 iters, declare converged.",
      citation: {
        source: "best-practice",
        label: "Behnia et al 1998 + OpenFOAM buoyantSimpleFoam reference",
      },
    },
  },
  5: {
    ...defaultSet[5],
    "result-interpretation": {
      kind: "result-interpretation",
      headline: "Nu_0 ≈ 88 (Re=23k, H/D=2) is the primary validation number",
      body: "Cooper 1993 reports Nu_0 = 88 ± 4 at Re=23k, H/D=2 · matching " +
        "within ±10% on Nu_0 is acceptable for RANS (DNS would need ±3%). " +
        "Secondary-peak Nu at r/D ≈ 2 is harder — k-ω SST typically overpredicts " +
        "by 15-20%. Realizable k-ε does better on the secondary peak but worse " +
        "on Nu_0. Document the trade-off; neither is 'wrong' at RANS fidelity.",
      citation: {
        source: "gold-reference",
        label: "Cooper et al 1993 Nu_r data + Behnia 1998 RANS-DNS comparison",
      },
    },
  },
};

// V82.1 · Rayleigh-Bénard convection · natural convection canonical
const rayleighBenardConvection: Record<StepId, CommentarySet> = {
  ...defaultSet,
  2: {
    ...defaultSet[2],
    "mesh-quality": {
      kind: "mesh-quality",
      headline: "thermal boundary layer δ_T sets the y+ target",
      body: "Rayleigh-Bénard at Ra = 10⁸ has thermal BL thickness δ_T ≈ H/(2·Nu) " +
        "≈ H/60. First-cell wall-normal spacing should be ≤ δ_T/8 · so ~120 cells " +
        "vertically with simpleGrading clustering · 96² lateral cells for box " +
        "AR = 1. Horizontal cells must resolve plume widths (~H/15) without " +
        "averaging across plumes — coarse grids see only the mean flow + miss " +
        "the unsteady plume dynamics.",
      citation: {
        source: "gold-reference",
        label: "Kerr 1996 + Verzicco-Camussi 1999 spectral DNS",
      },
    },
  },
  4: {
    ...defaultSet[4],
    convergence: {
      kind: "convergence",
      headline: "Boussinesq buoyantBoussinesqPimpleFoam · transient · monitor Nu",
      body: "Buoyancy-driven flow is INHERENTLY transient at Ra > 10⁵ — steady " +
        "solvers either fail or converge to non-physical steady plumes. Use " +
        "buoyantBoussinesqPimpleFoam, max Co=0.5 (thermal CFL is more restrictive " +
        "than momentum), time-average Nu over ≥20 buoyancy times t_b = √(H/(gβΔT)). " +
        "Convergence = ⟨Nu⟩_t drift < 1% across the last 5 t_b.",
      citation: {
        source: "best-practice",
        label: "OpenFOAM hotRoom + Verzicco-Camussi 1999 transient stats",
      },
    },
  },
  5: {
    ...defaultSet[5],
    "result-interpretation": {
      kind: "result-interpretation",
      headline: "Nu ∝ Ra^(2/7) scaling · Ra=10⁸ gives Nu ≈ 27 (Kerr 1996)",
      body: "Kerr 1996 + Niemela 2000 give Nu(Ra=10⁸) ≈ 27 within ±10% of the " +
        "classical 2/7-power law fit. RANS k-ε buoyancy-modified can hit this; " +
        "k-ω SST tends to underpredict by 5-15%. LES is better. If your Nu is " +
        "above 30, plume merging is being damped (Δt too large OR mesh too " +
        "coarse). Below 22 means buoyancy production is being underestimated " +
        "(check the gravity vector orientation + reference temperature).",
      citation: {
        source: "gold-reference",
        label: "Kerr 1996 + Niemela 2000 Ra-Nu compilation",
      },
    },
  },
};

// V82.1 · Differential-heated cavity · de Vahl Davis canonical
const differentialHeatedCavity: Record<StepId, CommentarySet> = {
  ...defaultSet,
  2: {
    ...defaultSet[2],
    "mesh-quality": {
      kind: "mesh-quality",
      headline: "thin BC layers on hot+cold walls · cluster, don't uniform-mesh",
      body: "de Vahl Davis 1983 canonical case (Ra=10³ to 10⁶) needs ≥40 cells " +
        "wall-normal on hot+cold sides with simpleGrading 4..1..4 clustering. " +
        "Top+bottom adiabatic walls can use 30 cells uniform. Aspect ratio 1 box · " +
        "any cell-Reynolds spike near corner regions (where horizontal+vertical " +
        "thermal BLs collide) is a leading indicator of high-Ra divergence " +
        "downstream.",
      citation: {
        source: "gold-reference",
        label: "de Vahl Davis 1983 benchmark + Le Quéré 1991 high-Ra extension",
      },
    },
  },
  4: {
    ...defaultSet[4],
    convergence: {
      kind: "convergence",
      headline: "steady at Ra ≤ 10⁶ · transient at Ra ≥ 10⁸",
      body: "Boussinesq buoyantSimpleFoam works steady up to Ra ≈ 10⁶ (de Vahl " +
        "Davis canonical range). Above Ra=10⁸ the flow becomes unstable + needs " +
        "transient solver. At Ra=10⁵ expect ~3000 iters to drop U/p/T residuals " +
        "to 1e-6 · Nusselt at hot wall (the integral diagnostic) should stabilize " +
        "to ±0.5% across 200 iters. Nu oscillation is a sign of Ra near transition.",
      citation: {
        source: "best-practice",
        label: "OpenFOAM buoyantCavity tutorial + de Vahl Davis 1983 residuals",
      },
    },
  },
  5: {
    ...defaultSet[5],
    "result-interpretation": {
      kind: "result-interpretation",
      headline: "Nu_hot · u_max · v_max are the de Vahl Davis benchmark trio",
      body: "de Vahl Davis 1983 Ra=10⁵ canonical: Nu_hot = 4.519, u_max = 34.73 " +
        "(at y/H = 0.855), v_max = 68.59 (at x/H = 0.0379) · normalized by α/H. " +
        "Within ±2% on all three = canonical PASS. If Nu_hot is high (~4.8+), " +
        "thermal BL is being over-resolved (rare); if low (~4.2-), BL is " +
        "under-resolved (common with uniform meshes). u_max/v_max locations are " +
        "less mesh-sensitive than magnitudes — match locations first, then tune.",
      citation: {
        source: "gold-reference",
        label: "de Vahl Davis 1983 Table I + Davis-Jones 1983 review",
      },
    },
  },
};

// V82.1 · Duct flow · square-duct secondary-flow canonical
const ductFlow: Record<StepId, CommentarySet> = {
  ...defaultSet,
  2: {
    ...defaultSet[2],
    "mesh-quality": {
      kind: "mesh-quality",
      headline: "secondary flow needs both walls resolved · NO wall-functions",
      body: "Square-duct turbulent flow has weak Prandtl-2nd-kind secondary " +
        "flow (~2% of bulk velocity) — visible only when BOTH adjacent walls " +
        "are wall-resolved. Use first-cell y+ < 1 on all 4 walls with ≥30 " +
        "cells in the y+ < 30 zone per wall. Streamwise periodic with ≥4πh " +
        "length. Wall-function meshes will NOT predict secondary flow at all · " +
        "this is a model+mesh interaction, not just mesh.",
      citation: {
        source: "gold-reference",
        label: "Gavrilakis 1992 DNS + Pinelli et al 2010 square-duct",
      },
    },
  },
  4: {
    ...defaultSet[4],
    convergence: {
      kind: "convergence",
      headline: "RSM or LES required · linear-eddy-viscosity models fail by design",
      body: "Linear-eddy-viscosity RANS models (k-ε, k-ω SST, Spalart-Allmaras) " +
        "CANNOT predict square-duct secondary flow — they assume isotropic " +
        "turbulent stress, which kills the Prandtl-2nd-kind mechanism. Use a " +
        "Reynolds Stress Model (Launder-Reece-Rodi or SSG) OR LES with WALE/" +
        "Smagorinsky. Convergence: time-averaged secondary-flow vortex peak " +
        "magnitude (~0.02 U_bulk) should stabilize to ±0.001 across 20 " +
        "flow-through times.",
      citation: {
        source: "best-practice",
        label: "Pope §11 (RSM derivation) + Pinelli et al 2010 LES results",
      },
    },
  },
  5: {
    ...defaultSet[5],
    "result-interpretation": {
      kind: "result-interpretation",
      headline: "8 corner vortices · peak ~2% U_bulk · location matters more than magnitude",
      body: "Gavrilakis 1992 DNS predicts 8 symmetric corner vortices in the " +
        "cross-section · peak secondary-flow velocity ≈ 2% of bulk · vortex " +
        "centers near (y/h, z/h) ≈ (0.45, 0.15) per quadrant. Topology (vortex " +
        "count + symmetry) is more diagnostic than magnitude — a 1.5% vs 2.5% " +
        "magnitude error is acceptable, but missing vortices or asymmetric " +
        "patterns indicate the turbulence model is wrong for this flow.",
      citation: {
        source: "gold-reference",
        label: "Gavrilakis 1992 DNS topology + secondary-flow vortex map",
      },
    },
  },
};

const COMMENTARY_BY_CASE: Record<string, Record<StepId, CommentarySet>> = {
  __default__: defaultSet,
  lid_driven_cavity: lidDrivenCavity,
  naca0012_airfoil: naca0012Airfoil,
  backward_facing_step: backwardFacingStep,
  // V82.1 · breadth completion · 10 Gold-Standard cases now covered
  circular_cylinder_wake: circularCylinderWake,
  turbulent_flat_plate: turbulentFlatPlate,
  plane_channel_flow: planeChannelFlow,
  impinging_jet: impingingJet,
  rayleigh_benard_convection: rayleighBenardConvection,
  differential_heated_cavity: differentialHeatedCavity,
  duct_flow: ductFlow,
};

export function getCommentary(
  caseId: string | null,
  step: StepId,
): CommentarySet {
  const key = caseId && COMMENTARY_BY_CASE[caseId] ? caseId : "__default__";
  return COMMENTARY_BY_CASE[key][step];
}

export const COMMENTARY_KINDS: ReadonlyArray<CommentaryKind> = [
  "mesh-quality",
  "convergence",
  "result-interpretation",
];
