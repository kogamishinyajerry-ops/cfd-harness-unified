# Codex GPT-5.4 Follow-up Review · PR #15 HMAC Sign/Verify Fixes (PR-5c.1)

Date: 2026-04-21
Reviewer: GPT-5.4 via Codex post-merge follow-up
Subject files: src/audit_package/sign.py, tests/test_audit_package/test_sign.py
Merge SHA: db83764b55fe78048aaaeed3c325552f7b5bfb54
Baseline SHA: 8d397d3d118996a83bdd58cb5eb8352cf8dbfce1

## Verdict
APPROVED_WITH_NOTES

M1 and L1 are closed in the code paths I reviewed: env-var decoding is now deterministic and sidecar I/O now enforces the intended 64-hex shape. The remaining issue is upgrade communication: an operator who was already using an un-prefixed base64 secret under PR-5c will not get an error after upgrading, but the key bytes silently change unless they add the new `base64:` prefix.

## Findings by severity
### Critical (must fix immediately)
None.

### High (fix before next related PR)
None.

### Medium (queue for follow-up)
1. PR-5c.1 silently reinterprets legacy un-prefixed base64 secrets as literal UTF-8 text, but the new operator guidance only appears on error paths those deployments never hit.
   Evidence: `src/audit_package/sign.py:128-163`, `tests/test_audit_package/test_sign.py:249-254`, `tests/test_audit_package/test_sign.py:284-290`
   Why it matters: under PR-5c, a value like `aGVsbG8=` decoded to `b"hello"`; under PR-5c.1 the same visible env-var value becomes `b"aGVsbG8="`. That closes the ambiguity finding, but it also breaks mixed-version sign/verify and historical-bundle verification for any deployment that previously stored raw `openssl rand -base64 32` output without the new prefix. Because the env var is still non-empty and non-malformed, `HmacSecretMissing` is never raised, so the operator gets no runtime migration hint.
   Suggested fix: publish an explicit upgrade note for PR-5c.1 and preferably add a migration guard on startup: if an un-prefixed value matches the old heuristic for padded standard base64, raise or log a dedicated message telling the operator to choose `base64:<...>` or `text:<...>` explicitly.

### Low / Informational
None.

## Per-area analysis
### 1. Explicit-prefix env-var parser / M1 ambiguity
The new parser does close the original ambiguity. `base64:` is decoded via `base64.b64decode(..., validate=True)`; `text:` is UTF-8 text; and un-prefixed values are now always literal UTF-8 bytes (`src/audit_package/sign.py:138-163`). That means a visible env-var string maps to exactly one byte sequence, and the old base64-first heuristic is gone.

`test_un_prefixed_base64_looking_string_is_literal` is asserting the correct post-PR-5c.1 invariant (`tests/test_audit_package/test_sign.py:249-254`). It is the key regression test for the M1 fix because it proves that an ambiguous-looking value no longer silently decodes.

Edge cases:
- Whitespace: outer whitespace is still normalized by `strip()` before prefix dispatch (`src/audit_package/sign.py:128`), so exact leading/trailing whitespace bytes cannot be represented. That is deterministic, but it is worth treating as part of the contract.
- BOM / prefix-like plain text: a UTF-8 BOM or an upper-case prefix such as `BASE64:` will not be recognized as a prefix and will instead be treated as literal text. That is deterministic rather than ambiguous, but it is untested and not called out in docs.
- Reserved prefixes are otherwise fine: if a caller wants literal bytes beginning with `base64:` or `text:`, `text:base64:...` is unambiguous.

The real residual issue is migration, not parser correctness: existing un-prefixed base64 deployments change behavior silently.

### 2. Sidecar regex `^[0-9a-fA-F]{64}$`
The regex is correct for the intended sidecar contract. Combined with the surrounding `strip()` calls, it blocks wrong-length, non-hex, and multi-line content on both write and read (`src/audit_package/sign.py:280-287`, `src/audit_package/sign.py:305-313`; `tests/test_audit_package/test_sign.py:338-381`).

Edge-case behavior is sensible:
- Windows CRLF is accepted after normalization because `read_sidecar()` strips line endings before matching.
- BOM does not bypass the check; it remains a non-hex character and causes `read_sidecar()` to return `None`.
- Trailing whitespace does not bypass either; it is normalized away before validation.

This is slightly lenient rather than byte-for-byte strict, but it does not permit malformed signatures through to `verify()`, which was the actual L1 concern.

### 3. Behavior-change tests vs old behavior
The changed tests mostly capture the new contract correctly:
- `test_base64_prefix_decoded` pins the new explicit binary-key path.
- `test_text_prefix_utf8_encoded` pins the explicit text path.
- `test_un_prefixed_base64_looking_string_is_literal` pins the most important changed behavior.
- `TestSidecarIO` and `TestEndToEnd` cover both stricter sidecar validation and the fact that malformed sidecars now short-circuit to `None`.

I did not find a test that is asserting the old heuristic by accident. The specific invariant in `test_un_prefixed_base64_looking_string_is_literal` is the right one.

What is still missing is contract pinning for a few edge inputs the previous review called out: URL-safe/unpadded base64, BOM-prefixed env values, and prefix case-sensitivity. Those are not correctness bugs in the current implementation, but they remain untested semantics.

### 4. Breaking-change communication / `HmacSecretMissing`
The `HmacSecretMissing` text is actionable when it is actually raised (`src/audit_package/sign.py:130-150`). It tells the operator the new forms to use and gives a concrete `openssl rand -base64 32` command.

The problem is that the most important upgrade hazard does not raise `HmacSecretMissing`. A legacy PR-5c deployment using an un-prefixed base64 secret is accepted as a valid un-prefixed text secret in PR-5c.1, so the error message never appears. For that reason, the message itself is not enough as the primary migration mechanism.

### 5. Anything else
I did not find a new bug in the sidecar validation change itself. The prior M2 concern remains deferred: sidecars are still v1-minimal and not self-describing for post-rotation archival verification.

I also did not find a direct code/test mismatch in the changed files, beyond the upgrade-communication gap above.

Verification note: `pytest -q tests/test_audit_package/test_sign.py` could not run to completion in this workspace because package import currently fails on missing `yaml` (`ModuleNotFoundError: No module named 'yaml'`). Review conclusions above are therefore based on static analysis plus direct focused probes of the changed helpers.

## Recommendations
1. Add an explicit PR-5c.1 upgrade note: if `CFD_HARNESS_HMAC_SECRET` previously contained raw base64 output without a prefix, rewrite it as `base64:<same-value>` before deploying PR-5c.1.
2. Prefer a runtime migration guard for legacy-looking un-prefixed values so mixed-version or historical verification failures are caught immediately instead of after signatures diverge.
3. Add a few narrow tests to pin the remaining edge semantics: URL-safe/unpadded base64 rejection, BOM/case-sensitive env prefixes, and CRLF/BOM sidecar reads.
