---
decision_id: DEC-V66-B-charter
title: V66-B "AI Advisor Stack Build-out" arc charter · target Pillar 3+7 advance · 20-case canonical eval set · advisor SDK
status: Accepted
parent_dec: DEC-V65-A-close
phase: V66-B
notion_sync_status: pending
predecessor: DEC-V65-A-close
batch: B100
confidence: high
autonomous_governance: true
verdict: ARC_CHARTER_ACCEPTED
v_row_landed: none (charter)
substrate: .planning/ARC-GOAL.md (transition v65→v66)
---

# DEC-V66-B-charter · V66-B "AI Advisor Stack Build-out" arc launch

## 1 · Decision

After V65-A close at 69.76 weighted (6/6 Done dims MET, 25.24 to 95), launch successor arc **V66-B "AI Advisor Stack Build-out"** targeting **Pillar 3 (advisor stack 72→90) + Pillar 7 (AI advisor SSOT 62→90)**. Continues V63→V64→V65 same-day cadence per V65-A close §9 V66-B recommendation. Inherits scoring framework v1.0 SSOT.

## 2 · Rationale

V65-A delivered Pillar 1 (validation maturity) +5.7 weighted + Pillar 2 (corpus depth) +4.2 weighted. Remaining gap to 95 is **25.24 points** with these unevenly distributed:

| Pillar | Weight | Current | Ceiling | Why V66-B picks this |
|---|---|---|---|---|
| 1 Validation maturity | 30% | 54 | +13.8 | V65-A territory · diminishing returns |
| 2 Corpus depth | 20% | 87.8 | +2.4 | Largely saturated |
| **3 Advisor stack** | **15%** | **72** | **+4.2** | **V66-B primary lever** |
| 4 Reproducibility | 10% | 78 | +2.2 | CI work needed, separate arc |
| 5 Governance | 10% | 88 | +1.2 | Largely saturated |
| 6 Engineer UX | 10% | 55 | +4.5 | V65-C territory · UI implementation |
| **7 AI-advisor SSOT** | **5%** | **62** | **+1.9** | **V66-B secondary lever** |

V66-B chases Pillar 3 + 7 = **+6.1 weighted ceiling** with autonomous-mode-friendly work (text/yaml/python files, no UI rendering required).

Why V66-B over V66-A continued FULL push:
- V66-A would target Pillar 1 further · but flat plate variants done · novel physics regimes need significant substrate work · 2 sessions per FULL typical
- V66-B builds on V130/V132 thesis already established · 20-case eval set seeded in memory · advisor rules in `.planning/methodology/` ready to expand · NO new physics substrate required
- V66-B 1 session can plausibly advance Pillar 3 by 10-15 raw + Pillar 7 by 20-25 raw → +3-4 weighted

## 3 · North Star (1 sentence)

> "Build the AI advisor stack into a 12+ rule corpus driven by a 20-case canonical eval set; promote Claude Code session = AI advisor (V132 collapse) into validated regression-protected SSOT; demonstrate advisor reproducibility via in-session re-runs over multi-case + multi-physics scenarios."

## 4 · Done Definition (all 6 required for close)

| # | Done dim | Start (V65-A close) | Done threshold | Verification |
|---|---|---|---|---|
| 1 | Advisor rule coverage expansion | 9 rules (V64-A) | **≥12 rules** with documented signatures | `.planning/methodology/advisor_rules.md` count ≥12 |
| 2 | Canonical eval set bootstrap | 0 cases | **≥20 canonical eval cases** documented with V-row attribution | `.planning/evals/canonical/` ≥20 case files |
| 3 | Advisor regression protection | none | **Automated eval runs over ≥20 cases** with pass/fail logging | `.planning/evals/runs/` ≥2 run logs |
| 4 | External Claude Code session SDK | conceptual (V132) | **1 SDK doc · 1 sample external session log · 1 reproducibility check** | `.planning/sdk/` doc + 1 sample |
| 5 | Advisor stack maturity | 72/100 | **Pillar 3 ≥85** | scoring framework re-anchor |
| 6 | V133-V140 candidate seeding | V101..V107 | **≥3 V13x candidates documented** (advisor-class signatures) | V-corpus has ≥3 new V13x candidates |

**Target close**: 6/6 Done dims MET via honest accounting per scoring framework v1.0.

## 5 · Tier seeds (parallel batches)

### Tier 1 · Bootstrap (unblocking · parallel)

- **M-V66B-EVAL-SET-BOOTSTRAP**: Inventory V-series corpus V51-V107 · pick 20 canonical eval cases (mix of LANDED V-rows + F-NEW candidates · multi-physics) · document each with: input dicts/sandbox path · expected V-row attribution · expected advisor rule firings · "advisor should say X about this case"
- **M-V66B-ADVISOR-RULES-AUDIT**: Re-read 9 V64-A advisor rules · identify gaps where V65-A V103-V107 + 7 F-NEW candidates suggest new rules · draft ≥3 new rules

### Tier 2 · Expansion (depends on Tier 1)

