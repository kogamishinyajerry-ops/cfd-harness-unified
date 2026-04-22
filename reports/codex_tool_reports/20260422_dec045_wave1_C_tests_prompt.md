# [CLAUDE → CODEX TOOL INVOCATION]

    from: claude-code-opus47 (Main Driver v6.2)
    to: codex-gpt54-xhigh (Joint Dev Peer · §A Diff Generator)
    task: "DEC-V61-045 Wave 1 Invocation C — test coverage for Wave 1 fixes"
    contract: Notion DEC-V61-045 PROPOSAL
    spec: .planning/decisions/2026-04-22_phase8_dec045_attestor_gates_blocker_fixes_PROPOSAL.md
    upstream_findings:
      - reports/codex_tool_reports/20260422_dec036b_codex_review.md (S2 nit — test coverage weaker than DEC claimed)
      - reports/codex_tool_reports/20260422_dec038_codex_review.md (CA-008 — missing 10-case integration)

    scope:
      Add test cases covering Wave 1 A/B changes. Do NOT modify existing tests
      unless they break from API shift. If an existing test needs signature
      update (e.g., attest(log) → attest(log, ...)), only update the minimum
      necessary; do NOT refactor or improve unrelated tests.

    allowed_files:
      - ui/backend/tests/test_convergence_attestor.py
      - ui/backend/tests/test_comparator_gates_g3_g4_g5.py

    read_only_context:
      - src/convergence_attestor.py   (post-Wave-1-A state; new APIs)
      - src/comparator_gates.py       (post-Wave-1-B state; new VTK reader)
      - knowledge/attestor_thresholds.yaml
      - reports/codex_tool_reports/20260422_dec045_wave1_A_convergence_attestor_result.md
      - reports/codex_tool_reports/20260422_dec045_wave1_B_comparator_gates_result.md

    forbidden_files:
      - any file not in allowed_files

    autonomy: TOOL-SCOPE

---

## Test cases to add

### In `ui/backend/tests/test_convergence_attestor.py`

Add these tests (new top-level `def test_*` functions). Import signatures:
```python
from src import convergence_attestor as ca
from src.convergence_attestor import Thresholds, load_thresholds
```

1. **test_load_thresholds_defaults**: `load_thresholds()` returns Thresholds with values matching YAML `defaults` section. Verify `continuity_floor==1e-4`, `residual_floor==1e-3`, `residual_floor_per_field["p_rgh"]==1e-2`.

2. **test_load_thresholds_per_case_impinging_jet**: `load_thresholds("impinging_jet")` returns Thresholds where `residual_floor_per_field["p_rgh"]==5e-3`. Other fields inherit defaults.

3. **test_load_thresholds_per_case_rayleigh_benard**: `load_thresholds("rayleigh_benard_convection")` returns Thresholds where `residual_floor_per_field["h"]==2e-3` AND `no_progress_decade_frac==0.3`.

4. **test_load_thresholds_unknown_case_falls_back**: `load_thresholds("nonexistent_xyz_12345")` returns Thresholds identical to `load_thresholds()` (defaults). No exception, no log ERROR (WARN or silent is OK).

5. **test_load_thresholds_missing_yaml_uses_hardcoded** (tmp_path fixture):
   ```python
   bad_path = tmp_path / "nonexistent.yaml"
   t = load_thresholds(yaml_path=bad_path)
   # Must return Thresholds instance, not raise. Values should match
   # hardcoded defaults (pre-YAML constants).
   assert t.continuity_floor == ca.A2_CONTINUITY_FLOOR
   assert t.residual_floor == ca.A3_RESIDUAL_FLOOR
   ```

6. **test_a1_exit_code_false_forces_fail**: construct a mock `execution_result` object (use `types.SimpleNamespace(success=False, exit_code=139)`). Pass a log with NO fatal markers. Call `_check_a1_solver_crash(log, execution_result=er)`. Assert verdict==FAIL, evidence contains exit_code.

7. **test_a1_log_fatal_fires_even_with_success_exit**: construct `execution_result=SimpleNamespace(success=True, exit_code=0)`. Pass a log containing `Floating exception` in the middle. Assert verdict==FAIL (log signal alone is sufficient).

8. **test_a1_sigFpe_banner_not_false_positive**: regression guard — a log with the startup banner `sigFpe : Enabling floating point exception trapping (FOAM_SIGFPE).` but NO actual FATAL/exception markers should NOT fire A1.

9. **test_a3_per_field_threshold_impinging_jet_p_rgh**: write a synthetic log with final `DILUPBiCGStab:  Solving for p_rgh, Initial residual = 6e-3, Final residual = 1e-5, No Iterations 2`. Call `_check_a3_residual_floor(log, thresholds=load_thresholds("impinging_jet"))`. Assert verdict==HAZARD (6e-3 > 5e-3 per-case threshold). Verify the default (not impinging_jet) would be FAIL/HAZARD at 6e-3 > 1e-3 — but for this test we want to prove the per-case override is applied.

10. **test_a6_decade_range_exactly_1_fires_fail** (CA-006 guard): synthetic residual timeline with initial residual oscillating between 1.0 and 10.0 for 50 iters (exactly 1 decade). With default `no_progress_decade_frac==1.0`, verdict should be FAIL (`<=` not `<`). Previously `< 1.0` would have been PASS at exactly 1.0.

