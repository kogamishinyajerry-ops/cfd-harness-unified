# V64-A · case_022 Driver-Seegmiller BFS · Full Validation Report

> **Sub-DEC**: DEC-V64-A-sub-M-V64A-VAL-FULL-5-BFS
> **Parent DEC**: DEC-V64-A-charter
> **Date**: 2026-05-15
> **Sandbox**: `~/Desktop/case_022_driver_seegmiller_bfs/case`
> **Repo dicts**: `.planning/case_profiles/case_022_v64_val_full_5_bfs_dicts/`

## 1. Headline verdict

**VERDICT: PARTIAL** on all four FULL gate dimensions.

| Gate dimension | Strict FULL target | Actual | Met? |
|---|---|---|---|
| Reattachment length | x_R/h ∈ [6.0, 6.5] | **5.443** | ✗ NOT MET (below marginal 5.5 floor too) |
| Cp 5-station Δ | \|Δ%\| < 10% all 5 | 1/5 within 10% (S2 only) | ✗ NOT MET |
| Cf 5-station Δ | \|Δ%\| < 20% all 5 (parts_manifest tol) | 1/5 within 20% (S5 only) | ✗ NOT MET |
| Residuals | 6/6 < 1e-5 | 1/5 met (ω only) | ✗ NOT MET |

**Done #1 advancement**: 0/3 → **0/3 stays** (no FULL credit; PARTIAL does not advance the strict-FULL counter).

**Done #2 status** (already MET at 3/3 post-B63): unchanged. This sub-DEC does NOT push Done #2; Driver-Seegmiller 1985 was already implicit in Done #2's "canonical literature comparison" coverage via NASA TMR-class references.

## 2. Canonical reference & convention

**Source**: Driver, D.M. & Seegmiller, H.L. (1985). *Features of a Reattaching Turbulent Shear Layer in Divergent Channel Flow.* NASA TM 86658 (also AIAA Journal Vol 23 No 2 pp 163-171, Feb 1985). Re-tabulated in NASA Turbulence Modeling Resource backstep_val data.

**Geometry**: 2D BFS, step height h = 12.7 mm, expansion ratio 1.125, downstream test section 20·h.

**Inflow** (canonical): U_ref = 44.2 m/s, Re_h = 37,500, fully-developed inlet BL with **δ/h ≈ 1.5**.

**This case's inflow** (per briefing reverse-condition sanction): uniform inlet at U_ref = 44.2 m/s, 20·h inlet section (doubled from briefing's 10·h to compensate). **Pre-step BL δ/h ≈ 0.4-0.5** (estimated from Schlichting 1/7-power law over L_dev = 0.254 m).

The inlet BL thickness mismatch is the **dominant systematic deviation source** driving all four FULL-gate failures. Documented honestly in CASE_SPEC §4 §8 §10 before run started.

## 3. Mesh & solver setup (recap)

- 3-block blockMesh, 116,000 hexahedra (28k upstream + 56k downstream upper + 32k recirculation)
- Bilinear wall-normal grading: δy_first ≈ 4.8 µm upper blocks / 4.1 µm Block 3
- checkMesh PASS clean, zero quality flags (max AR 669, max non-ortho 0, max skewness 8e-13)
- y+ achieved on bottomDownstream (validation surface): avg **0.158**, max 0.25 ✓ excellent
- y+ on stepWall: avg 1.44 (corner-singularity peak 6.06 unavoidable)
- simpleFoam kOmegaSST RAS, 5000 iter, NASA TMR URF (0.30/0.70/0.50/0.50)

## 4. Reattachment length

**Canonical**: x_R/h = 6.26 ± 0.10 (Driver-Seegmiller 1985, NASA TM 86658 Fig 7 p. 18)

**Actual**: x_R/h = **5.443** (linear-interp on τw_x sign change between faces 182-183 of bottomDownstream patch)

**Δ%** = 100 · (5.443 - 6.26) / 6.26 = **-13.05%**

Gate assessment:
- FULL [6.0, 6.5]: ✗ NOT MET
- Marginal [5.5, 7.0]: ✗ NOT MET (5.44 < 5.5)
- **PARTIAL on x_R/h**

