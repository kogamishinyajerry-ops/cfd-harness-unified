---
decision_id: DEC-V61-083 (DRAFT — pending Opus Gate Session N+1)
title: IJ Behnia 1999 re-anchor + gold_value approval (CLASS-3, Opus-Gate-N+1)
status: DRAFT_PENDING_OPUS_GATE_N_PLUS_1
authored_by: Claude Code Opus 4.7 (1M context · Session B v2 NARROW external-gate-blocked lane Track 2)
authored_at: 2026-04-26
authored_under: Session B v2 NARROW · Track 2 evidence preparation
parent_dec: DEC-V61-080
parent_authority_verdict: AUTH-V61-080-2026-04-26
authority_class: 3
autonomous_governance: false                # CLASS-3 explicitly forbids autonomous landing
external_gate_self_estimated_pass_rate: n/a # not Claude Code's call
notion_sync_status: queue-only synced 2026-04-26 (https://notion.so/34ec68942bed8177ac78c6e32255608c)  # DRAFT/Proposed page for queue visibility ONLY; gold-value re-anchor body still TBD-marked. Full sync (Status=Accepted, values filled) deferred until Opus Gate N+1 approval.
codex_tool_report_path: null
risk_flags:
  - executable_smoke_test
  - solver_stability_on_novel_geometry
  - gold_value_provenance_fictional
  - stored_value_no_external_anchor

evidence_package: docs/case_documentation/impinging_jet/_research_notes/2026-04-26_n1_anchor_evidence.md
opus_gate_session_id: TBD-CFDJerry-N+1
opus_gate_verdict: TBD
---

# DEC-V61-083 (DRAFT) · IJ Behnia 1999 Re-Anchor

> **THIS IS A DRAFT.** Per AUTH-V61-080-2026-04-26 §2 Case C and §3,
> Claude Code is **forbidden** from editing
> `knowledge/gold_standards/impinging_jet.yaml` `gold_value` / `tolerance`
> / `source` / `literature_doi` until Opus Gate Session N+1 APPROVEs
> the new anchor + value + tolerance.
>
> This draft is the **destination form** for the gate's approved values.
> The evidence package backing this draft is at
> `docs/case_documentation/impinging_jet/_research_notes/2026-04-26_n1_anchor_evidence.md`.

## Why

DOI integrity audit (DEC-V61-080 follow-on) found:

- Stored `literature_doi: 10.1016/j.ijheatfluidflow.2013.03.003` resolves
  to Rao et al. 2013 LES turbines paper — **completely unrelated**
- Stored `source: "Cooper 1984 / Behnad et al. 2013"` → "Behnad 2013"
  is unverifiable; canonical Behnia paper is **1999 IJHFF Vol 20(1)**, not 2013
- Pre-DEC YAML self-comment notes 4-5× discrepancy: stored Nu(r/d=0)=25
  vs Behnia 1999 reported peak ~110-130 at typical configurations

## Decision (TBD — Opus Gate to fill)

```yaml
# WHEN OPUS GATE N+1 APPROVES, FILL ALL TBDs BELOW:

knowledge/gold_standards/impinging_jet.yaml:
  source: TBD-OPUS-GATE-N+1
  literature_doi: TBD-OPUS-GATE-N+1
  reference_values:
    - r_over_d: 0.0
      Nu: TBD-OPUS-GATE-N+1
      description: TBD
    - r_over_d: 1.0
      Nu: TBD-OPUS-GATE-N+1
      description: TBD
  tolerance: TBD-OPUS-GATE-N+1
  source_integrity:                  # NEW field per P-12 escalation (P4 KOM input)
    last_doi_check_date: 2026-04-26
    last_doi_check_status: VERIFIED
    expected_first_author_lastname: TBD
    expected_year: TBD
    expected_journal_keyword: TBD
```

## Substantive content (Opus Gate Session N+1 must produce)

The gate session must, at minimum:

1. Verify Behnia 1999 IJHFF Vol 20(1) directly; report Nu(r/d=0) and
   Nu(r/d=1.0) values at (Re=10000, h/d=2) — or at the nearest
   configuration the paper covers, with extrapolation method documented
2. Adjudicate the 4-hypothesis question from evidence package §4
   (different non-dim convention / different Re definition / stored 25
   from a different paper / confined vs unconfined)
3. Choose between:
   - **Path A**: Single Behnia 1999 anchor + new gold values + new tolerance
   - **Path B**: Multi-source bracket (Behnia 1999 + Cooper companion +
     others) → gold value as range + widened tolerance
   - **Path C**: TBD-GOV1 hold pending P4 KOM `source_integrity`
     field ratification (preserves stored 25 as historical)
   - **Path D**: Defer to P4 KOM and re-anchor as part of schema
     migration (CLASS-4)
4. If choice is A or B, also approve corresponding edits to
   `docs/case_documentation/impinging_jet/{README.md, citations.bib,
   failure_notes.md}` for consistency

## What this draft DEC explicitly does NOT do

- ❌ Does NOT modify `knowledge/gold_standards/impinging_jet.yaml`
  (forbidden by AUTH §3)
- ❌ Does NOT propose specific Nu values (Opus Gate authority per AUTH §7)
- ❌ Does NOT modify any other case
- ❌ Does NOT update DOI integrity audit residual count (will update on
  promotion to Accepted)

## Promotion path

1. CFDJerry triggers Opus Gate Session N+1 with prompt structure per
   evidence package §7
2. Gate session output → frontmatter `opus_gate_verdict`
3. If APPROVE_WITH_VALUES → fill TBD markers, move file to
   `.planning/decisions/2026-04-26_v61_083_ij_re_anchor.md` (drop
   `_DRAFT` suffix), apply edits to `knowledge/**`, commit, sync Notion
4. If CHANGES_REQUIRED → loop with revised draft
5. If TBD-GOV1-HOLD → leave stored values; close DEC as Status=Closed
   with verdict noted; await P4 KOM ratification
6. If DEFER_TO_P4_KOM → close DEC as Status=Superseded; pending becomes
   P4 deliverable

## Source

- Evidence: `docs/case_documentation/impinging_jet/_research_notes/2026-04-26_n1_anchor_evidence.md`
- Parent: `.planning/decisions/2026-04-26_v61_080_gov1_gold_case_enrichment.md`
- Authority: `.planning/audit_evidence/2026-04-26_v61_080_v2_authority_gate_verdict.md` §2 Case C
