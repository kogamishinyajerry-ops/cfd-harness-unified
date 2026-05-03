# V61-112 Phase 1 · Codex pre-merge chain (R1 → R2 → R3 APPROVE)

**DEC**: DEC-V61-112 — Solver-profile YAML migration · Phase 1 (schema + registry + simpleFoam profile)
**Backend**: 86gs `gpt-5.4` (xhigh) · governance baseline per RETRO-V61-001
**Trigger**: multi-file backend (case_solve service surface) + new config schema package — RETRO-V61-001 mandatory pre-merge
**Self-estimated pass rate**: 60% — calibrated reasonable (3 rounds; substantive content monotonically converged)

---

## R1 (commit 6f49017) — CHANGES_REQUIRED · 0 P1 + 3 P2

> "The runtime migration is close, but the new acceptance gate is both unexecuted in the standard suite and logically unable to detect byte drift, and the loader does not actually validate the nested `fv_solution` schema it now relies on. Those issues undermine the safety guarantees this refactor is supposed to provide."

| # | Sev | Finding | File | Closure |
|---|-----|---------|------|---------|
| 1 | P2 | New solver-profile gate not collected by CI — `pyproject.toml` `testpaths = ["tests"]` skips `ui/backend/tests/test_solver_profiles.py`; only `test_report_bundle.py` is explicit-included. | `ui/backend/tests/test_solver_profiles.py:1-7` | Added file to BOTH ci.yml pytest invocations (mainline + plane-guard WARN-mode dogfood). |
| 2 | P2 | Byte-identity assertions are tautological — `_build_simplefoam_*()` now calls `load_profile`, so `assert profile.render_*() == _build_simplefoam_*()` exercises the same code path on both sides. | `ui/backend/tests/test_solver_profiles.py:51-53` | Captured pre-migration bytes as `V61_111_GOLDEN_*` constants in test file (controlDict @ end_time=200, controlDict @ floored end_time=2.5, fvSchemes, fvSolution); assertions now compare profile-render output against immovable historical contract. Wrapper-equivalence kept as separate (acknowledged-tautological) tests documenting rewire intent. |
| 3 | P2 | `_build_fv_solution` doesn't validate nested `control_block_fields` shape — malformed YAML (e.g. `residualControl: []`, `solvers: {p: {...}}`) loads silently, fails at OpenFOAM-write time. | `ui/backend/services/case_solve/solver_profiles/registry.py:167-170` | Added type-check pass: solvers must be mapping of {field: scalar}; control_block_fields must be mapping with values=scalar OR nested-mapping (leaves are non-bool scalars); relaxation_factors_* must be mapping. Each bad shape raises TypeError → wrapped to ProfileSchemaError. 6 new parametrized regression tests pin the contract. |

**R1 fix commit**: `c3afd33`

---

## R2 (commit c3afd33) — CHANGES_REQUIRED · 1 P1 + 1 P2

> "The backend CI workflow now collects a test module that requires `[ui]` dependencies the job does not install, so the configured test lane will fail on a clean runner. The schema hardening also still lets malformed `control_block_name` values through by stringifying them instead of rejecting them."

| # | Sev | Finding | File | Closure |
|---|-----|---------|------|---------|
| 1 | P1 | CI install missing `[ui]` extra → pydantic absent → pytest collection aborts on clean runner. New test imports through `ui.backend.services.case_solve.bc_setup_from_stl_patches` → triggers `case_solve/__init__.py` → `case_manifest/schema.py` → `pydantic`. CI installed only `[dev,workbench]`. | `.github/workflows/ci.yml:70-72` | Changed install line to `pip install -e ".[dev,workbench,ui]"`. Aligned with future case_solve test growth (V61-112 Phases 2-4 will add more tests in same import chain). Codex's alternative ("stop importing through that package path") was infeasible: any case_solve submodule import drags the parent `__init__.py` regardless. |
| 2 | P2 | `control_block_name` accepted via `str(...)` coercion → `null/list/dict` rendered as `None { ... }` or `['SIMPLE'] { ... }` block headers. R1 P2-3 schema-validation contract was incomplete here. | `ui/backend/services/case_solve/solver_profiles/registry.py:214-215` | Added explicit `isinstance(cbn, str)` check; rejects null/list/dict/int with TypeError → ProfileSchemaError. Parametrized regression test `test_fv_solution_control_block_name_non_string_raises_schema_error` pins for 4 bad-value shapes. |

