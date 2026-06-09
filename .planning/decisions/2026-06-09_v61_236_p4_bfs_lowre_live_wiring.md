---
decision_id: V61-236
title: P4 V71B-FOLLOWUP-1 item 1 — live execute()/TaskRunner gate wiring for the wall-RESOLVED low-Re kOmegaSST backward_facing_step anchor (the WIRING slice · runnable-coverage STAYS 3)
status: Proposed
parent_dec: V61-235 (the V&V-anchor slice this wires — gold + gate + extractor + frozen LIVE probe + advisor) · V61-234 (the wedge WIRING precedent: whitelist + dispatch + TaskRunner branch land in the wiring slice, NOT the V&V slice)
sibling_decs: V61-235 (the immediately prior V71.B V&V-anchor slice — this is its deferred live-wiring half, exactly as DEC-V61-234 was the live-wiring half of DEC-V61-233) · V61-088 (pre-implementation surface-scan discipline this slice followed)
phase: P4 (compressible/supersonic vertical) · V71B-FOLLOWUP-1 item 1 — the low-Re BFS live-wiring slice (turbulence-treatment breadth · NOT a coverage flip)
autonomous_governance: true
confidence: high
kogami_opt_in: false (sub-DEC class · live-wiring of an already-validated V&V anchor on a cell already PR; the binding gate is the Codex round-cap=3 chain on the adapter dispatch / runner / TaskRunner branch / whitelist surface. Not a charter trigger; user may invoke Kogami at will per V133.)
round_cap: 3
codex_review_relay: 86gs gpt-5.4 xhigh (governance baseline; codex review --commit)
codex_verdict: PENDING
codex_tool_report_path: reports/codex_tool_reports/v61_236_p4_bfs_lowre_wiring_report.md
notion_sync_status: retired (Notion deprecated per sponsor 2026-06-09 — no DEC sync)
touches_shared_dec: src/foam_agent_adapter.py (NEW _docker_run_of11_rm fresh --rm OF11 helper · NEW _execute_backward_facing_step_lowre persistent-output runner · execute() identity-keyed dispatch short-circuit) · src/task_runner.py (re-added _verify_bfs_lowre + the 4c identity-keyed verification branch removed in DEC-V61-235 R1) · knowledge/whitelist.yaml (the backward_facing_step_lowre specialized_gate_anchor entry — deferred from V61-235, lands here WITH its verification path) · tests/p4/test_bfs_lowre_wiring.py (NEW offline dispatch/collision/whitelist-load/verify regression) · tests/p4/test_bfs_lowre_live.py (NEW opt-in live e2e) · reports/showcase_aero/_v71b_bfs_lowre_backend_e2e/ (NEW frozen backend-launched evidence + tamper manifest) · .planning/cfd_capability_matrix.md (within-cell wiring note · counts UNCHANGED) · .planning/followups/v71b_bfs_lowre_live_wiring_deferred.md (item 1 marked LANDED · item 2 still open)
surface_scan: DEC-V61-088 compliant (V71B-FOLLOWUP-1 tracker is the ROADMAP item + grep of backward_facing_step_lowre / _execute_supersonic_wedge / _docker_run_esi_rm surface; disposition: extend — the wedge's DEC-V61-234 runner/dispatch/whitelist pattern is reused structurally for the low-Re BFS, no parallel-new abstraction introduced)
date: 2026-06-09
---

# DEC-V61-236 · P4 V71.B low-Re BFS live-wiring (V71B-FOLLOWUP-1 item 1)

## Context

DEC-V61-235 landed the **V&V-anchor** half of the wall-RESOLVED low-Re kOmegaSST
`backward_facing_step` (Re_H=5000, y+<1 integrate-to-wall): the gate
(`src.bfs_lowre_gate`), gold (Xr/H=6.26 inherited blended anchor ±10%), the shared
reattachment-floor mask SSOT (`src.bfs_floor_region`), the wall-shear extractor
(`src.bfs_lowre_extractor`), a frozen LIVE probe, offline gate tests, and the
`low_re_komegasst_trigger_advisor`. It deliberately did **NOT** wire the live
execution paths — mirroring the wedge arc, where DEC-V61-233 landed the V&V
validation and DEC-V61-234 (a separate slice) wired the workbench backend. Codex R0
on V61-235 flagged the two live-path gaps; both were deferred to V71B-FOLLOWUP-1.

This slice lands **item 1**: the gate live-wiring — so a workbench-launched solve of
the low-Re anchor flows through `execute()` and is verified by the Control-plane gate
on REAL solver output (not the frozen fixture). **Item 2** (advisor live-caller
wiring through `/api/ai-review`) stays open — it adds an extraction to a top-level
route surface (its own DEC-V61-088 surface-scan + review) and is independent of this
slice's value.

**The load-bearing distinction (unchanged from V61-235, the anti-overclaim guardrail):**
the wedge's wiring slice (DEC-V61-234) FLIPPED runnable-coverage 2→3 because
`rhoCentralFoam` is a genuinely NEW compute type. **This slice does NOT flip
anything** — the low-Re BFS is the SAME incompressible-RANS-steady solver as the
existing BFS/airfoil anchors, distinguished from the high-Re sibling purely by the
resolved near-wall mesh. **Runnable-coverage STAYS 3.** This is turbulence-TREATMENT
breadth becoming runnable-through-the-backend, NOT a new compute type.

## Decision

Wire the validated low-Re BFS anchor through the workbench execution backend, keyed on
case IDENTITY, with a persistent output the Control gate can read — and land the
deferred whitelist entry WITH its verification path (never selectable-but-unverifiable).

### What changed

1. **Fresh-`--rm` OF11 runner** (`src/foam_agent_adapter.py`). `_docker_run_of11_rm`
   (a structural clone of the wedge's `_docker_run_esi_rm`) bind-mounts the host
   work_dir at `/work`, sources `/opt/openfoam11/etc/bashrc`, and runs the command in
   a **fresh** `client.containers.run(...)` container removed in `finally` — disturbing
   **no running container** (the persistent `cfd-openfoam`/`of11_run`/`of11_probe` are
   never touched). `OF11_FOUNDATION_IMAGE = "openfoam/openfoam11-paraview510"`.

2. **Persistent BFS-lowre runner** (`_execute_backward_facing_step_lowre`). Creates a
   `tempfile.mkdtemp(prefix="backward_facing_step_lowre_", dir=self._work_dir)` and —
   critically — has **NO `finally: rmtree`** (the wedge persistence contract; the
   generic `execute()` path DOES rmtree, which is why this runner short-circuits BEFORE
   it). It FORCES `wall_treatment='resolved'` + `turbulence_model='kOmegaSST'` via
   `dataclasses.replace` (so a Notion spec with `boundary_conditions={}` still solves
   the resolved case), generates the case, runs `blockMesh && checkMesh && foamRun
   -solver incompressibleFluid && foamToVTK -latestTime -noZero -allPatches
   -noFaceZones`, derives `proof/floor_faces.csv` via the shared mask
   (`src.bfs_lowre_extractor.write_floor_faces_csv`, latest VTK by NUMERIC timestep —
   the DEC-V61-235 R1 lexical-sort lesson), extracts the QoIs, and returns an
   `ExecutionResult(success=True, is_mock=False, raw_output_path=<persistent dir>)`.
   The runner imports ONLY the Execution-plane extractor — NEVER the Control gate (no
   Execution⇄Control cycle; four-plane import-linter KEPT).

3. **Identity-keyed `execute()` dispatch.** A short-circuit keyed on
   `task_spec.name == 'backward_facing_step_lowre'` (NOT `geometry_type`, which
   collides with the high-Re BFS — the DEC-V61-235 R1 collision lesson) routes to the
   dedicated runner BEFORE the persistent-container connect. The high-Re sibling
   (`name='backward_facing_step'`, SAME geometry_type) is proven NOT to route here.

4. **TaskRunner verification branch** (`src/task_runner.py`). The `_verify_bfs_lowre`
   method + the `4c` branch (both REMOVED in DEC-V61-235 R1 because they ran against
   the executor's deleted temp dir) are re-added — now correct because the runner above
   produces a **persistent** `raw_output_path`. The branch is gated on the same case
   identity + `exec_result.success` + `attestation.overall != ATTEST_FAIL`, and
   `_verify_bfs_lowre` fail-closes (passed=False) on a missing `raw_output_path` —
   never a fabricated pass.

5. **Whitelist registration** (`knowledge/whitelist.yaml`). The
   `backward_facing_step_lowre` `case_kind: specialized_gate_anchor` entry (deferred
   from V61-235 per Codex R1 P1 — a selectable entry without a verification path is
   exposed-but-unverifiable) lands HERE, atomically with the dispatch + branch above.
   `id == name == 'backward_facing_step_lowre'` (the identity-keying contract);
   `load_gold_standard` → None → the specialized gate path runs.

### Measured result (frozen backend-e2e `reports/showcase_aero/_v71b_bfs_lowre_backend_e2e/`)

`foam_agent_adapter.execute(TaskSpec(name='backward_facing_step_lowre'))` launched a
REAL OF11 `foamRun -solver incompressibleFluid` solve in a fresh `--rm` container
(~63 s, `is_mock=False`), and the Control-plane gate PASSED on the backend output:

| Metric | Value | Bar | Verdict |
|---|---|---|---|
| reattachment Xr/H (wall-shear zero-crossing) | **5.8812** | 6.26 ±10% → [5.634, 6.886] | PASS (−6.05%) |
| first-cell y+ max, reattachment floor (119 faces) | **0.0661** | < 1 (resolved) | PASS |
| wall-shear pos→neg crossings | 1 | == 1 | PASS |

**Byte-for-byte reproducibility of the V&V probe (the strong result):** the backend
`execute()` solve produced a surface VTK **byte-identical** to the DEC-V61-235
hand-typed probe — `allPatches_3000.vtk` SHA256 `fd25bfce…` on BOTH. The OF11
incompressibleFluid solve of this adapter-generated case is deterministic: the
workbench backend reproduces the V&V probe's solver output bit-for-bit. The derived
floor-face data rows are identical; only a cosmetic header-comment path label differs.

## Four-question gate

- **Q1 LLM offline?** YES — the runner shells `blockMesh/checkMesh/foamRun/foamToVTK`
  and the extractor/gate are pure Python over the solver's own wallShearStress/yPlus
  field output; zero model calls anywhere in the dispatch → solve → extract → verify
  chain.
- **Q2 verdict artifacts-based?** YES — the TaskRunner branch runs
  `gate_bfs_lowre_against_gold` on the **persistent** `raw_output_path` (the real
  allPatches VTK the backend solve produced), a boolean conjunction over
  `ResultComparator` + three independent hard gates. No verdict is derived from the
  spec or from a fixture.
- **Q3 TrustGate explicit + fail-closed?** YES — tolerance 0.10 + y+<1 declared in the
  gold/gate; `_verify_bfs_lowre` fail-closes (passed=False, honest summary) on a
  missing `raw_output_path`; the runner `_fail`s with the persistent path on any
  non-zero solver exit; the offline regression proves the high-Re sibling does NOT
  route here (no silent mis-dispatch) and a missing path never fabricates a pass.
- **Q4 advisory-not-driver?** YES — the gate reports PASS/FAIL into the trust report;
  it never auto-decides engineering. (The advisor's live-caller wiring — item 2 —
  stays out of scope; this slice touches only the gate path.)

## Explicitly OUT of scope (V71B-FOLLOWUP-1 item 2 stays open)

- **Advisor live-caller wiring** (Codex R0 P2 on V61-235). `low_re_komegasst_trigger_advisor`
  is registered + dispatch-tested + behaviorally firing on the E21 config (its stated
  V71.B scope — closing the V69.2 KNOWN_F_NEW eval skip — is met), but no production
  caller (`/api/ai-review`, `/api/ai-diagnose`) populates `low_re_komegasst_inputs`
  yet. Wiring it adds a `RASModel` + first-cell-y+ extraction to a top-level route
  surface → its own DEC-V61-088 surface-scan + review. Disclosed, not hidden; tracked
  in `.planning/followups/v71b_bfs_lowre_live_wiring_deferred.md` (item 2, still open).
- A parametric resolved-BFS generator beyond the validated `case_definition/` (the
  adapter renders the same frozen-validated graded mesh; the gate stays byte-faithful).
- Spalart-Allmaras / RSM / LES turbulence-model anchors (V71.C+).

## Codex review trail (round-cap = 3 · 86gs gpt-5.4 xhigh · `codex review --commit`)

Full trail: `reports/codex_tool_reports/v61_236_p4_bfs_lowre_wiring_report.md`.

- **R0** (commit 462902e) — **CHANGES_REQUIRED**: 1 P1 + 1 P2, both production-path
  reachability (the runtime-emergent class the cross-family review exists to catch).
  - **P1**: `pyvista` (imported lazily by `bfs_lowre_extractor.write_floor_faces_csv`
    for the live VTK read) was UNDECLARED in `pyproject.toml`/`uv.lock` — so
    `backward_facing_step_lowre` was not runnable end-to-end on a clean env / CI; the
    runner's `except` did not catch the resulting `ImportError`.
  - **P2**: the dispatch keyed ONLY on `name=='backward_facing_step_lowre'`; a
    display-title caller (`NotionClient._parse_task` sets `name` from the page title,
    `boundary_conditions={}`) would fall through to the high-Re branch.
  - **R1 fix**: (P1) declared `pyvista>=0.44` in the `cfd-real-solver` extra (the
    `docker` precedent; offline gate-replay is stdlib so CI stays pyvista-free) +
    regenerated `uv.lock` (pyvista 0.48.4 + vtk 9.6.2) + added an explicit
    `except ImportError` → actionable BLOCK. (P2) broadened the dispatch to
    `name==slug OR boundary_conditions.wall_treatment=='resolved'` (strictly safer; no
    high-Re false-positive) + documented that the display-title concern is the RETIRED
    + already-dormant Notion path (`run_all`→`list_pending_tasks` raises
    NotImplementedError → `[]`); the supported whitelist/batch + direct paths reach the
    wiring. +1 routing test, fixed the high-Re collision test to a realistic
    wall-function spec. Regression: tests/p4 67 passed/2 skipped · full suite 2085
    passed/5 skipped · import-linter 5 kept/0 broken · high-Re BFS byte-identical.

(Trail appended as rounds complete; `codex_verdict` frontmatter flips to APPROVE +
`status: Accepted` + the capability-matrix cell flips to DONE on close. Per the
DEC-V61-235 test-red-team P1-1 lesson, the matrix reads "LANDED · pending Codex
APPROVE" until then.)
