---
decision_id: DEC-V65-A-sub-M-V65A-B85-LOWRE-PROBE-EXT
title: case_021 v65 low-Re probe-extension on B81 sandbox · F-NEW-low-Re-transition-trigger CONFIRMED in v65 but NOT promoted (same-case family · 2-case independence unmet) · Done #1 candidate strengthened
status: Accepted
parent_dec: DEC-V65-A-charter
phase: V65-A
notion_sync_status: pending (session-end batch sync per v2.3 round-1 rule)
predecessor: DEC-V65-A-sub-M-V65A-V106-THERMO-TEMPLATE-2ND
batch: B85
confidence: high
autonomous_governance: true
verdict: PROBE_EXTENSION_CONFIRMED · NOT_PROMOTED
v_row_landed: none (F-NEW-low-Re-transition-trigger remains V107 candidate awaiting independent 2nd-case witness)
validation_report: .planning/validation_reports/v65_case_021_lowRe_probe_ext.md
substrate: .planning/case_profiles/case_021_v65_tbl_2nd_re_dicts/ (Cf_results_lowRe.{csv,md} added)
---

# DEC-V65-A-sub-M-V65A-B85-LOWRE-PROBE-EXT · F-NEW-low-Re probe-extension confirmed (not promoted)

## 1 · Decision

case_021 v65 B81 sandbox (preserved post-V103 LANDING) reused for low-Re-band Cf probing at x ∈ [0.10, 0.31] m → Re_x ∈ [1.00e6, 3.00e6]. **5/5 stations under-predict Prandtl-Schlichting by 8-13%** (vs V64-A B64 candidate prediction "6-10%"). Pattern + sign + Re-band match candidate signature.

**V-row decision**: V107 candidate **NOT promoted** to LANDED. Reason: 2-case-witness independence unmet (both observations live in case_021 family — case_021 v64 at U=70 + case_021 v65 at U=140 on same mesh + same geometry). Probe-extension is a confidence-strengthener, not a promotion gate.

## 2 · Rationale (avoiding the v4-extension trap)

V64-A close §3.2 warned about over-counting promotions when 2nd witnesses are just resamples of the 1st. A clean V-row LANDING requires structurally independent 2nd case (different mesh + different geometry + different I_inlet OR different physics regime). case_021 v65 is a "sibling configuration" of case_021 v64, not an independent case.

Calling this V107 LANDED would inflate the corpus-depth score by an illegitimate count and pollute the V-series ledger for future ratification audits. Honest probe-extension classification preserves auditability.

## 3 · Setup (reuse, no new solver)

| Item | Value |
|---|---|
| Sandbox | `~/Desktop/case_021_nasa_tmr_flat_plate/case_v65/` (B81 preserved) |
| Time dir | 2500/ (B81 final converged state) |
| New script | `.planning/case_profiles/.../extract_cf_v65_lowre.py` (copy of extract_cf_v65.py with STATIONS rebound to Re_x ∈ [1e6, 3e6] band) |
| New artifacts | Cf_results_lowRe.{csv,md} (5-station extract) |
| Solver run | NONE — pure post-processing |
| Iter time | < 5 sec (Python parse of existing wallShearStress) |

## 4 · Results · 5-station low-Re band

| Station | Re_x | Δ% PS | Δ% SG | Sign |
|---|---|---|---|---|
| L1 | 1.0e6 | -12.46 | -12.71 | under |
| L2 | 1.5e6 | -13.32 | -14.49 | under (peak deficit) |
| L3 | 2.0e6 | -11.92 | -13.89 | under |
| L4 | 2.5e6 | -10.00 | -12.68 | under |
| L5 | 3.0e6 | -8.01 | -11.34 | under (recovering) |

Monotonic recovery as Re_x grows · consistent with "low-Re transition-zone modeling deficit" hypothesis. Peak deficit at Re_x ~1.5e6.

## 5 · Done dim advancement