- **M-V66B-NEW-RULE-1**: F-NEW-Cf-canonical-choice → "ADVISOR-V103: at Re_x > 5e6 prefer Schultz-Grunow over Prandtl-Schlichting; below Re_x=5e6 use Wieghardt experimental"
- **M-V66B-NEW-RULE-2**: F-NEW-low-Re-transition-trigger (V107) → "ADVISOR-V107: kOmegaSST with I_inlet=0.5% under-predicts Cf at Re_x ∈ [1e6, 3e6] by ~10%; consider transition model or higher I"
- **M-V66B-NEW-RULE-3**: F-NEW-shm-layer-addition-instability + F-NEW-tutorial-substrate-inspection → "ADVISOR-mesh-canonical: prefer purpose-built canonical tutorials over custom mesh attempts at y+~1 BL on curved geometry"

### Tier 3 · Regression protection (depends on Tier 1+2)

- **M-V66B-ADVISOR-EVAL-RUN-1**: Run advisor over 20 eval cases · log which rules fire on each · compare against expected firings · identify false negatives + false positives
- **M-V66B-SDK-SAMPLE**: External Claude Code session reads canonical eval case · runs advisor · reports findings · session log preserved for reproducibility
- **M-V66B-SCORE-VERIFY**: Pillar 3+7 re-anchor per scoring framework after Tier 1+2+3 land

### Tier 4 · Close

- **M-V66B-CLOSE**: V66-B close DEC after 6/6 Done dims MET · V67 charter seed

## 6 · Triggers (redirect rules)

| Trigger | Redirect |
|---|---|
| Canonical eval set lookup ≥ 3 sessions ineffective | Drop to 15 cases (Done #2 threshold relax) |
| Advisor rule new signatures fewer than expected | Mark V13x candidates "deferred-to-V67" not QUESTIONABLE |
| External SDK doc draft ≥ 2 sessions blocked | Use embedded session export instead of fresh-session-via-API path |
| Pillar 3 fails to reach 85 after all 6 Done dims | Accept Pillar 3 at 80+ as MET (Done #5 relax with documented rationale) |

## 7 · Anti-inflation guards (inherits scoring framework v1.0 §4)

❌ Advisor rule "renaming" doesn't count — distinct new signature required
❌ Eval case "duplication" — same case under different name doesn't multiply
❌ SDK doc "stub" — must have 1 sample external session log proving reproducibility
❌ V13x candidate without ≥1 instance — speculation doesn't count
✅ Honest "rule fires 0 times in 20 cases" accounting required — decay rule applies

## 8 · 4Q gate per artifact (V130 thesis enforced)

Every V66-B Done dim must answer YES to all 4:
1. LLM offline can run? (advisor rules + eval cases work without LLM)
2. Artifacts produced? (rule files, eval case files, run logs, SDK doc + sample)
3. TrustGate explainable? (rule signatures + expected firings + sample logs)
4. AI advisor-only? (Claude Code session is advisor, not driver; doesn't write physics dicts)

## 9 · v2.3 compliance

- DEC scope: arc charter (full DEC schema required for governance-rule-change)
- Codex 1-sync-trigger: NOT triggered (no security boundary in advisor stack)
- Kogami opt-in: NOT invoked (autonomous mandate); user can summon if strategic review desired
- Confidence: high (V130/V132 thesis foundation solid · 20-case eval set seeded in memory)
- Counter: autonomous_governance=true · arc charter +1

## 10 · V66-B vs V65-A scope discipline

V66-B does NOT:
- Add industrial FULL reports (V65-A territory · saturated for now)
- Touch Pillar 6 engineer UX (V65-C territory)
- Touch Pillar 4 reproducibility/CI (separate arc)
- Re-classify V65-A V-rows (V101-V107 frozen)

V66-B EXCLUSIVELY:
- Builds advisor stack maturity (Pillar 3)
- Validates AI-advisor SSOT (Pillar 7)
- Seeds V13x advisor-class V-rows (Pillar 2 minor)

## 11 · Score expectations

Per scoring framework v1.0 anchors:
- Pillar 3 advisor stack: 72 → ≥85 (+13 raw · "≥85" anchor "external SDK consumable")
- Pillar 7 AI advisor SSOT: 62 → ≥80 (+18 raw · "≥80" anchor "external SDK + regression-protected")
- Other pillars: mostly unchanged (V66-B disciplined scope)

**Expected V66-B close weighted**: 69.76 + (13 × 0.15) + (18 × 0.05) = 69.76 + 1.95 + 0.90 = **72.61**

Distance to 95: 25.24 → ~22.4 points (–2.85 from V66-B close).

If V66-B over-delivers (advisor rules count higher · eval set bigger), could reach 73-74 weighted.

## 12 · V67 seed (post-V66-B)

After V66-B close, the largest gaps remaining:
- Pillar 1 (30% weight, 54): industrial validation expansion across physics regimes → V67-A
- Pillar 6 (10% weight, 55): engineer UX workbench → V67-C
- Pillar 4 (10% weight, 78): CI/reproducibility hardening → V67-D
- Pillar 3 residual gain: more advisor rules → V67-B continuation

V67 theme decision deferred to V66-B close DEC.

## 13 · Cadence + autonomy commitments

- Same-day cadence with V65-A close (V63→V64→V65→V66 precedent)
- All sub-DECs scope-driven per v2.3 (sub-DEC frontmatter 6-field minimum)
- Notion sync session-end batch (Accepted only)
- No calendar gating (per project rule)
- User can override anytime; autonomous mode default per current mandate

— Claude Code (Opus 4.7 1M) · B100 · V66-B charter · 2026-05-16
