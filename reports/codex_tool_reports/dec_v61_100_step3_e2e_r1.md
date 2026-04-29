Verdict: APPROVE_WITH_COMMENTS

Finding count: 1

Scope

- Repo: `/Users/Zhuanz/Desktop/cfd-harness-unified`
- Commit: `8546f5054ba4afd28932ea4773d717101c785e67`
- Parent: `a83c2b20dd8efbffa13f9a0cd2ce66db1f04d54c`
- Changed file: `ui/backend/tests/test_setup_bc_envelope_route.py`

Findings

1. LOW — Negative-path E2E does not prove the bad `lid` pin actually survived PUT before the second POST

- File: `ui/backend/tests/test_setup_bc_envelope_route.py:430-441`
- Root cause: after the negative-path `PUT /api/cases/{id}/face-annotations`, the test only asserts `200` and then checks that the next `POST /setup-bc` stays `uncertain` and leaves `case_dir / "0"` absent. That final state is also the default no-annotation path, so this test does not prove that the wrong-face `lid` annotation was actually persisted and then re-read by the route layer. A regression that silently dropped the face entry while still returning `200` would leave this test green.
- Suggested fix: mirror the positive-path proof. Capture `put_payload = r_put.json()`, assert `put_payload["revision"] == 1`, assert the `bottom_face_id` entry exists with `name == "lid"` and `confidence == "user_authoritative"`, and assert the second envelope consumed that revision (`env["annotations_revision_consumed"] == 1`). That converts the test from "default uncertain path stayed uncertain" to "persisted wrong-face lid pin was re-read and still stayed uncertain."

Checklist Notes

1. Test isolation

- `_isolated_imported` now patches all three relevant module-level `IMPORTED_DIR` bindings: `ui.backend.services.case_scaffold`, `ui.backend.routes.case_solve`, and `ui.backend.routes.case_annotations` (`ui/backend/tests/test_setup_bc_envelope_route.py:27-46`).
- Combined with per-test `tmp_path`, fresh `TestClient`, and randomized `case_id`, I did not find shared-state leakage inside this file.

2. Positive full-loop correctness

- `test_envelope_full_loop_uncertain_pin_lid_then_confident_via_http` does exercise the real HTTP POST → PUT → POST loop (`ui/backend/tests/test_setup_bc_envelope_route.py:307-361`).
- The second POST proves it reloaded on-disk annotations via `annotations_revision_consumed == 1` (`:358`), and the executor run is evidenced by new `0/` and `system/` directories (`:359-360`).

3. Negative executor guard

- `assert not (case_dir / "0").is_dir()` is a sound proxy for "`setup_ldc_bc` did not run" in this repo.
- `_author_dicts()` creates `0/` immediately when `setup_ldc_bc` executes (`ui/backend/services/case_solve/bc_setup.py:222-224`), so a `200/uncertain` response plus no `0/` directory is valid evidence that the executor did not fire.

4. Inline cube fixture

- The duplicated cube fixture in this commit is semantically aligned with the existing classifier fixture today.
- I compared the four payloads against `ui/backend/tests/test_ai_classifier.py:42-202`; `points`, `faces`, `boundary`, and `owner` normalize equal, so I did not find current fixture drift in this commit.

Verification

```bash
PYTHONPATH=. .venv/bin/pytest -q ui/backend/tests/test_setup_bc_envelope_route.py
PYTHONPATH=. .venv/bin/pytest -q ui/backend/tests/test_ai_classifier.py -k 'full_loop_uncertain_then_pin_top_lid_then_confident'
```

Results

- `ui/backend/tests/test_setup_bc_envelope_route.py` — `9/9` passed
- `ui/backend/tests/test_ai_classifier.py -k full_loop_uncertain_then_pin_top_lid_then_confident` — `1/1` selected test passed
