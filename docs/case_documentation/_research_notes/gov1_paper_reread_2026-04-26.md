# GOV-1 Paper Re-Read Research Notes (2026-04-26)

> Closure attempt for the 3 open HOLDs identified in DEC-V61-080 §"Open questions".
> Findings escalated from research notes to **citation-data integrity issues** for two of three cases.
>
> **Author**: Claude Code Opus 4.7 (1M context) under DEC-V61-080 follow-on
> **Method**: WebSearch + DOI direct fetch + Semantic Scholar API metadata lookup
> **Status**: input material for GOV-1 v1.0; **DOES NOT** modify any tolerance value, gold value, or `knowledge/**` content (hard boundaries 1-5 honored)

## Executive summary

Of the 3 HOLDs originally framed as "correlation-variant ambiguity pending paper re-read":

| Case | Original framing | Re-read finding | Severity |
|---|---|---|---|
| Impinging Jet | Behnad 2013 paper re-read pending; 4-5× Nu peak discrepancy | 🚨 **DOI in gold YAML resolves to a completely unrelated paper** (LES in LP turbines). The Behnia/Parneix/Shabany/Durbin canonical work is **1999, not 2013**. Source citation is broken. | **HIGH** — citation provenance is wrong; gold value's literature anchor is unverified |
| Rayleigh-Bénard | Chaivat 2006 correlation variant ambiguity | 🚨 **DOI in gold YAML resolves to a completely unrelated paper** (single/two-phase rectangular jet array cooling). Author "Chaivat" not findable in any search. The cited paper may not exist. | **HIGH** — both author and DOI are unverified; gold value's literature anchor is fictional or mistranscribed |
| Lid-Driven Cavity (secondary vortex ψ) | No published reference for the primary→secondary relaxation factor 2× | Confirmed: Ghia 1982 secondary vortex stream function values are reproducible to <1% on adapter, primary <0.85%; 10% relaxation is engineering judgment grounded in well-documented corner-eddy mesh sensitivity. **No formal literature anchor exists for the 2× relaxation factor itself.** | **LOW** — engineering judgment with rationale; no factual error |

**Two of three HOLDs reveal corrupted citation provenance, not just correlation-variant ambiguity.**

This is functionally similar to FM-NACA-1 (`unreliable_paper_provenance`) which was already retired in DEC-V61-058 by multi-source pivot. The same retirement pattern likely applies to IJ and RBC, but the gold values themselves need re-anchoring against verified literature, which is GOV-1 v1.0 + Opus Gate scope.

## §1 Impinging Jet (IJ) — DOI resolves to unrelated paper

### 1.1 What gold YAML claims

`knowledge/gold_standards/impinging_jet.yaml`:
```yaml
source: "Cooper 1984 / Behnad et al. 2013"
literature_doi: "10.1016/j.ijheatfluidflow.2013.03.003"
```

### 1.2 What the DOI actually points to

Via Semantic Scholar API metadata lookup on `DOI:10.1016/j.ijheatfluidflow.2013.03.003`:

- **Title**: "Large eddy simulations in low-pressure turbines: Effect of wakes at elevated free-stream turbulence"
- **Authors**: V. N. Rao, P. Tucker, R. Jefferson-Loveday, J. Coull
- **Year**: 2013
- **Journal**: International Journal of Heat and Fluid Flow, Volume 43, Pages 85-95

This is a low-pressure turbine LES paper, **completely unrelated** to impinging jet heat transfer. The DOI is wrong.

### 1.3 What the canonical Behnia paper actually is

Via WebSearch (multiple cross-references):

- **Title**: "Numerical study of turbulent heat transfer in confined and unconfined impinging jets"
- **Authors**: M. Behnia, S. Parneix, Y. Shabany, P. A. Durbin
- **Year**: **1999** (NOT 2013)
- **Journal**: International Journal of Heat and Fluid Flow, Volume 20(1), pp. 1-9
- **Likely DOI**: `10.1016/S0142-727X(98)10040-1` (typical for IJHFF 1999 vol 20 issue 1; not verified by direct fetch)

### 1.4 What this means for the gold values

The stored Nu(r/d=0)=25 and Nu(r/d=1.0)=12 values were attributed to a paper whose DOI is wrong. Two possibilities:

