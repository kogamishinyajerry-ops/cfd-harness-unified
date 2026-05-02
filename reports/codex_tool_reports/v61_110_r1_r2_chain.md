# DEC-V61-110 · Codex R1-R2 chain

**DEC**: `.planning/decisions/2026-05-03_v61_110_drop_dead_symlink_branch.md`
**Trigger**: RETRO-V61-001 risk-tier · backend logic change to security-critical primitive (`patch_classification_store._assert_fd_still_matches_path`)
**Backend**: 86gamestore (`~/.codex-relay`, gpt-5.4, xhigh effort)
**Result**: 2 rounds → APPROVE
**Self-estimated pass-rate vs actual**: 85% (R0 estimate before Codex caught the reachability error) → ~50% actual (1 CHANGES_REQUIRED + 1 APPROVE)

## Round 1 (commit 80ed3a8 · CHANGES_REQUIRED)

**Original V61-110 R0 scope**: drop the now-unreachable S_ISLNK branch in
`_assert_fd_still_matches_path` after V109's case_lock O_NOFOLLOW fix.
Author's framing: "V109 closes the swap-to-symlink case at the case_lock
layer; the S_ISLNK branch is dead code; keep only the inode-mismatch
check (still load-bearing for delete-recreate)".

### Codex finding (1 P2)

**[P2] Restore explicit symlink classification in post-lock drift check**
— `ui/backend/services/case_solve/patch_classification_store.py:200-204`

> This branch is not actually dead in the reachable race where
> `case_dir` is renamed away and replaced with a symlink *after*
> `case_lock` has opened the directory fd but before
> `_assert_fd_still_matches_path()` runs.
> `ui/backend/tests/test_case_lock_race.py::test_case_lock_dir_fd_pinning_survives_swap_after_fd_open`
> already proves `case_lock` can survive that swap and still yield, so
> `os.stat(..., follow_symlinks=False)` here can legitimately see a
> symlink. Without the removed `S_ISLNK` check we now fall through to
> the inode-mismatch path, which
> `routes/case_patch_classification._store_error_to_http()` maps to
> `case_dir_missing`/404 instead of the intended `symlink_escape`/422,
> regressing the containment-violation contract for PUT/DELETE on a
> real race path.

Working as intended — Codex caught the reachability error at static
review, before the regression could ship. R0's framing ("V109 makes
the branch unreachable") was wrong; V109 protects only case_lock's
OPEN moment, not what happens after the lock yields control with
fd_case pinned.

## Round 2 (commit 767ed6c · APPROVE)

**Narrowed V61-110 R1 scope** (this DEC's final decision):
1. Restored the `S_ISLNK` branch — production code now identical to
   pre-V110.
2. Updated `_assert_fd_still_matches_path` docstring to reflect
   post-V109/V110 reality: BOTH branches load-bearing
   (delete-recreate via inode-mismatch; post-lock-yield swap via
   S_ISLNK).
3. Added regression test
   `test_assert_fd_still_matches_path_catches_post_lock_yield_symlink_swap`
   in `ui/backend/tests/test_patch_classification_store.py`. Test
   exercises the exact race Codex described and locks the contract.

### Pre-removal verification

To prove the regression test is sound, temporarily deleted the
S_ISLNK branch and re-ran the new test. Result:

```
FAILED test_assert_fd_still_matches_path_catches_post_lock_yield_symlink_swap
AssertionError: assert 'case_dir_missing' == 'symlink_escape'
  - symlink_escape
  + case_dir_missing
```

Matches Codex's predicted 422→404 regression exactly. Restored the
branch immediately after verification. The test now fails LOUD if
any future "this looks dead, let's remove it" attempt repeats the
R0 mistake.

### Codex verdict (R2)

> The commit restores the `S_ISLNK` handling that the prior change
> had removed incorrectly, and the new regression test covers the
> post-lock-yield symlink-swap path that motivates the fix. I did
> not identify any new functional regressions in the touched
> production code or tests.

**APPROVE.**

## Verification (R2 final state)

- 79/79 case_lock-adjacent tests green (78 pre-V110 + 1 new
  V61-110 regression):
  - `test_patch_classification_store.py` (20 · +1 new regression)
  - `test_case_lock_race.py` (7)
  - `test_case_dicts_route_race.py` (4)
  - `test_patch_classification_route.py` (10)
  - `test_patch_classification_override.py` (11)
  - `test_bc_setup_from_stl_patches.py` (27)

## Methodology takeaway (for next RETRO)

When claiming "X becomes dead code after upstream Y", verify the
claim by **attempting removal and running ALL race-path regression
tests**, not just static reasoning. R0's "drop the dead branch"
went all the way to a landed commit before Codex caught the
reachability error in R1. Static reasoning saw the V109 O_NOFOLLOW
guard and concluded "swap-to-symlink can never reach the assert" —
true at the OPEN moment, false at the post-lock-yield moment.

The new regression test (`test_assert_fd_still_matches_path_catches
_post_lock_yield_symlink_swap`) now exists to make this kind of
reasoning error fail loudly in CI. Adding it pays the cost of the
R1 round forward — the next reviewer who looks at the S_ISLNK
branch and thinks "this looks dead" will see the test and the
docstring's "do NOT remove without re-checking this race" warning.

## Counter

`autonomous_governance_counter_v61` advances by **+1** on V61-110
acceptance (autonomous_governance: true · single-DEC arc with one
CHANGES_REQUIRED → APPROVE Codex round).
