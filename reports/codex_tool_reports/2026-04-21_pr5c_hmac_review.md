# Codex GPT-5.4 Review · PR #14 HMAC Sign/Verify (DEC-V61-014)

Date: 2026-04-21
Reviewer: GPT-5.4 via /codex-gpt54 (invoked by claude-opus47-app post-merge per DEC-V61-013 counter discipline)
Subject files: src/audit_package/sign.py, tests/test_audit_package/test_sign.py
Merge SHA: 8d397d3d118996a83bdd58cb5eb8352cf8dbfce1

## Verdict
APPROVED_WITH_NOTES

## Findings by severity
### Critical (must fix immediately)
None.

### High (fix before next related PR)
None.

### Medium (queue for follow-up)
1. Ambiguous env-var decoding can silently change key bytes across tooling or future manual verifiers.
   Evidence: `src/audit_package/sign.py:102-122`, `tests/test_audit_package/test_sign.py:242-247`
   Why it matters: any padded/base64-alphabet value is decoded as base64 first. That keeps signer and verifier consistent inside this repo because they share the same helper, but it is brittle for the documented bash/manual verification flow and for any future non-Python verifier. The same visible env-var value can map to different byte keys depending on whether another implementation treats it as literal text or base64.
   Suggested fix: make the encoding explicit. Best option: accept only padded standard base64 and fail closed otherwise. If plain-text keys must remain supported, require an explicit prefix such as `base64:` / `text:` and add tests for ambiguous, URL-safe, and unpadded inputs.

2. The v1 sidecar + rotation story is not self-describing enough for post-rotation verification or multi-signer audit trails.
   Evidence: `src/audit_package/sign.py:46-53`, `src/audit_package/sign.py:221-245`, `docs/ui_roadmap.md:213-225`
   Why it matters: `.sig` stores only the MAC hex. There is no in-band `kid`, algorithm/version, or domain identifier, so after rotation the verifier must guess which retained key to try. That does not weaken HMAC tamper detection directly, but it weakens archival verifiability and signer attribution in a regulated setting.
   Suggested fix: document an explicit verifier keyring procedure now (retention window, rotation ledger, which key verified which bundle). For the next format revision, add at least `kid`, `alg`, and `domain` metadata; if digest fields are added for audit convenience, recompute them from the bundle rather than trusting sidecar copies.

### Low / Informational
1. Sidecar I/O does not validate exact signature shape.
   Evidence: `src/audit_package/sign.py:221-245`, `tests/test_audit_package/test_sign.py:293-304`
   Why it matters: `write_sidecar()` will persist any stripped text and `read_sidecar()` returns any non-empty string. `verify()` rejects malformed values later, so this is not a forgery bug, but strict validation would fail faster and keep audit artifacts cleaner.
   Suggested fix: enforce `^[0-9a-fA-F]{64}$` on write and read, with tests for non-hex, multi-line, and wrong-length sidecars.

2. Exact manifest canonicalization needs to be pinned in any external verification doc/script.
   Evidence: `src/audit_package/serialize.py:68-76`, `src/audit_package/sign.py:136-139`
   Why it matters: the implementation uses `json.dumps(..., sort_keys=True, ensure_ascii=False, indent=2)` plus a trailing newline. That is consistent and safe inside Python, but a generic “canonical JSON” description is too vague for a bash or other-language verifier.
   Suggested fix: publish the exact canonicalization contract alongside the future verification procedure, or expose a first-party verification CLI that calls the same code.

## Per-area analysis
### 1. HMAC input framing
Implemented as `DOMAIN_TAG || sha256(canonical_manifest) || sha256(zip_bytes)` at `src/audit_package/sign.py:129-139`. This is cryptographically sound for the stated threat model. The domain tag gives domain separation, the two inner digests are fixed-width so there is no framing ambiguity, and the outer primitive is HMAC so classic SHA-256 length-extension attacks do not apply. Security does rely on the normal preimage/second-preimage strength of SHA-256 for the inner digests, which is acceptable here. No blocking issue found.

### 2. Constant-time compare
Routing is correct. `verify()` recomputes the expected digest and uses `hmac.compare_digest` at `src/audit_package/sign.py:211-213`; `tests/test_audit_package/test_sign.py:188-200` confirms that path is exercised. I did not find a fallback path to `==`. The `.lower()` normalization is safe for the intended ASCII-hex input and does not expose the secret, though fixed-shape hex validation before comparison would still be cleaner.

### 3. Env var key loader
No secret leakage found. The raised `HmacSecretMissing` message at `src/audit_package/sign.py:104-109` includes only the env-var name and operator instructions, not the secret value. The issue is ambiguity, not disclosure: the base64-first heuristic at `src/audit_package/sign.py:113-122` can silently reinterpret some literal strings as binary keys. That is deterministic inside this codebase but brittle for external/manual verification and future multi-implementation use.

### 4. Sidecar format
The current v1 format is cryptographically sufficient for tamper detection if the verifier already knows the correct key, algorithm, and domain tag. It is not self-describing. Missing `kid`/algorithm/version/domain metadata does not let an attacker forge a bundle, but it does make audit operations and post-rotation verification harder. A manifest hash in the sidecar would be useful for audit/debugging, not for core authenticity; if added, the verifier should recompute it from the manifest/zip rather than trust the sidecar copy.

### 5. Key rotation
The documented procedure in `src/audit_package/sign.py:46-53` is incomplete for regulated retention. It covers “generate new key” and “new bundles use it,” but it does not define how verifiers retain old keys, how they decide which old key to try, how successful verification is attributed/logged, what happens for multi-signer or per-project parallel keys, or what the compromise/revocation story is. Without that process, old bundles remain verifiable only by operator convention, not by a documented control.

## Recommendations
1. Tighten `CFD_HARNESS_HMAC_SECRET` parsing to a single explicit encoding contract and add tests for ambiguous / URL-safe / unpadded inputs.
2. Keep `compare_digest` as the final equality primitive, but add fixed-shape hex validation before comparison.
3. Treat the current `.sig` format as v1-minimal only; document verifier keyring/rotation procedure immediately, and add `kid`/`alg`/`domain` metadata in the next format revision.
4. Publish the exact manifest canonicalization algorithm in the future verification doc/CLI so external auditors can reproduce the same MAC input byte-for-byte.
