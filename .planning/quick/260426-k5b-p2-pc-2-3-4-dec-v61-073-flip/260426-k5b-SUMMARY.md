---
quick_id: 260426-k5b
title: P2 三件套 PC-2/3/4 + DEC-V61-073 flip to Accepted
date: 2026-04-26
final_commit: 06e5f29
status: COMPLETE
---

# 260426-k5b · Summary

## Outcome

DEC-V61-073 flipped from `ACCEPTED_WITH_AMENDMENTS_PENDING_LANDING` to
`Accepted`. P2-T1 (DEC-V61-074, ExecutorMode ABC + 4-mode skeleton) is
**UNBLOCKED**. Methodology v2.0 §10.5 + §11 promote to **Active**.

## Commits landed

| # | Commit | What |
| --- | --- | --- |
| 1 | `cdedd6d` | PC-4 R1 — remove obsolete 5-surface §10.5.4a duplicate |
| 2 | `95e2c8b` | PC-3 R1 — sampling_audit.py + 8 unit tests |
| 3 | `f81624d` | PC-2 R1 — EXECUTOR_ABSTRACTION.md v0.2 + §5 + §6 (Codex CHANGES_REQUIRED, 5 findings) |
| 4 | `9cdac40` | PC-2 R2 — addressed 5 R1 findings (Codex still CHANGES_REQUIRED, 2 residual HIGH) |
| 5 | `50bb2eb` | PC-2 R3 — closed residual HIGH-1 + HIGH-2 → **Codex APPROVE** |
| 6 | `55f2642` | PC-3 R2 — addressed 1 HIGH + 2 MED + 1 LOW + 2 regex bugs; tests 8 → 24 → **Codex APPROVE** |
| 7 | `b03604a` | PC-4 R2 — closed §10.5.5 stale "5 surfaces" reference (Codex still CHANGES_REQUIRED, 1 new) |
| 8 | `25c4cd8` | PC-4 R3 — closed §10.5.5 stale "20→5 stays" rule reference → **Codex APPROVE** |
| 9 | `06e5f29` | DEC-V61-073 flip + PC closure addendum |

## Codex review summary (calibration data for future RETRO)

| PC | Estimated pass rate | Rounds needed | Outcome | Key finding category |
| --- | --- | --- | --- | --- |
| PC-2 | 0.85 (implicit) | 3 | APPROVE_AFTER_2_REVISIONS | Spec drift from actual code (manifest surface, MetricStatus enum, plane assignment) |
| PC-3 | 0.85 (implicit) | 2 | APPROVE_AFTER_1_REVISION | Mixed-commit blind spot, --json contract, raise-only enforcement, 2 regex bugs |
| PC-4 | 0.85 (implicit) | 3 | APPROVE_AFTER_2_REVISIONS | Stale narrative references contradicting amended rules |

DEC-V61-073's `external_gate_self_estimated_pass_rate: 0.85` was
honest within tolerance — every PC eventually approved, but each
needed at least one revision. Codex catches genuine drift between
spec text and code reality (PC-2), enforcement-script edge cases
(PC-3), and chronology-vs-current-rule contradictions in narrative
(PC-4) — not trivially-fixable typos. Self-pass-rate 0.85 is roughly
calibrated for "likely some mechanical fix-ups before APPROVE" and
that's what happened.

## Test posture

- Baseline at session start (`c65cbc7`): 860 passed / 1 flake / 2
  skipped (the flake `test_build_trust_gate_report_resolves_display_title_to_slug`
  passes isolated but fails under full-suite ordering — pre-existing
  test-isolation issue, unrelated to this PC arc).
- Final at session end (`06e5f29` on top of `4cb2aad` base which
  picked up parallel-session GOV-1 commits): **884 passed / 1 same
  flake / 2 skipped**. PC-3 added 24 new tests (16 covering R1
  regression categories), 0 regressions introduced.

## Concrete §10.5 numerical values now Active

- **Token budget cap**: 100,000 per fire (raise-only — `--cap` or
  `SAMPLING_AUDIT_CAP` below floor rejected with exit code 3 +
  stderr error referencing DEC-V61-073 §10.5.4b).
- **Ratchet post-`DEGRADATION_RULE_AT_RISK`**: 5 → 7 → 10 → 15 → 20.
- **§10.5.4a 7 audit-required surfaces** enumerated; surfaces 6+7
  (correction_spec/, .planning/case_profiles/) are the new
  DEC-V61-073 A4 additions, fully covered by the
  `scripts/methodology/sampling_audit.py` regex grep + a smoke test
  in `tests/methodology/test_sampling_audit.py`.

## Known follow-ups (NOT blockers)

- The `.planning/specs/EXECUTOR_ABSTRACTION_hybrid_init_invariant.md`
  amendment file is now subsumed by the canonical
  `docs/specs/EXECUTOR_ABSTRACTION.md` §5. It can be removed once
  the Notion canonical doc syncs from the new file (per §1 authority
  clause). Not removed in this arc to keep the audit trail intact.
- The pre-existing flaky test (`test_build_trust_gate_report_resolves_display_title_to_slug`)
  is a known test-isolation issue, not introduced by this PC arc.
  Stays as a known follow-up for a future debugging session.
- Notion sync for DEC-V61-073's flipped status pending (frontmatter
  notes `re-sync pending after PC closure`).

## What did NOT change

- No `src/` source code touched in this arc (other than `scripts/`
  and `tests/` which are infrastructure, not src/).
- Trust-core 5 modules untouched and still read-only: `src/gold_standards/`,
  `src/auto_verifier/`, `src/convergence_attestor.py`, `src/audit_package/`,
  `src/foam_agent_adapter.py`.
- No ROADMAP.md update (quick task).
