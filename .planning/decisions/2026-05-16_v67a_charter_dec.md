---
decision_id: DEC-V67-A-charter
title: V67-A "Industrial Validation Expansion" arc charter · target Pillar 1 advance · multi-physics canonical substrates · honest sandbox-vs-paper scope split
status: Accepted
parent_dec: DEC-V66-B-close
phase: V67-A
notion_sync_status: pending
predecessor: DEC-V66-B-close
batch: B107
confidence: med
autonomous_governance: true
verdict: ARC_CHARTER_ACCEPTED
v_row_landed: none (charter)
substrate: .planning/ARC-GOAL.md (transition v66→v67)
---

# DEC-V67-A-charter · V67-A "Industrial Validation Expansion" arc launch

## 1 · Decision

After V66-B close at 72.90 weighted (6/6 Done dims · 22.1 to 95), launch successor arc **V67-A "Industrial Validation Expansion"** targeting **Pillar 1 (validation maturity 54→65+)** via multi-physics canonical substrates. Continues V63→V64→V65→V66 same-day cadence per V66-B close §8.

## 2 · Rationale

V66-B advanced advisor stack (Pillar 3) + AI-SSOT (Pillar 7) with NO actual sandbox runs — pure documentation arc. V67-A pivots back to validation work (Pillar 1, 30% weight, highest leverage) because:

| Pillar | Weight | Current | Ceiling | Why V67-A picks this |
|---|---|---|---|---|
| **1 Validation maturity** | **30%** | **54** | **+13.8** | **V67-A primary lever · highest weight** |
| 2 Corpus depth | 20% | 88 | +1.4 | Saturated |
| 3 Advisor stack | 15% | 86 | +1.35 | V67-B territory · diminishing returns |
| 4 Reproducibility | 10% | 78 | +2.2 | V67-D territory · separate arc |
| 5 Governance | 10% | 88 | +1.2 | Saturated |
| 6 Engineer UX | 10% | 55 | +4.5 | V67-C territory · UI implementation |
| 7 AI-advisor SSOT | 5% | 82 | +0.65 | Saturated |

V67-A chases Pillar 1 = **+4.1 weighted ceiling** with HIGHEST per-point payoff (30% weight).

## 3 · Honest scope split · paper-vs-sandbox

V67-A scope deliberately separates work that's autonomous-feasible (paper-class) vs work that needs sandbox compute (run-class):

### Paper-class (autonomous-feasible · same-session deliverable)

- Substrate research: identify 5 canonical industrial validation candidates (ERCOFTAC T3A bypass transition · RAE 2822 transonic airfoil · NASA 30P30N high-lift · NACA 0015 fully-stalled · Driver-Seegmiller BFS extension)
- Case profile drafting: input dict templates · expected verdict signatures · expected advisor firings
- 2-case witness path: identify pairs that can witness same V-row independently
- Done dim definition: which milestones are paper-class vs run-class

### Run-class (sandbox compute · multi-session OR explicit user authorization)

- Actual OpenFOAM solver execution against new substrate
- Cf/Cp/u_tau extraction + canonical reference comparison
- FULL/PARTIAL/FAIL verdict ratification per scoring framework §3.1 (MARGINAL→FULL requires user explicit auth)
- New V-row LANDING with witnessed evidence

**This split prevents inflation**: V67-A close cannot claim Pillar 1 advance from paper-class work alone · run-class delivery requires actual benchmarks per V65-A anti-inflation rules.

## 4 · North Star (1 sentence)

> "Expand industrial validation breadth via 5 canonical substrate research + ≥1 actual industrial FULL benchmark, advancing Pillar 1 from 54 to ≥60 honestly (paper-class +3-4 raw · run-class +3-5 raw if sandbox runs land)."

## 5 · Done Definition (6 Done dims · all required for close)

| # | Done dim | Threshold | Verification | Class |
|---|---|---|---|---|
| 1 | Substrate research · 5 canonical candidates | 5 candidates each with input templates + verdict signatures | `.planning/case_profiles/V67A_*/` 5 files | Paper |
| 2 | 2-case witness pairs identified | ≥3 V-row witness pairs documented | DEC body §6 table | Paper |
| 3 | New industrial FULL ≥1 | actual sandbox run with experimental data delta < anchor threshold | run log + extract script output | **Run** |
| 4 | Eval set expansion | 20 → ≥25 cases | `.planning/evals/canonical/INDEX.md` updated | Paper + Run |
| 5 | Pillar 1 ≥60 | re-anchor honestly | scoring framework re-anchor per §3.1 | Mixed |
| 6 | V67-B + V67-C seed | charter prep for both | DEC body §10 seeds | Paper |

Done #3 (Run-class) is the gating Done dim — V67-A cannot close without ≥1 actual industrial FULL benchmark.

## 6 · Tier seeds (parallel batches)

### Tier 1 · Substrate research (Paper · parallel batches)

- **B108 · Research ERCOFTAC T3A bypass transition substrate** (γ-Re_θt validation target)
- **B109 · Research RAE 2822 transonic airfoil substrate** (compressible transonic Cp/Cf validation)
- **B110 · Research NASA 30P30N high-lift configuration** (multi-element airfoil at high AoA)
- **B111 · Research NACA 0015 fully-stalled** (deep-stall under-prediction · V104 3rd witness candidate)
- **B112 · Research Driver-Seegmiller BFS extension** (separation reattachment at higher Re)

