# case_026 · RESUME

**Case**: Plane Couette Channel · 1D LINEAR analytical · pure shear-driven · companion to B68 Poiseuille FULL
**Started**: 2026-05-15 (V64-A B69 dispatch · 7th FULL attempt · post-B68 strict-FULL precedent)
**Status**: IN FLIGHT (Commit 1 of 4 · substrate prep)
**Parent DEC**: DEC-V64-A-charter
**Sub-DEC**: DEC-V64-A-sub-M-V64A-VAL-FULL-COUETTE (in flight · drafted Commit 4)

## North Star (one line)

> 在 B68 Poiseuille 第一个 strict-FULL 之后, 用 1D LINEAR 更简单的 plane Couette canonical 推 Done #1 1/3 → 2/3 strict · 三轴差异化 (BC source / dp_dx / profile shape) 使其为真正第二 canonical, 不是 rebadge.

## Canonical reference

- Schlichting H. & Gersten K. (2017). *Boundary-Layer Theory*, 9th ed. Springer, §5.1.0
- White F.M. (2016). *Viscous Fluid Flow*, 3rd ed. McGraw-Hill, §3.2.1
- Analytical: u(y) = U_top · y/H, y ∈ [0, H]
- U_top = 0.1 m/s · ν = 1.5e-5 m²/s · H = 0.01 m
- du/dy = 10 1/s (constant) · dp/dx = 0 · τ_wall = ν·U_top/H = 1.5e-5 m²/s² · Re_h = 66.67

## Sandbox path

- Repo dicts: `.planning/case_profiles/case_026_v64_couette_dicts/`
- Local-run mount: `~/Desktop/case_026_plane_couette/case/` (copied from repo dicts at commit-2 mesh time)
- OpenFOAM: Docker `opencfd/openfoam-default:2312` (matches B68 path) OR host `~/OpenFOAM-v2512/etc/bashrc`

## Verdict scale (per briefing)

- **FULL**: max |Δu| < 1% across 17+ y-points AND residuals 4/4 < 1e-8 AND |Δ τ_w| < 1% (τ_w replaces dp/dx in strict trifecta since pure shear has dp/dx ≡ 0 analytically)
- **Marginal**: max |Δu| ∈ [1%, 3%] · documented & user-ratified
- **PARTIAL**: max |Δu| > 3% OR residuals not converged OR setup unfeasible

## Done dim advancement target

- Standalone strict PASS → Done #1 1/3 → **2/3 strict FULL** (cumulative with B68 Poiseuille)
- PARTIAL → stays 1/3 (per honest-failure-recording authorization)
- Done #2 already MET (3/3) ✓ — Schlichting/White Couette is canonical reference but doesn't add to MET quota

## Differentiation from B68 Poiseuille (3 axes)

| Axis | B68 Poiseuille | B69 Couette (this case) |
|---|---|---|
| BC source | inlet codedFixedValue parabolic | top fixedValue sliding wall + inlet codedFixedValue linear |
| Profile shape | parabolic (3/2)·u_mean·(1-(y/H)²) | linear U_top·y/H |
| dp/dx | -0.045 m²/s²/m (nonzero) | 0.0 (zero · pure shear) |
| Mesh y-grading | bilinear 3:1 toward both walls | uniform (no grading needed for linear profile) |
| Domain | y ∈ [-H, +H] (symmetric · two walls) | y ∈ [0, H] (asymmetric · one moving, one stationary) |
| Re_h | 133 (based on 2H hydraulic dia) | 66.7 (based on H gap) |
| τ_w analytical | 3·ν·u_mean/H = 4.5e-4 m²/s² | ν·U_top/H = 1.5e-5 m²/s² |

This is a GENUINE second canonical, not a rebadge.

## Outcome (TBD · final values after Commit 3)

(populated in Commit 4)

## Codex sync status

**Skipped**. No security boundary · no byte-repro path · same justification as case_022 / case_024 / case_025 sub-DECs (no auth / signing / authz / operator endpoint · pure read-only solver + analysis).

## Commit chain (planned)

- Commit 1: substrate prep · parts_manifest + CASE_SPEC + RESUME
- Commit 2: mesh prep · 9 dicts + 2 logs + MESH_PREP_LOG.md
- Commit 3: simpleFoam run + 40-y-point u(y) + τ_w + extract_couette.py + RUN_LOG.md
- Commit 4: validation report + sub-DEC + RESUME update with verdict

## Next action

Commit 1 finalize → Commit 2 mesh prep.
