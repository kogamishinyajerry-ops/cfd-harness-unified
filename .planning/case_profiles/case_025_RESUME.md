# case_025 · RESUME

**Case**: Plane Poiseuille Channel · simplest possible analytical canonical
**Started**: 2026-05-15 (V64-A B67 dispatch · 6th FULL attempt · companion to B66 BFS)
**Status**: **FULL strict-PASS landed** (commit 4 of 4) · sub-DEC Accepted
**Parent DEC**: DEC-V64-A-charter
**Sub-DEC**: DEC-V64-A-sub-M-V64A-VAL-FULL-POISEUILLE · **FULL** · first strict-FULL of V64-A arc

## North Star (one line)

> 在 4/4 PARTIAL track 之后用 THE simplest analytical canonical (plane Poiseuille · 1D parabolic u(y) · Re=133 deep laminar) 隔离 "infrastructure 是否健全" — 若 PASS 说明 V64-A 流水线干净, PARTIAL track 是 physics-driven; 若 PARTIAL 说明系统性 infrastructure 问题 (重大发现).

## Canonical reference

- Schlichting H. & Gersten K. (2017). *Boundary-Layer Theory*, 9th ed. Springer, §5.1.1
- White F.M. (2016). *Viscous Fluid Flow*, 3rd ed. McGraw-Hill, §3.3.1
- Analytical: u(y) = (3/2)·u_mean·(1 - (y/H)²), y ∈ [-H, +H]
- u_mean = 0.1 m/s · ν = 1.5e-5 m²/s · H = 0.01 m
- u_max = 0.15 m/s · dp/dx = -0.045 m²/s²/m · τ_wall = 3e-4 m²/s² · Re_h = 133.3

## Sandbox path

- Repo dicts: `.planning/case_profiles/case_025_v64_poiseuille_dicts/`
- Local-run mount: `~/Desktop/case_025_poiseuille_channel/case/` (copied from repo dicts at commit-2 mesh time)
- OpenFOAM: `~/OpenFOAM-v2512/etc/bashrc` (host install · macOS Apple Silicon)

## Verdict scale (per briefing)

- **FULL**: max |Δu| < 1% across 17+ y-points AND residuals 4/4 < 1e-8 AND |Δ dp/dx| < 1%
- **Marginal**: max |Δu| ∈ [1%, 3%] · documented & user-ratified
- **PARTIAL**: max |Δu| > 3% OR residuals not converged OR setup unfeasible

## Done dim advancement target

- Standalone strict PASS → Done #1 0/3 → **1/3 strict FULL**
- Coupled with B65 case_024 cavity Re=1000 (best of arc, 17/17 strict u at max 2.24%) if user ratifies cavity Re=1000 as standalone strict-PASS → 0/3 → **2/3 strict FULL**
- PARTIAL → stays 0/3 (per honest-failure-recording authorization)
- Done #2 already MET (3/3) ✓ — Schlichting/White canonical is reference but doesn't add to MET quota

## Outcome (final · post-B67 dispatch)

| Strict criterion | Achieved | Status |
|---|---|---|
| max \|Δu\| exit station | **0.0425%** of u_max | ✓ PASS (margin ×24) |
| Exit 40/40 strict 1% | **40/40** | ✓ PASS |
| Mid-channel 40/40 strict 1% | **40/40** (max 0.286%) | ✓ over-PASS |
| \|Δ dp/dx\| linear fit | **-0.1233%** | ✓ PASS (margin ×8) |
| residuals (laminar 3-field) | **3/3 < 1e-8** | ✓ PASS |
| τ_w cross-check Δ_mean | **-0.56%** | ✓ PASS (×3.6) |

**STRICT FULL TRIFECTA** → **Done #1 advances 0/3 → 1/3 strict FULL** (standalone)

## Realised vs expectation

- Expected max |Δu| < 0.5%: **achieved 0.04%** (×12 better than expectation)
- codedFixedValue compile: succeeded after `--user $(id -u):$(id -g)` fix (initial UID=0 security block · F-NEW-A V-row)
- simpleGrading bilinear single-block symmetric: worked cleanly · checkMesh max AR 3.66 · cell vol ratio 3:1 exactly as designed (F-NEW-B V-row)
- CASE_SPEC τ_w formula error (factor 2 vs 3): caught by cross-check, transparently disclosed (F-NEW-D V-row)

## Codex sync status

**Skipped**. No security boundary · no byte-repro path · same justification as case_022 / case_024 sub-DECs.

## Methodological inflection signal for V64-A retro

6th attempt at THE simplest analytical canonical clearing strict-FULL on first try is strong evidence that V64-A infrastructure is sound and prior 5 PARTIALs were real-physics-driven (NOT pipeline-driven). Candidate for dedicated retrospective doc.

## Commit chain

- Commit 1 (2e72199): substrate prep · parts_manifest + CASE_SPEC + RESUME
- Commit 2 (042a969): mesh prep · 9 dicts + 2 logs + MESH_PREP_LOG.md
- Commit 3 (82a35b2): simpleFoam run + 40-y-point u(y) + dp/dx + extract_poiseuille.py + RUN_LOG.md
- Commit 4 (this): validation report + sub-DEC + RESUME update

## Next action

Main session reconciles ARC-GOAL.md Done #1 0/3 → 1/3 strict; updates Notion DEC sync at session-end batch (this sub-DEC + cavity-v2 disjoint scope sub-DEC).
