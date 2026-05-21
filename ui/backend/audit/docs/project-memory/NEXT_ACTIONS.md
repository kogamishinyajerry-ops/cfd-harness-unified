# Next Actions

Small, concrete, ordered. Each item must have a clear acceptance criterion.

## 1. Run bootstrap verification
**Owner:** project-governor
**Acceptance:** `make bootstrap-check` exits 0; cockpit shows AMBER with no PASS-without-evidence.

## 2. Red Team review of the bootstrap
**Owner:** test-red-team
**Acceptance:** `docs/status/red_team_bootstrap_review.md` exists, lists findings, and contains a PASS/FAIL/BLOCKED verdict.

## 3. Select canonical reference dataset for `flat_plate_rans_sst`
**Owner:** benchmark-director
**Acceptance:** OQ-0001 resolved in DECISION_LOG; reference data + license stored under `cases/flat_plate_rans_sst/reference/`.

## 4. Decide OpenFOAM adapter strategy (docker vs native vs both)
**Owner:** openfoam-adapter-engineer + system-architect
**Acceptance:** OQ-0002 resolved; `docs/engineering/MODULE_BOUNDARIES.md` updated.

## 5. Populate 3 seeded negative-test directories
**Owner:** test-red-team + benchmark-director
**Acceptance:** at least three of `negative_tests/*/` are populated with manifests that the trust loop correctly returns FAIL/WARN on.

## 6. Tighten trust_report schema after Red Team feedback
**Owner:** system-architect
**Acceptance:** any constraint Red Team identifies as missing is encoded into `trust_report.schema.json` and exercised by a test.

## 7. Do NOT start any of the following yet
- writing the full workbench UI
- attempting multi-physics
- building design exploration
- silently switching the solver from mocked to real
- declaring any case "validated"
