# Codex Tool Report — DEC-V61-234 · P4 workbench backend wiring (runnable-coverage 2→3 flip)

- **Relay backend**: 86gamestore (`~/.codex-relay`), model `gpt-5.4`, reasoning `xhigh` (governance baseline, RETRO-V61-001).
- **Command**: `codex review --uncommitted` (the staged backend-wiring slice vs HEAD `2bb68ee`).
- **Round cap**: 3 (R0 + 2 fix iterations).
- **Raw logs**: `_r0_raw.txt` / `_r1_raw.txt` / `_r2_raw.txt` are **local-only** (gitignored via `reports/codex_tool_reports/*.txt`). **This tracked `.md` is the canonical, self-contained review trail.**
- **Scope note**: the review diff also includes the already-Accepted DEC-V61-233 slice (still uncommitted on the same branch). All findings below are on the NEW DEC-V61-234 wiring; the prior slice was not re-litigated.

## What this slice does

Wires **both** workbench backends so the harness launches the supersonic wedge
end-to-end — the executable reconciliation DEC-V61-233 deferred and DEC-V61-224(b)
mandates. New `GeometryType.SUPERSONIC_WEDGE` → `foam_agent_adapter._execute_supersonic_wedge`
runs a LIVE `rhoCentralFoam` solve in a fresh `--rm` ESI v2312 container; the
Control-plane oblique-shock gate PASSES on the backend output; the `cfdtrust`
backend is reconciled (manifest-driven solver + image-fork env-setup + injection
fence). Capability matrix flipped runnable-coverage **2→3** (lagging the working code).

## Round-by-round

### R0 — NO P1; 3× P2 + 1× P3 (all real, all integration/honesty-completeness) → all ADDRESSED

Codex headline: *"The new supersonic-wedge path can execute, but it currently drops
solver-log evidence, reuses a clobbering work directory, and is not registered in the
normal case/gold lookup pipeline. In addition, the audit explainer becomes misleading
once non-simpleFoam dispatch is enabled."* No functional/logic defect; the live solve
+ gate were sound from R0.

- **[P2-1] rhoCentralFoam log not persisted** (`foam_agent_adapter.py` `_execute_supersonic_wedge`):
  the runner captured `run_log` in memory but never wrote a `log.*` file under
  `raw_output_path`, so log-based consumers (`TaskRunner._resolve_log_path`,
  `auto_verifier._find_log_file`) would lose attestation. **Fix**: persist
  `run_log` → `work_dir/log.rhoCentralFoam` on BOTH success and failure (fail-tolerant),
  the same `log.{solver}` convention the OF11/CHT paths use. Verified live (1.49 MB log written).

- **[P2-2] clobbering work directory** (`foam_agent_adapter.py` `_execute_supersonic_wedge`):
  `work_dir` was derived only from `task_spec.name` and unconditionally `rmtree`'d before
  each run — a second/concurrent launch could erase a prior run's `raw_output_path` mid-read.
  **Fix**: a UNIQUE work dir per run via `tempfile.mkdtemp(prefix=case_id+"_", dir=self._work_dir)`;
  the unconditional rmtree removed. Verified live (raw_output_path now carries a unique suffix).

- **[P2-3] wedge anchor not in the runtime case registry** (`knowledge/whitelist.yaml`):
  nothing registered the new benchmark in the lookup tables `TaskRunner` uses, so
  `KnowledgeDB.get_execution_chain('wedge_oblique_shock')` returned None and the normal
  runner skipped it. **Fix**: added a `wedge_oblique_shock` whitelist entry
  (`geometry_type: SUPERSONIC_WEDGE`, `solver: rhoCentralFoam`,
  `solver_docker_image: opencfd/openfoam-default:2312`) so `get_execution_chain` now
  resolves the chain. Like the CHT anchor (`case_002a`) the entry carries **no inline
  generic `gold_standard`**: its verification is a SPECIALIZED physics gate, so
  `load_gold_standard` correctly returns None (→ TaskRunner "no gold → no comparison",
  no spurious generic-comparator FAIL) and `gate_wedge_against_gold` loads the analytical
  θ-β-M gold directly + applies the 6 hard gates. Not added to `src/auto_verifier`
  (its generic residual comparator cannot judge oblique-shock physics — the same design
  as the CHT specialized gate; an auto_verifier hook for specialized-physics gates is a
  pre-existing, CHT-shared follow-up, not a wedge-specific gap). `verification_gate` +
  `gold_standard_file` pointer fields make the specialized path discoverable from the registry.

- **[P3] `cfdtrust explain` hardcoded simpleFoam** (`ui/backend/audit/cfdtrust/cli_explain.py`
  `_explain_solver`): once `run()` dispatches the manifest-declared solver, the explainer
  still named `simpleFoam` in its PASS / residual-FAIL text, so a rhoCentralFoam run would
  be explained to the user as simpleFoam. **Fix**: `_explain_solver` now reads
  `manifest['solver']` (default simpleFoam) and names the actual solver.

