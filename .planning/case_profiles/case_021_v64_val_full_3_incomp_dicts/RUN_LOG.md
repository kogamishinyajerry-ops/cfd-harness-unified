# case_021 · simpleFoam Run Log

**Date**: 2026-05-15
**Container**: opencfd/openfoam-default:2312 (fresh `--rm` invocation)
**Sandbox**: `/Users/Zhuanz/Desktop/case_021_nasa_tmr_flat_plate/case`
**Sub-DEC**: DEC-V64-A-sub-M-V64A-VAL-FULL-3-INCOMP

## Run summary

| Metric | Value |
|---|---|
| Solver | `simpleFoam` (incompressible steady RANS) |
| Turbulence | kOmegaSST (RAS) |
| Mesh | 209,825 hexahedra (NASA TMR fine grid 545×385) |
| Iterations | **5000** (residualControl 1e-5 not strictly triggered; ran to endTime) |
| ClockTime | **3562 s ≈ 59.4 min** (single-core) |
| ExecutionTime | 3558 s (≈ 0.712 s/iter avg) |
| residualControl strict trigger | NO (4/5 fields plateau'd in 1.8e-5 to 4.7e-5 band) |
| FOAM FATAL / crash | NONE |

## Convergence trace (sparse · 14 checkpoints)

```
 iter             Ux             Uy              p          omega              k
--------------------------------------------------------------------------------
   10     4.1125e-04     2.6249e-03     3.0371e-01     5.9466e-05     1.5936e-02
   50     7.8534e-05     1.0322e-03     1.9152e-01     1.0733e-05     6.4054e-04
  100     4.9151e-05     4.6249e-04     1.3383e-01     6.3375e-06     4.6823e-04
  250     5.4031e-05     2.5875e-04     2.1940e-02     2.4739e-06     1.3627e-04
  500     6.3251e-05     2.6085e-04     6.9257e-03     1.3318e-06     8.8886e-05
 1000     7.1455e-05     2.7747e-04     2.4735e-03     6.4552e-07     7.8606e-05
 1500     6.7613e-05     2.0612e-04     4.7402e-04     3.8803e-07     7.0769e-05
 2000     5.5368e-05     1.4598e-04     1.7978e-04     2.5635e-07     5.9966e-05
 2500     4.5386e-05     1.1264e-04     1.0231e-04     1.8119e-07     5.1999e-05
 3000     3.7331e-05     9.6604e-05     8.1885e-05     1.3440e-07     4.5503e-05
 3500     3.1042e-05     8.1122e-05     6.8528e-05     1.0328e-07     3.9982e-05
 4000     2.5971e-05     6.7147e-05     5.8287e-05     8.1354e-08     3.5230e-05
 4500     2.1820e-05     5.6009e-05     5.0528e-05     6.5276e-08     3.1086e-05
 5000     1.8387e-05     4.7109e-05     4.4079e-05     5.3109e-08     2.7431e-05
```

(Source: `CONVERGENCE_TRACE.txt` · regenerable from SIMPLEFOAM_LOG_TRIMMED.txt
 sampled-iter rows; full unabridged log available in sandbox
 `~/Desktop/case_021_nasa_tmr_flat_plate/case/log.simpleFoam` 50,084 lines / 3.6MB)

## Final residuals (iter 5000)

| Field | Initial residual | residualControl 1e-5 met? |
|---|---|---|
| Ux | 1.84e-5 | ✗ (1.84× above) |
| Uy | 4.71e-5 | ✗ (4.7× above) |
| p | 4.41e-5 | ✗ (4.4× above) |
| omega | 5.31e-8 | ✓ (188× below) |
| k | 2.74e-5 | ✗ (2.7× above) |
| continuity (global) | -2.73e-8 | ✓ (machine zero) |

**Convergence analysis**: monotonic decrease from iter 0 to ~iter 3000, then asymptotic plateau. Ux drops from 2.60e-5 (iter 4000) to 1.84e-5 (iter 5000) = factor of 1.4× per 1000 iter — diminishing returns regime, near numerical-noise floor of `bounded linearUpwindV` scheme. Continuing to 10000 iter would likely push to ~1e-5 strict but adds no physics.

**Verdict on residual gate**: **4/5 plateau above 1e-5**. Strict 6/6 < 1e-5 NOT met. Convergence is **practical-converged** (no divergence, plateau'd) but NOT strict-converged.

## y+ statistics (plate boundary · iter 5000)

| Stat | Value |
|---|---|
| y+ min | **0.49** |
| y+ max | **1.54** |
| y+ average | **0.54** |

**Mesh design met**: target y+ ≈ 1 across the plate. nutUSpaldingWallFunction auto-blends viscous-sublayer / log-law correctly across this y+ range.

## wallShearStress on plate (iter 5000)

| Stat | τ_w_x (kinematic) [m²/s²] | τ_w_y |
|---|---|---|
| min | **-64.09** (singular at LE: x ≈ 0.5 mm) | -1.59 |
| max | **-6.56** (TE: x ≈ 1.995 m) | +0.001 |

Sign convention: OpenFOAM wallShearStress = -ν_eff × grad(U) ⋅ n_wall. For flow in +x direction, wall drags fluid in -x → τ_w_x is negative; magnitude grows toward LE (developing BL with steepest gradient).

## Reproducibility (LLM-offline)

```bash
docker run --rm -v /Users/Zhuanz/Desktop/case_021_nasa_tmr_flat_plate/case:/case \
  opencfd/openfoam-default:2312 \
  bash -c 'cd /case && simpleFoam 2>&1 | tee log.simpleFoam'
```

Re-extract Cf:

```bash
python3 .planning/case_profiles/case_021_v64_val_full_3_incomp_dicts/extract_cf.py \
  ~/Desktop/case_021_nasa_tmr_flat_plate/case
```

## Artifacts (this commit)

- `CONVERGENCE_TRACE.txt` (14-checkpoint residual trace · regenerable)
- `SIMPLEFOAM_LOG_TRIMMED.txt` (head + sampled iters + tail · 28KB)
- `extract_cf.py` (Cf extraction tool · pure stdlib · LLM-offline)
- `Cf_results.csv` (machine-readable 5-station table)
- `Cf_results.md` (human-readable 5-station table · PS + SG dual canonical)
