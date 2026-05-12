# DRAFT patch · A6 ADPI post-processor extraction

> **Status**: DRAFT · suggested-only · NOT auto-applied
> **Author**: case_012 sub-session · 2026-05-09
> **Target**: main session for landing as sub-DEC
> **Scope**: single sub-DEC, ~150 LOC (under 250 v2.3 cap)
> **Triggers**: case_012 v1 evidence; A6 promotion candidate per
> DEC-V61-198 cross-cut artifact extraction list

## Why this patch

case_012 sandbox `scripts/05_postprocess.py` consumes
`postProcessing/sample/<latestTime>/*.xy` files (OpenFOAM raw set
output) and computes:

1. **ADPI** (Air Diffusion Performance Index) per ASHRAE 55:
   `θ_ED = (T_local - T_ref) - 8 × (U_local - 0.15)`;
   ADPI = % of points where `-1.7 ≤ θ_ED ≤ +1.1`
2. **Throw distance T_50** along supply jet centerline:
   downstream arc-length where `T = T_supply + 0.5 × (T_room - T_supply)`
3. **Dumping criterion**: max vertical `dT/dz` in occupied zone
   (z = 0.1 .. 1.1 m); pass if `< 2 K/m`
4. **ΔT_ceiling-floor** stratification

These are HVAC-industry-recognizable engineering KPIs (per ASHRAE 55,
IEA Annex 20). Currently case_012-local. Promote to main project so
future HVAC / ventilation cases inherit the post-processor.

## Surface scan

`grep -rn "ADPI\|effective draft" ui/backend/services/` — no existing
implementation. New module:
`ui/backend/services/postprocess/hvac_adpi.py`.

## Promotion plan

Source: `~/Desktop/case_012_hvac_supply_diffuser/scripts/05_postprocess.py`
(roughly 200 LOC; extract as ~150 LOC after generalization).

### Public API surface (proposed)

```python
from ui.backend.services.postprocess.hvac_adpi import (
    AdpiResult,
    ThrowDistanceResult,
    DumpingResult,
    compute_adpi,
    compute_throw_distance,
    compute_dumping,
    parse_openfoam_set_xy,
)

# Inputs are already-parsed (coords, fields) tuples; loader is a
# separate function so callers can supply data from any source.
adpi: AdpiResult = compute_adpi(
    coords=...,           # list[tuple[float, float, float]]
    velocities=...,       # list[tuple[float, float, float]]
    temperatures=...,     # list[float]
    t_reference_K=...,    # float; volume-mean T from solver
)
```

### Test fixtures

Synthetic 27-point ASHRAE grid + linear T/U gradient → expected ADPI
analytically computed; case_012 v1 result captured as regression
fixture once sandbox lands.

## Cross-references

- V49 / V50 — case_012 V-finding append
- DEC-V61-198 — APU bay strategic pivot (Pillar 3 RAG corpus)
- `case_012_hvac_supply_diffuser/scripts/05_postprocess.py` — source
- `solver_convergence_playbook.md` § S22/S23 — ADPI stratification candidates

## Open questions

- Should `AdpiResult` carry per-point `θ_ED` for visualization?
- Should `compute_throw_distance` accept arbitrary axis (not just z)?
  case_012 uses z (vertical jet); future side-throw HVAC cases need x/y.
