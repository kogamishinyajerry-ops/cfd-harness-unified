# M-PANELS arc · Codex review · Round 4 (DEC-V61-096)

**Date**: 2026-04-28
**Reviewer**: Codex GPT-5.4 (xhigh)
**Round-4 fix commit**: `5b21df5` — `fix(panels): restore audit-package whitelist gate via is_whitelisted() (DEC-V61-096)`
**Tokens used**: 178,393

## Verdict

`APPROVE` — 0 P1, 0 P2, 0 WARNING.

## Codex assessment (verbatim)

> **Findings**
>
> No blocking findings.
>
> **Review**
>
> 1. The whitelist-only gate is restored correctly. `audit_package.py:160` now uses `validation_report.is_whitelisted` instead of relying on `load_case_detail()`. I re-ran the P1 reproducer with a seeded imported draft through `TestClient`: `GET /api/cases/imported_review_probe_case` returned `200`, while `POST /api/cases/imported_review_probe_case/runs/no_run/audit-package/build` returned `404` with `unknown case_id: 'imported_review_probe_case' (not in knowledge/whitelist.yaml)`.
>
> 2. `is_whitelisted()` is the right primitive shape. Keeping a named whitelist-membership predicate next to `_load_whitelist()` makes the contract explicit and documents why `load_case_detail()` is no longer safe as a whitelist surrogate. Inlining `_load_whitelist().get(case_id)` in the route would work mechanically, but it is easier to regress later and couples the route to a private loader unnecessarily.
>
> 3. I did not find another live caller needing the same treatment. `cases.py:31` intentionally wants "exists in any form", `validation.py:58` also wants that broader semantics and I confirmed an imported case reaches `/api/cases/{id}/runs` as `200 []`, and `validation_report.py:969` still rejects imported cases for `/api/validation-report/{id}` via `gold_standard is None`.
>
> 4. The tests cover both layers adequately. `test_cases_route.py:78` now exercises the actual `/api/cases/{id}` HTTP path for imported cases, `test_cases_route.py:121` guards the audit-package POST regression on the real route, and `test_cases_route.py:139` proves the helper semantics directly. The traversal check staying partly service-level is reasonable because the router normalizes dot-segments before the handler sees them.
>
> 5. No new correctness findings introduced by this round. Verification I ran locally was `PYTHONPATH=. ./.venv/bin/pytest -q ui/backend/tests/test_cases_route.py` (`7 passed`) plus the direct imported-case POST probe above.

## Closure

Round 3 P1 (audit-package whitelist regression) and Round 3 WARNING (route-layer test gap) both verified RESOLVED. Pre-merge gate per RETRO-V61-001: **CLEARED** for the M-PANELS Tier-A arc + smoke-prep follow-ups.

Cumulative arc: `08b0d16..5b21df5` — 4 Codex rounds total, ending APPROVE on the smoke-prep extension that surfaced after Round 2's APPROVE on the original Tier-A arc.

Codex-verified: APPROVE
