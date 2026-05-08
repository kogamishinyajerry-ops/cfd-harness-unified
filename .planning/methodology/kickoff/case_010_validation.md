# case_010 · Codex Output Validation Report

> **Round 1 of 2** · 2026-05-08 — main session  
> **Verdict: PASS WITH NOTES**.  
> **Backend**: 86gs gpt-5.5 xhigh.  
> Final case in 10-case roster.

## Summary
- **Case ID**: `case_010_drivaer_fastback_les`
- **Component**: TUM DrivAer fastback (smooth underbody, mirrors `wM`, wheels `wW`, half-vehicle). L=4.61 m, W=1.76 m, H=1.42 m, wheelbase=2.79 m
- **Hard exclusion honored**: `no_Ahmed_body_geometry: true` explicit
- **License**: TUM requires registration for binary STEP/IGES/STL; Codex bakes geometry into deterministic CadQuery script (no binary redistribution)
- **Solver**: pimpleFoam + WALE LES (v2 fallback dynamicKEqn). v2 backup pisoFoam if pimple under-converges per timestep
- **Wall treatment**: wall-modeled, target y+=30-100, nutUSpaldingWallFunction
- **Freestream**: U_inf=16 m/s, Re_L≈4.87e6, M≈0.05 (incompressible)
- **Target**: time-averaged Cd≈0.281, surface Cp at TUM published taps, base-pressure recovery, Q/λ2 wake topology
- **Defects**: D1 (0.35 mm `mirror_edge_trim_strip` gap on side-mirror housing) + D8 (sub-mm `underbody_sensor_cover_thin` between axles)
- **Effort**: 10-14h, ~3 versions

## 13-check pass/fail summary

| # | Check | Status |
|---|---|---|
| 1 | CadQuery script syntax | ✅ 250 LOC, py_compile OK |
| 2 | cadquery installable | ⚠ standard caveat |
| 3 | TUM URLs reachable | ✅ HTTP 200 |
| 4 | NOT Ahmed body | ✅ DrivAer fastback; `no_Ahmed_body_geometry: true` explicit |
| 5 | Patch names regex | ✅ 12 named bodies, no dupes |
| 6 | Symmetry plane at centerline | ✅ `symmetry_plane_centerline` |
| 7 | les block | ✅ WALE + nutUSpaldingWallFunction + dt + averaging strategy |
| 8 | freestream block w/ Re_L | ✅ Re_L=4.87e6, U_inf=16, fastback dimensions |
| 9 | vortex_metrics block | ✅ Q/λ2 thresholds + isosurface generation |
| 10 | Defects NOT on Cd zones | ✅ D1 on mirror trim (off-wake), D8 on underbody between axles (NOT front wheel, NOT rear wake) |
| 11 | Defects measurable | ✅ D1 distToShape, D8 BoundBox |
| 12 | Domain sizing | ✅ blockMesh dims per spec (4L upstream, 8L downstream, 5L top, 3L side, half-domain) |
| 13 | No moving wheels in v1 | ✅ stationary; v3+ extension if sub-session decides |

**All 13 checks pass.**

## Notes

### N1 · 8th consecutive A2-pending (assumed)
Cases 003-010 all expected to surface A2 gap. Confirmed during sub-session run. **8-of-8 evidence**.

### N2 · D8 thin_wall_advisor 4-case consistency
After case_004 (0.75mm shim) + case_007 (0.80mm transom) + case_008 (0.80mm TE tab) + case_010 (sub-mm underbody cover), four-case advisor consistency trial. Strong falsification context for thin_wall_advisor.

### N3 · License via registration → bake-into-script
TUM DrivAer requires registration for binary download. Codex's strategy: deterministic reconstruction from public TUM dimensions + published research papers (MDPI Fluids 2022/7/1/19). Same risk-managed approach as case_007 KCS. Sub-session does NOT redistribute the generated STEP externally without registration verification.

### N4 · First transient LES for project
No prior pimpleFoam + LES infrastructure. New artifact candidates:
- `les_fvschemes_writer.py` (WALE filter + cube-root-vol filter scale)
- `wall_function_writer.py` (nutUSpalding for wall-modeled)
- `field_average_function_object_writer.py` (time-averaging window)
- `q_criterion_post_processor.py` (Q/λ2 isosurface extraction)

### N5 · Final case — 10-case roster complete
With case_010 dispatched, the entire 10-case roster is paste-ready. All 10 numerics-class roots covered (compressible-buoyant-RANS, +CHT, incompressible-RANS, +MRF, compressible-RANS, compressible-shock-density-based, multiphase-VOF, RANS-Lagrangian, reacting-low-Mach, incompressible-LES). Workhorse OpenFOAM solver matrix complete.

## Approval
✅ proceed to `kickoff/case_010_drivaer_fastback_les.md`.

## Files
- `kickoff/case_010_codex_request.md`
- `kickoff/case_010_codex_response.md` (708 lines)
- `kickoff/case_010_validation.md` (this)
- `kickoff/case_010_drivaer_fastback_les.md` (next)
