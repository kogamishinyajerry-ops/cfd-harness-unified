# DEC-V61-060 · Codex Pre-Stage-A Plan Review · v3

**Reviewer**: Codex GPT-5.4 (sajihsmipoal@gmail.com)
**Submitted at**: 2026-04-25 ~19:42 +0800
**Verdict**: REQUEST_CHANGES
**Estimated pass rate as written**: 0.40 (0.45 after intake-only fix)
**Stage A.0 go/no-go**: NO_GO

## Findings (1H)

### F1-HIGH · Stage C / Stage E still encode the pre-v3 gate contract

File refs: intake.yaml:174 (observable), :564-573 (Batch C scope),
:614-616 (§9 close)

`NON_TYPE_HARD_INVARIANT` introduced correctly in §3, but Batch C
still says `2 HARD_GATED + 2 PROVISIONAL_ADVISORY` and still claims
comparator logic "inherits without re-shipping", while §9 still
requires `≥2 hard-gated values`. v2 F1 is only partially closed:
§1/§3 were structurally fixed, but §7/§9 still assume the old
two-hard-gate model. Silently grows Stage C scope (current codebase
treats only `PROVISIONAL_ADVISORY` specially; `NON_TYPE_HARD_INVARIANT`
would otherwise be counted as verdict-bearing hard-gated by default).

Required edit:
- Rewrite Batch C to `1 HARD_GATED + 1 NON_TYPE_HARD_INVARIANT + 2 PROVISIONAL_ADVISORY`
- Remove "inherits without re-shipping"
- Add explicit Stage C acceptance criterion: `NON_TYPE_HARD_INVARIANT`
  blocking on violation but excluded from `primary_gate_count` and
  the hard-gated pass fraction
- Rewrite §9 close conditions: close on `nusselt_number` plus
  invariant satisfaction, NOT `≥2 hard-gated values`
- Replace `defensible exact figure citation` with literal A.0
  BRANCH-A / BRANCH-B condition

## Status of v2 findings

- F1-HIGH (Type-II contract) — partially closed (§1/§3 structurally
  fixed, but §7/§9 still stale → escalates to v3 F1-HIGH)
- F2-MED (A.0 GO criterion) — closed
- F3-MED (observable_scope shape) — closed
- INFO-1 (BC + solver name) — closed

## Codex's other observations (no findings)

- `NON_TYPE_HARD_INVARIANT` defensible as concept, but only if §7
  explicitly scopes the Stage C branch and acceptance criteria.
- A.0 6-checkbox GO list objective enough; no remaining subjective
  language inside A.0.
- 7-item explicitly_out_of_scope adequate; no obvious missing surface.
- Pass-rate 0.45 reasonable only after intake-only fix lands.
