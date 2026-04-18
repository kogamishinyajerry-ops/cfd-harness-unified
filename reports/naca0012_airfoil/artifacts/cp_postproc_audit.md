# Cp Post-Processing Audit

Source files:
- `/src/foam_agent_adapter.py:7049`
- `/src/foam_agent_adapter.py:7053`
- `/src/foam_agent_adapter.py:7075`
- `/src/foam_agent_adapter.py:7102`
- `/src/foam_agent_adapter.py:7116`
- `/src/foam_agent_adapter.py:7121`
- `/src/result_comparator.py:223`
- `/src/result_comparator.py:241`
- `/tmp/cfd-harness-cases/ldc_2749_1776430899314/439/{Cx,Cz,p}`

Current formula path in `_extract_airfoil_cp`:

```python
U_ref = 1.0
rho = 1.0
q_ref = 0.5 * rho * U_ref**2
```

`p_ref` source in the same function:

```python
if (x < -0.5 * chord or x > 1.5 * chord) and abs(z) < 0.5 * chord:
    farfield_pressures.append(p)

p_ref = (
    sum(farfield_pressures) / len(farfield_pressures)
    if farfield_pressures
    else 0.0
)
```

Current `Cp` formula:

```python
cp_profile.append((x_key, (p_surface - p_ref) / q_ref))
```

Replayed on the preserved 439-step field dump:
- `farfield_count = 3844`
- `p_ref = 0.0058681300`
- `q_ref = 0.5`
- Current extractor output bins: `211`

Reference-point replay using the current extractor:
- `x/c = 0.0 -> Cp = 0.471535`
- `x/c = 0.3 -> Cp = -0.338249`
- `x/c = 1.0 -> Cp = 0.109458`

Those values match `/reports/naca0012_airfoil/auto_verify_report.yaml` to the reported 3-decimal samples:
- `0.471`
- `-0.338`
- `0.109`

Comparator axis audit:
- `/src/result_comparator.py:223-241` resolves `pressure_coefficient_x` against gold-standard `x_over_c`
- Comparison is coordinate-aware interpolation, not index-only matching

Interpretation:
- `p_inf` is not taken from the gold-standard table.
- `p_inf` is not taken from an explicit freestream boundary-condition preset.
- `p_inf` is taken from a far-field cell-average inside the extracted solution field.
- `q_inf` is hard-coded from `rho = 1.0` and `U_ref = 1.0`, so it is a freestream preset, not a sampled patch average.

Likely bias mechanism:
- The extractor uses near-surface cell-centre pressure rather than exact wall-face pressure.
- `surface_band = max(8 * dz_min, 0.02 * chord)` gives a fairly wide acceptance band near the body.
- That is consistent with extrema damping: stagnation Cp too low, suction peak too weak, recovery too low.