### Tier 2 · Witness path documentation (Paper · depends on Tier 1)

- **B113 · Map 2-case witness pairs** · per V-series 3-criterion gate

### Tier 3 · Sandbox execution (Run · depends on Tier 1+2 + user authorization for §3.1 FULL ratification)

- **B114-B118 · Sandbox run substrate-1 through substrate-5** · 1 attempt each · honest FAIL allowed
- **B119 · Aggregate run-class outcomes · honest Pillar 1 re-anchor**

### Tier 4 · Close

- **B120 · V67-A close DEC after 6/6 Done dims MET · V67-B + V67-C charter seeds**

## 7 · Triggers (redirect rules)

| Trigger | Redirect |
|---|---|
| Substrate research blocks ≥2 sessions on data access | Drop to 3 candidates (Done #1 threshold relax) |
| Sandbox run-class FAILs all 5 substrates | Honest Pillar 1 +0 raw on run-class · paper-class +3-4 still allowed |
| User does not authorize FULL ratification | Honest verdict capped at MARGINAL · run-class +1-2 raw only |
| Pillar 1 fails to reach 60 after 6 Done dims | Accept Pillar 1 at 57+ with documented rationale (Done #5 relax) |

## 8 · Anti-inflation guards (inherits scoring framework v1.0)

❌ Substrate research alone CANNOT count toward Pillar 1 advance (paper-class ≠ validation)
❌ "Probe extension" of existing FULL substrates doesn't count as new validation
❌ Same physics regime across multiple substrates = ≤1 V-row LANDING (anti-cherry-pick)
❌ MARGINAL→FULL ratification requires user explicit auth per §3.1(d)
✅ Honest FAIL accounting required — decay rule applies

## 9 · 4Q gate per artifact (V130 thesis enforced)

Every V67-A Done dim must answer YES to all 4:
1. LLM offline can run? (substrate research + case profiles work without LLM)
2. Artifacts produced? (case profile files, run logs, extract scripts)
3. TrustGate explainable? (canonical reference + delta tables + witness attribution)
4. AI advisor-only? (Claude Code session is advisor / planner, not the actual solver driver — OpenFOAM is)

## 10 · V67-B + V67-C seed (post-V67-A close)

After V67-A close, V67-B and V67-C run in parallel:

### V67-B · Advisor stack continuation (3-5 V13x → V109..V113)
- Migrate V13x-3 (cross-fire), V13x-4 (rhoCentralFoam), V13x-5 (substrate inspect), V13x-6 (yplus target), V13x-7 (residual qualifier) to LANDED with 2nd witnesses
- Python module migration optional · markdown-rule SDK adequate per V132 collapse

### V67-C · Engineer UX workbench parity
- Workbench UI per blueprint v3 (TopBar / 5-step Spine / Viewport+Artifacts / Engineer Control Rail / Truth Chain)
- N2-N6 sub-phases per existing N-series roadmap

## 11 · Score expectations

Per scoring framework v1.0 anchors:
- Pillar 1: 54 → ≥60 (+6 raw · "≥60" anchor "multi-substrate validation breadth" if 1+ FULL lands · "≥55" anchor "paper-class research depth" if all runs FAIL)
- Other pillars: mostly unchanged (V67-A disciplined scope)

**Expected V67-A close weighted (conservative · 1 FULL lands)**: 72.90 + (6 × 0.30) = **74.70**
**Expected V67-A close weighted (optimistic · 2 FULLs land)**: 72.90 + (9 × 0.30) = **75.60**
**Expected V67-A close weighted (pessimistic · 0 FULLs land · paper-class only)**: 72.90 + (3 × 0.30) = **73.80**

Distance to 95: 22.10 → ~20.3 to ~19.4 (–1.8 to –2.7 from V67-A close).

## 12 · v2.3 compliance

- DEC scope: arc charter (full DEC schema required for governance-rule-change)
- Codex 1-sync-trigger: NOT triggered
- Kogami opt-in: NOT invoked (autonomous mandate)
- Confidence: **med** (substrate research is autonomous-doable · sandbox run-class outcome uncertain · user §3.1 auth gating real)
- Counter: autonomous_governance=true · arc charter +1

## 13 · V67-A vs V66-B scope discipline

V67-A does NOT:
- Re-document advisor rules (V66-B territory · saturated)
- Add eval cases without sandbox runs (anti-inflation)
- Touch Pillar 6 UX (V67-C territory)
- Touch Pillar 4 CI (V67-D territory)
- Re-classify V66-B V108 (frozen)

V67-A EXCLUSIVELY:
- Researches 5 industrial canonical substrates (paper-class)
- Runs ≥1 sandbox FULL benchmark (run-class · requires user §3.1 auth for FULL ratification)
- Seeds V67-B + V67-C charter prep

## 14 · Cadence + autonomy commitments

- Same-day cadence with V66-B close: V67-A Tier 1 (substrate research) starts immediately autonomously
- Tier 3 (sandbox runs) gating: requires user authorization for §3.1 MARGINAL→FULL ratification
- All sub-DECs scope-driven per v2.3 (sub-DEC 6-field min)
- Notion sync session-end batch (Accepted only)
- User can override anytime

— Claude Code (Opus 4.7 1M) · B107 · V67-A charter · 2026-05-16
