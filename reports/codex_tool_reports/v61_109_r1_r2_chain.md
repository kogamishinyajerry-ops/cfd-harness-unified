# Codex Review Chain · DEC-V61-109 (R1 → R2)

**DEC**: DEC-V61-109 — case_lock O_NOFOLLOW upstream fix
**Risk-tier triggers** (per RETRO-V61-001):
  - Shared-infra primitive change (case_lock used by setup_bc, raw_dict editor, patch_classification_store)
  - New failure surface (case_dir-level symlink_escape detection)
  - Concurrency-sensitive code on the hot path
**Relay backend**: 86gamestore (`~/.codex-relay`, gpt-5.4, xhigh effort)
**Outcome**: APPROVE on R2 (`85b88e3`) after 2 rounds

## Why this many rounds

R1 found one P2 (MED) test-quality finding: my "dir_fd-pinning" regression test passed under both pre-V109 and post-V109 implementations because it didn't actually exercise a swap mid-flight. R2 verified the rewritten test (monkeypatched helper performs an attacker-style rename + symlink_to between fd_case open and lockfile open) genuinely distinguishes the two behaviors.

Importantly: **Codex found zero implementation defects in V109 itself across both rounds**. The single round of CHANGES_REQUIRED was on test quality, not code quality. This is a positive calibration signal: V109 was scoped to a clean architectural fix with a concrete predecessor (V108-A R9 documented residual) and Codex confirmed the scope was right.

## Round-by-round

### R1 — CHANGES_REQUIRED · 1 finding (initial commit `4a0fcd6`)
- **P2 (MED)**: `test_case_lock_dir_fd_relative_open_pins_case_dir` doesn't actually regress what it claims. Pre-V109 path-based implementation would also pass this test because nothing swaps or renames `case_dir` after `fd_case` is opened.

### R1 closure (`85b88e3`)
- Renamed test → `test_case_lock_dir_fd_pinning_survives_swap_after_fd_open`
- Monkeypatches `_open_or_create_lock_fd` to perform attacker-style swap BETWEEN `fd_case` open and lockfile open: `rename` real `case_dir` → "moved" sibling path; plant symlink at original `case_dir` path → "malicious" target dir
- With V109's dir_fd-relative open, `.case_lock` lands at `moved/.case_lock` (the pinned inode), NOT at `malicious/.case_lock` (the swapped path)
- Pre-V109 path-based open WOULD have landed it at `malicious/.case_lock` — confirmed by Codex R2 mental simulation

### R2 — APPROVE · 0 findings
> "The rewritten regression in `test_case_lock_race.py:220` now genuinely distinguishes the two behaviors: with the pre-V109 path-based open, the post-`fd_case` rename+symlink swap would redirect `.case_lock` into `malicious/.case_lock`, so this test would fail; with V109's dir-fd-relative helper... the pinned directory fd survives the rename and `openat` still creates `moved/.case_lock` as asserted... `locking.py` is unchanged in `85b88e3`, with no new implementation issues surfaced by this review."

### Implementation quality assessment from Codex R1
> "Static review did not find an implementation defect in the V109 lock fix itself: the `O_NOFOLLOW|O_DIRECTORY` open closes the V108-A residual, the `dir_fd` open is correctly anchored to `fd_case`, the Darwin retry helper preserves `O_NOFOLLOW` in both branches without a symlink-redirection window, the `FileExistsError` catch is narrowly scoped, fd cleanup is correct, and the docstring is honest about the still-out-of-scope parent-path symlink residual."

## Verification preserved across the chain

- **7/7 case_lock tests green** (3 pre-existing + 4 new V109 regressions)
- **78/78 case_lock-adjacent tests green**
- **835/839 full backend pass**; the 4 failing tests are the pre-existing V108 baseline (test_case_export, test_convergence_attestor, test_g1_missing_target_quantity × 2)
- **0 new failures introduced** by V109
- **1 V108-A test inverted**: was pinning the documented residual (`.case_lock` leaks to symlink target); now asserts the residual is closed

## Counter

Per RETRO-V61-001 telemetry: V109 contributes **+1** to `autonomous_governance_counter_v61`. Counter advances 57 → 58. Per DEC-V61-087 §5 truth table, the Kogami high-risk-PR review contributes +0 (advisory-chain Kogami artifacts are not counted).

## Honest scope

V109 is the canonical "small, surgical fix that closes a documented residual" arc:
- Surface: 1 file (`locking.py`) + 2 test files
- Codex rounds: 2 (1 on test quality only)
- Implementation findings: 0 across both rounds
- Surprising discovery: Darwin's `openat(O_CREAT|O_NOFOLLOW)` race under contention. Caught manually during pytest suite run (the concurrent-upserts test flaked); reproduced cleanly in 8-thread bursts; closed with the standard portable atomic open-or-create pattern. Folded into V109 scope per Kogami P2 #1 disposition (option a — same-blast-radius portability fix, NOT a "pragmatic scope reduction" of the V107.5 R16 type).

## Calibration update

V109 actual_pass_rate = ~50% (1 round of CHANGES_REQUIRED on test quality). Estimated 60% — within the new RETRO-V61-V107-V108 R1 baseline range (0.30 for "shared-infra primitive fd-hardening" with adjustment to 0.60 because V109's surface was small + bounded + had a clear predecessor). Calibration debt: minimal (Codex R2 explicitly noted no implementation defects).

## Future work

- **DEC-V61-110 candidate**: drop `patch_classification_store._assert_fd_still_matches_path` post-lock inode-drift check. With V109 in place this becomes belt-and-braces (case_lock itself rejects the swap before any work runs). Bounded refactor; one module touched. Tracked as `unblocks_followup` in V109 frontmatter per Kogami P2 #2 closure requirement.
- **Parent-path symlink residual**: `mkdir(parents=True)` can still create intermediate dirs through a symlinked PARENT. Out of scope for V109 — multi-tenant fix, not single-tenant threat model. Documented in `locking.py` docstring.
