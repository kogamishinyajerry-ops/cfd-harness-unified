# DEC-V61-109 · Kogami high-risk-PR review packet

**Trigger**: high-risk-PR per project CLAUDE.md §"Strategic package authoring"
(risk_class: high in merge_risk_summary.md → Kogami review required after
Codex APPROVE, before merge).

**Codex verdict ENUM**: APPROVE (R2 zero findings on commit `85b88e3`)

**Codex review chain**:
- R1 CHANGES_REQUIRED on commit `4a0fcd6` — 1 P2 (MED) finding:
  test_case_lock_dir_fd_relative_open_pins_case_dir didn't actually
  regress what it claimed. Pre-V109 path-based open would have passed
  it too.
- R1 P2 closure on commit `85b88e3`: rewrote the test to monkeypatch
  `_open_or_create_lock_fd` and perform an attacker-style swap
  (rename + symlink_to) BETWEEN fd_case open and lockfile open.
  Asserts .case_lock lands at the pinned inode (`moved/`), not the
  swapped malicious symlink target.
- R2 APPROVE on commit `85b88e3`: verified the rewritten test
  genuinely distinguishes pre-V109 from V109 behavior.

**Strategic package**:
- intent_summary.md: M7.1 milestone fit · business_goal: close
  V108-A documented residual on shared case_lock primitive ·
  affected_subsystems: case_lock, patch_classification store,
  setup_bc dispatcher, raw_dict editor route
- merge_risk_summary.md: risk_class=high · reversibility=easy ·
  blast_radius=cross-system

**Implementation summary** (commit `4a0fcd6` + test fix `85b88e3`):

The OLD case_lock opened the lockfile path with O_NOFOLLOW at the
FINAL component (`.case_lock`), but the case_dir itself was opened
by name. A planted/swapped case_dir symlink would redirect the
lockfile creation through the symlink target, leaking `.case_lock`
artifacts outside the case root and breaking the per-case
serialization invariant.

V109 fix:
1. Open case_dir with `O_RDONLY | O_NOFOLLOW | O_DIRECTORY` BEFORE
   the lockfile open. ELOOP/ENOTDIR translates to
   CaseLockError(failing_check="symlink_escape").
2. Open `.case_lock` via `dir_fd=fd_case` so path resolution is
   anchored at the now-pinned inode, not re-resolved via the
   case_dir path string. A swap of case_dir to a symlink AFTER
   fd_case is open has no effect on the lockfile location.
3. Wrap the auto-mkdir in try/except FileExistsError so a planted
   regular file at case_dir surfaces uniformly through the
   symlink_escape branch.
4. Portable atomic open-or-create (`_open_or_create_lock_fd`) to
   work around a Darwin kernel race in `openat(O_CREAT|O_NOFOLLOW)`
   under concurrent contention (reproduced manually 2/8 spurious
   ENOENT per round; closed by try-RDWR-then-EXCL-create-on-ENOENT
   pattern).

**Documented residuals + scope acknowledgments**:
- mkdir(parents=True) can still create intermediate dirs through
  a symlinked PARENT path. Out of scope for V109 (full fd-relative
  path creation is multi-tenant, not single-tenant threat model).
  Documented in the locking.py docstring.
- patch_classification_store still carries its `_assert_fd_still_matches_path`
  inode-drift check. With V109 in place this check is now belt-and-
  braces (case_lock itself rejects the swap before any work runs);
  Phase 2 cleanup to drop it is queued but out of V109 scope.

**Verification**:
- 7/7 case_lock tests green (3 pre-existing + 4 new V109 regressions)
- 78/78 case_lock-adjacent tests green
- 835/839 full backend pass; 4 failures are pre-existing V108
  baseline (test_case_export, test_convergence_attestor,
  test_g1_missing_target_quantity × 2). Zero new failures introduced.
- 1 V108-A test inverted: was pinning the documented residual
  (.case_lock leaks to symlink target); now asserts the residual
  is closed (test_patch_classification_store::test_symlink_escape_no_residual_lockfile_leak)

**Strategic fit**:
- Milestone: M7.1 imported-case → real-run hardening (per Kogami's
  RETRO-V61-V107-V108 strategic-fit note: "per-patch BC governance
  is a precondition for M7's imported case → real run flow")
- Closes the cross-cutting threat model gap that V108-A could only
  document, not fix
- Blast radius is cross-system but bounded by the pre-existing
  `failing_check="symlink_escape"` error contract that downstream
  routes already translate to 422

**Reviewer asks**:
1. Is the V109 fix scope-appropriate, or should it have included
   the parent-path symlink residual + the patch_classification_store
   `_assert_fd_still_matches_path` cleanup in the same DEC?
2. Are there strategic blind spots? E.g., does this scope adequately
   capture the §10.5.4a audit-required-surface treatment that
   RETRO-V61-V107-V108 R5 mandated?
3. The Darwin openat race workaround (`_open_or_create_lock_fd`)
   is a portability fix that emerged mid-implementation. Should it
   have been a separate DEC rather than absorbed into V109's scope?
