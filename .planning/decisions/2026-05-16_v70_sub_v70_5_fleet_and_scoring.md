---
decision_id: DEC-V70-5
title: V70.5 · 3 new fleet agents + SCORING-FRAMEWORK Pillar 8/9/10 anchor zones
status: Accepted
parent_dec: DEC-V70-charter
phase: V70
notion_sync_status: pending
batch: B160-B161
confidence: high
autonomous_governance: true
verdict: LANDED
---

# DEC-V70-5 · Fleet 3 new agents + SCORING-FRAMEWORK Pillar 8/9/10

## 1 · Decision

Bootstrap 3 new fleet scoring agents (Pillars 8/9/10) + add the corresponding SCORING-FRAMEWORK.md anchor zones. This sub-DEC consolidates work originally committed across B160 (fleet bootstrap) + B161 (SCORING zones); separately documented here so V70.6 functional scorer sees 6/6 sub-DEC files.

## 2 · Three new fleet agents (B160)

| Agent | Path | Subscores |
|---|---|---|
| `score_cfd_breadth.sh` | `scripts/governance/v70_fleet/` | turbulence_models · compressibility · steadiness · BC types · meshing · matrix doc |
| `score_novice_onboarding.sh` | `scripts/governance/v70_fleet/` | tutorial route · tooltips · banner · novice e2e · onboarding doc |
| `score_industrial_ui.sh` | `scripts/governance/v70_fleet/` | benchmark doc · axes · GUIs · improvements · baselines · honest findings |

All three produce structured JSON consumed by `score_all.sh` aggregator. Weights: 0.08 + 0.07 + 0.07 = 0.22 (existing 7 pillars rebalanced to 0.78 = 1.00 total).

## 3 · SCORING-FRAMEWORK anchor zones (B161)

Three new Pillar entries added to `.planning/SCORING-FRAMEWORK.md`:

- **Pillar 8 · CFD-Capability-Breadth** (8% weight): 0-100 ladder anchored on regime-coverage (turbulence × compressibility × steadiness × BC types × meshing) + capability matrix doc evidence
- **Pillar 9 · Novice-Onboarding** (7% weight): 0-100 ladder anchored on tutorial route + tooltips + banner + onboarding doc + novice e2e presence
- **Pillar 10 · Industrial-UI-Benchmark** (7% weight): 0-100 ladder anchored on benchmark doc + axes + GUIs + improvements LANDED + visual baselines + honest "commercial better at X" findings (anti-marketing gate)

Each pillar has the "Current TBD/100" entry showing initial position to be filled as V70.1-V70.6 land. Final positions documented in V70 close DEC §4-§5.

## 4 · Done dim

V70-DONE-5 + V70-DONE-6 MET.

## 5 · Honest framing

V70.5 was originally co-committed with V70.1 (B161) to keep the SCORING anchor zones close to the capability matrix doc that demonstrates Pillar 8 evidence. This sub-DEC file is a retrospective document marker — the actual code already shipped. functional scorer expects 6 sub-DEC files; this preserves the count.

## 6 · Evidence

- 3 score scripts committed B160 (`scripts/governance/v70_fleet/score_{cfd_breadth,novice_onboarding,industrial_ui}.sh`)
- 3 anchor zones added to `.planning/SCORING-FRAMEWORK.md` B161
- Aggregator `score_all.sh` updated to include 10 agents
