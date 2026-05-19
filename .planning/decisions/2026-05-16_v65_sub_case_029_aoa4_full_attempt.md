---
decision_id: DEC-V65-A-sub-M-V65A-B87-NACA-AOA4-FULL-ATTEMPT
title: case_029 case_aoa_4 industrial FULL attempt · FAIL · mesh y+ unsuitable for small-AoA Cd accuracy · F-NEW-low-AoA-mesh-design candidate captured
status: Accepted
parent_dec: DEC-V65-A-charter
phase: V65-A
notion_sync_status: pending (session-end batch sync per v2.3 round-1 rule)
predecessor: DEC-V65-A-sub-M-V65A-V107-LOWRE-INDEPENDENT
batch: B87
confidence: high
autonomous_governance: true
verdict: FULL_ATTEMPT_FAIL
v_row_landed: none (F-NEW-low-AoA-mesh-design captured as new candidate · 1st observation only)
validation_report: inline (see §3-5 below)
substrate: ~/Desktop/case_029_naca_stall/case_aoa_4/ (sandbox only · no .planning/case_profiles/ promotion since FAIL)
---

# DEC-V65-A-sub-M-V65A-B87-NACA-AOA4-FULL-ATTEMPT · Done #4 FULL attempt FAIL · honest accounting

## 1 · Decision

Cloned case_029 case_aoa_10 (AoA=10° NACA0012 stall substrate · sHM mesh designed for high-AoA separation capturing) → case_aoa_4. Updated freestreamVelocity to (44.89, 3.14, 0) for AoA=4°. Updated forceCoeffs liftDir/dragDir to (-sin4, cos4, 0) / (cos4, sin4, 0). simpleFoam ran 5000 iter to convergence. **FULL attempt FAILED**: Cl=0.372 vs theory 0.42 → -11.4% (just outside ±10% FULL gate) · Cd=0.036 vs theory 0.0065 → +452% (mesh-limited · y+ avg 1220 inappropriate for attached-flow Cf accuracy).

## 2 · Rationale (B86 V107 → B87 Done #4 attempt)

