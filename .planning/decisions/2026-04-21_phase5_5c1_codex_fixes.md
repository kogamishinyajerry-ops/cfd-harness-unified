---
decision_id: DEC-V61-015
timestamp: 2026-04-21T02:00 local
scope: Path B · Phase 5 · PR-5c.1 · Codex M1 + L1 mechanical fixes. Replaces env-var base64-heuristic with explicit `base64:` / `text:` / un-prefixed-as-plain-text contract. Adds `^[0-9a-fA-F]{64}$` validation on sidecar write + read. Post-merge Codex review returned APPROVED_WITH_NOTES with one new M3 (legacy migration hazard).
autonomous_governance: true
claude_signoff: yes
codex_tool_invoked: true
codex_diff_hash: db83764b55fe78048aaaeed3c325552f7b5bfb54
codex_tool_report_path: reports/codex_tool_reports/2026-04-21_pr5c1_codex_followup_review.md
codex_verdict: APPROVED_WITH_NOTES
counter_status: "v6.1 autonomous_governance counter 11 → 12. Codex reviewed post-merge per pattern established in DEC-V61-014."
reversibility: fully-reversible-by-pr-revert
  (One `git revert -m 1 db83764b` restores PR-5c's env-var heuristic + lax
  sidecar I/O. Because test changes include renaming and new cases, a
  revert also reverts the test surface — acceptable, since the pre-PR-5c.1
  state passed its own tests.)
