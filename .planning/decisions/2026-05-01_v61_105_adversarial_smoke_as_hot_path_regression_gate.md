---
decision_id: DEC-V61-105
title: Adversarial smoke as hot-path regression gate (RETRO-V61-053 executable_smoke_test risk_flag operationalized)
status: Proposed (2026-05-01 · authored under user direction "全权授予你开发，全都按你的建议来" + "深度规划开发方向，优化要显著（可以跨大步）" after the 2026-04-30/05-01 adversarial arc found 9 critical/high pipeline defects, several POST-R3)
authored_by: Claude Code Opus 4.7 (1M context)
authored_at: 2026-05-01
authored_under: tools/adversarial/results/iter01-06_findings.md (full 6-iteration arc) + 9 defect-fix commits b8053f9..27152d7 + smoke-runner commit d414367
parent_decisions:
  - DEC-V61-103 (BC mapper Phase 1 — produced the per-case Query-param surface this DEC's smoke runner exercises)
  - DEC-V61-104 (interior-obstacle topology — deferred; iter01 reclassified `physics_validation_required` and skipped by this DEC's smoke until V61-104 ships)
  - RETRO-V61-053 (post-R3 defect addendum 2026-04-24 introduced `executable_smoke_test` risk_flag — this DEC operationalizes that flag)
  - RETRO-V61-001 (risk-tier triggers — defines when Codex review is mandatory; this DEC adds smoke-runner pre-push gate as second necessary layer)
parent_artifacts:
  - tools/adversarial/run_smoke.py (the runner this DEC formalizes)
  - tools/adversarial/README.md (methodology + per-case status semantics)
  - scripts/git_hooks/pre_push_adversarial_smoke.sh (opt-in pre-push hook)
  - tools/adversarial/cases/iter01..iter06/intent.json (per-case smoke_runner blocks)
  - ui/backend/services/case_solve/solver_runner.py (defect 9 fix — end-time-aware convergence; without this the smoke runner false-FAILs on short cases)
  - ui/backend/routes/case_solve.py (per-case Query params — without this the smoke runner can't pass per-case stable solver settings)
counter_impact: +1 (autonomous_governance: true · methodology DEC, formalizes existing infrastructure rather than adding new architectural surface)
self_estimated_pass_rate: 80% (small surface · methodology + opt-in pre-push hook + 9 fixed defects already validate the approach · 2 known follow-ups documented as scope §6)
codex_tool_report_path: (TBD — review of commits 27152d7 + d414367 in flight)
notion_sync_status: synced 2026-05-01 (https://app.notion.com/p/353c68942bed81e4b4c1ee3f8eebb420)
---

# Why now

The 2026-04-30/05-01 adversarial arc fixed **9 critical/high pipeline defects** across **6 case classes**. Several were **POST-R3 defects** — Codex APPROVE'd code that failed at runtime:

- **Defect 8** (iter06 SYMMETRY constraint type) — Codex round 1 APPROVE'd the BC mapper changes; defect 8 was discovered when the case was actually solved end-to-end and icoFoam exited with FATAL IO ERROR. Fix took 2 Codex rounds (a6f40f2 + e1559b9).
- **Defect 9** (end-time-aware convergence) — Codex round 1 APPROVE'd defect-8 and the smoke runner; defect 9 emerged when the smoke runner started passing per-case end_time overrides shorter than the LDC-hardcoded 1.99 threshold. Fix landed in 27152d7.

Both defects validate RETRO-V61-053's `executable_smoke_test` risk_flag: **static review is necessary but not sufficient**. Live runtime exercises are needed to catch a class of bugs that only manifest under real solver execution.

`tools/adversarial/run_smoke.py` is the executable smoke. This DEC formalizes its role as the second necessary layer (with Codex code review) for backend hot-path PRs — and lays out a 12-month roadmap for closing the still-open methodology gap.

# Decision

## D-1 · Smoke runner is canonical convergence-regression gate

`tools/adversarial/run_smoke.py` is the **canonical executable** that asserts the cfd-harness pipeline (import → mesh → BC → solve) still produces convergent solutions for the validated case classes.

Per-case status semantics (declared in each case's `intent.json` `smoke_runner` block):

| status | semantics |
|---|---|
| `converged` | full pipeline must complete and `last_continuity_error` indicates convergence |
| `manual_bc_baseline` | uses author_dicts.py / a case-specific driver, not from_stl_patches mode — runner skips |
| `physics_validation_required` | converges numerically at smoke scale but physics is wrong (e.g. iter01 interior obstacle); needs analytical comparator, not smoke convergence |
| `expected_failure_v61_104` | known to fail (divergence, not wrong-physics) until DEC-V61-104 ships |

## D-2 · Pre-push hook is mandatory for backend hot-path PRs

`scripts/git_hooks/pre_push_adversarial_smoke.sh` runs the smoke suite when the push includes commits touching:

```
ui/backend/services/(meshing_gmsh|case_solve|geometry_ingest)
ui/backend/routes/(import_geometry|mesh_imported|case_solve)
```

**Mandatory**: developers must symlink the hook into `.git/hooks/pre-push` for backend work. The current opt-in install is a transitional state; D-3 below is the permanent gate.

**Bypass protocol**: `CFD_SMOKE_OVERRIDE=1 git push` for emergencies; record the rationale in the commit body or in the next RETRO. Bypasses are tracked.

## D-3 · CI integration is a follow-up commitment

CI (`.github/workflows/ci.yml`) currently runs in MOCK mode (no docker). Adding the smoke suite requires:

1. Pre-built `cfd-workbench/openfoam-v10:amd64` image published to ghcr.io (4.38GB image — too big to build per-PR, must cache)
2. Backend startup as a CI service (`uvicorn` background process)
3. Smoke suite invocation on PR

This is scoped as **DEC-V61-105 follow-up Phase 2** (separate landed work, ~2 weeks effort). The pre-push hook covers the gap until then.

## D-4 · Adding a new case class is a methodology contribution, not an ad-hoc commit

When the adversarial loop runs into a new defect, the case that exposed it becomes a regression case. Workflow:

1. Add `tools/adversarial/cases/iter<N>/` with `geometry.stl` + `intent.json` (with `smoke_runner` block)
2. Validate: `python tools/adversarial/run_smoke.py --filter iter<N>`
3. Document: add findings to `tools/adversarial/results/iter<N>_findings.md`
4. Commit case + findings together; reference the originating defect

# Scope

## In scope (this DEC)

- The smoke runner (`tools/adversarial/run_smoke.py`) ✅ shipped d414367
- Per-case status semantics ✅ shipped d414367 + intent annotations
- Pre-push hook script ✅ shipped d414367
- Methodology documentation (`tools/adversarial/README.md`) ✅ shipped d414367
- Defect 9 fix enabling per-case smoke params ✅ shipped 27152d7

## Out of scope (DEC-V61-105 Phase 2 follow-ups)

- **Phase 2.1 · CI integration** — publish openfoam image, add CI job, ~2 weeks
- **Phase 2.2 · Analytical comparator runner** — for `physics_validation_required` cases (iter01 interior obstacle and future cases needing physics validation); compare numerical solution to known analytical results (Poiseuille, Couette, lid-driven cavity at known Re)
- **Phase 2.3 · Parametric case generator** — instead of hand-crafting each iter case, build a tool that takes a parametric description (e.g., "rotated channel of length L, width W, Euler rotation R") and emits a valid adversarial case + intent. Could systematically explore the geometry space.

## Forward-looking · Phase 2.4 (Codex deferred findings) — defensive hardening

Two Codex post-merge findings deferred during the arc are still open:
- R2 MED #2: gmsh assumes 3-node tris; defensive check for mixed element types
- R2 LOW/MED #4: malformed face-points raise IndexError before the fallback path

Both forward-looking; current pipeline only generates 3-node tris, so neither is an active bug. Should land before Phase 2.3 (parametric generator may produce more-exotic meshes).

# Verification

`python tools/adversarial/run_smoke.py` (clean run): **4 PASS · 2 SKIP · 0 FAIL** in ~30s wall time.

Per-case results:
- iter01: SKIP (physics_validation_required)
- iter02: PASS (cells=6670, cont_err=7.74e-08, smoke 6.46s)
- iter03: SKIP (manual_bc_baseline, no geometry.stl)
- iter04: PASS (cells=4274, cont_err=4.19e-09, smoke 8.05s)
- iter05: PASS (cells=2972, cont_err=8.83e-09, smoke 6.54s)
- iter06: PASS (cells=5295, cont_err=3.09e-09, smoke 7.56s)

# Risks

| risk | severity | mitigation |
|---|---|---|
| Smoke caps too aggressive — divergence-detection misses slow-developing instabilities | medium | Per-case override of cap via `smoke_runner.solver_overrides` (Phase 2.4) |
| Pre-push hook is opt-in — developers can skip by not symlinking | medium | D-3 CI integration makes the gate non-bypassable; transitional period max 2 weeks |
| Smoke runner has no concurrency lock — parallel runs of `run_smoke.py` would race on case_id allocation | low | Document single-runner-per-backend; CI integration solves naturally |
| `physics_validation_required` becomes a dump bucket for "we don't know how to test this" | medium | Each such case must reference a future analytical-comparator commit (Phase 2.2 scope tracker) |
| Adding a new case class without a smoke_runner block — runner falls through to default `converged` | low | Document in README + `_DEFAULT_CONFIG` is `converged` so missing block surfaces as test data |

# Cross-references

- RETRO-V61-053 (executable_smoke_test risk_flag introduced 2026-04-24) — this DEC operationalizes that flag
- RETRO-V61-001 (risk-tier triggers + per-PR Codex baseline) — pre-push smoke is the second necessary layer atop Codex
- DEC-V61-103 (BC mapper Phase 1) — produced the route surface the smoke exercises
- DEC-V61-104 (interior-obstacle topology, deferred) — iter01 is its adversarial canary

# Codex round chain (this DEC's lineage)

| arc | round | verdict | summary |
|---|---|---|---|
| Defect 7 (iter05 compound names) | R1 | APPROVE | direct fix |
| Defects 5+6+7 closure | R2 | CHANGES_REQUIRED | area-weighted voting + canonical-token scan |
| Defect 5+7 follow-up | R3 | APPROVE_WITH_COMMENTS | both R2 closed |
| Defect 8 (iter06 symmetry) | R4 | CHANGES_REQUIRED | regex hazard + TOCTOU |
| Defect 8 closure | R5 | APPROVE_WITH_COMMENTS | both R4 closed |
| Defect 9 + smoke runner (this DEC) | R6 | (in flight) | TBD |
