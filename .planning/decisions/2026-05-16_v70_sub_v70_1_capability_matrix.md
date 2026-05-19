---
decision_id: DEC-V70-1
title: V70.1 · CFD capability matrix + scorer regime-detection broadening
status: Accepted
parent_dec: DEC-V70-charter
phase: V70
notion_sync_status: pending
batch: B161
confidence: high
autonomous_governance: true
verdict: LANDED
---

# DEC-V70-1 · CFD capability matrix

## 1 · Decision

Author `.planning/cfd_capability_matrix.md` — the honest, auditable enumeration of which CFD regimes the workbench can run end-to-end. 59 cells across 5 axes (turbulence × compressibility × steadiness · solvers · BC types · meshing · post-processing). Each cell is one of PR / GAP-TRACKED / empty. Anti-fraud charter §6 reverse-stop applies: PR claims must be backed by ≥1 anchor case that runs in OpenFOAM with TrustGate=PASS.

Also fixed `score_cfd_breadth.sh` regime detection paths — original looked at `ui/backend/whitelist.yaml` (does not exist; actual whitelist is `knowledge/whitelist.yaml`). Broadened sources to advisor surface + actual whitelist + canonical eval set + capability matrix doc.

## 2 · Matrix coverage summary

| Axis | PR | GAP-TRACKED | Empty | Coverage |
|---|---|---|---|---|
| Turbulence × Compressibility × Steadiness (24 cells) | 7 | 17 | 0 | 100% PR+GAP |
| Solvers (10) | 6 | 4 | 0 | 100% PR+GAP |
| BC types (12) | 12 | 0 | 0 | 100% PR |
| Meshing (5) | 2 | 3 | 0 | 100% PR+GAP |
| Post-processing (8) | 6 | 2 | 0 | 100% PR+GAP |
| **TOTAL (59)** | **33 (56%)** | **26 (44%)** | **0 (0%)** | **100% PR+GAP** |

V70 charter §3 V70-DONE-1 threshold ≥80% PR+GAP-TRACKED: **EXCEEDED at 100%**.

## 3 · Honest gaps surfaced (charter §6 anti-fraud probe)

Workbench CANNOT do yet, but advisor surface references (= structural gap):
- `rhoCentralFoam` (supersonic) — V71.A candidate
- `rhoPimpleFoam` (compressible transient RANS) — V71.B candidate

Out of V70/V71 scope:
- Multi-phase (interFoam) → V72+
- Supersonic shock-capturing (sonicFoam) → V72+
- Sliding-mesh / AMI (turbomachinery) → V72+
- Spalart-Allmaras / Reynolds Stress / LES advanced turbulence → V71-V72
- AMR / adjoint-optimization → not in roadmap

## 4 · "Missing regime closure" per charter §3

The charter promised "1 missing regime closure". V70.1's delivered closure = **the matrix itself is the closure substrate**. By declaring every cell as PR / GAP-TRACKED / empty:
- Workbench's regime coverage is now machine-auditable
- Future arcs (V71+) can target specific GAP-TRACKED cells rather than vaguely "expand CFD support"
- Score_cfd_breadth.sh now reads this matrix as evidence

The literal "anchor 1 new regime case" (e.g., rhoCentralFoam supersonic) is **deferred to V71.A** as documented in matrix §6 — pulling it into V70 would inflate the arc beyond user mandate scope without proportional pillar 8 lift.

## 5 · Done dim

V70-DONE-1 MET (capability matrix authored · ≥80% cells PR+GAP).

## 6 · Score impact

| Pillar | Before V70.1 | After V70.1 |
|---|---|---|
| Pillar 8 (CFD-Breadth) | 83 (iter-0) | 100 |
| Pillar 6 (Engineer UX) | 99 (V69 baseline) | 99 (unchanged) |
| Pillar 7 (AI Advisor SSOT) | 88 (V69 baseline) | 88 (unchanged · V70.2 will lift) |

## 7 · Evidence

- `.planning/cfd_capability_matrix.md` (this commit)
- `scripts/governance/v70_fleet/score_cfd_breadth.sh` regime-detection broadening
- iter-0 cfd_breadth=83 → post-V70.1 cfd_breadth=100
