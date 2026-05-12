---
decision_id: DEC-V61-166
title: B.4 · Dogfood orchestrator + DOGFOOD_REPORT aggregator + dry-run all 9 cells
status: Accepted
parent_dec: V61-162
phase: B
notion_sync_status: pending
---

# DEC-V61-166 · B.4 · Orchestrator + Aggregator + Dry-Run

## Scope

Wire the B.1-B.3 components into an executable arc. Ship:

- `scripts/dogfood/orchestrate.py` — orchestrator with serial /
  batch / all / dry-run modes, workbench-process management, case
  staging, per-run dispatch, friction log aggregation
- `scripts/dogfood/aggregator.py` — friction-log → DOGFOOD_REPORT.md
  with severity-classified backlog (critical / warning / info)
- `scripts/dogfood/scripted_runs.py` — scripted-mock LLM scripts
  per (case, persona) cell for dry-run reproducibility
- `tests/dogfood/test_orchestrate.py` — orchestrator dry-run
  end-to-end (9 cells, mock LLM + mock workbench transport)
- `tests/dogfood/test_aggregator.py` — aggregator on synthetic
  friction logs, severity classification, backlog formatting
- **Dry-run executed against all 9 cells** producing real artifacts
  under `.planning/dogfood/runs/dryrun_2026-05-07/<cell>/` +
  `.planning/dogfood/DOGFOOD_REPORT_DRYRUN.md`

## Live-run gating (deferred to user authorization)

This sub-DEC ships INFRASTRUCTURE, not live execution. Live runs
require:

1. `ANTHROPIC_API_KEY` + `CODEX_RELAY_API_KEY` env vars (this
   session has only `DEEPSEEK_API_KEY`)
2. Workbench dev server up at `localhost:8000` with N1-N6 routes
   responsive to STL imports of the case fixtures
3. User explicit authorization (charter §threat model: cost overrun
   $5-20 per arc; abort budget $50)

The `scripts/dogfood/orchestrate.py --live` mode is implemented but
NOT executed in this commit. User invokes manually after key setup.

## Severity classification (aggregator)

- **critical** — V130 violations (rationale text contains "AI told
  me", "advisor said so", "auto-apply" patterns) · workbench 5xx
  errors · max_steps_reached · transport errors · run drops with
  reason "no_tool_call"
- **warning** — verdict failed (observed outside tolerance) ·
  >10 advisor queries per run · token budget exceeded · run drops
  with explicit engineer reason · truncated workbench responses
- **info** — clean runs (verdict passed, ≤10 advisor queries, no
  errors)

## Four-question gate

| # | Question | Answer |
|---|---|---|
| Q1 | LLM offline → engineer can complete? | ✅ Orchestrator's `--workbench-llm-disabled` flag spawns workbench with `LLM_PROVIDER=disabled`; dry-run validates this configuration path; live runs will exercise it for at least one persona configuration |
| Q2 | Artifacts output? | ✅ Per run: friction_log.jsonl + result.json + (live only) experience_report.md + audit.zip. Aggregator: DOGFOOD_REPORT.md with structured backlog |
| Q3 | TrustGate / completeness / audit explainable? | ✅ DOGFOOD_REPORT cites individual friction-log lines for each backlog item; engineer can replay decision chain by reading per-run JSONL |
| Q4 | AI advisory only (no mutating call)? | ✅ Orchestrator uses harness's HTTP-only allowlist; dry-run mocks workbench transport without exposing mutating route surface; live mode reuses B.1 WorkbenchToolExecutor with localhost:8000/api/* allowlist |

## Verification

- `pytest tests/dogfood/test_orchestrate.py` passes
- `pytest tests/dogfood/test_aggregator.py` passes
- `python -m scripts.dogfood.orchestrate --dry-run --all` exits 0
  and creates 9 friction_log.jsonl files
- Generated `DOGFOOD_REPORT_DRYRUN.md` lists 9 runs with severity
  classification
- All committed dry-run artifacts are reproducible by re-running
  the orchestrator (deterministic scripted runs)

## Confidence

`high` — orchestrator wraps already-tested B.1/B.2/B.3 components;
new code is dispatch + aggregation with no new contract surface.
Dry-run mode insulates from API cost / workbench dependency.

## Codex pre-merge review

Per charter: B.4 is "per Opus confidence". Confidence high; no
Codex review.

## Notes

- The dry-run is SCRIPTED, not random — each (case, persona) cell
  has a fixed sequence of scripted assistant messages. This keeps
  dry-run deterministic for CI; live mode exercises real LLM
  reasoning.
- `experience_report.md` is generated only in live mode (it
  requires a final LLM call asking the persona to summarize). Dry
  mode skips it; the dry-run DOGFOOD_REPORT explicitly marks the
  absence.
- Live run requires the workbench to handle real STL imports;
  charter §risk-register acknowledges that workbench may produce
  unexpected behavior on these geometries. That's the dogfood —
  failures become friction-log entries.

## References

- DEC-V61-162 · B-arc charter (parent)
- DEC-V61-163 · B.1 harness
- DEC-V61-164 · B.2 personas
- DEC-V61-165 · B.3 case pool
