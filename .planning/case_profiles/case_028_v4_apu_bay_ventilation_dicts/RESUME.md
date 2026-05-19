# case_028 v3 · APU Bay Ventilation · STL-driven intake/vent · RESUME

**Created**: 2026-05-16 by V65-A B78 (Claude Code Opus 4.7 · autonomous mode)
**Predecessor**: case_028 v2 (V65-A B77 · strong-PARTIAL · `8eedc75`)
**Verdict status**: pending solver execution

## Purpose

v1 hypothesis empirically refined in B77: replacing 4 lateral slip→noSlip was **necessary but not sufficient**.
v3 closes the missing component: replace bg-block inlet/outlet (10.5 m² area each) with **STL-driven intake_duct / vent_door** apertures (~1 m² / ~0.3 m²) — predicted to drop mass flow into SAE AIR1168/4 typical APU bay range (0.5-2 kg/s).

## Key change from v2

| Surface | v2 | v3 |
|---|---|---|
| bg-block -x face | `patch` (inlet · U=5 m/s) | `wall` (renamed `end_minus_x`) |
| bg-block +x face | `patch` (outlet · zeroGradient) | `wall` (renamed `end_plus_x`) |
| intake_duct STL | sHM patchInfo `wall` | sHM patchInfo `patch` · surfaceNormalFixedValue U=1.5 m/s inflow |
| vent_door STL | sHM patchInfo `wall` | sHM patchInfo `patch` · inletOutlet BC · p=0 reference |
| 4 lateral patches | `wall` (noSlip · from v2) | unchanged |
| 27 remaining STL components | `wall` | unchanged |

## Quick re-run (sandbox)

```bash
cd ~/Desktop/case_028_apu_bay_ventilation/case_v3/
# (v3 sandbox · separate from v1/v2 sandbox at ~/Desktop/case_028_apu_bay_ventilation/case/)

# 1. Mesh
docker run --rm -v $(pwd):/case -w /case opencfd/openfoam-default:2312 blockMesh
docker run --rm -v $(pwd):/case -w /case opencfd/openfoam-default:2312 snappyHexMesh -overwrite
docker run --rm -v $(pwd):/case -w /case opencfd/openfoam-default:2312 checkMesh

# 2. Solver
docker run --rm -v $(pwd):/case -w /case opencfd/openfoam-default:2312 simpleFoam > log_simpleFoam.txt 2>&1

# 3. Advisor (from project root)
cd /Users/Zhuanz/Desktop/cfd-harness-unified
env -i HOME=$HOME PATH=/usr/local/bin:/usr/bin:/bin .venv/bin/python -m scripts.case_028_apu_bay.run_advisor_stack --case-dir .planning/case_profiles/case_028_v3_apu_bay_ventilation_dicts
```

## Verdict rubric (per B78 brief)

- **FULL** if: residual < 1e-4 on 4/4 + mass balance < 1% + advisor ≥6/9 + experimental delta < 50% on mass flow ✓
- **strong-PARTIAL** if: 3/4 FULL criteria met
- **PARTIAL** if: any of {convergence, mass balance} FAIL

## Done dim impact (predicted)

- Done #4 industrial-grade FULL: **0/3 → 1/3 if FULL** (first industrial-grade FULL for V65-A · Pillar 1 35→~50)
- Done #2 V101+ promotion: unchanged
- Done #6 V-row clause-1: maintained at 8/9+ on case_028 (regression OK)
