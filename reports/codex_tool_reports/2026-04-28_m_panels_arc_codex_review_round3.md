# M-PANELS arc · Codex review · Round 3 (DEC-V61-096)

**Date**: 2026-04-28
**Reviewer**: Codex GPT-5.4 (xhigh) — pre-smoke discovery: P1 audit-package contract regression
**Round-3 fix-target commit**: `ca1f48f` — `fix(panels): /api/cases/<id> falls through to imported drafts (DEC-V61-096)`
**Tokens used**: 160,704

## Verdict

`CHANGES_REQUIRED` — 1 P1, 1 WARNING, 0 P2.

## Findings

### Finding 1 [P1]: load_case_detail() widening silently broke audit-package whitelist gate

**Files**:
- `ui/backend/services/validation_report.py:904`
- `ui/backend/routes/audit_package.py:153`
- `src/audit_package/manifest.py:555`

**Issue**: `load_case_detail()` now means "whitelist case OR imported draft exists", but `build_audit_package()` was using it as a whitelist-only gate ("not in knowledge/whitelist.yaml => 404"). After ca1f48f, imported case_ids fell through this gate.

**Codex reproducer** (live test):
```
POST /api/cases/<imported>/runs/no_run/audit-package/build
  → 200 (was meant to 404)
manifest case.whitelist_entry = null
manifest case.gold_standard   = null
```

A signed audit package referencing an imported draft would mislead regulatory reviewers — no gold reference, no validation contract, no provenance (the original Codex PR-5d HIGH #1 reason for that gate).

### Finding 2 [WARNING]: imported/unknown/traversal cases tested via direct service call

**File**: `ui/backend/tests/test_cases_route.py:52`

**Issue**: Only the gold-case path used `client.get(...)` HTTP; imported/unknown/traversal/scaffold cases called `validation_report.load_case_detail()` directly. The actual `/api/cases/<id>` wire path for imported cases was uncovered.

## Round-4 fix lineage

Both addressed in commit `5b21df5` (`fix(panels): restore audit-package whitelist gate via is_whitelisted() (DEC-V61-096)`):

- F1 → New `is_whitelisted(case_id) -> bool` predicate in `validation_report.py`. `audit_package.py:158` switched from `load_case_detail() is None` to `not is_whitelisted()`. Other call sites (`cases.py`, `validation.py`, `build_validation_report`) audited and confirmed to want the broader "exists in any form" semantics.
- F2 → 4 of 7 tests now go through `TestClient.get/post`; added P1 regression guard test + `is_whitelisted` predicate test.

Codex re-ran the P1 reproducer in Round 4 and confirmed it now returns 404.

## Codex Round 3 assessment (verbatim)

> The imported-case fallback itself is fine for `/api/cases/{id}`, but it also changes a shared "case exists in whitelist" predicate and that creates a new contract regression outside the stated happy path.
>
> - Path-traversal guard: correct. The new helper matches `case_drafts.is_safe_case_id()`'s allowlist.
> - Gold-case contract: preserved. The whitelist branch in `load_case_detail()` is unchanged.
> - Imported `CaseDetail` synthesis: acceptable for the stated `/api/cases/{id}` happy path.
> - Collision behavior: correct. Whitelist still wins because the draft fallback only runs when the whitelist lookup misses.

Codex-verified: CHANGES_REQUIRED
