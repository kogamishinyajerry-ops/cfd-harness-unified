# External-Gate Decision Queue

Single entry point for decisions deferred from ADWM v5.2 autonomous
governance to external Gate review. Each item points to full rationale
rather than duplicating it.

**Queue state as of**: 2026-04-20 (post v6.1 cutover · post Q-3 completion
· post Path-B election per DEC-V61-002)
**Notion MCP status**: ONLINE (last probe 2026-04-20T12:20 —
`notion-get-users` returned the workspace user record). Q-3 officially
closed by DEC-V61-001 Decisions DB mirror; earlier 6 ADWM entries
remained valid from the 2026-04-19 direct-REST backfill batch.

**Path-B interaction** (2026-04-20): Q-1 (DHC gold accuracy) and Q-2
(R-A-relabel) remain OPEN but do NOT block Path-B phases P0..P4. They
re-enter the critical path at Path-B **Phase 5 Audit-Package Builder**,
because the commercial signing review cannot emit signed audit
packages while two known gold-accuracy / whitelist-correctness issues
are unresolved. Until then, the Phase-0 UI surfaces them in Screen 4's
`AuditConcern` list and `DecisionsTrail` — they are visible to every
reviewer rather than hidden.

---

## ~~Q-1: DHC (differential_heated_cavity) gold-reference accuracy~~ — CLOSED 2026-04-20

**Closure**: Resolved by DEC-V61-006 Path P-2 adoption (one of the two paths DEC-ADWM-004 FUSE itself named). Ra 1e10→1e6, Nu 30→8.8 (de Vahl Davis 1983). PR #6 merged `912b2ce1`. See `.planning/decisions/2026-04-20_b_class_gold_remediation.md` Case 6.

