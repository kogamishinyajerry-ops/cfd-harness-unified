# case_021 · Cf extraction at 5 stations · t=2500

Source: `2500/wallShearStress`

U_inf=140.0 m/s · ν=1.4612e-05 m²/s · ρ=1.225 kg/m³

Canonical references:
- **PS** = Prandtl-Schlichting eq 21.11: Cf = 0.0592 × Re_x^(-1/5) (classical 1/7-power; under-predicts at high Re)
- **SG** = Schultz-Grunow log-law: Cf = (2 log₁₀ Re_x − 0.65)^(−2.3) (preferred at high Re; NASA TMR validation manual reference)

| Station | Re_x | x [m] | τ_w (kin) [m²/s²] | Cf actual | Cf PS | Δ% PS | Cf SG | Δ% SG |
|---|---|---|---|---|---|---|---|---|
| L1 | 1.002e+06 | 0.1046 | 32.02859 | 0.003268 | 0.003734 | -12.46 | 0.003744 | -12.71 |
| L2 | 1.501e+06 | 0.1566 | 29.25528 | 0.002985 | 0.003444 | -13.32 | 0.003491 | -14.49 |
| L3 | 2.008e+06 | 0.2096 | 28.04367 | 0.002862 | 0.003249 | -11.92 | 0.003323 | -13.89 |
| L4 | 2.508e+06 | 0.2618 | 27.41010 | 0.002797 | 0.003108 | -10.00 | 0.003203 | -12.68 |
| L5 | 3.003e+06 | 0.3134 | 27.02555 | 0.002758 | 0.002998 | -8.01 | 0.003110 | -11.34 |
