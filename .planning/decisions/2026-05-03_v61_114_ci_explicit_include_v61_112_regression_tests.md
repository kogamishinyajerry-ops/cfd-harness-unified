---
decision_id: DEC-V61-114
title: CI explicit-include for V61-112 cross-module-error-contract regression tests (post-V61-113 audit continuation)
status: Accepted (2026-05-03 · Codex pre-merge 1-round APPROVE on commit 39e4ef4; chain report at reports/codex_tool_reports/v61_114_r1_chain.md; user 2026-05-03 autonomous-mode mandate + explicit "continue with one more DEC to trigger the arc retro" follow-up covers acceptance flip)
codex_tool_report_path: reports/codex_tool_reports/v61_114_r1_chain.md
authored_by: Claude Code Opus 4.7 (1M context)
authored_at: 2026-05-03
authored_under: V61-113 closure (commit 351bb2a · counter 71→72) demonstrated the preemptive-audit-driven-by-prior-chain-reports pattern works (1-round APPROVE). DEC-V61-114 applies the SAME pattern to a sibling gap surfaced by V61-112 Phase 4 R5 P2 + Phase 1 R1 P2-1: V61-112 series added 5 regression tests across 2 outside-testpaths test files that are NOT in CI explicit-include. Without this DEC, the regression guards merge but never run on PRs.
parent_decisions:
  - DEC-V61-113 (post-V61-112 lazy-validation audit · supplied the preemptive-audit-pattern lesson — this DEC applies same pattern to CI test coverage gap)
  - DEC-V61-112-Phase4 R5 P2 (Codex caught the same gap for test_setup_bc_envelope_route.py · this DEC closes the sibling gaps for test_bc_setup_user_override.py + test_bc_setup_from_stl_patches.py)
  - DEC-V61-112 Phase 1 R1 P2-1 (Codex caught the original gap for test_solver_profiles.py · same pattern, now applied to 2 more files)
  - RETRO-V61-001 (risk-tier · CI configuration change for backend test coverage = mandatory Codex pre-merge)
parent_artifacts:
  - reports/codex_tool_reports/v61_113_r1_chain.md (preemptive-audit-pattern methodology source)
  - reports/codex_tool_reports/v61_112_phase4_r1_r6_chain.md (5-stage cascade lesson § stage 5 CI exposure)
counter_impact: +1 (autonomous_governance: true · CI hardening, no external gate required) — this acceptance triggers RETRO-V61-001 cadence rule #2 (counter ≥20 since prior retro · last anchor RETRO-V61-V107-V108 at counter 53 → arc retro at counter 73)
self_estimated_pass_rate: 80% (HIGH baseline per V61-113-established "preemptive-audit migration" calibration anchor of ~80-90%. Scope is minimal: 2 explicit-include lines in ci.yml's 2 pytest invocations = 4 total line additions. No source code changes. No new tests. Risk surface narrows to: Codex possibly suggesting (a) adding a meta-test that audits CI coverage, (b) consolidating the explicit-include list into a variable, (c) catching that the test files might have additional dependencies the [ui] extra doesn't cover. Expect 1 round APPROVE; possible P3 nit.)
notion_sync_status: pending (Notion MCP offline this session; sync queued for next online window)

# DEC-V61-114 · CI explicit-include for V61-112 regression tests

## Why now

V61-113 closure demonstrated the preemptive-audit pattern (1-round APPROVE) for lazy-validation gaps. The natural extension: apply the same pattern to the analogous CI-coverage gap discovered DURING V61-112 Phase 4 R5 P2.

Phase 4 R5 closed test_setup_bc_envelope_route.py's CI-include gap. But during V61-112 Phases 3+4, **5 additional V61-112 cross-module-error-contract regression tests were added across 2 outside-testpaths test files that are STILL NOT in CI explicit-include**:

- `test_bc_setup_user_override.py`:
  1. `test_author_dicts_translates_profile_load_error_to_bc_setup_error` (Phase 3 R1 P2 closure · LDC path)
  2. `test_author_dicts_translates_profile_schema_error_to_bc_setup_error` (Phase 3 R1 P2 closure · LDC path)
  3. `test_author_channel_dicts_translates_profile_load_error_to_bc_setup_error` (Phase 4 proactive · channel path)
  4. `test_author_channel_dicts_translates_profile_schema_error_to_bc_setup_error` (Phase 4 proactive · channel path)
- `test_bc_setup_from_stl_patches.py`:
  5. `test_setup_bc_from_stl_patches_translates_profile_load_error_to_stl_patch_error` (Phase 4 R3 P2 closure · STL path)

Without explicit CI inclusion, these regression guards land via the V61-112 commits but **never run on PRs** because pyproject.toml's `testpaths = ["tests"]` restriction excludes `ui/backend/tests/*`. The pattern Codex flagged in Phase 1 R1 P2-1 + Phase 4 R5 P2 still applies.

## Decision

Add the 2 test files to ci.yml's 2 pytest invocations (mainline + plane-guard WARN-mode dogfood), mirroring the Phase 1 + Phase 4 R5 + Phase 4 R5 closure patterns:

