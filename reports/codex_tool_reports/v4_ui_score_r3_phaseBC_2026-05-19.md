# V4 UI Codex-relay scoring · Phase B+C · 2026-05-19

> Basis: source audit of current working tree under `ui/frontend/src/pages/workbench/v4` and `ui/frontend/src/visualization/viewport_kernel.ts`. No browser visual run.
>
> Reviewer: Codex relay 86gamestore backend · `gpt-5.5` (xhigh effort)
> Rubric: `.planning/transitions/2026-05-18_v4_ui_spec.md` §0 (binding)
> Prior rounds: R1=85/100 (SVG), R2=93/100 (SVG, token migration)
> Tokens consumed: 160,687

## Verdict: **PASS · 91/100**

| Dim | Score | Max | Notes |
|---|---:|---:|---|
| L · Layout | 18 | 20 | 5-zone frame, 224/300/96/60 proportions, connected rail intact |
| C · Color | 14 | 15 | V4 token discipline mostly preserved; vtk highlight colors are hard-coded floats |
| T · Typography | 14 | 15 | KPI/rail/pill sizes strong; post KPI can stringify long array values |
| M · Mode content | 21 | 25 | Real backend + vtk + picking raise fidelity, but mesh/post/boundary diverge from blueprint structure |
| F · Industrial feel | 15 | 15 | Full-bleed vtk viewport, no V3 chrome, CAE feel materially stronger |
| P · Polish | 9 | 10 | Picking, hover, reverse highlight, pulse, DOE ring good; silent pick degrade remains |
| **TOTAL** | **91** | **100** | **PASS** |

## Comparison to R2 baseline

| Dim | R2 SVG | B+C | Δ | Why |
|---|---:|---:|---:|---|
| L | 18 | 18 | 0 | Same shell proportions and connected BottomBar |
| C | 15 | 14 | -1 | `viewport_kernel.ts` highlight cyan/yellow bypass V4 tokens |
| T | 14 | 14 | 0 | Typography still mostly compliant |
| M | 24 | 21 | -3 | Real data improves truthfulness, but mesh histograms/post gauge/boundary callouts regressed |
| F | 15 | 15 | 0 | Real vtk viewport improves industrial credibility |
| P | 7 | 9 | +2 | R2 under-counted polish; Phase C adds picking + reverse highlight |
| **TOTAL** | **93** | **91** | **-2** | Better engineering ceiling, lower strict blueprint structural fidelity |

## Per-dimension findings

**L · Layout**
- Strong: shell still renders TopBar, LeftRail, MainCanvas+KPI, RightPanel, BottomBar in the correct frame at WorkbenchShellV4.tsx:42.
- Strong: LeftRail is `w-[224px]`, KPI strip is `h-24`, BottomBar is `h-[60px]` at LeftRailV4.tsx:344, KpiStripV4.tsx:240, BottomBarV4.tsx:148.
- Minor gap: real geometry/boundary side legends consume MainCanvas width; acceptable, but not as visually clean as the R2 SVG ideal.

**C · Color**
- Strong: V4 palette and expanded `scene`, `cadParts`, `bcTypes`, `V4_CFD_COLORMAP` SSOT remain in place at industrial_minimalist.ts:17.
- Regression from R2: vtk pick/hover overlays use hard-coded RGB floats, not V4 tokens, at viewport_kernel.ts:783 and viewport_kernel.ts:791.

**T · Typography**
- Strong: KPI values remain 30px tabular numbers at KpiStripV4.tsx:252; LeftRail tree is 11px at LeftRailV4.tsx:388.
- Gap: post KPI chips can stringify non-number `key_quantities`, including arrays, into 30px KPI text at KpiStripV4.tsx:198.

**M · Mode Content**
- Strong: Phase B fan-out hook is real and read-only: cases, basics, mesh, completeness, runs, latest detail, successful detail at useV4WorkbenchContext.ts:77.
- Strong: Phase C viewport avoids 404 mounting via GLB probe at useGlbAvailability.ts:42, mounts vtk full-bleed at ViewportV4.tsx:320, and supports pick + reverse highlight at ViewportV4.tsx:252 and viewport_kernel.ts:873.
- Regression from R2: mesh no longer has the blueprint's 5 histogram chips plus second numeric KPI row; it now renders 4 QC pills plus density chart at ModeRendererMesh.tsx:279.
- Regression from R2: post no longer has 3 mini profile charts plus radial gauge; it has centerline and residual bars at ModeRendererPost.tsx:347.
- Regression from R2: boundary real/fallback views do not render rounded callout labels with leader lines; fallback only mounts `IndustrialBoxScene` without BC label children at ModeRendererBoundary.tsx:172.
- Regression from R2: real-case RightPanel replaces mode-specific blueprint cards with generic matcher pills at RightPanelV4.tsx:132.

**F · Industrial Feel**
- Strong: vtk wrapper drops V3 chrome and keeps a full-bleed canvas at ViewportV4.tsx:4.
- Strong: SVG fallback still has glass walls, floor, shadow, zoned engine body, rotor blades, and struts at IndustrialBoxScene.tsx:233 and IndustrialBoxScene.tsx:357.
- Strong: solver/post streamlines remain curved and dense via `StreamlineField count={72}` / `count={60}` at ModeRendererSolver.tsx:105.

**P · Polish**
- Strong: BottomBar active glow/pulse is present at BottomBarV4.tsx:69; DOE ring/scale is present at ModeRendererDoe.tsx:53.
- Strong: Advisor progressive disclosure has `aria-expanded` at AdvisorPillStack.tsx:95.
- Gap: face-index fetch failure silently disables picking with no soft UI status at ViewportV4.tsx:305.

## Top 3 concrete improvements for R4

1. **Restore mesh/post blueprint structures with real data**: add backend bins for the 5 mesh histograms and residual/profile history for post's 3 mini charts + gauge, while keeping GCI/centerline as extra real overlays.
2. **Add real viewport annotation overlays**: BC callout labels with leader lines, selected patch labels, and tokenized pick/hover colors.
3. **Unify real-run data surfaces**: make Post KPI use `successfulRunDetail` when Post does, filter array key quantities out of KPI chips, and merge mode-specific RightPanel cards with matcher pills instead of replacing them.
