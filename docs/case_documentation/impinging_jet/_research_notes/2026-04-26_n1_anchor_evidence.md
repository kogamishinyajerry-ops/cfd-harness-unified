# IJ Anchor Evidence Package · Opus Gate N+1 Input

> Authored 2026-04-26 by Claude Code Opus 4.7 under DEC-V61-080 / AUTH-V61-080-2026-04-26 §3 Case C (CLASS-3 evidence draft).
>
> **Scope**: pre-gate evidence + candidate anchor table for Opus Gate Session N+1 (IJ anchor approval). Claude Code MAY NOT edit `knowledge/gold_standards/impinging_jet.yaml` `gold_value` / `tolerance` / `source` / `literature_doi` until this gate APPROVEs — this file is *input* to that gate, not a substitute.

## §1 · Configuration under audit

The pre-DEC IJ gold YAML claims:

| Field | Stored value |
|---|---|
| `case_id` | `impinging_jet` |
| Re | 10000 |
| h/d | 2.0 (nozzle-to-plate distance / nozzle diameter) |
| Geometry intent | axisymmetric heated impinging jet (adapter generates 2D planar slice — separate hazard FM-IJ-1) |
| Solver | simpleFoam + k-ε (RAS) |
| `source` | "Cooper 1984 / Behnad et al. 2013" |
| `literature_doi` | `10.1016/j.ijheatfluidflow.2013.03.003` |
| `nusselt_number` at r/d=0 | **25.0** (PROVISIONAL per Gate Q-new Case 9 HOLD) |
| `nusselt_number` at r/d=1.0 | **12.0** (PROVISIONAL) |
| `tolerance` | 0.15 (15%) |

## §2 · Citation integrity findings (verified)

**Stored DOI is broken**: `10.1016/j.ijheatfluidflow.2013.03.003` resolves
via Semantic Scholar to:

> **Rao, V. N. and Tucker, P. and Jefferson-Loveday, R. and Coull, J.**
> (2013). "Large eddy simulations in low-pressure turbines: Effect of
> wakes at elevated free-stream turbulence". *International Journal of
> Heat and Fluid Flow* 43, 85-95.

This is a **completely unrelated paper** (LES of LP turbines, not impinging
jets). The "Behnad et al. 2013" attribution is unverifiable.

## §3 · Candidate primary anchors

### Candidate A — Behnia, Parneix, Shabany, Durbin 1999 IJHFF Vol 20(1)

**Identity verified** (Semantic Scholar API):
- Title: *"Numerical study of turbulent heat transfer in confined and
  unconfined impinging jets"*
- Authors: M. Behnia, S. Parneix, Y. Shabany, P. Durbin
- Journal: **International Journal of Heat and Fluid Flow** Vol **20**(1), pp. 1–9 (Feb 1999)
- DOI: `10.1016/S0142-727X(98)10040-1`
- Type: numerical (v²−f model elliptic relaxation)

**Configuration coverage** (per search results + abstract): "range of
jet Reynolds numbers and jet-to-target distances" — exact (Re, h/d)
table is paywalled. The audit comment in the pre-DEC YAML reports:
> "Behnad 2013 ~110-130" Nu at stagnation — likely transcription
> from Behnia 1999 or a downstream paper citing it.

**Numerical anchor at (Re=10000, h/d=2)**: TBD-OPUS-GATE — Opus Gate
Session N+1 must read primary paper Fig./Table for Re=10000, h/d=2
(or nearest configuration) and report Nu(r/d=0) + Nu(r/d=1.0) +
configuration confidence.

**Pros**:
- Numerical study with full (Nu vs r/d) profile likely tabulated
- Known canonical reference in modern impinging-jet literature
- Reasonable match to adapter's RANS configuration (v²−f or kOmegaSST
  is closer to v²−f than legacy k-ε)

**Cons**:
- Numerical, not experimental — values are model-dependent
- v²−f vs adapter's k-ε creates a model-mismatch hazard; whichever
  Behnia variant we anchor against may not match adapter physics

### Candidate B — Cooper, Jackson, Launder, Liao 1993 IJHMT Vol 36(10)

**Identity to verify** (audit listed as "Cooper 1984"; my GOV-1 v0.5
citations.bib used Cooper 1993):
- Title: "Impinging jet studies for turbulence model assessment - I.
  Flow-field experiments"
- Authors: D. Cooper, D. C. Jackson, B. E. Launder, G. X. Liao
- Journal: International Journal of Heat and Mass Transfer 36(10),
  pp. 2675-2684 (1993)
- DOI: `10.1016/S0017-9310(05)80204-2` (verify with Opus Gate)
- Type: experimental flow-field (heat transfer in companion paper)

**Configuration coverage**: classic Cooper jet impingement experimental
data series. 1984 was the original conference work; 1993 is the journal
paper. Heat-transfer Nu data may be in a companion paper, not the 1993
flow-field paper.

**Numerical anchor at (Re=10000, h/d=2)**: TBD-OPUS-GATE — Opus Gate
must verify whether Cooper 1993 (or Cooper companion paper) reports
heat-transfer data; if heat-transfer is in a different Cooper paper,
identify and verify that one.

**Pros**:
- Experimental, not model-dependent
- Long-cited canonical baseline

**Cons**:
- 1984 conference vs 1993 journal vs heat-transfer companion paper —
  the actual data source for Nu may be a fourth paper not yet identified
- Experimental Nu values can have higher tolerance than RANS targets

### Candidate C — Baughn 1989 / Baughn & Shimizu 1989

**Identity**: experimental impinging jet heat-transfer reference often
cited alongside Cooper.

- Likely paper: Baughn & Shimizu 1989, *J Heat Transfer* 111(4), 1096–1098