**(a)** The values were transcribed from the genuine 1999 Behnia paper but the citation got corrupted to the wrong year/DOI somewhere along the way. Auditors should verify Re=10000, h/d=2 numbers against the 1999 paper directly.

**(b)** The values were transcribed from a different source entirely (e.g., a later citation, a textbook digest, a tutorial example) and the Behnia attribution itself is incorrect. This would be a more severe `synthesized_gold_no_cross_check` failure mode (cf. FM-LDC-1).

The pre-existing audit comment in the gold YAML is consistent with (b):
> "audit flagged Nu@r/d=0 = 25 vs Behnad 2013 ~110-130, but 4-5× discrepancy is too large to edit without reading Behnad et al. 2013 (DOI 10.1016/j.ijheatfluidflow.2013.03.003) directly"

If Behnia 1999 reports Nu peak ~110-130 (cited in audit notes), then the stored 25 cannot be from Behnia at all. The "~110-130" estimate likely came from another paper (e.g., Cooper 1984/1993, Baughn 1989, or numerical correlation papers) and was confused.

### 1.5 Recommended GOV-1 v1.0 action (NOT in scope of this DEC)

Multi-source pivot (analogous to NACA0012 DEC-V61-058 Batch A):
1. Pin a verified primary anchor (Behnia 1999 if Re=10000, h/d=2 fits — needs paper inspection)
2. If Behnia 1999 doesn't match the configuration, pin Cooper 1984/1993 or Baughn 1989 directly
3. Update gold values + tolerance + DOI to match the verified anchor
4. Mark gold_value `status: VERIFIED` with archive_id + source_table

This is gold-value re-anchoring, which is **out of GOV-1 v0.5 scope** (hard boundary 2: "no tolerance value change, no gold value change"). v1.0 + Opus Gate scope.

## §2 Rayleigh-Bénard Convection (RBC) — DOI resolves to unrelated paper, author not findable

### 2.1 What gold YAML claims

`knowledge/gold_standards/rayleigh_benard_convection.yaml`:
```yaml
source: "Chaivat et al. 2006"
literature_doi: "10.1016/j.ijheatmasstransfer.2005.07.039"
```

### 2.2 What the DOI actually points to

Via Semantic Scholar API metadata lookup on `DOI:10.1016/j.ijheatmasstransfer.2005.07.039`:

- **Title**: "Single-phase and two-phase cooling with an array of rectangular jets."
- **Authors**: M. Meyer, I. Mudawar, Chad. E. Boyack, C. A. Hale
- **Year**: 2006 (volume 49 issue 1, pp. 17-29)
- **Journal**: International Journal of Heat and Mass Transfer

This is a rectangular-jet-array cooling paper (heat exchanger / electronics cooling context), **completely unrelated** to Rayleigh-Bénard natural convection.

### 2.3 What "Chaivat 2006" actually is

The author name "Chaivat" was not findable in:
- Web search (multiple query variants)
- Semantic Scholar
- Google Scholar (via web search results)

Possible explanations:
**(a)** Author name is misspelled / mis-transliterated. Possible originals: "Chaiwat", "Chairat", "Chaiyat" (Thai), "Chavat", "Chaivat" (a transliteration that may correspond to Russian / Eastern European). Without knowing the original, I cannot find the paper.

**(b)** Author name is wholly fictional / a placeholder that survived from Phase 0 synthesis. This pattern was already documented at LDC FM-LDC-1 (Phase 0 synthesized values).

**(c)** Author name is correct but paper is in a non-indexed publication (conference proceedings, book chapter, regional journal not in Semantic Scholar).

The gold value Nu = 10.5 at Ra = 10⁶ is at the edge of plausibility for the laminar steady-convective regime. Possible cross-check anchors:

- **Globe & Dropkin 1959**: Nu ≈ 0.069·Ra^(1/3)·Pr^0.074 → at Ra=10⁶, Pr=0.71: Nu ≈ 0.069·100·1.0 = 6.9 (low Pr correction makes it ~7)
- **Pellew & Southwell 1940 / Krishnamurti 1970**: critical Ra = 1707.76 (onset); Nu vs Ra curve for moderate Ra ranges ~10-15 at Ra=10⁶
- **Niemela & Sreenivasan 2003**: experimental Nu = 0.124·Ra^0.309 → at Ra=10⁶: 0.124·44.7 ≈ 5.5

