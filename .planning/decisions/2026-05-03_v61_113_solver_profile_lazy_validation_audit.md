---
decision_id: DEC-V61-113
title: Solver-profile loader · post-V61-112 lazy-validation audit sweep
status: Accepted (2026-05-03 · Codex pre-merge 1-round APPROVE on commit 0abf18f; chain report at reports/codex_tool_reports/v61_113_r1_chain.md; user 2026-05-03 autonomous-mode mandate + explicit "按你的建议继续，执行开发" follow-up covers acceptance flip)
codex_tool_report_path: reports/codex_tool_reports/v61_113_r1_chain.md
authored_by: Claude Code Opus 4.7 (1M context)
authored_at: 2026-05-03
authored_under: V61-112 series closure (commit 8601183 · counter 70→71) closed 4 inline-template extraction phases. The series surfaced 2 separate instances of the same lazy-validation pattern (Phase 1 R1 P2-3 fv_solution + Phase 4 R1+R2 controlDict). DEC-V61-113 audits the remaining solver-profile loader surface for sibling gaps before they're caught in production or by future Codex rounds on unrelated PRs.
parent_decisions:
  - DEC-V61-112-Phase4 (final V61-112 phase · supplied the "5-stage hardening cascade" methodology lesson — this DEC applies stages 1-2 of that cascade to the remaining loader surface preemptively)
  - RETRO-V61-001 (risk-tier · backend module + config schema validation = mandatory Codex pre-merge)
parent_artifacts:
  - reports/codex_tool_reports/v61_112_phase4_r1_r6_chain.md (5-stage cascade methodology lesson)
  - reports/codex_tool_reports/v61_112_phase1_r1_r2_r3_chain.md (R1 P2-3 fv_solution validation gap precedent)
