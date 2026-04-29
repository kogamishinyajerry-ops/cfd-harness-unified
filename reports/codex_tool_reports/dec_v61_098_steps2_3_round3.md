# Codex verification · DEC-V61-098 Steps 2+3 · Round 3

**Date**: 2026-04-29
**Verdict**: `APPROVE`
**Commit reviewed**: `8ae2749`

## Verdict basis

Round-2 HIGH is closed in [_yaml_io.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/case_annotations/_yaml_io.py:204).

- `_exclusive_case_lock()` now opens `.face_annotations.lock` with `os.O_NOFOLLOW` in the flag set (`os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW`), which blocks final-component symlink traversal at lock creation/open time. See [_yaml_io.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/case_annotations/_yaml_io.py:238).
- `os.open(...)` failures are now wrapped to `AnnotationsIOError(..., failing_check="symlink_escape")`, which closes the prior raw-`IsADirectoryError` / raw-`OSError` leak and preserves the structured containment contract. See [_yaml_io.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/case_annotations/_yaml_io.py:239) and [_yaml_io.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/case_annotations/_yaml_io.py:246).
- `fcntl.flock(...)` acquisition failures are wrapped to `AnnotationsIOError`, so lock acquisition no longer exposes uncategorized syscall exceptions. See [_yaml_io.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/case_annotations/_yaml_io.py:252) and [_yaml_io.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/case_annotations/_yaml_io.py:255).
- Swallowing failures from `LOCK_UN` and `os.close` is acceptable here: both are cleanup-only paths inside `finally`, and the implementation correctly avoids masking an in-flight exception from the critical section. See [_yaml_io.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/case_annotations/_yaml_io.py:259) and [_yaml_io.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/services/case_annotations/_yaml_io.py:270).

The new regression coverage also matches the round-2 attack surface:

- nonexistent external target via lock symlink: [test_case_annotations.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/tests/test_case_annotations.py:376)
- lock symlink to directory: [test_case_annotations.py](/Users/Zhuanz/Desktop/cfd-harness-unified/ui/backend/tests/test_case_annotations.py:407)

## Local verification

I reproduced both prior attacks locally against commit `8ae2749`:

1. `.face_annotations.lock -> nonexistent outside path`
   Result: `save_annotations(...)` raised `AnnotationsIOError` with `failing_check="symlink_escape"`; the outside target was **not created**.
2. `.face_annotations.lock -> outside directory`
   Result: `save_annotations(...)` raised `AnnotationsIOError` with `failing_check="symlink_escape"`; the target directory remained **untouched**.

Targeted test run:

```bash
PYTHONPATH=. ./.venv/bin/pytest -q ui/backend/tests/test_case_annotations.py
```

Result: `28 passed`
