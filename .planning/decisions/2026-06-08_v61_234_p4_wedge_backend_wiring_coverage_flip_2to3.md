---
decision_id: V61-234
title: P4 V71.A — workbench backend wired (foam_agent_adapter + cfdtrust) → runnable-coverage FLIPPED 2→3 (rhoCentralFoam supersonic wedge; the executable reconciliation DEC-V61-233/224(b) deferred)
status: Accepted
parent_dec: V61-233 (the V&V half — direct-container LIVE_VALIDATED; this slice adds the backend-launch half) · V61-224 (the (b) image-reconciliation provision · the deferred "Option A — reconcile + run") · V61-207 (Blueprint v4 Law 1 runnable-coverage)
sibling_decs: V61-228 (W3.3b conjugate flip 1→2 — the immediately prior coverage flip · the looser "gate-is-enough" framing this slice deliberately does NOT inherit) · V61-232 (P4 scaffolding-first) · V61-225 (W3.2b — the adapter OF11 incompressible/CHT reconciliation this slice extends to ESI/compressible)
phase: P4 (compressible/supersonic vertical) · V71.A rhoCentralFoam anchor — runnable-coverage flip (the executable backend reconciliation)
autonomous_governance: true
confidence: high
kogami_opt_in: false (the user drove this autonomously with ultracode + L2; the binding gate is the Codex round-cap=3 chain on the shared docker-exec dispatch surface. This is a "high-risk PR after Codex APPROVE, large blast radius" case where invoking Kogami MIGHT be high-value — the user may invoke it; not auto-triggered post-V133.)
round_cap: 3
codex_review_relay: 86gs gpt-5.4 xhigh (governance baseline; codex review --uncommitted)
codex_verdict: APPROVE (cap=3 closed, 0 P1 at chain close; R0 3×P2+1×P3 addressed; R1 1×P1 — TaskRunner ⟷ specialized-gate wiring — addressed; R2 1×P2 fixed verbatim (ingest env-fork) + 1×P3 → retro queue. 86gs gpt-5.4 xhigh.)
codex_tool_report_path: reports/codex_tool_reports/v61_234_p4_wedge_backend_wiring_report.md
notion_sync_status: synced 2026-06-08 (https://app.notion.com/p/379c68942bed81bfb5a6c6c692b4f2cb)
touches_shared_dec: src/models.py (GeometryType +SUPERSONIC_WEDGE enum member) · src/foam_agent_adapter.py (early SUPERSONIC_WEDGE short-circuit + _execute_supersonic_wedge runner + _docker_run_esi_rm --rm ESI helper + ESI class constants) · src/task_runner.py (R1 P1: _verify_supersonic_wedge + geometry-gated run_task branch wiring the specialized oblique-shock gate into the normal verification flow) · ui/backend/audit/cfdtrust/backends/openfoam.py (manifest-driven solver verb _resolve_solver_name + image-fork env-setup _env_setup_for_image in BOTH run() and ingest() [R2 P2] + solver-name injection fence) · .planning/cfd_capability_matrix.md (rhoCentralFoam GAP-TRACKED→✅ PR · runnable-coverage 2→3 · coupled counters)
date: 2026-06-08
---

# DEC-V61-234 · P4 V71.A workbench backend wired → runnable-coverage FLIPPED 2→3

## Context

Blueprint v4 **Law 1** (DEC-V61-207): a compute type is "covered" only when its
solver runs end-to-end **through the workbench** AND a benchmark passes its
tolerance gate. The **DEC-V61-224(b)** image-reconciliation provision sharpened
"runnable": it requires the workbench **execution backend** (`foam_agent_adapter`)
wired to the image that provides the solver **AND reconciled with the `cfdtrust`
V&V backend — not divergent from it.**

**DEC-V61-233** ran a LIVE `rhoCentralFoam` solve of the M=2.0 inviscid 15° wedge on
the ESI v2312 image and the oblique-shock gate PASSED within 0.5% of the analytical
θ-β-M gold — but **Codex R0 P2-1 correctly refused the coverage flip**: that solve
ran **directly in a `--rm` container**, bypassing both workbench backends. So 233
landed honestly as a **V&V-validation milestone** (`validation_status:
LIVE_VALIDATED`), with the matrix held at GAP-TRACKED and **runnable-coverage stuck
at 2**. The remaining work — the executable backend reconciliation (DEC-V61-224's
deferred "Option A") — was explicitly scoped out and committed to "a separate slice
that WILL carry the full Codex round-cap=3 chain."

This DEC is that slice. The sponsor approved opening it (ultracode, L2).

## Decision

Wire **both** workbench backends so the harness genuinely launches the supersonic
wedge end-to-end, then flip the capability matrix — the flip **lagging** working,
tested code, per anti-fraud charter §6.

### What changed

1. **`GeometryType.SUPERSONIC_WEDGE`** (`src/models.py`) — the canonical routing key
   the gold YAMLs already declare; value byte-matches the gold contract. `TaskSpec`
   needs no new fields (it already carries `Ma`; the wedge geometry/physics live in
   the frozen `case_definition/` + the gold's `wedge_inputs`).

2. **`foam_agent_adapter` execution-backend wiring** (`src/foam_agent_adapter.py`):
   - An **early short-circuit** in `execute()` (before the Foundation-OF11
     persistent-container connect) routes `SUPERSONIC_WEDGE` to a dedicated
     **`_execute_supersonic_wedge`** runner — so the wedge is fully independent of
     the OF11 incompressible runtime and **never reaches the
     `_OF11_INCOMPRESSIBLE_SOLVERS` fence** (which is left byte-identical;
     rhoCentralFoam is NOT added to it — the honesty fence is un-weakened).
   - The runner stages the frozen, validated `case_definition/` (reused verbatim — no
     parametric generator, so the gate stays byte-faithful) and runs `blockMesh &&
     checkMesh && rhoCentralFoam` via a new **`_docker_run_esi_rm`** helper: a FRESH
     `docker run --rm` ESI v2312 container sourcing `/openfoam/profile.rc` (matching
     `reports/showcase_aero/_w71a_wedge_probe/REPRODUCE.md` verbatim), force-removed
     in `finally` — disturbing no running container (~/CLAUDE.md hard rule).
   - It then **EXTRACTS** the QoIs via the Execution-plane extractor and returns
     `ExecutionResult(success=True, is_mock=False, key_quantities=...)`. `success`
     means "a real solve completed and produced extractable QoIs" — NOT "the physics
     matches gold"; any non-zero exit or failed extraction is an honest BLOCK.

3. **`cfdtrust` V&V-backend reconciliation** (`ui/backend/audit/cfdtrust/backends/openfoam.py`)
   — the "not divergent" half of 224(b):
   - The solver verb is now **manifest-driven** (`_resolve_solver_name`, reading
     `manifest['solver']`, the same field the residual gate already trusts), NOT a
     hardcoded `simpleFoam`; absent → simpleFoam (existing manifests byte-stable).
   - The container env-setup is **image-fork-aware** (`_env_setup_for_image`: ESI
     `/openfoam/profile.rc` for `opencfd/*`, Foundation `/opt/openfoam11/etc/bashrc`
     otherwise) so an ESI manifest sources the right profile.
   - A **solver-name injection fence** (`^[A-Za-z][A-Za-z0-9_]*$`) sanitizes the
     manifest value before it reaches the container `bash -c` argv — closing the gap
     the existing image-name fence never covered.
   - **Codex R2 P2 (verbatim)**: the image-fork env-setup is applied in **both
     `run()` AND `ingest()`** — the ingest checkMesh call previously defaulted to the
     Foundation OF11 bashrc, which would false-BLOCK an ESI/opencfd ingest before
     reading any evidence. This completes the 224(b) reconciliation across both
     cfdtrust entry points (the pre-declared ingest follow-up is now closed, not
     deferred).

4b. **TaskRunner ⟷ specialized-gate wiring** (`src/task_runner.py`, **Codex R1 P1**):
   registering the wedge in the whitelist (R0 P2-3) made it SELECTABLE through
   `KnowledgeDB.list_whitelist_cases()` — but `GeometryType.SUPERSONIC_WEDGE` is a
   *loadable* enum (it MUST be, because the adapter dispatches on it — unlike the CHT
   `COMPLEX` sentinel that hides from the loader), so it was exposed-as-a-benchmark
   yet unverifiable: `load_gold_standard` → None, so `run_task` skipped comparison and
   `run_batch` reported "No gold standard found" after a real solve. Fixed by a
   `geometry_type`-gated branch in `run_task()` that routes a successful wedge run
   through a new `_verify_supersonic_wedge` helper → `gate_wedge_against_gold`,
   translating the `WedgeGateResult` into the normal `ComparisonResult` (any gate
   error is an honest FAIL, never a fabricated pass). Plane: Control→Control
   (contract-legal). This makes the wedge genuinely **launched AND verified** through
   the normal pipeline — stronger than the CHT precedent (verified out-of-band only).

4. **Capability matrix flip** (lags the working code): `rhoCentralFoam`
   GAP-TRACKED→✅ PR; Solvers PR 6→7/10; **runnable-coverage compute types 2→3**
   (incompressible RANS · CHT · compressible supersonic shock-capturing); §1
   laminar×COMP-STEADY cell→PR; §8 cells PR 33→35/59. breadth-score audit 100.

### Why this meets the 224(b) bar (and the stricter framing it is held to)

The flip is held to the **stricter DEC-V61-224(b) bar** — the workbench backend
*launches* it — **explicitly NOT the looser DEC-V61-228 "the gate is what flips
coverage" framing** (1→2). Pre-empting the goalpost-moving objection: the bar
tightened between 228 and 233; this slice meets the tighter bar, with NEW evidence
that a **backend** was the launcher:

- **Backend-launched e2e** (the delta 233 lacked):
  `reports/showcase_aero/_w71a_wedge_backend_e2e/` — `execution_result.json`
  (`launcher: foam_agent_adapter...execute()`, success=true, is_mock=false, the
  measured QoIs) + `gate_verdict.json` (gate PASS) + the backend-produced
  postProcessing + `SHA256SUMS` (6/6 verify OK). This is DISTINCT from
  `_w71a_wedge_probe` (a direct container run — the V&V half).
- **Both backends dispatch the same solver+image+profile** (not divergent): the
  adapter live e2e proves the dispatch works; the cfdtrust reconciliation is
  unit-tested to dispatch rhoCentralFoam on the ESI image with the ESI profile.
- **Plane discipline**: the Execution-plane adapter calls the Execution-plane
  extractor (allowed); the Control-plane gate is run by the caller (the test), never
  imported by the adapter — no Execution⇄Control cycle. Four-plane import-linter **5
  KEPT, 0 broken**; `gen_importlinter.py --check` byte-repro exit 0.

## Tests / verification

- **Fast (mocked docker, always-on)**: 8 adapter dispatch locks
  (`tests/p4/test_supersonic_wedge_dispatch.py`) + 6 cfdtrust dispatch locks
  (`ui/backend/audit/cfdtrust_tests/test_supersonic_wedge_backend.py`) — routing,
  ESI image/profile selection, BLOCK-on-failure, fence un-weakened, env-fork,
  injection rejection. `test_models` gains the enum assertion.
- **Opt-in gated live e2e** (`tests/p4/test_supersonic_wedge_live.py`,
  `CFDTRUST_LIVE_WEDGE_E2E=1`): the real backend launch + gate PASS (25s). SKIPS in
  the default suite (no docker / no ESI image), mirroring the
  `CFDTRUST_LIVE_NETWORK_TESTS` pattern.
- **R1 TaskRunner wiring lock** (`tests/p4/test_supersonic_wedge_taskrunner.py`, 5
  tests, hermetic — no docker, runs the real gate on the FROZEN backend-e2e output):
  `run_task` verifies the wedge via the specialized gate (passed=True, summary carries
  `wedge_oblique_shock gate`, trust_gate_report non-None); `run_batch` reports 1 PASS
  with "No gold standard found" ABSENT (the exact regression closed); honest FAIL on
  bad/empty output (no crash, no fabricated pass); the branch is geometry-gated.
- **R2 ingest env-fork locks** (`ui/backend/audit/cfdtrust_tests/test_ingest_mode.py`,
  2 tests): opencfd image → ingest sources `/openfoam/profile.rc`; image omitted →
  Foundation OF11 bashrc preserved (byte-stable).
- No regression: full p4 + models + cfdtrust suites green (`cfdtrust_tests` 498
  passed/1 skipped; p4+adapter+models+cfdtrust 746 passed/2 skipped; consumer set
  181 passed/1 skipped); four-plane lint 5 KEPT/0 broken; `gen_importlinter --check`
  byte-repro exit 0; breadth audit 100.

## Governance

- `autonomous_governance: true` (counter +1 on Accept).
- **Codex round-cap=3 chain** is the binding gate (security-boundary trigger: manifest
  values now reach a container argv via a shared exec path; new GeometryType;
  cross-file adapter+cfdtrust). **Chain CLOSED**: R0 (3×P2+1×P3 addressed) → R1 (1×P1
  TaskRunner wiring addressed) → R2 (final round, cap=3: NO P1; P2 ingest env-fork
  fixed verbatim; P3 case_export → retro queue). **Zero P1 outstanding** → APPROVE-
  equivalent → `status: Proposed → Accepted`. Per the cap=3 rule, remaining P2/P3 do
  not trigger further review rounds; the P2 was landed under the verbatim-exception
  (`不再走一轮`), the P3 entered the retro queue.
- **Four-question gate**: (1) LLM offline — N/A (no LLM surface); (2) artifacts — the
  backend-e2e frozen evidence + tamper manifest is the artifact; (3) TrustGate — the
  Control-plane oblique-shock gate is the verdict, PASS on backend output; (4)
  advisory-only — N/A (this is a runnable-execution path, the point of the slice).
- Notion: `pending_accepted` → session-end batch (Accepted-only).

## Documented follow-ups (out of scope, not blocking)

- θ=10° secondary case LIVE run (gold stays `ANALYTICAL_REFERENCE_AUTHORED`).
- ~~ESI-image ingest in the cfdtrust `ingest()` path~~ — **CLOSED at R2** (Codex R2
  P2, verbatim): `ingest()` now sources the image-fork env-setup, so the
  reconciliation covers both `run()` and `ingest()`.
- **[retro queue · Codex R2 P3]** `case_export.py` reads inline
  `case['gold_standard']` only, so the wedge (and CHT's `case_002a` — same shape,
  pre-existing) export with `Quantity: unknown` + dropped tolerance. The correct fix
  is an export-side fallback to the file-backed `knowledge/gold_standards/<case>.yaml`
  that handles the multi-doc / multi-observable specialized-gate shape (no single
  quantity/tolerance). NOT fixed here because the quick inline-stub fix would REGRESS
  the R1 specialized-gate wiring (a non-None `load_gold_standard` would re-route the
  wedge through the generic comparator). Cosmetic severity (reference-bundle README
  metadata; never a false PASS).
- **[retro queue · noted at R0]** an `auto_verifier` hook for specialized-physics
  gates (CHT-shared; the generic residual comparator cannot judge oblique-shock or
  conjugate-energy physics).
- A parametric wedge generator for varying M1/θ (this slice reuses the single frozen
  `case_definition/` verbatim — lowest-risk, gate-byte-faithful).
- A live `cfdtrust run <wedge>` (the cfdtrust dispatch is code+unit-test proven; the
  adapter live e2e is the headline backend-launch evidence).

## Evidence appendix

- Live e2e: `CFDTRUST_LIVE_WEDGE_E2E=1 .venv/bin/python -m pytest tests/p4/test_supersonic_wedge_live.py` → 1 passed (25s).
- Backend-e2e gate summary: `beta=45.2372°, M2=1.4445, p2/p1=2.1879, rho2/rho1=1.7219, T2/T1=1.2692, M1_meas=2.0000` · all 6 hard gates PASS.
- Docker state at flip: `opencfd/openfoam-default:2312` present; running containers `cfd_v12_run`/`of11_run`/`of11_probe` untouched (fresh `--rm`).
- Four-plane: `lint-imports` → 5 contracts kept, 0 broken; `gen_importlinter.py --check` exit 0.

— cfd-chief-engineer (L2), 2026-06-08
