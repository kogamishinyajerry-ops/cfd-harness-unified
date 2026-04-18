# Omega Initialization Audit

Source files:
- `/src/foam_agent_adapter.py:5485`
- `/src/foam_agent_adapter.py:5498`
- `/tmp/cfd-harness-cases/ldc_2749_1776430899314/0/omega`

Current string-level formula in code:

```python
omega_init = (k_init ** 0.5) / ((Cmu ** 0.25) * L_turb)
```

Current upstream definitions in the same block:

```python
I_turb = 0.005
k_init = 1.5 * (U_inf * I_turb) ** 2
L_turb = 0.1 * chord
Cmu = 0.09
```

Numeric audit with the current code path:
- `k_init = 3.75e-05`
- `Cmu ** 0.25 = 0.5477225575`
- `omega_correct = 0.1118033989`
- `beta_star = 0.09`
- `omega_wrong = sqrt(k_init) / (beta_star * L_turb) = 0.6804138174`
- Wrong/correct ratio: `6.0858x`

Observed preserved case evidence:
- `/tmp/cfd-harness-cases/ldc_2749_1776430899314/0/omega` stores `internalField uniform 0.11180339887498948`
- That matches the current Python expression exactly.

Interpretation:
- The symbolic formula in `/src/foam_agent_adapter.py:5498` is correct.
- The preserved case uses the corrected numeric value.
- The inline comment text is slightly numerically stale:
  - It says `0.09^0.25 ≈ 0.5623`, but Python evaluates `0.5477`
  - It says `omega ≈ 0.069`, but the current code and preserved case both yield `0.1118`
- The major qualitative conclusion still holds: using `beta_star` directly would over-inflate `omega_init`.

Root-cause implication:
- This audit supports the existing report conclusion that current Cp deviation is not primarily caused by the omega initialization formula.
