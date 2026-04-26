---
verdict_id: AUTH-V61-080-2026-04-26
title: Session B v2 NARROW authority class determination (RBC + IJ + DCT + CCW)
verdict_type: independent_opus_gate
verdict_outcome: SPLIT_EXECUTION_REQUIRED
auditor: Notion @Opus 4.7 (independent context, 2026-04-26 Asia/Shanghai)
delegating_principal: CFDJerry
parent_dec: DEC-V61-080
charter_basis: Pivot Charter §7 independence-of-context invariant
override_window_consumed: 0  # 0 days; CFDJerry's 30-day window fully preserved
binding_until: 2026-05-26  # 30 days from verdict; CFDJerry may override before this date
---

# Opus Gate Verdict — Session B v2 NARROW Authority Determination

> Verbatim transcript of the Notion @Opus 4.7 independent-context Opus
> Gate session (2026-04-26) responding to the prompt drafted in this
> chat after DEC-V61-080's amendment-landing arc. Saved as a binding
> repo artifact to ensure the verdict is reproducible after any Notion
> page edit / archival.

## §1 · V61-058 precedent finding

V61-058 was executed as **CLASS-2 equivalent** under the v6.1 governance
counter: the DEC frontmatter records `autonomous_governance: true` with
**mandatory Codex review** (3-round arc: pre-Stage-A REQUEST_CHANGES →
R1 CHANGES_REQUIRED → R2 APPROVE_WITH_COMMENTS), counter advancing
41→42. **No external Opus Gate was convened.**

**Critical distinguisher** that limits its precedential reach: V61-058
pivoted gold *provenance* to verified literature anchors (Ladson 1988
NASA TM-4074 + Abbott 1959 + Gregory 1970), and the sweep result was a
**documented FAIL** (Cl@α=8° = 0.491 vs gold 0.815, 40% under), closed
as `METHODOLOGY_COMPLETE_PHYSICS_FIDELITY_GAP_DOCUMENTED`. The gold
values themselves were not torqued to make the case pass — they were
anchored to verified primary literature and the gap was honestly recorded.

**Therefore V61-058 is precedential for citation-anchor pivots where
(a) the new anchor is a verified primary-literature source and
(b) gold values are read out of the new source rather than reverse-
engineered to fit existing harness behavior.** It is *not* precedential
for cases where the existing stored value's literature provenance is
fictional and the new anchor selection itself is contested.

## §2 · Per-case authority verdict

| Case | Class | Rationale |
|---|---|---|
| **A — CCW DOI typo** (`.002421` → `.002401`) | **CLASS-1** | Single-paper, single-author, single-year, single-title, single-volume/page identity uncontested. Four-character typo in `literature_doi` only; no `gold_value`, no `tolerance`, no `source` field touched. Does not engage Pivot Charter §4 inv 1 or inv 4. Defining example of CLASS-1. |
| **B — DCT journal swap** (IJHMT → ASME J. Fluids Eng., DOI `10.1115/1.3448250`) | **CLASS-2** | Bibliographic-block update is more than a typo (`source` + `literature_doi` both change), but paper identity (Jones 1976) and the f=0.0185 / 0.88·f_pipe relationship in `reference_correlation_context` remain intact. No gold value change, no tolerance change. Touches `knowledge/**.yaml` metadata substantively → mandatory `/codex-gpt54` review verifying (i) ASME archive confirms relationship, (ii) `reference_correlation_context` text still matches correctly-cited journal. Mirrors V61-058 in being verified-literature pivot with no harness-truth shift. |
| **C — IJ Behnia re-anchor** | **CLASS-3** | Stored DOI resolves to different paper entirely (LES turbines). Current Nu(r/d=0)=25 vs Behnia 1999 IJHFF Vol 20(1) reported ~110-130 is 4-5× discrepancy — well outside tolerance band. Resolution requires (i) primary-source paper read of Behnia 1999, (ii) identifying which paper stored 25 came from, (iii) deciding Cooper 1993 vs Behnia 1999, (iv) reconciling possibly-different Nu non-dim conventions. **Gold-value re-anchoring under fictional provenance**, not anchor cleanup over verified provenance — directly engages Pivot Charter §4 invariant 1. V61-058 precedent does NOT cover this shape. |
| **D — RBC Chaivat → multi-source pivot** | **CLASS-3** | "Chaivat et al. 2006" not findable in any indexed database; provenance is **fictional**, not merely mis-DOI'd. Stored Nu=10.5 doesn't match Globe-Dropkin 1959 (~7), Niemela-Sreenivasan 2003 (~5.5), or Goldstein-Tokuda 1980. Reverse-engineered `0.229·Ra^0.269 ≈ 9.4` correlation could not be located in any retrievable paper. Selecting new anchor (single primary vs multi-source bracket vs accept drift to ~7-9) is itself substantive constitutional choice. Same §4-invariant-1 engagement as Case C; arguably stronger because *no* primary literature currently supports stored value. |

