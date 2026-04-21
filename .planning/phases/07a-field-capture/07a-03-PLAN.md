---
phase: 07a-field-capture
plan: 03
type: execute
wave: 3
depends_on: [07a-01, 07a-02]
files_modified:
  - .planning/decisions/2026-04-21_phase7a_field_capture.md
  - .planning/STATE.md
  - .planning/ROADMAP.md
autonomous: false
requirements: [DEC-V61-031]
user_setup: []

must_haves:
  truths:
    - "Integration run `EXECUTOR_MODE=foam_agent .venv/bin/python scripts/phase5_audit_run.py lid_driven_cavity` produces `reports/phase5_fields/lid_driven_cavity/{YYYYMMDDTHHMMSSZ}/` with ≥3 files + `runs/audit_real_run.json` manifest"
    - "`GET /api/runs/lid_driven_cavity__audit_real_run/field-artifacts` on a running backend returns HTTP 200 with JSON containing ≥3 artifacts with valid SHA256"
    - "Codex review (`/codex-gpt54`) on Wave 1 + Wave 2 diff returns APPROVED or APPROVED_WITH_COMMENTS (no CHANGES_REQUIRED)"
    - "DEC-V61-031 drafted in `.planning/decisions/2026-04-21_phase7a_field_capture.md` with `notion_sync_status` updated after sync"
    - "STATE.md + ROADMAP.md Phase 7a section marked Status: COMPLETE"
    - "One atomic git commit containing all Wave 1+2+3 changes with DEC-V61-031 in message body"
    - "Backend pytest 79+ → ≥89 green (no regressions from the combined diff)"
  artifacts:
    - path: ".planning/decisions/2026-04-21_phase7a_field_capture.md"
      provides: "DEC-V61-031 decision record — Phase 7a field post-processing capture"
      contains: "DEC-V61-031"
    - path: "reports/phase5_fields/lid_driven_cavity/runs/audit_real_run.json"
      provides: "Per-run manifest resolving audit_real_run → timestamp dir"
      contains: "timestamp"
    - path: "reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review.md"
      provides: "Codex review output (linked from DEC frontmatter)"
      contains: "APPROVED"
  key_links:
    - from: ".planning/decisions/2026-04-21_phase7a_field_capture.md (frontmatter)"
      to: "reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review.md"
      via: "codex_tool_report_path frontmatter key"
      pattern: "codex_tool_report_path"
    - from: "git HEAD commit message"
      to: "DEC-V61-031"
      via: "explicit reference"
      pattern: "DEC-V61-031"
---

<objective>
Close Phase 7a: prove the full pipeline works end-to-end against real OpenFOAM, obtain Codex sign-off on all src/ + ui/backend/ edits, author DEC-V61-031, sync to Notion, update STATE/ROADMAP, and land one atomic commit.

Purpose: Phase 7a's value is only realized when a real audit_real_run produces artifacts that the backend serves. Unit tests in Wave 2 prove the route works offline; this wave proves the whole stack works online. The 三禁区 #1 (src/) edits mandate Codex review per RETRO-V61-001 + CLAUDE.md's Codex-per-risky-PR baseline.

Output:
- Evidence that `EXECUTOR_MODE=foam_agent .venv/bin/python scripts/phase5_audit_run.py lid_driven_cavity` produces real artifacts + manifest
- Evidence that running backend returns ≥3 artifacts over HTTP for the real `run_id`
- Codex review report written to `reports/codex_tool_reports/` + verdict captured
- DEC-V61-031 authored + Notion-synced
- STATE.md + ROADMAP.md updated
- One atomic git commit
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/07a-field-capture/07a-CONTEXT.md
@.planning/phases/07a-field-capture/07a-RESEARCH.md
@.planning/decisions/2026-04-21_phase5b_ldc_simplefoam_migration.md
@.planning/decisions/2026-04-21_phase5b_q5_ldc_gold_closure.md

<interfaces>
<!-- Precedents for Wave 3 outputs. -->

DEC frontmatter (from existing DEC-V61-029 at .planning/decisions/2026-04-21_phase5b_ldc_simplefoam_migration.md):
```yaml
<!-- yaml-fence -->
id: DEC-V61-NNN
title: "Phase 7a — Field post-processing capture"
date: 2026-04-21
autonomous_governance: true   # New 7a is autonomous; Codex review is post-merge quality gate, not external gate
status: Adopted
participants: [MiniMax-2.7, Codex-GPT-5.4]
notion_sync_status: pending
codex_tool_report_path: reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review.md
external_gate_self_estimated_pass_rate: 0.75
<!-- yaml-fence -->
```

ROADMAP update target (current text lines 37-46):
```
### Phase 7a: Field post-processing capture (Sprint 1, ~2-3 days)
- Status: Planned       ← change to COMPLETE
```

