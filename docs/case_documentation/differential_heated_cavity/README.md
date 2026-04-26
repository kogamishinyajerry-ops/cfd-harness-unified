# Differential Heated Cavity (DHC, Ra=10⁶ benchmark)

> Case ID: `differential_heated_cavity` · Whitelist row 6 · Status: SATISFIED (post-DEC-V61-006 Ra downgrade)
> GOV-1 enrichment · 2026-04-26 · Option B

## Physics description

Two-dimensional incompressible natural convection in a square cavity (AR=1) with opposing vertical walls held at hot (T_h) and cold (T_c) temperatures, top and bottom walls adiabatic. Boussinesq approximation couples buoyancy to the momentum equation. The flow is **steady laminar convective** at Ra=10⁶ with Pr=0.71 (air); turbulent onset occurs at Ra ≈ 1.5·10⁸.

- Ra = 10⁶, Pr = 0.71, AR = 1.0
- Solver: `buoyantBoussinesqSimpleFoam` (or equivalent), `turbulenceProperties simulationType laminar`
- Mesh: 80 wall-normal cells with wall grading (per STATE.md), comfortably resolves δ_T/L ≈ 0.032
- Geometry: `NATURAL_CONVECTION_CAVITY` adapter path

## Expected behavior (de Vahl Davis 1983 Table I-IV, Run 4)

| Observable | Reference | Tolerance | Role | Source |
|---|---|---|---|---|
| `nusselt_number` (mean Nu_avg, hot wall) | 8.8 | 0.10 | HEADLINE / HARD_GATED | de Vahl Davis 1983 Table IV |
| `nusselt_max` (peak local Nu at y/L≈0.0378) | 17.925 | 0.07 | SAME_SURFACE_CROSS_CHECK / HARD_GATED | de Vahl Davis 1983 Table III |
| `u_max_centerline_v` (peak \|u_x\| on x=L/2 vertical mid-plane, non-dim u·L/α) | 64.63 | 0.05 | INDEPENDENT_CROSS_CHECK / HARD_GATED | de Vahl Davis 1983 Table II Run 4 |
| `v_max_centerline_h` (peak \|u_y\| on y=L/2 horizontal mid-plane, non-dim v·L/α) | 219.36 | 0.05 | INDEPENDENT_CROSS_CHECK / HARD_GATED | de Vahl Davis 1983 Table II Run 4 |
| `psi_max_center` (peak \|ψ\| via trapezoidal ∫ u_x dy) | 16.750 | 0.08 | ADVISORY_RECONSTRUCTION / PROVISIONAL_ADVISORY | de Vahl Davis 1983 Table I Run 4 |

ψ_max is PROVISIONAL_ADVISORY: extractor demotes from HARD_GATED when closure_residual_max_nondim / |ψ_max_gold| ≥ 0.01 (1%). Advisory observables are reported but do **not** count toward pass-fraction.

## Boundary-condition compatibility

| BC type | Compatible? | Notes |
|---|---|---|
| Vertical walls T_hot/T_cold (Dirichlet T), adiabatic top/bottom (zeroGradient T), no-slip everywhere | ✅ Canonical | de Vahl Davis 1983 setup |
| Periodic top/bottom | ❌ Different physics | Removes vertical confinement; different correlation family |
| Constant-flux walls instead of constant-T | ⚠️ Different anchor | Need a Vahl Davis flux-formulation gold; not this case |
| Aspect ratio ≠ 1 | ⚠️ Different correlation | de Vahl Davis Tables cover AR=1; AR=2 uses Markatos & Pericleous |
| Higher Ra (>1.5·10⁸ turbulent) | ❌ Out of scope | Turbulent regime needs ~1000 wall-normal cells (see FM-DHC-1) |
| Pr ≠ 0.71 | ⚠️ Different anchor | de Vahl Davis Run 4 is Pr=0.71 air; other Pr cases use different reference values |

## Tolerance → citation map

