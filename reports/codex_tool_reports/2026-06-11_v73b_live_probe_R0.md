# Codex review R0 — V73.B RAE 2822 live probe (commit 7e8913e)

- relay: 86gs (gpt-5.4 xhigh) · `codex review --commit 7e8913e` · 2026-06-11
- verdict: CHANGES_REQUIRED-equivalent — 3×P2, no P1
- raw transcript: not archived in-repo (embedded diffs re-trigger the
  pre-push cadence scanner — known trailer trap); summary below is the
  complete findings list verbatim.

## Findings

- [P2] Remove wrapper-only prerequisites from the freeze workflow —
  scripts/p4/freeze_rae2822_probe.sh:19
  REPRODUCE.md's documented solve path never creates RUN_DONE or the log.*
  files the freeze script requires → the committed reproduce→freeze
  workflow is unusable without out-of-band steps.

- [P2] Validate bundle inputs before deleting the old frozen probe —
  scripts/p4/freeze_rae2822_probe.sh:29-31
  The script wipes reports/showcase_aero/_v73b_rae2822_probe before
  verifying coefficient.dat / surfaceFieldValue.dat / yPlus.dat / log.*;
  a failed refresh destroys the last good frozen bundle.

- [P2] Don't promote rhoSimpleFoam to PR from an ENFORCED FAIL —
  .planning/cfd_capability_matrix.md:38
  The matrix contract requires a TrustGate=PASS anchor for ✅ PR; the V73.B
  probe is frozen as tier-2 ENFORCED FAIL → downstream planning would treat
  compressible steady RANS as proven.

## Disposition (fix commit 225074f)

1. REPRODUCE.md step-2 script now emits the exact log.* names + RUN_DONE.
2. freeze script: `require` checks for ALL inputs hoisted BEFORE the wipe.
3. matrix: rhoSimpleFoam → GAP-TRACKED (honest-CONFLICT note), totals
   7/10 → 6/10, onboarding + DEC matched (V61-233 R0 correction precedent).
