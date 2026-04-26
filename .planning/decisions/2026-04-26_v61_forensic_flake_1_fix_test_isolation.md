---
decision_id: DEC-V61-FORENSIC-FLAKE-1-FIX
title: Fix test_build_trust_gate_report_resolves_display_title_to_slug isolation flake (sys.modules restore in test_plane_guard_edge.py polluter)
status: ACCEPTED (autonomous_governance · pure test-isolation fix · no src/** or knowledge/** touched)
authored_by: Claude Code Opus 4.7 (1M context · Session B v3 Track 1)
authored_at: 2026-04-26
authored_under: Session B v3 · P-1 (DEC-V61-FORENSIC-FLAKE-1 follow-up)
parent_dec: DEC-V61-FORENSIC-FLAKE-1
autonomous_governance: true
external_gate_self_estimated_pass_rate: 0.95    # pure test-isolation fix; no Codex trigger; full suite green confirmed
notion_sync_status: pending
codex_tool_report_path: null  # CLASS-1: no Codex required (RETRO-V61-001 triggers not met)
risk_flags: []
gov1_v1_scope:
  case_id: forensic_flake_1_fix
  fix_type: test_isolation
  fields_modified:
    - tests/test_plane_guard_edge.py
  follow_up_required: false
boundary_self_attestation:
  src_cfd_harness_trust_core: NOT_TOUCHED
  src_other: NOT_TOUCHED
  knowledge: NOT_TOUCHED
  docs_methodology: NOT_TOUCHED
  session_a_paths: NOT_TOUCHED
verification:
  before:
    - "EXECUTOR_MODE=mock .venv/bin/python -m pytest tests/ -q"
    - "Result: 1 failed, 956 passed, 2 skipped"
    - "Failure: tests/test_task_runner_trust_gate.py::test_build_trust_gate_report_resolves_display_title_to_slug"
  after:
    - "EXECUTOR_MODE=mock .venv/bin/python -m pytest tests/ -q"
    - "Result: 956 passed, 2 skipped, 0 failed"
---

# DEC-V61-FORENSIC-FLAKE-1-FIX · Test Isolation Flake Fix

## Why

Per DEC-V61-FORENSIC-FLAKE-1, the test
`tests/test_task_runner_trust_gate.py::test_build_trust_gate_report_resolves_display_title_to_slug`
was born flaky in commit `f0f0f80`. Forensic identified the symptom but
deferred the fix. Track 3 (Session B v3 P-1) executes the fix.

## Root cause (corrected from forensic hypothesis)

The forensic DEC hypothesized lazy-load memoization in
`load_tolerance_policy`. Investigation showed `load_tolerance_policy`
is purely file I/O with **no module-level cache**. Hypothesis was wrong.

Actual root cause: **stale module reference after sys.modules.pop**.

`tests/test_plane_guard_edge.py::test_a7b_log_schema_stability` (4
parametrizations) does:

```python
sys.modules.pop(target, None)        # target ∈ {src.task_runner, ...}
exec(f"import {target}", exec_globals)
```

This pop+reimport produces a NEW module object MODULE_B, replacing
MODULE_A in `sys.modules` AND in the parent package attribute
(`src.task_runner`). MODULE_A is the module that
`tests/test_task_runner_trust_gate.py`'s top-level
`from src.task_runner import _build_trust_gate_report` bound to at
collection time.

After pollution, when the failing test runs:

1. `from src import task_runner as tr` → returns MODULE_B (via `src`
   package attribute)
2. `monkeypatch.setattr(tr, "_resolve_case_slug_for_policy", ...)` →
   patches MODULE_B
3. `_build_trust_gate_report(...)` is the top-level imported symbol,
   bound to MODULE_A's function. Its `__globals__` is MODULE_A.`__dict__`
4. The bare-name lookup `_resolve_case_slug_for_policy(task_name)` inside
   the function body resolves via MODULE_A's `__dict__` — never sees the
   monkeypatch on MODULE_B
5. Production `_resolve_case_slug_for_policy` walks the real whitelist,
   doesn't find "Demo Display Title", returns it unchanged. Then
   `load_tolerance_policy("Demo Display Title")` finds no
   `Demo Display Title.yaml` in `tmp_path` → returns `{}`
6. Assertion `tolerance_policy_observables == ['alpha_obs', 'beta_obs']`
   fails (actual `[]`)

In isolation the polluter never runs, MODULE_A is the only module,
monkeypatch reaches it, test passes.

## Fix

Two-step `sys.modules` restore in the polluter
`test_a7b_log_schema_stability`:

1. Save the original `sys.modules[target]` before pop
2. After the test body asserts pass, restore in `finally`:
   - `sys.modules[target] = saved_target`
   - `setattr(parent_mod, child_name, saved_target)` — restore parent
     package attribute (e.g. `src.task_runner = MODULE_A`); the
     exec-triggered import mutates BOTH and restoring only
     `sys.modules` leaves the parent attr stale

Without the parent-attr restore step, `from src import task_runner`
still returns MODULE_B because Python looks up the attribute on the
`src` package object, not in `sys.modules`.

## Why test-side fix (not production-side)

DEC-V61-FORENSIC-FLAKE-1 §"Decision" listed two paths:
- **Test-side**: setUp/tearDown to reset `tolerance_policy_observables`
  registry (or other isolation primitive)
- **Production-side**: redesign `load_tolerance_policy` to not retain
  global state

Investigation rejected the production-side hypothesis (no global state
exists). The actual issue is in the polluter test (`test_plane_guard_edge.py`),
not in any production code. **No `src/cfd_harness/trust_core/**` touched
→ Boundary 6 not crossed → autonomous_governance applies.**

## Hard-boundary self-attestation

- ❌ NO `src/**` modification
- ❌ NO `knowledge/**` modification
- ❌ NO `docs/**` modification
- ❌ NO Session A path touched
- ✅ Single test file modified: `tests/test_plane_guard_edge.py`
  (added try/finally with sys.modules + parent-package-attr restore)

## Codex review

RETRO-V61-001 mandatory triggers checked:
- Multi-file frontend: NO
- API contract change: NO
- OpenFOAM solver fix: NO
- foam_agent_adapter >5LOC: NO
- New geometry generation: NO
- E2E ≥3 case failures: NO
- Docker+OpenFOAM debugging: NO
- GSD UX changes: NO
- Security-sensitive operator endpoint: NO
- Byte-reproducibility path: NO
- Cross-≥3-file API rename: NO

None match. CLASS-1 by default. No Codex review required.

## Verification

```
Before fix:
  EXECUTOR_MODE=mock .venv/bin/python -m pytest tests/ -q
  → 1 failed, 956 passed, 2 skipped (the flake)

After fix:
  EXECUTOR_MODE=mock .venv/bin/python -m pytest tests/ -q
  → 956 passed, 2 skipped, 0 failed
```

## Source

- Parent DEC: `.planning/decisions/2026-04-26_v61_forensic_flake_1_test_isolation.md`
- Audit input: `.planning/audit_evidence/2026-04-26_v61_080_a4_flake_attribution.txt`
- Modified file: `tests/test_plane_guard_edge.py` (test_a7b_log_schema_stability)
