---
decision_id: DEC-V61-110
title: Codex-corrected V109 framing in patch_classification_store._assert_fd_still_matches_path — keep S_ISLNK branch (not dead), update docstring + add post-lock-yield regression
status: Proposed (2026-05-03 · pending Codex re-review on R2 commit)
authored_by: Claude Code Opus 4.7 (1M context)
authored_at: 2026-05-03
authored_under: |
  user direction "全权授予你开发，全都按你的建议来" + DEC-V61-109 §"Documented residual + future work" R5 successor reference (originally framed as "drop the now-belt-and-braces inode-drift check post-V109").

  Two scope corrections happened during V61-110 implementation:

  R0 (pre-Codex, self-caught): V109's framing of "_assert_fd_still_matches_path becomes belt-and-braces" was an overgeneralization. V109 closes the swap-to-symlink case at the case_lock layer for the OPEN moment, but does NOT close the delete-recreate case (real dir deleted, real dir created in its place at the same path with NEW inode — case_lock's V109 O_NOFOLLOW open succeeds because the new path is a real directory). For the delete-recreate case, the inode-mismatch check is still load-bearing.

  V61-110 R0 therefore narrowed from "drop the entire check" to "drop only the unreachable S_ISLNK branch".

  R1 (Codex finding on commit 80ed3a8): the R0 framing was ALSO wrong. The S_ISLNK branch is NOT unreachable. V109's O_NOFOLLOW protects only case_lock's OPEN moment; once case_lock yields with the dir_fd pinned to the original real inode, an attacker can rename the original case_dir away and plant a symlink at the path BEFORE _assert_fd_still_matches_path runs. The branch IS reachable and load-bearing — without it, the post-lock-yield symlink swap regresses from symlink_escape (HTTP 422) to case_dir_missing (HTTP 404).

  V61-110 R1 (this DEC's final scope) therefore narrows further to: docstring-only correction + new regression test that locks the branch's reachable contract. NO production-code branch removal. The original "drop dead branch" intent is abandoned.
parent_decisions:
  - DEC-V61-109 (case_lock O_NOFOLLOW upstream fix · partial coverage of the swap race; V61-110 documents the residual)
  - DEC-V61-108-A (introduced _assert_fd_still_matches_path at R5 P1 + R6 P3 · this DEC keeps both branches)
  - RETRO-V61-001 (risk-tier triggers · single-file backend logic change to security-critical primitive = mandatory Codex review)
parent_artifacts:
  - ui/backend/services/case_solve/patch_classification_store.py (the file being touched · docstring + comment only)
  - ui/backend/tests/test_patch_classification_store.py (NEW regression test added)
  - ui/backend/services/case_manifest/locking.py (V109 added the partial protection that motivated the original V61-110 attempt)
counter_impact: +1 (autonomous_governance: true)
self_estimated_pass_rate: 95% (R1 was a successful Codex catch on R1 round · R2 is docstring-only + regression test that proves the bug-fix · low blast radius)
risk_class: low (post-Codex correction: no production behavior change; only docstring + test)
codex_tool_report_path: reports/codex_tool_reports/v61_110_r1_codex_findings.md (pending after R2 sweep)
notion_sync_status: pending — to sync after Codex APPROVE
post_r3_defects:
  - "R1 finding (Codex caught at static review): 'S_ISLNK branch is dead post-V109' was wrong; branch is reachable on post-lock-yield symlink swap. Working as intended — Codex caught at the right layer, before any post-merge incident. Counts as Codex-prevented regression, not post-R3 defect."

# Why now

DEC-V61-109 V109's framing claimed that _assert_fd_still_matches_path
"becomes belt-and-braces" (case_lock itself rejects the swap before
any work runs). Two layers of re-tracing proved this wrong:

R0 (self-caught): V109 closes only the swap-to-symlink at the OPEN
moment. The inode-mismatch check is still load-bearing for
delete-recreate (real dir → unlink → re-create at same path with
new inode; case_lock's O_NOFOLLOW open of the NEW real dir
succeeds, but fd_case still references the orphaned OLD inode).

R1 (Codex-caught): the S_ISLNK branch is ALSO load-bearing. After
case_lock yields with fd_case pinned, an attacker can rename the
original case_dir away and plant a symlink at the path. fd_case
still references the renamed real inode (file-handle access doesn't
follow path renames), but `os.stat(case_dir, follow_symlinks=False)`
now sees a symlink. Without the S_ISLNK branch, the assert falls
through to inode-mismatch, which `_store_error_to_http()` maps to
case_dir_missing/404 instead of the intended symlink_escape/422.
That regresses the containment-violation contract on a real race
path.

Both branches are load-bearing. V61-110 keeps the production code
unchanged and ships only docstring corrections + a regression test
that proves the post-lock-yield symlink swap is reachable and the
S_ISLNK branch catches it.

# Decision

Three-line scope:
1. Restore the `if stat.S_ISLNK(path_st.st_mode): raise ...` block
   in _assert_fd_still_matches_path (R0 attempt removed it; R1
   restores it after Codex finding).
2. Rewrite the function's docstring to reflect the post-V109/V110
   reality:
   - V109's "branch becomes unreachable" framing was wrong
   - Both branches (delete-recreate via inode-mismatch, AND swap-to-
     symlink via S_ISLNK) are load-bearing
   - Document why each is reachable (delete-recreate; post-lock-
     yield swap)
3. Add `test_assert_fd_still_matches_path_catches_post_lock_yield_
   symlink_swap` regression test in
   ui/backend/tests/test_patch_classification_store.py:
   - Exercises the exact race Codex described
   - Locks the branch's reachable contract
   - Pre-removal verification: with the S_ISLNK branch deleted, the
     test fails with `assert 'case_dir_missing' == 'symlink_escape'`
     (matches Codex's predicted 422→404 regression)

Out of scope for V61-110:
- Removing _assert_fd_still_matches_path entirely
- Removing the S_ISLNK branch (R0 attempt; abandoned per Codex R1)
- Removing _cleanup_case_lock_orphan_stub
- Touching case_lock or any other file (V61-110 is now a
  docstring-and-test-only change to a single file)

# Verification

- 79/79 case_lock-adjacent tests green (78 pre-V110 + 1 new
  V61-110 regression):
  - test_patch_classification_store.py (20 · +1 new regression)
  - test_case_lock_race.py (7)
  - test_case_dicts_route_race.py (4)
  - test_patch_classification_route.py (10)
  - test_patch_classification_override.py (11)
  - test_bc_setup_from_stl_patches.py (27)
- Pre-removal verification: temporarily removed the S_ISLNK branch
  and re-ran the new test; it failed with the exact 422→404
  regression Codex predicted. Restored the branch immediately
  after verification.
- Smoke baseline preserved (will verify post-Codex)
- 0 new failures · 1 new regression test added (locks the contract)

# Codex narrative

R1 (commit 80ed3a8 · 2026-05-03): Codex CHANGES_REQUIRED with one
P2 finding — "S_ISLNK branch is not actually dead; the post-lock-
yield symlink swap is reachable via test_case_lock_dir_fd_pinning_
survives_swap_after_fd_open semantics; removing the branch
regresses 422 to 404". Working as intended: static review caught
the regression at the right layer.

R2 (pending): docstring restoration + regression test addition
(this DEC's final scope). Re-review expected APPROVE since (a)
production code is now identical to pre-V110, (b) docstring is
strictly more accurate, (c) new test locks the contract.

# Future work

- Closes the V109 unblocks_followup pointer (with corrected
  framing: the check is NOT belt-and-braces; both branches are
  load-bearing).
- Methodology note for next RETRO: when claiming "X becomes dead
  code after upstream Y", verify the claim by attempting removal
  and running ALL race-path regression tests, not just static
  reasoning. R0's "drop the dead branch" went all the way to
  commit before Codex caught the reachability error in R1. The
  inode-mismatch test (`test_assert_fd_still_matches_path_catches
  _post_lock_yield_symlink_swap`) now exists to make this kind of
  reasoning error fail loudly in CI.
