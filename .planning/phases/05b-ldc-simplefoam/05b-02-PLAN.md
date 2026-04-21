---
phase: 05b-ldc-simplefoam
plan: 02
type: execute
wave: 2
depends_on:
  - "05b-01"
files_modified:
  - ui/backend/tests/fixtures/runs/lid_driven_cavity/audit_real_run_measurement.yaml
  - reports/phase5_audit/
autonomous: true
requirements:
  - LDC-FIXTURE-PASS
  - NO-REGRESSION-79
  - FRONTEND-TSC-CLEAN

must_haves:
  truths:
    - "Running scripts/phase5_audit_run.py lid_driven_cavity overwrites audit_real_run_measurement.yaml with comparator_passed: true"
    - "The regenerated fixture's run_metadata.expected_verdict is 'PASS'"
    - "Backend pytest suite reports 79/79 passed (no regression on teaching fixtures)"
    - "Frontend tsc --noEmit exits 0 (no regression)"
    - "HMAC-signed audit package endpoint returns measurement.comparator_verdict=PASS for audit_real_run"
  artifacts:
    - path: "ui/backend/tests/fixtures/runs/lid_driven_cavity/audit_real_run_measurement.yaml"
      provides: "Phase 5b real-solver audit fixture with PASS verdict"
      contains: "comparator_passed: true"
    - path: "reports/phase5_audit/"
      provides: "Raw solver run capture (JSON) timestamped per invocation"
      contains: "solver_success"
  key_links:
    - from: "scripts/phase5_audit_run.py"
      to: "src/foam_agent_adapter.py::_generate_lid_driven_cavity"
      via: "FoamAgentExecutor via TaskRunner.run_task"
      pattern: "FoamAgentExecutor\\(\\)"
    - from: "audit_real_run_measurement.yaml"
      to: "ui/backend/routes/audit_package.py::build_audit_package"
      via: "validation_report._load_run_measurement reads the fixture under run_id=audit_real_run"
      pattern: "audit_real_run"
---

<objective>
Regenerate the `audit_real_run_measurement.yaml` fixture for `lid_driven_cavity` by running the Phase 5a audit driver against the simpleFoam case generator produced by Plan 01. The new fixture MUST record `comparator_passed: true` and `expected_verdict: PASS`. Prove no regressions: backend pytest stays 79/79 green, frontend tsc --noEmit exits 0, and the HMAC-signed audit package route still returns a valid bundle now marked PASS.

Purpose: Plan 01 changed only the case generator. This plan closes the feedback loop — runs the solver, measures the result against Ghia 1982 (17 y-points, 5% tolerance), writes the canonical audit fixture, and verifies no existing test has been broken by the solver swap.

Output:
- Overwritten `ui/backend/tests/fixtures/runs/lid_driven_cavity/audit_real_run_measurement.yaml` with new commit_sha, new measurement values, and `comparator_passed: true`.
- New timestamped raw capture under `reports/phase5_audit/`.
- No source-code changes.

