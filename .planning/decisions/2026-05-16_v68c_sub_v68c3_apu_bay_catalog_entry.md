---
decision_id: DEC-V68-C.3
title: V68-C.3 · case_002a APU bay catalog entry · case_kind=imported_user + gold_pending=true
status: Accepted
parent_dec: DEC-V68-C-charter
phase: V68-C
notion_sync_status: pending
predecessor: DEC-V68-C-charter
batch: B145
confidence: high
autonomous_governance: true
verdict: SUB_DEC_LANDED
v_row_landed: none (sub-DEC)
substrate: V68-C charter §3 Done dim #5 + §5 sub-DEC V68-C.3
---

# DEC-V68-C.3 · case_002a APU bay catalog entry

## 1 · Decision

Land V68-C.3 by adding the APU bay industrial substrate to the catalog with explicit gold-pending semantics:

- **whitelist.yaml**: add `case_002a` entry (lines 257-298) with all standard fields plus two new yaml keys:
  - `case_kind: imported_user` — annotates the entry is not a curated Ghia/Driver-class case
  - `gold_pending: true` — flags that no third-party gold reference is authored yet
- **Backend schema** (`CaseIndexEntry`): two new optional fields with `case_kind` defaulting to `"whitelist"` and `gold_pending` defaulting to `False`. Defaults preserve the V68-A/B wire shape so existing 10 entries remain shape-stable.
- **list_cases()** reads both fields from the whitelist entry and populates the CaseIndexEntry.
- **batch_matrix + batch CSV** filter out gold_pending entries — those exports are gold-anchored verdict grids; a gold-less case yields only UNKNOWN rows that dilute the audit signal. The catalog GET /api/cases still lists the case for browsing.
- **Frontend** (`WorkbenchIndexPage.CaseCard`): renders an amber `⏳ gold pending` badge in place of the ContractChip and an inline disclaimer ("industrial substrate listed for browsing; no curated reference yet, so the trust gate stays PENDING until gold authoring"). `case_kind` + `gold_pending` flow through as `data-*` attributes for E2E selector use.

**Done dim mapping**:
- **DONE-5 · case_002a APU bay metadata entry** → **MET** at this sub-DEC (whitelist+11, listable, disclaimer surfaces, V130-honest)

**V68-C fleet criteria impact**: whitelist count goes 10→11, satisfying the physics agent's tightened `whitelist_pass=1` threshold.

## 2 · Rationale · why list a gold-less case at all

The APU bay industrial substrate drove the 2026-05-07 strategic pivot (charter operationally complete 2026-05-12 per APU-BAY-EXTEND arc; 5 V-series-extract artifacts LANDED). The substrate already exists at `_industrial_substrates/apu-bay-ventilation-cht/`, the AI review/diagnose routes can run on it, and the engineer audience for cfd-harness is industrial CFD practitioners — who care about industrial cases, not just academic Ghia/Driver canon.

Pre-V68-C.3 the catalog hid it. Pre-V68-C.3 you literally could not navigate to `/workbench/case/case_002a` and have the catalog index acknowledge it existed. That's dishonest about what the workbench can do.

V68-C.3 surfaces the case **with explicit honesty** about its gold state:
- Listable ✓ — engineer can browse it
- ⏳ Gold pending badge ✓ — engineer instantly sees it's not a verdict-bearing case
- Trust gate stays PENDING ✓ — no synthesized PASS/FAIL
- Batch grid + CSV exclude it ✓ — those reports are gold-anchored; case_002a doesn't belong in their universe
- V130 invariant intact ✓ — no AI synthesis, no fake gold

## 3 · Rationale · why two new fields not one

`case_kind` and `gold_pending` are **orthogonal**, not synonyms:
- A whitelist case can become gold_pending (curator pulls the gold pending re-derivation; e.g., the Rayleigh-Bénard Q-new Case 10 HOLD)
- An imported_user case can have a gold authored later (engineer pins a measured value with citation)

Compressing both into `case_kind: "imported_user_gold_pending"` would conflate the two life-cycle axes. Keeping them separate lets future arcs evolve each independently.

## 4 · Implementation summary

