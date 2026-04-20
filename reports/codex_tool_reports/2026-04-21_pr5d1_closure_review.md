# Codex GPT-5.4 Review · PR-5d.1 Screen 6 Audit Package Follow-up

Date: 2026-04-21
Reviewer: GPT-5.4 via Codex post-merge review (round 5 of Phase 5 · 95,221 tokens)
Subject files: `ui/backend/routes/audit_package.py`, `ui/backend/schemas/audit_package.py`, `ui/backend/tests/test_audit_package_route.py`, `ui/frontend/src/pages/AuditPackagePage.tsx`, `ui/frontend/src/types/audit_package.ts`
Merge SHA: `ca9fe0e525a92e8b52ea32092e228b0bf7ace73e`
Baseline SHA: `320bed10`

## Verdict
APPROVED_WITH_NOTES

## Findings by severity
### Critical (must fix immediately)
None.

### High (fix before production use)
None.

### Medium (queue for follow-up)
None.

### Low / Informational
1. PR-5d.1 preserves byte reproducibility by replacing `generated_at` with a deterministic hash fragment, but the API/manifest/UI still present that field as a timestamp.
   Evidence: the route now computes `generated_at = hashlib.sha256(f"{case_id}|{run_id}".encode("utf-8")).hexdigest()[:16]` at `ui/backend/routes/audit_package.py:167-175`; `build_manifest()` still treats `generated_at` as the manifest timestamp override at `src/audit_package/manifest.py:340-342` and emits it verbatim at `src/audit_package/manifest.py:409-413`; the frontend still renders it under the label “Generated at” at `ui/frontend/src/pages/AuditPackagePage.tsx:133-136`; the design docs still describe timestamps as canonicalized UTC values at `docs/ui_design.md:376-378`.
   Why it matters: reviewers or downstream consumers will reasonably read `generated_at` as a wall-clock build time, but current values are opaque 16-hex tokens such as `a843980d36d97c10`.
   Suggested fix: rename this field to something like `deterministic_build_id` / `build_fingerprint`, or keep a real UTC generation timestamp outside the signed canonical payload.

## Per-area analysis
### 1. HIGH #1 (unknown case_id signing hollow bundles)
The specific unknown-`case_id` gap is fixed.

- `build_audit_package()` now rejects unknown cases before signing by calling `load_case_detail(case_id)` and raising HTTP 404 when it returns `None` (`ui/backend/routes/audit_package.py:150-159`).
- That membership check is correct for the stated intent. `load_case_detail()` is backed by `_load_whitelist()`, does `case = whitelist.get(case_id)`, and returns `None` only when the id is absent from the whitelist (`ui/backend/services/validation_report.py:395-399`).
- The replacement test covers the new behavior directly: `test_unknown_case_id_returns_404()` POSTs `/api/cases/nonexistent_case/runs/r1/audit-package/build` and asserts `404` plus the expected error detail (`ui/backend/tests/test_audit_package_route.py:85-94`).

One caveat: the broader PR-5d “dry-build / no-run-output” behavior still exists for known cases. This follow-up did not change that contract; it only closed the unknown-case path.

### 2. HIGH #2 (byte-reproducibility contract)
This finding is fixed.

- The route now injects a deterministic `generated_at` derived from `(case_id, run_id)` before calling `build_manifest()` (`ui/backend/routes/audit_package.py:167-184`).
- `serialize_zip()` is still byte-deterministic for identical manifest input because it canonicalizes JSON, fixes zip metadata, and writes entries in sorted order (`src/audit_package/serialize.py:68-76`, `src/audit_package/serialize.py:144-162`).
- Since the HMAC covers both canonical manifest bytes and zip bytes, identical manifests now produce identical signatures as well (`src/audit_package/sign.py:262-308`).

The new tests are materially correct:

- `test_identical_posts_produce_byte_identical_zip()` asserts identical `generated_at`, identical `signature_hex`, and identical ZIP SHA-256 across two POSTs to the same `(case_id, run_id)` (`ui/backend/tests/test_audit_package_route.py:96-118`).
- `test_different_run_ids_produce_different_bundles()` asserts different `generated_at` and different signatures for `r1` vs `r2` (`ui/backend/tests/test_audit_package_route.py:120-125`). Because `run_id` is also embedded in the signed manifest and included in `manifest.json` inside the zip, this is sufficient to show the bundles diverge.