11. **test_a4_gap_blocks_reset_consecutive** (CA-007 guard): synthetic log with 4 time-step blocks: block 1 pressure cap (No Iterations 1000), block 2 no pressure solve (gap), block 3 pressure cap, block 4 pressure cap. Max consecutive capped = 2 (blocks 3-4). Assert A4 verdict==PASS.

12. **test_a4_three_consecutive_caps_fail**: 3 back-to-back capped blocks with no gaps. Assert A4 verdict==FAIL.

13. **test_attest_with_execution_result_failure**: `attest(log, execution_result=SimpleNamespace(success=False))` on an otherwise clean log. Assert `overall == "ATTEST_FAIL"` and A1 check in result.checks has verdict==FAIL.

### In `ui/backend/tests/test_comparator_gates_g3_g4_g5.py`

Add these tests. Import:
```python
from src.comparator_gates import read_final_velocity_max, check_all_gates
```

1. **test_read_final_velocity_max_skips_allPatches** (tmp_path): create fake VTK dir with `case_100.vtk` AND `allPatches/allPatches_100.vtk`. Both have pyvista-readable content with U data. Assert `read_final_velocity_max(dir)` returns max from case_100.vtk only.

   **NOTE**: creating synthetic pyvista-readable VTK files is non-trivial. Alternative: monkeypatch `pyvista.read` to return crafted meshes for specific paths. Use monkeypatch approach — it's more robust + faster.

2. **test_read_final_velocity_max_uses_latest_timestep** (tmp_path + monkeypatch): create 3 pseudo-files `case_100.vtk` (max |U|=999), `case_200.vtk` (max |U|=1.0), `case_500.vtk` (max |U|=2.0). Assert returns 2.0 (latest by timestep, NOT alphabetic).

3. **test_read_final_velocity_max_allPatches_only_returns_none** (tmp_path): VTK dir contains only `allPatches/*.vtk`, no internal. Assert returns None.

4. **test_read_final_velocity_max_numeric_vs_alphabetic_sort** (tmp_path + monkeypatch): create `case_10.vtk`, `case_100.vtk`, `case_2.vtk`. Alphabetic sort would pick `case_2.vtk` last (highest). Numeric should pick `case_100.vtk`. Assert returns the |U| value from case_100.vtk.

5. **test_read_final_velocity_max_no_timestep_suffix_skipped** (tmp_path): file `bare_case.vtk` (no trailing `_<int>.vtk`). Should be skipped. If no other files match → returns None.

6. **test_g3_boundary_99_U_ref_passes** (monkeypatch VTK reader): `check_all_gates(log, vtk_dir, U_ref=1.0)` where read_final_velocity_max returns 99.0 (just under K*U_ref=100). Assert no G3 violation.

7. **test_g3_boundary_101_U_ref_fails** (monkeypatch VTK reader): same setup with read returning 101.0. Assert G3 violation fires.

8. **test_g3_U_ref_none_behavior**: current code uses `U_ref=1.0` default when caller doesn't pass one. Document this in a test: call with `U_ref=1.0` (explicit) vs the default case. This is less a test of new behavior, more a pin-the-spec regression guard per DEC-036b S1 concern. If U_ref plumbing is Wave 2, skip this test with reason "Wave 2 scope".

## Implementation notes

- `monkeypatch.setattr("pyvista.read", fake_read)` where `fake_read(path_str)` returns a dict-like object with `.point_data` / `.cell_data` attributes containing numpy arrays. Use simple mock class.
- For synthetic logs: use the existing `_write_log` helper in test file (there's likely one; if not, create local helper).
- Tests should be fast: no real VTK I/O, no pyvista actual reads.
- Keep each test < 40 lines.

## Acceptance Checks

CHK-1: All 13 convergence_attestor tests + 8 comparator_gates tests PASS when run with `pytest ui/backend/tests/test_convergence_attestor.py ui/backend/tests/test_comparator_gates_g3_g4_g5.py -q`.

CHK-2: No existing tests fail. If an existing test breaks due to API change (attest() signature, threshold constants), minimal fix only — document each touched line in the output report.

CHK-3: No new pytest fixtures introduced at conftest.py level (keep fixtures local to test file).

## Reject Conditions

REJ-1: Edits outside `allowed_files`.
REJ-2: Refactoring or reformatting existing tests beyond minimum-necessary API updates.
REJ-3: Adding dependencies not currently in pyproject.toml.
REJ-4: Running actual pytest (that's Claude's verification step, not Codex's).
REJ-5: Deleting any existing test.

## Output format

```
# Codex Diff Report — DEC-V61-045 Wave 1 C

## Files modified
- ui/backend/tests/test_convergence_attestor.py [+N/-M]
- ui/backend/tests/test_comparator_gates_g3_g4_g5.py [+N/-M]

## Tests added (per file)
- Per-test one-line description + the CHK it covers

## Existing tests touched (if any)
- file:line — what changed + why (API shift requiring signature update)

## Self-verified checks
- CHK-1..3 PASS/FAIL evidence

## Tokens used
```

---

[/CLAUDE → CODEX TOOL INVOCATION]
