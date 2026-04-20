---
decision_id: DEC-V61-020
timestamp: 2026-04-21T05:55 local
scope: First DEC under new v6.1 governance (RETRO-V61-001 · bundle D). PR #20 declares `docker>=7.0` as `cfd-real-solver` optional dependency + fixes misleading error messages in `FoamAgentExecutor.execute()`. Round-6 Codex post-merge review returned APPROVED_WITH_NOTES at 77,607 tokens with two Low/Informational findings. L-PR20-1 (pip install shell-invalid) closed via verbatim-exception mechanical fix. L-PR20-2 (missing narrow tests) queued as P6 tech debt.
autonomous_governance: true
claude_signoff: yes
codex_tool_invoked: true
codex_diff_hash: b8be73aaa9eab8f5b99c9716e18ecf8fd4e25b18
codex_tool_report_path: reports/codex_tool_reports/2026-04-21_pr20_foam_adapter_review.md
codex_verdict: APPROVED_WITH_NOTES (2026-04-21T05:40 local · 77,607 tokens · first review under new v6.1 governance)
counter_status: "v6.1 autonomous_governance counter 0 → 1 (first increment under new governance; retrospective threshold ≥20)."
reversibility: fully-reversible-by-pr-revert
  (One `git revert -m 1 b8be73a` removes the docker optional-dep + error-
  message split. The L-PR20-1 verbatim fix at `04d6b9f` is independently
  revertable. Batch-run fixtures at `85fa4e5` are orthogonal and don't
  depend on this DEC.)
