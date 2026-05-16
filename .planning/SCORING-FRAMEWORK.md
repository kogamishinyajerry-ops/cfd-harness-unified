# cfd-harness-unified · Blueprint Scoring Framework v1.0
# 蓝图完成度评分机制 · 绝对诚实客观

**Established**: 2026-05-16 (V65-A session · B89)
**SSOT for**: All weighted/raw score updates in ARC-GOAL.md · sub-DEC §"Score impact" · session retros
**Target**: ≥95.0 weighted = excellence

---

## 1 · 7-Pillar weighted structure

| # | Pillar | Weight | Domain |
|---|---|---|---|
| 1 | Validation maturity | **30%** | Industrial FULL reports · canonical convergence quality · strict-FULL residual gates |
| 2 | Corpus depth | **20%** | V-series LANDED rows · case profiles · canonical-artifact ledger |
| 3 | Advisor stack | **15%** | AI advisor rule coverage · fire rates · diagnostic precision |
| 4 | Reproducibility | **10%** | Byte-deterministic builds · CI gates · sandbox immutability |
| 5 | Governance | **10%** | DEC discipline · Codex review hygiene · honest verdict accounting |
| 6 | Engineer UX | **10%** | Workbench UI · 5-step spine · Truth Chain visibility |
| 7 | AI-advisor SSOT | **5%** | V130 advisor-not-driver compliance · 4Q gate per artifact |

**Weighted = Σ (Pillar_raw / 100 × Weight × 100)** — i.e., a raw score of 100 across all pillars = 100 weighted.

---

## 2 · Per-pillar 0-100 raw rubric (honest anchors)

### Pillar 1 · Validation maturity (30% weight)

| Raw range | Anchor |
|---|---|
| 0-30 | No solver runs / no convergence evidence / no canonical comparison |
| 30-50 | 1-D analytical strict-FULL trio (Poiseuille / Couette / Pipe) achieved · industrial cases PARTIAL or FAIL |
| 50-65 | ≥1 industrial strong-PARTIAL with experimental/literature comparison · residuals at within-iter gate |
| **65-75** | **≥2 industrial strong-PARTIAL + 1 strict-FULL residual gate on independent substrate (current zone)** |
| 75-85 | ≥1 industrial FULL report achieved + 2 strong-PARTIAL with <10% canonical delta |
| 85-95 | ≥3 industrial FULL reports · canonical convergence demonstrated across physics regimes |
| 95-100 | Multi-physics industrial FULL coverage + cross-arc validation maturity established |

**Current: 41/100** — case_032 v65 5/5 strict-FULL + case_027 v65 physics-strict + case_028 v3 3/4 FULL criteria · zero industrial FULL achieved.

### Pillar 2 · Corpus depth (20% weight)

| Raw range | Anchor |
|---|---|
| 0-50 | < 10 V-rows · few cases profiled |
| 50-70 | V51-V100 corpus with ≥20 V-rows + ≥15 case profiles |
| **70-85** | **V101+ promotion zone · ≥4 V-rows LANDED in current arc · canonical-artifact ledger 2nd-witness path (current zone)** |
| 85-95 | ≥10 V-rows LANDED in current arc · cross-physics-regime coverage · multi-witness signatures |
| 95-100 | V-series complete across all canonical-artifact + F-NEW signatures with 3+ witnesses each |

**Current: 82.5/100** — 6 V-rows LANDED in V65-A (V101+V103+V104+V105+V106+V107) + 2 F-NEW candidates 1st-observation captured.

### Pillar 3 · Advisor stack (15% weight)

| Raw range | Anchor |
|---|---|
| 0-30 | < 3 advisor rules / no fire rate tracking |
| 30-60 | 9 advisor rules built · fire rates measured per case · case-level coverage 4-7/9 |
| **60-75** | **Advisor stack consolidated · over-met fire rates (8-13/9) · V-row attribution clauses enforced (current zone)** |
| 75-90 | AI advisor SDK consumable by external Claude Code sessions · self-test corpus |
| 90-100 | Advisor stack covers all known F-NEW signatures + V-row patterns + dynamic rule expansion |

**Current: 72/100** — 9-rule advisor with case_028 (8/9) + case_029 (13/9) over-met · V-row attribution clauses validated.

### Pillar 4 · Reproducibility (10% weight)

| Raw range | Anchor |
|---|---|
| 0-50 | Manual setup · no byte-determinism |
| 50-75 | Substrate immutability + sandbox docker pinned + dict version controlled |
| **75-85** | **Substrate + sandbox + log artifacts all under .planning/ control · byte-repro available (current zone)** |
| 85-100 | CI gates pass on every PR · byte-repro across multi-machine · canonical manifest validated |