STATE.md: find the active-phase section, update "Phase 7a" status line.

Atomic commit message style (per recent repo history, e.g. 59b9b92 / 4022842):
```
feat(phase-7a): field post-processing capture — VTK + sample + residuals on disk + backend route

Implements DEC-V61-031. src/foam_agent_adapter.py adds _emit_phase7a_function_objects helper
and _capture_field_artifacts executor method; scripts/phase5_audit_run.py threads a shared
timestamp and writes per-run manifest. Backend adds FieldArtifact Pydantic models,
services/field_artifacts.py with SHA256 caching, routes/field_artifacts.py following the
audit_package FileResponse precedent (not StaticFiles, per user ratification #1).

- 79 pytest → 89+ green (10 new tests)
- Codex review: APPROVED (see reports/codex_tool_reports/2026-04-21_phase7a_*)
- LDC integration: reports/phase5_fields/lid_driven_cavity/{ts}/ populated; GET returns 3 artifacts
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="false">
  <name>Task 1: Run end-to-end LDC integration + capture evidence</name>
  <files>
    reports/phase5_fields/lid_driven_cavity/{runtime_timestamp}/**
    reports/phase5_fields/lid_driven_cavity/runs/audit_real_run.json
    ui/backend/tests/fixtures/runs/lid_driven_cavity/audit_real_run_measurement.yaml  # REGENERATED by the driver
    .planning/phases/07a-field-capture/_integration_evidence.txt                      # NEW — evidence capture
  </files>
  <read_first>
    - scripts/phase5_audit_run.py (to understand the updated run_one path from Wave 1 Task 3)
    - .planning/phases/07a-field-capture/07a-RESEARCH.md (§4.2 S1+S2 integration signals)
    - ui/backend/tests/test_phase5_byte_repro.py (byte-repro must stay green AFTER regen)
  </read_first>
  <action>
**Step 1 — Pre-check Docker + venv:**
```bash
cd /Users/Zhuanz/Desktop/cfd-harness-unified
docker ps 2>&1 | head -3
.venv/bin/python --version
ls reports/ 2>&1  # confirm reports/ dir exists
```

**Step 2 — Clean slate (avoid stale artifacts confusing the verification):**
```bash
rm -rf reports/phase5_fields/lid_driven_cavity/ 2>&1 || true
```

**Step 3 — Run the end-to-end driver:**
```bash
cd /Users/Zhuanz/Desktop/cfd-harness-unified
EXECUTOR_MODE=foam_agent .venv/bin/python scripts/phase5_audit_run.py lid_driven_cavity 2>&1 | tee .planning/phases/07a-field-capture/_integration_evidence.txt
```

Expected: exits 0 in ~25-45 seconds. Prints `[audit] lid_driven_cavity → PASS · 22.4s · audit_real_run_measurement.yaml` (or FAIL verdict if comparator diverges — that's fine, verdict is orthogonal to 7a capture).

**Step 4 — Verify artifacts on disk:**
```bash
# List what we captured
find reports/phase5_fields/lid_driven_cavity/ -type f | sort | tee -a .planning/phases/07a-field-capture/_integration_evidence.txt

# Sanity-check the manifest
cat reports/phase5_fields/lid_driven_cavity/runs/audit_real_run.json | tee -a .planning/phases/07a-field-capture/_integration_evidence.txt

# Count kinds
echo "=== counts ===" >> .planning/phases/07a-field-capture/_integration_evidence.txt
find reports/phase5_fields/lid_driven_cavity/ -type f -name "*.vtk" | wc -l | xargs echo "vtk count:"  | tee -a .planning/phases/07a-field-capture/_integration_evidence.txt
find reports/phase5_fields/lid_driven_cavity/ -type f \( -name "*.xy" -o -name "*.csv" \) | wc -l | xargs echo "csv/xy count:" | tee -a .planning/phases/07a-field-capture/_integration_evidence.txt
```

Requirements:
- At least 1 `.vtk` file in `reports/phase5_fields/lid_driven_cavity/{ts}/VTK/`
- At least 1 `.xy` or `.csv` file under `postProcessing/sample/`
- `residuals.csv` at the root of the artifact dir (derived by `_emit_residuals_csv`)
- `log.simpleFoam` at the root of the artifact dir
- `reports/phase5_fields/lid_driven_cavity/runs/audit_real_run.json` exists, JSON is valid, `timestamp` key present

**Step 5 — Verify byte-repro test stays green after fixture regeneration:**
```bash
.venv/bin/pytest ui/backend/tests/test_phase5_byte_repro.py -v 2>&1 | tail -20 | tee -a .planning/phases/07a-field-capture/_integration_evidence.txt
```
All tests must pass.

**Step 6 — Launch backend + verify HTTP endpoint:**

Open a second terminal (or use `run_in_background`):
```bash
cd /Users/Zhuanz/Desktop/cfd-harness-unified
.venv/bin/uvicorn ui.backend.main:app --host 127.0.0.1 --port 8765
```

In the main terminal, probe the endpoint:
```bash
sleep 2
curl -sS http://127.0.0.1:8765/api/runs/lid_driven_cavity__audit_real_run/field-artifacts \
    | tee -a .planning/phases/07a-field-capture/_integration_evidence.txt