Detail: 3 τw_x sign changes found (corner sub-bubble face 5, secondary counter-rotating vortex face 54, main reattachment face 183); persistence-filter (≥20 consecutive negative faces downstream) selected face 183 as the main reattachment. See RUN_LOG §"Reattachment detection".

Source row: `case_022_v64_val_full_5_bfs_dicts/BFS_results.csv` row 1; raw τw_x from `case_022/5000/wallShearStress` patch `bottomDownstream` faces 182-183.

## 5. Cp on downstream wall (5 stations)

**Canonical**: NASA TM 86658 Driver-Seegmiller 1985 Fig 8 (digitized + NASA TMR backstep_val tabulated values).

Cp definition: Cp = (p - p_ref) / (0.5 · ρ · U_ref²). Both p and p_ref are kinematic in OF incompressible (p / ρ).

**p_ref**: averaged over 69 cells in x ∈ [0.10, 0.20] at y = 0.05 m (mid-channel, upstream of step, away from step-front pressure rise zone). p_ref = **-145.48 m²/s²** (kinematic).

| Station | x/h | x_abs [m] | p_kin [m²/s²] | Cp actual | Cp_DS_canonical | Δ% |
|---|---|---|---|---|---|---|
| S1 | 1.0 | 0.2667 | -238.971 | -0.0957 | -0.140 | +31.6% |
| S2 | 4.0 | 0.3048 | -257.175 | -0.1143 | -0.110 | **-3.95% ✓** |
| S3 | 8.0 | 0.3556 | +21.443 | **+0.1709** | -0.022 | sign mismatch (+877% nominal) |
| S4 | 12.0 | 0.4080 (offset from 0.4064) | +41.720 | +0.1916 | +0.067 | +186.0% |
| S5 | 16.0 | 0.4572 | +15.730 | +0.1650 | +0.119 | +38.7% |

**Cp gate** (|Δ%| < 10% all 5): **1/5 met (S2)** → ✗ NOT MET → PARTIAL.

**Physical interpretation**: S2 (x/h=4) is deep in the recirculation zone where Cp is at the local minimum — magnitudes match well because both my CFD and DS produce the same low-pressure plateau there. S3-S5 show **premature pressure recovery** consistent with my shorter recirculation bubble (x_R/h=5.44 vs 6.26): pressure recovery starts earlier, so by x/h=8 my flow has already begun recovery (+0.171) while DS is still in the pre-reattachment low-pressure zone (-0.022). The Δ% explosion at S3 is a sign-crossing artifact and should be interpreted as "absolute Cp differs by 0.193 from canonical".

Source rows: `BFS_results.csv` rows 1-5; p values from `postProcessing/sampleDict/5000/s{1..5}_xh{1,4,8,12,16}_p_yPlus_U_wallShearStress.xy` column 2 (p).

## 6. Cf on downstream wall (5 stations)

**Canonical**: NASA TM 86658 Driver-Seegmiller 1985 Fig 9 (digitized + NASA TMR backstep_val).

Cf definition: Cf = signed · 2 · |τ_w_kin| / U_ref². DS sign convention: Cf > 0 for forward flow, Cf < 0 for reverse flow. OF wallShearStress sign relation: τw_x_OF < 0 ↔ forward flow → Cf_actual = -2 · τw_x_OF / U_ref².

| Station | x/h | x_abs [m] | τw_x_OF [m²/s²] | Cf actual | Cf_DS_canonical | Δ% |
|---|---|---|---|---|---|---|
| S1 | 1.0 | 0.2667 (face 45) | -0.0834 | +0.000085 | **-0.00110** | sign mismatch (+108% nominal) |
| S2 | 4.0 | 0.3048 (face 146) | +3.2204 | -0.003297 | -0.00193 | -70.8% (mag too large) |
| S3 | 8.0 | 0.3556 (face 237) | -2.0484 | +0.002097 | +0.00069 | +204% (over-recovery) |
| S4 | 12.0 | 0.4064 (face 304) | -1.8951 | +0.001940 | +0.00140 | +38.6% |
| S5 | 16.0 | 0.4572 (face 356) | -2.0056 | +0.002053 | +0.00185 | **+11.0% ✓ (within 20%)** |

