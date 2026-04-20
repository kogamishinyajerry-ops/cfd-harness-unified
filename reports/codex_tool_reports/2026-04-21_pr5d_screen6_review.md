# Codex GPT-5.4 Review · PR-5d Screen 6 Audit Package Builder UI + API Route

Date: 2026-04-21
Reviewer: GPT-5.4 via Codex post-merge review
Subject files: `ui/backend/routes/audit_package.py`, `ui/backend/schemas/audit_package.py`, `ui/backend/tests/test_audit_package_route.py`, `ui/frontend/src/pages/AuditPackagePage.tsx`, `ui/frontend/src/types/audit_package.ts`, `ui/frontend/src/api/client.ts`
Merge SHA: `320bed10`
Baseline SHA: `7e6f5732`

## Verdict
CHANGES_REQUIRED

## Findings by severity
### Critical (must fix immediately)
None.

### High (fix before production use)
1. The POST route signs and serves placeholder bundles that are not bound to a real run, and it even accepts nonexistent cases.
   Evidence: the route calls `build_manifest(case_id=case_id, run_id=run_id)` without `run_output_dir`, `measurement`, `comparator_verdict`, or `audit_concerns` at `ui/backend/routes/audit_package.py:149-152`; `build_manifest()` therefore emits `run.status="no_run_output"` and an empty measurement block at `src/audit_package/manifest.py:391-406`; the new test explicitly blesses `POST /api/cases/nonexistent_case/...` returning 200 at `ui/backend/tests/test_audit_package_route.py:79-84`.
   Why it matters: Screen 6 can produce a signed “audit package” that contains no solver inputs, no outputs, no comparator verdict, and no case validation. In a regulated review flow that is a misleading artifact, not an evidence bundle.
   Suggested fix: reject unknown case/run IDs and require a resolved run-output/comparator source before signing, or clearly demote this endpoint to a dry-run/mock export and hide it from operator-facing production UI.

2. PR-5d breaks the documented byte-reproducibility contract at the operator endpoint.
   Evidence: the route does not pass a stable `generated_at` into `build_manifest()` at `ui/backend/routes/audit_package.py:149-152`, so the manifest auto-stamps current UTC time at `src/audit_package/manifest.py:412`; the product docs require identical inputs to produce byte-identical exports at `docs/ui_roadmap.md:220-223` and `docs/ui_design.md:376-378`. A direct probe with two identical POSTs one second apart produced different `generated_at` values, different ZIP hashes, and different HMACs.
   Why it matters: operators cannot reproduce or diff the same run’s bundle reliably; signatures rotate merely because wall-clock time changed.
   Suggested fix: derive `generated_at` from stable run metadata or move the human-visible build timestamp outside the signed canonical payload.

### Medium (queue for follow-up)
1. The hard-coded `vv40_checklist` overstates alignment with FDA/ASME V&V40 and points at evidence the current bundle shape does not contain.
   Evidence: the API exposes eight custom rows at `ui/backend/routes/audit_package.py:78-118`, but the FDA 2023 CM&S guidance structures credibility around preliminary steps, credibility evidence categories, and credibility factors/goals rather than this eight-row list (FDA guidance PDF TOC, p.3 lines 42-56: `https://www.fda.gov/media/154985/download`); the product design also says the V&V40 template should include Context-of-Use and Credibility Goals at `docs/ui_design.md:383-385`. Several mapped fields here, including `run.inputs`, `run.outputs.solver_log_tail`, and `measurement.*`, are absent from every current POST bundle because of finding #1.
   Why it matters: the UI can imply FDA-style coverage that the artifact does not actually provide, which is risky for compliance-facing review.
   Suggested fix: rename this to an internal evidence summary until the real framework template exists, or align it to the guidance categories and only reference fields guaranteed to be present.

### Low / Informational
None.

## Per-area analysis
### 1. Path traversal guard
No blocking issue found. `_resolve_bundle_file()` constrains `bundle_id` to lowercase 32-hex, uses fixed server-side filenames, resolves the candidate path, and verifies it remains under `_STAGING_ROOT` before serving (`ui/backend/routes/audit_package.py:229-245`). There is no shell invocation, so shell metacharacters are irrelevant. Symlink escapes are rejected because `resolve()` is checked against the resolved staging root. The only residual caveat is the usual same-host TOCTOU window between validation and `FileResponse` opening the file; that matters only if an attacker can already mutate the staging tree on disk.

### 2. HMAC secret handling
No secret disclosure bug found in the reviewed paths. The key is loaded fresh on each POST (`ui/backend/routes/audit_package.py:140-144`), never returned, and the 500 detail string comes from `HmacSecretMissing`, which contains rotation guidance but not the secret value (`src/audit_package/sign.py:195-226`). Returning the signature itself in `signature_hex` is expected and not sensitive.

### 3. Staging directory / concurrency / cleanup
UUID4 `bundle_id` directories make accidental collision negligible, and per-request subdirectories avoid ordinary cross-request overwrite races (`ui/backend/routes/audit_package.py:154-163`). The real ops gap is retention: there is still no TTL, quota, or cleanup path, so the staging tree grows monotonically (`ui/backend/routes/audit_package.py:20-31`). That is an operational concern, but I did not treat it as the top production blocker relative to the findings above.

### 4. Download endpoints / FileResponse / REST shape
Serving through `FileResponse` is acceptable here; the response uses attachment `Content-Disposition` and fixed server-side filenames. Five explicit GET endpoints are reasonable because the artifact set is closed and each response has a distinct media type. A generic `/artifacts/{filename}` route would reduce boilerplate but would not materially improve security or REST semantics.

### 5. V&V40 checklist mapping
Not accurate enough to describe as “FDA V&V40 credibility-evidence mapping” in its current form. The implementation is a product-specific summary table, not a faithful rendering of the FDA/ASME framework, and several referenced evidence fields are absent from current bundles.

### 6. Frontend state handling
No state-consistency bug found from the missing query invalidation. This mutation does not update any shared query cache, and TanStack Query clears mutation `data` on pending/error in the installed version, so stale bundle results do not persist after a failed rebuild. Error handling is acceptable for network and malformed-response cases because thrown `Error` objects still surface through `buildMutation.isError`, though the message formatting is fairly raw.

### 7. Additional structural note
Verification in this workspace exposed a broader Python-version mismatch: `pyproject.toml` still declares `requires-python = ">=3.9"` (`pyproject.toml:12-16`), but the current backend import path does not collect cleanly under Python 3.9. That issue predates and exceeds PR-5d, so I did not score it as a PR-local finding, but it remains relevant if 3.9 is still a supported deployment target.

## Verification note
Executed:

- `python3.11 -m pytest -q ui/backend/tests/test_audit_package_route.py` → `16 passed`
- Manual probe with `fastapi.testclient` under Python 3.11:
  - two identical POSTs to `/api/cases/duct_flow/runs/r1/audit-package/build` one second apart yielded different `generated_at` values and different ZIP SHA-256 values
  - downloaded manifest for a normal build showed `run.status = "no_run_output"` and empty `measurement`
  - `POST /api/cases/nonexistent_case/runs/r1/audit-package/build` returned `200`
- `python3 -m pytest -q ui/backend/tests/test_audit_package_route.py` under Python 3.9.6 failed during collection due broader backend typing/runtime compatibility issues, so 3.9 support was not validated from this workspace.