**Configuration coverage**: Re ≈ 23750 in some Baughn papers; the
(Re=10000, h/d=2) configuration may not be a direct Baughn anchor.
TBD-OPUS-GATE.

### Candidate D — Multi-source bracket (recommended pattern, mirrors NACA DEC-V61-058)

Per V61-058 NACA precedent + AUTH-V61-080 §1 finding:

> "V61-058 is precedential for citation-anchor pivots where (a) the
> new anchor is a verified primary-literature source and (b) gold
> values are read out of the new source rather than reverse-engineered
> to fit existing harness behavior."

For IJ at (Re=10000, h/d=2), bracket gold value with:
- **PRIMARY**: Behnia 1999 (numerical, v²−f), Nu(r/d=0) = TBD; Nu(r/d=1.0) = TBD
- **SECONDARY**: Cooper companion paper (experimental), Nu peak at stagnation TBD
- **TOLERANCE**: derived from PRIMARY ± SECONDARY spread + adapter
  k-ε vs v²−f model uncertainty

If PRIMARY and SECONDARY differ by >25%, gold becomes a **range**
rather than a point value, and tolerance widens correspondingly.

## §4 · Audit-flagged 4-5× discrepancy resolution paths

The pre-DEC YAML contains the comment:

> "audit flagged Nu@r/d=0 = 25 vs Behnad 2013 ~110-130, but 4-5×
> discrepancy is too large to edit without reading Behnad et al. 2013
> directly"

Possible explanations Opus Gate must adjudicate:

1. **Different non-dim convention**: Stored Nu=25 may use a different
   reference length or temperature than Behnia 1999. Likely candidates:
   nozzle diameter D_nozzle vs hydraulic L_h; ΔT (T_wall - T_jet) vs
   (T_wall - T_∞).
2. **Different Re definition**: Stored Re=10000 may be at nozzle exit
   vs at impingement plate vs based on max jet velocity. Behnia 1999
   may use a different convention.
3. **Stored 25 is from a different paper entirely**: never properly
   sourced; the "Behnad 2013" attribution is wrong both on year (1999)
   AND on numerical match (~110-130 vs 25).
4. **Stored 25 is from confined-jet configuration**, while Behnia 1999
   reports both confined and unconfined; values differ substantially.

**Opus Gate Session N+1 must adjudicate** between (1)-(4) and approve
either the new anchor + value, or a TBD-GOV1 hold pending P4 KOM
`source_integrity` field ratification.

## §5 · Draft TBD-marked replacement values for Opus Gate consideration

```yaml
# DRAFT — Opus Gate Session N+1 must approve / amend / reject before merge
source: "TBD-OPUS-GATE-N+1 (candidates: Behnia 1999 IJHFF 20(1) / Cooper-companion-1989-or-1993 / multi-source-bracket)"
literature_doi: "TBD-OPUS-GATE-N+1"  # candidate Behnia: 10.1016/S0142-727X(98)10040-1
quantity: nusselt_number
reference_values:
  - r_over_d: 0.0
    Nu: TBD-OPUS-GATE-N+1  # candidate range from Behnia 1999 search: 30-130 depending on configuration + model + Re definition
    description: "stagnation point Nusselt number at r/d=0 (PROVISIONAL pending Opus Gate adjudication)"
  - r_over_d: 1.0
    Nu: TBD-OPUS-GATE-N+1
    description: "off-stagnation Nusselt at r/d=1.0"
tolerance: TBD-OPUS-GATE-N+1  # likely 0.15-0.25 if multi-source bracket; 0.05-0.10 if single primary anchor
source_integrity:
  last_doi_check_date: 2026-04-26
  last_doi_check_status: VERIFIED         # Behnia 1999 DOI 10.1016/S0142-727X(98)10040-1 verified
  expected_first_author_lastname: Behnia  # if Candidate A
  expected_year: 1999                     # if Candidate A
  expected_journal_keyword: "Heat and Fluid Flow"
```

## §6 · What this evidence package does NOT provide

- ❌ Primary Behnia 1999 paper Nu(r/d) profile at Re=10000, h/d=2 — paywalled / behind ScienceDirect access
- ❌ Verification of Cooper 1993 vs Cooper-companion-paper heat-transfer source
- ❌ Adjudication between confined vs unconfined Behnia 1999 configuration
- ❌ Numerical gold value or new tolerance — these are Opus Gate Session N+1's substantive deliverable

## §7 · Recommended Opus Gate Session N+1 prompt structure

CFDJerry, when convening N+1, the prompt should:

1. Provide auditor with this evidence package (`docs/case_documentation/impinging_jet/_research_notes/2026-04-26_n1_anchor_evidence.md`)
2. Provide auditor with primary source access (Behnia 1999 IJHFF Vol 20(1) PDF, or grant institutional credentials)
3. Ask auditor to fill `TBD-OPUS-GATE-N+1` markers in §5 above with verified values
4. Ask auditor to declare which of the 4 hypotheses in §4 explains the stored 25 value
5. Output: APPROVE_WITH_VALUES | CHANGES_REQUIRED | TBD-GOV1-HOLD | DEFER_TO_P4_KOM

The DEC-V61-083 draft (`.planning/decisions/draft/2026-04-26_v61_083_ij_re_anchor.md`)
is paired with this evidence package and is the destination for the
Opus Gate's approved values.

## Sources

- Behnia 1999 identity confirmed via Semantic Scholar API: `https://api.semanticscholar.org/graph/v1/paper/DOI:10.1016/S0142-727X(98)10040-1`
- Audit context: `docs/case_documentation/_research_notes/gov1_paper_reread_2026-04-26.md` §1
- Authority verdict: `.planning/audit_evidence/2026-04-26_v61_080_v2_authority_gate_verdict.md` §2 Case C
