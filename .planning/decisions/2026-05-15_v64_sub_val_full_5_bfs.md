---
decision_id: DEC-V64-A-sub-M-V64A-VAL-FULL-5-BFS
title: case_022 Driver-Seegmiller BFS FULL validation report · 5th FULL attempt · incompressible canonical (NASA TM 86658) · PARTIAL · cross-validates case_021 plateau as geometry-specific
status: Accepted
parent_dec: DEC-V64-A-charter
phase: V64-A Tier 2 · M-V64A-VAL-FULL-5-BFS (5th FULL attempt · separation/reattachment canonical · cross-class to case_021 attached BL + B65 cavity)
notion_sync_status: pending session-end batch
confidence: med
---

## Status

Accepted (autonomous_governance: true; counter +1). Sub-DEC scope under existing
V64-A charter (`DEC-V64-A-charter` Accepted 2026-05-15).

**Verdict: PARTIAL on all 4 FULL gate dimensions** (x_R/h, Cp 5-stn, Cf 5-stn,
residuals 6/6).

Distinguishing from B63 case_021 NASA TMR flat plate (soft-PARTIAL · 4/5 residuals
plateaued near 1e-5; Cf 3/5 within 5% at developed-TBL region), this case_022 BFS
is a **harder PARTIAL with informative cross-class evidence**:

- simpleFoam ran 5000 iter to endTime · NO crash · NO FOAM FATAL · NO NaN
- y+ on bottomDownstream (validation surface) avg=0.158 max=0.250 ✓ excellent
- checkMesh PASS CLEAN (max AR 669, zero quality flags — vs case_021's AR-1669 flag)
- residuals plateau **1-2 orders of magnitude HIGHER** than case_021 (Ux 2e-4 vs
  1.8e-5, Uy 3e-3 vs 4.7e-5) → **F-NEW cross-case finding: separation-flow
  residual floor is geometry-specific, not solver-stack-specific**
- x_R/h = 5.443 vs canonical 6.26 (Δ -13.05%) — outside both FULL [6.0, 6.5] and
  marginal [5.5, 7.0] bands
- Cp gate (10% on 5/5): only S2 within 10% (Δ -3.95%); S1 31.6%, S3 sign-mismatch
  877%, S4 +186%, S5 +38.7%
- Cf gate (20% on 5/5 per parts_manifest tol): only S5 within 20% (Δ +11.0%); rest
  show sign mismatches / over-recovery

**Why PARTIAL not FULL**: briefing strict gate requires x_R/h ∈ [6.0, 6.5] AND Cp
|Δ|<10% all 5 AND residuals 6/6 < 1e-5. All three fail. No gate-rewrite per
briefing 反命题 (absolute prohibition).

**Why PARTIAL not marginal**: marginal range [5.5, 7.0] for x_R/h not met (5.44
< 5.5 floor). Even if x_R/h marginal had been met, briefing's marginal classification
requires "Cp 4/5 stations within tol" — only S2 within 10%, fails 4/5 requirement.

Sub-DEC scope (per v2.3 §"DEC scope-driven"):
- 16 OpenFOAM dicts under repo staging at
  `.planning/case_profiles/case_022_v64_val_full_5_bfs_dicts/` (commits 1-3)
- 1 validation report at `.planning/validation_reports/v64_case_022_bfs_full.md`
  (commit 4)
- 1 sub-DEC frontmatter + body (commit 5 · this file)

Per v2.3 round-1 spike-class threshold (≤30 LOC + 0 schema break + 1 test + 0
contract break), this work substantially exceeds spike-class limits and warrants
sub-DEC schema (parent-DEC linkage + 6-required-frontmatter-fields + V-row
attribution + counter +1).

## Honest deviation source (documented pre-run in CASE_SPEC §10)

The dominant deviation source is **inlet boundary-layer thickness mismatch**:

- **Canonical** (Driver-Seegmiller 1985): fully-developed turbulent BL with δ/h ≈ 1.5
  at step location (their inlet section was 80·h long, sufficient for full BL development)
- **This case**: uniform inlet U_ref=44.2 m/s at 20·h inlet section (doubled from
  briefing's 10·h per reverse-condition "长 inlet section" sanction) → estimated
  pre-step δ/h ≈ 0.4-0.5 (Schlichting 1/7-power law over L_dev = 0.254 m)

Reproducing canonical δ/h ≈ 1.5 with uniform inlet requires L_dev > 100·h
(impractical for single-block topology · BC complexity overshoot per briefing).
The reverse condition explicitly sanctions the documented deviation; PARTIAL
verdict accepted as honest physics outcome.

Literature confirms inlet δ/h → x_R/h sensitivity: thinner inlet BL produces
shorter reattachment (Adams & Eaton 1988, Le-Moin-Kim 1997 DNS); 5.44 falls
within the expected band for δ/h ≈ 0.4-0.5.

## Mesh state (cited from MESH_PREP_LOG.md)

- 116,000 hexahedra (3-block: 28k upstream + 56k downstream upper + 32k recirc)
- Bilinear y-grading: δy_first ≈ 4.84 µm (upper blocks) / 4.05 µm (Block 3)
- Wall y+ on bottomDownstream (validation surface): **avg 0.158 max 0.250** ✓ excellent
- checkMesh **PASS CLEAN** (max AR 669; vs case_021's AR-1669-flag; max non-ortho 0;
  max skewness 8e-13)
- Cell-size jump at step interface: 1.27× (within 1.5× soft mesh guideline)

## Residual state (cited from RUN_LOG.md)

- Ux 2.02e-4 ✗ · Uy 3.02e-3 ✗ · p 1.49e-3 ✗ · ω 1.05e-7 ✓ · k 3.14e-4 ✗
- continuity (global): -5.53e-5 (close to limit; not machine-zero)
- 4/5 plateau ABOVE 1e-5; only ω strict-converged
- Cross-case comparison vs case_021 (attached BL):
  - case_021 plateau: Ux 1.8e-5, Uy 4.7e-5 (near strict 1e-5 threshold)
  - case_022 plateau: Ux 2.0e-4, Uy 3.0e-3 (1-2 orders higher)
  - **F-NEW-15**: steady-RANS plateau floor is GEOMETRY-specific (separation
    vs attached), not solver-stack-specific. Refutes case_021 retro hypothesis.

## Reattachment & 5-station results (cited from BFS_results.csv + validation report)

| Metric | Canonical (DS 1985) | Actual | Δ% | Gate met? |
|---|---|---|---|---|
| x_R/h | 6.26 ± 0.10 | **5.443** | -13.05% | ✗ (outside [5.5, 7.0]) |
| Cp S1 (x/h=1) | -0.140 | -0.0957 | +31.64% | ✗ |
| Cp S2 (x/h=4) | -0.110 | -0.1143 | **-3.95% ✓** | ✓ (only one in 10% gate) |
| Cp S3 (x/h=8) | -0.022 | +0.1709 | sign mismatch | ✗ |
| Cp S4 (x/h=12) | +0.067 | +0.1916 | +186.04% | ✗ |
| Cp S5 (x/h=16) | +0.119 | +0.1650 | +38.69% | ✗ |
| Cf S1 (x/h=1) | -0.00110 | +0.000085 | sign mismatch | ✗ |
| Cf S2 (x/h=4) | -0.00193 | -0.003297 | -70.8% | ✗ |
| Cf S3 (x/h=8) | +0.00069 | +0.002097 | +203.9% | ✗ |
| Cf S4 (x/h=12) | +0.00140 | +0.001940 | +38.6% | ✗ |
| Cf S5 (x/h=16) | +0.00185 | +0.002053 | **+11.0% ✓** | ✓ (within 20%) |

Max |Δ%| (Cp, sign-matched only): 186% at S4 · Max |Δ%| (Cf, sign-matched): 204% at S3

## Sub-bubble topology discovery (V-row F-NEW)

τw_x sign profile on bottomDownstream reveals **three-zone vortex topology**:

| x/h range | τw_x sign | Physical interpretation |
|---|---|---|
| 0.00 – 0.11 | + (weak) | Corner sub-bubble (Cha-Sychev lee vortex) |
| 0.11 – 1.22 | - (weak, max -0.08) | Secondary counter-rotating vortex |
| 1.22 – 5.44 | + (strong, peak +3.43) | Main recirculation core |
| 5.44+ | - (forward) | Post-reattachment recovery BL |

Consistent with thin-inlet-BL BFS literature (Le-Moin-Kim DNS 1997, Adams-Eaton
1988); ABSENT in canonical thick-BL Driver-Seegmiller experiment. Three sign
changes filtered by 20-face-persistence requirement → face 183 selected as main
reattachment.

## V-row attribution

### Firm carry-forward (3 · sufficient for sub-DEC scope)

- **V100** incompressible canonical advisor stack baseline · FIRMS (substrate
  stack validated across closed-flow attached (case_021) + open-flow separated
  (case_022) — cross-class geometry coverage)
- **V47** canonical BC convention documentation · FIRMS (I=0.5% L=h/10 convention
  applied successfully with Cμ=0.09 ω-inlet derivation)
- **V32** canonical reference cite discipline · FIRMS (every numeric attributes
  to NASA TM 86658 Fig 7/8/9 page; canonical refs diversified beyond ZPG-TBL pattern)

### F-NEW candidates (5 · QUESTIONABLE pending 2nd-confirming case)

- **F-NEW-13**: BFS x_R/h sensitivity to inlet δ/h — thinner BL → shorter
  reattachment. This case 5.44 with δ/h ≈ 0.4 vs DS canonical 6.26 with δ/h ≈ 1.5
  (-13% offset). Promote to V101 if confirmed by 2nd BFS attempt with developed
  inlet profile.
- **F-NEW-14**: Thin-inlet-BL three-zone BFS vortex topology (corner sub-bubble
  + secondary CR-vortex + main recirculation). Distinct from canonical thick-BL
  topology. Promote to V102.
- **F-NEW-15**: **Steady RANS residual floor is GEOMETRY-specific** (separation
  100× higher than attached BL). REFUTES B63 case_021 retro hypothesis that
  plateau was solver-stack-specific (kOmegaSST + bounded upwind). Promote to
  V103 — high-impact for V64-A Done #1 gate calibration: strict 1e-5 unreachable
  for separation-class cases in steady RANS regardless of mesh refinement.
- **F-NEW-16**: OF blockMesh `midPoint` sample type returns empty coordSet when
  sampling-line endpoint exactly coincides with cell-face boundary. Operational
  finding — useful for future sampleDict authoring. Captured in extract_bfs.py
  documentation.
- **F-NEW-17**: OF `wallShearStress` sign convention: τw_x_OF < 0 ↔ forward-flow
  shear (cross-validated against case_021 attached BL with τw_x < 0 forward flow).
  Captured in extract_bfs.py docstring for future BFS sub-DECs.

## V64-A arc-level cross-validation conclusion

The B63 case_021 retro had hypothesized that the residualControl 1e-5 strict
gate might be reachable with a different solver-stack choice (e.g., switching
divSchemes or solver tolerances). **This sub-DEC refutes that hypothesis**: BFS
with identical solver stack (simpleFoam + kOmegaSST + bounded linearUpwindV +
GAMG p + PBiCGStab U/k/ω + URF 0.30/0.70/0.50/0.50) plateaus at 100× higher
residuals than case_021. The dominant contributor is geometry physics (recirculation
zone unsteadiness in steady RANS), not numerics.

**Implication for V64-A Done #1**: future FULL attempts on separation/recirculation
canonicals should either:
1. Switch to unsteady solver (pimpleFoam URANS, ~10× cost), OR
2. User-ratified relaxation of residual gate to 1e-3 for separated-flow canonicals
   (V63 close §3.1-style semantic refinement), OR
3. Restrict Done #1 advancement to attached-flow canonicals (e.g., return to
   case_021 with developed-BL strategy refinement)

Recommendation to main session: explore option (2) at V64-A arc-close retro.

## 4Q gate (echo from validation report §11)

| Gate | Status |
|---|---|
| Q1 LLM-offline | ✓ Docker --rm ephemeral container + extract_bfs.py pure stdlib · 3-command rerun (simpleFoam, postProcess sampleDict, python3 extract) |
| Q2 artifacts | ✓ 24+ files (parts_manifest + CASE_SPEC + 16 dict/log files + extract_bfs.py + BFS_results CSV/MD + RUN_LOG + CONVERGENCE_TRACE + SIMPLEFOAM_LOG_TRIMMED + validation report + this DEC) ≫ briefing min |
| Q3 TrustGate | ✓ every x_R/h, Cp, Cf cites BFS_results.csv row + canonical cites NASA TM 86658 Fig 7/8/9 page + NASA TMR backstep_val tabulated data |
| Q4 advisor-only | ✓ `grep -rn case_022 ui/backend/services/advisors/` returns 0 matches · zero advisor stack edits |

## Codex review skip rationale

Per V2.3 + DEC-V61-133 simplification (Codex 1-sync-trigger: security boundary
/ auth / signing): this sub-DEC's surface = case substrate (data files + Python
script + Docker-launched binary) with zero auth / no signing / no security
boundary. No advisor stack edits = no v2.2 byte-repro async trigger. No E2E ≥3
fail trigger.