# Download one artifact to confirm the file endpoint
curl -sS -o /tmp/phase7a_residuals.csv \
    "http://127.0.0.1:8765/api/runs/lid_driven_cavity__audit_real_run/field-artifacts/residuals.csv"
head -5 /tmp/phase7a_residuals.csv | tee -a .planning/phases/07a-field-capture/_integration_evidence.txt

# Traversal guard check
curl -sS -o /dev/null -w "traversal_status=%{http_code}\n" \
    "http://127.0.0.1:8765/api/runs/lid_driven_cavity__audit_real_run/field-artifacts/..%2Fetc%2Fpasswd" \
    | tee -a .planning/phases/07a-field-capture/_integration_evidence.txt
```

Then stop the backend (Ctrl-C or `kill %1`).

Expected:
- Manifest endpoint returns JSON with `run_id`, `case_id`, `timestamp`, `artifacts` (≥3)
- Download returns a CSV starting with `#,Time,` or similar
- Traversal probe returns `traversal_status=404`

**Step 7 — If integration fails (any of S1-S7 from 07a-RESEARCH.md §4.2)**:
- Capture the failure in `_integration_evidence.txt`
- Do NOT proceed to Task 2 (Codex) — go back to Wave 1 or Wave 2 and revise
- Report back to the orchestrator via the task summary
  </action>
  <verify>
    <automated>test -f reports/phase5_fields/lid_driven_cavity/runs/audit_real_run.json && .venv/bin/python -c "
import json, pathlib
p = pathlib.Path('reports/phase5_fields/lid_driven_cavity/runs/audit_real_run.json')
d = json.loads(p.read_text())
assert d['run_label'] == 'audit_real_run'
assert d['case_id'] == 'lid_driven_cavity'
ts = d['timestamp']
assert len(ts) == 16 and ts.endswith('Z')
artifact_dir = pathlib.Path('reports/phase5_fields/lid_driven_cavity') / ts
files = list(artifact_dir.rglob('*'))
file_count = sum(1 for f in files if f.is_file())
assert file_count >= 3, f'only {file_count} files in {artifact_dir}'
vtks = list(artifact_dir.rglob('*.vtk'))
assert len(vtks) >= 1, 'no .vtk found'
print(f'OK: {file_count} files, {len(vtks)} vtk(s)')
"</automated>
  </verify>
  <acceptance_criteria>
    - `reports/phase5_fields/lid_driven_cavity/runs/audit_real_run.json` exists and is valid JSON
    - At least 1 `.vtk` file exists under `reports/phase5_fields/lid_driven_cavity/{ts}/`
    - At least 3 files total under `reports/phase5_fields/lid_driven_cavity/{ts}/`
    - `residuals.csv` exists at `reports/phase5_fields/lid_driven_cavity/{ts}/residuals.csv`
    - `log.simpleFoam` exists at `reports/phase5_fields/lid_driven_cavity/{ts}/log.simpleFoam`
    - `.venv/bin/pytest ui/backend/tests/test_phase5_byte_repro.py -v` exits 0
    - `curl http://127.0.0.1:8765/api/runs/lid_driven_cavity__audit_real_run/field-artifacts` returns JSON with `artifacts` array of length ≥3
    - `curl .../field-artifacts/residuals.csv` returns HTTP 200 with CSV content
    - `curl .../field-artifacts/..%2Fetc%2Fpasswd` returns HTTP 404
    - `.planning/phases/07a-field-capture/_integration_evidence.txt` exists and contains all evidence from steps 3-6
  </acceptance_criteria>
  <done>
