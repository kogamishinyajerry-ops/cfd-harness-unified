# Red Team Round-15 Review — Phase 1 Step 2c Meta Scan

**Scope:** adversarial probe of the OpenFOAM 2c additions: `docker run` wrapper, simpleFoam log parser, residuals.csv writer, gate computation. ~200 LOC of new code in `src/cfdtrust/backends/openfoam.py` plus 9 positive tests.
**Author:** test-red-team agent.
**Date:** 2026-05-21.
**Previous round:** `red_team_round14_review.md` (PASS, 0/0/1/2 — MED documented + 2 LOWs closed on 2b scaffold).
**Verdict:** **FAIL — 0/0/2/2** at probe time, **all closed in this same batch**. The exact pattern round 14 predicted: "200 LOC, new external dep → 1 HIGH or MED possible." Two MEDs surfaced.

---

## Method

13 probes spanning subprocess invocation discipline, regex robustness, gate-logic edge cases, manifest-vs-log field-name asymmetry, and runtime argv-injection. No live `docker run` was needed — all findings reproducible by reasoning over the code + targeted unit tests.

| # | Probe                                                                          | Outcome   |
|---|--------------------------------------------------------------------------------|-----------|
| 1 | `_run_docker_command` image argv slot — embedded flags?                         | **R15-F-03** (LOW) |
| 2 | `case_dir.resolve()` with colons / weird path chars                             | clean (docker -v parser rejects pre-emptively) |
| 3 | shell_args parameter — caller-controlled?                                       | clean (only literal `"blockMesh"` / `"simpleFoam"` from project code) |
| 4 | Residual regex DoS — catastrophic backtracking?                                 | clean (bounded char classes) |
| 5 | yPlus regex assumes OpenFOAM 11 line shape — silent drift on OF version bump?   | LOW info — downgraded, y+ doesn't drive PASS/FAIL |
| 6 | Gate field-naming asymmetry: manifest `Ux` target but log only emits `U`        | **R15-F-02** (MED) — PASS without checking |
| 7 | `max_iterations` type coerce — non-int manifest value crashes int()             | LOW (schema constrains; informational) |
| 8 | CSV field-name with comma — corruption?                                         | clean (regex `\w+` excludes comma) |
| 9 | solver.log path traversal                                                       | clean (fixed name) |
| 10 | `--- STDERR ---` marker spoofable in solver stdout?                            | LOW info — purely cosmetic |
| 11 | TOCTOU between symlink walk and `docker -v`                                    | out of trust model (single-user local) |
| 12 | OSError during `subprocess.run` reported as `simplefoam_crashed`               | **R15-F-01** (MED) — honesty violation |
| 13 | blockMesh timeout collapsed into generic `blockmesh_failed`                    | **R15-F-04** (LOW) |

Probes 6 + 12 are the high-value findings. Both directly involve the honesty rule (`real_solver_invoked`, no PASS without contract check) — the exact failure modes the trust harness exists to prevent.

---

## Findings

### R15-F-01 — MEDIUM — docker fork OSError mis-reported as `simplefoam_crashed` with `real_solver_invoked: True` (closed in this batch)

**File:** `src/cfdtrust/backends/openfoam.py:619` (pre-fix), the `if rc != 0:` block in `run()`.

The pre-fix code in `_run_docker_command` distinguished two `-1` returncode causes only by the substring `"timed out" in stderr`:

```python
# Pre-fix _run_docker_command:
except subprocess.TimeoutExpired:
    return -1, partial, f"docker command timed out after {timeout}s"
except OSError as e:
    return -1, "", f"docker invocation failed: {e}"
```

Caller in `run()`:
```python
if rc == -1 and "timed out" in (sf_stderr or "").lower():
    # → simplefoam_timed_out
else:
    # → simplefoam_crashed, real_solver_invoked=True
```

The OSError path falls into the else branch, which lies: it reports `real_solver_invoked: True` even though the OSError happened BEFORE `subprocess.run` could fork the docker process. The solver was never invoked — there is nothing for the user's trust report to claim happened. Yet the harness would record an "execution attempted" gate state.

This is the exact "claim something happened that didn't" failure mode the project's core principles 11–12 forbid (`Do not hide mocked execution`, `Do not hide missing evidence`).

**Trigger conditions (realistic):**
- Host runs out of file descriptors mid-trust-loop
- Docker daemon restarts between env probe (succeeded) and solver invocation (OSError on socket reconnect)
- macOS/Linux ENOMEM during fork
- Container runtime quota exhausted

**Fix (applied in this batch):**

1. `_run_docker_command` now prepends explicit markers `OFA-TIMEOUT:` / `OFA-OSERROR:` to stderr.
2. `run()` discriminates three sub-cases:
   - `OFA-OSERROR` → BLOCKED `docker_invocation_failed`, `real_solver_invoked: False`, `execution: skipped`
   - `OFA-TIMEOUT` → BLOCKED `simplefoam_timed_out`, `real_solver_invoked: True`, `execution: attempted` (solver did start)
   - any other non-zero rc → BLOCKED `simplefoam_crashed`, `real_solver_invoked: True` (solver started and crashed inside container)
