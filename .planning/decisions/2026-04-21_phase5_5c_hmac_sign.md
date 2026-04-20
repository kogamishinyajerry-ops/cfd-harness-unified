---
decision_id: DEC-V61-014
timestamp: 2026-04-21T01:25 local
scope: Path B · Phase 5 · PR-5c · HMAC-SHA256 sign/verify. Adds src/audit_package/sign.py with sign/verify over (manifest, zip_bytes, key) using DOMAIN_TAG || sha256(manifest) || sha256(zip) framing, constant-time compare, base64-or-plain env-var key loader, sidecar .sig I/O. Post-merge security review by Codex GPT-5.4.
autonomous_governance: true
claude_signoff: yes
codex_tool_invoked: true
codex_diff_hash: 8d397d3d118996a83bdd58cb5eb8352cf8dbfce1
codex_tool_report_path: reports/codex_tool_reports/2026-04-21_pr5c_hmac_review.md
codex_verdict: APPROVED_WITH_NOTES
counter_status: "v6.1 autonomous_governance counter 10 → 11. Codex review invoked post-merge per DEC-V61-013 discipline. User-approved pattern: continue autonomous PR-5c, self-dispatch Codex review post-merge."
reversibility: fully-reversible-by-pr-revert
  (One `git revert -m 1 8d397d3d` removes src/audit_package/sign.py + tests
  + __init__.py exposure updates. manifest.py + serialize.py from earlier
  PRs remain intact and have no dependency on sign.py. No consumers exist
  yet — PR-5d hasn't landed. Clean revert.)
notion_sync_status: synced 2026-04-21T01:35 (https://www.notion.so/348c68942bed811e9f39d406fb2ad991) — Decisions DB page created with Scope=Project, Status=Accepted, Canonical Follow-up=PR #14 URL, Codex verdict + findings recorded in body
github_pr_url: https://github.com/kogamishinyajerry-ops/cfd-harness-unified/pull/14
github_merge_sha: 8d397d3d118996a83bdd58cb5eb8352cf8dbfce1
github_merge_method: merge (regular merge commit — 留痕 > 聪明)
external_gate_self_estimated_pass_rate: 93%
  (HMAC construction sound, constant-time compare confirmed by Codex.
  Residual 7% risk: env-var base64/plain heuristic flagged as medium by
  Codex — could cause inconsistent decoding between signer and external
  verifiers. Queued for PR-5c.1 follow-up.)
supersedes: null
superseded_by: null
upstream: DEC-V61-013 (serialize module — provides _canonical_json + serialize_zip_bytes inputs to HMAC)
kickoff_plan: .planning/phase5_audit_package_builder_kickoff.md
---

# DEC-V61-014: Phase 5 PR-5c — HMAC-SHA256 sign/verify (post-merge Codex review)

## Decision summary

Third of 4 Phase 5 PRs. Adds security-critical HMAC-SHA256 signing + verification for audit-package bundles. Post-merge review by Codex GPT-5.4 returned **APPROVED_WITH_NOTES** — no critical/high findings, 2 medium + 2 low items queued for follow-up PR-5c.1.

## Signing construction

```
hmac_input = DOMAIN_TAG || sha256(canonical_manifest_bytes) || sha256(zip_bytes)
signature  = hmac.new(key, hmac_input, sha256).hexdigest()
```

- `DOMAIN_TAG = b"cfd-harness-audit-v1|"` — domain separation
- Fixed 32-byte SHA-256 prefixes → unambiguous framing
- `canonical_manifest_bytes` = `json.dumps(manifest, sort_keys=True, ensure_ascii=False, indent=2) + "\n"` from `serialize._canonical_json`
- `zip_bytes` from `serialize_zip_bytes(manifest)` — byte-reproducible per DEC-V61-013

Codex confirmed (per-area analysis §1): construction is cryptographically sound for the stated threat model. Length-extension immune (HMAC outer primitive). Concatenation-collision defeated (fixed-length inner digests). Domain separation intact.

## Constant-time compare

`verify()` routes final equality check through `hmac.compare_digest`. Test `TestConstantTimeCompare::test_verify_uses_hmac_compare_digest` patches and asserts the call. Codex confirmed (per-area §2): no fallback path to `==`. `.lower()` normalization is safe for ASCII hex.

## Env var key loader (`CFD_HARNESS_HMAC_SECRET`)

- base64 first (for high-entropy binary keys)
- UTF-8 plain-text fallback
- Unset / empty / whitespace-only → `HmacSecretMissing` with actionable `openssl rand -base64 32` hint

**Codex flagged as Medium (M1)**: the base64-first heuristic can silently reinterpret plain text that happens to match the base64 alphabet pattern. For Python signers + verifiers using the same helper, this is deterministic. For external tooling (bash `openssl`, Go/Rust verifiers) it's brittle. Recommended fix: explicit `base64:` / `text:` prefix on the env-var value. Queued for PR-5c.1.

## Sidecar `.sig` format (v1)

Single line: hex digest + `\n`. Deliberately minimal — auditors can verify with `cat` + documented procedure.

**Codex flagged as Medium (M2)**: v1 is insufficient for regulated retention (no `kid`, algorithm identifier, domain version, manifest hash). Verifiers must guess which retained key to try after rotation. Not a forgery vector but weakens archival verifiability and signer attribution. Fix for v2: add `kid` / `alg` / `domain` / `manifest_sha256` metadata as JSON sidecar. Queued for post-Phase-5 when multi-signer or key-rotation ledger becomes a requirement.

**Codex flagged as Low (L1)**: `read_sidecar` accepts any non-empty string; `write_sidecar` accepts any text. `verify()` rejects malformed values downstream, so this is not a forgery bug — but stricter input validation (regex `^[0-9a-fA-F]{64}$`) would fail faster and keep audit artifacts cleaner. Queued for PR-5c.1.

## Key rotation procedure

Documented in module docstring (generate new key, update env var, old-key-signed bundles remain verifiable by whoever holds the old key).

**Codex flagged as Medium (M2, same finding)**: documentation is incomplete for regulated retention — doesn't specify verifier keyring retention window, key-rotation ledger, successful-verification attribution/logging, multi-signer stories, or compromise/revocation procedure. Queued for a dedicated governance DEC (operational runbook alongside any future key-management upgrade).

**Codex flagged as Low (L2)**: canonical JSON spec must be publishable alongside any future external verification CLI (explicit `sort_keys=True, ensure_ascii=False, indent=2, trailing \n`), so bash/Go/Rust verifiers can produce byte-identical inputs.

## Codex review full report

`reports/codex_tool_reports/2026-04-21_pr5c_hmac_review.md` (committed alongside this DEC).

Token cost: 117,588 (GPT-5.4 xhigh reasoning).

## Follow-up PR-5c.1 (queued, NOT this DEC)

Single PR addressing Codex findings M1 + L1 (smaller-scope, mechanical):

1. **Explicit env-var encoding contract**: `base64:` / `text:` prefix on `CFD_HARNESS_HMAC_SECRET`. Backwards-compat: treat un-prefixed values as UTF-8 plain-text (no more base64 heuristic). Tests: ambiguous / URL-safe / unpadded base64 inputs.
2. **Sidecar hex validation**: enforce `^[0-9a-fA-F]{64}$` on `write_sidecar` + `read_sidecar`. Tests: non-hex / multi-line / wrong-length rejection.

M2 (sidecar v2 with kid/alg/domain + rotation runbook) deferred to a dedicated governance DEC — larger scope that benefits from Kogami design input.

L2 (canonical JSON spec doc) rolls into Phase 5 PR-5d or a post-Phase-5 docs PR.

## 禁区 compliance

| Area | Touched? |
|---|---|
| `src/` (DEC-V61-003 turf) | YES — new `sign.py` |
| `tests/` | YES — 33 new tests |
| `knowledge/**` | NOT TOUCHED |
| `reports/codex_tool_reports/` | YES — Codex review artifact (audit trail per v6.1) |
| Notion DB destruction | NOT TOUCHED |

## Regression

```
pytest 8-file matrix → 284 passed + 1 skipped in 1.62s
```

251 baseline + 33 new across 8 test classes. 1 skip is the PDF-backend raise-path (unreachable on this host where weasyprint works).

## Counter status

v6.1 autonomous_governance counter: 10 → **11**. Codex tool review was invoked for this DEC per the hard-floor-4 discipline established in DEC-V61-013. Going forward PR-5d should follow the same pattern OR Kogami should run the v6.1 formal counter-reset retrospective.

## Reversibility

One `git revert -m 1 8d397d3d` on main + this DEC file cleanup restores pre-PR-5c state. manifest.py + serialize.py remain fully functional without sign.py.

## Next steps

1. Mirror this DEC to Notion.
2. Update STATE.md.
3. Commit Codex review report to repo.
4. Ping Kogami: proceed to PR-5d (Screen 6 UI)? Land PR-5c.1 (Codex fixes) first? Pause for governance retrospective?