**Current: 78/100** — substrate immutability + docker openfoam-default:2312 + dict version control. CI not yet integrated.

### Pillar 5 · Governance (10% weight)

| Raw range | Anchor |
|---|---|
| 0-50 | Ad-hoc commits · no DEC discipline |
| 50-75 | DEC scope-driven · sub-DEC frontmatter ≥6 fields · Codex 1-sync-trigger on security boundary |
| **75-90** | **honest FAIL accounting · §3.1/§3.2 ratification semantics · Kogami opt-in (current zone)** |
| 90-100 | Multi-arc governance precedent · counter telemetry analyzed in retros · zero alias-inflation incidents |

**Current: 83/100** — honest FAIL accounting (B79/B80/B87/B88) + §3.1 semantics multi-case validated + Kogami opt-in + Notion Accepted-only sync.

### Pillar 6 · Engineer UX (10% weight)

| Raw range | Anchor |
|---|---|
| 0-40 | CLI-only · no UI |
| **40-65** | **Workbench 4-region layout + 5-step spine designed · concept SVG approved (current zone)** |
| 65-80 | 5-step spine partially implemented · Truth Chain visible · advisor integration UI live |
| 80-95 | Full workbench parity · M2 mesh + M3 physics + M4 solver + M5 postprocess UIs all functional |
| 95-100 | Engineer can complete industrial case e2e without leaving workbench |

**Current: 55/100** — concept SVG + N1.1 step-1 ingest scaffolded · M2-M6 unimplemented.

### Pillar 7 · AI-advisor SSOT (5% weight)

| Raw range | Anchor |
|---|---|
| 0-40 | AI writes case files / drives workflow |
| **40-70** | **V130 advisor-not-driver thesis established · 4Q gate per artifact · AI as consultant role (current zone)** |
| 70-90 | Claude Code session = AI advisor (per V132 collapse) · external SDK / API surface |
| 90-100 | AI advisor SSOT validates against eval set · regression-protected · canonical advisor scenarios |

**Current: 62/100** — V130 thesis solidified + 4Q gate uniformly applied + Claude Code session = AI advisor (V132).

---

## 3 · Score update protocol (honest accounting)

Every batch (sub-DEC) MUST update score per these rules:

### LANDING-class outcomes (positive Δ)

| Outcome class | Pillar Δ raw | Justification gate |
|---|---|---|
| V-row LANDING (3-criterion gate triple-met) | Pillar 2 +3 | Distinct-signature + 2-case independence + canonical attribution |
| Industrial strong-PARTIAL with experimental delta | Pillar 1 +0.5-1 | Solver convergence + experimental comparison documented |
| Industrial FULL (≥10% canonical agreement) | Pillar 1 +3-5 | Full convergence + experimental within ±10% + V-row attribution |
| §3.1 user-ratified MARGINAL-to-FULL | Pillar 5 +1, Pillar 1 +2 | User explicit auth + canonical artifact on non-primary-physics-component |
| Strict-FULL residual gate on independent substrate | Pillar 1 +1 | All 5 fields below 1e-5 final residual + substrate independence justified |

### Probe / candidate / methodology-only outcomes (small Δ)

| Outcome class | Pillar Δ raw | Justification gate |
|---|---|---|
| Probe-extension same-case (signature confirmed not promoted) | Pillar 2 +0.5-1 | Signature reproduced but 2-case independence unmet |
| F-NEW 1st-observation candidate captured | Pillar 2 +0.5 | New signature documented + 1 instance only |
| Honest FAIL with root-cause diagnosis | Pillar 5 +0.5 | FAIL acknowledged + lesson captured + no score inflation |
| MIXED outcome with sub-DEC body | Pillar 5 +0.3 | Partial success documented + open questions queued |

### Negative or zero Δ outcomes (no score inflation)

| Outcome class | Pillar Δ raw | Reason |
|---|---|---|
| FULL attempt FAIL without honest accounting | 0 | Already covered by honest-FAIL +0.5 above; no double-count |
| Repeat-sampling within same case family | 0 | Same-case probes don't multiply corpus depth |
| Alias-renamed V-rows | 0 | Distinct-signature gate required for new V-row Δ |
| Substrate copy without solver run | 0 | Substrate without validation has zero corpus depth value |

### Decay rules (anti-staleness)

| Trigger | Decay |
|---|---|
| V-row LANDED but not corpus-referenced in 3 arcs | -0.5 from Pillar 2 |
| Industrial FULL but solver doesn't reproduce in next arc | -1 from Pillar 1 |
| Advisor rule fires zero times in 5 cases | -0.3 from Pillar 3 |

---

## 4 · Anti-inflation guards

