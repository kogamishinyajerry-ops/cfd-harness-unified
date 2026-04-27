# ROADMAP

> **2026-04-26 refocus**: post-pivot user-as-first-customer reframe (Pivot Charter Addendum 1).
> Single main-line: **Workbench Closed-Loop M1-M4** — open case → modify params → real OpenFOAM → SSE phase → verdict → run history → auto-jump.
> Phase 1-8 / W1-W4 governance archive moved to `## Closed (do not reopen)`.

## Current main-line: Workbench Closed-Loop M1-M4

**North star**: 你能每天打开 `/workbench`，改 LDC 参数，跑真实 Docker+OpenFOAM，看见三态 verdict，对比历史 run。30 天交付。

**Total budget**: ~650 LOC + tests, <1.5 weeks active dev time. Significantly under the 30-day estimate because `case_editor.py` + `wizard_drivers.py` SolverDriver protocol + `RunPhaseEvent` Q13 forward-compat schema + `reports/{case_id}/` artifact convention already shipped.

### M1 — RealSolverDriver (week 1, ~200 LOC)
- **Goal**: `wizard_drivers.py` gets a `RealSolverDriver` sibling to `MockSolverDriver`. Wraps `FoamAgentExecutor.execute(task_spec) -> ExecutionResult` (the only public method needed).
- **Required outputs**:
  - `RealSolverDriver(case_id)` class in `ui/backend/services/wizard_drivers.py` honoring SolverDriver protocol
  - env: `CFD_HARNESS_WIZARD_SOLVER=real|mock` (default `mock` for backward compat with Stage 8a demo)
  - foam_agent stdout/stderr → SSE `log` / `phase_start` / `phase_done` / `metric` / `run_done` events
  - Q13 forward-compat fields wired: `level: warning|error`, `stream: stderr`, `exit_code` for non-zero exits
  - Tests: subprocess mocked at `FoamAgentExecutor.execute` boundary; SSE shape regression against MockSolverDriver test scaffold
  - **Retire `ui/backend/services/run_monitor.py` synthetic residual stream** (Phase-3 placeholder, Q11 trust-violation risk)
