# PR #23 Post-Merge Review

Baseline: `36e3249`  
Merge SHA: `aed95d4`  
Scope: audit-package `generated_at -> build_fingerprint` rename across 10 files  
Governance trigger: RETRO-V61-001 `>=3-file API schema rename`

## Verdict

`APPROVED_WITH_NOTES`

No blocking defects found in the merged rename. The runtime/API/UI rename is complete inside the audit-package surface, and the in-repo consumers are aligned on `build_fingerprint`.

## Findings

No blocking findings.

## Notes

1. `build_fingerprint` is materially better than `generated_at`, but it is still an identifier derived from `(case_id, run_id)`, not a fingerprint of artifact bytes or repo content. That makes it acceptable here, but only because the code and schema descriptions now explain the derivation clearly.
   Evidence: `ui/backend/routes/audit_package.py`, `ui/backend/schemas/audit_package.py`, `src/audit_package/manifest.py`

2. The new negative assertion in `ui/backend/tests/test_audit_package_route.py` is good for guarding the POST response contract, but it does not fully guard all exposed surfaces against legacy-key drift. A future regression could reintroduce `generated_at` inside `manifest.json` while leaving the route response clean. That is not happening now, but if you want stronger drift detection, add one negative assertion at manifest-builder or downloaded-manifest level.
   Evidence: `tests/test_audit_package/test_manifest.py`, `ui/backend/tests/test_audit_package_route.py`

## Review Answers

1. Is the rename complete?

Yes, for the audit-package subsystem runtime surface.

- Current `generated_at` hits under `src/audit_package`, `ui/backend`, `ui/frontend/src`, and `tests/test_audit_package` are only explanatory comments/docstrings plus the new negative assertion.
- No stale runtime field access remains in the audit-package manifest builder, serializer, backend response model, backend route, frontend types, or frontend page.
- Remaining real `generated_at` usages are in `src/report_engine/*`, which is explicitly out of scope and semantically unrelated.

2. Is `build_fingerprint` semantically correct?

Mostly yes, and clearly better than `generated_at`.

- `artifact_fingerprint` would be wrong because the value is not derived from the built artifact bytes.
- `content_hash` would also be wrong for the same reason.
- `build_id` would be the most conservative alternative if you wanted a name that makes fewer claims.
- Given the current code comments and schema description explicitly saying this is a deterministic 16-hex identifier derived from `(case_id, run_id)`, `build_fingerprint` is acceptable.

Important caveat:

- `src/audit_package/manifest.py` still falls back to `_default_now_utc()` when `build_fingerprint` is omitted.
- That means the generic builder API still permits timestamp-shaped values under the new field name.
- This is not a blocker because the only production caller in-tree, `ui/backend/routes/audit_package.py`, always passes the deterministic hash fragment.

3. Frontend label change UX?

Yes. `Build fingerprint` is better UX than `Generated at` for this value.

- The monospace `<code>` treatment in `ui/frontend/src/pages/AuditPackagePage.tsx` correctly signals that the field is a token, not a date/time.
- This reduces the exact reviewer confusion that triggered the rename.
- Optional future refinement: small helper text such as "deterministic 16-hex id" if non-technical operators will see this screen.

4. Is `test_build_response_has_no_legacy_generated_at_key` sufficient?

Sufficient for route-response drift, not sufficient for every exposed artifact.

- It will catch accidental reintroduction of `generated_at` in the POST response body.
- It will not catch a future regression that adds `generated_at` back into the downloaded `manifest.json` or zipped manifest while keeping the route response clean.
- Existing manifest/serialize/sign tests already exercise the renamed field and would likely catch many mistakes, but they do not currently assert legacy-key absence at the manifest layer.

Recommendation:

- Keep the current route-level assertion.
- If you want stronger future drift detection, add `assert "generated_at" not in manifest` in `tests/test_audit_package/test_manifest.py` or the manifest download E2E path.

5. Backward compatibility / external consumer exposure?

This is a deliberate breaking rename on every public audit-package surface:

- FastAPI response model / OpenAPI schema
- JSON returned by `POST /api/cases/{case_id}/runs/{run_id}/audit-package/build`
- Downloaded `manifest.json`
- Zipped `manifest.json`
- HTML reviewer render
- Frontend TypeScript contract

There are no stale in-repo consumers left on the old key, so the merge is internally coherent.

For out-of-repo consumers:

- There is no compatibility alias.
- Any client expecting `generated_at` will break and must update to `build_fingerprint`.
- Given the stated Path A decision, that trade-off is consistent with choosing a clean contract over dual-field transitional complexity.

## Verification Performed

- `git diff --stat 36e3249 aed95d4`
- `rg -n "generated_at|build_fingerprint" src ui tests`
- `PYTHONPATH=. ./.venv/bin/pytest -q ui/backend/tests/test_audit_package_route.py tests/test_audit_package/test_manifest.py tests/test_audit_package/test_serialize.py tests/test_audit_package/test_sign.py`
  Result: `131 passed, 1 skipped`
- `npm --prefix ui/frontend run typecheck`
  Result: passed
- FastAPI/OpenAPI inspection confirmed `AuditPackageBuildResponse` exposes `build_fingerprint` and not `generated_at`
- TestClient inspection confirmed the route response and downloaded manifest contain `build_fingerprint` and omit `generated_at`