```yaml
python -m pytest tests/ \
  ui/backend/tests/test_report_bundle.py \
  ui/backend/tests/test_solver_profiles.py \
  ui/backend/tests/test_setup_bc_envelope_route.py \
  ui/backend/tests/test_bc_setup_user_override.py \
  ui/backend/tests/test_bc_setup_from_stl_patches.py -q
```

The full files are added (not just the V61-112 regression tests within), because:
1. Selective test collection at the function level requires fragile pytest expressions
2. The other tests in these files exercise existing service-module behavior; adding them to CI provides ADDITIONAL guard coverage, not just for V61-112-specific gaps
3. Verified locally: both files pass clean in CI-equivalent mode (1215 passed in V61-113 closure regression run)

## Acceptance criteria

§1 ci.yml mainline pytest invocation includes both files explicitly. Same pattern as test_solver_profiles.py + test_setup_bc_envelope_route.py inclusion (V61-112 Phase 1 + Phase 4 R5 closures).

§2 ci.yml plane-guard WARN-mode dogfood pytest invocation also includes both files. Same dual-include pattern as the prior V61-112 closures.

§3 Local verification: `pytest tests/ <all 5 explicit-includes>` produces no new failures.

§4 Codex pre-merge APPROVE / APPROVE_WITH_COMMENTS per RETRO-V61-001 risk-tier (CI configuration change for backend test coverage).

§5 Surface scan applied per V61-088: `.github/workflows/ci.yml` (lines 65-105 region) · disposition `extend existing (preemptive sibling-gap closure mirroring 3 prior V61-112 closures)`.

## Out of scope

- Audit of OTHER ui/backend/tests/* files for CI-include gaps — separate DEC if sweep-style audit warranted (this DEC scope-limits to V61-112-attributable regression tests)
- Refactor of CI explicit-include list into a YAML anchor or variable — adds cognitive overhead for future appends; defer until N=8+ files
- Updating pyproject.toml testpaths = ["tests", "ui/backend/tests"] — would discover EVERY test under ui/backend/tests/, including ones not previously vetted for CI-mode safety. Out of scope; explicit-include preserves selective discipline.

## Process note

V61-113 lesson "preemptive audit driven by prior chain reports works" applied directly:
- DEC-V61-114 cites Phase 4 R5 P2 + Phase 1 R1 P2-1 chain reports as the methodology source
- Cited gaps are sibling instances of the same pattern Codex caught earlier
- High pass-rate predicted (80%) per V61-113-established preemptive-audit calibration anchor

`Surface-scan-found: .github/workflows/ci.yml:80-86 (mainline pytest invocation, missing test_bc_setup_user_override.py + test_bc_setup_from_stl_patches.py) + .github/workflows/ci.yml:101-107 (plane-guard WARN-mode dogfood pytest invocation, same gap) · disposition: extend existing (preemptive sibling-gap closure)`

## Counter impact + arc retro trigger

This DEC's acceptance advances `autonomous_governance_counter_v61` 72 → 73, triggering RETRO-V61-001 cadence rule #2 (counter ≥20 since prior retro · last anchor RETRO-V61-V107-V108 at counter 53 → arc retro at counter 73). The next session begins with the arc retro.

V61-114's small scope is intentional: it's the "right-sized" DEC to close a real gap AND yield a clean arc boundary for retro analysis. The retro will have 20 acceptances to analyze (V61-088 → V61-114) covering the full V61-112 series + supporting work + V61-111 + V61-113.

## Acceptance closure (2026-05-03 · Codex pre-merge 1-round APPROVE)

V61-114 implementation landed in commit `39e4ef4`. Codex pre-merge
chain on 86gs `gpt-5.4` xhigh:

| Round | Commit | Verdict | Findings |
|-------|--------|---------|----------|
| R1 | 39e4ef4 | APPROVE clean | "The workflow change consistently adds the two missing backend test files to both pytest invocations in CI, which closes the stated coverage gap without introducing an obvious regression in the job configuration." |

**Note**: First Codex run truncated mid-grep (no verdict produced).
Re-run yielded clean APPROVE on the same commit.

**Second consecutive 1-round APPROVE in this session** (after V61-113).
Validates the V61-113-established preemptive-audit calibration anchor
(~80-90% pass-rate) — pattern is reproducible.

**Self-pass-rate calibration**: predicted 80% / actual 1 round APPROVE.
Calibration honest.

**Counter advancement**: 72 → 73. Triggers RETRO-V61-001 cadence rule
#2 (counter ≥20 since prior retro · last anchor RETRO-V61-V107-V108 at
counter 53 → arc retro at counter 73). Arc retro is next session's
first work item; analyzes 20-DEC arc V61-088 → V61-114 with self-pass-
rate calibration data across 5 distinct categories established this
session: bug-fix migration · schema-extension · schema-reuse ·
cross-cutting cascade · preemptive audit.

**V61-114 acceptance criteria status**: all 5 criteria PASS
(§1 mainline pytest invocation extended · §2 plane-guard dogfood
extended · §3 local verification · §4 Codex APPROVE · §5 Surface scan
applied).