Post-R0 verification: 730 passed / 2 skipped under `.venv` (p4 + foam_agent_adapter +
models + full cfdtrust_tests); 65 consumer-regression passed (knowledge_db, e2e_mock,
task_runner_trust_gate); four-plane import-linter 5 KEPT / 0 broken; `gen_importlinter.py
--check` byte-repro exit 0; live e2e re-PASS (27s); backend-e2e SHA manifest 6/6 OK.

### R1 — 1× P1 (ESCALATION of R0's P2-3) + (no new P2/P3) → ADDRESSED

Codex headline (verbatim core): *"Wire the specialized wedge gate into TaskRunner
flows — `knowledge/whitelist.yaml`. Adding `wedge_oblique_shock` to the whitelist
makes it selectable through `KnowledgeDB.list_whitelist_cases()` /
`_task_spec_from_case_id()`, but `KnowledgeDB.load_gold_standard()` still only reads
inline `whitelist.yaml::gold_standard`. The new `gold_standard_file` and
`verification_gate` fields are therefore ignored: `TaskRunner.run_task()` skips
comparison entirely for this case, and `run_batch()` will report 'No gold standard
found for case wedge_oblique_shock' even after a successful live run. In other words,
the case is now exposed as a benchmark, but none of the normal TaskRunner-based
workflows ever call `gate_wedge_against_gold`."*

This is the integration consequence of the R0 P2-3 fix: registering the anchor closed
the `get_execution_chain` gap but opened an **exposed-but-unverifiable** gap, because
`SUPERSONIC_WEDGE` is a *loadable* enum.

- **[P1] specialized wedge gate not wired into TaskRunner** → **Option A (wire it),
  not Option B (make it non-loadable like CHT)** — and the choice was **forced, not
  free**: the CHT anchor hides from `list_whitelist_cases()` by using the
  `geometry_type: COMPLEX` *sentinel* (an INVALID `GeometryType`, so the
  `GeometryType(...)` try/except skips it). The wedge **cannot** use that trick —
  `GeometryType.SUPERSONIC_WEDGE` MUST be a valid enum member because the
  `foam_agent_adapter` dispatches on it. So the wedge is unavoidably loadable, hence
  it MUST be verifiable through TaskRunner or it is an honesty gap. **Fix**
  (`src/task_runner.py`): (1) a new private `_verify_supersonic_wedge(exec_result)`
  helper that lazily imports `gate_wedge_against_gold` (Control→Control — both modules
  are Control-plane, contracts 1/2/3 untouched), runs it on
  `exec_result.raw_output_path`, and translates the `WedgeGateResult` →
  `ComparisonResult(passed, summary, gold_standard_id="wedge_oblique_shock")`; any gate
  error is an honest FAIL, never a fabricated pass. (2) a `geometry_type`-gated branch
  in `run_task()` (`comparison is None and geometry is SUPERSONIC_WEDGE and success and
  not ATTEST_FAIL`) that sets `comparison` from the helper — mirroring the generic
  comparison guard so no other case path is touched. `run_batch()` needs no change: it
  now sees a populated `comparison_result`, so the "No gold standard found" fallback is
  never reached. No `CorrectionSpec` is synthesized on wedge FAIL (a benchmark anchor's
  verdict is reported, not auto-corrected; the recorder expects generic-comparator
  deviations the specialized gate does not emit).

Post-R1 verification (under `.venv`):
- New wiring lock `tests/p4/test_supersonic_wedge_taskrunner.py` (5 tests, all pass):
  `run_task` verifies the wedge via the real gate against the FROZEN backend-e2e output
  (passed=True, summary carries `wedge_oblique_shock gate`, trust_gate_report non-None);
  extraction-failure + no-output-path are honest FAILs (no crash, no fabricated pass);
  `run_batch(["wedge_oblique_shock"])` reports **1 PASS** and the string
  `No gold standard found` is **absent** from every result summary (the exact
  regression closed); the branch is geometry-gated (a SIMPLE_GRID spec never calls
  `_verify_supersonic_wedge`).
- No regression: `tests/p4/ + test_foam_agent_adapter{,_run_report} + test_models +
  ui/.../cfdtrust_tests` → **746 passed / 2 skipped**; consumer set (`test_task_runner`,
  `test_task_runner_trust_gate`, `test_task_runner_executor_mode`, `test_knowledge_db`,
  `test_e2e_mock`, `test_auto_verifier`) → 181 passed / 1 skipped.
- Four-plane import-linter **5 KEPT / 0 broken** (the new Control→Control import is
  contract-legal); `gen_importlinter.py --check` byte-repro exit 0.

### R2 — NO P1; 1× P2 + 1× P3 (final round under cap=3) → P2 ADDRESSED (verbatim), P3 → retro queue

Codex headline (verbatim): *"The main wedge/backend wiring looks sound, but the
ESI image reconciliation is incomplete because ingest-mode still uses the
Foundation bashrc and will fail on opencfd images. There is also a smaller
regression in exported case metadata for the newly listed wedge anchor."*

