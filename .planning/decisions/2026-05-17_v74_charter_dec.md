---
decision_id: DEC-V74-charter
title: V74 charter · v3 Data Fidelity & Auditability + 5-surface a11y + per-ref completeness · 13-pillar fleet
status: Accepted
parent_dec: DEC-V73-close
phase: V74
notion_sync_status: pending
batch: B190
confidence: high
autonomous_governance: true
---

# DEC-V74-charter · v3 Data Fidelity & Auditability · 13-pillar fleet

## 1 · North Star

Engineer opens `/workbench/v3/case/lid_driven_cavity?step=5`. The TopBar shows **the actual run_id from the live backend** (not a fake "a4f3b21"). At Step 5 the TrustGate panel renders a **numeric gold-standard delta strip**: each gold reference point with its observed value, % error, and the worst-error point highlighted. The TruthChain tab lists 4 canonical provenance hashes (`corpus_sha · solver_version · mesh_sha · gold_sha`) as **copyable chips**, each truncated to 12 hex chars. The whole shell passes an axe-core audit on Steps **1 / 2 / 3 / 4 / 5** with zero serious/critical WCAG 2.1 AA violations (V73's 3 surfaces extended to 5).

## 2 · NEW Pillar 13 · 数据保真度与可审计性 (Data Fidelity & Auditability)

Industrial CAE software (Solidworks, STAR-CCM+, ANSYS) all expose canonical run identifiers, provenance hashes, and downloadable audit packages. The V73 close left these buried or absent on the v3 surface. Pillar 13 forces them to surface as first-class UI affordances.

| Subscore | Weight | Floor for FULL |
|---|---|---|
| `run_id_visible` | 25 | TopBar shows a real, dynamic run_id from backend (data-testid="topbar-run-id" + data-source="live") |
| `gold_delta_visible` | 25 | TrustGate renders ≥3 per-point gold-delta rows w/ numeric error_pct + worst-point highlight |
| `audit_package_downloadable` | 25 | A `<a download>` or button surfaces in TruthChain that triggers `/api/cases/:id/audit-package` |
| `byte_repro_hash_visible` | 25 | TruthChain lists 4 hashes (corpus_sha + solver_version + mesh_sha + gold_sha) as copyable chips |

Weight = **0.06** (same as Pillar 12).

## 3 · Pillar extensions (V74 increment)

| Pillar | V73 close | V74 |
|---|---|---|
| 11 interaction_polish | wcag_runtime requires Step 1/3/5 PASS (3 surfaces) | requires Step 1/2/3/4/5 PASS (5 surfaces) |
| 12 backend_integration | useQuery_count ≥12 / endpoints ≥5 | useQuery_count ≥18 / endpoints ≥6 |
| 4 visualization | 44 PNG baselines | ≥52 PNG baselines |

## 4 · Sub-DEC plan (6)

| Sub-DEC | Headline | Pillar fed |
|---|---|---|
| V74.1 | WCAG 2.1 AA extension to Step 2 + Step 4 | 11 wcag_runtime |
| V74.2 | Multi-case ribbon per-ref `/completeness` wire | 12 endpoints / 13 gold_delta |
| V74.3 | run_id + 4 provenance hashes surface | 13 run_id + byte_repro |
| V74.4 | GoldDelta panel · numeric error strip | 13 gold_delta_visible |
| V74.5 | Pillar 13 scorer (this script) + audit-package download wire | 13 audit_package_downloadable |
| V74.6 | 8 visual baselines (45-52) + close + retro | 4 + close |

## 5 · Reverse-stops

- V132 MUTATING_ROUTES net diff > 0
- Any auto-execute button (V130 invariant)
- Any pillar regression below 99
- Any of 44 V73 baselines drifts > maxDiffPixelRatio=0.01
- axe-core finds WCAG violations on any of Steps 1-5
- Provenance hashes are hardcoded / non-canonical
- run_id surfaces a stub string instead of live backend value

## 6 · Counter telemetry

- V74-charter: B190
- V74.1-V74.6 + close: B191-B197 (estimated)

## 7 · Close gate

12 pillars × 100/100 × 2 consecutive iters (same gate as V72 / V73).
