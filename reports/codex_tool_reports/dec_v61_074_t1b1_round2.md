# DEC-V61-074 P2-T1.b.1 · Codex pre-merge review · Round 2

- **Verdict**: APPROVE_WITH_COMMENTS (R1 HIGH closed)
- **Diff target**: T1.b.1 R2 patch on `src/executor/base.py` + 3 pinning tests
- **Date**: 2026-04-26
- **Tokens used**: 119,076
- **Codex CLI run id**: b0yc7133k (transcript: `dec_v61_074_t1b1_round2.log`, gitignored)

## R1 HIGH finding · CLOSED

`ExecutorAbc.contract_hash` now derives from the spec source via `_executor_spec_sha256()` plus `MODE` and `VERSION`, with class identity removed from the tuple (`base.py:79`, `base.py:247`).

The new pinning tests would catch a regression back to class-identity hashing — rename invariance, spec-digest sensitivity, and exact tuple pinning are all covered in `tests/test_executor_modes/test_executor_abc.py:175`. The manifest path still round-trips that value unchanged (`manifest.py:477`, `manifest.py:609`).

## R2 findings

### 1. LOW — Stale inline comment at manifest.py:467

`src/audit_package/manifest.py:467` still says the default executor hash is based on `class qualname + MODE.value + VERSION`, which became false after the R2 change in `src/executor/base.py:247`. Runtime behavior is correct because the manifest still copies `executor.contract_hash` verbatim, but the inline guidance at the manifest write site is now misleading.

**Suggested fix**: Update that inline comment to describe the current identity source — e.g. `sha256(spec_file_sha256|MODE|VERSION)` or equivalent wording that makes clear the hash is spec-derived, not class-derived.

## Verification

Targeted test modules in repo `.venv`:
- `.venv/bin/pytest -q tests/test_executor_modes/test_executor_abc.py -q` → **26 passed**
- `.venv/bin/pytest -q tests/test_audit_package/test_manifest.py -q` → **31 passed**

Confirms older T1.a hash tests still pass under the new derivation.

## LOW closure

LOW finding closed verbatim within RETRO-V61-001 5-condition exception (≤20 LOC, 1 file, no API surface change, diff-level Codex match) — inline comment swap landed in the same commit `f599129` (attribution-misaligned per DEC addendum).
