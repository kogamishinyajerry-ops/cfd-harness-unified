---
decision_id: DEC-V61-016
timestamp: 2026-04-21T02:30 local
scope: Path B · Phase 5 · PR-5c.2 · Codex M3 mitigation. Adds migration note to sign.py module docstring, runtime DeprecationWarning for legacy-looking un-prefixed base64 env vars, and edge-case tests for URL-safe base64 / BOM / CRLF sidecars. Post-merge third-round Codex review returns APPROVED_WITH_NOTES — correctness OK but warning severity (DeprecationWarning) is Python-default-suppressed; queued for immediate PR-5c.3 fix.
autonomous_governance: true
claude_signoff: yes
codex_tool_invoked: true
codex_diff_hash: 87264bc10f9084c772cb54912ecd9b1add695865
codex_tool_report_path: reports/codex_tool_reports/2026-04-21_pr5c2_m3_review.md
codex_verdict: APPROVED_WITH_NOTES
counter_status: "v6.1 autonomous_governance counter 12 → 13. Third consecutive Codex post-merge review."
reversibility: fully-reversible-by-pr-revert
  (One `git revert -m 1 87264bc1` removes the migration docstring + guard
  + 11 tests. Prior PR-5c.1 state is restored. M3 would re-open.)
notion_sync_status: synced 2026-04-21T02:35 (https://www.notion.so/348c68942bed81309326dbf19543fb24)
github_pr_url: https://github.com/kogamishinyajerry-ops/cfd-harness-unified/pull/16
github_merge_sha: 87264bc10f9084c772cb54912ecd9b1add695865
github_merge_method: merge (regular merge commit — 留痕 > 聪明)
external_gate_self_estimated_pass_rate: 88%
  (Heuristic is correct, edge tests cover intended cases, but warning-
  visibility issue means the runtime guard doesn't actually reach
  operators — PR-5c.2's "runtime guard" delivery is aspirational until
  PR-5c.3 lands. M3 is therefore substantively addressed but not fully
  closed.)
supersedes: null
superseded_by: null
upstream: DEC-V61-015 (PR-5c.1 surfaced M3 via Codex review)
kickoff_plan: .planning/phase5_audit_package_builder_kickoff.md
followup_pr: PR-5c.3 (DEC-V61-017) — change DeprecationWarning to visible UserWarning subclass
---

# DEC-V61-016: Phase 5 PR-5c.2 — Codex M3 mitigation (APPROVED_WITH_NOTES, visibility fix queued)

## Decision summary

Mechanical mitigation for Codex M3 (legacy migration hazard surfaced by PR-5c.1 Codex review). Three deliverables landed:

1. **Migration note** in `src/audit_package/sign.py` module docstring.
2. **Runtime guard** `_looks_like_legacy_base64` + warning emission when un-prefixed env value matches plausible-binary-key base64 heuristic.
3. **Edge-case tests**: URL-safe base64 rejection, unpadded base64 rejection, CRLF sidecar acceptance, BOM sidecar rejection, trailing whitespace.

Third-round Codex review confirmed: heuristic is appropriate, edge tests cover intended cases, **BUT** the `DeprecationWarning` class is suppressed by default in Python ≥3.7 outside `__main__`, making the runtime guard invisible to operators at signer startup — the intended delivery mechanism.

## Codex third-round per-area findings

| Area | Status |
|---|---|
| Migration note prominence | OK — module docstring is sufficient for PR-5d UI wiring round |
| `_looks_like_legacy_base64` heuristic accuracy | OK — narrow enough (≥24, standard alphabet, valid padding, decodes) |
| False-positive rate | Acceptable — dense-alphabet plain text can warn; `text:` escape hatch documented |
| Warning severity choice | **INCORRECT** — `DeprecationWarning` is silenced by default |
| Edge-case test coverage | OK — no false negatives found |

## Visibility issue — root cause

Per Codex: `DeprecationWarning` is Python's "developer-facing" class, silenced by default outside `__main__` unless tests explicitly enable capture (as our `recwarn`-using tests do). Operators running the signer in production will NOT see the warning.

The correct class for "operator action required" is `UserWarning` (or a custom subclass for targeted filter control).

Our tests pass because pytest's `recwarn` fixture enables all warning capture. Production Python doesn't.

## Mitigation plan — PR-5c.3 (next, DEC-V61-017)

Three-line change:

1. Add `class HmacLegacyKeyWarning(UserWarning): pass` in sign.py.
2. Change `warnings.warn(..., DeprecationWarning, ...)` → `warnings.warn(..., HmacLegacyKeyWarning, ...)`.
3. Update test assertions: `issubclass(w.category, DeprecationWarning)` → `issubclass(w.category, HmacLegacyKeyWarning)`.
4. Update module docstring sentence "at DeprecationWarning level" → "at HmacLegacyKeyWarning level (UserWarning subclass, visible by default)".

Fixes the visibility issue exactly per Codex recommendation #2. No new functionality; M3 becomes truly closed after PR-5c.3 merges.

## Other Codex notes (non-blocking)

Codex also reported a `TestConstantTimeCompare` failure in their environment, but verified in our venv (with `pytest-mock`) the test passes. Likely Codex ran system Python without pytest-mock. Not a real regression.

## Codex findings ledger

| ID | Severity | Status post-PR-5c.2 |
|---|---|---|
| M1 | Medium | ✅ CLOSED (PR-5c.1) |
| L1 | Low | ✅ CLOSED (PR-5c.1) |
| **M3** | **Medium** | **🟡 SUBSTANTIVELY CLOSED — visibility fix queued in PR-5c.3** |
| M2 | Medium | 🔒 QUEUED (sidecar v2 + rotation runbook — governance DEC) |
| L2 | Low | 🔒 QUEUED (canonical JSON spec — docs PR) |

## 禁区 compliance

| Area | Touched? |
|---|---|
| `src/` (DEC-V61-003 turf) | YES — sign.py docstring + helper + guard |
| `tests/` | YES — 11 new tests |
| `knowledge/**` | NOT TOUCHED |
| `reports/codex_tool_reports/` | YES — third review artifact (token cost 94,316) |

## Regression

```
pytest 8-file matrix → 309 passed + 1 skipped in 1.61s
```

298 prior baseline + 11 new. No regressions.

## Counter

v6.1 autonomous_governance counter: 12 → **13**. Third consecutive Codex post-merge review.

**Review arc token costs**: 117,588 + 76,152 + 94,316 = **288,056 total** across PR-5c / PR-5c.1 / PR-5c.2. Diminishing marginal returns — 3rd review found only the warning-class issue, which is a non-functional usability defect. Recommend NO 4th Codex review for PR-5c.3 (mechanical fix; any review would be >token cost of fix).

## Reversibility

One `git revert -m 1 87264bc1` on main restores pre-PR-5c.2 state.

## Next steps

1. Mirror this DEC to Notion.
2. STATE.md update.
3. Land PR-5c.3 immediately (mechanical visibility fix per Codex rec #2).
4. DEC-V61-017 closes M3 fully.
5. Proceed to PR-5d (Screen 6 UI).
