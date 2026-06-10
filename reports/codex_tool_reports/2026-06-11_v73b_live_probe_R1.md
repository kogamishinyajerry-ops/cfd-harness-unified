# Codex review R1 — V73.B fix round (commit e930d6a)

- relay: 86gs (gpt-5.4 xhigh) · `codex review --commit e930d6a` · 2026-06-11
- verdict: CHANGES_REQUIRED-equivalent — 2×P2, no P1 (narrowing 3→2)
- raw transcript: not archived in-repo (embedded diffs re-trigger the
  pre-push cadence scanner); complete findings verbatim below.

## Findings

- [P2] Gate RUN_DONE on a successful solve and reconstruct —
  reports/showcase_aero/_v73b_rae2822_probe/REPRODUCE.md:39-42
  The documented snippet reaches `touch RUN_DONE` even when checkMesh /
  rhoSimpleFoam / reconstructPar exit non-zero → freeze can mistake a
  partial refresh for the converged probe.

- [P2] Propagate the rhoSimpleFoam demotion through the matrix —
  .planning/cfd_capability_matrix.md:38
  §2 row demoted but the SST×COMP-STEADY regime cell in §1, the §1/§8
  derived counters, the §6 narrative and the totalPressure BC evidence row
  still carried the aspirational claim.

## Disposition (fix commit c296b18)

1. REPRODUCE.md script: `set -e` fail-fast; RUN_DONE only after all steps
   exit 0.
2. Matrix: §1 cell → GAP-TRACKED; §1 counters 8/24→7/24; §8 aggregate
   35/59→33/59 (−2); §6 narrative corrected; totalPressure evidence
   re-pointed at the real advisor surface. Bundle re-frozen.
