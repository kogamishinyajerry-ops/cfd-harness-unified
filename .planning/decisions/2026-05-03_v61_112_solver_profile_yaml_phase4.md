---
decision_id: DEC-V61-112-Phase4
title: Solver-profile YAML migration · Phase 4 — channel pimpleFoam profile (V61-101 setup_channel_bc inline template extraction · final phase)
status: Accepted (2026-05-03 · Codex pre-merge 6-round chain APPROVE on commit 2fc58e9; chain report at reports/codex_tool_reports/v61_112_phase4_r1_r6_chain.md; user 2026-05-03 autonomous-mode mandate + explicit "start V61-112 Phase 4" follow-up covers acceptance flip)
codex_tool_report_path: reports/codex_tool_reports/v61_112_phase4_r1_r6_chain.md
authored_by: Claude Code Opus 4.7 (1M context)
authored_at: 2026-05-03
authored_under: V61-112 Phase 3 acceptance closure (commit 3736839 · counter 69→70) explicitly identifies Phase 4 (channel pimpleFoam migration) as the final phase in the V61-112 series
parent_decisions:
  - DEC-V61-112-Phase3 (icoFoam LDC profile · Accepted commit 3736839 · supplied the cross-module-error-contract translation pattern + module-level load_profile import)
  - DEC-V61-112-Phase2 (pimpleFoam STL profile + per-solver name_pad · Accepted commit 528bc6b · this DEC reuses the Phase 2-extended schema with one further extension)
  - DEC-V61-101 (channel mesh + setup_channel_bc · supplied the channel pimpleFoam template authored INLINE in `bc_setup.py:806-893` — extraction target for this Phase)
  - DEC-V61-107 + DEC-V61-097.5 (Codex review history that produced the channel pimpleFoam fvSchemes choices: `divDevReff` term + Gauss-linear convection + orthogonal laplacian/snGrad)
  - RETRO-V61-001 (risk-tier · multi-file backend (case_solve service surface) + new config schema profile + cross-module error-contract refactor = mandatory Codex pre-merge)
parent_artifacts:
  - reports/codex_tool_reports/v61_112_phase3_r1_r2_chain.md (Phase 3 2-round APPROVE chain · NEW methodology lesson "cross-module error contracts" applied directly to Phase 4)
  - ui/backend/services/case_solve/bc_setup.py:806-893 (V61-101 inline channel pimpleFoam controlDict + fvSchemes + fvSolution — extraction targets for this Phase)