### Prohibited score moves

❌ **Alias inflation**: renaming V51-V100 rows as V101+ does NOT score
❌ **Probe-extension claiming LANDING**: same-case repeat sampling doesn't satisfy 2-case independence
❌ **Cherry-pick canonical**: comparing only to most-favorable correlation
❌ **FAIL hiding**: marking diverged runs as "convergence-pending" rather than FAIL
❌ **Premature LANDING**: claiming V-row before 2nd witness exists
❌ **Pillar 6 advance on UI mock only**: ⏳ needs functional implementation
❌ **Pillar 3 advance via rule renaming**: needs new signature coverage

### Required score moves

✅ **Honest FAIL = +0.5 Pillar 5** even if Pillar 1/2 don't advance
✅ **Methodology lesson capture** = +0.5 Pillar 5 (anti-stale knowledge)
✅ **Independence verification documented** = required for V-row Δ
✅ **Substrate immutability check** = required before sandbox-only experiments score

---

## 5 · Current score breakdown (B88 endpoint)

| Pillar | Raw | Weight | Weighted contribution |
|---|---|---|---|
| 1 | 41 | 30% | 12.30 |
| 2 | 82.5 | 20% | 16.50 |
| 3 | 72 | 15% | 10.80 |
| 4 | 78 | 10% | 7.80 |
| 5 | 83 | 10% | 8.30 |
| 6 | 55 | 10% | 5.50 |
| 7 | 62 | 5% | 3.10 |
| **Total** | | | **64.30** |

**Wait — weighted recalculation gives 64.30, but ARC-GOAL says 67.0. Let me reconcile.**

The discrepancy: ARC-GOAL trajectory was tracked as Δ accumulation from baseline rather than Σ pillars × weight at each point. Let me re-anchor.

**Re-anchoring from pillars (this becomes new canonical)**:
- 41×0.30 + 82.5×0.20 + 72×0.15 + 78×0.10 + 83×0.10 + 55×0.10 + 62×0.05
- = 12.30 + 16.50 + 10.80 + 7.80 + 8.30 + 5.50 + 3.10
- = **64.30**

**Discrepancy explained**: ARC-GOAL accumulator drifted by +2.7 from per-batch Δ summing instead of pillar re-anchoring. Honest re-anchoring places us at **64.3 weighted, distance 30.7 to 95**.

**This is an anti-inflation correction**, applied per the §4 "FAIL hiding" rule (in this case, accumulator hiding).

---

## 6 · Updated trajectory (post-re-anchor)

| Endpoint | ARC-GOAL accumulator | Pillar re-anchor | Discrepancy |
|---|---|---|---|
| B72 start | 62.0 | ~63 | -1.0 (modest baseline drift) |
| B86 (V107 LANDS) | 66.7 | ~63.4 | -3.3 |
| **B88 (after FAIL salvage)** | **67.0** | **64.3** | **-2.7** |

Going forward, **scoring framework v1.0 SSOT** = per-pillar re-anchor at every sub-DEC. ARC-GOAL accumulator becomes a debug trace, not the authority.

---

## 7 · Path to 95 weighted (gap analysis)

Current: 64.3 → Target: 95 → Gap: **30.7 weighted**

| Pillar | Current raw | Headroom raw | Weighted ceiling |
|---|---|---|---|
| 1 (30%) | 41 | 59 | **+17.7** |
| 2 (20%) | 82.5 | 17.5 | +3.5 |
| 3 (15%) | 72 | 28 | +4.2 |
| 4 (10%) | 78 | 22 | +2.2 |
| 5 (10%) | 83 | 17 | +1.7 |
| 6 (10%) | 55 | 45 | **+4.5** |
| 7 (5%) | 62 | 38 | +1.9 |

**Largest gaps**: Pillar 1 (+17.7) + Pillar 6 (+4.5) + Pillar 3 (+4.2). To reach 95 need ~80% of available raw headroom across all pillars, with Pillar 1 the primary lever.

**Pillar 1 path** = industrial FULL reports + canonical convergence quality. Done #4 (3 FULL targets) directly addresses this.

**Pillar 6 path** = workbench UI implementation (V65-C arc territory).

**Pillar 3 path** = advisor stack expansion (V65-B arc territory).

---

## 8 · Honesty enforcement

This framework will be re-verified at:
- Every V-row LANDING (per-batch Pillar 2 Δ honesty)
- Every Done dim MET claim (per-batch arc check)
- Every arc close DEC (full re-anchor)
- Session-end retros (drift check)

**Drift detection**: if accumulator > pillar re-anchor + 1.0 → score inflation flagged, retro mandatory.

— Claude Code (Opus 4.7 1M) · B89 · 2026-05-16
