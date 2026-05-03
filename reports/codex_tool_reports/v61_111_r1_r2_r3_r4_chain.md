# Codex Review Chain · DEC-V61-111

**DEC**: DEC-V61-111 — iter01 numerical setup fix · honor intent.json:solver.name routing + simpleFoam template + V61-106 Phase 1.3 unblock
**Risk-tier triggers** (per RETRO-V61-001): OpenFOAM solver fix + case_solve route changes >5 LOC + new geometry-class authoring path = mandatory Codex pre-merge review
**Backend**: 86gs · model gpt-5.4 (xhigh) · governance baseline

## Round-by-round summary

| Round | Commit | Verdict | Findings (P1 / P2 / P3) | Notes |
|------:|--------|---------|-------------------------:|-------|
| R1 | `4832a85` | CHANGES_REQUIRED | 2 P1 + 1 P2 | Foundational — both P1 are real regressions in the new path |
| R2 | `ddcff1f` | CHANGES_REQUIRED | 0 P1 + 2 P2 | No P1 → substantive content converging |
| R3 | `c38ff43` | CHANGES_REQUIRED | 0 P1 + 1 P2 | Single residual finding on the no-match boundary |
| R4 | `26183da` | **APPROVE** | 0 | "consistently aligns BC setup's override guard and reported solver_name with the existing /solve dispatch fallback" |

## R1 (commit 4832a85) findings + closure

### R1 P1-1: Stale solver-marker overrides on cross-solver reruns

> "When a case has a user-owned solver dict from the existing pimpleFoam path, this branch will still preserve that file and only run `_detect_icofoam_marker_overrides()`, which checks for `application icoFoam` only. A `solver_name='simpleFoam'` rerun can therefore leave `system/controlDict` or `system/fvSolution` on the old pimpleFoam template while authoring the other files as simpleFoam, producing an incoherent solver group..."

**Closure**: generalized `_detect_icofoam_marker_overrides` → `_detect_solver_marker_overrides(case_dir, *, ai_solver)`. Hardcoded the 3 known solver regexes; backward-compat shim retained for the legacy symbol. 2 new tests pin the cross-solver mismatch in both directions (AI-simpleFoam-vs-user-pimpleFoam, AI-pimpleFoam-vs-user-simpleFoam).

### R1 P1-2: simpleFoam residualControl early-exit misclassified as not-converged

> "`run_icofoam()` and the SSE path still call `_is_converged()`, which only returns true when `end_time_reached` is essentially the configured `endTime`, so any simpleFoam case that converges early will now be reported as `converged=false`..."

**Closure**: `_is_converged()` gains `application` + `log_text` kwargs. For `application=='simpleFoam'`, accept either `ran full iteration budget` OR `log contains "SIMPLE solution converged in N iterations"` (OpenFOAM-canonical message). `_PreparedStream` gains `application` field so the SSE path can pass the actual solver to the convergence check. Transient (icoFoam/pimpleFoam) gate unchanged. 1 new test covers happy-path early-exit + crash detection + transient backward compat.

### R1 P2-1: solver_name field can lie when controlDict skipped

> "`solver_name` is returned unconditionally from `resolved_solver`, but `_atomic_commit_dicts()` may skip `system/controlDict` because of the override-preservation contract..."

**Closure**: after the commit, if `system/controlDict` is in `skipped`, re-read the on-disk `application` and report THAT as `solver_name` (with a warning surfacing the divergence). 1 new test exercises the full-group override case.

## R2 (commit ddcff1f) findings + closure

### R2 P2-1: solver_name re-read parser disagreed with /solve dispatch parser

> "When `system/controlDict` is skipped because the engineer owns it, this new branch strips block comments before reading `application`. That makes the returned `solver_name` diverge from `read_application_from_control_dict()` in `solver_runner.py`, which still scans the raw file."

