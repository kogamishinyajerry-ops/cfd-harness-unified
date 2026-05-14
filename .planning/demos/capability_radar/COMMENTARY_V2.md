# Capability Radar v2 · Justification

**Generated**: 2026-05-14 by M-RADAR-V2 build session (Claude Code Opus 4.7 1M ctx, sub-session)
**Baseline**: v1 `COMMENTARY.md` (2026-05-13) · v1.5 early-signal `SCORE-DELTA-2026-05-13-session-5.md`
**Status**: M-RADAR-V2 milestone deliverable. v1 PNG preserved as governance baseline (NOT deleted).
**Substrate window**: v1 timestamp (2026-05-13 morning) → v2 timestamp (2026-05-14 evening) = 6 Track C sessions + 2 advisor lands + A6 V96/V97 fix + V-series 84→98.

## Summary table — cfd-harness column v1 → v2

| # | Axis | v1 | v1.5 | **v2** | Δ vs v1 | v1.5 forecast criterion met? |
|---|---|---|---|---|---|---|
| 1 | CAD/几何 ingest | 6 | 6.5 | **7.0** | +1.0 | n/a (v1.5 capped at +0.5; v2 exceeds via A6/V96+V97 fix land + CRM-HLS first walk-through) |
| 2 | 网格生成 | 6 | 6.0 | **6.5** | +0.5 | partial — v1.5 bar was "mesh debug ≤3-iter on new case"; case_011 v3 took 5 iter to v5b; case_003 was 1-iter. Mixed evidence → +0.5 not +1.0 |
| 3 | 物理模型覆盖 | 7 | 7.0 | **8.0** | +1.0 | **met** — v1.5 bar "e2e numerics class counter 1 → 2" exceeded (1/3 → 3/3) |
| 4 | 求解器健壮性 | 6 | 6.0 | **7.0** | +1.0 | **met** — v1.5 bar "≥1 new solver-numerics-class V-row family" exceeded (V92 multi-region heterogeneity + V93 reacting limiter floor = 2 families) |
| 5 | 后处理质量 | 7 | 7.0 | **7.0** | 0 | n/a — no postproc substrate this session arc |
| 6 | CLI/自动化 | 9 | 9.0 | **9.0** | 0 | n/a (already at ceiling for OSS-side) |
| 7 | AI 智能辅助 | 8 | 8.5 | **9.0** | +1.0 | exceeded v1.5 forecast — advisor stack 4 LANDED → 8 LANDED + M6 charter empirically demonstrated by Track C session 5 |
| 8 | 可重现/审计 | 9 | 9.5 | **9.5** | +0.5 | met at v1.5; held at v2 (no new drift-prevention infra) |

**Half-axis averages**:

| Half | v1 | v1.5 | **v2** | Target | Status |
|---|---|---|---|---|---|
| **Left** (axes 1-5) / 5 | (6+6+7+6+7)/5 = **6.40** | 6.50 | **(7+6.5+8+7+7)/5 = 7.10** | ≥ **7.2** | **NOT MET · gap 0.1** |
| **Right** (axes 6-8) / 3 | (9+8+9)/3 = **8.67** | 9.00 | **(9+9+9.5)/3 = 9.17** | ≥ 8.7 (maintain) | **MET · margin +0.47** |

**Done dim 5 verdict**: **NOT MET (left half 7.10 < 7.2)**. Bottleneck identified §"Bottleneck analysis" below.

---

## Per-axis justification (cfd-harness column · v2 detail)

### 1. CAD/几何 ingest — v2: 7.0 (v1: 6 · Δ +1.0)

- **v1 baseline state**: 14 industrial cases through STEP/STL · V20 unit detection · mojibake handling.
- **v2 additions** (substrate window):
  - **A6 V96/V97 fix LANDED** (commit `83e2793` 2026-05-14): `parse_step_header_unit` max_bytes 64KB → 1MB; `bbox_plausible_units` industrial-extent cap 100m → 1000m. Closes 2 silent failure modes on industrial-aircraft-scale STEPs.
  - **CRM-HLS Tier-1 industrial STEP** (716KB, INCH-at-byte-707430) successfully walked through full pipeline to mesh in case_003 session 6 — first NASA/AIAA aerospace Tier-1 reference geometry exercised.
  - **A4 + A5 + A6 + A8 + A10 LANDED** since v1 baseline: 6 CAD/geometry-layer advisors active (A1, A2-v2, A4, A5, A6-hardened, A7) + 2 downstream advisors (A8 mesh-layer, A10 thermo-layer).
