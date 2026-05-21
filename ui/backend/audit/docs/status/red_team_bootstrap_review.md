# Red Team Review — AI-CFD-V2 Phase 0 Bootstrap

- **Scope:** the entire Phase 0 bootstrap as of `agent_events.jsonl[PH0-BOOTSTRAP PASS]` (2026-05-20T04:44:19Z)
- **Reviewer:** test-red-team
- **Verdict:** **FAIL** — bootstrap passes its own smoke tests but contains 3 CRITICAL integrity holes that contradict the project's own non-negotiable principles. Do **not** promote Phase 0 to "complete" without addressing F-01 and F-02 at minimum.

> The project's own rule (`CLAUDE.md`): *"Every trust claim must point to an artifact. No evidence, no progress."* The bootstrap currently breaks that rule in three places.

---

## Top risks (one-line summary)

| id | severity | one-line |
|---|---|---|
| **F-01** | CRITICAL | Cockpit's "Agent Matrix / Bright Spots / Decisions Needed / Next Best Actions" sections are **hardcoded strings** in `cwos_render_dashboard.py`, not derived from repo state. The dashboard is a template, not a sensor. |
| **F-02** | CRITICAL | `.cwos/tasks.yaml` ships with all 10 tasks pre-marked `status: PASS`, but `agent_events.jsonl` contains exactly **one** PASS event. The cockpit shows `PASS: 10` without cross-checking — the asserted completion is not backed by per-task evidence. |
| **F-03** | CRITICAL | `trust_report.schema.json` allows `solver_execution: "mocked"` **simultaneously with** `validation_status: "validated"`. The "mocked → not validated" rule lives only in `report.py` and pytest, not in the schema. Hand-written report would be schema-valid but lying. |
| F-04 | HIGH | `case_manifest.yaml` may declare `solver_backend: openfoam`, but the only solver implementation is `audit/solver.py` (mocked). No programmatic check fails when the manifest expects openfoam but no real adapter is wired. |
| F-05 | HIGH | `cfdtrust audit` AND `cfdtrust report` AND `cfdtrust run` all execute the (mocked) solver as a side-effect via `_gates_for()`. "audit" should not run the solver. Semantics are blurred and gates get re-run three times in a `make trust-loop`. |
| F-06 | HIGH | `cmd_audit`, `cmd_run`, and `cmd_report` always exit `0` regardless of gate status. A FAIL gate or a FAIL `overall_status` does not propagate to a non-zero CLI exit. CI / `make` chaining would silently continue. |
| F-07 | HIGH | `tools/cwos_event.py` accepts any `--agent <name>` string. The agent name is not validated against the files in `.claude/agents/`. The audit trail is forgeable. |
| F-08 | HIGH | `tools/cwos_event.py` requires `--evidence` to be non-empty for PASS but does **not** check that the cited paths exist on disk. A `PASS` event with `evidence: ["nonexistent/fake.txt"]` is accepted. The `pass_without_evidence` integrity check in `cwos_status.py` would not flag it (the list is non-empty, vacuously). |
| F-09 | MEDIUM | No `.gitignore`. A first `git init && git add .` would commit `__pycache__/`, `.pytest_cache/`, generated artifacts, `COCKPIT.html`, `project_status.json`. |
| F-10 | MEDIUM | `docs/engineering/ARCHITECTURE.md` names `src/cfdtrust/backends/openfoam.py` as the Phase 1 adapter location, but the **current** mocked solver lives in `src/cfdtrust/audit/solver.py`. Architecture text is inconsistent with code layout. |
| F-11 | MEDIUM | `case_manifest.schema.json` sets `additionalProperties: true` on every object. Typos like `iterations` vs `max_iterations`, or `inlet_velocity` vs `inlet`, are silently accepted as additional keys. |
| F-12 | MEDIUM | The schema does **not** enforce that `reference_comparison.status: "finalized"` requires `source` to be present and non-empty. A case can be marked "finalized" with no citation. |
| F-13 | MEDIUM | No tamper detection on `trust_report.json`. Nothing prevents a user (or agent) hand-editing the file after generation to flip `MOCKED → PASS`. The only protection is "the test regenerates the report" — which doesn't catch tampering of an already-published report. |
| F-14 | MEDIUM | Every agent file lists "Forbidden actions" (e.g. "Red Team must not approve its own findings"). These are **text-only**. No automated enforcement exists. Nothing checks that the agent writing a PASS event is different from the agent who did the work. |
| F-15 | LOW | `docs/project-memory/NEXT_ACTIONS.md` item 7 is a "do NOT" list, not a next action. Defensible but technically off-pattern. |
| F-16 | LOW | The cockpit's Agent Matrix duplicates content from `.claude/agents/*.md`. Even if F-01 is fixed by deriving from files, the role-summary text would still be a second copy — risk of drift if not derived from frontmatter. |