notion_sync_status: synced 2026-04-21T02:10 (https://www.notion.so/348c68942bed811ab9b0e2715b443efa) — Decisions DB page created with Scope=Project, Status=Accepted, Canonical Follow-up=PR #15 URL, Codex M3 new finding recorded in body
github_pr_url: https://github.com/kogamishinyajerry-ops/cfd-harness-unified/pull/15
github_merge_sha: db83764b55fe78048aaaeed3c325552f7b5bfb54
github_merge_method: merge (regular merge commit — 留痕 > 聪明)
external_gate_self_estimated_pass_rate: 92%
  (Fixes are correct per Codex static analysis + focused probes. 298/1skip
  regression. Residual 8% risk: M3 silent-migration hazard — legacy
  un-prefixed base64 env vars become literal UTF-8 bytes with no error.
  Mitigation queued as PR-5c.2 docs-only amendment.)
supersedes: null
superseded_by: null
upstream: DEC-V61-014 (PR-5c HMAC; this DEC closes two of its four Codex
  findings). M2 and L2 remain queued.
kickoff_plan: .planning/phase5_audit_package_builder_kickoff.md
---

# DEC-V61-015: Phase 5 PR-5c.1 — Codex M1 + L1 fixes (second-round APPROVED_WITH_NOTES)

## Decision summary

Mechanical follow-up to PR-5c addressing Codex GPT-5.4 findings M1 (env-var base64-vs-plain ambiguity) and L1 (missing sidecar hex-shape validation). Post-merge Codex re-review confirms the fixes are technically correct and introduces one new **M3 legacy-migration hazard**.

## Changes

### M1 · Explicit env-var encoding prefix

```
CFD_HARNESS_HMAC_SECRET:
  `base64:<padded-standard-base64>`  → base64-decoded bytes
  `text:<utf-8-string>`              → UTF-8 encoded
  un-prefixed                        → UTF-8 plain-text (no heuristic)
```

Malformed `base64:` payload → `HmacSecretMissing` with fix hint.
Empty `text:` / `base64:` payload → `HmacSecretMissing`.

**Behavioral change**: `CFD_HARNESS_HMAC_SECRET=aGVsbG8=` previously produced `b"hello"` (heuristic base64 decode); now produces `b"aGVsbG8="` (literal UTF-8). Test `test_un_prefixed_base64_looking_string_is_literal` locks the new contract.

### L1 · Sidecar hex-shape validation

- `write_sidecar` raises `ValueError` on empty / wrong-length / non-hex / multi-line input
- `read_sidecar` returns None on same malformed inputs
- Contract: `^[0-9a-fA-F]{64}$` (case-insensitive, post-strip)

Test surface expanded: 14 new tests across `TestGetHmacSecretFromEnv` (+6), `TestSidecarIO` (+5), `TestEndToEnd` (+3).

## Codex second-round verdict

**APPROVED_WITH_NOTES**. Full report at `reports/codex_tool_reports/2026-04-21_pr5c1_codex_followup_review.md` (token 76,152).

Codex confirmed:
- M1 closure: explicit-prefix parser is correct; reserved prefixes disambiguated; residual base64-looking-literal → now explicitly literal.
- L1 closure: regex correctly blocks non-hex / wrong-length / multi-line on both write and read.
- Tests correctly capture the new contract; no accidentally-asserting-old-behavior tests.

## New Codex finding: M3 legacy-migration hazard (Medium)

> A legacy PR-5c deployment using an un-prefixed base64 secret is accepted as a valid un-prefixed text secret in PR-5c.1, so the HmacSecretMissing error message never appears. For that reason, the message itself is not enough as the primary migration mechanism.

Concretely: if an operator had `CFD_HARNESS_HMAC_SECRET=aGVsbG8=` working on PR-5c (signer used key bytes `b"hello"`), PR-5c.1 silently reinterprets it as `b"aGVsbG8="` and every new signature will diverge. The signer and its own existing verifier using the same deployment will both break, but no error fires — the operator notices only via failed verification downstream.

**Codex's recommended mitigations** (not applied in PR-5c.1, queued):

1. Explicit upgrade note in module docstring + README: "If `CFD_HARNESS_HMAC_SECRET` previously held unprefixed base64, rewrite as `base64:<same>` before deploying PR-5c.1."
2. Optional runtime migration guard: heuristically detect un-prefixed values that look like valid padded base64 of ≥16 bytes and emit a `DeprecationWarning` pointing at the explicit prefix.
3. Edge-case tests for URL-safe base64, unpadded base64, BOM, case-sensitive prefixes, CRLF line endings.

## Mitigation plan (PR-5c.2, queued)

Single docs-only PR addressing Codex M3 Recommendation 1:

- Add migration section to `src/audit_package/sign.py` module docstring.
- Add short note to `README.md` Phase 5 section (if it exists) or to a new `docs/audit_package_migration.md`.
- Optionally: runtime `DeprecationWarning` guard for legacy-looking values (Codex rec #2). Low-risk, ~5 LOC.

Edge-case tests (Codex rec #3) can roll into PR-5c.2 or stand alone.

## Codex findings ledger (running tally across PR-5c + PR-5c.1)

| ID | Severity | Status | Resolution |
|---|---|---|---|
| M1 | Medium | ✅ CLOSED | PR-5c.1 explicit prefix contract |
| M2 | Medium | 🔒 QUEUED | Sidecar v2 + rotation runbook — governance DEC |
| **M3** | **Medium** | **🔒 NEW — QUEUED** | **Legacy migration hazard — PR-5c.2 docs-only** |
| L1 | Low | ✅ CLOSED | PR-5c.1 hex-shape validation |
| L2 | Low | 🔒 QUEUED | Canonical JSON spec publication |

## 禁区 compliance

| Area | Touched? |
|---|---|
| `src/` (DEC-V61-003 turf) | YES — edits to sign.py |
| `tests/` | YES — 14 new/modified tests |
| `knowledge/**` | NOT TOUCHED |
| `reports/codex_tool_reports/` | YES — second review artifact |

## Regression

```
pytest 8-file matrix → 298 passed + 1 skipped in 1.58s
```

284 baseline + 14 new. No pre-existing test broken except renames noted in PR body.

## Counter

v6.1 autonomous_governance counter: 11 → **12**. Codex invoked per established pattern (security-critical diff, even if mechanical). Pattern holds across 2 consecutive PRs now, demonstrating the counter-discipline is sustainable.

## Reversibility

One `git revert -m 1 db83764b` on main restores PR-5c state. The 14 test changes revert with it.

## Next steps

1. Mirror this DEC to Notion (will include M3 for audit continuity).
2. Update STATE.md — counter tick + Codex findings ledger.
3. Queue PR-5c.2 as small docs-only amendment addressing M3 rec #1 (can land alongside PR-5d or before).
4. Proceed to PR-5d (Screen 6 UI) unless Kogami wants PR-5c.2 first.