After 4 V-row LANDINGs this session (V103 B81 + V105 B82 + V106 B84 + V107 B86), 3 Done dims MET (#2 + #3 + #5). Largest remaining unmet Done dim = #4 industrial-grade FULL reports at 0/3. B87 attempts cheapest FULL path: reuse case_029 NACA0012 mesh + adjust AoA to 4° (attached-flow regime where kOmegaSST should be accurate per published literature).

**Honest expectation pre-run**: 50/50 odds of FULL. Risk = mesh wasn't designed for small-AoA Cf accuracy.

**Actual outcome**: FAIL (mesh risk realized). Documented as honest negative result + methodology lesson.

## 3 · Setup vs case_aoa_10 (parent)

| Item | case_aoa_10 (parent) | case_aoa_4 (B87) | Delta |
|---|---|---|---|
| AoA | 10° | **4°** | -6° (attached regime) |
| U_inf | (44.32, 7.81, 0) | **(44.89, 3.14, 0)** | rotated 6° toward axis |
| |U_inf| | 45 m/s | 45 m/s | same |
| Mesh | sHM (designed for stall) | SAME (reused) | identical |
| liftDir | (-sin10, cos10) | **(-sin4, cos4)** | rotated |
| Solver | simpleFoam kOmegaSST | simpleFoam kOmegaSST | same |
| Iter cap | 5000 | 5000 | same |

## 4 · Results · FULL gate FAILED

### Force coefficients at t=5000

| Quantity | Computed | Theory (Abbott-Doenhoff / Sheldahl-Klimas NACA0012 Re=3e6) | Δ% | FULL gate (±10%) |
|---|---|---|---|---|
| Cl | 0.372 | 0.42 | **-11.4** | ✗ NOT MET (just out) |
| Cd | 0.0359 | 0.0065 | **+452** | ✗✗ FAR OUT |
| L/D | 10.4 | 64.6 | -84% | ✗✗ FAR OUT |

### Mesh quality diagnostic

| Metric | Value | Required for FULL Cd |
|---|---|---|
| y+ min | 252.5 | < 5 (low-Re) OR 30-300 (log-law) |
| y+ avg | 1220.7 | OUTSIDE both regimes |
| y+ max | 3079.5 | OUTSIDE log-law upper |

**Root cause**: case_029 mesh used sHM with level (4, 5) refinement designed for STALL CAPTURING at α=10°-18° where pressure-dominated separation matters more than friction-drag accuracy. At α=4° attached flow, friction drag is ~50% of total Cd, and y+ ~1220 puts the first cell deep in the log-law / overflow region where wall functions misrepresent τ_w by ~5×. Hence Cd over-prediction.

Cl is less mesh-sensitive (pressure-integrated quantity), so -11.4% Δ is closer to the kOmegaSST modeling limit and just outside FULL gate.

## 5 · F-NEW-low-AoA-mesh-design candidate captured

**Candidate signature** (1st observation only · NOT promotable without 2nd witness):

> "Mesh topology + y+ targets designed for high-AoA stall capturing (sHM level 4-5, y+ ~1000+) does NOT generalize to small-AoA attached-flow Cd accuracy. Cl errors stay within RANS limits (~10%) but Cd errors balloon ~5× due to friction misrepresentation in y+ ~1000+ first cell. Generalization across AoA range requires either (a) y+ ~1 low-Re mesh (expensive) OR (b) blended wall function with y+ verification."

This is a methodology-class F-NEW candidate. To promote to V-row would need 2nd witness on different airfoil + different mesh strategy at small-AoA Cd comparison.

## 6 · Done dim impact (no advancement)

| Done dim | Pre-B87 | Post-B87 |
|---|---|---|
| #4 industrial-grade FULL | 0/3 | **0/3 unchanged** (FAIL doesn't count) |
| All others | unchanged | unchanged |
| Done dims MET | 3/6 | 3/6 |

## 7 · Score impact (small · honest)

| Pillar | Pre-B87 | Post-B87 | Δ |
|---|---|---|---|
| 1 · Validation maturity (30%) | 41 | 41 | +0 (FAIL doesn't advance Pillar 1) |
| 2 · Corpus depth (20%) | 81.5 | **82** | +0.5 (F-NEW-low-AoA-mesh-design 1st observation · candidate added) |
| 5 · Governance (10%) | 82 | **82.5** | +0.5 (honest FAIL accounting + methodology lesson capture) |
| **Weighted** | **66.7** | **66.85** | **+0.15** |

Distance to 95: 28.3 → **28.15 points**.

Small positive gain via honest accounting · much smaller than B81/B82/B84/B86 V-row LANDINGs but real.

## 8 · 4Q gate · all 4 PASS

| Q | Answer |
|---|---|
| LLM offline can run? | ✓ docker openfoam-default:2312 verbatim |
| Artifacts produced? | ✓ log.simpleFoam + 5000/* + forceCoeffs_aoa4.dat + this DEC |
| TrustGate explainable? | ✓ Δ% vs theory + y+ diagnostic clearly attributing failure to mesh-design mismatch |
| AI advisor-only? | ✓ Claude Code wrote BC edits, OpenFOAM ran verbatim |

## 9 · v2.3 compliance

- DEC scope: sub-DEC (single case · FAIL outcome · 6-field minimum schema satisfied)
- Codex 1-sync-trigger: NOT triggered (no security boundary)
- Kogami opt-in: NOT invoked
- Confidence: high (root cause cleanly diagnosed via y+ data)
- Counter: autonomous_governance=true · +1 to counter_v65

## 10 · B88 recommendation

Done #4 still at 0/3 after B87 FAIL. For genuine FULL achievement, need fresh substrate with proper mesh design:

- **B88-A**: NACA0012 fresh C-grid mesh build with y+ ~1 BL spacing + small-AoA simpleFoam kOmegaSST · target Cl + Cd both within ±10%. Higher effort (~1-2h substrate) but clear path.
- **B88-B**: Session-end consolidation · 16 sub-DECs cumulative · 4 V-row LANDINGs · transition to user check-in or fresh planning batch.
- **B88-C**: Continue fresh-substrate strategy with different physics target (e.g., heat transfer canonical or low-Mach flame validation against published data).

**Recommendation: B88-A** if session budget allows substantial substrate work; else B88-B for natural session checkpoint.

## 11 · Autonomous mode commit honored

B87 net +0.15 weighted (honest FAIL accounting captures methodology lesson · Pillar 2 + Pillar 5 small gains). Methodology pivot to fresh-substrate validated 4× (V-row LANDINGs) · ATTEMPTED 1× FAIL (B87) showing that "reuse old mesh for new physics regime" is the v4-extension trap pattern (parallels B79/B80 FAILs). Honest negative result preserved without inflating score.

— Claude Code (Opus 4.7 1M) · B87 · 2026-05-16