**Autonomous boundary (WARNING #6 resolution):** This plan is `autonomous: true`. There is no "return to orchestrator" semantics inside the plan body. On failure modes (comparator still FAIL, tests red, tsc red, docker down after restart), the task **exits non-zero with a diagnostic note logged to `/tmp/phase5b_ldc_run.log`**. gsd-execute-phase propagates the non-zero exit as a plan FAIL, and the orchestrator (outside this plan) handles re-dispatch of Plan 01 with revision context. Do NOT attempt any orchestrator-level control flow from within these tasks.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/05b-ldc-simplefoam/05b-CONTEXT.md
@.planning/phases/05b-ldc-simplefoam/05b-RESEARCH.md
@.planning/phases/05b-ldc-simplefoam/05b-01-PLAN.md
@CLAUDE.md

<interfaces>
Phase 5a driver — `scripts/phase5_audit_run.py`:
```
Usage:
  EXECUTOR_MODE=foam_agent .venv/bin/python scripts/phase5_audit_run.py lid_driven_cavity

Writes:
  ui/backend/tests/fixtures/runs/lid_driven_cavity/audit_real_run_measurement.yaml
  reports/phase5_audit/{YYYYMMDDTHHMMSSZ}_lid_driven_cavity_raw.json

Exit code:
  0 if ALL specified cases ran without exception
  1 if any case raised
  2 if EXECUTOR_MODE not set or no cases given
  (Note: exit 0 does NOT imply comparator PASS — only that solver ran.
   Comparator verdict is in the fixture YAML's expected_verdict field
   and in measurement.comparator_passed.)
```

Current fixture state (pre-Plan-01, baseline — this is what gets overwritten):
```yaml
# See ui/backend/tests/fixtures/runs/lid_driven_cavity/audit_real_run_measurement.yaml
# run_metadata.expected_verdict: FAIL
# measurement.comparator_passed: false
# 5 deviations at y=0.0625, 0.1250, 0.5000, 0.7500, 1.0000
```

Schema contract — `ui/backend/tests/test_phase5_byte_repro.py`:
The regenerated fixture MUST still satisfy these keys (mandatory):
- run_metadata.run_id == "audit_real_run"
- run_metadata.category == "audit_real_run"
- measurement.{value, unit, run_id, commit_sha, measured_at, quantity, extraction_source, solver_success, comparator_passed}
- decisions_trail is a non-empty list

Docker requirement:
```
The FoamAgentExecutor runs openfoam via the `cfd-openfoam` Docker container.
Container must be up. To check:
  docker ps --filter name=cfd-openfoam --format '{{.Names}}\t{{.Status}}'
If not running, start:
  docker start cfd-openfoam
```

Allowed wall-time budget per case invocation: ≤ 5 minutes (CONTEXT.md estimates 30-90 s; give generous headroom).
</interfaces>
</context>

<tasks>

<task type="auto" tdd="false">
  <name>Task 1: Regenerate audit_real_run fixture via phase5_audit_run.py</name>
  <files>
    ui/backend/tests/fixtures/runs/lid_driven_cavity/audit_real_run_measurement.yaml
    reports/phase5_audit/*.json
  </files>
  <read_first>
    - scripts/phase5_audit_run.py (driver that will be invoked)
    - ui/backend/tests/fixtures/runs/lid_driven_cavity/audit_real_run_measurement.yaml (current baseline showing what gets overwritten — FAIL with 5 deviations)
    - .planning/phases/05b-ldc-simplefoam/05b-RESEARCH.md section `## Expected wall time and iteration count`
  </read_first>
  <action>
    All diagnostics/errors append to `/tmp/phase5b_ldc_run.log`. On any unrecoverable failure, `exit 2` (plan-level FAIL signal propagated upward).

    Step 1 — Verify Plan 01 landed in `src/foam_agent_adapter.py`:
    ```
    cd /Users/Zhuanz/Desktop/cfd-harness-unified
    grep -q 'application     simpleFoam' src/foam_agent_adapter.py \
      && echo "OK Plan 01 landed" \
      || { echo "FAIL Plan 01 not landed (simpleFoam missing)" | tee -a /tmp/phase5b_ldc_run.log; exit 2; }
    grep -q '(129 129 1)' src/foam_agent_adapter.py \
      && echo "OK 129 mesh" \
      || { echo "FAIL 129 mesh absent" | tee -a /tmp/phase5b_ldc_run.log; exit 2; }
    ```
    If either check fails, abort with non-zero exit — plan FAIL propagates to gsd-execute-phase.

    Step 2 — Verify Docker container (WARNING #5 fix — explicit re-check after restart):
    ```
    if docker ps --filter name=cfd-openfoam --filter status=running -q | grep -q .; then
      echo "OK docker up"
    else
      echo "docker down, attempting restart" | tee -a /tmp/phase5b_ldc_run.log
      docker start cfd-openfoam && sleep 2
      # Mandatory re-check after restart — do NOT assume docker start worked:
      docker ps --filter name=cfd-openfoam --filter status=running -q | grep -q . \
        || { echo "FAIL: docker still down after restart" | tee -a /tmp/phase5b_ldc_run.log; exit 2; }
      echo "OK docker restarted"
    fi
    ```

    Step 3 — Run the audit driver:
    ```
    cd /Users/Zhuanz/Desktop/cfd-harness-unified
    EXECUTOR_MODE=foam_agent .venv/bin/python scripts/phase5_audit_run.py lid_driven_cavity 2>&1 | tee -a /tmp/phase5b_ldc_run.log
    ```
    Wall-time budget: up to 5 minutes. If it hangs past 5 min, investigate before aborting — could be Docker starvation, not a real issue. On driver failure (exit != 0), log to `/tmp/phase5b_ldc_run.log` and exit non-zero.

    Step 4 — Inspect outputs:
    ```
    cat ui/backend/tests/fixtures/runs/lid_driven_cavity/audit_real_run_measurement.yaml
    ls -t reports/phase5_audit/*lid_driven_cavity* | head -1
    ```

    Step 5 — If `comparator_passed: true` and `expected_verdict: PASS` (verified via the python yaml.safe_load block in `<verify>`): success. Commit this plan's artifacts in Plan 03. Do NOT commit here (Plan 03 handles git + Codex + DEC atomically).

    Step 6 — If the fixture STILL shows FAIL:
    - Log deviations and diagnostic info to `/tmp/phase5b_ldc_run.log`:
      ```
      echo "=== PLAN 02 FAILURE DIAG ===" >> /tmp/phase5b_ldc_run.log
      ls -t reports/phase5_audit/*lid_driven_cavity*.json | head -1 \
        | xargs -I{} python -c "import json,sys; d=json.load(open(sys.argv[1])); print(json.dumps(d.get('deviations', d), indent=2))" {} \
        >> /tmp/phase5b_ldc_run.log
      echo "recommendation: re-dispatch Plan 01 with divSchemes fallback (limitedLinearV 1 -> linearUpwind default) OR extend endTime 2000->5000 OR loosen URFs (U 0.9->0.7, p 0.3->0.2). See RESEARCH.md R1/R3." >> /tmp/phase5b_ldc_run.log
      ```
    - Exit non-zero (`exit 1`). gsd-execute-phase will mark this plan FAIL and the orchestrator handles re-dispatch with the log as revision context.
    - Do NOT attempt to hand-edit the fixture YAML to make it pass — the fixture is AUTO-GENERATED (header comment states this) and any hand-edit is a 三禁区 violation (fixture integrity).
    - Do NOT attempt to re-edit `src/foam_agent_adapter.py` from within this plan — that is Plan 01's territory.

    Step 7 — Sanity log (success path only):
    ```
    echo "=== PLAN 02 TASK 1 RESULT ==="
    grep -E 'expected_verdict|comparator_passed|value:|commit_sha' \
      ui/backend/tests/fixtures/runs/lid_driven_cavity/audit_real_run_measurement.yaml
    ```
  </action>
  <verify>
    <automated>cd /Users/Zhuanz/Desktop/cfd-harness-unified && .venv/bin/python -c "
import yaml, pathlib
p = pathlib.Path('ui/backend/tests/fixtures/runs/lid_driven_cavity/audit_real_run_measurement.yaml')
doc = yaml.safe_load(p.read_text())
assert doc['run_metadata']['run_id'] == 'audit_real_run', 'run_id wrong'
assert doc['run_metadata']['category'] == 'audit_real_run', 'category wrong'
assert doc['run_metadata']['expected_verdict'] == 'PASS', f'verdict is {doc[\"run_metadata\"][\"expected_verdict\"]}, want PASS'
m = doc['measurement']
assert m['comparator_passed'] is True, f'comparator_passed is {m[\"comparator_passed\"]}, want True'
assert m['solver_success'] is True, 'solver_success not True'
for k in ('value','unit','run_id','commit_sha','measured_at','quantity','extraction_source'):
    assert k in m, f'schema missing key {k}'
assert len(doc.get('decisions_trail', [])) >= 1, 'decisions_trail empty'
print('FIXTURE OK: verdict=PASS, comparator_passed=True, schema satisfied')
"
</automated>
  </verify>
  <acceptance_criteria>
    - File `ui/backend/tests/fixtures/runs/lid_driven_cavity/audit_real_run_measurement.yaml` exists with mtime > plan start time
    - At least one new file exists under `reports/phase5_audit/*lid_driven_cavity*.json` newer than plan start
    - **The automated verify block (python yaml.safe_load) exits 0 and prints `FIXTURE OK: verdict=PASS, comparator_passed=True, schema satisfied`.** This is the canonical PASS gate — the yaml.safe_load path is schema-tolerant (quoted/unquoted values, boolean vs string `true`), unlike brittle grep-on-raw-text.
    - Quote-tolerant grep backup check (BLOCKER #1 fix — tolerates both `expected_verdict: PASS` and `expected_verdict: "PASS"` / `'PASS'`): `grep -cE "expected_verdict:\s*['\"]?PASS['\"]?" ui/backend/tests/fixtures/runs/lid_driven_cavity/audit_real_run_measurement.yaml` returns 1
    - Quote-tolerant boolean grep (BLOCKER #1 fix): `grep -cE "comparator_passed:\s*['\"]?(true|True|yes)['\"]?" ui/backend/tests/fixtures/runs/lid_driven_cavity/audit_real_run_measurement.yaml` returns 1
    - (Note: the python yaml.safe_load block is authoritative. Grep criteria above are defensive secondary checks that tolerate yaml emitter variations. If yaml.safe_load passes but grep returns 0, still treat as PASS — emitter may have quoted the scalar.)
    - The phase5_audit_run.py invocation exited 0 (solver ran without exception)
  </acceptance_criteria>
  <done>
    The regenerated fixture records PASS against Ghia 1982 at 5% tolerance on all 17 y-points. Raw JSON capture exists for traceability.
  </done>
</task>

<task type="auto" tdd="false">
  <name>Task 2: Backend pytest 79/79 + frontend tsc --noEmit (regression guard)</name>
  <files></files>
  <read_first>
    - .planning/phases/05b-ldc-simplefoam/05b-RESEARCH.md section `### Dimension 5: No regression on teaching fixtures` and `### Dimension 6: Frontend tsc clean`
    - ui/backend/tests/test_phase5_byte_repro.py (to understand the schema contract that the new fixture must satisfy)
  </read_first>
  <action>
    Step 1 — Backend pytest:
    ```
    cd /Users/Zhuanz/Desktop/cfd-harness-unified
    .venv/bin/python -m pytest ui/backend/tests/ -v 2>&1 | tee /tmp/phase5b_pytest.log
    ```
    Expected: 79 passed. (Numbers from ROADMAP/CONTEXT: "Backend 79/79 pytest green".) If the test count drifts (say 80 or 78), investigate whether a new test was added in a merge or something changed since last baseline — the contract is "no NEW failures"; a test-count increase that is all-green is acceptable, surface in the SUMMARY.

    Step 2 — If any test fails:
    - If it's in `test_phase5_byte_repro.py` and the failure is `comparator_passed` mismatch or numeric drift → the fixture is now PASS-shaped but the byte-repro test hard-codes PASS/FAIL expectations. Re-read the test to confirm — per RESEARCH.md R4, the byte-repro test "checks schema, not exact values, so it's unaffected by numeric deltas". Therefore ANY test failure here means a schema violation in Task 1's fixture OR a genuine unrelated regression. Do NOT disable tests.
    - If it's in a teaching-fixture test (reference_pass / under_resolved / wrong_model / grid_convergence) → Plan 01 should NOT have touched anything consumed by those tests. Investigate — likely means Plan 01 accidentally mutated shared state.
    - Log the failure diff to `/tmp/phase5b_pytest.log` (already redirected above). Exit non-zero (`exit 1`). gsd-execute-phase propagates as plan FAIL. Do NOT hand-fix individual test expectations.

    Step 3 — Frontend tsc:
    ```
    cd /Users/Zhuanz/Desktop/cfd-harness-unified/ui/frontend
    npx tsc --noEmit 2>&1 | tee /tmp/phase5b_tsc.log
    ```
    Expected: exit 0, no output (or just the standard "version" line). On non-zero exit, log + propagate FAIL.

    Step 4 — Optional but recommended (smoke the signed audit package route):
    ```
    cd /Users/Zhuanz/Desktop/cfd-harness-unified
    .venv/bin/python -m pytest ui/backend/tests/test_audit_package_route.py::TestAuditRealRunWiring -v 2>&1 | tail -40
    ```
    This class specifically covers the LDC audit_real_run route. Should be within the 79 from Step 1 but running it in isolation is a faster signal if Step 1 fails.
  </action>
  <verify>
    <automated>cd /Users/Zhuanz/Desktop/cfd-harness-unified && .venv/bin/python -m pytest ui/backend/tests/ -q 2>&1 | tail -5 && cd ui/frontend && npx tsc --noEmit && echo "TSC OK"</automated>
  </verify>
  <acceptance_criteria>
    - Backend pytest last line matches pattern `79 passed` (OR `NN passed` where NN ≥ 79 and `0 failed`)
    - No test marked as `failed` in the pytest log
    - `npx tsc --noEmit` exits 0 and prints `TSC OK` (the echo in the verify block)
    - `TestAuditRealRunWiring` class in `test_audit_package_route.py` all green (typically 3-5 tests under that class)
  </acceptance_criteria>
  <done>
    Backend suite 79/79 (or ≥79/all-green). Frontend typecheck clean. The fixture regeneration introduced zero regressions in either surface.
  </done>
</task>

</tasks>

<verification>
1. The fixture at `ui/backend/tests/fixtures/runs/lid_driven_cavity/audit_real_run_measurement.yaml` has `comparator_passed: true` and `expected_verdict: PASS` (verified via yaml.safe_load, not brittle grep).
2. `reports/phase5_audit/` has a fresh raw JSON capture for this run.
3. `.venv/bin/python -m pytest ui/backend/tests/` exits 0 with ≥79 passed, 0 failed.
4. `cd ui/frontend && npx tsc --noEmit` exits 0.
5. `TestAuditRealRunWiring` class is green inside the full backend run (confirmation of end-to-end pipeline: fixture → route → signed package).
6. On any failure, diagnostics are in `/tmp/phase5b_ldc_run.log` and/or `/tmp/phase5b_pytest.log` / `/tmp/phase5b_tsc.log`; plan exits non-zero so gsd-execute-phase registers FAIL.
</verification>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| test-fixture → production audit-package route | Fixture values flow into HMAC-signed audit bundles — any tampering materially affects the integrity claim of the audit package surface. Test fixtures are committed to git and reviewed, so supply-chain attack surface is the dev's workstation, not runtime. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-05b-04 | Tampering | Hand-edit of `audit_real_run_measurement.yaml` to force PASS | mitigate | Fixture has a mandatory header comment "AUTO-GENERATED, DO NOT HAND-EDIT". Plan forbids hand-edit explicitly. Regeneration via `phase5_audit_run.py` is the only sanctioned path; raw JSON capture in `reports/phase5_audit/` provides a secondary traceable artifact. Plan 03 will include the raw capture in the commit. |
| T-05b-05 | Information Disclosure | Raw solver capture `reports/phase5_audit/*.json` could leak absolute paths | accept | The JSON contains case_id, duration, numeric quantities, deviations — no credentials or host secrets. Pattern already in use since Phase 5a. |
| T-05b-06 | Repudiation | Cannot prove which commit produced the PASS verdict | mitigate | `measurement.commit_sha` field embeds the git HEAD at run-time via `_git_head_sha()` in the driver. Plan 03 ensures the commit that ships the fixture = the commit referenced by commit_sha. |
</threat_model>

<success_criteria>
1. Fixture regenerated and shows PASS.
2. Backend 79/79 green (or ≥79 all green).
3. Frontend tsc clean.
4. No source-code changes made in this plan (src/, ui/, scripts/ untouched by this plan).
5. Raw JSON capture present under reports/phase5_audit/.
6. On failure, non-zero exit propagated; diagnostic logs in `/tmp/`.
</success_criteria>

<output>
After completion, create `.planning/phases/05b-ldc-simplefoam/05b-02-SUMMARY.md` with:
- The new fixture's measurement.value, commit_sha, measured_at
- Pytest result summary (X passed / Y failed)
- Frontend tsc result (clean / errors)
- Path to the raw JSON capture file
- Any deviations observed even under PASS verdict (diagnostic, not blocking)
- Recommendation: proceed to Plan 03 (Codex + commit + DEC)
</output>
</content>
</invoke>