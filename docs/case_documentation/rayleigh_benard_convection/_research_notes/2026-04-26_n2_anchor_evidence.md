# RBC Anchor Evidence Package · Opus Gate N+2 Input

> Authored 2026-04-26 by Claude Code Opus 4.7 under DEC-V61-080 / AUTH-V61-080-2026-04-26 §3 Case D (CLASS-3 evidence draft).
>
> **Scope**: pre-gate evidence + candidate anchor table for Opus Gate Session N+2 (RBC anchor approval). Claude Code MAY NOT edit `knowledge/gold_standards/rayleigh_benard_convection.yaml` `gold_value` / `tolerance` / `source` / `literature_doi` until this gate APPROVEs.

## §1 · Configuration under audit

| Field | Stored value |
|---|---|
| `case_id` | `rayleigh_benard_convection` |
| Ra | 10⁶ |
| Pr | 0.71 (air) |
| AR | 2.0 |
| Solver | buoyantFoam (Boussinesq), laminar (per DEC-V61-005) |
| `source` | "Chaivat et al. 2006" |
| `literature_doi` | `10.1016/j.ijheatmasstransfer.2005.07.039` |
| `nusselt_number` (mean Nu, hot bottom wall) | **10.5** (PROVISIONAL per Gate Q-new Case 10 HOLD) |
| `tolerance` | 0.15 (15%) |

## §2 · Citation integrity findings (verified)

**Stored DOI resolves to unrelated paper**:

> **Meyer, M. and Mudawar, I. and Boyack, C. E. and Hale, C. A.** (2006).
> "Single-phase and two-phase cooling with an array of rectangular jets".
> *International Journal of Heat and Mass Transfer* 49(1), pp. 17-29.

Completely unrelated to Rayleigh-Bénard convection.

**Author "Chaivat" not findable** in:
- Semantic Scholar (multiple query variants)
- Google Scholar (via web search)
- Crossref (via web search)
- Annual Reviews / IJHMT archives

The provenance is **fictional or mistranscribed**. The audit-recomputed
"Chaivat correlation Nu = 0.229·Ra^0.269" → at Ra=10⁶ gives 9.4
(internally consistent with stored 10.5 within 15% tolerance), but the
correlation form itself cannot be located in any retrievable paper.

## §3 · Candidate primary anchors

### Candidate A — Globe & Dropkin 1959 J Heat Transfer 81(1)

**Identity verified** (ASME Digital Collection + WebSearch):
- Title: *"Natural-Convection Heat Transfer in Liquids Confined by Two
  Horizontal Plates and Heated From Below"*
- Authors: S. Globe, D. Dropkin
- Journal: **Journal of Heat Transfer** Vol **81**(1), pp. 24–28 (Feb 1959)
- DOI: `10.1115/1.3680025` (audit found)
- Type: experimental
- Range: Ra ∈ [1.51×10⁵, 6.76×10⁸], Pr ∈ [0.02, 8750]
- Working fluids: water, silicone oils (1.5/50/1000 cSt), mercury

**Correlation form** (per WebSearch + classical textbook references):

> Nu ≈ 0.069 · Ra^(1/3) · Pr^0.074

**Numerical anchor at (Ra=10⁶, Pr=0.71, AR=2)**:
- Ra^(1/3) = (10⁶)^(1/3) = 100
- Pr^0.074 = 0.71^0.074 ≈ 0.975
- **Nu ≈ 0.069 × 100 × 0.975 ≈ 6.73**

**Pros**:
- Verified primary literature; ASME archive accessible
- Matches Pivot Charter §4 inv 1 truth-source criterion
- Wide Ra/Pr coverage including air at moderate Ra
- Long-standing canonical reference

**Cons**:
- Aspect ratio NOT specified in correlation; AR=2 may need a
  separate AR-correction factor
- Correlation is for wide horizontal layers; 2D enclosure ψ
  AR=2 is geometrically intermediate
- Stored Nu=10.5 differs from Globe-Dropkin's 6.73 by ~56% — large
  drift if Globe-Dropkin selected as primary

### Candidate B — Niemela, Skrbek, Sreenivasan, Donnelly 2000 *Nature*

**Identity verified** (Nature.com + ResearchGate + PubMed):
- Title: *"Turbulent convection at very high Rayleigh numbers"*
- Authors: J. J. Niemela, L. Skrbek, K. R. Sreenivasan, R. J. Donnelly
- Journal: **Nature** Vol **404**, pp. 837–840 (April 2000)
- DOI: `10.1038/35009036`
- PubMed: 10786783
- Type: experimental (cryogenic helium gas)
- Range: Ra ∈ [10⁶, 10¹⁷], Pr near 1

