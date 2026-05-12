---
status: v1 · single-instance pattern · codify on recurrence
first_observed: 2026-05-12
related_dec: V61-133 (cadence floor THRESHOLD=30), V61-198 (industrial-case sediment scale)
---

# Split-stack PR pattern (codex/stack-XX-*)

A PR composition strategy for landing large batches of work (≥10×
cadence threshold) atomically while staying within v2.3 governance.

## When the pattern fires

Trigger conditions (all three):

1. Local main is ≥3× THRESHOLD commits ahead of origin/main
   (THRESHOLD = 30 per V61-133, so ≥90 commits queued).
2. Work spans ≥3 charters or methodology surfaces (e.g. N-series
   charters + B-arc + APU bay pivot + sediment cases).
3. Direct push to origin/main blocked by `check_codex_cadence` hook
   without an audited override.

## How the 2026-05-12 instance played out

- **Control PR**: opened as Draft (PR #50) targeting `main`,
  publishing all 147 commits for review. State: CLOSED — never merged
  directly.
- **Split**: 10 stacked PRs (#51-#60), each `Base: codex/stack-NN`,
  `Head: codex/stack-(NN+1)`. Linear chain.
- **Layer scoping**: organized by charter / methodology surface
  - stack-00: CI baseline + cadence-hook isolation + tests that must
    pre-land for CI-cleanliness of later layers
  - stack-01: blueprint v3 + N2 mesh charters
  - stack-02: N3 physics + N4 BC
  - stack-03: N5 reports + N6 advisor
  - stack-04..05: B-arc + B-extension
  - stack-06: APU pivot + case methodology + 5-artifact A2
  - stack-07: industrial sediment cases 003-016
  - stack-08: case_003 ramp + V-series corpus injection
  - stack-09: artifact closeout (docs · governance · evidence)
- **Atomicity**: all 10 merged within 12 minutes (06:45-06:57 UTC ·
  `Merge pull request #51..#60`).
- **Hygiene split**: `8997584 test: restore baseline verification`
  (4-file test+typecheck baseline) was **explicitly broken across
  layers** (Step2Mesh → stack-01, PhysicsPanel → stack-02, etc.) to
  keep intermediate layers CI-clean. **stack-09 ended up docs-only**
  because the baseline patch moved earlier.

## Why this is consistent with v2.3 governance

- Each PR is independently reviewable — Codex round cap=3 still applies
  per-PR if any layer needed it.
- v2.3 1-sync-trigger (auth/signing/security boundary) — none of these
  10 layers crossed that surface; the stack is in the "async-post-merge
  or no Codex needed" tier.
- Cadence hook was bypassed via audited override for the control PR
  push only; individual layer PRs each had clean cadence inheritance.

## Risks / things to watch on recurrence

- **Stack ordering errors**: the dependency chain is linear; merging
  out of order = phantom conflicts. GitHub merge-when-ready works iff
  each child PR rebases as parents merge.
- **Single-failure cascade**: if stack-04 fails CI/review, stack-05..09
  cannot ship without rebasing. Plan for layer-cohesion.
- **Hygiene-split fragility**: splitting a single logical commit
  (8997584) across layers means each split must individually pass
  typecheck — fragile if any sub-file is forgotten.
- **Review surface explosion**: 10 PRs × per-PR review checks = 10×
  CI minutes. Acceptable when work batch is real, hostile when used to
  avoid one large review.

## What to codify if pattern recurs

On 2nd instance, lift this from "v1 single-instance" to
"recognized workflow" — promote to a sub-DEC scope methodology +
add to `.claude/methodology/` PR cookbook entry. Add concrete
PR-body template + branch-naming spec (current convention:
`codex/stack-NN-<short-slug>`).

## References

- Control PR: https://github.com/kogamishinyajerry-ops/cfd-harness-unified/pull/50 (CLOSED · 2026-05-12)
- Split PRs: #51..#60 (all MERGED 2026-05-12)
- Original batch source branch: `codex/artifact-closeout-20260512`
- Backup snapshot: `backup/main.before-origin-main-reset-20260512T151235`
  (preserved 10 backup commits with content equivalents on main · audit-verified 2026-05-12)
