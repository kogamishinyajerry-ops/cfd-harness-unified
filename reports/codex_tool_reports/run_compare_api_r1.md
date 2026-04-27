# Run Compare API Review R1

## Verdict

Request changes before merge.

No P0 issues. I found two P1 blockers:

1. The new route inherits an unsafe path-segment guard from `run_history`, so traversal-like segments such as `..` are accepted and only fail later as `404` instead of being rejected as `400`.
2. The array diff path currently hides `NaN`/`inf` mismatches by reporting zero deviation when the remaining finite points happen to match.

API-contract note: the free-form `dict` response is acceptable short-term for a frontend-only diff surface, and this backend already has a few schema-less JSON endpoints. I would not block on that alone. But it does publish only a generic OpenAPI `type: object` and skips response validation, so add a typed schema before widening external consumers. Relevant lines: `ui/backend/routes/run_history.py:79-84`, `ui/backend/routes/preflight.py:20-26`, `ui/backend/routes/batch_matrix.py:19-22`.

## Findings

### P0

- None.

### P1

- BUG: `compare_runs_route()` is not path-safe as shipped because it relies on `get_run_detail() -> run_dir() -> _safe_segment()`, and `_safe_segment()` accepts dot-only segments such as `..`.
  - Files: `ui/backend/routes/run_history.py:93-100`, `ui/backend/services/run_history.py:40-47`, `ui/backend/services/run_history.py:258-265`
  - Why it matters: `GET /api/cases/%2E%2E/run-history/run_a/compare/run_b` should be rejected as unsafe input, but on a local `TestClient` smoke it returned `404` and attempted to read `reports/../runs/run_a`. That means the new endpoint widens exposure of a real traversal weakness instead of enforcing the repo’s stricter segment-validation standard.
  - Contrast: the repo already has a hardened validator that rejects `.`, `..`, percent-decoded traversal, and embedded `..`: `ui/backend/services/run_ids.py:14-37`.

- BUG: `_array_diff()` silently drops non-finite points and can emit a false “no difference” result for arrays that are not actually comparable.
  - Files: `ui/backend/services/run_compare.py:72-106`, `ui/backend/tests/test_run_compare.py:182-212`
  - Why it matters: for `_array_diff("profile", [1.0, 2.0, 3.0], [1.0, nan, 3.0])`, the current implementation returns `max_abs_dev=0.0`, `max_abs_dev_index=0`, and `mean_abs_dev=0.0`. That makes a NaN-tainted or partially diverged run look identical to the clean run in the diff surface.
  - The docstring promises array diffs that “flag inf/nan” at the top-level service description (`ui/backend/services/run_compare.py:11-15`), but the array path currently provides no taint flag, skipped-index count, or non-finite marker.

### P2

- WARNING: mixed scalar-vs-array changes are misclassified and lose type/shape information.
  - Files: `ui/backend/services/run_compare.py:120-154`
  - Why it matters: `_diff_dicts()` checks `if _is_scalar(va) or _is_scalar(vb)` before array handling. If a quantity changes from scalar to array (or array to scalar) across runs, it falls into `_scalar_diff()` instead of surfacing a type mismatch or array-shape issue. That will be confusing if extraction logic evolves between runs.

- WARNING: the new test module does not exercise the FastAPI route layer, so the HTTP mapping and unsafe-input behavior are currently untested.
  - Files: `ui/backend/tests/test_run_compare.py:86-212`, `ui/backend/routes/run_history.py:93-100`
  - Why it matters: all 10 tests call `compare_runs()` directly. They verify service math, but they do not verify `400` vs `404`, path validation, or the route’s response shape.

## Verification Notes

- `./.venv/bin/python -m pytest ui/backend/tests/test_run_compare.py -q` → `10 passed`
- Local `TestClient` smoke:
  - `GET /api/cases/lid_driven_cavity/run-history/run_a/compare/run_b` → `200`
  - `GET /api/cases/no_such_case/run-history/run_a/compare/run_b` → `404`
  - `GET /api/cases/%2E%2E/run-history/run_a/compare/run_b` → `404` (should be `400` if traversal guard were effective)
- Local direct reproduction:
  - `_array_diff("profile", [1.0, 2.0, 3.0], [1.0, float("nan"), 3.0])`
  - Returned `{'key': 'profile', 'a_len': 3, 'b_len': 3, 'shape_match': True, 'max_abs_dev': 0.0, 'max_abs_dev_index': 0, 'mean_abs_dev': 0.0}`