Real OpenFOAM LDC run staged ≥3 artifacts to `reports/phase5_fields/lid_driven_cavity/{ts}/`. Backend route returns them as JSON over HTTP with valid SHA256. Traversal probe rejected. Byte-repro test stays green. All evidence captured in `_integration_evidence.txt` for Codex review context.
  </done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <name>Task 2: Codex review of Wave 1 + Wave 2 diff + capture review report</name>
  <what-built>
    Wave 1 edited `src/foam_agent_adapter.py` (~130 LOC: helper + executor method + residuals CSV emitter) and `scripts/phase5_audit_run.py` (~45 LOC: timestamp threading + manifest writer + YAML key). Wave 2 created 4 new backend files (`schemas/validation.py` extension, `services/run_ids.py`, `services/field_artifacts.py`, `routes/field_artifacts.py`) + 1 router registration in `main.py` + 1 test file with 10+ tests.

    Codex review is MANDATORY per:
    - RETRO-V61-001 trigger: `src/` 三禁区 #1 + >5 LOC
    - CLAUDE.md Codex-per-risky-PR baseline: "multi-file backend change" + "cross ≥3 files API schema" (new Pydantic model + route + service)
    - 07a-RESEARCH.md self-pass-rate 75% → post-merge Codex acceptable; ≤70% would be pre-merge (we are above threshold)
  </what-built>
  <how-to-verify>
    **The user (or MiniMax-2.7) MUST run Codex review via `/codex-gpt54`, NOT via Agent tool.**

    1. **Check Codex account quota before running:**
       ```bash
       cx-auto 20
       ```
       If any account < 20%, auto-switch to highest-score account.

    2. **Prepare review prompt and invoke Codex:**
       Create a temp prompt file or use inline. The review prompt should be:
       ```
       Review Phase 7a field-capture implementation. Three files are critical:

       1. src/foam_agent_adapter.py — new _emit_phase7a_function_objects helper,
          new _capture_field_artifacts method on FoamAgentExecutor, call-site
          wiring in execute()'s try-block. Check: (a) the call is BEFORE the
          finally-block teardown, (b) all exceptions are swallowed (best-effort),
          (c) no injection via task_spec.metadata values into shell commands,
          (d) no regression to _copy_postprocess_fields or other existing cases.

       2. scripts/phase5_audit_run.py — timestamp threading + manifest writer +
          field_artifacts YAML key injected after decisions_trail. Check: (a)
          byte-repro-safety (no timestamps in the YAML doc itself — they live
          in the runs/{run_label}.json manifest), (b) fallback when artifact
          dir doesn't materialize, (c) other-case compatibility.

       3. ui/backend/services/field_artifacts.py + routes/field_artifacts.py —
          file-serve pattern. Check: (a) traversal defense on {filename} and
          {run_id} parameters, (b) SHA256 caching correctness (no stale-hash
          on content change via same mtime+size), (c) FileResponse pattern
          matches audit_package.py:284-342, (d) MIME map is explicit (no
          StaticFiles guessing per user ratification #1).

       Identify any:
       - Security issues (priority: path traversal, command injection, MIME confusion)
       - Regression risk in the FoamAgentExecutor try-block
       - Byte-reproducibility violations in the audit YAML
       - Test gaps (are all 8 signals S1-S8 from 07a-RESEARCH.md §4.2 covered?)

       Reply APPROVED / APPROVED_WITH_COMMENTS / CHANGES_REQUIRED with numbered findings.
       ```

       Run:
       ```bash
       cx-auto 20 && codex exec "<prompt above>" 2>&1 | tee reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review.md
       ```

    3. **Read the Codex output file:**
       ```bash
       cat reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review.md
       ```

    4. **Based on verdict:**
       - **APPROVED** or **APPROVED_WITH_COMMENTS**: Proceed to Task 3.
       - **CHANGES_REQUIRED**: STOP. Record required changes in the DEC frontmatter as `codex_round_1_required_changes`. Apply minimum patches. Rerun Codex (round 2). Only when APPROVED do we proceed.

    5. **Report back:** Tell the user the verdict + brief summary of any comments.
  </how-to-verify>
  <files>
    reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review.md
  </files>
  <action>
Run the Codex review via `/codex-gpt54` or `cx-auto 20 && codex exec` per the prompt in <how-to-verify>. Capture the full output to `reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review.md`. Parse the verdict line (APPROVED / APPROVED_WITH_COMMENTS / CHANGES_REQUIRED). If CHANGES_REQUIRED, stop and return to Wave 1 or Wave 2 with the required-changes list.
  </action>
  <verify>
    <automated>test -s reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review.md && grep -E 'APPROVED|APPROVED_WITH_COMMENTS|CHANGES_REQUIRED' reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review.md</automated>
  </verify>
  <done>
Codex review report exists at `reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review.md`, contains a verdict line matching APPROVED / APPROVED_WITH_COMMENTS / CHANGES_REQUIRED, and the user has confirmed to proceed. If CHANGES_REQUIRED: loop back with fixes; do NOT proceed to Task 3.
  </done>
  <resume-signal>Paste the Codex verdict (APPROVED / APPROVED_WITH_COMMENTS / CHANGES_REQUIRED) and a one-line summary of findings, OR type "codex_approved_no_comments" if clean.</resume-signal>
</task>

