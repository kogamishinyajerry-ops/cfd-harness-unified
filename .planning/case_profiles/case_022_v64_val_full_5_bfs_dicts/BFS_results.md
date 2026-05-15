# case_022 · BFS validation metrics · t=5000

Source files:
- `5000/wallShearStress` (wallShearStress on bottomDownstream)
- `postProcessing/sampleDict/5000/` (sampleDict outputs)

Reference: NASA TM 86658 Driver & Seegmiller 1985

U_ref=44.2 m/s · ν=1.5e-05 m²/s · h=0.0127 m · x_step=0.254 m

## Reattachment length (DS Fig 7)

- x_R         = 0.32313 m
- **x_R/h     = 5.443** (face idx 183 in bottomDownstream patch)
- Canonical   = 6.26 ± 0.10
- **Δ%        = -13.05%**
- FULL gate [6.0, 6.5]:    ✗ NOT MET
- Marginal [5.5, 7.0]:     ✗ NOT MET

## Cp & Cf at 5 stations (DS Figs 8 & 9)

| Station | x/h | x_abs [m] | face_idx | τ_w_x_OF [m²/s²] | Cf actual | Cf DS | Δ%_Cf | p_kin [m²/s²] | Cp actual | Cp DS | Δ%_Cp |
|---|---|---|---|---|---|---|---|---|---|---|---|
| S1 | 1.0 | 0.2667 | 45 | -0.083445 | +0.000085 | -0.001100 | +107.77 | -238.9707 | -0.0957 | -0.1400 | +31.64 |
| S2 | 4.0 | 0.3049 | 146 | +3.220402 | -0.003297 | -0.001930 | -70.82 | -257.1746 | -0.1143 | -0.1100 | -3.95 |
| S3 | 8.0 | 0.3555 | 237 | -2.048383 | +0.002097 | +0.000690 | +203.91 | 21.4430 | +0.1709 | -0.0220 | +876.76 |
| S4 | 12.0 | 0.4066 | 304 | -1.895056 | +0.001940 | +0.001400 | +38.57 | 41.7197 | +0.1916 | +0.0670 | +186.04 |
| S5 | 16.0 | 0.4570 | 356 | -2.005557 | +0.002053 | +0.001850 | +10.98 | 15.7302 | +0.1650 | +0.1190 | +38.69 |

Sign convention: τ_w_x_OF is OpenFOAM's `wallShearStress.x` (kinematic).
Cf_actual = -2·τ_w_x_OF/U_ref² (DS convention: positive for forward flow).
Cp_actual = (p_kin - p_kin_ref) / (0.5·U_ref²) (kinematic).
