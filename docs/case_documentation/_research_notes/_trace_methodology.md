# Tier-(c) → Tier-(a) Citation Trace Methodology

> Draft for Session B v4 P-3 GOV-1 v0.6 → v0.7 upgrade pass.
> Status: **DRAFT (CLASS-1 autonomous)**, ratification optional. Application of methodology produces a CLASS-2 documentation change (citations.bib + READMEs); the methodology document itself is meta-rule.
> Author: Claude Code (cfd-harness-unified governance)
> Date: 2026-04-26

## Purpose

GOV-1 v0.6 surfaced 8 tier-(c) citations (`dec_v61_057_intake` ×4, `dec_v61_058_intake` ×4) that are anchored to internal DEC §B intake decisions rather than primary literature. The naive upgrade path "the gold value's primary paper exists for this case → reclassify the tolerance citation as that paper too" is **circular** and would inflate the literature-coverage metric without adding rigor.

This methodology codifies what counts as a valid tier-(c) → tier-(a) upgrade so the GOV-1 v0.7 pass produces an honest count, not a cosmetic one.

## §1 What qualifies as a tier-(a) tolerance trace

A tolerance citation is **tier-(a) eligible** if and only if **all four** conditions hold:

1. **Direct support clause.** The cited paper's §X (a specific, identifiable section, table, figure, or appendix) **directly contains** a quantitative basis for the tolerance value chosen — examples:
   - Reported measurement uncertainty / tunnel repeatability for the same observable
   - Mesh-sensitivity table giving observed scatter of the observable across grids
   - Cross-validation summary giving observed scatter across studies (paper-internal, not meta-literature outside the cited paper)
   - Discretization-error analysis quantifying numerical noise floor