<task type="auto" tdd="false">
  <name>Task 3: Author DEC-V61-031 + update STATE/ROADMAP + atomic git commit</name>
  <files>
    .planning/decisions/2026-04-21_phase7a_field_capture.md
    .planning/STATE.md
    .planning/ROADMAP.md
  </files>
  <read_first>
    - .planning/decisions/2026-04-21_phase5b_ldc_simplefoam_migration.md (format precedent — DEC-V61-029)
    - .planning/decisions/2026-04-21_phase5b_q5_ldc_gold_closure.md (format precedent — DEC-V61-030)
    - .planning/STATE.md (find the current Phase / active-phase block to update)
    - .planning/ROADMAP.md (lines 37-46 — Phase 7a section to mark COMPLETE)
    - reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review.md (linked from DEC frontmatter)
    - .planning/phases/07a-field-capture/_integration_evidence.txt (linked from DEC body)
  </read_first>
  <action>
**Step 1 — Write DEC-V61-031** at `.planning/decisions/2026-04-21_phase7a_field_capture.md`:

```markdown
<!-- yaml-fence -->
id: DEC-V61-031
title: "Phase 7a — Field post-processing capture (VTK + sample + residuals on disk + backend route)"
date: 2026-04-21
autonomous_governance: true
status: Adopted
participants: [MiniMax-2.7, Codex-GPT-5.4]
notion_sync_status: pending
codex_tool_report_path: reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review.md
external_gate_self_estimated_pass_rate: 0.75   # Research-declared; actual Codex verdict updates this field post-review.
linked_dec: [DEC-V61-028, DEC-V61-029, DEC-V61-030]
linked_retrospective: [RETRO-V61-001]
<!-- yaml-fence -->

# DEC-V61-031 — Phase 7a field post-processing capture

## Context

Phase 7's goal is scientific-grade CFD-vs-gold reporting. Phase 7a is Sprint 1 foundation:
capture the raw artifacts (VTK + sampled CSV + residuals) every `audit_real_run` produces,
so Phase 7b (rendering) and Phase 7c (comparison report) have stable inputs.

Before 7a, `FoamAgentExecutor` discarded the case dir in its `finally:` block
(src/foam_agent_adapter.py:618-623). Only scalar metrics survived, so
`/validation-report/*` had no full-field evidence to defend its verdicts.

## Decision

Three orthogonal changes:

1. **Solver-side.** `src/foam_agent_adapter.py::_generate_lid_driven_cavity` now emits
   a `controlDict.functions{}` block with `sample` + `residuals` function objects
   (yPlus stubbed for turbulent cases — inert on laminar LDC per 07a-CONTEXT).
   User ratification #2 changed the write-control from `runTime` to `timeStep`
   (steady simpleFoam has no runTime dimension). User ratification #3 uses the
   structured `residuals` function object output instead of log.simpleFoam regex.
   User ratification #4 fixed the sample coords to physical post-convertToMeters
   space (x=0.05 in 0.1-scaled mesh, not x=0.5).

2. **Runner-side.** New `FoamAgentExecutor._capture_field_artifacts` method is invoked
   inside the try-block, AFTER `_copy_postprocess_fields` and BEFORE `_parse_solver_log`,
   so artifacts are staged to host `reports/phase5_fields/{case_id}/{timestamp}/` BEFORE
   the finally-block tears down the case dir (Option B from 07a-RESEARCH.md §2.1). The
   timestamp is authored by the driver (not the executor) per §3.5, threaded via
   `task_spec.metadata["phase7a_timestamp"]`. Other cases that haven't yet opted into
   Phase 7a are a silent no-op (the method is gated on the metadata key).

3. **Backend-side.** New `GET /api/runs/{run_id}/field-artifacts` route +
   `GET /api/runs/{run_id}/field-artifacts/{filename}` download route, both using the
   existing `FileResponse + _resolve_*_file` precedent from `routes/audit_package.py:284-342`.
   User ratification #1 rejected the original CONTEXT decision to use `StaticFiles` —
   the project has no StaticFiles usage elsewhere; `FileResponse` keeps one pattern.
   `run_id = "{case_id}__{run_label}"` parsed via `services/run_ids.py::parse_run_id`
   (rpartition-based, user ratification #5). Per-run manifest at
   `reports/phase5_fields/{case_id}/runs/{run_label}.json` maps label → timestamp.
   Artifacts sorted by `(kind_order, filename)` with `vtk=0 < csv=1 < residual_log=2`
   per user ratification #6.

## Alternatives considered

- **StaticFiles mount** (original CONTEXT proposal): rejected by user ratification #1 — would create
  a second file-hosting paradigm in the backend and JSON+file endpoints would live on different mounts.
- **Option A** (success-callback hook on executor): rejected in research §2.1 — widens the executor
  API surface for all 9 other case generators, adding regression risk.
- **Parse `log.simpleFoam` for residuals**: rejected by user ratification #3 — OpenFOAM's
  `residuals` function object writes a stable space-separated `.dat` file; no regex needed.

## Scope

LDC-only Sprint 1. Turbulent yPlus emission is stubbed but inactive. Other 9 cases will be
fanned-out in Phase 7c Sprint 2 (which reuses `_emit_phase7a_function_objects` per-case).

## Evidence

- LOC: `src/foam_agent_adapter.py` +~130 LOC; `scripts/phase5_audit_run.py` +~45 LOC;
  `ui/backend/` 4 new files (~250 LOC total) + 1 line in main.py.
- Tests: 79 pre-7a → 89+ post-7a (10 new route tests in `test_field_artifacts_route.py`).
- Integration: `.planning/phases/07a-field-capture/_integration_evidence.txt` shows real
  LDC run staging ≥3 artifacts; backend route returning them over HTTP with traversal guard
  proven via 404 response.
- Codex review: see `codex_tool_report_path` in frontmatter.

## Risks / open questions

- **SHA256 cache stale-hash**: content change with identical (mtime, size) returns stale hash.
  Accepted MVP risk (07a-RESEARCH.md §2.6). Phase 7e may upgrade to content-hash cache.
- **Foam-to-VTK `-allPatches` on empty patches**: mitigated by fallback to `foamToVTK` without
  `-allPatches` (§3.2).
- **Byte-repro**: the new `field_artifacts` YAML key has NO embedded timestamps — the
  timestamp lives in the `runs/{run_label}.json` manifest outside the fixture dir.
  `test_phase5_byte_repro.py` stays green (verified in Wave 3 Task 1).

## Self-estimated pass rate

Declared 0.75 pre-review (per 07a-RESEARCH.md §9). Update this field after Codex
verdict lands.

## References

- 07a-CONTEXT.md — user decisions (7 ratifications)
- 07a-RESEARCH.md — technical research (8 questions + validation matrix)
- DEC-V61-029 — Phase 5b LDC simpleFoam migration (upstream)
- DEC-V61-030 — Phase 5b Q-5 Ghia 1982 gold closure (upstream)
- RETRO-V61-001 — risk-tier Codex trigger rules
```

**Step 2 — Update STATE.md**:

Find the active-phase block and update:
- Current phase: Phase 7a → `Phase 7a — field post-processing capture (COMPLETE, DEC-V61-031)`
- Next phase: Phase 7b or whichever is pending
- Add to recent-decisions list: `DEC-V61-031 (2026-04-21) — Phase 7a field capture`
- Update counter block `autonomous_governance_counter_v61` (incremented by 1 for DEC-V61-031)

Use a minimal targeted edit; preserve existing structure. If the file has a "Current Phase" section, update just that section's text.

**Step 3 — Update ROADMAP.md**:

At lines 37-46 (the `### Phase 7a: Field post-processing capture (Sprint 1, ~2-3 days)` block):
- Change `Status: Planned` → `Status: COMPLETE (DEC-V61-031, 2026-04-21)`
- Keep all other lines intact

If Phase 7a has a `Plans:` checklist at the end of its section, mark each as `[x]`.

**Step 4 — Stage + commit atomically:**

```bash
cd /Users/Zhuanz/Desktop/cfd-harness-unified

# Explicit file list — avoid `git add .` per CLAUDE.md rules.
git add \
    src/foam_agent_adapter.py \
    scripts/phase5_audit_run.py \
    ui/backend/schemas/validation.py \
    ui/backend/services/run_ids.py \
    ui/backend/services/field_artifacts.py \
    ui/backend/routes/field_artifacts.py \
    ui/backend/main.py \
    ui/backend/tests/test_field_artifacts_route.py \
    ui/backend/tests/fixtures/runs/lid_driven_cavity/field_artifacts_manifest.yaml \
    ui/backend/tests/fixtures/runs/lid_driven_cavity/audit_real_run_measurement.yaml \
    ui/backend/tests/fixtures/phase7a_sample_fields/ \
    reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review.md \
    reports/phase5_fields/lid_driven_cavity/runs/audit_real_run.json \
    .planning/decisions/2026-04-21_phase7a_field_capture.md \
    .planning/STATE.md \
    .planning/ROADMAP.md \
    .planning/phases/07a-field-capture/_integration_evidence.txt \
    .planning/phases/07a-field-capture/07a-01-PLAN.md \
    .planning/phases/07a-field-capture/07a-02-PLAN.md \
    .planning/phases/07a-field-capture/07a-03-PLAN.md

# DO NOT commit reports/phase5_fields/lid_driven_cavity/{timestamp}/  — these are
# 1.3 MB VTK blobs that shouldn't be in git history. Add a .gitignore rule if not
# already present.
if ! grep -q "reports/phase5_fields/.*/20" .gitignore 2>/dev/null; then
    echo "" >> .gitignore
    echo "# Phase 7a field artifacts — large binary outputs, not committed" >> .gitignore
    echo "reports/phase5_fields/*/20*/" >> .gitignore
    git add .gitignore
