# Codex pre-merge review · DEC-V61-098 Steps 2+3 · Round 2

**Date**: 2026-04-29
**Verdict**: `Codex-verified: CHANGES_REQUIRED residual lock-file symlink escape still lets save_annotations() write outside the case root, so the round-1 containment issue is not fully closed`
**Severity**: `HIGH`
**Commit reviewed**: `bc70730` (round-1 closure commit)

---

## Findings

### 1. HIGH — `_exclusive_case_lock()` reintroduces an external write path through `.face_annotations.lock`, and lock-path failures now bypass the `AnnotationsIOError` contract
**File**: `ui/backend/services/case_annotations/_yaml_io.py:224-234` and `ui/backend/routes/case_annotations.py:192-205`

The fixed-name `.tmp` issue is closed: `tempfile.mkstemp(dir=case_root)` removes the predictable staging path, and I did not find a residual escape through the new temp-file path itself. The new lock sentinel is the remaining problem.

`_exclusive_case_lock()` opens `case_root / ".face_annotations.lock"` with:

```python
os.open(str(lock_path), os.O_RDWR | os.O_CREAT, 0o600)
```

That call has no `O_NOFOLLOW` and no containment validation for the lock path. If an attacker plants `case_dir/.face_annotations.lock -> /outside/path`, `os.open()` follows the symlink and, because `O_CREAT` is present, creates the target outside the case root when it does not already exist.

I reproduced this locally by creating `.face_annotations.lock` as a symlink to a nonexistent sibling path outside the case dir and then calling `save_annotations(...)`: the save returned successfully, and a zero-byte file was created at the external target. That is still a filesystem escape from the case root, even though it no longer overwrites YAML content.

The same path also introduces a new exception-contract hole. If `.face_annotations.lock` points to a directory, `_exclusive_case_lock()` raises raw `IsADirectoryError`; `save_annotations()` does not wrap it, and the route only catches `AnnotationsRevisionConflict` and `AnnotationsIOError`, so the request falls through as an uncategorized 500 instead of the intended structured 422 error shape.

**Verbatim fix**: harden the lock path exactly like the temp path: open the sentinel with no-follow semantics (`O_NOFOLLOW` where available), reject any symlink leaf as `AnnotationsIOError(failing_check="symlink_escape")`, and wrap `os.open` / `flock` / `close` failures into `AnnotationsIOError` so callers never see raw `OSError`.

## Non-blocking observations

- The round-1 signed-zero MED is closed. `_normalize_coord()` in [ui/backend/services/case_annotations/__init__.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/case_annotations/__init__.py:66) correctly collapses `-0.0` to `0.0`, and the new regression test covers mixed-sign-zero inputs.
- The round-1 LOW on `error_detail` is closed. `AIActionEnvelope.model_post_init()` now rejects `error_detail` unless `confidence == "blocked"`, and the schema regression test matches that contract.
- The `LOCK_UN` + `os.close` release path is structurally correct for exceptions inside the critical section. If `_save_annotations_locked()` raises, the inner `finally` attempts `LOCK_UN`, and the outer `finally` still closes the fd. Even if `LOCK_UN` itself raises, `os.close(fd)` still runs and releases the advisory lock.
- The new thread-based concurrency test is useful for the original shared-`.tmp` collision and for the revision-conflict path, but it is not strong proof of cross-process behavior. `fcntl.flock` is the correct primitive for same-host cross-process serialization; a subprocess-based regression test would improve confidence, but the absence of that test is not the blocking issue here.
- The deferred non-blockers from round 1 are acceptable to leave for round 3. I would not block this round on the OpenAPI `response_model` drift or the debatable `confidence="uncertain"`/no-questions schema strictness while the lock-file containment bug remains open.

## Review focus answers

1. The round-1 MED signed-zero finding is fully closed. The round-1 HIGH temp-path finding is only partially closed: the `mkstemp()` path looks good, but `.face_annotations.lock` reopens a containment escape.
2. Yes, the `LOCK_UN` / `os.close` `finally` structure handles exceptions in the critical section correctly. The problem is not lock release; it is unsafe lock-path opening and unwrapped lock-path exceptions.
3. The Barrier test gives meaningful same-process contention coverage, especially for the old shared-temp collision. It does not prove cross-process behavior by itself; `flock` is the cross-process mechanism, and a subprocess test would be the stronger proof.
4. Yes. The new HIGH is the lock-file symlink escape plus the raw-`OSError` contract break on lock acquisition failures.
5. Yes, the deferred LOW items can wait for round 3.

## Verification

- Targeted regression suites passed in the repo venv:
  - `PYTHONPATH=. ./.venv/bin/pytest -q ui/backend/tests/test_case_annotations.py ui/backend/tests/test_ai_action_schema.py`
  - Result: `43 passed`
- Wider reviewed slice passed in the repo venv:
  - `PYTHONPATH=. ./.venv/bin/pytest -q ui/backend/tests/test_case_annotations.py ui/backend/tests/test_ai_action_schema.py ui/backend/tests/test_setup_bc_envelope_route.py ui/backend/tests/test_solver_streamer.py`
  - Result in this checkout on 2026-04-29: `61 passed`
- Additional local repros run during review:
  - planted `.face_annotations.lock -> outside_created_by_lock` and confirmed `save_annotations()` succeeded while creating the external zero-byte file
  - planted `.face_annotations.lock -> outside_dir` and confirmed `save_annotations()` raised raw `IsADirectoryError`
