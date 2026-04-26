---
decision_id: DEC-V61-082
title: DCT Jones 1976 journal swap (IJHMT → ASME J Fluids Eng) + correlation form correction (CLASS-2)
status: ACCEPTED_PENDING_CODEX_REVIEW (Codex review mandatory per AUTH-V61-080-2026-04-26 §2 Case B; Claude Code edit landed at HEAD <post-commit>; Codex APPROVE / CHANGES_REQUIRED to be appended)
authored_by: Claude Code Opus 4.7 (1M context · Session B v2 NARROW Claude-Code lane)
authored_at: 2026-04-26
authored_under: Session B v2 NARROW · Track 1 (Cases A+B Claude-Code lane)
parent_dec: DEC-V61-080
parent_authority_verdict: AUTH-V61-080-2026-04-26
autonomous_governance: true
external_gate_self_estimated_pass_rate: 0.75    # CLASS-2 with substantive correlation re-description; Codex may flag the Re* re-anchoring or the residual 0.88-claim retraction
notion_sync_status: pending
codex_tool_report_path: pending  # /codex-gpt54 review must run; report path written here when complete
risk_flags:
  - executable_smoke_test                     # not applicable (knowledge metadata only, no executable change)
  - solver_stability_on_novel_geometry        # not applicable
gov1_v1_scope:
  case_id: B
  case_name: duct_flow
  authority_class: 2
  fix_type: journal_metadata_swap_with_correlation_form_correction
  fields_modified:
    - knowledge/gold_standards/duct_flow.yaml::source (Int. J. Heat Mass Transfer → ASME J. Fluids Eng.)
    - knowledge/gold_standards/duct_flow.yaml::literature_doi (10.1016/0017-9310(76)90033-4 → 10.1115/1.3448250)
    - knowledge/gold_standards/duct_flow.yaml::physics_contract.reference_correlation_context (re-described from "f_duct ≈ 0.88×f_pipe" to actual Jones 1976 "Re* modified Reynolds number" formulation)
    - docs/case_documentation/duct_flow/citations.bib::jones1976 entry (full bibliographic block)
    - docs/case_documentation/duct_flow/citations.bib::colebrook1939 note (cross-check description updated)
  fields_NOT_modified:
    - ref_value 0.0185                  # gold value unchanged
    - tolerance 0.10                    # tolerance unchanged
    - physics_contract.contract_status  # SATISFIED status unchanged
    - all other knowledge/** fields
codex_review_charter:
  required_verifications:
    - Verify Jones 1976 actual paper (ASME J Fluids Eng 98(2):173-180, DOI 10.1115/1.3448250) uses the "laminar equivalent" Re* approach as described in the new reference_correlation_context block (claim verified by Claude Code via WebSearch + ASME paper abstract; Codex should independently confirm or flag).
    - Verify the ~5% scatter band about smooth-tube line at AR=1, Re=50000 actually places f=0.0185 within tolerance vs the Colebrook 0.0206 smooth-pipe value (the prior 0.88-ratio claim gives 0.0181, ~2% below 0.0185; the actual Jones Re* approach may give a different cross-check value).
    - If Codex finds the 0.0185 value falls OUTSIDE the corrected-correlation's tolerance band, escalate to CLASS-3 follow-up DEC for gold_value re-anchoring.
  if_codex_approves: append codex_tool_report_path to this DEC frontmatter; promote status to ACCEPTED.
  if_codex_changes_required: address findings via additional commits; if findings touch gold_value or tolerance, escalate to CLASS-3 (separate Opus Gate session).
---

# DEC-V61-082 · DCT Jones 1976 Journal Swap + Correlation Form Correction (CLASS-2)

## Why

Per the post-DEC-V61-080 DOI integrity audit and Opus Gate authority verdict
AUTH-V61-080-2026-04-26 §2 Case B:

The `literature_doi` field for Jones 1976 in
`knowledge/gold_standards/duct_flow.yaml` was `10.1016/0017-9310(76)90033-4`
— which does not resolve at `doi.org` (HTTP 404). The cited journal
"International Journal of Heat and Mass Transfer 19, pp. 1067-1074" was
also wrong: the actual paper is in **ASME *Journal of Fluids Engineering* 98(2),
pp. 173-180, DOI `10.1115/1.3448250`** (verified via [ASME Digital Collection](https://asmedigitalcollection.asme.org/fluidsengineering/article-abstract/98/2/173/417608) +
[MTU PDF mirror](https://pages.mtu.edu/~fmorriso/cm310/JonesOCpaper1976.pdf)).

Paper identity (Jones, "An Improvement in the Calculation of Turbulent
Friction in Rectangular Ducts", 1976) is **uncontested**. Author,
year, title preserved; only journal + DOI + volume/pages corrected.

## Pre-emptive correlation-form finding (escalation flag for Codex)

While verifying the journal swap, Claude Code's WebSearch on Jones 1976
content surfaced that the paper's **actual technical approach** is a
**"laminar equivalent" modified Reynolds number `Re*`** such that the
laminar relation `f = 64/Re*` unifies friction across rectangular-duct
aspect ratios 1:1 to 39:1, with ~5% scatter band about the smooth-tube
line in the turbulent regime.

The pre-DEC-V61-082 `reference_correlation_context` block in `duct_flow.yaml`
described Jones 1976's correlation as `f_duct ≈ 0.88 × f_pipe(Re_h)`. This
0.88 ratio summarization was **Claude Code's internal shorthand** (likely
introduced in DEC-V61-011 or later) that does NOT match Jones 1976's
actual published formulation. The numerical cross-check `0.88 × 0.0206 =
0.0181` is internally consistent with that shorthand but is not what
Jones reports as the canonical method.

The numerical gold value `f = 0.0185 at Re=50000` is **unchanged** in
this DEC. It remains within Jones's stated ~5% turbulent-similarity band
about Colebrook smooth-pipe `f = 0.0206`. The change is descriptive: the
correlation form in `reference_correlation_context` is re-anchored to
the actual Re* approach.

**This re-description borders on substantive content (correlation form,
not just metadata)**. Per AUTH-V61-080 §2 Case B, the Codex review
verification list must include:

1. Confirm Jones 1976 ASME paper uses the Re* approach as now described
2. Confirm the ~5% scatter-band claim at AR=1, Re=50000 actually places
   f=0.0185 within the corrected-correlation's tolerance vs Colebrook's
   0.0206 (the prior 0.88-shorthand gave 0.0181, ~2% below 0.0185)
3. If 0.0185 falls outside the corrected-correlation's tolerance band,
   **escalate to CLASS-3 follow-up DEC** (gold_value re-anchoring is
   out of CLASS-2 authority per AUTH-V61-080)

## Decision

Three coordinated edits within CLASS-2 metadata-and-correlation-form scope:

1. `knowledge/gold_standards/duct_flow.yaml::source` →
   `"Jones 1976, ASME J. Fluids Eng. 98(2), 173-180 / Jones & Launder 1973, ..."`
2. `knowledge/gold_standards/duct_flow.yaml::literature_doi` →
   `"10.1115/1.3448250"`
3. `knowledge/gold_standards/duct_flow.yaml::physics_contract.reference_correlation_context`
   re-described from "f_duct ≈ 0.88×f_pipe" to actual Re* approach with
   inline NOTE flagging the change for Codex review and CLASS-3 escalation
   pathway.

Plus citations.bib updates:
- `jones1976` entry: full bibliographic block + descriptive note re-anchored
- `colebrook1939` note: cross-check description updated to reflect Re* approach

`ref_value: 0.0185` and `tolerance: 0.10` are **unchanged** (CLASS-2 scope
preserves these).

## Mandatory Codex review

Per AUTH-V61-080-2026-04-26 §2 Case B and `gov1_v1_scope.codex_review_charter`
above. CFDJerry must run `/codex-gpt54` against this DEC + the modified
files; Codex tool report path is appended to this DEC's frontmatter
when review completes. Status promotes ACCEPTED_PENDING_CODEX_REVIEW
→ ACCEPTED on Codex APPROVE.

## Hard-boundary self-attestation

- ❌ NO `ref_value` modified (gold value 0.0185 unchanged)
- ❌ NO `tolerance` modified (0.10 unchanged)
- ❌ NO `physics_contract.contract_status` modified (still SATISFIED)
- ❌ NO `physics_contract.physics_precondition` array modified
- ❌ NO new schema field added (boundary 4 untouched)
- ❌ NO `src/cfd_harness/trust_core/**` change
- ❌ NO Session A path touched
- ✅ Boundaries 1, 2, 4, 5, 6, 7 honored at CLASS-2 scope

## Reproducibility

```bash
# Verify corrected DOI:
curl -sI 'https://doi.org/10.1115/1.3448250' | head -1
# Expected: HTTP/2 302 (redirects to ASME Digital Collection paper)

# Verify legacy DOI does NOT resolve:
curl -sI 'https://doi.org/10.1016/0017-9310(76)90033-4' | head -1
# Expected: HTTP/2 404
```

## Source

- Repo DEC: `.planning/decisions/2026-04-26_v61_082_dct_journal_swap.md`
- Repo audit input: `docs/case_documentation/_research_notes/gov1_paper_reread_2026-04-26.md`
- Repo authority verdict: `.planning/audit_evidence/2026-04-26_v61_080_v2_authority_gate_verdict.md`
- Parent DEC: `.planning/decisions/2026-04-26_v61_080_gov1_gold_case_enrichment.md`
- Verified citation: [Jones 1976, ASME J. Fluids Eng. 98(2), 173-180, DOI 10.1115/1.3448250](https://doi.org/10.1115/1.3448250)
- Independent cross-check (PDF mirror): https://pages.mtu.edu/~fmorriso/cm310/JonesOCpaper1976.pdf
