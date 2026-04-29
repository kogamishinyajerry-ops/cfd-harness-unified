# Pre-merge Review: DEC-V61-101 Step 1 (`e470618`)

## Findings

None.

## Closure Verification

### Finding 1 (HIGH) - closed

- `_split_channel_patches()` now rejects any inlet/outlet pin set that is not fully consumed after routing, via `missing_inlet` / `missing_outlet` and `BCSetupError("stale pins after classifier verification ...")` in `ui/backend/services/case_solve/bc_setup.py:453-528`.
- `test_channel_executor_rejects_partially_stale_pin_set` really exercises that new parity check, not the older zero-match guards: it passes one real inlet plus one bogus inlet plus one real outlet, so the pre-existing `n_inlet == 0` / `n_outlet == 0` checks cannot fire first. See `ui/backend/tests/test_ai_classifier.py:847-870`.
- No remaining silent-drop path was found for contracted channel pins. The classifier only promotes `user_authoritative` annotations whose `name` contains `inlet` or `outlet` (`ui/backend/services/ai_actions/classifier/__init__.py:245-266`, `:506-615`). Extra labels are ignored upstream by design rather than being routed to `walls` by the executor.

### Finding 2 (MED) - closed

- Envelope mode now maps both `setup_bc_failed` and `setup_channel_bc_failed` through `_setup_bc_failure_to_http()` in `ui/backend/routes/case_solve.py:180-191`.
- The original precedence is preserved: `not_an_ldc_cube` still matches first (`ui/backend/routes/case_solve.py:83-90`), channel mismatch second (`:91-107`), and `mesh_missing` third (`:108-114`). Direct repo-venv probe returned `400 not_an_ldc_cube`, `409 mesh_missing`, and `422 channel_pin_mismatch`.
- `test_envelope_channel_executor_failure_routes_to_422_pin_mismatch` genuinely hits the new 422 path: it forces `setup_channel_bc_failed` through the wrapper and asserts the route returns `detail.failing_check == "channel_pin_mismatch"` plus a channel-style message. See `ui/backend/tests/test_setup_bc_envelope_route.py:590-688`.

### Finding 3 (LOW) - closed

- `setup_channel_bc()` now computes `l_char` from the minimum nonzero bbox extent before Reynolds calculation in `ui/backend/services/case_solve/bc_setup.py:732-752`.
- `test_channel_executor_reports_re_100_on_unit_cross_section` verifies `res.reynolds ~= 100` on the `1x1x10` fixture. See `ui/backend/tests/test_ai_classifier.py:873-890`.
- Direct repo-venv probe of the full wrapper path confirmed `env.summary` is `Set up channel laminar BCs: inlet=1 face · outlet=1 face · walls=4 faces. Re≈100 (icoFoam laminar).` The existing full-loop tests still only assert the inlet/outlet substrings (`ui/backend/tests/test_ai_classifier.py:827-845`, `ui/backend/tests/test_setup_bc_envelope_route.py:566-587`), but the observed behavior matches the requested closure.

## Verification

1. `PYTHONPATH=. .venv/bin/pytest -q ui/backend/tests/test_ai_classifier.py -k 'test_channel_executor_rejects_partially_stale_pin_set or test_channel_executor_reports_re_100_on_unit_cross_section or test_full_loop_channel_uncertain_pin_inlet_outlet_then_confident'` -> `3 passed`
2. `PYTHONPATH=. .venv/bin/pytest -q ui/backend/tests/test_setup_bc_envelope_route.py -k 'test_envelope_channel_executor_failure_routes_to_422_pin_mismatch or test_envelope_full_loop_channel_inlet_outlet_pin_then_confident_via_http'` -> `2 passed`
3. `PYTHONPATH=. .venv/bin/pytest -q ui/backend/tests/test_ai_classifier.py ui/backend/tests/test_setup_bc_envelope_route.py` -> `34 passed`
4. Direct repo-venv probes confirmed HTTP mapping precedence (`400/409/422`) and wrapper summary `Re≈100`.

## Verdict

**APPROVE** - 0 findings.