- **LOC**: 278 insertions / 6 deletions across 9 files
- **Whitelist count assertion**: V68-C fleet `score_physics.sh` `whitelist_pass` threshold (≥11) now MET via the new entry
- **Tests added**: 1 backend (rewrote `test_cases_index_contains_eleven_entries` with positive case_002a assertions + negative whitelist-purity assertions for the other 10) + 3 frontend (gold-pending badge / contract chip preserved / Edit link emitted)
- **Regression**: 405/405 vitest PASS (402→405); backend 87/87 in V68-C-relevant suites; 14 pre-existing failures unchanged (G1, geometry_ingest, meshing_gmsh, n6_2/n6_3 — all unrelated to V68-C.3)

## 5 · Acceptance · UX verified

| Surface | Pre-V68-C.3 | Post-V68-C.3 |
|---|---|---|
| GET /api/cases | 10 entries, no case_002a | 11 entries, case_002a included with case_kind=imported_user, gold_pending=true |
| GET /api/exports/batch.csv | 10 case_ids | 10 case_ids (case_002a filtered — no gold to anchor) |
| GET /api/batch-matrix n_cases | 10 | 10 (case_002a filtered for same reason) |
| /workbench index card | case_002a absent | ⏳ gold pending badge + disclaimer; Edit & run link works |
| /workbench/case/case_002a | URL existed but catalog hid it | URL exists AND catalog lists it; MaterialCard renders reference mode (V68-C.1 path) since case isn't in IMPORTED_DIR |
| AI advisor /ai-review on case_002a | 404 (not in IMPORTED_DIR) | 404 (unchanged — V130 contract preserved) |

## 6 · Files changed

| File | Status | Purpose |
|---|---|---|
| knowledge/whitelist.yaml | M | + case_002a entry with case_kind + gold_pending |
| ui/backend/schemas/validation.py | M | + 2 fields on CaseIndexEntry |
| ui/backend/services/validation_report.py | M | list_cases() reads new fields |
| ui/backend/services/batch_matrix.py | M | filter gold_pending in row loader |
| ui/backend/services/export_csv.py | M | filter gold_pending in case-id loader |
| ui/backend/tests/test_validation_report.py | M | rewrote 10→11 case count test with case_002a + purity assertions |
| ui/frontend/src/types/validation.ts | M | + 2 optional fields |
| ui/frontend/src/pages/workbench/WorkbenchIndexPage.tsx | M | + GoldPendingBadge + disclaimer + data-* attrs |
| ui/frontend/src/pages/workbench/__tests__/WorkbenchIndexPage.gold_pending.test.tsx | A | 3 vitest |

## 7 · Risk register

| Risk | Probability | Mitigation |
|---|---|---|
| Engineer sees ⏳ badge, thinks case is broken, doesn't open it | low | Inline disclaimer explicitly says "listed for browsing"; Edit & run link visually identical to whitelist cases |
| Future contributor adds a case with gold_pending=true but forgets case_kind | low | Schema defaults: case_kind defaults to "whitelist" (safer; engineer sees normal contract chip until gold_pending kicks in for badge) |
| Batch CSV / Matrix consumer expects all whitelist cases including case_002a | low | Filter logic explicit with comment; gold_pending=true is the documented opt-out signal |
| `_load_gold_standard("case_002a")` returns None, downstream code crashes | mitigated | Verified via `PYTHONPATH=. uv run python -c "list_cases()"` — case_002a returns has_gold_standard=False, contract_status=UNKNOWN cleanly |

## 8 · Honest scope · what's NOT in V68-C.3

- **No gold authoring**: that's the deferred-to-future-arc work the gold_pending flag exists to document
- **No /workbench/case/case_002a deep-link verification at e2e level**: that's V68-C.4's (playwright covers it there)
- **No backend route changes**: GET /api/cases/case_002a returns the case via existing whitelist resolution; /physics + /ai-review still 404 because case isn't in IMPORTED_DIR (correct V130 contract)

## 9 · Confidence: high

- 9 files changed but all changes are additive with explicit defaults preserving prior wire shape
- Verified end-to-end: 11 cases listed, case_002a flagged correctly, batch exports cleanly skip it, frontend renders badge + disclaimer
- All V68-C-relevant suites green; pre-existing failures untouched
- Whitelist count assertion now MET → next iter physics score should jump 75 → 100

— V68-C.3 sub-DEC · 2026-05-16 · B145