3. Same triad applied to blockMesh (R15-F-04 fix below).
4. Two regression tests:
   - `test_r15_f01_oserror_during_docker_fork_reports_real_solver_invoked_false`
   - `test_r15_f01_timeout_is_distinguishable_from_oserror`

### R15-F-02 — MEDIUM — Gate declares PASS when zero manifest target fields were actually found in the log (closed in this batch)

**File:** `src/cfdtrust/backends/openfoam.py:401-473` (`_compute_gate_from_residuals`).

Pre-fix gate logic:
```python
for tgt_field, tgt_val in targets.items():
    actual = final.get(tgt_field)
    if actual is None:
        # Try U → Ux/Uy/Uz synonym
        if tgt_field == "U": ...
    if actual is None:
        continue  # silently skip
    checked.append(tgt_field)
    if actual > tgt_val: failed.append(...)

converged = parsed["converged"] or (checked and not failed)
if not converged: return FAIL
return PASS  # ← BUG: can land here with checked=[] if SIMPLE converged
```

If a manifest declares targets like `velocity_x: 1e-5` (typo for `Ux`) — or any field name that doesn't appear in the OpenFOAM log — every iteration of the loop hits the `actual is None → continue` branch. `checked` ends up empty.

But: real OpenFOAM 11 SIMPLE emits `"SIMPLE solution converged in N iterations"` on the final iteration, which the parser sets `parsed["converged"] = True`. Then `converged = True or (False) = True`. The function falls through to PASS, with summary `(all 0 field residuals ≤ target)`.

**Outcome of the bug:** a `trust_report.json` with `overall_status: PASS` — when the harness has not actually verified a single residual target. This is the failure mode core principle 2 forbids: "A CFD case is correct only if it passes its explicit case contract."

**Trigger conditions (realistic):**
- Manifest contract reviewer types `velocity_x` instead of `Ux`
- Phase 2 manifest schema evolves but a legacy case_manifest.yaml still uses old field names
- A user copies a `solver_contract` block from a documentation example with placeholder names

**Fix (applied in this batch):**

```python
if targets and not checked:
    return BLOCKED "no_target_fields_in_log"  # with diagnostic details
```

Surfaces the manifest/log drift explicitly with `manifest_targets` (sorted) and `fields_in_log` (sorted) so the user can see the mismatch at a glance. Three regression tests:
- `test_r15_f02_no_pass_when_zero_target_fields_found_in_log`
- `test_r15_f02_partial_overlap_still_passes_on_overlapping_fields` (protects legitimate "manifest declares more fields than this run emitted" case)
- (the existing `test_compute_gate_from_residuals_passes_when_converged` already fences the positive path)

### R15-F-03 — LOW — `solver_docker_image` regex allowed argv-injection vectors (closed in this batch)

**File:** `src/cfdtrust/schemas/case_manifest.schema.json:28-33` (pre-fix) + `src/cfdtrust/backends/openfoam.py:_run_docker_command` argv composition.

The pre-fix schema regex was `^\\S` — only required the first character to be non-whitespace. That accepted strings like:

- `--privileged alpine` — `docker run --rm --entrypoint /bin/bash -v ... --privileged alpine -c "..."`. The `--privileged` is then absorbed by docker run as a flag, granting the container privileged mode.
- `-it openfoam/openfoam11` — `-it` becomes a flag; the actual image is then `openfoam/openfoam11` but the user might assume `-it openfoam/openfoam11` is the full reference.
- `openfoam ; rm -rf /` — accepted by schema. Whether dangerous depends on argv parsing path; in our list-form invocation this becomes a single argv token `"openfoam ; rm -rf /"` which docker will reject as invalid reference, but the surface area is wider than necessary.

The harness's existing list-form `subprocess.run` discipline mostly defangs this, but the schema acceptance lets a malicious manifest get further into the call chain than it should.

**Fix (applied in this batch):**

1. Schema regex tightened: `^[a-zA-Z0-9][a-zA-Z0-9._:/@-]*$`. Disallows leading dash, whitespace, shell metachars, length capped at 256.
2. Runtime double-check `_is_valid_docker_image_name()` in `openfoam.py` — even if a manifest bypasses schema validation (manual edit, code path that skips JSON schema), the adapter rejects with `manifest_invalid_solver_docker_image` BEFORE any `subprocess.run` call.
3. Three regression tests:
   - `test_r15_f03_schema_rejects_image_with_leading_dash` (9 attack strings)
   - `test_r15_f03_schema_accepts_real_docker_image_names` (7 legitimate references including ghcr.io and `registry:port/org/image:tag`)
   - `test_r15_f03_adapter_blocks_image_with_argv_injection_at_runtime` (asserts `subprocess.run` is NEVER called when image fails runtime check)