counter_impact: +1 (autonomous_governance: true · preventive hardening, no external gate required)
self_estimated_pass_rate: 70% (HIGH baseline because this DEC is preemptive: applying KNOWN methodology lessons to KNOWN sibling surfaces. Audit scope is narrow — 2 loader functions (`_build_fv_schemes` + top-level `_build_profile`) + 1 exception class extension in `load_profile`. No new schema fields. No new render paths. Expect Codex 1-2 rounds; possible P3 nits on parametrized test coverage breadth.)
notion_sync_status: synced 2026-05-03 (https://www.notion.so/DEC-V61-113-Solver-profile-loader-post-V61-112-lazy-validation-audit-sweep-355c68942bed8169b15fc505a02d784e)
---

# DEC-V61-113 · Solver-profile loader lazy-validation audit

## Why now

V61-112 series closed 2026-05-03 (commits d0402e8 · 528bc6b · 3736839 · 8601183 · counter 67→71). The series surfaced 2 separate instances of the same lazy-validation pattern across Codex review rounds:

- **Phase 1 R1 P2-3**: `_build_fv_solution` accepted malformed nested-dict shapes (`residualControl: []`, `solvers: {p: {nested: dict}}`) silently → render-time failure
- **Phase 4 R1 + R2**: `_build_control_dict` accepted bool/string for numeric fields (`max_delta_t_value: "0.05"`) and `max_delta_t_follows_delta_t: "false"` → render-time truthiness branch silently authored or suppressed maxDeltaT

Two of three loader functions had this pattern. The Phase 4 chain report's "5-stage hardening cascade" lesson explicitly identifies stage 1 (validate at load time) as the prevention mechanism. **The third loader function — `_build_fv_schemes` — has the same gap, currently latent.**

Inspection of `_build_fv_schemes` at `registry.py:210-224`:
```python
for key in (...):
    if key in raw:
        value = raw[key]
        if not isinstance(value, dict):
            raise TypeError(...)
        # Coerce all values to str; YAML may parse numerics.
        kwargs[key] = {str(k): str(v) for k, v in value.items()}
```

The shape check on `value` (must be mapping) is correct, but each scheme expression value gets `str(v)` coerced — including `list`, `dict`, `None` which would produce garbage like `"['Gauss', 'linear']"` or `"None"` rendered into the fvSchemes file. OpenFOAM would reject those at solver startup. Same lazy-validation pattern as Phase 4 R1.

Additionally, top-level `_build_profile` at `registry.py:93-120`:
- Validates `family` ∈ {steady, transient} ✓
- Validates `name` matches filename ✓
- Does NOT validate that `control_dict` / `fv_schemes` / `fv_solution` are dict-typed before passing to `_build_*` builders. If `raw["control_dict"]` is a string or list, `_build_control_dict` crashes with `AttributeError` on `.keys()` access. `AttributeError` is NOT caught by `load_profile()`'s `except (KeyError, TypeError, ValueError)` block → escapes as raw 500.

## Decision

3-part hardening sweep:

### Part 1: `_build_fv_schemes` value-type validation

Reject non-scalar values in scheme dict entries. Allowed: `str`, `int`, `float`. Rejected: `bool`, `list`, `dict`, `None`. Maintains backward-compat for all 4 V61-112 profiles (which use only string-typed values per the OpenFOAM scheme syntax).

### Part 2: `_build_profile` top-level dict-shape validation

Validate `control_dict`, `fv_schemes`, `fv_solution` are dict-typed BEFORE delegating to `_build_*` builders. Raise `TypeError` on shape mismatch → wrapped to `ProfileSchemaError` by `load_profile`.

### Part 3: `load_profile` exception-handler widening

Add `AttributeError` to the `except` block so any residual builder-side type-mismatch surfaces as `ProfileSchemaError`, not raw 500.

## Acceptance criteria

§1 `_build_fv_schemes` rejects `list/dict/None/bool` values for scheme expressions; raises `TypeError` → `ProfileSchemaError` at load time.

§2 `_build_profile` rejects non-dict values for `control_dict / fv_schemes / fv_solution`; raises `TypeError` → `ProfileSchemaError` at load time.

§3 `load_profile` catches `AttributeError` (alongside existing `KeyError / TypeError / ValueError`) so any residual builder-side type-mismatch surfaces as `ProfileSchemaError`.

§4 All 4 V61-112 profiles (simpleFoam, pimpleFoam, icoFoam, channelPimpleFoam) continue to load + render byte-identical to their V61-097/V61-101/V61-107.5/V61-111 inline contracts. 87+ Phase 1-4 tests pass.

§5 Parametrized regression tests pin each new validation path with multiple bad-shape inputs (mirror V61-112 Phase 4 R1 pattern).

§6 Codex pre-merge APPROVE / APPROVE_WITH_COMMENTS per RETRO-V61-001.

§7 Surface scan applied per V61-088: `solver_profiles/registry.py:93-120, 210-224` · disposition `extend existing (preemptive hardening of remaining lazy-validation surface; no schema/render contract changes)`.

## Out of scope

- Other case_solve service modules (bc_setup, solver_runner, results_extractor) — separate DEC if audit warranted there
- case_manifest schema — already pydantic-validated; out of solver-profile scope
- New schema fields — this DEC ADDS NO new fields; only validates existing fields more strictly

## Process note

V61-112 series methodology lessons applied directly:
- Lesson "5-stage hardening cascade" (Phase 4): stages 1 (eager validation) + 2 (service-error wrap) applied preemptively. Stages 3-5 (route mapping + regression test + CI exposure) NOT in scope — this DEC doesn't introduce new failing_check values; existing ProfileSchemaError → BCSetupError/StlPatchBCError chain at `bc_setup.py` + `bc_setup_from_stl_patches.py` already covers downstream stages from V61-112 Phases 3+4.
- Lesson "byte-identity gates need golden constants" (Phase 1): no impact — this DEC doesn't change render paths, only load-time validation. Existing 87+ V61-112 tests verify no render drift.

`Surface-scan-found: ui/backend/services/case_solve/solver_profiles/registry.py:93-120 (top-level builder, missing control_dict/fv_schemes/fv_solution dict-shape validation) + ui/backend/services/case_solve/solver_profiles/registry.py:210-224 (fv_schemes builder, value-type str-coercion bypasses bool/list/dict/None rejection) · disposition: extend existing (preemptive sibling-gap closure; no schema/render contract changes)`

## Acceptance closure (2026-05-03 · Codex pre-merge 1-round APPROVE)

V61-113 implementation landed in commit `0abf18f`. Codex pre-merge
chain on 86gs `gpt-5.4` xhigh:

| Round | Commit | Verdict | Findings |
|-------|--------|---------|----------|
| R1 | 0abf18f | APPROVE clean | "Static review of the loader hardening and accompanying tests did not reveal a concrete correctness regression in the modified paths. The new validations and error wrapping appear internally consistent with the existing call sites that translate ProfileSchemaError into service-layer failures." |

**Single-round outcome — first in this session's V61-111 → V61-113
arc**. Direct application of V61-112 methodology lessons (recorded
in Phase 1 + Phase 4 chain reports) translated to first-pass success.

**Tests**: 18 new V61-113 parametrized tests + 110 V61-112+V61-113
total + 1215/1218 CI-equivalent regression-clean.

**Self-pass-rate calibration**: predicted 70% / actual 1 round
APPROVE. Calibration honest slight underestimate.

**NEW calibration baseline** captured in chain report § Self-pass-
rate calibration: "preemptive-audit migration (driven by prior
chain reports): ~80-90%". Becomes the 4th calibration anchor
alongside schema-extension (~50%), schema-reuse (~60-70%),
cross-cutting cascade (~30-40%).

**NEW methodology lesson** captured in chain report § Methodology
validation: "preemptive audit driven by prior chain reports works".
The chain-report-as-knowledge-transfer pattern justifies the writing
cost of detailed methodology-lesson sections — V61-112's chain
reports directly produced V61-113's first-pass success. RETRO-V61-001
candidate intake: track "lessons-applied count" per retro as the
leading indicator that chain-report methodology is paying off.

**V61-113 acceptance criteria status**: all 7 criteria PASS
(§1 fv_schemes value-type validation · §2 top-level dict-shape
validation · §3 AttributeError handler widening · §4 4 V61-112
profiles continue to load+render byte-identical · §5 parametrized
regression tests · §6 Codex APPROVE · §7 Surface scan applied).
