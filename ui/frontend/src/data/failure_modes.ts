/**
 * V83.3 · V5.B contract · curated CFD failure-mode patterns
 *
 * Per .planning/blueprints/v5/INDEX.md Contract V5.B:
 *   3 canonical failure patterns, each rendered as a card with:
 *     - SYMPTOM (what goes wrong · red border)
 *     - AI DIAGNOSIS (what AI advisor catches · sand-coral border)
 *     - FIX SUGGESTION (engineer-applied fix · text-secondary)
 *   All text is human-curated. V80 reverse-stop #7 enforced.
 *   NO "apply fix" button anywhere (V132 invariant).
 */

export interface FailureMode {
  id: "mesh-skewness" | "under-relaxation" | "wake-resolution";
  title: string;
  symptom: {
    headline: string;
    body: string;
    severity: "critical" | "warning";
  };
  diagnosis: {
    headline: string;
    body: string;
    advisor_signal: string; // e.g., "Pillar 2 physics rule + skewness threshold"
  };
  fix: {
    headline: string;
    body: string;
    citation: { source: string; label: string };
  };
}

export const FAILURE_MODES: ReadonlyArray<FailureMode> = [
  {
    id: "mesh-skewness",
    title: "Mesh-driven divergence on a sharp corner",
    symptom: {
      headline: "Skewness 0.94 on the lid · simpleFoam diverges by iter 50",
      body:
        "snappyHexMesh produced 12 tetrahedral cells at the lid-wall corner " +
        "with skewness > 0.9 (peak 0.94). simpleFoam's least-squares gradient " +
        "reconstruction amplifies the error every iteration; pressure residual " +
        "climbs from 1e-3 at iter 20 to 1e+2 at iter 50, then NaN.",
      severity: "critical",
    },
    diagnosis: {
      headline: "AI advisor flags the cluster · cites OpenFOAM mesh-quality limits",
      body:
        "Pillar 2 physics rule catches the >0.85 skewness threshold (OpenFOAM " +
        "User Guide §5.4 calls this the second-order accuracy boundary). " +
        "The advisor surfaces the 12-cell list with their coordinates and a " +
        "link to the corner refinement settings.",
      advisor_signal: "rule-based · skewness gauge + cell-list citation",
    },
    fix: {
      headline: "Raise minRefinementCells in the corner region",
      body:
        "Edit system/snappyHexMeshDict · refinementRegions to add a corner " +
        "box with level (3 3). Re-run snappyHexMesh; expected max skewness " +
        "drops to 0.78. The engineer applies the fix; the advisor never " +
        "executes the change (V130 invariant).",
      citation: {
        source: "best-practice",
        label: "OpenFOAM User Guide §5.4 mesh-quality controls",
      },
    },
  },
  {
    id: "under-relaxation",
    title: "Under-relaxation too aggressive · oscillating residuals",
    symptom: {
      headline: "p relax = 0.7 · residuals oscillate ±0.3 decades around 1e-3",
      body:
        "simpleFoam controlDict has pressure relaxation factor 0.7 (typical " +
        "tutorial default) but the case is high-Re (Re_h = 25,000 in a " +
        "backward-facing step). Pressure residual swings between 5e-4 and " +
        "2e-3 every 5 iterations · velocity follows by 3 iters · no global " +
        "convergence after 3000 iterations.",
      severity: "warning",
    },
    diagnosis: {
      headline: "AI advisor matches the convergence-shape pattern · cites Versteeg",
      body:
        "The advisor's convergence-shape detector classifies the residual " +
        "history as 'oscillating plateau' (Versteeg & Malalasekera §4.5 " +
        "Table 4.2). The cause-effect rule fires: pressure relaxation > 0.5 " +
        "at high-Re is the canonical trigger.",
      advisor_signal: "shape pattern · oscillation amplitude + period",
    },
    fix: {
      headline: "Drop p relax to 0.3 · raise U relax to 0.7",
      body:
        "Edit system/fvSolution · relaxationFactors. Conservative values for " +
        "high-Re steady runs: p=0.3, U=0.7, k=0.7, omega=0.7. Expected: " +
        "monotonic decay to 1e-5 within ~800 iterations.",
      citation: {
        source: "best-practice",
        label: "Versteeg & Malalasekera §4.5 + OpenFOAM simpleFoam tutorial",
      },
    },
  },
  {
    id: "wake-resolution",
    title: "Cylinder wake under-resolved · St 27% high vs reference",
    symptom: {
      headline: "Re=100 vortex shedding · St=0.21 measured, 0.166 reference",
      body:
        "Lift-coefficient FFT after 5 shedding cycles shows St = 0.21 ± 0.01. " +
        "Williamson 1989 reference is 0.166. The 27% overshoot is the " +
        "telltale signature of an under-resolved wake — numerical diffusion " +
        "shortens the apparent shedding period.",
      severity: "warning",
    },
    diagnosis: {
      headline: "AI advisor compares to Williamson 1989 · flags mesh-density gap",
      body:
        "Pillar 8 cfd_breadth catches the >5% deviation from canonical St. " +
        "The advisor surfaces the wake-cell count (~20 cells / shedding " +
        "wavelength) and cites Williamson 1989's >30 cells / wavelength " +
        "requirement for laminar-regime St fidelity.",
      advisor_signal: "gold-reference delta · St(Re) lookup vs measured",
    },
    fix: {
      headline: "Refine the structured wake block to ≥30 cells / wavelength",
      body:
        "Edit blockMeshDict · increase the wake-block streamwise cell count " +
        "from 80 to 120 (× 1.5). Re-mesh, re-run. Expected St drops to " +
        "~0.168 within ±2% of reference. Engineer applies the blockMeshDict " +
        "change; advisor never edits files (V130 invariant).",
      citation: {
        source: "gold-reference",
        label: "Williamson 1989 + Norberg 2003 cylinder review",
      },
    },
  },
];
