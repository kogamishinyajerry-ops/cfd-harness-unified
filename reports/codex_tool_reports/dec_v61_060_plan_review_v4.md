# DEC-V61-060 · Codex Pre-Stage-A Plan Review · v4

**Reviewer**: Codex GPT-5.4 (ksnbdajdjddkdd@gmail.com — switched from
sajihsmipoal after first attempt hung at 1h+ with 0 CPU activity)
**Submitted at**: 2026-04-25 ~19:55 +0800 (initial); retried 21:00 +0800
**Verdict**: APPROVE_PLAN_WITH_CHANGES
**Estimated pass rate**: 0.45
**Stage A.0 go/no-go**: GO

## Findings (1M + 1L; no HIGH)

### F1-MED · Batch D scope still reads like the pre-reshape surface

File refs: intake.yaml:167 (§3 contract), :593 (§7C acceptance),
:615 (§7D scope), :651 (§9 close)

Batch D scope listed `nu_top, w_max_nondim, roll_count_x` as
secondary_scalars allowlist, but the v4 contract enforceable
secondary is `nusselt_top_asymmetry`, NOT `nu_top` (which is an
internal extractor intermediate). Cross-section was ambiguous.

Required edit: align Batch D to v4 contract — make 4-card surface
explicit (`nusselt_number HARD_GATED`, `nusselt_top_asymmetry
NON_TYPE_HARD_INVARIANT`, `w_max_nondim PROVISIONAL_ADVISORY`,
`roll_count_x PROVISIONAL_ADVISORY`); state explicitly that `nu_top`
is a non-contract helper diagnostic.

### F2-LOW · Two text-only stale spots remain outside the operative fix

File refs: intake.yaml:152 (§3 heading), :472 (§6 pass-rate)

Required edits:
- §3 heading: include `NON_TYPE_HARD_INVARIANT` (was just
  `HARD_GATED + PROVISIONAL_ADVISORY split`)
- §6 pass-rate rationale: consolidate to single 0.45 narrative;
  remove conflicting "Honest 0.40" + "v3 raises..." mixed messaging

## Status of v3 findings

- v3 F1-HIGH (§7/§9 stale) — closed structurally in v4; no remaining
  live `2 HARD_GATED` / `≥2 hard-gated values` references in Batch
  C or §9 (only in historical v1/v2/v3 review-history blocks)

## Codex's other observations

- Stage C acceptance criteria i-iv concrete enough
- C.2 realistic as one semantic commit
- §9 waiver_allowed concrete enough
- Pass-rate 0.45 reasonable; Stage A coupled-stack risk unchanged
- Verdict: APPROVE_PLAN_WITH_CHANGES (with 2 verbatim-applicable
  changes; not REQUEST_CHANGES, so Stage A.0 may begin once fixes
  land)

## Operational note

First Codex attempt (sajihsmipoal account) hung at 1h+ with 0 CPU
activity (process in S/sleeping state, no network). Killed and
retried on ksnbdajdjddkdd (90% quota score); retry succeeded in
~5 minutes with full review output.

## v4 → v4-final patch (verbatim per CLAUDE.md 5-condition exception)

5-condition check satisfied:
1. Diff-level match Codex `Required edit` ✓ (literal wording)
2. Total ≤20 LOC ✓ (operative changes; §6 is text reflow)
3. Files ≤2 ✓ (single file: intake.yaml)
4. No public API change ✓ (planning artifact)
5. PR body references round + finding ID ✓ (commit cites v4 F1-MED + F2-LOW)

→ Stage A.0 GO.
