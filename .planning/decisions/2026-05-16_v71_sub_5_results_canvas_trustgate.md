---
decision_id: DEC-V71-5
title: V71.5 · ResultsCanvas + TrustGate verdict surface · V71.P/Q LANDED · Image 07
status: Accepted
parent_dec: DEC-V71-charter
phase: V71
notion_sync_status: pending
predecessor: DEC-V71-4
batch: B174
confidence: high
autonomous_governance: true
verdict: LANDED
v_row_landed: V71.5 (Done dimension #5 of 9)
substrate: V71.4 LANDED B173 · 425 tests pass
---

# DEC-V71-5 · ResultsCanvas + TrustGate verdict surface

## 1 · Decision

Land V71.P (ResultsCanvas) + V71.Q (TrustGateVerdict component) per blueprint Image 07. Step 5 report viewport now shows a large verdict block at the top with semantic color, summary line, point-by-point comparison, and provenance footer.

## 2 · Scope

New file: `ui/frontend/src/pages/workbench/v3/components/canvas/TrustGateVerdict.tsx` (~165 LOC).

Modified: `canvas/ReportComparisonV3.tsx` mounts the verdict block at the top of the canvas above the existing Ghia 1982 chart.

Verdict states with tone mapping:
- `PASS` → v3.inlet · "PASS" 34px
- `PASS_WITH_DISCLAIMER` → v3.symmetry
- `FAIL` → v3.wall
- `PENDING` / `INCONCLUSIVE` → v3.textTertiary

Point-by-point row format: `y/H | gold | computed | err%` with err% colored green if `|err|≤5%`, red otherwise.

## 3 · V130 / V132 compliance

The verdict block is **display-only**. There is no:
- "Promote to gold" button
- "Override verdict" button
- "Publish" button
- "Re-run" or "Auto-fix" button

V71.R (GoldPromotionPath) is **deferred** per V71 charter — it would route from this surface to a separate promotion workflow as a quiet text link, never as an action button.

New test asserts none of `/promote|override|publish|推送|覆盖/i` match any button in the rendered DOM.

## 4 · Tests

`npx vitest run` → **427 pass** (was 425 · +2 V71.5 tests). `npx tsc --noEmit` → **PASS**.

## 5 · Goal-backward map

Charter Done dim #5 ("ResultsCanvas + TrustGate verdict — gold-vs-computed chart + HUGE PASS + point-by-point table") → **LANDED**.

## 6 · Risks

- Verdict + sample points are currently hard-coded to PASS with the cavity Ghia perturbation. V72+ will wire `/api/cases/:id/trust-gate` to derive verdict from real run results.
- Point-by-point shows 5 sample stations (indexes 4/7/9/11/13 of 17 Ghia points) for readability. Full table can fold open in a future iter.

## 7 · Surface-scan trailer

**Surface-scan: clean.** No pre-existing TrustGate verdict UI component (the existing `useCaseStatus` hook exposes `trustGate` string but had no canvas renderer). V71.5 is greenfield on a top-level component.

## 8 · Counter

Counter +1. Cumulative arc counter for V71: **6** (charter + V71.1-5).

## 9 · Next

V71.6 — Lock 8 visual baselines (23-30) against blueprint images · run V71 close-confirm iter · author V71 close DEC + retro.

---

**Co-Authored-By**: Claude Opus 4.7 (1M context)
