---
decision_id: DEC-V61-107
title: fvSchemes upgrade for non-orthogonal STL meshes (partial — fvSchemes-only scope)
status: Accepted (2026-04-30 · scope is "fvSchemes-only · partial of broader V107 plan" — the full V107 plan was elaborated and supplanted by V107.5 within hours, so V107 lands as a clean partial close. Codex APPROVE on commit e929f01 first round.)
authored_by: Claude Code Opus 4.7 (1M context)
authored_at: 2026-04-30
authored_under: |
  user direction "全权授予你开发，全都按你的建议来" + standing CFD strategic
  target "处理任意的 CAD 几何". Surfaced from iter01 adversarial defect analysis
  showing that gmsh-tetrahedralized non-orthogonal STL meshes require corrected
  Laplacian schemes + nNonOrthogonalCorrectors > 0 to converge cleanly.
parent_decisions:
  - DEC-V61-103 (Imported-case BC mapper · provides the named-patch substrate this DEC's solver-config tuning targets)
  - DEC-V61-104 (Interior obstacle topology · gmsh tet meshes from CAD imports are inherently non-orthogonal)
  - RETRO-V61-001 (risk-tier triggers · OpenFOAM solver config change → mandatory Codex review)
parent_artifacts:
  - ui/backend/services/case_solve/foam_agent_adapter.py (fvSchemes write site)
  - tools/adversarial/results/iter01_v61_104_phase1_partial_findings.md (defect class motivating the change)
counter_impact: +1 (autonomous_governance: true)
self_estimated_pass_rate: 85% (bounded scope — single config-file change; expected first-pass APPROVE)
actual_pass_rate: 100% (Codex R1 APPROVE on first round — calibration was honest)
codex_tool_report_path: reports/codex_tool_reports/v61_107_partial_fvschemes_upgrade.md (commit 47ae9e5)
implementation_commits:
  - e929f01 (fix(case-solve): DEC-V61-107 partial — fvSchemes upgrade for non-orthogonal STL meshes)
  - 47ae9e5 (docs(reports): DEC-V61-107 partial — Codex APPROVE via 86gs relay)
follow_up_dec: V61-107.5 (the broader V107 plan — pimpleFoam migration — was peeled into V107.5 the same day; V107 closes here as the partial-scope fvSchemes change only)
notion_sync_status: pending — to sync 2026-05-02

# Why now

iter01 adversarial test surfaced slow convergence on the gmsh-tet
mesh of a thin-blade-in-plenum geometry. Diagnosis: the icoFoam
fvSchemes config used `default Gauss linear` for Laplacian schemes
and `nNonOrthogonalCorrectors 0` — both reasonable for orthogonal
hex meshes (the LDC dogfood path) but inadequate for the heavily
non-orthogonal tets gmsh produces from arbitrary CAD imports.

The fix is bounded: switch Laplacian schemes to `Gauss linear
corrected` and bump `nNonOrthogonalCorrectors` to 2 in the SIMPLE
control loop. No new code paths, no new file formats, no new
threat surface — just a config-file string update with a regression
test for the new shape.

# Decision

Bounded fvSchemes upgrade only. The fuller V107 plan that was
sketched (pimpleFoam migration + post-flight rejection plumbing
for the named-patch BC mapper) was peeled into DEC-V61-107.5
within the same session — V107.5 ended up requiring 9 Codex
rounds vs. V107's 1, validating the decision to keep them as
separate DECs.

# Codex narrative

R1 APPROVE on first round. Codex commented that the test fixture's
expected residual envelope might need re-baselining if the new
schemes produce systematically smaller residuals; the comment was
non-blocking and the fixture stayed unchanged because the existing
envelope was permissive enough.

Self-pass-rate estimate (85%) was on-mark — calibration debt: zero.

# Verification

- Smoke baseline (4 PASS · 0 EF · 2 SKIP · 0 FAIL) preserved
- Existing fvSchemes regression tests stayed green
- Codex R1 APPROVE commit 47ae9e5 chain report

# Future work

DEC-V61-107.5 picks up the pimpleFoam migration and the named-patch
mapper post-flight rejection plumbing. DEC-V61-108 picks up the
per-patch BC override surface. The arc V107 → V107.5 → V108
materially advances the user's North Star "engineer-editable BCs
on arbitrary CAD geometry".