**Cf gate** (|Δ%| < 20% all 5 per parts_manifest tolerance_policy): **1/5 met (S5)** → ✗ NOT MET → PARTIAL.

**Physical interpretation**:
- **S1 sign mismatch**: my x/h=1 is in the secondary counter-rotating vortex zone (τw_x < 0 means forward-flow direction shear there — see RUN_LOG sub-bubble interpretation). DS's thick-BL flow has no such secondary vortex and shows reverse-flow Cf < 0.
- **S2 magnitude excess**: x/h=4 is the recirculation core in both my CFD and DS. My recirculation is more energetic (stronger reverse flow near wall) → larger \|τw_x\| → over-magnitude Cf.
- **S3 over-recovery**: my x_R/h=5.44 means x/h=8 is well downstream of reattachment, recovering rapidly. DS at x/h=8 is just barely post-reattachment (DS x_R/h=6.26) so Cf still small. Same premature-recovery pattern as Cp.
- **S5 ✓**: by x/h=16 both flows have substantially recovered, and Cf has converged to its asymptotic recovery-boundary-layer value. The deviation collapses to 11%.

Source rows: `BFS_results.csv` rows 1-5; τw_x values from `case_022/5000/wallShearStress` patch `bottomDownstream` faces 45, 146, 237, 304, 356.

## 7. Convergence assessment

**Strict gate**: 6/6 residuals < 1e-5 at iter 5000. **Result**: **1/5 met (ω only)**.

| Field | Residual at iter 5000 | Strict 1e-5 met? |
|---|---|---|
| Ux | 2.02e-4 | ✗ (20× above) |
| Uy | 3.02e-3 | ✗ (302× above) |
| p | 1.49e-3 | ✗ (149× above) |
| omega | 1.05e-7 | ✓ |
| k | 3.14e-4 | ✗ (31× above) |

**Cross-case comparison** (case_021 attached flow vs case_022 separated flow):

| Field | case_021 (attached BL, FULL-3) | case_022 (separated BFS, FULL-5) | Ratio |
|---|---|---|---|
| Ux | 1.84e-5 | 2.02e-4 | 11× higher |
| Uy | 4.71e-5 | 3.02e-3 | 64× higher |
| p | 4.41e-5 | 1.49e-3 | 34× higher |
| omega | 5.31e-8 | 1.05e-7 | 2× higher |
| k | 2.74e-5 | 3.14e-4 | 11× higher |

**F-NEW (new finding, cross-case insight)**: **steady RANS residual floor is geometry-specific**. Attached-flow case (case_021) plateaus near 1e-5 strict threshold; separated-flow case (case_022) plateaus 1-2 orders of magnitude HIGHER due to inherent recirculation-zone unsteadiness that steady-RANS cannot fully damp. This refutes the case_021 retro's hypothesis that the plateau was solver-stack-specific (kOmegaSST + bounded upwind) — it's actually **flow-physics-specific** (separation vs attached).

**Implication for V64-A Done #1**: strict residualControl 1e-5 may be unreachable for separation/recirculation canonicals in steady RANS regardless of mesh/scheme refinement. Future BFS attempts may need to either:
1. Switch to unsteady solver (pimpleFoam URANS, ~10× cost), OR
2. Relax residual gate to 1e-3 for separated-flow canonicals, OR
3. Stick with attached-flow canonicals for residual-strict Done #1 progression.

## 8. F-NEW catalog (this sub-session)

