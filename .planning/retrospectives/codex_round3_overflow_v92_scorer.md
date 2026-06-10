# Codex round-cap overflow · V92 scorer arc (DEC-V92-charter)

Date: 2026-06-10 · Review chain: R0 (a448e9d) → fix 2d06799 → R1 → fix 18530bd → R2 (cap=3 reached)

## Disposition summary

| Round | Finding | Severity | Disposition |
|---|---|---|---|
| R0 | pw_vote counted per tests[] instance, not per spec (CROSSBROWSER inflation) | P2 | FIXED 2d06799 |
| R1 | skipped legs vetoed spec as confirmed_failed | P2 | FIXED 18530bd |
| R2 | tests[].status outcome "skipped" masks interrupted/did-not-run legs | P1 | FIXED (verbatim Codex round-2 P1 — skip marker is result-level only) |
| R2 | all-skipped report → total==0 → score_ux.sh labels it "playwright json parse failure" | P2 | **THIS QUEUE ENTRY** (below) |

## R2 P2 (queued, not fixed)

**Finding (verbatim scope)**: if every project leg of every spec is
skipped, `vote()` returns a valid report with `total == 0`;
`scripts/governance/v78_fleet/score_ux.sh` interprets `total == 0` as
`playwright json parse failure · 0 tests recognized`, so a valid
all-skipped run is mislabeled as a parser failure. Codex: "If fully
skipped specs are meant to be neutral, the caller contract needs to
change in the same patch."

**Why queued instead of fixed at cap**:
- Failure direction is **pessimistic / fail-closed**: an all-skipped
  suite scores as a failure demanding attention — it can never inflate
  a score. (Same class as MicroCOMAC 批19 R2 P2 precedent: pessimistic
  value distortion ≠ gate-safety defect → retro queue, no round 4.)
- The path requires the ENTIRE ui suite to be skipped — no current spec
  in `ui/frontend` is conditionally skipped; reaching total==0 today
  implies something genuinely abnormal, where a loud failure is
  arguably the right behavior anyway.
- A correct fix changes the pw_vote ↔ score_ux caller contract (new
  `skipped_specs` field + a third classification "all-skipped · no
  evidence" distinct from both parse-failure and pass). That is a
  contract design decision, not a verbatim landing.

**Proposed fix for next scoring-evolution arc**: pw_vote emits
`skipped_specs` count; score_ux.sh branches `total==0 && skipped>0` →
honest_note "all specs skipped · no UX evidence this run" with the same
failing score as today (keeps fail-closed), only the LABEL stops lying
about a parse failure. Rollback trigger unchanged from DEC-V92-charter.

**Owner**: user ratification at next retro (per v2.3 round cap=3 rule).