**R2 fix commit**: `ca5d2ab`

---

## R3 (commit ca5d2ab) — APPROVE clean

> "I did not find a discrete regression introduced by this commit. The CI change addresses the new test's import-time dependency on `pydantic`, and the `solver_profiles` change correctly rejects non-string `control_block_name` values before invalid OpenFOAM output can be rendered."

---

## Substantive convergence audit

| Round | P1 | P2 | Total | Δ from prior |
|-------|-----|-----|-------|--------------|
| R1 | 0 | 3 | 3 | (baseline) |
| R2 | 1 | 1 | 2 | -1 net (P1 emerged from CI surface change introduced by R1 fix; P2-3-residual surfaced by R1-P2-3 closure stopping short of `control_block_name` field) |
| R3 | 0 | 0 | 0 | -2 net · APPROVE |

R2 P1 was NOT a regression introduced by R1's substantive fixes — it was a surfaced gap created by including the test in the CI lane (R1 P2-1 closure). The pydantic dependency was always present in the test's import chain; R1 just made the test reachable. Codex correctly demanded the install line be widened to match.

R2 P2 was an "incomplete-fix" finding — R1 P2-3 hardened nested fields but missed the top-level string field. R2 closure widened the same validation pass to `control_block_name`.

R3 clean APPROVE confirms both R1 substantive concerns (test gate, schema validation) and R2 substantive concerns (CI dependency, control_block_name coercion) closed without introducing new gaps.

---

## Self-pass-rate calibration

- **Predicted**: 60% (V61-111 lessons applied — single-source-of-truth parser, dataclass-validated schema; expected 1-2 P2 schema-validation finer points)
- **Actual**: 3 rounds (R1 found 3 P2 schema-validation gaps + acceptance-gate gaps; R2 found 1 P1 CI-surface + 1 P2 schema continuation; R3 clean)
- **Calibration verdict**: **honest underestimate by ~10pp** — actual content (3+2 substantive findings) was slightly larger than predicted "1-2 P2", but pattern matches: schema-validation finer points caught in R1, surface integration caught in R2. ≤70% threshold correctly triggered pre-merge mandatory per RETRO-V61-001 + DEC §self_estimated_pass_rate gating.

For RETRO-V61-001 trend: V61-112 follows V61-111 as a 2nd consecutive case where YAML/schema migration work needed 2 fix rounds before APPROVE. Calibration baseline for "config-schema migration with golden-byte gate + schema validation" should anchor at ~50%, not 60%.

---

## Methodology lesson · acceptance gate authoring

V61-112 R1 P2-2 ("byte-identity assertions are tautological after rewire") is a NEW pattern not yet captured in any methodology doc:

**The gate-authoring trap**: when a refactor's acceptance gate is "new code produces same bytes as old code", the `assert new_func() == old_func()` pattern is correct ONLY while the OLD function still has its old implementation. The moment the OLD function is rewired to delegate to the NEW one (which is exactly what V61-112 does — `_build_simplefoam_*` now wraps `load_profile`), both sides of the assertion exercise the same code, and the gate becomes blind to drift in the new code.

**The fix pattern**: capture the old function's output as literal golden bytes BEFORE the rewire. Embed those bytes in the test as immovable constants. The new code then has a fixed historical contract to match.

**RETRO-V61-001 candidate intake** (for next retro): "byte-identity acceptance gates for refactor-without-behavior-change migrations MUST embed pre-rewire output as literal golden constants, NOT compare new_func() against rewired old_func()". Pattern applicable to: future V61-112 Phases 2-4 (pimpleFoam, icoFoam, channel migrations); any future "extract inline template into config" refactor.

---

## Cross-referenced artifacts

- DEC-V61-112: `.planning/decisions/2026-05-03_v61_112_solver_profile_yaml_phase1.md`
- Implementation commits: `6f49017` (Phase 1 initial) → `c3afd33` (R1 fix) → `ca5d2ab` (R2 fix)
- Tests: 21 new + 1063 CI-equivalent regression-clean
- Surface scan: clean (additive only — no new top-level files; `solver_profiles/` package new but lives under existing `case_solve/` service tree)
- Phase 2-4 follow-ups (deferred): pimpleFoam profile · icoFoam LDC migration · channel migration → separate DECs
