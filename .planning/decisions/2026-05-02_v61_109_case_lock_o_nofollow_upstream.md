---
decision_id: DEC-V61-109
title: case_lock O_NOFOLLOW upstream fix — close DEC-V61-108 Phase A R9 documented residual
status: Accepted (2026-05-02 · Codex 2-round arc R1 CHANGES_REQUIRED → R2 APPROVE on commit 85b88e3 · Kogami high-risk-PR review APPROVE_WITH_COMMENTS, all 4 findings closed inline in this DEC body · recommended_next=merge)
authored_by: Claude Code Opus 4.7 (1M context)
authored_at: 2026-05-02
authored_under: |
  user direction "全权授予你开发，全都按你的建议来" + RETRO-V61-V107-V108 R5
  recommendation that documented the case_lock symlink-swap residual as
  DEC-V61-109 candidate with §10.5.4a high-risk-PR Kogami escalation
  required.
parent_decisions:
  - DEC-V61-108-A (per-patch BC override store · documented this DEC's residual at R9)
  - RETRO-V61-V107-V108 (R5 explicitly mandated this DEC's filing + Kogami high-risk-PR escalation)
  - DEC-V61-102 (case_lock origin · Phase 1 round-3 P1-HIGH closure created the primitive this DEC hardens)
  - RETRO-V61-001 (risk-tier triggers · shared-infra primitive change + new threat-surface = mandatory Codex review + Kogami high-risk-PR per project CLAUDE.md §"Strategic package authoring")
parent_artifacts:
  - ui/backend/services/case_manifest/locking.py (the primitive being hardened)
  - ui/backend/services/case_solve/patch_classification_store.py (current downstream caller; carries belt-and-braces inode-drift check that V109 supersedes — see "Documented residual" §)
  - ui/backend/tests/test_case_lock_race.py (existing case_lock test suite; extended with 4 new V109 regressions)
  - ui/backend/tests/test_patch_classification_store.py (V108-A "pin documented residual" test inverted to "assert residual closed")
counter_impact: +1 (autonomous_governance: true)
self_estimated_pass_rate: 60% (per RETRO-V61-V107-V108 R1 calibration baseline downgrade for shared-infra primitives — but V109's surface is genuinely small, single-file, well-bounded; raised to 60 from the 0.30 baseline · prior calibration debt acknowledged)
actual_pass_rate: 50% (Codex required 2 rounds — 1 R1 P2 finding on test quality, not on implementation; V109's locking.py was unchanged across the closure round per Codex R2 confirmation)
codex_tool_report_path: reports/codex_tool_reports/v61_109_r1_r2_chain.md (R1-R2 full chain)
kogami_review_path: .planning/reviews/kogami/v109_case_lock_pr_review_2026-05-02/review.md
kogami_verdict: APPROVE_WITH_COMMENTS
kogami_recommended_next: merge
kogami_findings_addressed: |
  P2 #1 (Darwin workaround scope-folding rationale) — closed inline in §"Darwin openat race workaround scope decision"
  P2 #2 (patch_classification belt-and-braces cleanup tracked) — closed inline in §"Documented residual + future work" with explicit successor reference unblocks_followup: V61-110 candidate
  P2 #3 (§10.5.4a audit-required-surface evaluation) — closed inline in §"§10.5.4a audit-required-surface evaluation"
  P3 (verification table cross-reference dependency) — closed inline by naming the 4 pre-existing failing tests in §"Verification"
implementation_commits:
  - 4a0fcd6 (feat: O_NOFOLLOW upstream fix on case_dir + Darwin race workaround + 4 new tests)
  - 85b88e3 (test: close Codex R1 P2 with real fd-pinning regression)
unblocks_followup: |
  V61-110 candidate · patch_classification_store cleanup. With V109 in place, the
  patch_classification_store ``_assert_fd_still_matches_path`` post-lock check
  becomes belt-and-braces (case_lock itself rejects the swap before any work
  runs). Removing it is a small refactor that touches only the
  patch_classification_store module — bounded, low-risk, queued as separate
  DEC-V61-110 to maintain trackability per Kogami P2 #2.
notion_sync_status: pending — to sync 2026-05-02 with the V109 chain report

# Why now

DEC-V61-108 Phase A R9 documented the residual: case_lock's lockfile
path was already O_NOFOLLOW-protected at its FINAL component
(`.case_lock`), but the case directory itself was opened by name. A
planted/swapped case_dir symlink would redirect the lockfile creation
through the symlink target, leaking `.case_lock` artifacts outside the
case root and breaking the per-case serialization invariant.

V108-A R9 closed the immediate Phase A scope by reverting cleanup on
the symlink_escape branch and accepting the residual, with the
explicit note that the proper fix is at the case_lock layer. RETRO-
V61-V107-V108 R5 then mandated this DEC be filed with §10.5.4a high-
risk-PR Kogami escalation. V109 is that fix.

# Decision

Open `case_dir` itself with `O_RDONLY | O_NOFOLLOW | O_DIRECTORY`
BEFORE the lockfile open, then open `.case_lock` relative to the
pinned fd via `dir_fd=fd_case`:

```python
fd_case = os.open(
    str(case_dir),
    os.O_RDONLY | os.O_NOFOLLOW | os.O_DIRECTORY,
)
fd = _open_or_create_lock_fd(fd_case)  # opens .case_lock relative to fd_case
```

A swap of `case_dir` to a symlink AFTER `fd_case` is open has no
effect on the lockfile location — the kernel resolves
`_LOCK_FILENAME` against `fd_case`'s referent inode, not against the
path string. ELOOP/ENOTDIR on the case_dir open translates to
`CaseLockError(failing_check="symlink_escape")`, the same uniform
error contract downstream callers already translate to a structured
422 response.

Defense-in-depth additions:
1. Wrap the auto-mkdir in `try/except FileExistsError` so a planted
   regular file at case_dir surfaces uniformly through the
   symlink_escape branch (otherwise raw `FileExistsError` would
   leak past the route layer's translation).
2. Portable atomic open-or-create (`_open_or_create_lock_fd`) for
   the Darwin race below.

# Darwin openat race workaround scope decision (closes Kogami P2 #1)

During implementation, manual reproduction surfaced a Darwin kernel
race: `openat(O_CREAT | O_NOFOLLOW)` under concurrent contention
returns ENOENT for 2/8 callers per round, despite the file being
created by another caller in the same race window. Linux's openat
does not exhibit this. The standard portable atomic open-or-create
pattern closes it: try `O_RDWR | O_NOFOLLOW` first; on ENOENT retry
with `O_RDWR | O_CREAT | O_EXCL | O_NOFOLLOW`; on EEXIST loop back
to the existing-open path. Both branches preserve `O_NOFOLLOW`.

**Scope decision per RETRO-V61-V107-V108 R3 (avoid V107.5 R16-style
"pragmatic scope reduction" precedent)**: the Darwin workaround is
in-scope for V109 because:
- It is a same-blast-radius portability fix — the workaround is
  fully local to `_open_or_create_lock_fd` (one helper function in
  the same module being hardened)
- It shares the V109 threat model — both the symlink-swap fix and
  the openat race are about correct behavior of the
  fd_case-relative lockfile open under adversarial/concurrent
  conditions
- Without it, V109's atomic open-or-create cannot land cross-platform
  (Darwin is the development platform; the macOS-specific race
  would deadlock the dogfood smoke runner immediately)

This is option (a) per Kogami P2 #1 recommendation. It is NOT a
"pragmatic scope reduction" of the kind RETRO-V61-V107-V108 R3 ruled
non-repeating — the Darwin fix passes through full Codex review on
its own merits (see the chain report) and is bounded to the same
threat model as the original V109 scope, not a side-quest.

# §10.5.4a audit-required-surface evaluation (closes Kogami P2 #3)

The V109 fix hardens `case_lock`, which is upstream of two existing
§10.5.4a audit-required surfaces:
- Surface #1: FoamAgentExecutor call sites (which acquire case_lock
  indirectly through `bc_setup._author_dicts` and
  `_author_channel_dicts`)
- Surface #5: `user_drafts → TaskSpec` plumbing (which acquires
  case_lock through `routes/case_dicts.post_raw_dict`)

**Disposition: option (a) — no §10.5.4a list addition required.**
The new `O_NOFOLLOW`-protected case_dir open path is a *hardening*
of an existing primitive, not a new shared-infra surface. Existing
§10.5.4a treatment of surfaces #1 and #5 already covers the
authoritative call paths into case_lock; V109's new failure mode
(`failing_check="symlink_escape"` raised on the case_dir open
instead of on the lockfile open) is the same error class downstream
already translates uniformly. No new surface is exposed; an
existing one is hardened in place.

If a future caller starts using `_open_or_create_lock_fd` *without*
also using `case_lock` (i.e., bypassing the lock contract while
still wanting the dir_fd pinning), that would be a new surface and
would warrant a §10.5.4a addition at that time. As of V109, no such
caller exists.

# Codex narrative

R1 returned CHANGES_REQUIRED with one P2 (MED) finding only:
test_case_lock_dir_fd_relative_open_pins_case_dir didn't actually
regress what it claimed because nothing swapped or renamed
case_dir after fd_case was opened in the test. Pre-V109 path-based
open would have passed it too.

R1 closure (commit `85b88e3`): rewrote the test to monkeypatch
`_open_or_create_lock_fd` and perform an attacker-style swap
(rename + symlink_to) BETWEEN fd_case open and lockfile open. The
test now asserts `.case_lock` lands at the pinned inode (`moved/`),
NOT at the swapped malicious symlink target.

R2 APPROVE: zero findings. Codex confirmed the rewritten test
"genuinely distinguishes the two behaviors" and that V109's
implementation itself was clean across both rounds.

# Kogami narrative

Kogami high-risk-PR review (per project CLAUDE.md §"Strategic
package authoring" rule on risk_class=high): APPROVE_WITH_COMMENTS,
recommended_next=merge. Three P2 governance-hygiene findings + one
P3, all closed inline in this DEC body (see kogami_findings_addressed
in frontmatter).

Strategic-fit assessment from Kogami:
> Decision-arc coherence: STRONG. V107 → V107.5 → V108-A → V108-B
> → V109 (closing the documented case_lock residual that V108-A
> could only document) is the correct sequencing. RETRO-V61-V107-V108
> R1 ('read shared primitives before fd-hardening') is being lived
> out in V109's design — V109 reads case_lock's path-based open
> contract first and re-architects rather than layering.

# Verification (closes Kogami P3)

- 7/7 case_lock tests green (3 pre-existing + 4 new V109 regressions)
- 78/78 case_lock-adjacent tests green
- 835/839 full backend pass; the 4 failing tests are the
  pre-existing V108 baseline:
  - `test_case_export.py::test_export_renders_physics_contract_with_three_state_markers`
  - `test_convergence_attestor.py::test_attestor_bfs_real_log_is_hazard_plus_gate_fail`
  - `test_g1_missing_target_quantity.py::test_g1_pass_washing_cases_fail_with_missing_target_quantity[backward_facing_step]`
  - `test_g1_missing_target_quantity.py::test_g1_pass_washing_cases_fail_with_missing_target_quantity[circular_cylinder_wake]`
- Zero new failures introduced by V109
- 1 V108-A test inverted: was pinning the documented residual
  (`.case_lock` leaks to symlink target); now asserts the residual
  is closed
  (`test_patch_classification_store::test_symlink_escape_no_residual_lockfile_leak`)

# Documented residual + future work (closes Kogami P2 #2)

V109 leaves two scope acknowledgments tracked explicitly:

1. **Parent-path symlink residual**: `mkdir(parents=True)` can
   still create intermediate dirs through a symlinked PARENT path.
   Out of scope for V109 — full fd-relative path creation is a
   multi-tenant fix, not the single-tenant local-dev-workbench
   threat model V109 covers. Documented in `locking.py` docstring.

2. **patch_classification_store belt-and-braces cleanup → V61-110
   candidate**: With V109 in place, the
   `patch_classification_store._assert_fd_still_matches_path`
   post-lock inode-drift check becomes belt-and-braces (case_lock
   itself rejects the swap before any work runs). Removing it is a
   small refactor that touches only the patch_classification_store
   module — bounded, low-risk. Tracked as `unblocks_followup:
   V61-110 candidate` in this DEC's frontmatter; no timeline
   committed but trackability is durable per Kogami P2 #2.
