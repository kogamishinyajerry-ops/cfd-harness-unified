# Codex Review Chain · DEC-V61-108 Phase A (R1 → R11)

**DEC**: DEC-V61-108 Phase A — Per-patch BC classification override
**Risk-tier triggers** (per RETRO-V61-001):
  - Multi-file backend logic + new API contract
  - New routes + new sidecar file format
  - Classifier semantics change on the case_solve hot path
**Relay backend**: 86gamestore (`~/.codex-relay`, gpt-5.4, xhigh effort)
**Outcome**: APPROVE on R11 (`dfb13db`) after 11 rounds

## Why this many rounds

R1 surfaced 3 valid concrete defects (concurrency, symlink escape, stale-read race). R2→R10 each found new corner cases in the hardening I built to close R1. The recurring root cause: the `case_lock` module (used project-wide for setup_bc, raw_dict editor, etc.) opens `case_dir` via path resolution without `O_NOFOLLOW`, so it leaks artifacts through any in-flight symlink swap. Every cleanup attempt at the patch_classification layer was racy or unprovably-ours. R9 → architectural close: skip cleanup on the symlink_escape branch, document the residual `.case_lock` leak as upstream `case_lock` work.

## Round-by-round

### R1 — CHANGES_REQUIRED · 3 findings
- **P1-A** (HIGH): concurrent PUT/DELETE lose updates (read-modify-write race).
- **P1-B** (HIGH): sidecar write follows symlinks → write outside case root.
- **P2** (MED): setup_bc reads overrides BEFORE acquiring `case_lock` — stale-read race vs in-flight PUT.

### R1 closure (`343a145`)
- New `services/case_solve/patch_classification_store.py` owns all I/O.
- `upsert_override` / `delete_override` wrap read-modify-write in `case_lock`.
- Atomic write via `tempfile.mkstemp` + `os.replace`; symlink containment check on the resolved path.
- Override load + classify + dict author moved INSIDE `case_lock` in `setup_bc_from_stl_patches`.
- 8 new hardening tests.

### R2 — CHANGES_REQUIRED · 1 finding
- **P1** (HIGH): containment check accepts in-tree symlinks. `patch_classification.yaml -> system/controlDict` would let PUT overwrite controlDict.

### R2 closure (`34e8a92`)
- Walk every path component; reject if any is a symlink (regardless of where it points).

### R3 — CHANGES_REQUIRED · 1 finding
- **P2** (HIGH): TOCTOU between R2 preflight walk and pathname-based `mkstemp`/`os.replace`. Attacker can swap `system/` to a symlink between validation and write.

### R3 closure (`2d85e4f`)
- Fully fd-based I/O via openat-style ops: `O_NOFOLLOW | O_DIRECTORY` on all dir opens; `os.replace` with `src/dst_dir_fd`. Replaced `_atomic_write_under_case` + helpers.

### R4 — CHANGES_REQUIRED · 2 findings
- **P1** (HIGH): the READ half (`load_patch_classification_overrides`) still uses pathname resolution → same TOCTOU on the read path.
- **P2** (MED): `case_lock`'s auto-mkdir silently re-creates a deleted case before our existence check fires.

### R4 closure (`23090d1`)
- `_apply_under_case(case_dir, *, mutate)` — single fd_case+fd_system pair shared by load and write halves. `_open_case_no_follow` BEFORE `case_lock` so missing case is rejected without auto-mkdir running.

### R5 — CHANGES_REQUIRED · 1 finding
- **P1** (HIGH): if case_dir is delete-recreated between `_open_case_no_follow` and `case_lock`, fd_case references the OLD inode while case_lock locks the NEW one. Writes go to orphaned inode; serialization broken.

### R5 closure (`683578b`)
- `_assert_fd_still_matches_path(fd_case, case_dir)` runs immediately after `case_lock`. Compares `fstat(fd_case)` vs `lstat(case_dir)`; mismatch on `(st_ino, st_dev)` raises.

### R6 — CHANGES_REQUIRED · 2 findings
- **P2** (MED): R5's check correctly aborts but `case_lock` already created the orphan stub at the case_dir path, leaving a "live empty case" for subsequent requests.
- **P3** (LOW): symlink-replacement misclassified as `case_dir_missing` (404) instead of `symlink_escape` (422).