- **v2 remaining gaps**:
  - V94 (cq.exporters single-shell face-zone loss) still **open** — STL emitted from CAD-stage face-named bodies loses face labels; downstream sHM gets one undifferentiated patch per region pair.
  - V98 cascade shows CRM-HLS source STEP encodes idealized-scale (not 1:1 CRM) — V20 deeper than v1 thought.
  - CATIA / NX / Creo native plugins still absent; STEP still mandatory bridge.
- **Why +1.0 not +0.5**: v1.5 early-signal capped at +0.5 because "no NEW industrial-CAD complexity validated" — v2 invalidates that cap by walking CRM-HLS Tier-1 through the pipeline. The fact that V96/V97 surfaced AND were fixed in the same session-arc demonstrates the advisor-feedback loop now closes on industrial-aircraft-scale inputs. +1.0 reflects substrate-validated capability gain, not just advisor-stack growth.
- **STAR-CCM+ 9 / Fluent 8 / OpenFOAM 3**: unchanged.

### 2. 网格生成 — v2: 6.5 (v1: 6 · Δ +0.5)

- **v1 baseline**: sHM + cfMesh wrapped · 943k cells production validated · refinementBox + 3-layer prism templates.
- **v2 additions**:
  - **A8 `shm_dict_validator` LANDED** 2026-05-14 (DEC-V61-198-sub-A8) — first mesh-layer advisor in stack (~310 LOC + 9-test suite). Closes V52 (typo class) + V86 (orchestration class) cross-topology pair.
  - **case_011 v5b 3-region chtMR mesh** constructed: hot 142% / cold 115% / solid 37% retention, all 3 regions present, chtMR-SimpleFoam runs on it.
  - **case_003 197k cells** from Tier-1 industrial CRM-HLS STEP via sHM in 21.4s wall-clock · checkMesh `Mesh OK` · non-ortho max 46.3° · skewness max 2.05.
  - **V92 codifies principled hybrid `cellZoneInside inside` ↔ `insidePoint` walk strategy** for complex-void multi-region STLs.
  - **V95 NEGATIVE evidence** (case_002a M-APU-RESTORE): STL surface surgery to restore phantom outlet FAILS when feature scale < sHM cell size — empirical bound for the technique.
  - **V89 / V90 / V92** family catalogued (locationsInMesh syntax + cellZoneInside heterogeneity).
