# Codex Review · DEC-V61-107 partial (fvSchemes upgrade)

**Reviewed commit**: `e929f01`
**Risk-tier triggers** (per RETRO-V61-001): "OpenFOAM solver report fix" — modifying authored fvSchemes counts as a solver-config change for the case_solve hot path.
**Relay backend**: 86gamestore (`~/.codex-relay`, gpt-5.4, xhigh effort)
**Command**: `codex review --commit e929f01`

## Verdict

**APPROVE** (no findings)

Direct quote:
> "The commit only adjusts the fvSchemes authored by the STL-patch BC path, and the new OpenFOAM schemes are syntactically valid and consistent with the existing icoFoam setup. I did not find a discrete regression or runtime failure introduced by this change in the touched code."

## Scope reviewed

`ui/backend/services/case_solve/bc_setup_from_stl_patches.py` — fvSchemes block changed:
- `divSchemes div(phi,U)`: `Gauss linear` → `Gauss linearUpwind grad(U)`
- `laplacianSchemes default`: `Gauss linear orthogonal` → `Gauss linear corrected`
- `snGradSchemes default`: `orthogonal` → `corrected`

## Verification preserved

- 4 PASS · 0 EF · 2 SKIP · 0 FAIL adversarial smoke baseline
- 15/15 BC mapper tests
- 27/27 V61-106 framework tests

## Honest scope

This commit lands the universally-correct fvSchemes upgrade and does NOT fix iter01's structural divergence. The dt sweep + log inspection chain documented in `tools/adversarial/results/iter01_v61_107_partial_2026-05-01.md` confirms the residual divergence is icoFoam-specific (lacks `adjustTimeStep` support); the fix needs a pimpleFoam migration deferred to DEC-V61-107.5.