fi

git status

git commit -m "$(cat <<'EOF'
feat(phase-7a): field post-processing capture — VTK + sample + residuals on disk + backend route

Implements DEC-V61-031. Every audit_real_run now persists OpenFOAM field
artifacts (binary VTK + sampled CSV + structured residuals) to a stable
on-disk layout under reports/phase5_fields/{case_id}/{timestamp}/, with a
per-run manifest at reports/phase5_fields/{case_id}/runs/{run_label}.json,
and a backend route surfacing them with SHA256 + size.

Solver-side:
- src/foam_agent_adapter.py: new _emit_phase7a_function_objects helper
  (controlDict.functions{} with sample + residuals + yPlus-stubbed) and
  new FoamAgentExecutor._capture_field_artifacts method wired into the
  execute() try-block BEFORE the finally teardown. Timestamp authored by
  the driver and threaded via task_spec.metadata["phase7a_timestamp"].

Driver-side:
- scripts/phase5_audit_run.py: pre-computes shared timestamp, writes
  per-run manifest, appends field_artifacts YAML key after decisions_trail
  (NO timestamps in the YAML doc — byte-repro preserved per 07a-RESEARCH.md §3.1).

Backend-side:
- ui/backend/schemas/validation.py: new FieldArtifact + FieldArtifactsResponse
  Pydantic v2 models.
