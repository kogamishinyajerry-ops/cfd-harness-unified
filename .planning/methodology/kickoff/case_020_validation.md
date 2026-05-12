# case_020 Codex Output Validation

> **Verdict**: **PASS** · **FINAL CASE in 11-case industrial-extension batch**
> **Designed by**: Codex (gpt-5.4 high, CRS) · 117k tokens, single-round emit
> **Validated**: 2026-05-08 · cap=3, R1 only
> **Note**: Section markers normalized

## Validation checklist

| # | Check | Result | Notes |
|---|---|---|---|
| 1 | CAD source declared | ✅ | Tier-3 parametric fallback (no Tier-1 ERCOFTAC porous-filter CAD found); HEPA terminal filter cassette |
| 2 | py_compile | ✅ | 167 LOC clean |
| 3 | Names regex | ✅ | All entities valid |
| 4 | Single fluid region + cellZone | ✅ | region_fluid + porous_zone_filter_element |
| 5 | Filter geometry | ✅ | rounded-rectangle HVAC housing with HEPA cassette + plenum |
| 6 | D9 faceted | ✅ | 16 facets per 90° on housing corner curvature |
| 7 | D10 open shell | ✅ | 1.0 mm slit at filter-frame corner connecting upstream + downstream plenums (within 0.5-2 mm spec); FIRST D10 INJECTION |
| 8 | Operating point | ✅ | U_face=2.5 m/s, Re_housing≈3.3e4, air at standard conditions |
| 9 | Darcy-Forchheimer anisotropic | ✅ | streamwise < cross-stream resistance; `coordinateSystem` basis flagged as failure mode |
| 10 | Bypass flow metric | ✅ | bypass through D10 as % of total flow — quantifies leak path |
| 11 | Reference data tolerance | ✅ | Δp ±10%, uniformity ±0.05 |
| 12 | Industrial flavor | ✅ | HEPA terminal filter cassette (data center / clean room industry) |
| 13 | D10 advisor-gap V-finding | ✅ | flagged as new failure mode; first D10 in project |
| 14 | D9 advisor-gap V-finding | ✅ | 2nd or 3rd D9 evidence (after case_016 + 017) |

## Batch close note

case_020 closes the **11-case industrial-extension batch**
(case_011-020). All 9 codex_request files written + dispatched +
validated + kickoffs prepared. Defect catalog coverage complete:
D1 (11×), D2 (1×), D5 (2×), D6 (2×), D7 (2×), D8 (3×), D9 (3×),
D10 (1×). D3 + D4 remain uncovered (carry to next batch).

## Decision: **PASS**
