---
decision_id: DEC-V61-172
title: B-extend charter · F6 conversation pruning + F7 STL patch discovery — drive verdict pass rate to ≥1/3 on DeepSeek cells
status: Accepted
parent_dec: V61-162
phase: B-extend
notion_sync_status: pending
---

# DEC-V61-172 · B-Extend Charter

## Status

**Accepted 2026-05-07** — Per B-arc close (DEC-V61-171) recommendation
#1 + user authorization. B-extend is a focused two-fix arc on top of
the closed B-arc.

## Scope

Two surgical fixes, then re-run live partial (3 DeepSeek cells) to
measure verdict-pass impact. Goal: at least one cell submits a passing
verdict (verdict pass ≥ 1/3).

| Sub-DEC | Capability | Commit gate |
|---|---|---|
| DEC-V61-173 | B-ext.1 conversation pruning in `persona_runner.py` (F6) | per Opus confidence |
| DEC-V61-174 | B-ext.2 patch discovery routes added to `/actions` catalogue (F7) + step 4 description updated for `defaultFaces`-only case | per Opus confidence |
| DEC-V61-175 | B-ext.3 R4 live re-run + close + Chinese delta summary | n/a |

Each sub-DEC is a single atomic commit per V133 charter rules.

## Charter goal

R3 demonstrated that the B-arc bottleneck is harness-side, not
workbench-side:

- Per-turn input bandwidth (DeepSeek's ~64k input cap) is hit around
  turn 10-15 because conversation history accumulates linearly
- pipe_expansion specifically failed Step 4 setup-bc 400 because STL
  ingest reported only `defaultFaces` and the persona had no path to
  split it

Fix both, re-run R4, target verdict pass ≥ 1/3.

## Out of scope

- Full 9-cell cross-Cartesian (still gated on Anthropic + CODEX_RELAY
  API keys; B-extend stays 3-cell DeepSeek)
- Workflow-completion validation beyond the R4 measurement
- Workbench taxonomy unification (`/api/cases/...` vs
  `/api/import/...`) — listed in B-arc close as larger architectural
  question; deferred until B-extend results indicate it's actually
  blocking

## Threat model (delta vs B-arc)

| Threat | Mitigation |
|---|---|
| Pruning drops critical context (e.g., persona forgets a verdict-relevant chunk_id) | Always preserve initial brief + last K turns full; only summarize older `tool_result` bodies; preserve every `verdict` / `decision` event in friction log unchanged |
| Pruning summary is itself prompt-injection-sensitive | Summary is generated harness-side from structured event data, not LLM output; no untrusted text |
| F7 patch routes add new mutating surface | Charter forbids new mutating routes in B-extend; we add catalogue entries pointing at EXISTING `PUT /face-annotations` + `PUT /patch-classification` (already in MUTATING_ROUTES set per V132); no new V132 contract |

## Four-question gate

| # | Q | A |
|---|---|---|
| Q1 | LLM offline → engineer can complete? | ✅ Pruning is harness-side, no LLM dependency; patch discovery routes are read-only catalogue entries |
| Q2 | Artifacts? | ✅ Friction log unchanged (full event trail); `result.json` unchanged |
| Q3 | Audit explainable? | ✅ Pruning summaries cite turn number + URL + status; engineer can replay the underlying friction log line-by-line |
| Q4 | AI advisory only? | ✅ No new mutating routes; catalogue points at existing surfaces |

## Verification (charter-level)

- [ ] B-ext.1 lands with tests for prune-window correctness
- [ ] B-ext.2 lands with /actions test asserting face-annotations + face-index + patch-classification entries present
- [ ] R4 live runs all 3 DeepSeek cells against workbench with both fixes
- [ ] DOGFOOD_REPORT_LIVE_R4.md shows verdict pass count, severity table, V130 stillgreen
- [ ] If R4 verdict pass < 1/3, charter §recommended-next-steps flags
      whether to iterate B-ext.4 or escalate to B-extend-2
- [ ] Chinese delta summary (vs B.6 close summary) delivered

## References

- DEC-V61-162 · B-arc charter
- DEC-V61-171 · B-arc close (B-extend recommendation)
- `.planning/dogfood/DOGFOOD_REPORT_LIVE_PROGRESSION.md` — F6 + F7 origin
- `.planning/reviews/kogami/b_arc_strategic_retro_2026-05-07/review.md` — Kogami P2-1 (F5↔F7 coupling)