notion_sync_status: synced 2026-04-21T06:00 (https://www.notion.so/348c68942bed8135bbe1c7dbdefcadcd) — Decisions DB page created Status=Accepted, Scope=Phase, full round-6 ledger mirrored in body
github_pr_url: https://github.com/kogamishinyajerry-ops/cfd-harness-unified/pull/20
github_merge_sha: b8be73aaa9eab8f5b99c9716e18ecf8fd4e25b18
github_merge_method: merge (regular merge commit — 留痕 > 聪明)
external_gate_self_estimated_pass_rate: 92%
  (Self-estimate held. Codex round 6 returned APPROVED_WITH_NOTES with
  Critical/High/Medium all NONE. One real Low bug caught — L-PR20-1 pip
  install shell-invalid without quotes — closed verbatim in commit
  `04d6b9f`. L-PR20-2 test-coverage gap is genuine but low-severity.)
supersedes: null
superseded_by: null
upstream: RETRO-V61-001 (new v6.1 governance — this is the first DEC under
  the risk-tier-driven model)
downstream: §5d Part-2 acceptance batch (commit `85fa4e5`) consumed the
  `docker>=7.0` dependency to drive FoamAgentExecutor end-to-end, populating
  4 previously-UNKNOWN whitelist cases with real-solver-derived measurements.
---

# DEC-V61-020: PR #20 — `docker` optional dep + error-message honesty

## Decision summary

First DEC under the new v6.1 governance ratified in RETRO-V61-001.
Unblocks §5d Part-2 real-solver acceptance runs by declaring the Docker
Python SDK as a proper optional dependency (`cfd-real-solver`) and
fixing three identical misleading error messages in `FoamAgentExecutor`
to produce actionable guidance per failure mode.

## Changes

### pyproject.toml — `cfd-real-solver = ["docker>=7.0"]`

`src/foam_agent_adapter.py` imports Python `docker` SDK at module-top
but the package was never declared — the adapter silently guarded on
`_DOCKER_AVAILABLE` and emitted a generic error when the import failed.
Installing via `-e '.[cfd-real-solver]'` now declares the dep honestly,
enables supply-chain pinning, and makes the install path copy-pasteable
from the error message itself.

MOCK-mode unit tests stay lean (no Docker SDK needed).

### src/foam_agent_adapter.py:418-475 — branch-specific error messages

Three identical "foam-agent not found in PATH. Install Foam-Agent..."
messages split into four actionable branches:

| Trigger | New message |
|---|---|
| `_DOCKER_AVAILABLE=False` | "Docker Python SDK not installed. Install with `.venv/bin/pip install -e '.[cfd-real-solver]'` (or `pip install 'docker>=7.0'`)." |
| `docker.errors.NotFound` | "Docker container '{name}' not found. Start with `docker start {name}` (or create from image cfd-workbench/openfoam-v10:arm64)." |
| `docker.errors.DockerException` (not NotFound) | "Docker daemon or container unavailable: {exc}. Verify `docker info` works and the container is started." |
| Generic Exception during `from_env()` | "Unexpected error initialising Docker client: {exc!r}" |

`NotFound` is dispatched inside the `DockerException` handler via
`isinstance` with a `isinstance(not_found_cls, type)` type-guard. The
guard is needed because the existing test surface mocks `docker.errors`
as a `MagicMock`, which makes `docker.errors.NotFound` another
`MagicMock` rather than an exception class — a separate `except
docker.errors.NotFound:` clause would raise `TypeError: catching
classes that do not inherit from BaseException`. The `isinstance(...,
type)` guard lets the dispatch fall through to the `DockerException`
branch under mocks while routing real `NotFound` correctly under
real SDK.

### Post-round-6 verbatim fix (commit `04d6b9f`)

Codex round-6 finding L-PR20-1 flagged `pip install docker>=7.0` in the
missing-SDK error text as shell-invalid — both zsh (`zsh:1: 7.0 not
found`) and bash (redirects output to file `=7.0`) break on the
unquoted `>=`. Fix: single-quote → `pip install 'docker>=7.0'`.

Applied under the **verbatim-exception rule** of the new v6.1
governance (all 5 criteria met: diff-level match of Codex's suggested
fix, 1-char change, 1 file, no API change, PR body cites round +
finding ID). Skipped follow-up Codex review per that rule.

## Regression

```
pytest tests/test_foam_agent_adapter.py -q      → 94 passed
Full 9-file matrix                              → 327 passed + 1 skipped (unchanged)
```

Codex ran targeted tests + live SDK probes + shell probes but did NOT
rerun the full 327/1skip matrix. Static analysis + focused verification
of the changed paths only.

## Codex round-6 findings ledger

| ID | Severity | Status | Resolution |
|---|---|---|---|
| L-PR20-1 (pip shell-invalid) | Low | ✅ CLOSED (verbatim fix `04d6b9f`) | Quote `'docker>=7.0'` |
| L-PR20-2 (missing narrow tests) | Low | 🔒 QUEUED as P6 tech debt | Add tests for `_DOCKER_AVAILABLE=False`, real `NotFound` dispatch, MagicMock no-TypeError guard |

## 禁区 compliance

| Area | Touched? |
|---|---|
| `src/` (autonomous turf) | YES — adapter error paths |
| `pyproject.toml` (autonomous turf) | YES — new optional group |
| `tests/` | NOT TOUCHED |
| `knowledge/gold_standards/**` | NOT TOUCHED (禁区) |
| `knowledge/whitelist.yaml` `reference_values` | NOT TOUCHED (禁区) |
| `reports/codex_tool_reports/` | YES — round-6 artifact |

## Governance notes (first DEC under new v6.1)

- **Counter**: 0 → 1. Under the new telemetry-only model, no stop-signal at
  this count. Retrospective owed on counter ≥ 20 OR phase-close OR any
  `CHANGES_REQUIRED` verdict.
- **Codex trigger**: `src/foam_agent_adapter.py` modification > 5 LOC
  (actual change: ~46 LOC) → mandatory Codex review per the
  baseline rule. Self-pass-rate was 92%, above the 70% threshold that
  would force pre-merge — post-merge review was sufficient.
- **Verbatim-exception rule** was exercised correctly on L-PR20-1; this is
  the first live test of the tightened 5-of-5 criteria.

## Reversibility

`git revert -m 1 b8be73a` restores the pre-PR-20 adapter + pyproject.
The L-PR20-1 fix at `04d6b9f` is a separate revert target. No cross-
dependency with the Part-2 acceptance commit `85fa4e5` (which only
consumes the now-declared dep but doesn't mutate it).
