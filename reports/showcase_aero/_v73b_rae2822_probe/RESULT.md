# Result — V73.B RAE 2822 Case 9 live probe (frozen verdict)

## Headline

**Tier-1 SANITY-PASS (all 9 gates) · Tier-2 ENFORCED-FAIL (honest CONFLICT).**

The probe run is internally consistent and converged — and the gate correctly
reports that vanilla rhoSimpleFoam + kOmegaSST does NOT reproduce the AGARD
AR-138 Case 9 experimental anchors within tolerance. That CONFLICT is the
deliverable, not a defect: the two-tier oracle exists to say true things, and
the true thing here is a reproducible solver-family bias (see §3).

## 1. Frozen numbers (t_snap = 2627, self-stopped on residualControl 5e-5)

| Quantity | Probe | Anchor (AGARD AR-138) | Tolerance | Verdict |
|---|---|---|---|---|
| Cl (forceCoeffs) | 0.8777 | 0.803 | rel 5% (ENFORCED) | **FAIL (+9.3%)** |
| shock x/c | 0.6005 | 0.525 | atol 0.05 (ENFORCED) | **FAIL (+0.075)** |
| Cd (forceCoeffs) | 0.0304 | 0.0168 | rel 15% (ADVISORY) | reported (+81%) |
| Cl contour cross-check | Cl_p = 0.8691 | vs Cl_fc | rel 5% (tier-1 C6) | PASS (1.0%) |
| M measured (probe) | 0.7340 | 0.734 declared/gold | atol 0.005 | PASS |
| alpha measured | 2.676 deg | 2.79 declared/gold | atol 0.2 deg | PASS (bias −0.114 deg, see §4) |
| max Cp | 1.1366 | Cp_stag = 1.1420 | C1 window | PASS |
| min Cp upper | −1.3414 | < Cp* = −0.6477 | C3 supersonic pocket | PASS |
| y+ (aerofoil) | max 0.70 | <= 1 (B109) | resolved-wall claim | PASS |

Solver: rhoSimpleFoam (transonic SIMPLEC formulation) + kOmegaSST, ESI v2312
native arm64, 8-way scotch. Mesh: 6-block polyLine C-grid, 184,800 cells
(320 cells around the airfoil, 220 wall-normal, first cell 3.6e-6c).

## 2. Convergence quality

- Self-stopped at iter 2627 on residualControl 5e-5 (not endTime).
- Final-50 Cl std 0.13% — no limit cycle (see §3 history).
- Grid check: the 100-wrap-cell build gave Cl 0.865 / shock 0.598 → the
  160-wrap refinement gave 0.878 / 0.6005. The aft shock is grid-converged,
  not under-resolution.

## 3. The honest finding: formulation + code-family bias

Structured-grid codes (CFL3D / TAU / elsA class) with SST report Cl ≈
0.78–0.81 and shock x/c ≈ 0.50–0.53 on this case; the experiment (tabulated)
says Cl 0.803, shock 0.525. This probe's converged answer sits at Cl 0.878,
shock 0.60 — aft-shock/high-lift, consistent with published vanilla-OpenFOAM
RAE 2822 attempts. Two formulation arms were run:

- `transonic yes` + SIMPLEC (squareBend profile + nNonOrthogonalCorrectors 1):
  converges cleanly (twice: 854 and 2627 iters) → **frozen here**.
- vendor aerofoil profile (`transonic no`, p 0.7 / rho 0.01 / U 0.3): on this
  resolved-wall mesh it limit-cycles (Cl ± 0.035, period ~6, never meets
  residualControl; iters 1000–4500 observed) around mean Cl ≈ 0.817 — closer
  to the anchor but NOT a converged steady solution; with the corrector added
  it slows to ~0.4 iter/s (impractical). Freezing an unconverged
  closer-to-anchor mean instead of a converged honest miss would be
  oracle-gaming; the converged arm is frozen.

ΔCl ≈ 0.06 between pressure-term formulations exceeds the anchor tolerance:
discretization sensitivity is a first-order effect on this case. Follow-up
candidates (V-series intel, NOT this slice): rhoCentralFoam LTS
(density-based shock capture — the gold's pinned fallback), wall-function
mesh variant, Cp-profile-band QoI.

## 4. Known biases documented

- Farfield circulation bias: measured alpha 2.676 vs declared 2.79 — the
  freestream BC at 30c absorbs ~0.11 deg of bound-vortex upwash (measured
  0.217 deg at 15c, halved by the domain doubling — scales as 1/R as
  predicted). Within the 0.2-deg gate; an even larger domain or point-vortex
  farfield correction would shrink it further (and would push Cl HIGHER,
  away from the anchor — the bias does not explain the miss).
- Fully-turbulent (no trip) vs experiment tripped at x/c=0.03: standard
  convention; contributes to the ADVISORY Cd overshoot, not to the Cl/shock
  ENFORCED misses.
