# Testing Strategy

## Pyramid

```
        ┌──────────────────────┐
        │  Red Team reviews    │  ← human + AI-assisted, periodic
        ├──────────────────────┤
        │  Negative tests      │  ← Phase 2; seeded bad cases must FAIL/WARN
        ├──────────────────────┤
        │  Integration tests   │  ← Phase 0; trust loop end-to-end on flat plate
        ├──────────────────────┤
        │  Unit tests          │  ← Phase 0; per-module
        └──────────────────────┘
```

## Phase 0 coverage

| test file | covers |
|---|---|
| `tests/test_manifest.py` | schema loading; sample manifest validates; missing required field fails |
| `tests/test_trust_report.py` | trust_report has required fields; mocked solver cannot claim validated |
| `tests/test_negative_cases.py` | schema rejects manifests with missing required sections |
| `tests/test_cwos_status.py` | status JSON aggregation; PASS without evidence is flagged |
| `tests/test_cockpit_render.py` | cockpit MD + HTML rendered; required sections present |

## Definition of "test"

- runs under `pytest -q`
- exits 0 on success, non-zero on failure
- does not depend on network access
- does not depend on OpenFOAM being installed (Phase 0)
- does not depend on `git` being installed (Phase 0)

## Coverage targets

- every CLI subcommand has at least one happy-path test
- every audit gate has at least one negative test by Phase 2
- every schema constraint has at least one test that exercises it
- the cockpit renderer has at least one test asserting MOCKED is visible

## What we do not test in Phase 0

- real OpenFOAM execution (no solver in Phase 0)
- multi-case aggregation (only one case exists)
- AI advisor outputs (advisor lands in Phase 4)
- UI screens (Phase 3)

## False-pass discipline

A test that always passes regardless of behavior is a defect. Periodically the
test-red-team agent will introduce a temporary bug in the code under test to
confirm that the corresponding test fails. The bug is reverted; the experience
is recorded in the Red Team review.