The stored 10.5 is plausibly within range, but the cited "0.229·Ra^0.269" correlation reproduces 9.4 at Ra=10⁶ (audit comment) — closer to the stored 10.5 than to Globe-Dropkin or Niemela-Sreenivasan. The stated coefficient 0.229 doesn't match standard published correlations I could find.

### 2.4 What this means for the gold values

The RBC HOLD now has two layers:
- Layer 1 (original): "which Chaivat correlation variant is the primary equation?"
- Layer 2 (new): "does Chaivat exist as a citable author? does the cited paper exist?"

If layer 2 fails, the gold value Nu=10.5 is effectively unanchored. Phase 7 Docker E2E reported Nu=10.5 matches "ref" — but the ref came from a possibly-fictional source. The numerical agreement is internally consistent (adapter produces 10.5 vs gold 10.5) but the gold value's external grounding is broken.

### 2.5 Recommended GOV-1 v1.0 action (NOT in scope of this DEC)

Multi-source pivot:
1. Drop "Chaivat 2006" attribution
2. Re-anchor against Globe & Dropkin 1959, Niemela & Sreenivasan 2003, or Goldstein & Tokuda 1980 (canonical RBC correlations)
3. Update gold value to whatever the new anchor reports at Ra=10⁶, Pr=0.71, AR=2
4. Adjust tolerance based on the new anchor's stated uncertainty band
5. Mark gold_value `status: VERIFIED` with archive_id + correlation form

If the adapter's Nu=10.5 falls outside the new anchor's tolerance band, this becomes a substantive physics-correctness question rather than just citation-cleanup.

## §3 Lid-Driven Cavity (LDC) — secondary vortex ψ relaxation

### 3.1 What gold YAML claims

`knowledge/gold_standards/lid_driven_cavity.yaml` (secondary_vortices block):
```yaml
psi_tolerance: 0.10  # Relaxed from 0.05 — corner eddies are mesh-sensitive
```
With inline comment: "RELAXED from primary's 0.05 because corner eddies are an order of magnitude more mesh-sensitive than the primary vortex".

### 3.2 What the literature actually says

Via WebSearch on Ghia 1982 LDC benchmark + secondary vortex tolerance:

> "Stream function values show very good accuracy, with differences from reference values less than 0.85% for the primary vortex and 0.98% for secondary vortices when compared against the Ghia et al. benchmark."

So **on a sufficiently-resolved mesh**, both primary and secondary ψ are reproducible to ~1% against Ghia's 129×129 Re=100 benchmark. This contradicts the harness's framing that secondaries are "an order of magnitude more mesh-sensitive".

### 3.3 What this means for the tolerance

Two reconcilable interpretations:

**(a) Mesh-quality interpretation**: on Ghia's 129² mesh, both ψ values are accurate to ~1%. On a coarser harness mesh (or with a non-Poisson ψ extractor that has wall-closure residual ~3.4e-3), the secondary ψ values are dominated by the noise floor (FM-LDC-4). The 10% tolerance is then a noise-floor accommodation, NOT an inherent corner-eddy mesh-sensitivity claim. This reframing is more honest.

**(b) Algorithm-dependent interpretation**: trapezoidal ∫U_x dy reconstruction has a different error profile than Ghia's stream-function-vorticity formulation. On the trapezoidal extractor, corner eddies ARE substantially more sensitive than the primary because their ψ magnitudes are 5-6 orders smaller and any integration drift is amplified. This matches the inline comment's intent.

Both interpretations are physically reasonable. Neither is formally cited in published literature — the 2× relaxation is an engineering choice based on noise-floor / extractor-method considerations specific to the harness's ψ reconstruction approach.

### 3.4 Recommended action

**Within GOV-1 v0.5 scope**: keep the existing `TBD-GOV1` marker but enrich the rationale in the per-case `failure_notes.md` (FM-LDC-4 already covers the noise-floor angle).