<details><summary>Historical record (for trace)</summary>

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
- **Decision**: Path P-2 adopted by Gate Q-new / DEC-V61-006. Nu gold 30→8.8 at Ra=1e6 (de Vahl Davis 1983 benchmark — more canonical than the 10-20 range originally cited, resolvable on 40-80 wall-normal cells).
- **Notion backfill**: COMPLETE (DEC-ADWM-004 synced 2026-04-19 to [page 346c6894…b255](https://www.notion.so/346c68942bed8106b2bfc8457384b255); confirmed by re-probe 2026-04-20T12:20)

</details>

## Q-2: R-A-relabel (fully_developed_turbulent_pipe_flow → duct_flow)

- **Full gate request (2026-04-20T23:05)**: `.planning/gates/Q-2_r_a_relabel.md` — formal 4-path decision surface (A/B/C/D), audit recommendation Path A, Phase 5 interaction notes.
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

## ~~Q-3: Autonomous-governance decision backfill to Notion Decisions DB~~ — CLOSED 2026-04-19 / RE-CLOSED 2026-04-20

- **Resolution 2026-04-19** (ADWM batch): Notion MCP was unreachable but
  `NOTION_TOKEN` direct REST API call worked. All 6 ADWM decisions
  backfilled via `/tmp/notion_backfill_decisions.py`:
  - DEC-ADWM-001: ADWM v5.2 activation + 5-goal plan — Scope=Project, Status=Accepted
  - DEC-ADWM-002: EX-1-008 mean-Nu refactor self-APPROVE — Status=Closed
  - DEC-ADWM-003: EX-1-G3 cylinder_wake physics_contract restructure — Status=Closed
  - DEC-ADWM-004: EX-1-008 FUSE + DHC escalation — Scope=Architecture, Status=Accepted
  - DEC-ADWM-005: EX-1-009 Spalding audit self-APPROVE — Status=Closed
  - DEC-ADWM-006: EX-1-010 cylinder canonical-band audit self-APPROVE — Status=Closed
- S-003l Session record also created in Sessions DB with Status=Closed.
  Homepage snapshot (heading + callout + 5-row table) updated from
  2026-04-17 state to 2026-04-19 state.
- **Re-closure 2026-04-20** (v6.1 cutover): DEC-V61-001 mirrored to
  Decisions DB at [page 348c6894…b6aef](https://www.notion.so/348c68942bed8192b936f9fe2cbb6aef)
  via MCP (Notion MCP back online). All 7 local decision frontmatters
  now carry `notion_sync_status: synced <date> (<DB url>)`.

---

## ~~Q-new: Whitelist B-class gold-value remediation (5 cases)~~ — PARTIALLY CLOSED 2026-04-20

**Closure**: Kogami approved 3 of 5 cases (4/6/8 accepted; 9/10 held pending literature re-source). Pre-flight audit re-verification caught a Case 10 miscalculation (actual Chaivat=9.4 not 7.2) → de-escalated Case 10 from edit to HOLD. PR #6 merged `912b2ce1`. DEC-V61-006.

<details><summary>Historical record (for trace)</summary>

- **Source**: `.planning/gates/Q-new_whitelist_remediation.md` (full rationale + per-case audit evidence)
- **Filed**: 2026-04-20T20:55 by claude-opus47-app under handoff §7 stop rule #3 ("触 knowledge/whitelist.yaml reference_values 必须走 gate")
- **Upstream**: DEC-V61-004 (C1+C2 infra fixes) · DEC-V61-005 (A-class metadata)
- **Blocking class**: Hard floor #3 — `knowledge/whitelist.yaml` `reference_values` + tolerance edits required (禁区 #3)
- **Summary**: 5 cases have gold values that appear inconsistent with their stated reference literature per `docs/whitelist_audit.md` §5.2 — Turbulent Flat Plate (Re_x=25k is laminar, needs Blasius), DHC Ra=1e10 (Nu=30 vs literature 120-325), Plane Channel (u+@y+=30 = 14.5 vs Moser 13.5), Impinging Jet (Nu@r/d=0 = 25 vs Behnad ~115), Rayleigh-Bénard Ra=1e6 (Nu=10.5 vs Chaivat 7.2).
- **Decisions landed** (DEC-V61-006):
  - Case 4: **A** — Blasius laminar substitution
  - Case 6: **P-2** — Ra 1e10→1e6, Nu 30→8.8 (de Vahl Davis 1983); **Q-1 closed by same edit**
  - Case 8: **A** — u+@y+=30: 14.5→13.5 (Moser log-law)
  - Case 9: **C** — HOLD, Behnad 2013 re-read pending (audit 4-5× discrepancy too large to edit blind)
  - Case 10: **C** — HOLD, Chaivat 2006 re-read pending (audit miscalc caught pre-flight; current 10.5 within 15% tolerance)

</details>

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
Updated: 2026-04-20 by claude-opus47-app (v6.1 Sole Primary Driver;
post v6.1 cutover landing + Q-3 re-closure after MCP restoration)
Updated: 2026-04-20 by claude-opus47-app (Path-B election per
DEC-V61-002 — Q-1/Q-2 reclassified as Phase-5 blockers, not Phase-0..4
blockers; added interaction-note to header)
Updated: 2026-04-20 by claude-opus47-app (post Phase 1..4 landing per
DEC-V61-003 — Case Editor + Decisions Queue + Run Monitor + Dashboard
now live on feat/ui-mvp-phase-1-to-4; Q-1/Q-2 remain the sole
blockers for Phase 5 Audit Package Builder critical path)
Updated: 2026-04-20 by claude-opus47-app (C-class infra + A-class
metadata landed per DEC-V61-004/005; Q-new filed for B-class gold
remediation 5-case package — subsumes Q-1; STOP until Kogami decision)
Updated: 2026-04-20 by claude-opus47-app (Q-new Kogami-approved 3 of
5 cases — PR #6 merged 912b2ce1 per DEC-V61-006; Q-1 + Q-new PARTIALLY
CLOSED; only Q-2 R-A-relabel remains open; Cases 9+10 queued for
future literature re-source → potential DEC-V61-007)
