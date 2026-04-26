# DEC-V61-072 Sampling Audit - First Execution Report

## Verdict: DEGRADATION_RULE_AT_RISK

## Per-commit summary
| sha | category 1 | 2 | 3 | 4 | 5 | overall |
| --- | --- | --- | --- | --- | --- | --- |
| `3d3509e` | clean | real-solver exec surface | clean | clean | clean | review-trigger |
| `ce0a8ce` | clean | draft save now feeds real run | clean | clean | whitelist no longer bounds params | review-trigger |
| `5fff107` | clean | new API + `reports/` writes | `/runs` namespace collision | second-level IDs + lossy writeback | clean | high blind-spot density |
| `74a93f1` | clean | clean | reactive rename fix | clean | clean | confirms category 3 gap |
| `6b7492c` | clean | operator failure semantics from stderr | clean | clean | clean | medium |
| `ecc1981` | clean | clean | clean | clean | clean | clean |
| `e83067c` | clean | clean | clean | clean | clean | clean |
| `61052a9` | clean | clean | clean | clean | clean | clean |
| `faf8446` | clean | new cross-case API | clean | `reports/*` discovery assumption | clean | medium |

## Blind-spot findings (only categories with evidence)

### Finding 1
- Category number: 2
- Affected commits: `3d3509e`, `ce0a8ce`, `5fff107`, `6b7492c`, `faf8446`
- Evidence: `ui/backend/services/wizard_drivers.py:452-457,514-517` exposes `FoamAgentExecutor.execute(...)` behind the workbench run path; `ui/frontend/src/pages/workbench/EditCasePage.tsx:16-19,118-137` writes draft YAML and immediately launches the real run path; `ui/backend/services/run_history.py:102-165` persists durable artifacts under `reports/{case_id}/runs/{run_id}`; `ui/backend/routes/run_history.py:22-33` at `5fff107` and `ui/backend/routes/run_history.py:37-75` at `faf8446` add new `/api` read surfaces; `ui/backend/services/wizard_drivers.py:282-344,551-569,641-688` turns solver stderr and exit-code text into durable operator-facing failure categories and remediation hints.
- Severity: HIGH
- Recommended Sec. 10.5 amendment: Any commit that invokes `FoamAgentExecutor`, changes execution reachability from UI/editor flows, adds `/api/**` routes, or writes durable runtime artifacts under `reports/` is audit-required even when no trust-core file is touched.

### Finding 2
- Category number: 3
- Affected commits: `5fff107`, `74a93f1`
- Evidence: `ui/backend/routes/run_history.py:3-4,22-33` at `5fff107` introduced `/api/cases/{case_id}/runs`; `ui/backend/main.py:93-106` at `5fff107` mounted `validation.router` before `run_history.router`, so the older Learn `/runs` handler won route resolution; `ui/backend/routes/run_history.py:6-11` at `74a93f1` and `ui/frontend/src/api/client.ts:123-134` at `74a93f1` rename the surface to `/run-history` to recover.
- Severity: MED
- Recommended Sec. 10.5 amendment: Any new route path, renamed path, schema key, or storage key must ship with a namespace grep against existing handlers and consumers before direct commit.

### Finding 3
- Category number: 4
- Affected commits: `5fff107`, `faf8446`
- Evidence: `ui/backend/services/run_history.py:50-56` at `5fff107` uses second-level `run_id` timestamps only; `ui/backend/services/run_history.py:118-123` at `5fff107` treats same `(case_id, run_id)` writes as idempotent overwrite; `ui/backend/services/wizard_drivers.py:447-456,538-544` at `5fff107` downgrades run-history write failures to warning logs while still emitting `run_done`; `ui/backend/services/run_history.py:173-185,199-213` at `faf8446` silently skips partial or unreadable run dirs; `ui/backend/services/run_history.py:216-255` at `faf8446` infers valid cross-case buckets from `reports/*` naming and directory shape rather than an explicit manifest.
- Severity: MED
- Recommended Sec. 10.5 amendment: Treat ID generation, artifact persistence, writeback failure handling, and filesystem discovery logic as determinism-sensitive surfaces that require review or an explicit deterministic test before bypass.

### Finding 4
- Category number: 5
- Affected commits: `ce0a8ce` with downstream surfacing in `5fff107`, `e83067c`, `faf8446`
- Evidence: `ui/backend/services/case_drafts.py:87-126` only blocks parse failures and allows structurally incomplete YAML to be saved with warnings; `ui/backend/services/wizard_drivers.py:375-422` prioritizes `ui/backend/user_drafts/{case_id}.yaml` over `knowledge/whitelist.yaml` and passes draft `parameters` plus `boundary_conditions` straight into `TaskSpec`; `ui/frontend/src/pages/workbench/EditCasePage.tsx:21-24,96-116,118-137` preserves non-form YAML fields, lets the user mutate numeric parameters, and immediately runs the solver on the draft result.
- Severity: HIGH
- Recommended Sec. 10.5 amendment: Any commit that lets `user_drafts` influence `TaskSpec` or solver inputs outside whitelist-fixed values is automatically audit-required until per-case range and compatibility validation exists.

## Methodology Sec. 10.5 recommendations
- Reduce the sampling interval from 20 to 5 direct-ship commits until two consecutive samples come back with no category 2-5 findings.
- Pre-flag commit-time audit requirements for any change that touches `FoamAgentExecutor` call sites, subprocess or Docker reachability, `/api/**` route registration, `reports/` persistence, or `user_drafts` to `TaskSpec` plumbing.
- Require a route-namespace collision check for every new or renamed `/api/cases/{id}/...` path before direct-to-main shipping.
- Require deterministic checks for same-second run creation, partial-write recovery, and cross-case feed discovery before bypassing review on run-history features.
- If a retro sample finds a HIGH blind spot, keep the merge only if there is no trust-core bleed or known corruption; otherwise open an immediate reviewed follow-up and temporarily remove the touched surface from the degradation allowlist.

## Counter calibration
Did this 9-commit batch warrant the Sec. 10 degradation? NO - the batch crossed from "workbench wrapper" into real solver execution, draft-to-solver input, durable runtime artifact writes, and new operator-facing API surfaces, so module-only gating was too weak even though trust-core files stayed untouched.