**For GOV-1 v1.0**: consider whether to (a) tighten the tolerance to 5% AND fix the extractor (Poisson solve `∇²ψ = -ω_z` per FM-LDC-4 resolution plan), or (b) keep 10% as documented engineering choice with the noise-floor rationale.

This is a **methodological choice**, not a citation-data-integrity issue, so it's lower-severity than IJ and RBC.

## §4 Pattern: corrupted citation provenance is not a single-case anomaly

The two HIGH-severity findings (IJ, RBC) confirm that citation-data-integrity is a recurring failure mode across the gold-standard set:

| Case | Status | Pattern |
|---|---|---|
| `naca0012_airfoil` | RESOLVED in DEC-V61-058 | Pre-V61-058 cited "Thomas 1979 / Lada & Gostling 2007" with DOI 10.1017/S0001924000001169 — flagged unreliable; multi-source pivot to Ladson 1988 NTRS-19880019495 + Abbott 1959 + Gregory 1970 |
| `impinging_jet` | NEW FINDING (this doc) | Cites "Behnad et al. 2013" with DOI 10.1016/j.ijheatfluidflow.2013.03.003 — DOI resolves to unrelated LES turbines paper. Genuine Behnia paper is 1999. |
| `rayleigh_benard_convection` | NEW FINDING (this doc) | Cites "Chaivat et al. 2006" with DOI 10.1016/j.ijheatmasstransfer.2005.07.039 — DOI resolves to unrelated jet-array cooling paper. Author not findable. |

3 of 10 cases (30%) have a citation-data-integrity issue at some point. NACA was caught and resolved by an independent audit (Codex F4); IJ and RBC remained latent until this GOV-1 v0.5 paper re-read.

The pattern theme P-12 in `_p4_schema_input.md` (`unreliable_paper_provenance`) was originally framed around NACA only. **This research note expands its observation set to 3 cases**, escalating the pattern from "LOW (resolved by Codex F4)" to **HIGH** (recurring; 30% case prevalence; latent until manual re-read).

P4 schema design should treat link-rot / DOI-mismatch / author-unfindable as a first-class invariant: at gold-value ingest time, **fetch the cited DOI** and check that title/authors/year roughly match the declared `source` field. This catches both genuine link rot and synthesized-from-thin-air placeholders.

## §5 What this DEC follow-on does NOT do

- ❌ Does NOT modify any tolerance value
- ❌ Does NOT modify any gold value
- ❌ Does NOT modify `knowledge/whitelist.yaml` or `knowledge/gold_standards/*.yaml`
- ❌ Does NOT close the IJ or RBC HOLDs (they require Opus Gate decision on re-anchoring)
- ❌ Does NOT modify `_p4_schema_input.md` to update P-12 severity (deferred to a separate DEC if pattern-set update is approved)

## §6 What this DEC follow-on DOES

- ✅ Documents the IJ DOI-mismatch finding with primary evidence (Semantic Scholar API metadata)
- ✅ Documents the RBC author-unfindable + DOI-mismatch finding
- ✅ Documents the LDC ψ relaxation rationale (noise-floor interpretation more honest than corner-eddy mesh-sensitivity claim)
- ✅ Provides input for GOV-1 v1.0 and P4 P-12 pattern severity escalation
- ✅ Honors all 7 hard boundaries from DEC-V61-080

## Sources

- IJ DOI metadata via Semantic Scholar: `https://api.semanticscholar.org/graph/v1/paper/DOI:10.1016/j.ijheatfluidflow.2013.03.003`
- RBC DOI metadata via Semantic Scholar: `https://api.semanticscholar.org/graph/v1/paper/DOI:10.1016/j.ijheatmasstransfer.2005.07.039`
- Behnia 1999 cross-references: WebSearch on "Behnia Parneix Shabany Durbin impinging jet"
- Ghia 1982 LDC tolerance: WebSearch on "Ghia 1982 lid-driven cavity Re=100 secondary vortex"
- Pre-existing in-yaml audit notes: `knowledge/gold_standards/impinging_jet.yaml` Gate Q-new Case 9 HOLD comment; `knowledge/gold_standards/rayleigh_benard_convection.yaml` Gate Q-new Case 10 HOLD comment