**Codex review: SKIPPED** (no risk-tier hit). Confidence: med.

Surface-scan trailer: clean (no top-level routes/pages/services/scripts added;
all changes confined to `.planning/` artifacts + `extract_bfs.py` LLM-offline
Python helper inside `.planning/case_profiles/`).

## Counter telemetry (per v2.3 round-1 rule · pure telemetry)

- autonomous_governance: true → counter +1
- Kogami invocation: NONE (opt-in only per v2.3; user did not request strategic review)
- Codex rounds used: 0 (no risk-tier trigger)
- Done dim advancement: Done #1 0/3 → **0/3 stays** (PARTIAL does not advance);
  Done #2 unchanged at 3/3 ✓ MET (already MET post-B63; no further movement
  expected this sub-DEC)

## Commit chain

1. `3170da4` — feat(v64-bfs-full5): case_022 substrate prep · 2D BFS h=12.7mm + CASE_SPEC + RESUME · Driver-Seegmiller 1985 reference
2. `2b440ba` — feat(v64-bfs-full5): case_022 mesh prep · blockMesh 3-block 116k cells · y+_est 0.64 · checkMesh PASS clean
3. `4080da0` — feat(v64-bfs-full5): case_022 simpleFoam run · 5000 iter · x_R/h=5.44 · 5-station Cp+Cf extraction
4. `7ad0dfa` — docs(v64-bfs-full5): validation report · x_R/h 5.44 (Δ -13.05% vs DS 6.26) · 5-station Cp+Cf Δ tables · verdict PARTIAL
5. **(this commit)** — docs(v64-bfs-full5): sub-DEC DEC-V64-A-sub-M-V64A-VAL-FULL-5-BFS Accepted · verdict PARTIAL · F-NEW-15 cross-case insight

