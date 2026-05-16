# ARC-GOAL · V74 v3 Data Fidelity & Auditability + 5-surface a11y + per-ref completeness · **ACTIVE 2026-05-17**

> **Charter**: `.planning/decisions/2026-05-17_v74_charter_dec.md` (Accepted B190)
> **Predecessor**: DEC-V73-close (12-pillar 100/100 · B189)
> **NEW Pillar 13**: 数据保真度与可审计性 (Data Fidelity & Auditability) · 4 subscores
> **Target**: 13-pillar min ≥99 · 2-consecutive close gate

## North Star

Engineer at Step 5 sees **the actual backend run_id** in the TopBar (not fake), a **numeric gold-delta strip** in the TrustGate with worst-point highlight, and **4 copyable provenance hashes** in TruthChain. axe-core 0 violations on Steps 1-5 (was 1/3/5).

## Done dim checklist

- [x] **V73-DONE-1..11 carry** — verify no regression on V73 close
- [x] **V74-DONE-12 · Composite** — Pillar 13 = **100** · axe-core **0 violations on 5 surfaces** · TopBar run_id **live** · GoldDeltaPanel rendered · audit-package download wire · 4 provenance hash chips

## Sub-DEC progress

- [x] **V74.1 · WCAG Step 2 + Step 4** — axe-core spec extended · 5 surfaces PASS
- [x] **V74.2 · Multi-case ribbon per-ref completeness** — closes V73 retro Q4
- [x] **V74.3 · run_id + provenance hashes** — TopBar + TruthChain copyable
- [x] **V74.4 · GoldDelta panel** — numeric error strip + worst-point highlight
- [x] **V74.5 · Pillar 13 scorer wired** — 4 subscores · audit-package download
- [x] **V74.6 · 8 visual baselines (45-52) + close + retro**

## Fleet criteria (13 pillars · V74 NEW Pillar 13)

| # | Agent | V73 close | V74 |
|---|---|---|---|
| 1-9 | (carry) | 100 | unchanged |
| 4 | Visualization | 100 (44 PNG) | **≥52 PNG** |
| 10 | Industrial-UI | 100 | unchanged (+ V74.4 gold delta panel test contributes) |
| 11 | Interaction-Polish | 100 | **wcag_runtime: 3 → 5 surfaces required** |
| 12 | Backend-Integration | 100 | **useQuery_count ≥18 / endpoints ≥6** |
| 13 | **Data-Fidelity-Auditability** | **N/A** | **≥99** (NEW · 4 subscores) |

## Iteration tracker

| Iter | Date | min(13) | weighted | Lowest dim | Notes | Score report |
|---|---|---|---|---|---|---|
| 0 (V74 baseline) | 2026-05-17 | 8 | 91.52 | data_fidelity (NEW pillar) | charter LANDED · pillar 13 NEW · 12 of 13 carry V73 100 | V74_iter_0.md |
| 1 | 2026-05-17 | **100** | 115.32 | (all 100) | V74.1+2+3+4+5 LANDED · CLOSE_ELIGIBLE | V74_iter_1.md |
| 2 | 2026-05-17 | **100** | 115.32 | (all 100) | stability re-confirm · CLOSE_CONFIRMED (2-consec) | V74_iter_2.md |
| 3 | 2026-05-17 | **100** | 115.32 | (all 100) | + 8 baselines (45-52) · 52/52 PASS · 3-consec margin | V74_iter_3.md |

## Reverse-stop log

- V132 MUTATING_ROUTES net diff > 0
- Any auto-execute button in any v3 surface
- Pillar 6 regression below 99
- Any of 44 V73 baselines drifts > 0.01 pixel ratio
- axe-core finds WCAG violations on any of Steps 1-5
- Hardcoded run_id or provenance hashes
- Audit-package download button without a real backend route

## Counter telemetry

- V74 charter: B190
- V74.1-V74.6 + close: B191-B197 estimated

— V74 ARC-GOAL · 2026-05-17