- ui/backend/services/run_ids.py: new parse_run_id helper (rpartition on '__').
- ui/backend/services/field_artifacts.py: list_artifacts, resolve_artifact_path,
  sha256_of with (path, mtime, size) caching.
- ui/backend/routes/field_artifacts.py: two endpoints mirroring
  audit_package.py's FileResponse pattern — NOT StaticFiles per user
  ratification #1.
- ui/backend/main.py: one-line router registration.

Tests:
- ui/backend/tests/test_field_artifacts_route.py: 10 new tests (manifest
  200/404, ordering vtk<csv<residual_log, SHA256 format, download 200/404,
  traversal reject). Committed offline sample fixture at
  tests/fixtures/phase7a_sample_fields/ so tests run without the solver.
- 79 pytest → 89+ green; test_phase5_byte_repro.py stays green.

Integration:
- .planning/phases/07a-field-capture/_integration_evidence.txt: live
  LDC run produced ≥3 artifacts; backend route returned them over HTTP;
  traversal probe returned 404.

Codex review:
- reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review.md
- Verdict: see file. RETRO-V61-001 trigger: src/ >5 LOC mandated review.

User ratifications honored:
1. FileResponse (not StaticFiles) — audit_package.py precedent
2. writeControl timeStep (simpleFoam is iteration-based, not runTime)
3. residuals function object (structured .dat; no log.simpleFoam regex)
4. Physical-space sample coords (x=0.05 in 0.1-scaled mesh)
5. run_id = "{case}__{run_label}"; rpartition-based helper
6. Artifact sort: vtk < csv < residual_log
7. Per-run manifest at reports/phase5_fields/{case}/runs/{run_label}.json

Refs: DEC-V61-031, RETRO-V61-001, 07a-CONTEXT.md, 07a-RESEARCH.md

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"