**No case lands in CLASS-4.** The P4 KOM `gold_value.source_integrity`
schema field proposal is forward-looking *tracking* improvement (per
`_p4_schema_input.md` P-12 escalation); does not block four substantive
fixes from landing in their respective lanes. Pivot Charter §4 inv 4
restricts schema-shape changes, **not** value updates within existing
schema.

## §3 · Session B v2 NARROW execution shape

**SESSION_B_V2_NARROW splits.** It does **not** proceed end-to-end as
a single arc.

### Claude-Code-only half (CLASS-1 + CLASS-2)

Proceeds under V61-001 / V61-053 amended Codex-trigger rules:

- **Case A (CCW)** — single DEC, `autonomous_governance: true`, no Codex
  tool report required (CLASS-1 metadata-only typo precedent)
- **Case B (DCT)** — single DEC, `autonomous_governance: true`, **mandatory
  `/codex-gpt54` review** with `codex_tool_report_path` written into DEC
  frontmatter (mirrors V61-058 R1+R2 pattern at lighter scope since no
  gold-value change)
- Pre-conditions: A1 ✅ landed (`0bca459`), A4 formal cross-session DEC
  issued under CFDJerry authority (currently ⏳ evidence-only)

### External-gate half (CLASS-3)

Claude Code drafts but holds gold-YAML edits:

- **Case C (IJ)** — Claude Code may produce: (i) candidate multi-source
  anchor table (Cooper 1993 vs Behnia 1999, with retrieved Nu values at
  Re=10000 / h/d=2), (ii) `_research_notes/` paper-read evidence file,
  (iii) draft DEC with TBD-marked `gold_value` / `tolerance`. **MAY NOT**
  edit `knowledge/gold_standards/impinging_jet.yaml` `gold_value` /
  `tolerance` / `source` / `literature_doi` fields until separate
  independent-context Opus Gate session approves new anchor + value +
  tolerance.
- **Case D (RBC)** — same shape as Case C, against
  `knowledge/gold_standards/rayleigh_benard_convection.yaml`.

**This split is binding on Claude Code subject to §6 below.**

## §4 · Required Opus Gate sessions

Two gate sessions, **CFDJerry-triggered**, in priority order:

1. **Opus Gate Session N+1 (P0) — IJ anchor approval.**
   *"Approve [Cooper 1993 / Behnia 1999 IJHFF Vol 20(1) / multi-source
   bracket] as IJ primary anchor at Re=10000, h/d=2; approve new gold
   `nusselt_number` peak value X with tolerance Y%; resolve where stored
   value Nu=25 actually came from or accept it as un-attributable."*

2. **Opus Gate Session N+2 (P0) — RBC anchor approval.**
   *"Approve [Globe & Dropkin 1959 / Niemela & Sreenivasan 2003 /
   multi-source bracket] as RBC primary anchor at Ra=10⁶; approve new
   gold `nusselt_number` value X with tolerance Y%; or approve TBD-GOV1
   hold pending P4 KOM `source_integrity` field ratification."*

Both gates CFDJerry-triggered per Pivot Charter §7. Claude Code cannot
self-trigger; can only deliver draft evidence package.

## §5 · Constitutional findings

