---
decision_id: DEC-V61-110
title: Drop the now-unreachable S_ISLNK branch in patch_classification_store._assert_fd_still_matches_path (V109 follow-up)
status: Proposed (2026-05-03 · pending Codex review)
authored_by: Claude Code Opus 4.7 (1M context)
authored_at: 2026-05-03
authored_under: |
  user direction "全权授予你开发，全都按你的建议来" + DEC-V61-109 §"Documented residual + future work" R5 successor reference (unblocks_followup: V61-110 candidate · drop the now-belt-and-braces inode-drift check post-V109).

  Important scope clarification surfaced during implementation: V109's framing of "_assert_fd_still_matches_path becomes belt-and-braces" was an overgeneralization. Re-tracing the threat model: V109 closes the swap-to-symlink case at the case_lock layer, but does NOT close the delete-recreate case (real dir deleted, real dir created in its place at the same path with NEW inode — case_lock's V109 O_NOFOLLOW open succeeds because the new path is a real directory, not a symlink). For the delete-recreate case, the inode-mismatch check is still load-bearing.

  V61-110 therefore narrows to "drop the unreachable S_ISLNK branch", not "drop the entire check". The remaining check (FileNotFoundError + ino/dev mismatch) stays.
parent_decisions:
  - DEC-V61-109 (case_lock O_NOFOLLOW upstream fix · made the S_ISLNK branch unreachable; DEC-V61-110 cleans up the dead code)
  - DEC-V61-108-A (introduced _assert_fd_still_matches_path at R5 P1 + R6 P3 · this DEC removes the R6 P3 portion only)
  - RETRO-V61-001 (risk-tier triggers · single-file backend logic change to security-critical primitive = mandatory Codex review)
parent_artifacts:
  - ui/backend/services/case_solve/patch_classification_store.py (the file being touched)
  - ui/backend/services/case_manifest/locking.py (V109 added the upstream protection that makes the S_ISLNK branch dead)
  - ui/backend/tests/test_patch_classification_store.py:test_upsert_returns_symlink_escape_when_path_swapped_to_symlink (the test that used to exercise the S_ISLNK branch; now exercises the case_lock path with the same failing_check enum)
counter_impact: +1 (autonomous_governance: true)
self_estimated_pass_rate: 85% (small dead-code removal · single file · single function · all tests preserved · low blast radius)
risk_class: low (per Kogami high-risk-PR exemption: not multi-file, not new API contract, not new file format, not security-sensitive operator endpoint)
codex_tool_report_path: (pending)
notion_sync_status: pending — to sync after Codex APPROVE

# Why now

DEC-V61-109 V109's framing claimed that _assert_fd_still_matches_path
"becomes belt-and-braces" (case_lock itself rejects the swap before
any work runs). On re-tracing during V61-110 implementation, that
framing turned out to be partially wrong:

- V109 DOES close the swap-to-symlink case (case_lock's
  O_NOFOLLOW|O_DIRECTORY open of case_dir raises ELOOP →
  CaseLockError(symlink_escape) BEFORE any post-lock check runs).
- V109 does NOT close the delete-recreate case (real dir deleted then
  re-created at the same path with a NEW inode; case_lock's
  O_NOFOLLOW open succeeds because the new path is a real directory).

So the inode-mismatch check inside _assert_fd_still_matches_path is
still load-bearing for the delete-recreate case. Only the S_ISLNK
branch within that function is unreachable post-V109.

V61-110 narrows to: remove just the dead S_ISLNK branch + update the
docstring to reflect the corrected threat model. This is the right
shape — Kogami P2 #2's "tracked successor reference" framing is
preserved, V109's framing is corrected, and the live check stays
load-bearing for the case it actually still covers.

# Decision

Two-line scope:
1. Remove the `if stat.S_ISLNK(path_st.st_mode): raise ...` block
   from _assert_fd_still_matches_path (lines 222-229 pre-V110).
2. Rewrite the function's docstring to:
   - Drop the R6 P3 narrative (no longer applies)
   - Add the V109/V110 closure note explaining what's removed and
     why it's safe
   - Document the post-V109/V110 coverage (delete-recreate case
     remains; symlink-replacement is upstream's job)

Out of scope for V61-110:
- Removing _assert_fd_still_matches_path entirely (would re-open the
  delete-recreate race)
- Removing _cleanup_case_lock_orphan_stub (still needed for the
  case_dir_missing branch which is still reachable)
- Touching case_lock or any other file (V61-110 is a targeted
  dead-code removal in a single function)

# Verification

- 78/78 case_lock-adjacent tests green post-removal:
  - test_patch_classification_store.py (19 tests · including the
    swap-to-symlink test which now exercises the case_lock path
    instead of the S_ISLNK branch; same failing_check enum so the
    assertion is unchanged)
  - test_case_lock_race.py (7 tests)
  - test_case_dicts_route_race.py (4 tests)
  - test_patch_classification_route.py (10 tests)
  - test_patch_classification_override.py (11 tests)
  - test_bc_setup_from_stl_patches.py (27 tests)
- Smoke baseline preserved (will verify post-Codex)
- 0 new failures expected (this is dead-code removal, not behavior
  change)

# Codex narrative

(Pending; review after this DEC commits.)

# Future work

Closes the V109 unblocks_followup pointer. No further follow-up
expected — the inode-mismatch check is correct as-is for its
remaining responsibility (delete-recreate detection).
