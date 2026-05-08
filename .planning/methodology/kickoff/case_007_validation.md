# case_007 · Codex Output Validation Report

> **Round 2 of 2** · 2026-05-08 — main session
>
> **Verdict: PASS WITH NOTES**.
>
> **Round 1 history**: Codex hallucinated a "read-only workspace"
> objection (misread Deliverable 3 = path string as binary STEP
> requirement). Round 2 succeeded with explicit clarification
> prepended.
>
> **Backend**: 86gs gpt-5.5 xhigh (primary path, recovered from
> case_006 503).

## Summary

- **Case ID**: `case_007_kcs_ship_vof`
- **Component**: KRISO Container Ship KCS half-hull, ITTC G2010 / Tokyo Workshop benchmark
- **Source**: Tier-1-adjacent — NMRI/Tokyo Workshop public pages (URLs HTTP 200, license context noted: pages don't show explicit redistribution prohibition; Codex bakes hull offsets into script rather than redistributing binary)
- **Solver**: interFoam (steady-like via tail-averaged unsteady), v2 fallback interIsoFoam, Fr=0.26, U_inf=2.1962 m/s, Re=1.4e7, Lpp=7.2786 m model scale
- **Defects**: D1 (0.35 mm rudder hub gap) + D8 (0.80 mm thin transom plate above waterline)
- **Effort**: 8-12h, ~3 versions

## Check pass/fail summary

| # | Check | Status |
|---|---|---|
| 1 | CadQuery script syntax | ✅ 312 LOC, py_compile OK |
| 2 | cadquery installable | ⚠ standard caveat (sub-session venv) |
| 3 | Source URLs reachable | ✅ both NMRI URLs HTTP 200 |
| 4 | Patch names regex valid | ✅ 10 named bodies, no dupes |
| 5 | Symmetry plane at centerline | ✅ U/alpha.water/p_rgh: symmetry |
| 6 | Atmosphere `alpha.water: inletOutlet` | ✅ + p_rgh: totalPressure(p0=0) |
| 7 | water_inlet/outlet alpha.water BC | ✅ variableHeightFlowRate / zeroGradient |
| 8 | multiphase block | ✅ ρ_w=998.8, ρ_a=1.225, ν_w=1.05e-6, ν_a=1.5e-5, σ=0.072 |
| 9 | reference_conditions | ✅ Fr=0.26, U_inf, Re, Lpp, design WL |
| 10 | wave_metrics | ✅ Ct/Cf(ITTC-1957)/Cw + wave cut at y/L=0.1509 |
| 11 | Defects measurable | ✅ D1 distToShape, D8 BoundBox |
| 12 | Defects in safe zones | ✅ hull surface untouched, wave cut line untouched |
| 13 | Solver class match | ✅ multiphase-VOF / interFoam |

**All 13 checks pass.**

## Notes

### N1 · License context

KCS source pages (Tokyo 2015 + NMRI gothenburg2000) do not show
explicit redistribution prohibition but also no explicit
permission. Codex's strategy of baking hull offsets into the
CadQuery script (rather than redistributing a binary STEP) is
the right risk-managed path. Sub-session can use the script's
output STEP locally; external publication would require explicit
ITTC permission check.

### N2 · A2 advisor LANDED (2026-05-08)

D1's `expected_advisor_to_catch: virtual_interface_detector`
(backfilled from `_pending_A2`). The 5-of-5 compounded evidence
across cases 003-007 (later 8-of-8 through case_010) triggered
A2 extraction; advisor landed in commit `a09ae0a` at
`ui/backend/services/geometry_ingest/virtual_interface_detector.py`.

### N3 · D8 exercises landed advisor

D8's `expected_advisor_to_catch: thin_wall_advisor` (LANDED).
0.80 mm transom plate is similar to case_004's 0.75 mm yaw_sensor_shim.
Sub-session should observe consistent thin_wall_advisor behavior
across both cases; if results diverge, that signals advisor
sensitivity to context (geometry topology, refinement level).

### N4 · First multiphase case for project

The harness has no prior `interFoam` infrastructure. New artifact
candidates after sub-session:
- `multiphase_bc_writer.py` (alpha.water + p_rgh + free-surface
  family)
- `setFields_water_level_writer.py` (initialize alpha.water from
  design waterline z)
- `wave_cut_post_processor.py` (alpha=0.5 iso-surface + y/L
  longitudinal cut + Cw extraction via tail-averaged forces minus
  Cf(ITTC-1957))

### N5 · Round 1 hallucination logged

Round 1 Codex refused with "read-only workspace can't write
binary STEP" — misreading of Deliverable 3 spec (which is a path
STRING, not a binary file). Round 2 with explicit clarification
prepended succeeded. Pattern to watch: future Codex case-design
prompts should include the clarification preamble in the prompt
template to prevent recurrence. Filing as RETRO addendum candidate.

## Approval to dispatch

✅ proceed to `kickoff/case_007_kcs_ship_vof.md`.

## Files

- `kickoff/case_007_codex_request.md`
- `kickoff/case_007_codex_response.md` (round 2 output, 644 lines)
- `kickoff/case_007_validation.md` (this file)
- `kickoff/case_007_kcs_ship_vof.md` (next)
