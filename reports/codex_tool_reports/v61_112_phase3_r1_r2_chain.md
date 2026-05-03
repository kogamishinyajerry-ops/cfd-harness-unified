# V61-112 Phase 3 · Codex pre-merge chain (R1 → R2 APPROVE)

**DEC**: DEC-V61-112-Phase3 — icoFoam LDC profile (V61-097 inline extraction)
**Backend**: 86gs `gpt-5.4` (xhigh) · governance baseline per RETRO-V61-001
**Trigger**: multi-file backend (case_solve service surface) + new config schema profile + ≤70% self-pass-rate gate — RETRO-V61-001 mandatory pre-merge
**Self-estimated pass rate**: 60% (calibrated UP from Phase 1+2's 50% baseline because Phase 3 introduces NO new schema extensions). Actual: 2 rounds (1 P2 + APPROVE) — calibration honest, slightly underestimated.

---

## R1 (commit f09992a) — CHANGES_REQUIRED · 0 P1 + 1 P2

> "The rendered icoFoam dicts themselves match the old inline output, but the new YAML-backed load path introduces an uncaught failure mode in `setup_ldc_bc()`. That breaks the route-level error contract in profile-missing or profile-invalid deployments."

| # | Sev | Finding | File | Closure |
|---|-----|---------|------|---------|
| 1 | P2 | `load_profile("icoFoam")` raises `ProfileNotFoundError` (missing YAML in runtime image) or `ProfileSchemaError` (malformed YAML); `_author_dicts()` doesn't translate to `BCSetupError`; `setup_ldc_bc()` only translates `CaseLockError`; both /setup_bc legacy route + setup_bc_with_annotations() handle BCSetupError exclusively. Result: deployment hazard surfaces as unhandled 500 AFTER mesh has been rewritten, instead of the established 4xx/5xx envelope. | `bc_setup.py:461-463` | Wrapped `load_profile("icoFoam")` in try/except for `(ProfileNotFoundError, ProfileSchemaError)` → re-raise as `BCSetupError("icoFoam solver-profile load failed: ...")` with `__cause__` chain preserved. Moved `load_profile` import from function-local to module-level so tests can monkeypatch. 2 new regression tests pin the contract. |

**R1 fix commit**: `fce714d`

---

## R2 (commit fce714d) — APPROVE clean

> "The change cleanly wraps the targeted solver-profile load failures in `BCSetupError` without altering the existing happy path, and the added regression tests exercise both missing-profile and malformed-profile scenarios. I did not find a concrete correctness regression introduced by this commit."

---

## Substantive convergence audit

| Round | P1 | P2 | P3 | Total | Δ vs prior |
|-------|-----|-----|-----|-------|-----------|
| R1 | 0 | 1 | 0 | 1 | (baseline) |
| R2 | 0 | 0 | 0 | 0 | -1 · APPROVE |

Best convergence in the V61-112 series so far:
- Phase 1: 3 rounds (3 P2 → 1 P1+1 P2 → APPROVE)
- Phase 2: 3 rounds (1 P2 → 1 P3 → APPROVE)
- **Phase 3: 2 rounds (1 P2 → APPROVE)** ← shorter

Phase 3's tighter chain reflects the "schema reused, no extensions" scope discipline: the migration was structurally simpler (no new schema fields, no new format helpers, no new edge cases for caller-input types). The single P2 was the deployment-hazard error envelope — correctly caught by Codex on the cross-module integration surface (load_profile crossing into BCSetupError contract).

---

## Self-pass-rate calibration

- **Predicted**: 60% (calibrated UP from Phase 1+2's 50% baseline because Phase 3 reuses Phase 2-extended schema without further extensions)
- **Actual**: 2 rounds (1 P2 substantive + APPROVE)
- **Calibration verdict**: **honest underestimate by ~10pp** — predicted 2-3 rounds got 2. The "no schema extensions" scope discipline paid off as predicted; the only finding was a cross-module error-contract gap (not a schema/render bug).

For RETRO-V61-001 trend across V61-112 series:
- Phases 1+2 (NEW schema work): 3 rounds each, ~50% baseline holds
- **Phase 3 (NO new schema): 2 rounds, ~60-70% baseline applicable**

The lesson: when refactor reuses an established schema without extension, the round-count baseline can be raised. **RETRO candidate intake**: differentiate "schema-extension migration" (50%) from "schema-reuse migration" (60-70%).

---

## Methodology lesson captured for next RETRO

### Cross-module error contracts when introducing new dependencies

**Pattern**: a refactor that introduces a new module-level dependency (`load_profile()` from solver_profiles) into a service module (`bc_setup.py`) must preserve the SERVICE module's error envelope contract. Service modules typically have a domain-specific Error type (BCSetupError) that callers/routes handle exclusively. New dependencies whose exception types are unfamiliar to callers MUST be translated at the service-module boundary.

**Phase 3 R1 P2 trap**: the LDC `setup_ldc_bc` route's error contract was BCSetupError-only. Phase 3's `load_profile("icoFoam")` introduced a NEW failure mode (ProfileNotFoundError / ProfileSchemaError) into the service module. The new exceptions bypass the established route handler chain → 500 instead of 4xx/5xx envelope.

**The fix pattern**: always translate cross-module-dependency exceptions at the service-module boundary using `try/except` + `raise BCSetupError(...) from exc`. The `from exc` chain preserves diagnostics for debugging.

**RETRO-V61-001 candidate intake**: when a refactor introduces a new MODULE-LEVEL dependency (not just a new helper from the same module), audit the service module's error envelope and translate any new exception types at the entry point. Add regression tests verifying the translation.

---

## Cross-referenced artifacts

- DEC-V61-112-Phase3: `.planning/decisions/2026-05-03_v61_112_solver_profile_yaml_phase3.md`
- Phase 1 chain report: `reports/codex_tool_reports/v61_112_phase1_r1_r2_r3_chain.md`
- Phase 2 chain report: `reports/codex_tool_reports/v61_112_phase2_r1_r2_r3_chain.md`
- Implementation commits: `f09992a` (Phase 3 initial) → `fce714d` (R1 fix)
- Tests: 8 new Phase 3 V61-112 + 2 new BCSetupError-translation regression = 10 new tests + 1172 CI-equivalent regression-clean
- Surface scan: `bc_setup.py:452-503 (V61-097 inline LDC icoFoam) + bc_setup.py:822-906 (channel pimpleFoam — Phase 4 follow-up)` · disposition `refactor existing`
- Phase 4 (deferred): channel pimpleFoam migration → next/last DEC in the V61-112 series
