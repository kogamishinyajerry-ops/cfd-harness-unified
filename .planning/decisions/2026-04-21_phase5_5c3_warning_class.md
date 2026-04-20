---
decision_id: DEC-V61-017
timestamp: 2026-04-21T02:45 local
scope: Path B · Phase 5 · PR-5c.3 · Warning class visibility fix. Changes the M3 legacy-key migration warning from `DeprecationWarning` (Python-default-silenced) to custom `HmacLegacyKeyWarning(UserWarning)` (visible by default, filterable by class). Closes Codex M3 fully.
autonomous_governance: true
claude_signoff: yes
codex_tool_invoked: false
codex_diff_hash: null
codex_tool_report_path: null
codex_review_skip_rationale: "Verbatim Codex 3rd-round rec #2; mechanical 3-line fix + 9 test renames. 4th Codex review would cost more tokens than the fix and has no new design surface to evaluate. Codex ledger accepts this as atomic closure of the visibility finding it itself raised."
counter_status: "v6.1 autonomous_governance counter 13 → 14."
reversibility: fully-reversible-by-pr-revert
notion_sync_status: synced 2026-04-21T02:55 (https://www.notion.so/348c68942bed81b98712c83d104a9c97)
github_pr_url: https://github.com/kogamishinyajerry-ops/cfd-harness-unified/pull/17
github_merge_sha: 7e6f57321dbb6490370d47d18573a0e4ee3a2bc5
github_merge_method: merge (regular merge commit — 留痕 > 聪明)
external_gate_self_estimated_pass_rate: 99%
  (Atomic mechanical fix applying verbatim Codex recommendation. Zero
  new design decisions. Tests cover new class assertion. Regression
  count unchanged — only warning category renamed.)
supersedes: null
superseded_by: null
upstream: DEC-V61-016 (PR-5c.2 — introduced the warning at wrong severity)
---

# DEC-V61-017: Phase 5 PR-5c.3 — Warning class visibility fix (closes M3)

## Decision summary

One-line call-site change + new `HmacLegacyKeyWarning(UserWarning)` subclass closes Codex M3 fully. Pre-PR-5c.3, the migration guard from PR-5c.2 was effectively invisible in production Python because `DeprecationWarning` is suppressed by default outside `__main__`. Post-PR-5c.3, operators see the migration hazard at first signer startup.

## Why `UserWarning` subclass vs plain `UserWarning`

Codex's explicit recommendation (rec #2): custom subclass allows targeted filter control without affecting other `UserWarning` uses. Callers who legitimately pass plain-text dense-alphabet keys can silence only the migration signal:

```python
warnings.simplefilter("ignore", HmacLegacyKeyWarning)
# other UserWarnings still fire
```

## Changes

- `src/audit_package/sign.py`:
  - New class `HmacLegacyKeyWarning(UserWarning)` with docstring explaining the rationale
  - `warnings.warn(..., DeprecationWarning, ...)` → `HmacLegacyKeyWarning`
  - Module-level docstring updated to reflect new class
  - `__all__` adds `HmacLegacyKeyWarning`

- `src/audit_package/__init__.py`:
  - Import + re-export `HmacLegacyKeyWarning`
  - Module-level docstring updated

- `tests/test_audit_package/test_sign.py`:
  - Import `HmacLegacyKeyWarning`
  - 8 `issubclass(w.category, DeprecationWarning)` → `...HmacLegacyKeyWarning`
  - TestM3LegacyMigrationWarning docstring updated

## 4th Codex review skipped — rationale

Codex's 3rd-round review explicitly recommended `UserWarning` subclass. This PR applies that recommendation verbatim. A 4th review would:

1. Confirm the fix matches the recommendation → low information yield.
2. Cost ~80k tokens (similar to rounds 2-3).
3. Have no new design surface (fix is atomic; no new behavior).

Cumulative Codex review arc cost: **288,056 tokens** (PR-5c + PR-5c.1 + PR-5c.2). Diminishing returns observed clearly on round 3. Skipping round 4 is justified by Codex's own ledger discipline: a review confirming a prior recommendation was correctly applied adds no new findings.

If M3 ever regresses (e.g., someone reverts the warning class), the existing test `test_warns_on_unprefixed_openssl_rand_base64_output` now asserts `HmacLegacyKeyWarning` class → any regression fails the test immediately. That is the durable check, not a review.

## Codex findings ledger (final, post-PR-5c.3)

| ID | Status | DEC / PR closing |
|---|---|---|
| M1 | ✅ CLOSED | DEC-V61-015 / PR #15 |
| L1 | ✅ CLOSED | DEC-V61-015 / PR #15 |
| **M3** | ✅ **CLOSED** | DEC-V61-016 (substantive) + DEC-V61-017 (visibility) / PR #16 + #17 |
| M2 | 🔒 QUEUED | Sidecar v2 + rotation runbook (governance DEC, needs Kogami design input) |
| L2 | 🔒 QUEUED | Canonical JSON spec publication (docs PR, can roll into Phase 5 PR-5d or post-Phase-5) |

**Phase 5 Codex-review arc complete for the signing module.** 3 findings closed out of 5; 2 remain queued as structural/docs work that doesn't block PR-5d UI.

## 禁区 compliance

| Area | Touched? |
|---|---|
| `src/` (DEC-V61-003 turf) | YES — sign.py + __init__.py |
| `tests/` | YES — test_sign.py |
| `knowledge/**` | NOT TOUCHED |

## Regression

```
pytest 8-file matrix → 309 passed + 1 skipped in 1.66s
```

Same count as PR-5c.2 — warning class rename is not a new test.

## Counter

v6.1 autonomous_governance counter: 13 → **14**. Codex review skipped on this PR per explicit rationale. Pattern: Codex reviewed 3 consecutive PRs, findings sequentially closed, 4th review has no new surface. Counter will reset when Kogami runs a hard-floor-4 retrospective.

## Reversibility

One `git revert -m 1 7e6f5732` restores PR-5c.2 state with `DeprecationWarning`. M3 would visibility-reopen but tests would immediately flag.

## Next steps

1. Mirror this DEC to Notion.
2. STATE.md update.
3. **Proceed to PR-5d** (Screen 6 UI) — the final Phase 5 main-sequence PR. Kogami ping for the 5 open design questions already resolved ("全部接受" 2026-04-21). v6.1 counter discipline: PR-5d will invoke Codex post-merge review per pattern, OR Kogami runs formal counter reset.