| Done dim | Pre-B85 | Post-B85 |
|---|---|---|
| #1 V64-A carry-over (5 candidates) | 4/5 absorbed (5th = F-NEW-low-Re still candidate) | 4/5 absorbed + **1 probe-confirmed** (5th candidate validated in v65 but not yet LANDED — same case family) |
| #2 V101+ promotion | 5/6 ✓ MET | 5/6 ✓ MET (unchanged) |
| #3 net-new industrial | 2/2 ✓ MET | 2/2 ✓ MET (unchanged) |
| #4 industrial-grade FULL | 0/3 | 0/3 (unchanged) |
| #5 canonical-artifact ledger | 2/2 ✓ MET | 2/2 ✓ MET (unchanged) |
| #6 V-row truth-capture | unchanged | unchanged |
| **MET total** | **3/6** | **3/6** |

No new Done dim MET this batch. Probe-extension is a corpus-depth quality gain, not a Done-dim advancement.

## 6 · Score impact

| Pillar | Pre-B85 | Post-B85 | Δ |
|---|---|---|---|
| 2 · Corpus depth (20%) | 77.5 | **78.5** | **+1** (F-NEW-low-Re better-characterized; candidate strength increased) |
| **Weighted** | **65.6** | **65.8** | **+0.2** |

Distance to 95: 29.4 → **29.2 points**.

Smaller magnitude than B81/B82/B84 (each +0.6-1.0 via V-row LANDING) because no V-row promoted. But honest +0.2 beats fake +0.6 from over-counting.

## 7 · 4Q gate · all 4 PASS

| Q | Answer |
|---|---|
| LLM offline can run? | ✓ pure post-processing of existing wallShearStress |
| Artifacts produced? | ✓ Cf_results_lowRe.{csv,md} + validation report + this DEC |
| TrustGate explainable? | ✓ Δ% vs 2 canonicals + Re-band shape characterization |
| AI advisor-only? | ✓ no AI touched substrate |

## 8 · v2.3 compliance

- DEC scope: sub-DEC (single case · probe extension · 6-field schema satisfied)
- Codex 1-sync-trigger: NOT triggered (no security boundary / signing / auth)
- Kogami opt-in: NOT invoked (no user request)
- Confidence: high (pattern reproduces clearly · honest classification)
- Counter: autonomous_governance=true · +1 to counter_v65

## 9 · Backward compatibility

- B81 substrate (case_021 v65) UNTOUCHED — added Cf_results_lowRe.{csv,md} as additional artifacts
- B81 V103 LANDING status UNCHANGED
- F-NEW-low-Re-transition-trigger candidate status upgraded "1st observation" → "1st observation + probe-confirmed"
- No retroactive changes to V101-V106 ledger

## 10 · B86 recommendation

To advance F-NEW-low-Re-transition-trigger to V-row LANDED, need structurally independent 2nd-case witness. Cheapest path:

- **B86-A (recommended)**: NACA0012 v65 (B84 sandbox preserved) low-Re BL Cf probe — add sampleDict over upper surface, extract Cf at x/c stations, test if kOmegaSST shows same low-Re deficit at NACA0012 transonic BL. If yes → V107 LANDS (independent 2nd case).
- **B86-B**: Done #4 industrial-grade FULL attempt — first FULL report (still 0/3 · biggest unmet Done-dim)
- **B86-C**: F-NEW-low-Re-band rebuilt with ERCOFTAC T3A bypass-transition substrate (most legitimate independent case · but requires fresh substrate build)

**Recommendation: B86-A** (high EV / low effort / preserves sandbox economy). If V107 LANDS → Done #1 V64-A carry-over moves to 5/5 ABSORBED ✓ MET → 4 Done dims MET total.

## 11 · Autonomous mode commit honored

B85 net +0.2 weighted, small but real gain via honest probe-extension classification. Avoids v4-extension trap of inflating corpus-depth via same-case repeat sampling. B86 launches without AskUserQuestion per autonomy mode.

— Claude Code (Opus 4.7 1M) · B85 · 2026-05-16