**Correlation form** (per Nature paper):

> Nu = 0.124 · Ra^0.309 ± 0.0043

**Numerical anchor at (Ra=10⁶, Pr ≈ 1)**:
- Ra^0.309 = 10^(6 × 0.309) = 10^1.854 ≈ 71.5
- **Nu ≈ 0.124 × 71.5 ≈ 8.87**

**Pros**:
- Verified primary literature in Nature (top-tier)
- Wide Ra coverage starting EXACTLY at Ra=10⁶
- Close to stored 10.5 (drift only ~16%, marginal vs 15% tolerance)
- Valid for Pr ≈ 1 (close to air at 0.71)

**Cons**:
- Working fluid is cryogenic helium, not air; Pr correction may apply
- Authors note it is "between 1/3 and 2/7 laws" — exponent 0.309
  is empirical, not theoretically derived
- "Often cited as Niemela & Sreenivasan 2003" in some literature, but
  the Nature paper is 2000 (audit's "2003" attribution may be a
  different follow-up)

> **Audit's claim of "Nu ≈ 5.5" at Ra=10⁶ for Niemela-Sreenivasan
> appears to be an arithmetic error.** Recompute confirms ~8.87.
> Opus Gate must verify.

### Candidate C — Goldstein & Tokuda 1980 J Heat Transfer

**Identity to verify**:
- Likely citation: R. J. Goldstein, S. Tokuda, "Heat transfer by
  thermal convection at high Rayleigh numbers", *International Journal
  of Heat and Mass Transfer* 23, pp. 738-740 (1980) (TBD-OPUS-GATE)
- Type: experimental

**Correlation form**: TBD-OPUS-GATE.

### Candidate D — Multi-source bracket (recommended, V61-058 NACA precedent)

Mirror NACA DEC-V61-058 multi-source-pivot pattern:
- **PRIMARY**: Niemela 2000 *Nature* — Nu = 0.124·Ra^0.309 → 8.87 at Ra=10⁶
- **SECONDARY** (cross-check at low Ra): Globe-Dropkin 1959 — Nu ≈ 6.73
- **TERTIARY** (Pr correction): Goldstein-Tokuda 1980 (TBD)

If PRIMARY and SECONDARY differ ~30% (Niemela 8.87 vs Globe-Dropkin 6.73),
gold becomes a **range** rather than a point value:

> Nu_gold = 8.0 ± 1.5 (covers Niemela 8.87 and Globe-Dropkin 6.73 within ±20%)

Or stored Nu=10.5 is retained but flagged with explicit `status:
PROVISIONAL` and `valid_regime: { Ra: [1e6, 1e7], Pr_range: [0.6, 1.0] }`
until a single canonical anchor is selected.

## §4 · Why "Chaivat" cannot be found — three hypotheses

Opus Gate Session N+2 must adjudicate which is correct:

1. **Author name misspelled / mistransliterated**. Candidate originals:
   "Chaiwat" (Thai), "Chairat", "Chaiyat", "Chavat" (Russian/Eastern
   European), "Cha Wat" (compound). Without knowing original, cannot
   find paper. **Search exhaustively** by correlation form `0.229·Ra^0.269`
   may find the actual author.

2. **Author name fictional / Phase 0 placeholder**. Pattern documented
   at LDC FM-LDC-1 (Phase 0 synthesized values failed cross-check);
   "Chaivat" may be the same kind of synthesized placeholder that
   survived Phase 0 → DEC-V61-005 cleanup.

3. **Paper is in non-indexed publication**. Conference proceedings,
   regional journal not in Crossref/Scholar, doctoral thesis. Less
   likely given the prominence of the result; classical Nu correlations
   are usually heavily indexed.

If hypothesis 2 is correct, the stored Nu=10.5 has **no external
literature anchor** and the entire DEC entry should be re-anchored
from scratch.

## §5 · Draft TBD-marked replacement values for Opus Gate consideration