| Observable | Tolerance | Citation key | Type |
|---|---|---|---|
| `nusselt_number` | 0.10 | `de_vahl_davis_1983` | de Vahl Davis 1983 reports Nu=8.800 ±0.2% across multiple cross-validation studies; 10% covers harness mesh + scheme variability |
| `nusselt_max` | 0.07 | `dec_v61_057_intake` | DEC-V61-057 intake §B.1 chose 7% based on extractor sensitivity at peak local Nu region. GOV-1 v0.7 trace attempted (de Vahl Davis 1983 Tables I-IV / hypothetical §3 mesh-sensitivity) — paper is a converged-numerical-benchmark with no per-grid scatter table or measurement-noise discussion; 7% reflects harness extractor noise at peak BL-resolution-sensitive region, no published anchor. Tier-(c) retained per `_research_notes/_trace_methodology.md` §1.1. |
| `u_max_centerline_v` | 0.05 | `dec_v61_057_intake` | DEC-V61-057 intake §B.2 chose 5% — interior-velocity peak is a tight independent cross-check. GOV-1 v0.7 trace attempted (de Vahl Davis Table II) — Table II gives gold value u_max=64.63 but no scatter band; 5% is harness engineering choice for interior-peak independence, no published anchor. Tier-(c) retained per `_research_notes/_trace_methodology.md` §1.1/§2 (no gold-value-by-association). |
| `v_max_centerline_h` | 0.05 | `dec_v61_057_intake` | DEC-V61-057 intake §B.2 same rationale. GOV-1 v0.7 trace attempted (de Vahl Davis Table II) — same outcome as `u_max_centerline_v`. Tier-(c) retained. |
| `psi_max_center` | 0.08 | `dec_v61_057_intake` | DEC-V61-057 intake §B.3 chose 8% — trapezoidal ∫ reconstruction noise floor. GOV-1 v0.7 trace attempted (de Vahl Davis Table I) — Table I gives gold value ψ_max=16.750 but no scatter band; 8% specifically reflects trapezoidal-∫ reconstruction noise (numerical method choice), no published anchor. Tier-(c) retained per `_research_notes/_trace_methodology.md` §1.1. |

Citation coverage: 5/5 = 100%. **GOV-1 v0.7 tier-(a) count for this case: 1/5** (`nusselt_number` headline only, via de Vahl Davis 1983 + ±0.2% meta-literature cross-validation envelope). 4/5 cross-check tolerances remain tier-(c) with honest-fallback annotations — de Vahl Davis 1983 is a converged-numerical-benchmark paper without per-observable scatter or measurement-noise sections, so no §X passage directly supports the 7%/5%/5%/8% tolerance choices. This is not a documentation gap — it is a real distinction in rigor between gold-value anchoring and tolerance anchoring.

## Geometry sketch

```
    adiabatic top ─────────────────────────
    ↑                                       ↑
    │  T_h                          T_c     │
    │ (hot)                       (cold)    │
    │   ┃          ↻ buoyancy        ┃     │  L (cavity height)
    │   ┃        boundary layers     ┃     │
    │   ┃           ↺                ┃     │
    │  no-slip                   no-slip   │
    ↓                                       ↓
    adiabatic bottom ──────────────────────
    ←──────────── L (AR=1) ─────────────→
```

At Ra=10⁶: thermal BL thickness δ_T/L ≈ 0.032 → 5-10 BL cells on adapter's 80-cell wall-normal mesh, comfortably resolved.

## Known good results

- `nusselt_number`: ATTEST_PASS, Nu within 10% of 8.8 on adapter
- 4 multi-dim observables (nusselt_max + interior velocity peaks + ψ_max) added in DEC-V61-057 Stage C provide INDEPENDENT_CROSS_CHECK / SAME_SURFACE_CROSS_CHECK gates
- ψ_max reported as PROVISIONAL_ADVISORY when closure residual fails the 1% threshold

## References

See [`citations.bib`](citations.bib). Key refs: de Vahl Davis 1983 (primary, all 5 observables), Markatos & Pericleous 1984 (cross-check correlations for higher AR), ASME V&V 20-2009.
