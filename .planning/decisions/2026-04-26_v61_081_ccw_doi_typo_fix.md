---
decision_id: DEC-V61-081
title: CCW Williamson 1996 DOI typo fix (.002421 → .002401, CLASS-1)
status: ACCEPTED (autonomous_governance under Opus Gate authority verdict AUTH-V61-080-2026-04-26 §2 Case A CLASS-1)
authored_by: Claude Code Opus 4.7 (1M context · Session B v2 NARROW Claude-Code lane)
authored_at: 2026-04-26
authored_under: Session B v2 NARROW · Track 1 (Cases A+B Claude-Code lane)
parent_dec: DEC-V61-080
parent_authority_verdict: AUTH-V61-080-2026-04-26
autonomous_governance: true
external_gate_self_estimated_pass_rate: 0.99    # CLASS-1 trivial typo, no Codex required, no gold value change
notion_sync_status: pending
codex_tool_report_path: null  # CLASS-1: no Codex review required per authority verdict §2
risk_flags: []
gov1_v1_scope:
  case_id: A
  case_name: circular_cylinder_wake
  authority_class: 1
  fix_type: doi_typo_correction
  fields_modified:
    - knowledge/gold_standards/circular_cylinder_wake.yaml::literature_doi (4 occurrences, replace_all)
    - docs/case_documentation/circular_cylinder_wake/citations.bib::williamson1996.doi (1 occurrence)
  fields_NOT_modified:
    - source                  # Williamson 1996 attribution unchanged
    - reference_values        # all gold values (St=0.164, cd=1.33, cl_rms=0.048, deficit profile) unchanged
    - tolerance               # all tolerance values unchanged
    - any other knowledge/** field
---

# DEC-V61-081 · CCW Williamson 1996 DOI Typo Fix (CLASS-1)

## Why

Per the post-DEC-V61-080 DOI integrity audit (`docs/case_documentation/_research_notes/gov1_paper_reread_2026-04-26.md`)
and Opus Gate authority verdict AUTH-V61-080-2026-04-26 §2 Case A:

The `literature_doi` field for the Williamson 1996 paper in
`knowledge/gold_standards/circular_cylinder_wake.yaml` was
`10.1146/annurev.fl.28.010196.002421` — which does not resolve at
`doi.org` (HTTP 404). The correct DOI for Williamson, "Vortex Dynamics
in the Cylinder Wake", *Annual Review of Fluid Mechanics* 28:477-539
(1996) is `10.1146/annurev.fl.28.010196.002401` (verified via Annual
Reviews + Semantic Scholar + ADS Harvard `1996AnRFM..28..477W`).

The error is a four-character typo (`421` → `401`) in the last segment.
Paper identity (author, year, title, volume, pages, journal) is
**uncontested** and unchanged. No gold value changes; no tolerance
changes; no `source` field change.

## Decision

Replace all 4 occurrences of `10.1146/annurev.fl.28.010196.002421` in
`knowledge/gold_standards/circular_cylinder_wake.yaml` (one per
observable block: `strouhal_number`, `cd_mean`, `cl_rms`,
`u_mean_centerline`) and 1 occurrence in
`docs/case_documentation/circular_cylinder_wake/citations.bib` with
the verified DOI `10.1146/annurev.fl.28.010196.002401`.

Authority class CLASS-1 per AUTH-V61-080-2026-04-26 §2:
> "Single-paper, single-author, single-year, single-title, single-
> volume/page identity is uncontested. Four-character typo in
> `literature_doi` only; no `gold_value`, no `tolerance`, no `source`
> field touched. Does not touch Pivot Charter §4 invariant 1 (no
> truth-source change) nor invariant 4 (no schema/field-format change).
> Defining example of CLASS-1."

No Codex tool report required (CLASS-1).

## Impact

- 5 lines changed across 2 files (4 in YAML `replace_all`, 1 in `citations.bib`)
- Zero comparator behavior change (DOI is metadata; not read by any extractor or gate)
- Citation integrity: CCW row in DOI integrity audit moves from ⚠️ LOW (typo) to ✅ verified clean
- DOI integrity audit residual count: 3 of 10 (was 4 of 10 active issues)

## Alternatives

- (a) Defer to Session B v2 BROAD bundling all 4 fixes — REJECTED, authority verdict mandates SPLIT execution
- (b) Bundle into Case B (DCT) commit — REJECTED, atomic per-case commits per V61-058 precedent
- (c) Wait for P4 KOM source_integrity field — REJECTED, AUTH §2 Case A explicitly classifies as CLASS-1, not CLASS-4

## Hard-boundary self-attestation

- ❌ NO `gold_value` / `reference_values` modified
- ❌ NO `tolerance` modified
- ❌ NO `source` field modified (paper attribution unchanged)
- ❌ NO `physics_contract` block modified
- ❌ NO new schema field added (boundary 4 untouched — same `literature_doi` field, just corrected value)
- ❌ NO `src/cfd_harness/trust_core/**` change
- ❌ NO Session A path touched
- ❌ NO P4 KOM-blocking change (boundary 5 untouched)

Hard boundaries 1, 2, 4, 5, 6, 7 honored. Only `knowledge/**` write touches a single value-string in an existing field.

## Reproducibility

```bash
# Verify correct DOI resolves:
curl -sI 'https://doi.org/10.1146/annurev.fl.28.010196.002401' | head -1
# Expected: HTTP/2 302 (redirects to Annual Reviews paper)

# Verify wrong DOI does NOT resolve:
curl -sI 'https://doi.org/10.1146/annurev.fl.28.010196.002421' | head -1
# Expected: HTTP/2 404
```

## Source

- Repo DEC: `.planning/decisions/2026-04-26_v61_081_ccw_doi_typo_fix.md`
- Repo audit input: `docs/case_documentation/_research_notes/gov1_paper_reread_2026-04-26.md`
- Repo authority verdict: `.planning/audit_evidence/2026-04-26_v61_080_v2_authority_gate_verdict.md`
- Parent DEC: `.planning/decisions/2026-04-26_v61_080_gov1_gold_case_enrichment.md`

Verified citation source: [Williamson 1996, *Annual Reviews of Fluid Mechanics* 28:477-539, DOI 10.1146/annurev.fl.28.010196.002401](https://doi.org/10.1146/annurev.fl.28.010196.002401)
