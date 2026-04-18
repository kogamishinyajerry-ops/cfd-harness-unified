# External-Gate Decision Queue

Single entry point for decisions deferred from ADWM v5.2 autonomous
governance to external Gate review. Each item points to full rationale
rather than duplicating it.

**Queue state as of**: 2026-04-19 (post-EX-1-010)
**Notion MCP status**: UNREACHABLE (last probe 2026-04-19T00:12 —
`not_found_error`). Items marked `Notion backfill PENDING` will be
mirrored to Decisions DB the moment MCP is restored.

---

## Q-1: DHC (differential_heated_cavity) gold-reference accuracy

- **Source**: `.planning/decisions/2026-04-18_ex1_008_fuse.md` (DEC-ADWM-004)
- **Blocking class**: hard floor #1 — gold numeric edit required
- **Summary**: EX-1-008 G1 CHK-3 measured Nu=77.82 on B1 256² mesh;
  gold `ref_value=30.0`. Literature for Ra=1e10 2D DHC actually
  sits in 100-160 range — gold may itself be inconsistent with
  stated Ra. Cycle 2 FUSED because Option B (snGrad) would land
  HIGHER not lower, cannot close a gold-accuracy question.
- **Two decision paths** (external Gate picks one):
  - **Path P-1** (gold correction): update `ref_value` to re-sourced
    Ra=1e10 value (100-160 range); expand tolerance to ±20-25% to
    cover 256² BL-resolution gap.
  - **Path P-2** (regime downgrade): keep current gold numbers but
    move whitelist Ra target from 1e10 to 1e6-1e7 where Nu ≈ 10-20
    is both well-documented AND resolvable on current mesh.
- **Current state**: narrative `physics_contract.contract_status`
  updated 2026-04-18 (commit 5e06ab4) to record EX-1-008 precondition
  #3 SATISFIED (mean-over-y extractor). Numeric fields unchanged.
- **Notion backfill**: PENDING (DEC-ADWM-004)

## Q-2: R-A-relabel (fully_developed_turbulent_pipe_flow → duct_flow)

- **Source**: `reports/ex1_first_slice/diagnostic_memo.md` §R-A-relabel
  (rank 3 remediation) + `reports/ex1_005_whitelist_coverage_and_mini_review/methodology_mini_review.md`
  §R-A-relabel rank-3 note
- **Blocking class**: whitelist.yaml edit required (beyond gold numeric;
  changes physics contract type)
- **Summary**: Adapter's `SIMPLE_GRID` for this case is a rectangular
  duct, not a circular pipe — so the Hagen-Poiseuille / Moody-chart
  pipe correlation being applied is a categorical mismatch. Duct-flow
  Darcy correlation would be physically valid. Relabel requires:
  1. Rename whitelist entry and Gold YAML
  2. Create new `knowledge/gold_standards/duct_flow.yaml` with duct
     Darcy f reference
  3. Consumer routing update in error_attributor for new task name
- **External-Gate authority needed**: whitelist.yaml is out-of-scope
  for ADWM v5.2 autonomous authority; mini-review explicitly says
  "Do NOT rush to land R-A-relabel just to use it."
- **Cycle budget estimate**: 1-2 cycles once approved (single YAML
  create + whitelist edit + test updates; no src/ logic change)
- **Notion backfill**: N/A (no ADWM decision yet — needs external
  Gate to grant authority)

## ~~Q-3: ADWM decision backfill to Notion Decisions DB~~ — CLOSED 2026-04-19

- **Resolution**: Notion MCP remained unreachable but `NOTION_TOKEN`
  direct REST API call worked. All 6 decisions backfilled via
  `/tmp/notion_backfill_decisions.py`:
  - DEC-ADWM-001: ADWM v5.2 activation + 5-goal plan — Scope=Project, Status=Accepted
  - DEC-ADWM-002: EX-1-008 mean-Nu refactor self-APPROVE — Status=Closed
  - DEC-ADWM-003: EX-1-G3 cylinder_wake physics_contract restructure — Status=Closed
  - DEC-ADWM-004: EX-1-008 FUSE + DHC escalation — Scope=Architecture, Status=Accepted
  - DEC-ADWM-005: EX-1-009 Spalding audit self-APPROVE — Status=Closed
  - DEC-ADWM-006: EX-1-010 cylinder canonical-band audit self-APPROVE — Status=Closed
- S-003l Session record also created in Sessions DB with Status=Closed.
- Homepage snapshot (heading + callout + 5-row table) updated from
  2026-04-17 state to 2026-04-19 state.

---

## Meta

- Adding to this queue: append a new `## Q-N:` section. Keep each to
  ~20 lines with pointer to the full rationale document.
- Removing from this queue: once external Gate acts or MCP restores
  for the Notion class, strike through but keep the entry for
  historical trace.
- This index is one of two authoritative cross-cutting state
  documents in `.planning/` alongside `d4_plus_rules.yaml`.

Produced: 2026-04-19 by opus47-main (ADWM v5.2 autonomous continuation;
post-EX-1-010 landing)