### R6 closure (`b29e860`)
- `_cleanup_case_lock_orphan_stub(case_dir)` — best-effort tear-down of the orphan stub after drift detection.
- `_assert_fd_still_matches_path` distinguishes symlink-replacement (raises `symlink_escape`) from delete-recreate (raises `case_dir_missing`).

### R7 — CHANGES_REQUIRED · 2 findings
- **P1** (HIGH): cleanup ran on EVERY drift class including `symlink_escape`. Path-based ops then followed the symlink and could mutate external content.
- **P2** (MED): cleanup `rmdir`'d empty dirs without checking `.case_lock` was present (could remove unrelated empty dirs).

### R7 closure (`ca75d68`)
- Cleanup gated on `failing_check == "case_dir_missing"`. Cleanup helper rewritten with fd-based listing + `.case_lock` authority gate.

### R8 — CHANGES_REQUIRED · 1 finding
- **P1** (HIGH): R7's "skip cleanup on symlink_escape" left case_lock's `.case_lock` artifact behind in the symlink target. Codex argued the prior code "at least removed the stray file for empty targets".

### R8 closure (`a47b878`)
- `_cleanup_case_lock_orphan_stub` gained `allow_symlink_target` parameter. On symlink_escape branch, path-based unlink of `.case_lock` IF target contains exactly that file.

### R9 — CHANGES_REQUIRED · 2 findings
- **P1** (HIGH): R8's "remove .case_lock if it's the only file" can't prove ownership — POSIX `O_CREAT` doesn't report whether the file was just created.
- **P2** (HIGH): check + unlink sequence is racy on a mutable symlink; attacker can repoint between operations.

### R9 architectural close (`f28e70d`)
- REVERT the symlink_escape cleanup branch entirely (back to R7 P1's behavior).
- DOCUMENT the residual `.case_lock` leak as an upstream `case_lock` bug whose proper fix (open case_dir with `O_NOFOLLOW` before opening lockfile) is out of scope for this DEC.
- New test `test_symlink_escape_documented_residual_lockfile_leak` pins the documented behavior.
- Threat model justification: requires active local attacker swapping case_dir at the right moment in a single-tenant dev workbench — outside realistic threat model.

### R10 — CHANGES_REQUIRED · 1 finding
- **P2** (MED): R9's regression test asserted on `<target>/patch_classification.yaml` (root) but the store writes to `<target>/system/patch_classification.yaml`. Trivially-passing assertion.

### R10 closure (`dfb13db`)
- Verbatim test fix: assertion now checks the actual write target, plus belt-and-braces check that `<target>/system/` was never created.

### R11 — APPROVE · 0 findings
> "The change only strengthens a regression test by asserting against the real sidecar location and by checking that the external `system/` directory is never created. I did not find any incorrect assumptions or regressions introduced by the updated assertions."

## Verification preserved across the chain
- 19 store + 10 route + 11 override + 27 regression = **67 patch_classification tests, all green**
- **844 broader backend tests passing** (4 pre-existing failures unrelated to V108)
- **Smoke baseline: 4 PASS · 0 EF · 2 SKIP · 0 FAIL preserved on every closure**

## Counter

Per RETRO-V61-001 telemetry: each Codex round increments `autonomous_governance_counter_v61` by 1. R1–R11 = 11 increments on DEC-V61-108 Phase A. Combined with DEC-V61-107.5's 9 (R12–R20) = 20 ticks across the two arcs. Eligible for arc-size retro at next ≥ 20 boundary check.

## Honest scope

R1 surfaced 3 real defects in legitimate hardening territory (concurrency, symlink, race). R2–R10 explored the corner-case space exhaustively; the recurring root cause was upstream `case_lock`'s pathname-based open. The architectural close in R9 made this explicit: clean up where we can (case_dir_missing branch), document what we can't (symlink_escape branch), point to the upstream fix that would close the residual.

## Future work

Track in a separate DEC: make `services/case_manifest/locking.py:case_lock` symlink-safe at the case_dir level (open case_dir with `O_NOFOLLOW | O_DIRECTORY` before opening the lockfile). That fix would:
- Eliminate the `.case_lock` leak to symlink targets that this DEC documents as residual
- Let `patch_classification_store._apply_under_case` drop the post-lock `_assert_fd_still_matches_path` check
- Benefit every other code path that calls `case_lock(case_dir)` (setup_bc, raw_dict editor, etc.)

Blast radius is wider than DEC-V61-108 Phase A (case_lock is shared), so the change deserves its own scope + Codex pass.
