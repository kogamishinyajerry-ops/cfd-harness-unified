# R2 Verification: `9889927`

## Finding 1

- Severity: MEDIUM
- File: `ui/backend/services/meshing_gmsh/to_foam.py:287-295`
- Related path: `ui/backend/services/case_solve/bc_setup.py:151-156,408,448`
- Root cause: The new `polyMesh.pre_split` cleanup is ordered correctly after host-side `constant/polyMesh` extraction, but the `except OSError: pass` branch is not actually safe. If `shutil.rmtree(pre_split)` fails, `run_gmsh_to_foam()` still returns success while `_restore_pre_split_if_present()` continues to blindly restore any surviving backup before both the LDC and channel splitters run. The inline comment claims the BC executor will detect a stale backup via a `pre_split` fingerprint check, but no such check exists anywhere in `bc_setup.py`. That means the original stale-backup overwrite remains reachable on the cleanup-failure path.
- Suggested fix: Do not silently continue if invalidating `polyMesh.pre_split` fails. Either raise `GmshToFoamError` from the cleanup branch, or add a real freshness/fingerprint guard before `_restore_pre_split_if_present()` can copy a backup over a newly re-meshed `polyMesh`. Add a regression test for the removal-failure branch as well, since the current test only covers successful backup deletion.

## Other Checks

- `[1]` Ordering is correct: `container.get_archive(...)` + `_extract_tarball(...)` materialize the fresh host `constant/polyMesh` at `ui/backend/services/meshing_gmsh/to_foam.py:259-265` before the stale-backup cleanup runs at `:287-295`.
- `[3]` The new test does exercise the intended post-remesh happy path: it creates a backup, deletes both `constant/polyMesh` and `constant/polyMesh.pre_split`, restages a shifted mesh, then reruns `setup_channel_bc()` with a new outlet face id (`ui/backend/tests/test_ai_classifier.py:947-1018`). This simulates successful Step 2 cleanup; it does not cover the `OSError` fallback branch.
- `[4]` No direct regression was observed in the existing `setup_ldc_bc` same-case idempotency path. Focused verification command: `PYTHONPATH=. .venv/bin/pytest -q ui/backend/tests/test_ai_classifier.py -k 'test_setup_ldc_bc_is_idempotent_on_same_case_dir or test_setup_channel_bc_is_idempotent_on_same_case_dir or test_setup_bc_rejects_stale_pre_split_backup_after_remesh'` → `3 passed, 24 deselected`.

## Verdict

`REQUEST CHANGES` — 1 finding.