git status
git log -1 --stat
```

**Step 5 — Notion sync of DEC-V61-031:**

After commit lands, update DEC frontmatter to change `notion_sync_status: pending` to `notion_sync_status: synced 2026-04-21 (<notion_url>)`. This can be done:
- Automatically by a project hook, OR
- Manually by the Notion MCP with the DEC file contents as input

Refer to the Notion deep-sync rules in CLAUDE.md (§ "Notion 深度同步规则"):
1. Create a page in the Decisions DB with the DEC body
2. Capture the Notion URL
3. Update the DEC frontmatter with `notion_sync_status: synced <date> (<url>)`
4. Commit the sync-status update as a separate minor commit: `docs(dec-v61-031): Notion sync`

If Notion MCP is not available, leave `notion_sync_status: pending` and record the TODO in STATE.md.

**Step 6 — Summary message to user:**

Report:
- DEC-V61-031 authored and committed
- Codex verdict (from Task 2 output)
- Total commit size (`git log -1 --stat | tail -3`)
- STATE/ROADMAP updated to COMPLETE
- Notion sync status (synced vs pending)
- Next up: Phase 7b (render pipeline) or user's choice
  </action>
  <verify>
    <automated>test -f .planning/decisions/2026-04-21_phase7a_field_capture.md && grep -c "DEC-V61-031" .planning/decisions/2026-04-21_phase7a_field_capture.md | awk '$1 >= 2 {exit 0} {exit 1}' && grep -c "COMPLETE" .planning/ROADMAP.md | awk '$1 >= 1 {exit 0} {exit 1}' && git log -1 --format="%s" | grep -q "phase-7a" && git log -1 --format="%b" | grep -q "DEC-V61-031"</automated>
  </verify>
  <acceptance_criteria>
    - `.planning/decisions/2026-04-21_phase7a_field_capture.md` exists, contains `id: DEC-V61-031`
    - Frontmatter contains `autonomous_governance: true`, `status: Adopted`, `codex_tool_report_path: reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review.md`
    - `grep "Status: COMPLETE" .planning/ROADMAP.md` returns ≥1 match near the Phase 7a section (line 37-46)
    - STATE.md updated (check `git diff HEAD~1 .planning/STATE.md` shows non-empty diff)
    - `git log -1 --format="%s"` contains `phase-7a` and `field` (commit subject)
    - `git log -1 --format="%b"` contains `DEC-V61-031` and `Codex review`
    - `git status` shows clean working tree after commit
    - `.gitignore` includes `reports/phase5_fields/*/20*/` rule (large VTK blobs excluded)
    - `reports/codex_tool_reports/2026-04-21_phase7a_field_capture_codex_review.md` exists and is non-empty
    - `.planning/phases/07a-field-capture/_integration_evidence.txt` is committed
    - Commit is a single commit (not multiple) for the Wave 1+2+3 change set
  </acceptance_criteria>
  <done>
Single atomic commit on main with all Wave 1+2+3 changes. DEC-V61-031 written with autonomous_governance=true, Codex report linked, integration evidence referenced. STATE.md + ROADMAP.md updated to reflect Phase 7a COMPLETE. `.gitignore` excludes large VTK blobs. Notion sync status is either synced (with URL in frontmatter) or pending (with STATE.md TODO).
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Local dev machine → git remote | `git push` is NOT called in this plan (per CLAUDE.md git rules); user pushes manually |
| Codex CLI → internet | `codex exec` sends code diff to external OpenAI-backed service |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-07a-13 | Information Disclosure | Codex review sends code to external service | accept | Standard project operation; no secrets or PII in this codebase's Phase 7a files (checked — no env vars, no tokens) |
| T-07a-14 | Tampering | Atomic commit may accidentally include uncommitted debug code | mitigate | Explicit file list in `git add` (no `git add .`); `git status` before commit surfaces surprises |
| T-07a-15 | Denial of Service | 1.3 MB VTK accidentally committed | mitigate | `.gitignore` rule for `reports/phase5_fields/*/20*/` added in Task 3 Step 4 |
| T-07a-16 | Repudiation | Commit without DEC reference | mitigate | Commit message body REQUIRED to reference `DEC-V61-031` (acceptance criterion) |
</threat_model>

<verification>
Phase 7a is COMPLETE when:

1. Integration evidence shows real artifacts on disk + backend returning them over HTTP (Task 1 done)
2. Codex review verdict is APPROVED or APPROVED_WITH_COMMENTS (Task 2 done)
3. DEC-V61-031 exists, STATE/ROADMAP updated, atomic commit landed (Task 3 done)
4. Full backend pytest green (≥89 tests)
5. Byte-repro test green
6. Notion sync status captured (synced OR explicit pending TODO in STATE.md)
</verification>

<success_criteria>
- `scripts/phase5_audit_run.py lid_driven_cavity` produces `reports/phase5_fields/lid_driven_cavity/{ts}/` with VTK + sample CSV + residuals + log
- `GET /api/runs/lid_driven_cavity__audit_real_run/field-artifacts` returns ≥3 artifacts with valid SHA256 over HTTP
- Codex review returns APPROVED / APPROVED_WITH_COMMENTS (not CHANGES_REQUIRED)
- DEC-V61-031 authored per RETRO-V61-001 autonomous format
- `git log -1` is the atomic Phase 7a commit with DEC reference in body
- `.planning/ROADMAP.md` marks Phase 7a as COMPLETE
- `.planning/STATE.md` updated with DEC-V61-031 in recent decisions
- Notion sync either done (URL in DEC frontmatter) or explicitly pending (TODO in STATE.md)
- Ready to hand off to Phase 7b (render pipeline) with stable artifact-on-disk contract
</success_criteria>

<output>
Create `.planning/phases/07a-field-capture/07a-03-SUMMARY.md` + a top-level `.planning/phases/07a-field-capture/PHASE-SUMMARY.md` (aggregating Wave 1+2+3 outcomes) documenting:
- Codex verdict and any required follow-up
- Final total LOC delta
- Final test count (before vs after)
- Integration evidence bullet summary
- DEC-V61-031 commit SHA + Notion URL (if synced)
- Open items for Phase 7b (e.g. "reuse `_emit_phase7a_function_objects` for BFS in Phase 7c Sprint 2")
</output>