- **Constraints**: line-A only — touches ONLY `wizard_drivers.py` + tests + minor `run_monitor.py` deletion. Does NOT modify `foam_agent_adapter.py` internals (line-B's territory).

### M2 — `/workbench/case/{id}/edit` frontend (week 2, ~150 LOC)
- **Goal**: New page reuses the existing `case_editor.py` backend (already complete: GET/PUT/POST-lint/DELETE on `/api/cases/{id}/yaml`, writes to `ui/backend/user_drafts/`, hard-floor protects `whitelist.yaml` + `gold_standards/`).
- **Required outputs**:
  - `ui/frontend/src/pages/workbench/EditCasePage.tsx` — load YAML, edit Re/mesh size/endTime, server-rendered byte-exact preview pattern (reused from Stage 8a wizard)
  - "Run with these params" button → `POST /api/wizard/draft` → triggers RealSolverDriver via `CFD_HARNESS_WIZARD_SOLVER=real`
  - Lint feedback inline (typo defense same as wizard)
- **Constraints**: line-A only.

### M3 — Run history + auto-jump (week 3, ~250 LOC)
- **Goal**: Every real run lands in `reports/{case_id}/runs/{run_id}/{measurement.yaml, verdict.json, summary.json}`. Frontend table + auto-jump after SSE `run_done`.
- **Required outputs**:
  - `ui/backend/services/run_history.py` enumerating `reports/{case_id}/runs/*` directories
  - `GET /api/cases/{case_id}/runs` + `GET /api/cases/{case_id}/runs/{run_id}` endpoints
  - `RunHistoryPage.tsx` table — date / Re / mesh / verdict / duration
  - SSE `run_done` handler in `WorkbenchRunPage` auto-redirects to `/workbench/case/{id}/run/{run_id}`
- **Constraints**: line-A only. New write-domain: `reports/{case_id}/runs/{run_id}/` (not `reports/phase5_fields/` which is Phase-7 territory).

### M4 — Docker fail classifier (week 3-4, ~80 LOC)
- **Goal**: Distinguish docker_missing / openfoam_missing / mesh_failed / solver_diverged / postprocess_failed from raw FATAL, surface readable suggestion in UI.
- **Required outputs**:
  - `_classify_failure(stderr, exit_code) -> FailureCategory` in `wizard_drivers.py::RealSolverDriver`
  - SSE `run_done` carries `failure_category` field (Q13 schema-forward already supports arbitrary fields)
  - Frontend `FailureBanner` component showing category + 1-2 sentence remediation
- **Constraints**: line-A only.

## Next main-line: Beginner Full Stack M5–M8 (post-M4 · added 2026-04-27)

**Origin**: graduated into the M-sequence from prior §90-day extension "import/register your own OpenFOAM case + full closed-loop on user-supplied geometry + Docker failure root-cause UI". User-as-first-customer pivot (Pivot Charter Addendum 1) makes this the natural sequel to M1–M4 dogfood-validation (3 anchors closed 2026-04-27).

**Sequencing**: M5 → M6 → M7 → M8 in M-letter order. **No calendar deadline.** Gate between Ms is completion-of-prior-M; final gate at end of M8 is the stranger-dogfood test (replaces the 60-day-window framing previously implied by the kickoff spec — per Kogami M5 clearance 2026-04-27 finding 3).

### M5 — STL-only Case Import v0

- **Goal**: Workbench-side STL upload + trimesh sanity check + scaffold OpenFOAM case directory by forking the LDC template + route to `/workbench/case/{id}/edit`.
- **Tier split** (per Kogami clearance 2026-04-27 findings 1, 2, 5 — reading (a) routine + trust-core carve-outs):
  - **M5.0 routine**: `geometry_ingest/`, `case_scaffold/`, `import_geometry.py` route, `ImportPage.tsx`, `case_manifest.yaml` `source_origin` schema field, trimesh dep. Routine path per post-pivot 2026-04-26 standing rule: direct commit to main, single-pass Codex review on upload+pip-dep novelty. No DEC.
  - **M5.1 trust-core micro-PR**: TrustGate hard-cap imported cases at `PASS_WITH_DISCLAIMER` (touches `src/metrics/trust_gate/` semantic boundary) + `audit_package` `--include-imported` filter (touches `src/audit_package/` explicitly trust-core). Full trust-core path: DEC-V61-08X authored, Codex 3-round, Kogami high-risk-PR clearance with intent_summary + merge_risk_summary.
- **Out of scope (deferred to later M)**: STEP/IGES, geometry healing, UI patch picking, cfMesh, NL agent on case generation.
- **Strategic clearance record**: `.planning/reviews/kogami/m5_kickoff_governance_clearance_2026-04-27/` (APPROVE_WITH_COMMENTS · `recommended_next: revise` · 7 findings).
- **Revised kickoff spec**: `.planning/strategic/m5_kickoff/spec_v2_2026-04-27.md`.

### M6 — gmsh-based unstructured meshing path

- **Goal**: Take the imported case's `triSurface/{stl}` (M5.0 output), run gmsh + `gmshToFoam`, and write a runnable mesh under `user_drafts/imported/{case_id}/constant/polyMesh/`. After M6 lands, every imported case has a real OpenFOAM-runnable mesh.
- **Tier split** (per Kogami M6 clearance 2026-04-27 finding 1, 4 — read (iii)):
  - **M6.0 routine**: `meshing_gmsh/`, `mesh_imported.py` route, `MeshWizardPage.tsx`, gmsh+gmshToFoam pipeline, D4 dependency pin (`gmsh>=4.11,<4.13`) + CI smoke install matrix + macOS arm64 wheel posture. 50M power-mode hard cap; 5M beginner cap as soft warning until M6.0.1 calibration pass.
  - **M6.1 trust-core micro-PR**: `src/foam_agent_adapter.py` only — add `mesh_already_provided: bool` flag to skip `blockMesh` when `constant/polyMesh/` is populated. Narrow scope per Kogami M6 finding 4 (no case_kind dispatch change, no manifest-as-trust-core-input).
- **Sequencing rule** (per Notion-Opus advisory 2026-04-27 finding 1): **M6.0 implementation MUST NOT begin** until M5.0 (`4a0755e..23bcba6`) has Codex APPROVE recorded. "Should wait" is upgraded to "must wait" — refuses stacked governance debt.
- **Phase-Done gate** (per Notion-Opus advisory finding 3): **M6 cannot be marked Done while M6.1 is unmerged.** The trust-core micro-PR carve-out is a blocker on M6's Done flip, not on a future artifact's existence. Otherwise gmsh-meshed cases attempt `blockMesh` at M7-runtime and fail.
- **D6 calibration unlock** (per Notion-Opus advisory finding 4c): M6.0.1 may convert the 5M beginner soft-warning to a hard cap **only when telemetry covers N≥3 distinct STLs (mix of bundled fixtures + real user uploads)**, not single-PR data. Single-sample calibration is anecdote.
- **Strategic clearance**: `.planning/reviews/kogami/m6_kickoff_governance_clearance_2026-04-27/` (APPROVE_WITH_COMMENTS · 5 findings).
- **Revised kickoff spec**: `.planning/strategic/m6_kickoff/spec_v2_2026-04-27.md`.

### M7 — Fill-in M5.0 sHM stub + real OpenFOAM run on imported case + mesh budget tiering

- **Goal**: Fill the `system/snappyHexMeshDict.stub` that M5.0 wrote, run `snappyHexMesh` on imported geometry as a second mesh-engine option, then execute the real solver. Two-tier mesh budget: `mesh_mode="beginner"` (default) hard-cap 5M cells; `mesh_mode="power"` cap 50M. Single toggle inside Mesh Wizard, not a separate page.
- **Mesh-engine relationship**: M6 = gmsh path · M7 = snappyHexMesh path. Whether to introduce a per-case `mesh_engine` selector field is deferred to the M7 kickoff (when the second engine actually exists). M6 ships the gmsh path as the only engine.
- **D6 cap calibration**: M6.0 ships 5M as soft warning until empirical telemetry lands; M7 inherits whatever beginner cap M6.0.1 calibration produces.
- **MUST RESOLVE at M7 kickoff** (per Notion-Opus advisory 2026-04-27 finding 2 — the "homeless decision"): once M6 has shipped gmsh and M7 ships sHM, an imported case has **two** mesh backends. Who picks for a given case? UI selector? Heuristic on STL complexity (face count, watertight-ness)? Cell-budget-driven (gmsh for low-budget, sHM for high)? D8's "30 minutes end-to-end" implicitly assumes the user never has to choose — that assumption needs an explicit answer at M7 kickoff, not deferred to runtime.
- **Phase-Done gate** (per Notion-Opus advisory finding 3): **M7 cannot be marked Done while M5.1 is unmerged.** TrustGate hard-cap + `audit_package` filter must land before imported cases can produce verdicts in production — otherwise imported cases silently reach `PASS` verdicts despite having no gold-standard reference.
- **Phase-START prerequisite — Path A first-customer recruitment** (per Notion-Opus advisory finding 5 · user chose Path A at S-002): **M7 implementation MUST NOT begin until at least one stranger meeting the criteria in `.planning/strategic/path_a_first_customer_recruitment_2026-04-27.md` is named in that document's "Recruited" table with consent recorded.** If no stranger is named by the natural M7-kickoff trigger (M6.0 + M6.0.1 + M6.1 all shipped), either pause the M-sequence to focus on recruitment OR explicitly retreat to Path B via Pivot Charter Addendum 2 — default-drift into M7-without-stranger is forbidden.

### M8 — Beginner report v0 + Docker failure root-cause UI

- **Goal**: passive `beginner_report` listing (verdict warnings + case_quality deltas + identified sharp edges) + Docker failure root-cause surfacing in UI. Active anti-pattern detection (cellCount<1k / AR>100) deferred to M8.1 stretch.

### M5–M8 completion gate (binding · supersedes prior calendar framing)

Mandatory stranger dogfood: 1 CFD-literate non-project-member runs end-to-end (M5 import → M6 mesh → M7 run → M8 report) in target 30 min / cap 45 min. If blocked, the M5–M8 sequence is NOT done. **Replaces** the 60-day-window stranger dogfood framing implied by the kickoff spec (Kogami M5 clearance finding 3 resolution).

## Governance posture: downgraded (2026-04-26 standing rule)

Per Pivot Charter Addendum 1 + methodology v2.0 §10:

**Trust-core (Codex审查 mandatory, DEC mandatory for >5 LOC changes)**:
- `knowledge/gold_standards/`
- `src/auto_verifier/`
- `src/convergence_attestor.py`
- `src/audit_package/`
- `src/foam_agent_adapter.py` (line-B's writes; main-line treats as read-only)

**Routine path (no DEC, no round-2 Codex iteration, direct commit to main)**:
- `ui/backend/routes/`, `ui/backend/services/` (except trust-core wrapping)
- `ui/backend/schemas/`, `ui/backend/tests/`
- `ui/frontend/src/`
- `scripts/check_*` (governance hooks)

**Notion sync**: only on DEC landing or post-incident retro. No daily control-plane sync.

## Line-A / Line-B isolation contract (硬约束)

| Surface | line-A writes? | line-A reads? | line-B writes? |
|---|---|---|---|
| `ui/backend/services/wizard_drivers.py` | ✅ | ✅ | ❌ |
| `ui/backend/services/run_history.py` (NEW) | ✅ | ✅ | ❌ |
| `ui/frontend/src/pages/workbench/**` | ✅ | ✅ | ❌ |
| `ui/backend/tests/**` | ✅ | ✅ | ❌ |
| `src/foam_agent_adapter.py::FoamAgentExecutor.execute()` | ❌ | ✅ (public surface only) | ✅ |
| `src/foam_agent_adapter.py::_generate_*` / `_emit_*` (internals) | ❌ | ❌ | ✅ |
| `knowledge/gold_standards/**` | ❌ | ✅ | ✅ |
| `src/auto_verifier/`, `src/convergence_attestor.py` | ❌ | ✅ | ✅ |
| `reports/{case_id}/runs/{run_id}/` (NEW) | ✅ | ✅ | ❌ |
| `reports/phase5_fields/` (Phase-7 territory) | ❌ | ❌ | ✅ |

**Active line-B branches** (informational, do not touch from main-line):
- `dec-v61-058-naca`, `dec-v61-059-pc`, `dec-v61-060-rbc`, `dec-v61-062-naca-cgrid`, `dec-v61-063-flat-plate`, `dec-v61-063-naca-transition`
- `feat/c3a-ldc-gold-anchored-sampling`, `feat/c3b-naca-surfaces`, `feat/c3c-impinging-jet-wallheatflux`

## 60/90-day extensions (post-M4, not in current scope)

- 60-day: 3 anchor case 闭环 (LDC + cylinder + NACA-or-DHC) + run-comparison (diff two runs side-by-side) + project/workspace minimal concept
- 90-day: ~~import/register your own OpenFOAM case + full closed-loop on user-supplied geometry + Docker failure root-cause UI~~ — **graduated 2026-04-27 into M5–M8 sequence above** (M5 import / M6 gmsh / M7 real run + mesh tiering / M8 beginner report + Docker root-cause). PyPI / external-pilot / commercialization revisit remains 90-day item, deferred until after M8.

## Closed (do not reopen)

### Workbench arc — COMPLETE 2026-04-25
- Stages 1-6 + Stage 8a (Onboarding Wizard, mock solver) + Stage 8b prep (SolverDriver protocol)
- Tier-B(1) LDC tolerance probe, Tier-B(2) wizard interaction tests, Tier-B(4) Codex-verified cadence hook
- 4-round Opus 4.7 review (R1 → R4) ended at stop criterion: APPROVE_WITH_COMMENTS 0.76, Δ +0.04 ≤ 0.05 threshold
- Polish bundles: round-2 P0+P1, round-3 governance polish (F11+F5+F18+F10+F3+F8), RETRO-V61-002 lite (F2+F4+F9+F13)

### v6.1 W1 governance arc — COMPLETE 2026-04-25
- G-1..G-9 closed (Pivot Charter, Charter freeze, Gov1 Version Policy v1, Spec Promotion Gate, ADR-001 import enforcement, case-profile risk_flags, retro 5th trigger, state stamp, Opus W2 phase transition)
- ADR-002 ACCEPTED, methodology v2.0 ACTIVE
- 37+ DECs landed, counter ~42

### Phase 1-8 — COMPLETE 2026-04-13 → 2026-04-22
- Full archive in `.planning/STATE.md` Phase Status sections (lines 64-1333)
- 10-case whitelist: 8 PASS / 2 HOLD; convergence attestor + 5 hard gates active
- Audit package L4 spec landed; HMAC signing + byte-reproducibility enforced

## Deferred (post-M4 reactivation candidates, not blocking main-line)

- **PR-5 Part A nit closure** (Q2 exit_code reshape, Q3 schema_version, Q5 F3 test verify, Q6 retro entry, Q7 EN fallback, Q12 strict mode flag) — workbench arc post-mortem nits; not main-line
- **W4 hard-fail toggle PR** (Task #86, A13 watchdog + A18 .jsonl rollback counter) — wait for genuine dogfood signals (≥30 CI runs / ≥15 cross-track commits / 0 violations / escape <20% per ADR-002 §5)
- **ADR-001 Codex R1 CHANGES_REQUIRED fix** (4fd9215 doc/config mismatch + filesystem-read coverage overstatement) — original author `claude-opus47-app` owns; main-line not blocking
- **Stage 8c / Stage 9 / 50-case expansion** — out of 30/60/90 scope
- **PyPI / external-customer pilot / commercialization** — post-M4 only; `docs/product_thesis.md` reframed as `status: candidate-future-narrative`
- **Spec promotion (6 specs)** — methodology framework exists; promotion is governance ceremony, not main-line
- **Retro cadence at counter=40** — already crossed without retro; counter is now telemetry-only per RETRO-V61-001 risk-tier-driven model