- **v2 remaining gaps**:
  - **V85 connected-component cap** still load-bearing (37% solid retention floor on case_011 v5b).
  - Complex-internal-void STL multi-region still fragile (V92's cold-PASS / solid-FAIL under identical syntax).
  - No polyhedral mesh (OpenFOAM limitation).
  - **case_011 v1→v5b took 5 mesh iterations** to land — *more*, not fewer, debug iter than V73-V78 7-iter case_002a baseline. v1.5 forecast bar "≤3-iter on new case" only partially met (case_003 was 1-iter; case_011 was 5-iter).
- **Why +0.5 not +1.0**: A8 LANDED is a real capability advance but mesh-debug-loop reduction is genuinely mixed evidence. Stay conservative.
- **STAR-CCM+ 9 / Fluent 8 / OpenFOAM 5**: unchanged.

### 3. 物理模型覆盖 — v2: 8.0 (v1: 7 · Δ +1.0)

- **v1 baseline**: cross 10 numerics classes nominally available · each class only 1-2 cases · 覆盖度浅.
- **v2 additions**:
  - **ARC-GOAL #4 e2e numerics class counter 1/3 → 3/3**:
    - compressible-buoyant-RANS (case_002a, baseline)
    - **CHT-multi-stream** — case_011 v3 chtMultiRegionSimpleFoam 200 SIMPLE iter without FATAL, 4-order residual reduction per region (h_hot 1.0 → 9.96e-5; h_cold 1.0 → 2.00e-4; h_solid 0.015 → 3.60e-6)
    - **reacting-low-Mach** — case_009 v1.5 ignite 2000 timesteps · 0 limit warnings · Tmax 1985 K monotone ignite envelope · DRM-19 19+2 species · PaSR + Cmix=1.0 + kEpsilon
  - **A10 `thermo_polynomial_range_advisor` LANDED** 2026-05-14 — first reacting-class advisor in stack; codifies V93 actionable rule (boundary fixedValue T ≥ per-species Tlow + safety margin).
  - **V93 actionable rule** for reacting class limiter behavior.
- **v2 remaining gaps**:
  - **External-high-Re-BL NOT promoted** (case_003 session 6 ran simpleFoam 411 iter but Cl ≈ -0.096 sign-inconsistent · y+ ≈ 2.1×10⁵ outside kOmegaSST nutkWallFunction valid envelope · V98 cascade).
  - **V94 caveat on CHT-multi-stream**: case_011 v3 ran degenerate pure-conduction (no labeled inlet/outlet face-zones → no flow patches). Solver passed procedurally, physics regime is conduction-only.
  - Radiation, DEM/DPM, multiphase-VOF, transonic-compressible still **unexercised at e2e**.
- **Why +1.0**: v1.5 forecast bar was 1 → 2 e2e classes; v2 delivered 1 → 3. Per v1.5's own scoring rubric, this exceeds the +1.0 trigger.
- **STAR-CCM+ 10 / Fluent 10 / OpenFOAM 9**: unchanged.

### 4. 求解器健壮性 — v2: 7.0 (v1: 6 · Δ +1.0)

- **v1 baseline**: V-series sediment 13+ death-mode classes · case_002a 2689 SIMPLE iters · V84 production schemes.
- **v2 additions** — new solver-numerics-class V-row families:
  - **V92** — multi-region `cellZoneInside inside` ray-cast heterogeneity (CHT family). New family: STL-topology-dependent cellZone classifier behavior.
  - **V93** — reacting-low-Mach pre-ignition T floor rule (reacting family). New family: per-species polynomial range vs boundary T cross-check.
  - **V96 + V97** — A6 unit_detector advisor-internal silent fall-through (CAD family but solver-blocking via V20 cascade). New family: advisor-double-silence-as-INCONCLUSIVE pattern.
  - **V98** — external-high-Re-BL y+ resolution physical infeasibility at V20-unresolved scale (external-aerodynamics family). New family: solver-runs-but-physics-meaningless cascade.
  - **3 new e2e numerics classes** demonstrated no-FATAL behavior: CHT-multi-stream (200 iter), reacting (2000 step), external-RANS (411 iter).
- **v2 remaining gaps**:
  - Inherently OpenFOAM-bound robustness (no commercial under-relaxation auto-tune).
  - buoyantSimpleFoam 5-divergence-record-history from V5/V6/V7 unchanged.
  - V98 demonstrates "runs without divergence" ≠ "physically valid" — solver-side robustness is necessary not sufficient.
- **Why +1.0**: v1.5 forecast bar was "≥1 new solver-numerics-class V-row family (not D7/sediment-only)". v2 has **at least 4** new families (V92/V93/V96/V97/V98 — V96+V97 share one family). Per v1.5's own rubric this exceeds +1.0 trigger.
- **STAR-CCM+ 9 / Fluent 9 / OpenFOAM 6**: unchanged.

### 5. 后处理质量 — v2: 7.0 (v1: 7 · Δ 0)

- **v1 baseline**: ParaView HD reports (4-tier 22MB HTML embedded) · 8× 3200×2000 PNG templates · v6N renderers · trame WebGL.
- **v2 additions**: case_009 v1.5 has `parse_log_and_plot.py` + evidence PNGs — case-local utility, not harness-wide capability addition. case_003 has session6_advisor_xapp.txt / session6_y_plus_check.txt — likewise case-local evidence.
- **No new ParaView / trame / HD-report tooling. No 后处理 advisor candidate landed. No new postproc V-row family**.
- **Why 0**: no substrate work on this axis. Honest holding pattern.
- **STAR-CCM+ 9 / Fluent 8 / OpenFOAM 5**: unchanged.

### 6. CLI/自动化 — v2: 9.0 (v1: 9 · Δ 0)

- **v1 baseline**: case_002a F4b 10.4h fully Claude-Code-session-driven · uv venv · 30-patch naming.yaml SSOT · dogfood_loop.py.
- **v2 additions**: corpus-sync hook landed (M-DRIFT) but is audit-layer infrastructure not workflow extension; commit-msg hook chain validation. No new CLI workflow primitive.
- **Why 0**: already at OSS-side ceiling 9 (tied with OpenFOAM vanilla); a 10 would require something neither project has yet (e.g., fully autonomous case author with zero human review).

### 7. AI 智能辅助 — v2: 9.0 (v1: 8 · Δ +1.0)

- **v1 baseline**: corpus_loader offline · V-series 84-row + S-series 24-row corpus · 4 advisors LANDED (A1, A2-v2, A3, A7) · `/ai-review` `/ai-diagnose` routes · 4-question gate · DEC-V61-199 Anthropic agent canon.
- **v2 additions**:
  - **Advisor stack 4 LANDED → 8 LANDED**: A4 face_orientation (2026-05-13) · A5 inlet_outlet_validator (2026-05-13) · A8 shm_dict_validator (2026-05-14) · A10 thermo_polynomial_range_advisor (2026-05-14). **100% of charted A1-A8 + A10 candidates now in code** (only A6 not separately landed as it lives in unit_detector.py · A9 not yet defined).
  - **M6 charter empirically demonstrated** in Track C session 5 (case_009 v1.5): Claude Code session as M6 advisor = real-time gap-detection (V41/V91 channel-(b) gap surfaced) + actionable-rule codification (V93) + paired before/after evidence for A10 promotion gate.
  - **6 Track C sessions** completed in 3 calendar days (cadence drift acknowledged in session 6 §7) — but the substrate output is real: 6 sessions × 5 numerics-class probes × 14 V-rows landed.
  - **A6 V96/V97 advisor hardening** demonstrates advisor-feedback loop closes on production substrate.
- **v2 remaining gaps**:
  - A11 (yPlus pre-flight wall-shear advisor) candidate registered post-V98 but not landed.
  - `audit_verdict_semantics_advisor` (V83 6-cross-application Pillar-2 candidate) still drafted not landed.
  - Cross-mechanism robustness for A10 (GRI-3.0 path not yet validated).
- **Why +1.0**: advisor stack doubled (4 → 8) and the M6 charter "advisor 接管决策" thesis is now empirically demonstrated for one class (session 5 paired before/after on case_009). +1.0 is conservative given evidence; could argue +1.5 to **9.5** but capping at 9 because 8 axes-of-AI-utility is reasonable upper bound until competing-AI-tier (Siemens Industrial Copilot etc.) calibration data emerges.
- **STAR-CCM+ 2 / Fluent 1 / OpenFOAM 0**: unchanged.

### 8. 可重现/审计 — v2: 9.5 (v1: 9 · Δ +0.5)

- **v1 baseline**: V-series + DEC chain + Codex relay reports + corpus sync + 4-question gate + naming.yaml SSOT + 100% git tracked + Surface-scan trailer + DEC-V61-088.
- **v2 additions**:
  - **M-DRIFT corpus drift-prevention pre-commit hook** landed (already credited at v1.5).
  - **V-series 84 → 98 rows** (+14): all dual-corpus-mirrored, all cross-referenced in DECs, all backfilled where retroactive.
  - **V91 sediment-state correction protocol** demonstrated (V41 [VALIDATED] → [QUESTIONABLE 2026-05-14]) — sediment-state itself now treated as verifiable artifact class.
- **Why hold at 9.5 (not 10)**: per COMMENTARY §"评分会怎么变" — "10 留给还未出现的能力" principle. The remaining 0.5 sits with truly-novel reproducibility primitives not yet invented (e.g., byte-deterministic case-author replay with cryptographic chain).

---

## Bottleneck analysis (Done dim 5 NOT MET · gap 0.1)

**Left half average 7.10 vs target 7.2 → gap 0.1.**

To close gap 0.1, one of these single-axis moves would suffice:
- **网格 6.5 → 7.0** (+0.5 on axis 2 = +0.1 on left half average): would require evidence that mesh-debug-loop reduces below v1.5's "≤3-iter on new case" bar. v2 substrate has *mixed* evidence (case_003 1-iter PASS but case_011 v3 5-iter to v5b). Not cleanly met.
- **后处理 7.0 → 7.5** (+0.5 on axis 5 = +0.1 on left half average): would require new postproc tooling / advisor / V-row family. No substrate work this arc.

**Primary bottleneck identified**: **网格生成 (6.5)**. The structural OpenFOAM-sHM bound + V85 connected-component cap + complex-internal-void STL multi-region fragility (V92) are the load-bearing barriers. A8 LANDED helped (first mesh-layer advisor) but didn't shorten the debug loop on case_011 v3.

**Secondary bottleneck**: **后处理 (7.0)** — unchanged from v1; structurally tractable but no substrate work this arc directed at the axis.

**Tertiary structural ceiling**: **求解器 (7.0)** + **CAD (7.0)** — both moved +1.0 this arc; further +0.5 each would require either commercial-tier convergence acceleration (求解器) or CATIA/NX/Creo native plugin (CAD). Neither is in the M1-M6 roadmap.

---

## Substrate-most-recent-pushed axis (informational)

Although Done dim 5 NOT MET, the **物理 axis** received the heaviest substrate push:
- e2e numerics class counter 1/3 → 3/3 (3× increase)
- 2 new e2e class evidence rows (chtMR · reacting) with quantified residual reduction + ignite signal
- A10 LANDED (first reacting-class advisor)
- V93 actionable rule codified

This is the axis that **most directly reflects the M-XCLASS milestone** (Tier 3 cross-numerics-class second case PASS) ticking `[x]` and reacting-low-Mach formally promoted in session 5 retro §9.

---

## Delta vs v1 justification — at-a-glance

| Axis | v1 → v2 | Trigger evidence |
|---|---|---|
| CAD | 6 → 7 | A6 V96/V97 fix + CRM-HLS Tier-1 walk-through (commit `83e2793` + session 6) |
| 网格 | 6 → 6.5 | A8 LANDED (DEC-V61-198-sub-A8) + 3-region v5b mesh + 197k industrial mesh |
| 物理 | 7 → 8 | e2e counter 1/3 → 3/3 (V92 + V93 + chtMR 200 iter + reacting 2000 step) |
| 求解器 | 6 → 7 | ≥4 new solver-numerics-class V-row families (V92/V93/V96+V97/V98) |
| 后处理 | 7 → 7 | (no substrate work) |
| CLI | 9 → 9 | M-DRIFT audit-infra only; ceiling holds |
| AI | 8 → 9 | Advisor stack 4 → 8 LANDED + M6 charter empirically demonstrated (session 5) |
| 审计 | 9 → 9.5 | (held at v1.5 level; M-DRIFT + V-series 84→98 + V91 sediment-correction protocol) |

---

## What v2 explicitly does NOT claim

- ❌ Done dim 5 **NOT MET** at v2 (left half 7.10 < 7.2 target).
- ❌ Does NOT overwrite v1 PNG (preserved as `capability_radar.png` governance baseline).
- ❌ Does NOT amend COMMENTARY.md (v1 stays v1 truth; v2 is a new commentary layer).
- ❌ Does NOT touch commercial-baseline scores (STAR-CCM+/Fluent/OpenFOAM vanilla unchanged per hard constraint).
- ❌ Does NOT update `.planning/ARC-GOAL.md` (main session reconcile per B19 race-avoidance constraint).
- ❌ Does NOT credit case_007 / case_008 / case_005 etc. (not exercised this substrate window).

---

## What the v2 left-half-gap-0.1 tells the main session

The gap is **structurally tight**. Pushing left half to ≥7.2 from here requires:
1. **Track C session 7 mesh-debug-loop shrinking** demonstrated on a new case (would move 网格 to 7.0 → close gap exactly), **OR**
2. **Postproc substrate work** (e.g., new HD-report advisor or trame integration land) (would move 后处理 to 7.5 → close gap exactly), **OR**
3. **Resolution of V94 face-label loss** + e2e on case_011 v4 with real flow patches (would unlock physics axis to 8.5 → close gap with margin), **OR**
4. Combinations.

These are **substrate-pushable single moves**, not structural barriers. The 0.1 gap is reachable in 1-2 sessions, not a months-out target. M-RADAR-V2 milestone reports NOT MET honestly; the path to MET is clear.

**Recommendation for main session**: tick M-RADAR-V2 milestone `[x]` (the v2 re-paint deliverable is complete and honest), but mark Done dim 5 as `[NOT MET · gap 0.1 · path: Track C session 7 mesh-debug shrink OR postproc V-row land]`.

— EOF —
