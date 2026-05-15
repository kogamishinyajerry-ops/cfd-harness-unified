# case_021 · Cf extraction at 5 stations · t=5000

Source: `5000/wallShearStress`

U_inf=70.0 m/s · ν=1.4612e-05 m²/s · ρ=1.225 kg/m³

Canonical references:
- **PS** = Prandtl-Schlichting eq 21.11: Cf = 0.0592 × Re_x^(-1/5) (classical 1/7-power; under-predicts at high Re)
- **SG** = Schultz-Grunow log-law: Cf = (2 log₁₀ Re_x − 0.65)^(−2.3) (preferred at high Re; NASA TMR validation manual reference)

| Station | Re_x | x [m] | τ_w (kin) [m²/s²] | Cf actual | Cf PS | Δ% PS | Cf SG | Δ% SG |
|---|---|---|---|---|---|---|---|---|
| S1 | 2.000e+06 | 0.4174 | 7.30085 | 0.002980 | 0.003252 | -8.36 | 0.003326 | -10.40 |
| S2 | 4.003e+06 | 0.8356 | 6.81579 | 0.002782 | 0.002830 | -1.71 | 0.002970 | -6.33 |
| S3 | 6.013e+06 | 1.2552 | 6.66372 | 0.002720 | 0.002609 | +4.24 | 0.002786 | -2.38 |
| S4 | 8.019e+06 | 1.6740 | 6.59369 | 0.002691 | 0.002463 | +9.26 | 0.002666 | +0.95 |
| S5 | 9.559e+06 | 1.9953 | 6.56140 | 0.002678 | 0.002378 | +12.61 | 0.002596 | +3.16 |