1. **Pivot Charter §4 should add explicit "Gold-value modification
   authority" §4.7 sub-section.** V61-058 + this gate jointly establish
   that auto/Codex/Opus line for `knowledge/gold_standards/*.yaml`
   `gold_value` field edits is currently inferred from invariants 1 and
   4 rather than codified directly. Canonical rule: *"`gold_value` edits
   where new anchor is verified primary literature and value is read out
   of source: CLASS-2; `gold_value` edits where prior provenance is
   fictional or anchor itself is contested: CLASS-3."* Codification
   would prevent next case-N audit from re-litigating.

2. **P-12 LOW→HIGH severity escalation in `_p4_schema_input.md` is now
   empirically confirmed**: 4 of 10 cases (40%) have citation-integrity
   issues, 2 are HIGH (fictional/wrong-paper provenance). P4 KOM
   `gold_value.source_integrity` field is no longer optional — it is
   **load-bearing** acceptance test for the schema.

3. **The independent-context invariant held under load.** This gate
   operated without inheriting prior session reasoning, including
   DEC-V61-080's own internal "external Opus Gate required" recommendation
   — and reached substantively similar conclusion via independent
   application of §4 invariant 1. Healthy signal for gate architecture.

## §6 · 30-day override window status

**0 days consumed · CFDJerry's window fully preserved.** Independent-
context Opus Gate verdicts are advisory-binding subject to 30-day
override window per Pivot Charter §7 / DEC-AUDIT-2026-04-26 framing.
CFDJerry retains full authority within 30 days from 2026-04-26 to:

- Override Cases C/D from CLASS-3 down to CLASS-2 (Codex-only) — would
  require a Decisions DB entry naming this verdict and citing override
  clause
- Accept verdict as-is (default if no override filed)
- Accept subset (e.g., concur on A/B/D classification, override C to
  CLASS-2)

Until override (if any), **Claude Code is bound to the §3 split execution
shape** with explicit hard-binding on knowledge/gold_standards/{impinging_jet,rayleigh_benard_convection}.yaml.

---

## Implementation impact for repo

This verdict adds a new hard boundary to Session B v2 (and any future
gold-value edit work):

```
session_b_v2_authority_split:
  case_a_ccw:
    class: 1
    pre_conditions: [a1_landed]
    blocking: false
    write_paths_allowed:
      - knowledge/gold_standards/circular_cylinder_wake.yaml  # literature_doi field only
      - docs/case_documentation/circular_cylinder_wake/citations.bib
  case_b_dct:
    class: 2
    pre_conditions: [a1_landed, codex_tool_report_must_run]
    blocking: false
    write_paths_allowed:
      - knowledge/gold_standards/duct_flow.yaml  # source + literature_doi only
      - docs/case_documentation/duct_flow/citations.bib
  case_c_ij:
    class: 3
    pre_conditions: [a1_landed, opus_gate_n_plus_1_approved]
    blocking: true  # Claude Code BLOCKED on knowledge/gold_standards/impinging_jet.yaml
    write_paths_allowed_pre_gate:
      - docs/case_documentation/impinging_jet/_research_notes/
      - .planning/decisions/<draft DEC with TBD markers>
    write_paths_allowed_post_gate:
      - knowledge/gold_standards/impinging_jet.yaml  # only after Opus Gate N+1 APPROVE
      - docs/case_documentation/impinging_jet/citations.bib
  case_d_rbc:
    class: 3
    pre_conditions: [a1_landed, opus_gate_n_plus_2_approved]
    blocking: true  # Claude Code BLOCKED on knowledge/gold_standards/rayleigh_benard_convection.yaml
    # ... (parallel structure to Case C)
```

This becomes load-bearing input for any DEC that opens Session B v2.

## Source

Verdict text verbatim from Notion @Opus 4.7 independent-context session
2026-04-26 (Asia/Shanghai timezone), invoked under Pivot Charter §7
delegation by CFDJerry. Saved as repo artifact at
`.planning/audit_evidence/2026-04-26_v61_080_v2_authority_gate_verdict.md`
to ensure binding-text reproducibility independent of any subsequent
Notion edit.

Notion verdict URL: pending CFDJerry creation of a DEC-AUTH-V61-080
sub-page under Decisions DB (recommended for discoverability; not
required for binding).