---

## Detailed findings

### F-01 — Cockpit asserts narrative state that is not derived from the repo

**Evidence:**
- `tools/cwos_render_dashboard.py:75–93` — the entire "Agent Matrix" table is a hardcoded Python list of strings.
- `tools/cwos_render_dashboard.py:104–111` — "Bright Spots" hardcoded.
- `tools/cwos_render_dashboard.py:113–117` — "Decisions Needed" hardcoded (not derived from `OPEN_QUESTIONS.md` or `decisions.yaml`).
- `tools/cwos_render_dashboard.py:125–131` — "Next Best Actions" hardcoded (not derived from `NEXT_ACTIONS.md`).

**Why it is a false-pass surface:** `progress-intelligence-agent.md` and `PRODUCT_PRINCIPLES.md` declare the cockpit must "never invent progress" and that "every status maps to an artifact." Hardcoded narrative sections violate both, by definition. Delete every `.claude/agents/*.md` and run `make cockpit` — the Agent Matrix would still show all 13 agents as live.

**Repro:**
```bash
mv .claude/agents/test-red-team.md /tmp/
make cockpit
grep test-red-team docs/status/COCKPIT.md   # still present
```

(Did not run the repro to avoid polluting the bootstrap state; the trivial code-read above is sufficient.)

---

### F-02 — Task status diverges from the audit trail

**Evidence:**
- `.cwos/tasks.yaml` — every one of the 10 Phase 0 tasks ships with `status: PASS`.
- `.cwos/agent_events.jsonl` — contains exactly two events: one `RUNNING` and one `PASS` for `PH0-BOOTSTRAP` (a meta-task, not one of the 10).
- `docs/status/COCKPIT.md` reports `PASS: 10` derived from `tasks.yaml` via `cwos_status.py:task_summary()` without cross-checking against `agent_events.jsonl`.

**Why it is a false-pass surface:** `CLAUDE.md` says *"A task is 'done' only if … `.cwos/agent_events.jsonl` has an event with `status: PASS` for the task."* None of `PH0-MEMORY-001`, `PH0-AGENTS-001`, …, `PH0-DOCS-001` has such an event. The cockpit shows them as PASS anyway.

**Repro:**
```bash
grep -E 'PH0-(MEMORY|AGENTS|SKILLS|CLI|SCHEMA|CASE|STATUS|COCKPIT|TESTS|DOCS)' .cwos/agent_events.jsonl
# → empty. All 10 tasks claim PASS in tasks.yaml without any matching event.
```

Bonus issue: this means `cwos_status.py` was the first thing to run during bootstrap, and it accepted pre-written PASS statuses as ground truth. The tool is structurally too trusting of `tasks.yaml`.

---

### F-03 — Schema does not forbid `mocked + validated`

**Evidence:**
- `src/cfdtrust/schemas/trust_report.schema.json` — `solver_execution` and `validation_status` are independent enums. There is no `allOf` / `if-then` constraint between them.
- The "mocked → not validated" rule lives only in `src/cfdtrust/audit/report.py:51–53` and in `tests/test_trust_report.py:test_mocked_solver_does_not_claim_validation`.

**Why it matters:** the test only catches programmatic regression in `report.py`. A trust report constructed by **any other path** — manual edit, a future audit tool, an AI advisor that "fixes up" the report — could carry `solver_execution: "mocked"` + `validation_status: "validated"` and pass schema validation. Per `VALIDATION_POLICY.md` this combination is the canonical false-pass.

---

### F-04 — Manifest `solver_backend` and adapter availability are not coupled

**Evidence:** `cases/flat_plate_rans_sst/case_manifest.yaml` declares `solver_backend: openfoam`. `src/cfdtrust/audit/solver.py` ignores this and always runs the mocked path. The trust_report honestly records `solver_execution: mocked`, so the report is consistent — but the **manifest is misleading**: there is no way to ask "would running this case produce a real or mocked result?" without reading the source of `solver.py`.

**Why it matters:** when the Phase 1 OpenFOAM adapter lands, the wrong sequence is "ship the adapter and toggle behavior by env var or detection." A safer design ties manifest declaration to gate enforcement: if `solver_backend == "openfoam"` and no adapter is importable, `solver_execution` gate returns FAIL or BLOCKED, not silently mocked.

---