**Closure**: removed the comment-stripping pass. Both BC setup re-read and `_detect_solver_marker_overrides` now use the SAME `_APPLICATION_RE` (`^\s*application\s+(\w+)\s*;`) on raw text — identical to `read_application_from_control_dict` in solver_runner.py. 1 new parity test exercises the agreement contract. R2 also surfaced a latent V61-107.5 R17 P3 test bug (it pinned a comment-stripped behavior that solver_runner doesn't have); that test was rewritten to assert the parser-parity behavior.

### R2 P2-2: Override guard hardcoded to {icoFoam, pimpleFoam, simpleFoam}

> "If a user-overridden `system/controlDict` says some other solver such as `application pisoFoam;` while BC setup is authoring `pimpleFoam` or `simpleFoam`, the guard returns `[]`, the other two solver-group files are still AI-written for a different solver, and the next `/solve` aborts on the mixed dictionaries."

**Closure**: extracted application name with the same `_APPLICATION_RE` and rejected when it ≠ `ai_solver`. Generic over any solver name. 1 new test pins arbitrary-solver mismatch detection (`application pisoFoam;` vs AI pimpleFoam).

## R3 (commit c38ff43) findings + closure

### R3 P2-1: Parser-no-match path still diverged from /solve dispatch

> "If a user-owned `controlDict` keeps the live directive on the same line as an inline block comment, for example `/* old */ application simpleFoam;`, `_APPLICATION_RE.search(raw)` returns `None`. After this change `_detect_solver_marker_overrides()` treats that as safe, while `read_application_from_control_dict()` in the solve path falls back to `icoFoam`..."

**Closure**: aligned both the guard and the on-disk re-read with /solve's icoFoam fallback. `user_application = m.group(1) if m is not None else "icoFoam"`. 1 new test pins the parity at the no-match boundary (inline block-comment makes application unparseable, solver_runner falls back to icoFoam, AI authors pimpleFoam → guard fires partial-override).

## R4 (commit 26183da) verdict

**`APPROVE` clean.**

> "The change consistently aligns BC setup's override guard and reported `solver_name` with the existing `/solve` dispatch fallback when `system/controlDict` cannot be parsed. I did not find a discrete, introduced bug in the modified behavior."

## Self-pass-rate calibration

- DEC authoring estimate: **50%**
- Actual: 3 rounds CHANGES_REQUIRED (R1 → R2 → R3) before R4 APPROVE
- Calibration: estimate was reasonable for a multi-file backend route + new solver authoring path. Each round reduced the P-level (R1: 2 P1+1 P2 → R2: 0 P1+2 P2 → R3: 0 P1+1 P2 → R4: clean), indicating substantive content converged on a stable contract rather than chasing structural problems.

## Methodology lesson for next RETRO

V61-111 is the canonical example of "parser parity matters": three review rounds were spent finding cases where the BC setup's view of a controlDict diverged from `/solve` dispatch. The deeper lesson is that wherever two code paths read the SAME source-of-truth file (here: user-overridden controlDict → both the BC setup guard AND the dispatch dispatcher), they MUST share the parser. The V61-107.5 R17 P3 test was a latent bug masked by the legacy `_detect_icofoam_marker_overrides` having its own private comment-stripping that diverged from `read_application_from_control_dict` — the fact that the test passed for V61-107.5 obscured the real /solve-time defect.

Pattern to apply going forward: any feature that reads a config file the dispatcher also reads should import the dispatcher's reader function, not re-parse the file. V61-111 closure imports/mirrors solver_runner.py's `_APPLICATION_RE`; V61-102 Phase 3 (solver-profile YAML migration) should consolidate this into a single canonical parser used by all readers.

## Implementation commit chain

- `4832a85` — feat(case-solve): DEC-V61-111 — solver_name routing + simpleFoam template + iter01 reclassify
- `ddcff1f` — fix(case-solve): DEC-V61-111 — close Codex R1 (2 P1 + 1 P2)
- `c38ff43` — fix(case-solve): DEC-V61-111 — close Codex R2 (2 P2)
- `26183da` — fix(case-solve): DEC-V61-111 — close Codex R3 (1 P2)
- (closure commit follows: DEC status flip + V61-106 Phase 1.3 closure update + STATE anchor)

## Tests

- 53/53 V61-111-scope tests pass (`ui/backend/tests/test_bc_setup_from_stl_patches.py` + `ui/backend/tests/test_solver_streamer.py`)
- 850/854 full backend test suite pass (4 pre-existing baseline failures unrelated to V61-111: test_case_export 3-state markers, test_convergence_attestor BFS hazard-gate, 2× test_g1 missing-target-quantity)

## V61-106 Phase 1.3 status post-V61-111

Phase 1.3 (iter01 reclassification from `physics_validation_required` → `analytical_comparator_pass`) was the canonical follow-up V61-106 deferred to V61-111. iter01 intent.json now declares `expected_status: analytical_comparator_pass` with the V61-106 §Phase 1.3 prototype comparators (u_magnitude_max>=1.0, u_x_min<0.0, cell_count==7159) untouched. The smoke runner forwards `intent.json:solver.name=simpleFoam` to `/setup-bc?solver_name=simpleFoam`, the backend writes the V61-111 simpleFoam template, /solve dispatches simpleFoam.

**Live iter01 dogfood verification (Docker OpenFOAM container required) is the remaining acceptance §3 gate.** Codex review covers static correctness; live-run validates the runtime contract.
