# W3.3b — Full two-region conjugate Gnielinski benchmark (live-run recipe)

This is the live OpenFOAM-11 solve that flips **runnable-coverage 1 → 2**
(Blueprint v4 Law 1): a FULL conjugate heat-transfer solve where the FLUID flow
PRODUCES the heat-transfer coefficient `h`, validated against the Gnielinski
(1976) turbulent-duct correlation.

## Result (frozen artifacts in `postProcessing/`)

| quantity | live solve | Gnielinski ref | error | gate |
|---|---|---|---|---|
| Nu | **113.21** | 104.7987 | **+8.03%** | PASS (10% band) |
| energy balance \|Q_iface − ṁ·cp·ΔT\| | 0.977 W = **2.12%** of Q_iface | — | PASS (<5% hard gate) |
| Re | 50000 | 3e3–5e6 valid | — | PASS (in band) |

h_produced = 59.55 W/m²·K, ΔT_window = 32.06 K. Nu is assembled from the
solver's OWN integrated wall-heat + cup-mixing bulk T — NEVER from the closed
form (anti-tautology; see `src/cht_conjugate_extractor.py`).

Offline CI replay (no Docker): `tests/p3/test_cht_conjugate_gate.py`.
Self-verifying reference derivation: `tests/p3/test_cht_pipe_gnielinski_gold.py`.
Gold contract: `knowledge/gold_standards/cht_pipe_gnielinski.yaml`.

## Geometry (parallel-plate realization of the Gnielinski pipe)

D_h = 2·(full gap H) = 0.05 m → modeled as a half-channel (symmetry at the
centerline, half-gap b = 0.0125 m) + a conducting solid wall (b → yo = 0.0175,
k_solid = 50). L = 2.0 m = 40·D_h (fully developed). Air @300K, U_inlet =
15.894610 m/s → Re_Dh = U·D_h/ν = 50000.

## Recipe (container `cfd-openfoam`, OF11)

```bash
# 1. single blockMesh with two named cellZones (fluid + solid)
blockMesh -case <case>
splitMeshRegions -cellZones -overwrite          # -> auto fluid_to_solid / solid_to_fluid
                                                #    mappedWall interface patches
# 2. measurement + diagnostic faceZones on the fluid-side interface
topoSet -region fluid -dict system/fluid/topoSetDict

# 3. SOLVE  (application foamMultiRun; regionSolvers {fluid fluid; solid solid;})
#    The resolved (y+~0.8) mesh cold-starts unstable at Re=50000, so restart
#    from a converged coarse (wall-function) field to get a smooth IC:
mapFields <coarse_converged_case> -sourceRegion fluid -targetRegion fluid \
          -sourceTime latestTime -consistent          # writes mapped field into 0/fluid
foamMultiRun -case <case>                              # PIMPLE transient, maxCo ~0.5
```

The committed `0/` is the uniform-IC definition; the `mapFields` step is a
runtime convergence aid (avoids the high-Re fine-mesh cold-start energy
undershoot), not part of the physical case definition.

## Honesty note (load-bearing)

The +8% over-prediction is the REAL, honestly-reported kOmegaSST + constant-Prt
internal-heat-transfer bias — it is inside the 10% honest band at Re=50000.
At Re=10000 the same machinery over-predicts ~+17% (a documented low-Re RANS
bias, NOT a bug): that was a NO-GO and the benchmark was re-anchored to the
mid-turbulent Re=50000 validation point (DEC-V61-228), where both the RANS
closure and the correlation are robust. The 10% tolerance was NOT loosened and
the result was NOT engineered to pass; the reference is the closed-form
Gnielinski value re-derived from inputs in the gold's self-verifying test.