2. **Same observable.** The directly-supported quantity in §X is the same observable (or a tight super-set) as the harness gate. Example pass: §3.4 reports tunnel repeatability for `Cl@α=8°` and the harness gates `lift_coefficient_alpha_eight`. Example fail: §3 reports mesh-sensitivity for `Nu_avg` but harness gates `Nu_max` (different reduction of same field — needs its own anchor).
3. **Tolerance envelope contains §X-stated noise floor.** The harness tolerance is **at least** the §X-stated noise floor (so the gate cannot be tighter than the paper's own measurement / model uncertainty). Wider envelopes that add a numerical/mesh buffer on top of §X are still tier-(a) eligible, with the §X value as the load-bearing lower bound.
4. **No circular path.** §X is not itself derived from `dec_v61_05X_intake` or any harness-internal artifact. The paper is independent prior art.

If all 4 hold, the citation upgrades to **dual-citation** form (see §3). If any fails, the citation **stays tier-(c)** with an honest fallback annotation (see §4).

## §2 What does NOT qualify (anti-patterns)

The following are explicit anti-patterns that **must not** be used to justify a tier-(a) upgrade:

- **Gold-value-by-association.** "The paper provides the gold value, therefore the tolerance is anchored in the same paper." A gold value tells you the **target**; it does not tell you the **acceptable deviation envelope**. These are independent claims and need independent anchors.
- **Meta-literature smuggling.** "The paper has been cross-validated by ≥40 subsequent studies within ±0.2%, therefore the tolerance is anchored to the paper." The ±0.2% figure lives in the meta-literature (subsequent studies), not in the cited paper itself. The paper alone is not a tier-(a) anchor for the tolerance under §1.1.
- **Methodology paper for an unrelated quantity.** "The paper discusses mesh sensitivity for `quantity_A`, therefore the tolerance for `quantity_B` (different observable) is anchored to it." Fails §1.2.
- **DEC-cites-paper-cites-DEC loops.** If the DEC §B rationale was itself derived by reading the paper and the paper is then re-cited as the tolerance anchor, the literature anchor must be the **direct** §X passage that informed §B, not the round-trip. If §B's rationale is the harness team's engineering judgment about extractor noise / numerical method choice (typical for cross-check observables), the upgrade fails §1.1.

## §3 Dual-citation format for successful upgrades

When all four §1 conditions hold, the README tolerance row uses **dual citation**:

```
| `observable` | 0.X | `paper_key` (§X) + `dec_v61_05X_intake` | <Paper> §X reports <noise floor / repeatability>; <X% tolerance> covers <§X figure> + harness numerical buffer (§B). |
```

The internal DEC citation is **retained as secondary** so the trace from intake decision → paper anchor remains visible in the audit trail. The bib note for the secondary entry should be updated to read:

```
note = {... \S B.X chose Y\% tolerance, derived from <paper_key> \S X-stated <noise floor> plus harness numerical buffer.}
```

The tier classification in the README breakdown table counts the upgraded row under tier-(a), but the README narrative around the table should explicitly note it as **"literature-informed via dual citation"** to distinguish from rows where the paper directly states the tolerance value (rare in CFD validation literature).

## §4 Honest fallback for failed upgrades

When any §1 condition fails, the citation **stays tier-(c)**. The README tolerance row is annotated:

```
| `observable` | 0.X | `dec_v61_05X_intake` | <existing rationale> · <paper> §X-anchor attempted under GOV-1 v0.7 trace methodology, no §X passage directly supports tolerance — engineering judgment retained. |
```

The README tier breakdown table keeps these in tier-(c) and the narrative section explicitly states:

> "GOV-1 v0.7 attempted tier-(c) → tier-(a) upgrade for N entries; M succeeded under §1 conditions, N-M failed §1.1/§1.2 and remain tier-(c) with honest annotation. Failed cases reflect harness-internal numerical/extractor decisions that have no published anchor — not a documentation gap, a real distinction in rigor."

This preserves the honest count and avoids the trap of inflating literature coverage by reclassifying engineering judgments as paper anchors.

## §5 Borderline cases & resolution

CFD validation literature rarely reports per-observable tolerance bands the way experimental measurement literature does. Most direct-support tier-(a) traces (when they exist) come from:

- **Experimental papers reporting tunnel repeatability** (Ladson 1988 §3.4 paradigm — paradigmatic example: `lift_coefficient_alpha_eight` 5% citing Ladson §3.4 ±1.2%)
- **Numerical benchmark papers reporting grid-convergence tables** (rare; de Vahl Davis 1983 reports converged values but no per-grid scatter table)
- **Discretization-error studies** (typically separate methods papers, not the gold-value paper)

Borderline pattern: paper §X reports a noise floor for the case category (not the specific observable), e.g., Ladson §3.4 ±1.2% applies primarily to `Cl@α=8°` but the lift slope gate `dCl/dα` is computed from {α=0°, 4°, 8°} measurements that all share that ±1.2% tunnel noise. Compounded over the slope estimation, the worst-case linearity-check noise floor is ~√3 × 1.2% ≈ 2.1%. A 10% gate that includes this 2.1% lower bound + numerical buffer is **legitimately literature-informed** under §1 with the slope being a §1.2 "tight super-set" of the §X-anchored quantity.

Such borderline upgrades MUST cite the §X passage and explicitly note the compounded-noise reasoning in the README rationale column. They MUST NOT be silent reclassifications.

## §6 Application protocol

1. For each tier-(c) entry, evaluate §1 conditions 1-4 and write a one-line verdict in the per-entry trace log (this `_trace_methodology.md` document's appendix when applied).
2. Apply upgrades and fallbacks per §3 and §4.
3. Update `docs/case_documentation/README.md` tier breakdown table with honest counts.
4. Close in DEC-V61-086 with explicit per-entry trace verdict table.
5. If methodology requires CLASS-2 ratification before application (because a citation key in the gold YAML's `source` field would change — not the case here, all upgrades touch only `docs/case_documentation/**`), pause and queue for CFDJerry / Notion @Opus 4.7 ratification. **For this v0.7 pass, no `source` field touches are anticipated**; methodology and application proceed CLASS-1 autonomously.

## §7 What this methodology does NOT do

- It does not change any `knowledge/gold_standards/*.yaml` `source` / `gold_value` / `tolerance` field. Those are CLASS-3 forbidden under DEC-V61-085 §4.7.
- It does not retroactively reclassify tier-(b) ASME V&V 20-2009 entries. Tier-(b) is its own anchor class with its own justification (Pivot Charter §5).
- It does not propose collapsing the dec_v61_05X_intake bib entries. Those remain in citations.bib as secondary anchors for traceability even when upgraded to dual-citation.

## Appendix — Per-entry trace verdict log (filled at application time)

| Case | Observable | Tolerance | Candidate anchor | §1.1 direct support? | §1.2 same observable? | §1.3 envelope ≥ §X? | §1.4 no circular? | Verdict |
|---|---|---|---|---|---|---|---|---|
| DHC | `nusselt_max` | 0.07 | de Vahl Davis 1983 §3 | ❌ no §3 mesh-sensitivity table | n/a | n/a | n/a | tier-(c) retained — extractor noise floor is harness-internal |
| DHC | `u_max_centerline_v` | 0.05 | de Vahl Davis 1983 Table II | ❌ Table II gives gold value, no scatter band | n/a | n/a | n/a | tier-(c) retained — interior-peak independence is harness engineering choice |
| DHC | `v_max_centerline_h` | 0.05 | de Vahl Davis 1983 Table II | ❌ same as above | n/a | n/a | n/a | tier-(c) retained — same rationale |
| DHC | `psi_max_center` | 0.08 | de Vahl Davis 1983 Table I | ❌ Table I gives gold value, tolerance is trapezoidal-∫ noise floor | n/a | n/a | n/a | tier-(c) retained — numerical method noise floor, no published anchor |
| NACA | `pressure_coefficient` profile | 0.20 | Abbott 1959 Fig 4-7 / Gregory 1970 Fig 7 | ❌ figures show profile shape, no scatter band; 20% specifically targets harness 30-50% cell-band attenuation | n/a | n/a | n/a | tier-(c) retained — harness-observed attenuation, no published anchor |
| NACA | `lift_slope_dCl_dalpha` | 0.10 | Ladson 1988 §3.4 | ✅ §3.4 ±1.2% tunnel repeatability | ✅ §1.2 super-set: slope computed from Cl(0/4/8°) measurements all sharing ±1.2% | ✅ 10% > 2.1% compounded | ✅ Ladson independent of intake | **tier-(a) UPGRADE — dual citation Ladson §3.4 + dec_v61_058_intake** |
| NACA | `drag_coefficient_alpha_zero` | 0.15 | Ladson 1988 §3.4 | ❌ §3.4 reports lift repeatability, not drag wall-function noise | ❌ different observable + different physics | n/a | n/a | tier-(c) retained — wall-function discretization noise is solver-specific, no published anchor |
| NACA | `y_plus_max` | n/a (advisory) | n/a | ❌ Codex F5 ruling, not literature | n/a | n/a | n/a | tier-(c) retained — internal review artifact (and advisory, doesn't gate) |

**Aggregate**: 1 upgrade (NACA `lift_slope_dCl_dalpha`) / 7 honest fallback / 8 total.
**GOV-1 v0.7 tier-(a) count**: 10 + 1 = **11/29 = 38%** (vs v0.6 baseline 10/29 = 34%).

The honest delta is +1 upgrade, not the ≥5 implied by the "≥15/29 expected" target. This reflects the reality that DHC's primary paper (de Vahl Davis 1983) is a converged-numerical-benchmark paper without per-grid scatter or measurement-noise sections, and most NACA cross-check tolerances are harness-internal numerical/extractor decisions. The methodology's no-circular-citation rule (§2) prevents inflating the count via gold-value-by-association.