counter_impact: +1 (autonomous_governance: true · final architectural foundation in V61-112 series · no external gate required)
self_estimated_pass_rate: 55% (calibrated between Phase 1+2's 50% baseline and Phase 3's 60% achievement. Phase 4 introduces ONE schema extension (max_delta_t_value: float | None for fixed-cap maxDeltaT distinct from "follows caller delta_t"), so it's not a pure schema-reuse migration like Phase 3. The cross-module error-contract pattern from Phase 3 R1 P2 is applied PROACTIVELY (BCSetupError wrapping at the setup_channel_bc call site) to avoid a repeat finding. Expect 2-3 rounds; possible P2 on the new max_delta_t_value field validation or on subtle byte-identity gaps from the channel template's int-vs-float literals (writeInterval=1 INT vs STL pimpleFoam's 1.0 FLOAT).)
notion_sync_status: pending (Notion MCP offline this session; sync queued for next online window)

# DEC-V61-112 Phase 4 · channel pimpleFoam profile (final phase)

## Why now

V61-112 Phase 3 closed 2026-05-03 with the LDC icoFoam profile. Phase 3 acceptance closure explicitly identifies Phase 4 (channel pimpleFoam) as the final phase in the V61-112 series. User explicit direction "start V61-112 Phase 4" authorizes immediate execution.

V61-101 landed `setup_channel_bc` (channel mesh + named-patch BC) with channel-specific pimpleFoam inline templates at `bc_setup.py:806-893`. The channel pimpleFoam differs from both V61-107.5 STL pimpleFoam (Phase 2) AND from V61-097 LDC icoFoam (Phase 3) in important ways — it's a DISTINCT 4th profile, not a duplicate of either.

## Decision

Author `ui/backend/services/case_solve/solver_profiles/profiles/channelPimpleFoam.yaml` extracting the V61-101 inline channel pimpleFoam templates. Rewire `_author_channel_dicts` (in `bc_setup.py`) inline `w(...)` calls to delegate via `load_profile("channelPimpleFoam").render_*()`, mirroring Phase 3's LDC pattern (no helper layer; direct inline-template rewire) plus Phase 3 R1 P2 cross-module error-contract pattern (BCSetupError translation applied proactively).

### Channel pimpleFoam vs STL pimpleFoam (Phase 2) vs LDC icoFoam (Phase 3)

| Aspect | LDC icoFoam (P3) | STL pimpleFoam (P2) | Channel pimpleFoam (P4) |
|--------|------------------|---------------------|-------------------------|
| application | icoFoam | pimpleFoam | pimpleFoam |
| control_block_name | PISO | PIMPLE | PIMPLE |
| solvers | 3 (p, pFinal, U) | 4 (p, pFinal, U, UFinal) | 4 (p, pFinal, U, UFinal) |
| ddt | Euler | Euler | Euler |
| div(phi,U) | Gauss linear | Gauss linearUpwind grad(U) | **Gauss linear** (no linearUpwind) |
| div(nuEff·dev2(grad(U)))) | absent (icoFoam-only) | Gauss linear | **Gauss linear** (pimpleFoam routes through divDevReff regardless of laminar) |
| laplacian | Gauss linear orthogonal | Gauss linear corrected | **Gauss linear orthogonal** (channel mesh structured) |
| snGrad | orthogonal | corrected | **orthogonal** |
| writeControl | runTime | runTime | runTime |
| writeInterval | 0.5 (float) | 1.0 (float) | **1 (int)** |
| adjustTimeStep | omit | yes | yes |
| maxCo | omit | 0.5 | 0.5 |
| maxDeltaT | omit | follows caller delta_t | **0.05 fixed cap** |
| iteration_floor | absent | absent | absent |

Channel pimpleFoam is closer to STL pimpleFoam in solver mechanics (PIMPLE block, 4-solver shape, pimpleFoam application) but closer to LDC icoFoam in fvSchemes (Gauss linear convection, orthogonal laplacian/snGrad — channel mesh is structured/orthogonal, not tetrahedral STL). It needs a SEPARATE profile.

### Schema extension required: `max_delta_t_value: float | None = None`

Channel pimpleFoam uses `maxDeltaT 0.05;` — a FIXED cap, distinct from both:
- Phase 3 icoFoam: maxDeltaT omitted (`max_delta_t_follows_delta_t: false`, no value field)
- Phase 2 STL pimpleFoam: maxDeltaT follows caller delta_t (`max_delta_t_follows_delta_t: true`)

New schema field `max_delta_t_value: float | None = None`:
- `None` → fall through to `max_delta_t_follows_delta_t` (Phase 2 backward-compat)
- numeric → render `maxDeltaT {value};` directly (Phase 4 channel use case)

Migration impact:
- Phase 1 simpleFoam.yaml: omits both fields (current behavior — maxDeltaT line absent)
- Phase 2 pimpleFoam.yaml: continues using `max_delta_t_follows_delta_t: true` (unchanged)
- Phase 3 icoFoam.yaml: omits both (current behavior — maxDeltaT line absent)
- Phase 4 channelPimpleFoam.yaml: uses `max_delta_t_value: 0.05` (new field)

### Cross-module error-contract pattern applied PROACTIVELY

Phase 3 R1 P2 surfaced that `load_profile()` failures bypass the service module's BCSetupError envelope. Phase 3 fixed at `_author_dicts` (LDC). Phase 4 applies the SAME pattern to `_author_channel_dicts` proactively — wrap `load_profile("channelPimpleFoam")` in `try/except` for `(ProfileNotFoundError, ProfileSchemaError)` → `raise BCSetupError(...) from exc`. Avoids a repeat Codex finding.

## Acceptance criteria

§1 Phase 4 channelPimpleFoam.yaml byte-identical to V61-101 inline output for the channel default case parameters (no caller args; literals from inline). Verified via golden-snapshot constants embedded in `test_solver_profiles.py`.

§2 Phase 1 + 2 + 3 profiles + golden tests UNCHANGED (50/50 + 17 = 67 tests). Phase 4 schema extension (`max_delta_t_value`) MUST be backward-compat — no Phase 1/2/3 test perturbation.

§3 `_author_channel_dicts` rewire: 3 inline `w("system/controlDict", ...)` / `w("system/fvSchemes", ...)` / `w("system/fvSolution", ...)` calls replaced with `load_profile("channelPimpleFoam").render_*()` results. No `_build_channelpimplefoam_*` wrapper functions introduced (Phase 3 pattern: inline rewire).

§4 Cross-module error-contract: `_author_channel_dicts` wraps `load_profile()` in BCSetupError translation (proactively applying Phase 3 R1 P2 lesson). 2 regression tests pin the contract for ProfileNotFoundError + ProfileSchemaError.

§5 Codex pre-merge APPROVE / APPROVE_WITH_COMMENTS per RETRO-V61-001 risk-tier (multi-file backend route + new config schema profile + ≤70% self-pass-rate gate).

§6 Surface scan applied per V61-088: `bc_setup.py:806-893 (V61-101 inline channel pimpleFoam)` · disposition `refactor existing (final phase in V61-112 series; no further migration sites)`.

## Out of scope

- 0/U + 0/p + constant/physicalProperties + constant/momentumTransport templates (lines 750-805 in bc_setup.py for channel) — case-physics fields, NOT solver templates. Out of solver-profile scope; remain inline in `_author_channel_dicts`.
- Live channel dogfood verification — Docker container required; behavioral parity verified by existing 1172+ backend tests covering setup_channel_bc + adversarial smoke for iter02/iter04/iter05/iter06 named-patch cases.
- V61-102 §Phase 3 closure DEC update — V61-112 Phase 4 closes V61-102 §Phase 3 step 4 of 4 (final), but updating V61-102 frontmatter is a docs-only follow-up outside this DEC's scope.

## Process note

V61-112 Phase 4 explicitly applies the V61-088 pre-implementation surface scan rule:

`Surface-scan-found: ui/backend/services/case_solve/bc_setup.py:806-893 (V61-101 inline channel pimpleFoam controlDict + fvSchemes + fvSolution) · disposition: refactor existing (final phase in V61-112 series; closes V61-102 §Phase 3 step 4 of 4)`

V61-112 Phase 4 applies all V61-112 series methodology lessons:
- Phase 1 lesson: golden snapshots captured BEFORE rewire as literal constants
- Phase 2 lesson 1: snapshot tests exercise real caller input types — channel's no-args path
- Phase 2 lesson 2: dataclass int defaults — Phase 3 inheritance preserved
- Phase 3 lesson: cross-module error-contract translation applied PROACTIVELY at `_author_channel_dicts` to avoid repeat Codex finding

## V61-112 series closure

Phase 4 is the FINAL phase in the V61-112 series. Acceptance flips V61-102 §Phase 3 status from "3-of-4 done" to "4-of-4 COMPLETE" (closure step is a separate docs commit outside this DEC scope per §Out-of-scope).

After Phase 4: 4 inline-template extraction sites in case_solve consolidated into 4 YAML profiles (simpleFoam · pimpleFoam · icoFoam · channelPimpleFoam) under a single registry + schema. The V61-111 closure recommendation "consolidate the inline templates into YAML solver profiles so the dispatcher's parser is the canonical one all readers share" is COMPLETE.

## Acceptance closure (2026-05-03 · Codex pre-merge 6-round APPROVE)

Phase 4 implementation landed across commits `710083e` (initial) →
`e1cb332` (R1) → `4681e2d` (R2) → `5b18b60` (R3) → `4542928` (R4)
→ `2fc58e9` (R5). Codex pre-merge chain on 86gs `gpt-5.4` xhigh:

| Round | Commit | Verdict | Findings | Closure approach |
|-------|--------|---------|----------|------------------|
| R1 | 710083e | CHANGES_REQUIRED | 0 P1 + 1 P2 | 4 transient field validators (max_delta_t_value, max_co, adjust_time_step, iteration_floor) + 19 parametrized tests |
| R2 | e1cb332 | CHANGES_REQUIRED | 0 P1 + 1 P2 | 5th transient field validator (max_delta_t_follows_delta_t — STL pimpleFoam.yaml) + 5 parametrized tests |
| R3 | 4681e2d | CHANGES_REQUIRED | 0 P1 + 1 P2 | STL path try/except wrap → StlPatchBCError(failing_check="solver_profile_load_failed") + 1 regression test |
| R4 | 5b18b60 | CHANGES_REQUIRED | 0 P1 + 1 P2 | Route status mapping `"solver_profile_load_failed": 500` + route-level FastAPI TestClient regression |
| R5 | 4542928 | CHANGES_REQUIRED | 0 P1 + 1 P2 | ci.yml explicit-include for test_setup_bc_envelope_route.py |
| R6 | 2fc58e9 | APPROVE clean | — | "I did not find a concrete regression in the workflow syntax, dependency setup, or test-discovery behavior" |

**Substantive convergence**: 5 P2 findings across 5 fix rounds, but each round closed a DIFFERENT stage of a 5-stage cross-cutting cascade pipeline (validation → service-error wrap → route mapping → CI exposure). NOT scope creep; each prior fix correctly translated/wrapped/mapped the new code path but exposed an unhardened downstream stage. Severity stable at P2 across rounds; substantive content monotonically advanced.

**Tests**: ~30 new tests across 4 files (92 V61-112 + 19 STL + 12 user_override + 1 envelope_route) + 1146/1149 CI-equivalent regression-clean.

**Self-pass-rate calibration**: predicted 55% / actual 6 rounds (5 P2 + APPROVE). Calibration **honest overestimate** — the 5-stage cascade pattern was not anticipated; baseline for "cross-cutting cascade migration" should anchor at ~30-40% (distinct from "schema-extension migration" ~50% and "schema-reuse migration" ~60-70%).

**NEW methodology lesson captured in chain report** (full text in
report § Methodology lesson · The 5-stage hardening cascade): when
a refactor introduces a NEW failure surface that crosses multiple
service boundaries (validation → exception types → route mapping →
test coverage), plan ALL 5 stages upfront in the same commit:
1. Eager schema validation (raise ServiceError, not runtime errors)
2. Wrap at service-module boundary (`from exc` chain)
3. Route HTTP status mapping (explicit, not default-fallback)
4. Add regression test (router-level, not just service-level)
5. CI test exposure (testpaths / explicit-include)

Pre-merge review will still find sibling/downstream gaps but the round count drops from 5+ to 1-2. **Anti-pattern**: rejecting later rounds as "out-of-scope"; they are gaps that didn't exist until the prior fix.

**Phase 4 acceptance criteria status**:
- §1 channelPimpleFoam.yaml byte-identical to V61-101 inline: PASS
- §2 Phase 1+2+3 backward-compat preserved: PASS (50/50 + 17 = 67 prior tests pass)
- §3 _author_channel_dicts rewire delegates: PASS (3 inline calls replaced)
- §4 Cross-module error-contract: PASS (proactive at channel + retroactive at STL via R3)
- §5 Codex pre-merge APPROVE: PASS (R6)
- §6 Surface scan applied: PASS

**V61-112 series closure** (post-Phase 4):
- 4 inline-template extraction sites consolidated into 4 YAML profiles
- counter v6.1 advances 67 → 71 across the 4-DEC arc
- Cross-cutting hardening uniform across LDC + channel + STL paths
- V61-102 §Phase 3 deferral fully closed (4-of-4 done)
- V61-111 closure recommendation "consolidate inline templates" COMPLETE
