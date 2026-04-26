# DEC-V61-074 P2-T1.b.1 · Codex pre-merge review · Round 1

- **Verdict**: CHANGES_REQUIRED
- **Diff target**: T1.b.1 unstaged (`src/audit_package/manifest.py` + `tests/test_audit_package/test_manifest.py`)
- **Date**: 2026-04-26
- **Tokens used**: 207,221
- **Codex CLI run id**: bepszkw7l (transcript: `dec_v61_074_t1b1_round1.log`, gitignored)

## Findings

### 1. HIGH — `executor.contract_hash` is class-identity, not spec-derived

The new `executor.contract_hash` that T1.b.1 writes into the signed manifest is still the executor class-identity hash, not the frozen contract-spec hash that §3/F-3 requires.

**Evidence**:
- `src/audit_package/manifest.py:467` copies `default_executor.contract_hash` / `executor.contract_hash` directly
- `src/executor/base.py:172` still defines that property as `sha256(class qualname|MODE|VERSION)`
- Contradicts normative contract in `docs/specs/EXECUTOR_ABSTRACTION.md:65` and spike at `.planning/specs/EXECUTOR_ABSTRACTION_compatibility_spike.md:60`
- New tests in `tests/test_audit_package/test_manifest.py:404` lock the drift in by asserting against `DockerOpenFOAMExecutor().contract_hash` / `mock_exec.contract_hash`

**Impact**: A class rename or module move will churn signed manifest bytes and break the downstream reference identity that §6.3 keys off `executor.contract_hash` for (`EXECUTOR_ABSTRACTION.md:248`), even when the contract did not change.

**Suggested fix**: Change `ExecutorAbc.contract_hash` to derive from the frozen executor-contract spec source required by §3/F-3. Update the new manifest assertions to compare against that canonical hash. Add the missing `executor_contract_hash_pinning` test so refactors cannot silently change audit manifests.

## No additional findings

`SCHEMA_VERSION` un-bumped, CONTROL→EXECUTION import legality under `.importlinter`, canonical JSON byte ordering, and legacy HMAC scope all OK. Targeted verification passed locally with `tests/test_audit_package/test_manifest.py` at 31/31 — but the passing tests currently encode the spec drift above.

## R2 closure

R2 fix landed at commit `f599129` (attribution-misaligned per DEC addendum). See `dec_v61_074_t1b1_round2.md` for R2 verdict.