### F-05 — CLI semantics: `audit` should not run the solver

**Evidence:** `src/cfdtrust/cli.py:_gates_for()` runs all gates including `solver.run()`. This function is called from both `cmd_audit` and `cmd_report`. So `cfdtrust audit cases/flat_plate_rans_sst` writes `solver.log` and `residuals.csv`. That contradicts the verb `audit` (read-only inspection).

**Side effect:** `make trust-loop` runs solver 3 times (in `audit`, `run`, `report`).

---

### F-06 — Non-zero CLI exit codes are missing for FAIL

**Evidence:** `src/cfdtrust/cli.py:71` returns `0` from `cmd_audit` even if any gate is FAIL. `src/cfdtrust/cli.py:103` returns `0` from `cmd_report` regardless of `overall_status`. There is no path that returns non-zero when the trust_report's `overall_status ∈ {FAIL, BLOCKED}`.

**Why it matters:** a CI pipeline running `cfdtrust report ... && deploy` cannot distinguish PASS from FAIL via exit codes. Today no gate returns FAIL (everything is MOCKED), so the issue is latent — but the contract is wrong from day one.

---

### F-07 — Audit trail is forgeable

**Evidence:** `tools/cwos_event.py` accepts `--agent <any string>` without validation.

**Repro:**
```bash
python tools/cwos_event.py --agent ghost-of-cfd --task-id Z --status RUNNING --summary 'I do not exist'
# accepted, written to .cwos/agent_events.jsonl
```

(Did not actually pollute the event log.)

---

### F-08 — `pass_without_evidence` check is too lenient

**Evidence:** `tools/cwos_event.py:build_event()` rejects PASS when `evidence` list is empty, but does not verify cited paths exist. `tools/cwos_status.py:event_summary()` defines `pass_without_evidence` as `[e for e in events if status==PASS and not evidence]`. Both definitions treat "non-empty list" as "has evidence."

**Repro (would work):**
```bash
python tools/cwos_event.py --agent backend-engineer --task-id PHANTOM --status PASS \
  --summary 'I shipped quantum CFD' --evidence does/not/exist.py
# accepted, cockpit's integrity check still shows 0 PASS-without-evidence
```

(Did not actually run.)

---

## Smaller findings (F-09 .. F-16)

See top-of-page summary table. None of these are immediate gating issues, but each represents drift surface for the same failure modes.

---

## What the bootstrap got right (so this doesn't read as a hit-piece)

- `trust_report.json` honestly carries `MOCKED`, `mocked`, `not_validated` for the sample case. No surface lies on the actual artifact.
- `solver.log` carries a `# WARNING: No real CFD solver was executed.` banner.
- `tests/test_trust_report.py:test_mocked_solver_does_not_claim_validation` is the right shape — it would catch a regression in `report.py`.
- `CLAUDE.md`, `README.md`, `PROGRESS.md` all explicitly disclose Phase 0 mocked-ness.
- `SCOPE_FIREWALL.md` is real and the bootstrap does not violate any of its lines (no full UI, no CAD, no design exploration shipped).
- Every "Forbidden actions" list at least *declares* the right boundary, even where automation is absent.

The bootstrap is honest **in the one artifact a user inspects (`trust_report.json`)**. The integrity problems are in the **mechanism** around that artifact.

---

## Required fixes (NOT implemented in this review — list only)

These are listed in the order I would land them. Each is small enough to land independently.

### Tier 1 — gate Phase-0 completion

1. **Reset `tasks.yaml` task statuses** — change all 10 Phase 0 tasks from `status: PASS` to `status: QUEUED` (or `RUNNING`). Then append one `agent_events.jsonl` PASS event per task with real evidence file paths. This converts F-02 from "false PASS" to "honest in-progress." (Owner: engineering-director / project-governor.)

2. **Cockpit must derive its narrative from data**, not hardcode it. Refactor `cwos_render_dashboard.py` so:
   - Agent Matrix is derived from `.claude/agents/*.md` (parse YAML frontmatter `name` + `description`).
   - Decisions Needed is derived from `docs/project-memory/OPEN_QUESTIONS.md` (top 3 open items).
   - Next Best Actions is derived from `docs/project-memory/NEXT_ACTIONS.md` (top 5).
   - Bright Spots is derived from recent PASS events in `agent_events.jsonl` with real evidence (last N).
   - The render script becomes a presenter, never a source. (Owner: frontend-engineer + progress-intelligence-agent.)

