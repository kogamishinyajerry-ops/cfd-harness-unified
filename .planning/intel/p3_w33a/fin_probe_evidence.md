# W3.3a · straight-fin CHT benchmark — LIVE OF11 probe evidence (2026-06-03)

De-risking probe (W3.2b-style "prove before implement"): does the analytical
straight-fin gold standard (`knowledge/gold_standards/cht_straight_fin.yaml`)
actually reproduce in a real OF11 solid-conduction solve, within the 5% gate?

## Case (designed via Workflow `wuep5hxdl`, 3 doc-grounded agents + judge; OF11-source-verified)

- Solver: `foamRun -solver solid` (OF11 Foundation single solid region; steady via `ddtSchemes steadyState`).
- `constant/physicalProperties`: `constSolidThermo`, `kappa uniform 180` (W/m·K).
- Mesh: thin bar 100×2×2 = 400 hex (checkMesh: max skewness 4.6e-14, OK). L=0.05, w=1.0, t=0.003 m.
- `0/T` BCs: base(x=0)=fixedValue 400 K · tip(x=L)=zeroGradient (adiabatic) · fin (4 lateral faces)=`externalTemperature` (Robin q=h(T−Ta), h=100, Ta=300). θ_b=100 K.
- Convective BC name `externalTemperature` is the OF11.org rename of ESI `externalWallHeatFluxTemperature` (workflow caught this trap; consistent with the `find` for the ESI name returning empty).
- Case files: `reports/showcase_aero/_w33a_fin_probe/` (host). Run in container `cfd-openfoam` at /tmp/w33a_fin.

## Run + extraction (live, iteration 400)

- Converged: final `e` (internal-energy) residual = **7.83e-9**.
- `Q_base` = areaIntegrate(wallHeatFlux) on base = **775.857 W**
- `Q_fin`  = areaIntegrate(wallHeatFlux) on fin  = **−775.857 W** → energy conservation |Q_base|=|Q_fin| to 1e-4 W (adiabatic tip confirmed).
- `T_tip`  = areaAverage(T) on tip = **366.622 K** ; baseT areaAverage = 400.000 K (sanity).
- `q_ideal` = h·A_fin·θ_b, A_fin = P·L = 0.1003 m² → 1003.0 W.

## Verdict vs analytical (5% gate)

| QoI | sim | analytical | rel. err | gate |
|---|---|---|---|---|
| fin_efficiency | 0.77354 | 0.77402 | **0.063%** | ✅ PASS (<5%) |
| tip_temperature_ratio | 0.66622 | 0.66604 | **0.028%** | ✅ PASS (<5%) |

The live OF11 solid solve reproduces BOTH analytical fin quantities to <0.07% —
far inside the 5% gold-standard tolerance. The benchmark is reproducible.

## Adversarial verification (Workflow `wi98g7czg`) — CONFIRMED_WITH_CAVEATS

3 diverse-lens skeptics (analytical re-derivation / extraction-circularity / OF11
physics fidelity) + a synthesis judge. **All 3 lenses returned `refuted: false`
(high confidence)**; the judge additionally read the raw artifacts and
independently re-derived the result. Verdict: **CONFIRMED_WITH_CAVEATS ·
trustworthy=true**.

Confirmations:
- Analytical re-derived from the 1-D fin ODE (adiabatic tip): eta=0.774022,
  tip=0.666036 — match. eta verified two independent ways.
- **Not circular**: q_ideal=h·P·L·θ_b uses ONLY inputs (no tanh/cosh/m); the
  numerator Q_base is the solver's own integrated wallHeatFlux.
- **Not fabricated**: the gold-standard reference is re-derived from inputs by
  `tests/p3/test_cht_straight_fin_gold.py` (the honesty lock).
- **Dual-channel consistency** rules out a compensating bug: mL back-derived from
  the independent TEMPERATURE observable (0.96331) matches analytical mL (0.96369),
  cross-validating the independent FLUX channel.
- Physically grounded: Bi=h(t/2)/k=8.3e-4 ≪ 1 (1-D reduction faithful); the fin
  flux decreasing base→tip is the correct cooling profile (Robin BC truly carries flux).

Recorded caveats (none are physics refutations):
1. ARTIFACT (closed): `log.checkMesh` + the converged `400/` field are now copied
   back to the host probe dir (originally only blockMesh/foamRun logs were).
2. HYGIENE (closed): a stray never-executed `of11_fin_case/` (a design-agent
   leftover, 4000-cell variant) was removed; the ONLY canonical case is
   `_w33a_fin_probe/`.
3. SCOPE (by design): this validates the SOLID conduction + imposed-h Robin BC
   against the exact adiabatic-tip fin — **necessary but NOT sufficient** for the
   formal runnable-coverage 1→2 flip, which additionally requires **W3.3b** (full
   two-region conjugate vs Gnielinski, fluid-produced h). Coverage stays 1.

**Disposition**: the straight-fin SOLID-SIDE benchmark is LIVE-VALIDATED. The
gold-standard `contract_status` is updated to SOLID_SIDE_LIVE_VALIDATED ·
CONJUGATE_FLIP_PENDING_W3.3b.

Raw artifacts: `reports/showcase_aero/_w33a_fin_probe/log.foamRun`,
`.../postProcessing/{basePower,finPower,tipT,baseT}/0/surfaceFieldValue.dat`.