| ID | Finding | Evidence | V-row promotion candidate |
|---|---|---|---|
| F-NEW-13 | BFS x_R/h sensitivity to inlet δ/h: thinner BL → shorter reattachment | x_R/h = 5.44 with δ/h ≈ 0.4 vs DS canonical 6.26 with δ/h ≈ 1.5; -13.05% offset | Yes — useful for future BC validation choices |
| F-NEW-14 | Thin-inlet-BL BFS three-zone vortex topology (corner sub-bubble + secondary CR-vortex + main recirculation) | τw_x sign profile faces 5, 54, 183 in CONVERGENCE/RUN_LOG | Yes — distinct from canonical thick-BL DS observation |
| F-NEW-15 | Steady RANS residual floor is geometry-specific (separation 100× higher than attached BL) | case_022 Uy 3.02e-3 vs case_021 Uy 4.71e-5; ratio 64× | Yes — affects V64-A Done #1 gate calibration |
| F-NEW-16 | OF blockMesh midPoint sample empty-coordSet when target coincides with cell-face boundary | s4 x=0.4064 ↔ Block 3 face 304 at x=0.4064 (exact); p_ref_station similar | Operational — useful for future sampleDict authoring |
| F-NEW-17 | OF wallShearStress sign convention: τw_x < 0 = forward flow direction shear | case_021 plate (forward) → τw_x < 0; case_022 recirc → τw_x > 0 | Confirms documentation in extract_bfs.py |

## 9. V-row attribution (anticipated firmness changes)

Reuse from prior V64-A sub-DECs:
- **V100** (incompressible canonical advisor stack baseline · LANDED B55): FIRMS — BFS is a different geometry class than flat plate (closed-flow attached vs open-flow separated), and the substrate stack worked end-to-end without solver/mesh defects. Net-new evidence for substrate flexibility.
- **V47** (NREL UAE BC convention documentation): partial reuse — same I=0.5% L_t=h/10 turbulence-inlet convention applied successfully.

Net-new V-row candidates (firms after retro review):
- **V-NEW** (potential): "BFS validation strategy" V-row capturing F-NEW-13..17 + inlet-BC strategy recommendations for future BFS attempts.

## 10. Honest assessment (per briefing reverse condition)

**This is a PARTIAL verdict and Done #1 stays at 0/3.** The case ran cleanly (no crash, no mesh defects, y+ on validation surface excellent), but the strict FULL gates were not achievable with the simplified uniform-inlet BC. The deviation pattern (premature reattachment, premature Cp recovery, secondary vortex topology, residual plateau ~100× higher) is **physically interpretable and consistent with the documented inlet-BL thickness deficit**, not a hidden solver/mesh defect.

**No cherry-picking**: all 5 Cp stations and 5 Cf stations reported with absolute and percentage Δ; sign mismatches called out explicitly; residuals reported per-field (not as a single aggregate).

**No gate-rewrite**: strict gate [6.0, 6.5] x_R/h, 10% Cp, 1e-5 residuals retained verbatim from briefing. Marginal range [5.5, 7.0] retained verbatim. PARTIAL classification follows strictly.

**Path to FULL (future sub-DEC, out of this scope)**: implement `fixedProfile` or `codedFixedValue` inlet BC reproducing canonical δ/h ≈ 1.5 BL profile. Mesh and solver stack would be reusable.

**Cross-validation with B65 lid-driven cavity** (disjoint scope): the originally-anticipated Done #1 advancement to 0→2/3 (if both BFS and cavity PASS) is not realizable on this BFS leg. Cavity result is independent and may still advance Done #1 to 0→1/3 if it strict-passes.

## 11. 4Q gate (final)

- **Q1 LLM-offline**: env -i HOME PATH .venv/bin/python re-runnable via:
  - `docker run --rm -v ~/Desktop/case_022_driver_seegmiller_bfs/case:/case opencfd/openfoam-default:2312 bash -c 'cd /case && simpleFoam'`
  - `python3 .planning/case_profiles/case_022_v64_val_full_5_bfs_dicts/extract_bfs.py ~/Desktop/case_022_driver_seegmiller_bfs/case`
- **Q2 artifacts**: parts_manifest + CASE_SPEC + RESUME + 16 dict/log files + extract_bfs.py + BFS_results CSV/MD + RUN_LOG + CONVERGENCE_TRACE + SIMPLEFOAM_LOG_TRIMMED + this validation report + sub-DEC (commit 5)
- **Q3 TrustGate**: every metric in §4-§7 cites the source CSV/postProcessing file row + line in canonical (NASA TM 86658 Fig 7/8/9 + NASA TMR backstep_val table)
- **Q4 advisor-only**: NO ui/backend/ touched this sub-session