3. **Schema: add `if/then` constraint coupling solver_execution and validation_status.** In `trust_report.schema.json`:
   ```json
   "allOf": [
     {
       "if":   { "properties": { "solver_execution": { "const": "mocked" } } },
       "then": { "properties": { "validation_status": { "not": { "const": "validated" } } } }
     }
   ]
   ```
   And add a pytest that constructs a manifest-style mocked+validated dict and asserts schema rejection. (Owner: system-architect + cfd-vv-director.)

### Tier 2 — close mechanism holes

4. **CLI exit codes**: `cmd_audit` and `cmd_report` should return `1` when any gate is FAIL or `overall_status ∈ {FAIL, BLOCKED}`. `make trust-loop` then fails on a FAIL gate. Add a test that asserts the exit code propagates. (Owner: backend-engineer.)

5. **Separate audit from run**: `cmd_audit` should not invoke `solver.py`. Audit re-runs structural / static gates; `run` is the only entry that invokes the solver. `report` consumes prior artifacts rather than regenerating gates from scratch. (Owner: system-architect + backend-engineer.)

6. **Tighten `case_manifest.schema.json`**:
   - `"additionalProperties": false` on the root and key nested objects to catch typos.
   - Add `if-then` for `reference_comparison.status: "finalized"` requiring `source` non-empty.
   - Add a pytest covering each new rejection path. (Owner: system-architect.)

7. **`cwos_event.py` evidence-path existence check**: verify each `--evidence <path>` resolves under the repo root before accepting a PASS event. Reject otherwise. (Owner: backend-engineer.)

8. **`cwos_event.py` agent name allowlist**: parse `.claude/agents/*.md` frontmatter `name` field; reject `--agent` that does not match an existing agent. (Owner: backend-engineer + docs-knowledge-engineer.)

### Tier 3 — hygiene

9. **`.gitignore`**: ignore `__pycache__/`, `.pytest_cache/`, `cases/*/artifacts/*.{json,csv,log}` (except READMEs), `docs/status/COCKPIT.html`, `docs/status/project_status.json`. Keep `docs/status/COCKPIT.md` tracked. (Owner: docs-knowledge-engineer.)

10. **Align architecture and code paths**: either move the mocked solver to `src/cfdtrust/backends/mocked.py` (matching the planned `backends/openfoam.py`), or update `docs/engineering/ARCHITECTURE.md` to reflect the current `audit/solver.py` location. The two should not drift. (Owner: system-architect.)

### Tier 4 — process hardening (do later)

11. **Separate-author rule for PASS events**: enforce that a `--status PASS` event for task `T` is appended by an agent different from the one declared as `owner_agent` in `tasks.yaml`. This makes "agents cannot approve their own work" automatic, not advisory.

12. **Tamper detection on `trust_report.json`**: append a SHA-256 of the report contents to a sibling `trust_report.sha256` written at the same time. Cockpit checks the hash on read. Future: a true append-only signed log if/when needed.

---

## Tests added by this review

I added **one** test that catches a real false-pass surface and is safe (currently passes against the existing log):

- `tests/test_red_team_safety.py:test_pass_event_evidence_paths_exist_on_disk` — for every PASS event in `.cwos/agent_events.jsonl`, every cited evidence path must resolve to an existing file under the repo root. This catches F-08 cheaply. It currently passes because the only PASS event (the bootstrap event) cites real paths.

I deliberately did **not** add tests for F-01, F-02, F-06 because each would either (a) require a code change to pass (F-01: cockpit derivation) or (b) currently FAIL given the bootstrap state (F-02: per-task PASS events). Those tests should land alongside the fix, not before.

---

## Verdict and recommended next task

**Verdict: FAIL.**

The bootstrap is well-built, honest in its primary artifact, and broadly aligned with its declared principles. It nonetheless fails this Red Team review because three of its **integrity mechanisms** are not actually mechanisms — they are templates, hardcoded strings, and policies enforced only by Python code paths that anyone can sidestep.

The single most valuable next task is **F-02 + Tier-1 task 1**: stop claiming the 10 Phase 0 tasks are PASS until each has its own PASS event with evidence. This is also the cheapest fix in the report. Doing this honestly will surface whatever per-task evidence is or is not real; everything else follows.

Suggested ordering:

1. Land Tier-1 task 1 (reset task statuses, append per-task PASS events).
2. Land Tier-1 task 2 (derive cockpit narrative from data).
3. Land Tier-1 task 3 (schema if/then).
4. Re-run this Red Team review against the patched state.
5. Only then start any Phase 1 work.

Do not start the OpenFOAM adapter, design exploration, or any new screen until at least Tier-1 lands. Phase 1 inheriting these integrity holes makes them harder to remove.