The R1 P1 fix (TaskRunner ⟷ specialized gate wiring) is **accepted** — no
re-litigation. Two new findings, both real, neither blocking the binding gate
(no P1):

- **[P2] ingest-mode env-setup not fork-aware** (`ui/backend/audit/cfdtrust/backends/openfoam.py`,
  `ingest()` checkMesh call): `run()` now derives `_env_setup_for_image(image)`,
  but `ingest()` still called `_run_docker_command("checkMesh", ...)` with the
  default Foundation OF11 bashrc — so ingesting an ESI/opencfd case (e.g. an
  externally produced rhoCentralFoam wedge) would source a non-existent
  `/opt/openfoam11/etc/bashrc` inside the ESI container and **false-BLOCK at
  checkMesh before any evidence is read**, leaving the 224(b) reconciliation
  incomplete for ingest workflows. This had been pre-declared an out-of-scope
  follow-up in the DEC; Codex correctly flagged that the declaration leaves a
  real gap. **Fix (verbatim Codex R2 — `不再走一轮` per the verbatim-exception
  rule): pass `env_setup=_env_setup_for_image(image)` to the ingest checkMesh
  call**, exactly mirroring `run()`. `image` is already validated (non-empty +
  valid-docker-name) before that call. New locks
  (`ui/backend/audit/cfdtrust_tests/test_ingest_mode.py`): an opencfd image →
  `source /openfoam/profile.rc` (not the OF11 bashrc); image omitted → Foundation
  bashrc preserved (byte-stable). This **completes the reconciliation across BOTH
  `run()` and `ingest()`** — strengthening, not weakening, the slice's 224(b)
  claim. Being the literal landing of R2's own suggestion, it is verbatim-exempt
  from a further review round (cap=3 reached at R2).

- **[P3] export metadata for the wedge anchor** (`ui/backend/routes/case_export.py`):
  the route reads inline `case['gold_standard']` only (for `quantity` /
  `tolerance`), so the wedge — which intentionally carries NO inline generic gold
  (its verdict is the specialized gate) — exports as `Quantity: unknown` with the
  tolerance dropped. **Disposition → retro queue + DEC follow-up, NOT fixed in
  this slice**, for three honest reasons: (1) the "obvious" quick fix — adding an
  inline `gold_standard` stub — would **REGRESS the R1 P1 fix**: it would make
  `load_gold_standard` return non-None, so the generic comparison block fires
  first and the `comparison is None` wedge branch never runs, **bypassing the
  specialized gate** the whole slice exists to wire. So that fix is not available.
  (2) The correct fix (export falls back to the file-backed
  `knowledge/gold_standards/<case>.yaml`, handling the multi-doc / multi-observable
  specialized-gate shape that has no single `quantity`/`tolerance`) is a genuine
  design change on a user-facing route. (3) The root cause is **pre-existing and
  shared with the CHT anchor** (`case_002a`, also whitelisted without inline gold
  — `case_export` reads the raw whitelist, so CHT degrades identically); the
  wedge is the second instance, not a new bug class. Severity is cosmetic
  (degraded README metadata in a reference bundle — never a false PASS, never a
  safety/correctness failure), consistent with the documented auto_verifier
  specialized-gate-hook follow-up precedent.

Post-R2 verification (under `.venv`): full `ui/backend/audit/cfdtrust_tests/`
→ **498 passed / 1 skipped** (incl. the 2 new ingest env-fork locks + the 6
DEC-234 backend locks); four-plane import-linter **5 KEPT / 0 broken**;
`gen_importlinter.py --check` byte-repro exit 0.

## Net verdict — APPROVE-equivalent (cap=3 closed; binding P1 axis clean)

- **R0**: NO P1; 3× P2 + 1× P3 — all ADDRESSED.
- **R1**: 1× P1 (escalation of R0 P2-3) — ADDRESSED (TaskRunner ⟷ specialized
  gate wiring; the choice was architecturally forced, not free).
- **R2** (final round, cap=3): NO P1; 1× P2 (ADDRESSED verbatim — ingest env-fork
  completing the reconciliation) + 1× P3 (→ retro queue, with an honest rationale
  that the quick fix would regress R1 and the root cause is CHT-shared/pre-existing).

The binding governance gate (the security-boundary trigger: manifest solver+image
now flow into a container argv via a shared exec path) is satisfied — **zero P1
outstanding** at chain close. Two findings deferred to the retro queue:
- the P3 `case_export` fallback for specialized-gate anchors (CHT-shared); and
- the pre-existing auto_verifier specialized-physics-gate hook (CHT-shared, noted
  at R0).

DEC-V61-234 advances `status: Proposed → Accepted`; `codex_verdict: APPROVE
(cap=3 closed, 0 P1; R2 P2 fixed verbatim, R2 P3 + auto_verifier hook → retro queue)`.