```yaml
# DRAFT — Opus Gate Session N+2 must approve / amend / reject before merge
source: "TBD-OPUS-GATE-N+2 (candidates: Niemela et al 2000 Nature 404 / Globe & Dropkin 1959 J Heat Transfer 81(1) / multi-source-bracket-D)"
literature_doi: "TBD-OPUS-GATE-N+2"
# Candidate Niemela:    10.1038/35009036  (Nu = 0.124·Ra^0.309 → 8.87 at Ra=1e6)
# Candidate Globe-Dropkin: 10.1115/1.3680025 (Nu = 0.069·Ra^(1/3)·Pr^0.074 → 6.73 at Ra=1e6, Pr=0.71)
quantity: nusselt_number
reference_values:
  - Ra: 1e6
    Nu: TBD-OPUS-GATE-N+2  # candidates: ~8.87 (Niemela), ~6.73 (Globe-Dropkin), ~8.0±1.5 (multi-source bracket), or PROVISIONAL_HOLD on 10.5 with widened tolerance
tolerance: TBD-OPUS-GATE-N+2  # likely 0.15-0.25 if bracket; 0.10 if single primary anchor
source_integrity:
  last_doi_check_date: 2026-04-26
  last_doi_check_status: VERIFIED          # Niemela 2000 + Globe-Dropkin 1959 both verified
  chaivat_2006_status: NOT_LOCATABLE       # provenance flagged fictional
  expected_first_author_lastname: TBD-OPUS-GATE-N+2
  expected_year: TBD-OPUS-GATE-N+2
  expected_journal_keyword: TBD-OPUS-GATE-N+2
notes:
  - "Audit-recomputed Niemela-Sreenivasan Nu ≈ 5.5 at Ra=1e6 was ARITHMETIC ERROR; correct value is ~8.87 (verified 2026-04-26). Opus Gate should use 8.87 as the Niemela anchor."
  - "Stored Nu=10.5 differs from both candidate primaries: 18% above Niemela (within tolerance), 56% above Globe-Dropkin (outside tolerance)."
```

## §6 · Cross-validation: stored Nu=10.5 vs candidate anchors

| Anchor | Nu at Ra=10⁶, Pr=0.71 | Drift vs stored 10.5 |
|---|---|---|
| Niemela 2000 (Pr ≈ 1) | 8.87 | +18% (within 15% tolerance band? marginally outside) |
| Globe-Dropkin 1959 (Pr=0.71 explicit) | 6.73 | +56% (well outside 15%) |
| "Chaivat 0.229·Ra^0.269" (provenance fictional) | 9.4 | +12% (within 15%) |
| Goldstein-Tokuda 1980 | TBD | TBD |

The stored 10.5 is most consistent with the fictional Chaivat
correlation, second-most with Niemela, least with Globe-Dropkin. This
suggests **stored 10.5 was reverse-engineered from the fictional
correlation** rather than from a real paper, OR was set to match
adapter output for an early version of the harness.

This makes Case D substantively higher-risk than Case C: not only is
provenance broken, the value itself may have no external grounding.

## §7 · What this evidence package does NOT provide

- ❌ Independent verification that Globe-Dropkin's correlation form is
  `0.069·Ra^(1/3)·Pr^0.074` exactly (could be a textbook simplification;
  primary paper may have explicit AR or geometry corrections)
- ❌ Goldstein-Tokuda 1980 primary citation + correlation form
- ❌ Search for the actual paper that contains `0.229·Ra^0.269` (if any)
- ❌ Numerical gold value or new tolerance — these are Opus Gate Session
  N+2's substantive deliverable

## §8 · Recommended Opus Gate Session N+2 prompt structure

CFDJerry, when convening N+2, the prompt should:

1. Provide auditor with this evidence package (`docs/case_documentation/rayleigh_benard_convection/_research_notes/2026-04-26_n2_anchor_evidence.md`)
2. Provide auditor with primary source access (Niemela 2000 *Nature* + Globe-Dropkin 1959 *J Heat Transfer* PDFs)
3. Ask auditor to:
   - Verify Niemela 2000's `Nu = 0.124·Ra^0.309` correlation gives 8.87 at Ra=10⁶
   - Verify Globe-Dropkin 1959's `Nu = 0.069·Ra^(1/3)·Pr^0.074` correlation gives 6.73 at Ra=10⁶, Pr=0.71
   - Adjudicate Chaivat hypothesis (1/2/3 in §4 above)
   - Choose between single primary, multi-source bracket, or provisional hold
4. Output: APPROVE_WITH_VALUES | CHANGES_REQUIRED | TBD-GOV1-HOLD | DEFER_TO_P4_KOM

The DEC-V61-084 draft (`.planning/decisions/draft/2026-04-26_v61_084_rbc_re_anchor.md`)
is paired with this evidence package and is the destination for the
Opus Gate's approved values.

## Sources

- Niemela 2000 *Nature* 404:837-840: https://www.nature.com/articles/35009036
- Globe-Dropkin 1959 *J Heat Transfer* 81(1):24-28: https://asmedigitalcollection.asme.org/heattransfer/article-abstract/81/1/24/397579
- Audit context: `docs/case_documentation/_research_notes/gov1_paper_reread_2026-04-26.md` §2
- Authority verdict: `.planning/audit_evidence/2026-04-26_v61_080_v2_authority_gate_verdict.md` §2 Case D
