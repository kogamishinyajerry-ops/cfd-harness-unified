---
decision_id: DEC-V61-084 (DRAFT — pending Opus Gate Session N+2)
title: RBC Chaivat→Niemela/Globe-Dropkin re-anchor + gold_value approval (CLASS-3, Opus-Gate-N+2)
status: DRAFT_PENDING_OPUS_GATE_N_PLUS_2
authored_by: Claude Code Opus 4.7 (1M context · Session B v2 NARROW external-gate-blocked lane Track 2)
authored_at: 2026-04-26
authored_under: Session B v2 NARROW · Track 2 evidence preparation
parent_dec: DEC-V61-080
parent_authority_verdict: AUTH-V61-080-2026-04-26
authority_class: 3
autonomous_governance: false                # CLASS-3 explicitly forbids autonomous landing
external_gate_self_estimated_pass_rate: n/a # not Claude Code's call
notion_sync_status: pending  # do not sync until Opus Gate N+2 approves
codex_tool_report_path: null
risk_flags:
  - executable_smoke_test
  - solver_stability_on_novel_geometry
  - gold_value_provenance_fictional
  - author_name_unfindable_in_any_database

evidence_package: docs/case_documentation/rayleigh_benard_convection/_research_notes/2026-04-26_n2_anchor_evidence.md
opus_gate_session_id: TBD-CFDJerry-N+2
opus_gate_verdict: TBD
---

# DEC-V61-084 (DRAFT) · RBC Chaivat → Multi-Source Re-Anchor

> **THIS IS A DRAFT.** Per AUTH-V61-080-2026-04-26 §2 Case D and §3,
> Claude Code is **forbidden** from editing
> `knowledge/gold_standards/rayleigh_benard_convection.yaml` `gold_value`
> / `tolerance` / `source` / `literature_doi` until Opus Gate Session
> N+2 APPROVEs the new anchor + value + tolerance.

## Why

DOI integrity audit (DEC-V61-080 follow-on) found:

- Stored `literature_doi: 10.1016/j.ijheatmasstransfer.2005.07.039`
  resolves to Meyer et al. 2006 jet array cooling paper — **completely
  unrelated** to RBC
- Stored `source: "Chaivat et al. 2006"` — **author "Chaivat" not
  findable** in Semantic Scholar / Google Scholar / Crossref / IJHMT
  archives. Provenance is **fictional or mistranscribed**.
- The audit-recomputed "Chaivat correlation Nu = 0.229·Ra^0.269" → 9.4
  at Ra=10⁶ is internally consistent with stored 10.5 within tolerance,
  but the correlation form itself cannot be located in any retrievable
  paper — strongly suggesting reverse-engineering from harness output

## Higher severity than Case C

Case D is substantively higher-risk than Case C (IJ) because:
- IJ has wrong DOI but author Behnia 1999 IS findable + verifiable
- RBC has wrong DOI AND fictional author, AND the correlation that
  reproduces stored 10.5 is itself unfindable
- Stored Nu=10.5 differs from BOTH verified candidate primaries
  (Niemela 2000: 8.87, Globe-Dropkin 1959: 6.73) — so the stored value
  may have **no external literature anchor at all**

## Decision (TBD — Opus Gate to fill)

```yaml
# WHEN OPUS GATE N+2 APPROVES, FILL ALL TBDs BELOW:

knowledge/gold_standards/rayleigh_benard_convection.yaml:
  source: TBD-OPUS-GATE-N+2
  literature_doi: TBD-OPUS-GATE-N+2
  observables:
    - name: nusselt_number
      ref_value: TBD-OPUS-GATE-N+2  # 候选：~8.87 (Niemela 2000) / ~6.73 (Globe-Dropkin 1959) / ~8.0±1.5 (multi-source bracket) / 10.5 PROVISIONAL_HOLD
      tolerance: { mode: relative, value: TBD-OPUS-GATE-N+2 }
  source_integrity:                  # NEW field per P-12 escalation
    last_doi_check_date: 2026-04-26
    last_doi_check_status: VERIFIED
    chaivat_2006_status: NOT_LOCATABLE_IN_ANY_DATABASE
    expected_first_author_lastname: TBD
    expected_year: TBD
    expected_journal_keyword: TBD
```

## Substantive content (Opus Gate Session N+2 must produce)

1. Verify candidate correlations:
   - Niemela 2000 *Nature* 404:837-840: `Nu = 0.124·Ra^0.309` → at Ra=10⁶ gives **8.87** (Claude Code recompute; audit's claim of 5.5 was arithmetic error per evidence package §3 Candidate B)
   - Globe-Dropkin 1959 *J Heat Transfer* 81(1):24-28: `Nu = 0.069·Ra^(1/3)·Pr^0.074` → at Ra=10⁶, Pr=0.71 gives **6.73**
2. Adjudicate the 3-hypothesis question from evidence package §4:
   - (1) Chaivat is misspelled; correct paper findable
   - (2) Chaivat is fictional / Phase 0 placeholder
   - (3) Chaivat is in non-indexed publication
3. Choose between:
   - **Path A**: Single Niemela 2000 primary anchor + Nu_gold ≈ 8.87 + tolerance ~0.10-0.15
   - **Path B**: Single Globe-Dropkin 1959 primary anchor + Nu_gold ≈ 6.73 + tolerance ~0.10-0.15
   - **Path C**: Multi-source bracket (Niemela primary + Globe-Dropkin secondary) + Nu_gold = 8.0 ± 1.5 + tolerance ~0.20-0.25
   - **Path D**: TBD-GOV1 hold; preserve stored 10.5 + widen tolerance to 25-30%; explicit `status: PROVISIONAL` + `valid_regime` markers
   - **Path E**: Defer to P4 KOM (CLASS-4)
4. If choice is A/B/C, also approve corresponding edits to
   `docs/case_documentation/rayleigh_benard_convection/{README.md, citations.bib, failure_notes.md}` for consistency

## What this draft DEC explicitly does NOT do

- ❌ Does NOT modify `knowledge/gold_standards/rayleigh_benard_convection.yaml`
- ❌ Does NOT propose specific Nu values (Opus Gate authority)
- ❌ Does NOT search exhaustively for the misspelled "Chaivat" — Opus
  Gate may exhaust this hypothesis if substantive

## Promotion path

(parallel to DEC-V61-083 promotion path; see that draft)

## Source

- Evidence: `docs/case_documentation/rayleigh_benard_convection/_research_notes/2026-04-26_n2_anchor_evidence.md`
- Parent: `.planning/decisions/2026-04-26_v61_080_gov1_gold_case_enrichment.md`
- Authority: `.planning/audit_evidence/2026-04-26_v61_080_v2_authority_gate_verdict.md` §2 Case D
