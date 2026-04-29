# Pre-merge Review: DEC-V61-101 Step 1 (`b7986ba`)

## HIGH — Executor does not enforce exact classifier→executor pin parity

**File:** `ui/backend/services/case_solve/bc_setup.py:453-488`

**Root cause:** `_split_channel_patches()` routes boundary faces by `face_id` membership, but after the scan it only checks `n_inlet > 0` and `n_outlet > 0`. It never proves that every supplied `inlet_face_ids` / `outlet_face_ids` entry was matched, and it never rejects overlapping input sets. That means the executor can silently accept a partially stale pin set instead of failing loud when the verified classifier contract no longer holds.

**Observed behavior:** Direct repro on the shipped 1×1×10 fixture succeeded with `inlet_face_ids=(<real inlet fid>, "bogus_missing_inlet_fid")` and `outlet_face_ids=(<real outlet fid>,)`. `setup_channel_bc()` returned success and rewrote the boundary as `1 inlet / 1 outlet / 4 walls` instead of raising `BCSetupError`.

**Why this matters:** Audit item A requires defense in depth: if the classifier verified specific face IDs, the executor must honor those exact IDs or fail. The current implementation only guarantees "at least one inlet and one outlet survived", which is weaker than the reviewed contract.

**Suggested fix:** Track `matched_inlet_ids` / `matched_outlet_ids` during the boundary scan, reject `missing_inlets = inlet_set - matched_inlet_ids`, `missing_outlets = outlet_set - matched_outlet_ids`, and reject `inlet_set & outlet_set` before rewriting any files. Add a regression test for "one valid + one stale pin still raises".

## MED — Channel executor failures bypass the route’s BC error mapping

**File:** `ui/backend/routes/case_solve.py:163-178`, `ui/backend/services/ai_actions/__init__.py:216-219`

**Root cause:** The wrapper raises `AIActionError(..., failing_check="setup_channel_bc_failed")` for channel executor failures, but the route only special-cases `setup_bc_failed` before falling back to a generic `422`. As a result, channel setup failures do not go through `_setup_bc_failure_to_http()` and do not preserve the setup-bc rejection contract.

**Observed behavior:** A direct route-level probe that raised `AIActionError("executor exploded", failing_check="setup_channel_bc_failed")` returned `422 {"detail": {"failing_check": "setup_channel_bc_failed", ...}}`.

**Why this matters:** The new non-cube path can now fail after a `confident` classifier verdict. On that path the frontend will see an annotations-style `422` instead of the setup-bc 4xx/5xx surface used everywhere else for BC setup failures.

**Suggested fix:** Treat `setup_channel_bc_failed` the same as `setup_bc_failed` in the route, or collapse both executors onto one BC failure tag. While touching that code, extend `_setup_bc_failure_to_http()` for channel-specific stale-pin / no-wall messages so they do not degrade to a generic `write_failed`.

## LOW — Reported Reynolds number contradicts the DEC’s locked default channel example

**File:** `ui/backend/services/case_solve/bc_setup.py:692-703`

**Root cause:** `setup_channel_bc()` computes `reynolds` from the maximum bounding-box extent. For the reviewed 1×1×10 channel fixture, that uses `L_char = 10`, so the result is `1000.0`. The DEC and classifier text, however, define the locked default example as `Re~100` from `U=1`, `D=1`, `nu=0.01`.

**Observed behavior:** Direct repro on the same 1×1×10 fixture returned `ChannelBCSetupResult.reynolds == 1000.0`.

**Why this matters:** The solver dicts remain laminar, but the user-facing summary in `ui/backend/services/ai_actions/__init__.py:221-229` will report `Re≈1000`, which contradicts both the DEC and the classifier’s "Re~100 default" explanation.

**Suggested fix:** Derive the characteristic length from inlet geometry / hydraulic diameter, or remove the numeric Reynolds from the summary until a truthful definition is implemented. Add a regression assertion for the reported value.

## Verification

1. `PYTHONPATH=. .venv/bin/pytest -q ui/backend/tests/test_ai_classifier.py ui/backend/tests/test_setup_bc_envelope_route.py` → `31 passed in 0.45s`
2. Backward-compat LDC checks are included in that slice, including `test_full_loop_uncertain_then_pin_top_lid_then_confident` and `test_wrapper_classifier_with_top_plane_lid_pin_returns_confident`.
3. Additional direct repro confirmed partial stale pin acceptance in `setup_channel_bc()`.
4. Additional direct repro confirmed the route returns `422` for `setup_channel_bc_failed`.
5. Additional direct repro confirmed the reported Reynolds value is `1000.0` on the 1×1×10 fixture.

## Verdict

**CHANGES_REQUIRED** — 3 findings.
