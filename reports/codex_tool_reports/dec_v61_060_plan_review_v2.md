# DEC-V61-060 · Codex Pre-Stage-A Plan Review · v2

**Reviewer**: Codex GPT-5.4 (sajihsmipoal@gmail.com)
**Submitted at**: 2026-04-25 ~19:35 +0800
**Verdict**: REQUEST_CHANGES
**Estimated pass rate as written**: 0.45
**Stage A.0 go/no-go**: NO_GO

## Findings (3 = 1H + 2M)

### F1-HIGH · Type-II classification still over-hardens contract

File refs: intake.yaml:72, 115, 159, 532

case_type=II is set, but the file still claims 2 HARD_GATED observables
(`nusselt_number` + `nusselt_top_asymmetry`). Type-II semantics in this
repo close on **one headline scalar gate** + non-Type-count
conservation/profile checks.

Required edit:
- Reduce `primary_gate_count` to 1.
- Demote `nusselt_top_asymmetry` out of `HARD_GATED` (e.g. to
  `CONSERVATION_INVARIANT` or new role that doesn't count toward
  Type-count).
- Rewrite §1/§3/§9 so the case closes on `nusselt_number` scalar gate
  alone, with conservation/profile checks visible but non-Type-count.

### F2-MED · Stage A.0 GO criterion still subjective

File refs: intake.yaml:127, 133, 186, 451

Words like "clean", "defensible", "confirms or pivots" leave the GO
condition open to re-litigation.

Required edit:
- Add explicit pass/fail checklist in intake:
  - exact paper + DOI + table/figure/page for `nusselt_number`
  - numeric `ref_value` landed in gold YAML
  - whitelist citation corrected
  - explicit two-branch rule for `w_max_nondim`: (a) exact locator
    found → eligible for v3 promotion (separate intake); (b) no exact
    locator → permanently advisory in this DEC.

### F3-MED · observable_scope shape malformed + missing out-of-scope guard

File refs: intake.yaml:148, 174

`observable_scope` is a flat list of observables, but the canonical
intake shape is `observable_scope.in_scope` + `.explicitly_out_of_scope`.

Required edit:
- Restore `in_scope` and `explicitly_out_of_scope` keys.
- List excluded surfaces explicitly:
  - periodic-sidewall variant
  - Type-I promotion path
  - any additional hard gate beyond the headline `nusselt_number`

## Extra notes (not findings, but informational)

- `fixedGradient T = 0` should be `zeroGradient` per OF tutorial syntax
  (intake.yaml:246 wording is approximate, not literal).
- This repo emits `buoyantFoam` on OpenFOAM 10, NOT
  `buoyantSimpleFoam` (legacy).
- Asymmetry tolerance 5% (not 2%) is the safer first-RBC threshold
  per Codex; matches what's in the file at line 165.

## Status of v1 findings

- F1-HIGH (case_type) — partially closed (II asserted but contract not
  reduced)
- F2-HIGH (citation) — closed
- F3-HIGH (A.0 mandatory) — partially closed (mandatory but criterion
  still subjective)
- F4-HIGH (BC + solver) — closed
- F5-MED (Stage A reorder) — closed
- F6-MED (codex_budget_rounds 5) — closed
- F7-LOW (v1→v2 bookkeeping) — closed