On the delimiter/collision question:

- The 16-hex prefix is sufficient for determinism; it is not used as the security boundary. Bundle integrity still comes from the full manifest contents plus the HMAC.
- A collision or `|`-delimiter ambiguity would at most make two bundles share the same `generated_at` token; it would not make their manifests, ZIPs, or signatures interchangeable because `case_id` and `run_id` remain explicit signed fields.
- I checked the current whitelist data in this workspace and found no case ids containing `|`, so there is no present cross-case ambiguity. If future case ids may contain delimiters, hashing a structured encoding such as JSON would be cleaner.

### 3. MEDIUM (rename `vv40_checklist` → `evidence_summary`)
This finding is fixed end-to-end.

- Backend schema: `AuditPackageBuildResponse` now exposes `evidence_summary`, and the item model is renamed `AuditPackageEvidenceItem` with an explicit “not a faithful FDA/ASME V&V40 template” description (`ui/backend/schemas/audit_package.py:27-41`, `ui/backend/schemas/audit_package.py:44-72`).
- Route: the response now populates `evidence_summary=[...]` from `_EVIDENCE_SUMMARY` instead of `vv40_checklist=[...]` (`ui/backend/routes/audit_package.py:72-88`, `ui/backend/routes/audit_package.py:239-253`).
- Frontend types: `AuditPackageBuildResponse` and the row type were renamed consistently (`ui/frontend/src/types/audit_package.ts:11-32`).
- Frontend page: the UI now says “Internal V&V evidence summary,” explicitly states it is not a substitute for a formal FDA/ASME V&V40 template, and no longer claims FDA/ASME compliance (`ui/frontend/src/pages/AuditPackagePage.tsx:50-56`, `ui/frontend/src/pages/AuditPackagePage.tsx:182-191`).
- Tests: the route test now asserts `evidence_summary` is present and that the legacy `vv40_checklist` key is absent (`ui/backend/tests/test_audit_package_route.py:28-42`, `ui/backend/tests/test_audit_package_route.py:71-83`).

The disclaimer is sufficient for this PR. It clearly demotes the table from “framework compliance artifact” to “internal evidence mapping,” which addresses the original overclaim.

### 4. Collateral / regressions
No new security or integrity regressions stood out in the changed code.

- `load_case_detail()` does not meaningfully expand the attack surface beyond the existing case-list/detail APIs; it reveals only whitelist membership, which the UI already exposes.
- The 16-hex `generated_at` token is acceptable for determinism and does not weaken signature integrity because signatures still bind the full manifest plus zip bytes.
- Staging-directory behavior is unchanged: per-request UUID directories are still isolated, traversal defenses are unchanged, and TTL cleanup is still absent (`ui/backend/routes/audit_package.py:65-68`, `ui/backend/routes/audit_package.py:186-227`, `ui/backend/routes/audit_package.py:264-277`). That cleanup gap remains an ops follow-up, not a new PR-5d.1 regression.
- I did not find any stale `vv40_checklist` API field usage in the reviewed backend/frontend codepath after the rename. The remaining stale “V&V40 checklist mapping” wording in the top-of-file route docstring is internal commentary only (`ui/backend/routes/audit_package.py:3-5`), not part of the API or UI surface.

## Verification note
Executed:

- `git diff --stat 320bed10..ca9fe0e -- ui/`
- `python3.11 -m pytest -q ui/backend/tests/test_audit_package_route.py` → `18 passed`
- `npm run typecheck` in `ui/frontend` → passed
- Manual FastAPI `TestClient` probes under Python 3.11:
  - `POST /api/cases/nonexistent_case/runs/r1/audit-package/build` returned `404`
  - two identical POSTs to `/api/cases/duct_flow/runs/r1/audit-package/build` produced identical `generated_at`, identical `signature_hex`, and byte-identical ZIP bytes (SHA-256 `28b4efa3772e53cce30a39e30dd02412240192fe28f744dac6170ddffb498ce8`)
  - `POST /api/cases/duct_flow/runs/r2/audit-package/build` diverged as expected from `r1`
  - the unchanged known-case dry-build path still returns `200` with `run.status = "no_run_output"` and empty `measurement`, confirming that PR-5d.1 narrowed the original HIGH #1 by blocking unknown cases but did not alter the pre-existing skeleton-bundle behavior
