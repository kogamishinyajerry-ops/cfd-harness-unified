# Pre-merge Review: `cd455bc`

## Finding 1

- Severity: HIGH
- File: `ui/backend/services/case_solve/bc_setup.py:151-156`
- Root cause: `_restore_pre_split_if_present()` unconditionally restores any existing `constant/polyMesh.pre_split` before looking at the current mesh. That is safe for pure same-mesh retries, but Step 2 re-mesh writes a fresh `constant/polyMesh/` without deleting the sibling backup (`ui/backend/services/meshing_gmsh/to_foam.py:251-265`). After any prior `setup_*_bc()` call, a later Step 2 run on the same `case_dir` leaves a stale `polyMesh.pre_split` behind; the next Step 3 call then clobbers the newly generated mesh with the old backup. I reproduced this locally by running `setup_channel_bc()` once, replacing `constant/polyMesh` with a shifted channel mesh while leaving `polyMesh.pre_split` intact, and calling `setup_channel_bc()` again. The second call restored the old points and failed with `no boundary face matched any inlet pin ...`, proving the new mesh was discarded.
- Suggested fix: invalidate the backup when Step 2 regenerates the mesh, or make restore conditional on a mesh fingerprint match. The minimal safe fix is to delete `constant/polyMesh.pre_split` in the gmsh-to-FOAM materialization path before/after writing the new `constant/polyMesh`. Add a regression test for: first `setup_*_bc()`, then re-mesh same `case_dir`, then `setup_*_bc()` again, asserting the fresh mesh survives and the old backup is ignored.

## Other Checks

- `[A]` No same-process race found in the intended sequential retry flow; both splitters restore before recreating the backup.
- `[C]` LDC and channel splitters follow the same restore → parse → backup → split pattern.
- `[D]` The off-axis topology math is correct for the `1×1×10` prism: `1 inlet + 1 outlet + 4 walls = 6 boundary faces`, and both idempotency tests do invoke the full `setup_*_bc()` path twice.
- `[E]` Targeted compatibility tests passed: `PYTHONPATH=. ./.venv/bin/pytest ui/backend/tests/test_ai_classifier.py -k 'setup_ldc_bc_is_idempotent_on_same_case_dir or setup_channel_bc_is_idempotent_on_same_case_dir or channel_executor_handles_off_axis_inlet_outlet_topology or full_loop_channel_uncertain_pin_inlet_outlet_then_confident or full_loop_channel_executor_writes_correct_inlet_velocity'` → `5 passed`.

## Verdict

`REQUEST CHANGES` — 1 finding.
