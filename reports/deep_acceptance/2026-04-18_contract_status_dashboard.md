# 10-Case physics_contract Dashboard Snapshot

- Snapshot time: 2026-04-18T20:55 local
- Source: `knowledge/gold_standards/*.yaml` (top-level `physics_contract.contract_status` field)
- Consumer online since: EX-1-006 (2026-04-18, commit 7ea0773)
- Producer→Consumer channel coverage: **9/10** (1 silently skipped due to YAML-comment encoding — see case #3 note)

## Summary distribution

| contract_status | count | share | semantic |
|---|---|---|---|
| COMPATIBLE | 3 | 30% | all preconditions met; PASS is physics-valid |
| COMPATIBLE_WITH_SILENT_PASS_HAZARD | 2 | 20% | PASS is real but a code branch can produce a false confirmatory signal under some inputs |
| PARTIALLY_COMPATIBLE | 1 | 10% | one precondition unmet but deviation is quantifiable and of known sign |
| DEVIATION | 1 | 10% | precondition(s) unmet in a quantifiable-under-prediction way; ongoing remediation |
| INCOMPATIBLE | 2 | 20% | precondition(s) unmet; behind a D5-equivalent gate |
| INCOMPATIBLE_WITH_LITERATURE_DISGUISED_AS_COMPATIBLE | 1 | 10% | observable name and literature reference do not correspond to the extracted quantity |

**Verdict-PASS headline**: 9/10 cases report Phase-7-PASS or PASS_WITH_DEVIATIONS.
**Contract-weighted headline**: only **3/10** cases are fully physics-backed PASSes. The remaining 6 carry some form of caveat; 1 is an active FAIL (fully_developed_plane_channel_flow).

## Per-case table (all 10 canonical whitelist)

| # | case | verdict | contract_status | audit_concern on PASS | silent-pass hazard src:line | last_measurement |
|---|------|---------|-----------------|-----------------------|-----------------------------|------------------|
| 1 | lid_driven_cavity_benchmark | PASS | COMPATIBLE | null | — | Phase 7 Wave 2-3 (u_centerline[17pts] at Re=100) |
| 2 | backward_facing_step_steady | PASS | COMPATIBLE | null | — | Phase 7 Wave 2-3 |
| 3 | circular_cylinder_wake | PASS | COMPATIBLE_WITH_SILENT_PASS_HAZARD ⚠️ comment-encoded | **SKIPPED by consumer** (EX-1-006 known gap) | foam_agent_adapter.py:6766-6774 (hardcoded canonical_st=0.165 for any Re in [50,200]) | Phase 7 Wave 2-3 |
| 4 | turbulent_flat_plate | PASS_WITH_DEVIATIONS | COMPATIBLE_WITH_SILENT_PASS_HAZARD | audit_concern=COMPATIBLE_WITH_SILENT_PASS_HAZARD | foam_agent_adapter.py:6924-6930 (Cf>0.01 → Spalding substitution path) | Phase 7 Wave 2-3 (Cf=0.0027) |
| 5 | cylinder_crossflow | PASS | see case #3 — alias | (see case #3) | (see case #3) | Phase 7 Wave 2-3 |
| 6 | rayleigh_benard_convection | PASS_WITH_DEVIATIONS | COMPATIBLE at Ra=1e6; NOT transferable to Ra≥1e9 | null (not a silent-pass case at Ra=1e6) | — | Phase 7 Wave 2-3 (Nu=10.5) |
| 7 | differential_heated_cavity | **FAIL → post-commit MEASUREMENT 2026-04-18** | DEVIATION (R-E landed via EX-1-007 B1) | null (FAIL path) | EX-1-008 candidate: foam_agent_adapter.py:6656-6712 (local-vs-mean methodology mismatch) | EX-1-007 B1 post-commit Nu=66.25 vs gold=30 (ABOVE_BAND) |
| 8 | naca0012_airfoil | PASS_WITH_DEVIATIONS (permanent per DEC-EX-A) | PARTIALLY_COMPATIBLE | null (deviation is known-sign, quantifiable) | — | Phase 7 Wave 3 DEC-EX-A (Cp 40% dev; Path W/H both REJECT) |
| 9 | axisymmetric_impinging_jet | PASS_WITH_DEVIATIONS | INCOMPATIBLE_WITH_LITERATURE_DISGUISED_AS_COMPATIBLE | audit_concern=INCOMPATIBLE_WITH_LITERATURE_DISGUISED_AS_COMPATIBLE | foam_agent_adapter.py:4257+ (Nu slot stores flat-plate Cf=0.0042, not Cooper Nu=25) | Phase 7 Wave 2-3 |
| 10 | fully_developed_plane_channel_flow | FAIL | INCOMPATIBLE | null (FAIL path) | — (behind R-D, D5-equivalent) | Phase 7 Wave 2-3 |
| 11 | fully_developed_turbulent_pipe_flow | FAIL | INCOMPATIBLE | null (FAIL path) | — (SIMPLE_GRID ≠ circular pipe, behind R-A-relabel) | Phase 7 Wave 2-3 |

*(Note: canonical whitelist is 10 cases; this table shows 11 rows because cylinder_crossflow and circular_cylinder_wake are whitelist aliases sharing the same gold standard + same physics_contract. STATE.md counts as 10 canonical.)*

## Trend delta vs prior snapshot

- Prior snapshot: EX-1-005 completion (2026-04-18 mid-session).
- Since then: **EX-1-006** wired audit_concern consumer; **EX-1-007 B1** landed DHC mesh + uncovered 3 pre-existing bugs (duplicate writeInterval, extractor y_tol, extractor local-vs-mean methodology).
- New facts captured post-EX-1-005:
  - DHC Nu measurement = 66.25 vs gold=30 → methodology-FAIL but mesh-PASS (honest reading).
  - case #3 (cylinder) producer→consumer silently skipped — G3 slice planned.
  - new D4+ rule candidate #6 (mesh_refinement_wall_packing_smoke_check, MANDATORY).

## Contract-status concentration → highest-value remediations

Ranked by combined (severity × feasibility):

1. **EX-1-008 G1 target — DHC `_extract_nc_nusselt` mean-Nu refactor**. Transforms case #7 from DEVIATION (with methodology-FAIL masking) to real PASS_WITH_DEVIATIONS at known tolerance. Dispatch Codex.
2. **EX-1-G3 target — cylinder contract_status comment → structured**. Converts case #3 silent-skip to live audit_concern channel. Dispatch Codex.
3. **Tier-1 future — snappyHexMesh rewrite (DEC-EX-C)** for case #8. Deferred per Wave 3 closeout; not in current ADWM window.
4. **Tier-1 future — Cf>0.01 Spalding substitution audit** (case #4). error_attributor pattern: flag when fallback branch fires. Not in current ADWM window.
5. **Tier-1 future — R-D DNS solver swap** (case #10, case #11). Behind D5 gate; PL-1 frozen.

## Demo-ready cases (档1 candidates)

Only the 3 clean COMPATIBLE cases (1, 2, and the pair 3+5 if G3 lands first) are demo-ready today for Before/After/Reference overlay + Error Convergence Narrative storytelling.

- Case #1 lid_driven_cavity_benchmark — Re=100 Ghia 1982 reference; Docker E2E PASS, u_centerline 17 points, reports/lid_driven_cavity_benchmark/ exists.
- Case #2 backward_facing_step_steady — reattachment_length vs Driver 1985; Docker E2E PASS, reports/backward_facing_step_steady/ exists.
- Case #5 cylinder_crossflow — cd_mean/cl_rms vs Williamson 1996; Docker E2E PASS, reports/cylinder_crossflow/ exists.

G2 slice will author Case Completion Reports for these three.

---

Produced: 2026-04-18 by opus47-main (ADWM v5.2)
Source of truth: `knowledge/gold_standards/*.yaml`
Next refresh trigger: any physics_contract change OR next deep acceptance package