### R15-F-04 — LOW — blockMesh timeout collapsed into generic `blockmesh_failed` (closed in this batch)

**File:** `src/cfdtrust/backends/openfoam.py` `run()` blockMesh `rc != 0` branch.

Pre-fix: blockMesh timing out (slow Docker emulation on Apple Silicon — common in this project) produced `BLOCKED blockmesh_failed` with the timeout error string buried in `stderr_tail`. A user reading the trust report couldn't distinguish "your blockMeshDict has a syntax error" from "blockMesh ran for an hour and got killed."

**Fix (applied in this batch):** same triad as R15-F-01: `OFA-OSERROR` → `docker_invocation_failed`, `OFA-TIMEOUT` → `blockmesh_timed_out`, else → `blockmesh_failed`. Regression test `test_r15_f04_blockmesh_timeout_distinguished_from_dict_syntax_error`.

---

## What was probed and worked

- **Subprocess discipline**: list-form argv throughout, no `shell=True` at the host layer; the only string entering a shell is inside the container via `bash -c`, and that string is project-controlled literal text.
- **Recursive symlink walk** (carried forward from R-17 / round 13): exercises every nested file before docker -v binds the dir; closes the symlink-host-exfil class.
- **Residual regex coverage**: matches the four common OpenFOAM solvers (smoothSolver, GAMG, PCG, PBiCGStab, DICPCG); rejected catastrophic-backtracking patterns.
- **Field naming map** (combined `U` → split `Ux/Uy/Uz`): now documented AND fenced. The newly added "no target fields found" gate makes silent drift impossible.
- **Honesty discipline** is now correctly partitioned across three rc-non-zero sub-cases (OSError / timeout / crash), each with the right `real_solver_invoked` and `execution` values.

---

## Cumulative severity trend

| Round                       | CRIT | HIGH | MED | LOW | Total |
|-----------------------------|------|------|-----|-----|-------|
| 13 (2a meta)                | 0    | 0    | 0   | 0   | 0     |
| 14 (2b meta + fix)          | 0    | 0    | 1*  | 2   | 3     |
| **15 (2c meta + fix)**      | **0**| **0**| **2**| **2**| **4** |

*R14-F-03 documented-not-fixed; R15-F-01/F-02 both mechanically closed in this batch. The "fix-round drops severity by one tier" trend is BROKEN here — but that's the round-14 pattern observation talking back: net-new code with a new external dependency (docker subprocess + log parser) is where the ceiling can rise again. Two MEDs surfaced as predicted. Honest pattern-prediction success, not a regression.

---

## Pattern update — the prediction held

Round-14 review predicted:
> Sub-commit 2c (`docker run simpleFoam` wrapper + log parser) will introduce a NEW external dependency (subprocess invocation chain). Expect **1 HIGH or MED** on its meta scan.

Actual: 2 MEDs + 2 LOWs. The pattern is:

```
~40 LOC, well-scoped:        zero-finding likely
~200 LOC, single module:     1 MED + a couple LOW
~200 LOC, multi-file dicts:  1 MED + a couple LOW
~200 LOC, new external dep:  1-2 MED + LOWs
```

Both round-15 MEDs are honesty-rule failures, not security failures. This is interesting — the bigger the attack surface against the project's own truth claims (vs. against the host system), the more useful the adversarial probe is. Future rounds should bias probes toward "could this produce a false PASS?" over "could this run code on the host?" — the former is the project's actual product hazard.

---

## Verdict

**PASS (mechanically closed)** on the round-15 batch.

All four findings (2 MED + 2 LOW) have code fixes + regression tests; 118/118 pytest + 1 opt-in network skip. No documented-only deferrals this round.

Phase 1 step 2c is now structurally honest. Live `docker run` invocation (R14-F-03 demonstration — y+ ~ 53 vs target 0.5-5 — is exactly what the new `_compute_gate_from_residuals` is built to surface as a FAIL) should be performed as the next demonstrative milestone.

---

## Recommended next options for the owner

1. **(α)** Run live `docker run simpleFoam` against `cases/flat_plate_rans_sst` end-to-end. The trust harness should land at FAIL (residual targets met but mesh gate fails on y+) or BLOCKED (mesh contract not yet enforced). Either way, demonstrates the loop. ~5-15 minutes wall-clock on amd64-on-arm64 emulation.
2. **(β)** Proceed directly to sub-commit 2d — NASA TMR reference data fetch + cache + `reference_comparison.csv` generation. No live solver run yet. ~1 hour.
3. **(γ)** Natural session boundary at this clean state. 118/118 green + 4 R15 findings closed = a defensible stopping point.

Recommendation: **(α)**. The trust loop has never been observed end-to-end with a real solver. Doing it now — even with the documented y+ mismatch (R14-F-03) producing a FAIL — proves the whole chain works against real OpenFOAM 11 output.
