# Run Compare API Review R2

## Verdict

APPROVE_WITH_COMMENTS.

R1's two P1 blockers are closed, and the route layer is now exercised. I found one remaining P2 edge case worth a follow-up before this diff surface is widened beyond today's numeric-array inputs.

## Findings

### P2

- WARNING: scalar↔array mismatches still lose shape/type info when the "array" side is an empty or non-numeric list.
  - Files: `ui/backend/services/run_compare.py:143-169`, `ui/backend/services/run_compare.py:183-194`
  - Why it matters: the new `type_mismatch=True` branch only triggers when exactly one side satisfies `_is_numeric_array()`, which itself requires a non-empty numeric list. Repro: `_diff_dicts({"k": 1.0}, {"k": []})` currently returns `scalar_diffs=[{"key": "k", "a": 1.0, "b": "[]", ...}]` and no `array_diffs`, so the same shape-loss R1 flagged still happens for empty-list / failed-extraction cases.
  - Suggested follow-up: branch on `isinstance(v, list)` before scalar handling, then use `_kind_of()` only to label numeric vs empty vs nonnumeric list variants inside the mismatch payload.

## R1 Closure Check

- OK: P1.1 closed. `compare_runs_route()` now validates `case_id`, `run_a_id`, and `run_b_id` up front via `_validate_segment()` before calling the service, and direct `TestClient` probes now return `400` for `/api/cases/%2E%2E/run-history/run_a/compare/run_b` and `/api/cases/lid_driven_cavity/run-history/%2E%2E/compare/run_b`. Relevant lines: `ui/backend/routes/run_history.py:80-109`, `ui/backend/services/run_ids.py:22-37`.
- OK: P1.2 closed. `_array_diff()` now surfaces `tainted` plus capped `tainted_indices`, and the NaN-tainted regression test asserts that signal. Relevant lines: `ui/backend/services/run_compare.py:72-121`, `ui/backend/tests/test_run_compare.py:182-220`.
- OK-ish: P2.1 partially closed. Numeric scalar↔array mismatches now land in `array_diffs` with `type_mismatch=True` and `a_kind/b_kind`, which fixes the original repro for non-empty numeric arrays. Relevant lines: `ui/backend/services/run_compare.py:148-167`, `ui/backend/tests/test_run_compare.py:232-267`. The remaining empty/nonnumeric-list gap is the warning above.
- OK: P2.2 closed. The route layer now has four `TestClient` tests for traversal rejection, missing-run `404`, and happy-path JSON shape. Relevant lines: `ui/backend/tests/test_run_compare.py:283-362`.

## Verification Notes

- `PYTHONPATH=. ./.venv/bin/pytest -q ui/backend/tests/test_run_compare.py` -> `16 passed`
- Direct route smoke via `TestClient`:
  - `/api/cases/%2E%2E/run-history/run_a/compare/run_b` -> `400`
  - `/api/cases/..%2F/run-history/run_a/compare/run_b` -> `404` (router-level decode to `/`, so this never reaches the handler)
  - `/api/cases/lid_driven_cavity/run-history/%2E%2E/compare/run_b` -> `400`
  - `/api/cases/lid_driven_cavity/run-history/.../compare/run_b` -> `400`
- Direct helper repro of remaining edge case:
  - `_diff_dicts({"k": 1.0}, {"k": []})` -> emits only `scalar_diffs`, not `array_diffs`