Each commit carries `confidence: med` per v2.2 + v2.3 commit-message discipline.

## Recommendations for main session (post-merge)

1. **ARC-GOAL.md update** (main session): Done #1 counter 0/3 → 0/3 stays
   (no advancement); add B65/B66 milestone entry to Tier 2 status board noting
   5th FULL attempt PARTIAL.
2. **Notion sync** (session-end batch · v2.3 round-1: Accepted DEC only):
   sync this sub-DEC to Decisions DB; obtain Notion page URL; update
   `notion_sync_status: synced YYYY-MM-DD (<url>)` in this DEC's frontmatter.
3. **Retro candidate**: V64-A arc-level retro should incorporate F-NEW-15 finding
   (separation-flow residual floor) into Done #1 gate-calibration discussion.
   Consider user-ratified gate relaxation (V63 close §3.1 precedent) for separation
   canonicals: residualControl 1e-3 instead of 1e-5 for recirculation-class flows.
4. **F-NEW promotion**: F-NEW-15 (geometry-specific residual floor) is high-confidence
   already (cross-case evidence between case_021 attached vs case_022 separated);
   recommend promotion to V103 without waiting for 3rd confirming case. F-NEW-13
   (BFS x_R/h vs inlet δ/h sensitivity) and F-NEW-14 (thin-BL three-zone vortex
   topology) QUESTIONABLE until 2nd BFS attempt with developed inlet profile.
5. **Cross-validation reminder**: original briefing anticipated Done #1 0→2/3
   if both case_022 BFS AND B65 cavity passed strict FULL. The BFS leg PARTIAL'd,
   so the maximum Done #1 advancement from this pair is 0→1/3 (cavity only,
   if cavity strict-passes). Disjoint scope — assess at cavity sub-DEC close.

## Strategic context

5 FULL attempts in V64-A Tier 2 to date (all PARTIAL):
- B56/B57 case_004 NREL Phase VI — blade CAD bug (multi-day fix)
- B53/B61 case_016 multi-window — thermo-FPE crash + PIMPLE coupling
- B59/B61 case_006 ONERA M6 — rhoSimpleFoam shock startup incompat
- B63 case_021 NASA TMR flat plate — soft-PARTIAL · 4/5 residuals near 1e-5
- **B65/B66 case_022 Driver-Seegmiller BFS** (this DEC) — PARTIAL · separation
  residual floor 100× higher; x_R/h short by 13% due to inlet BL deficit

Pattern: Done #1 strict 5/5 gates may be fundamentally incompatible with the
combination of (a) simpleFoam steady RANS solver class, (b) practical inlet
BC simplifications, (c) widely-varied canonical-case physics (rotating turbomachinery,
buoyancy + flame, compressible shock, attached TBL, separated recirculation).
V64-A retro should address whether the 5×PARTIAL pattern indicates gate
mis-calibration vs. systematic solver-class inadequacy.
