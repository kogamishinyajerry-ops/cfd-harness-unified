---
arc: anchor_04_run_compare_api
status: CLOSED · API hardened · UI refactor deferred
date_started: 2026-04-27T10:50Z
date_closed: 2026-04-27T11:10Z
roadmap_item: §60-day · run-comparison
---

# Anchor #4 · Run-vs-run comparison API closeout

## Discovery: §60-day item was already done at frontend level

Before this session, `ui/frontend/src/pages/workbench/RunComparePage.tsx`
already existed (built 2026-04-26, 349 LOC) with:
- Two-up overlay layout
- Client-side task_spec_diff
- Client-side key_quantities overlay (B - A)
- Client-side residuals overlay (B / A ratio)
- Wired App.tsx route `/workbench/case/:caseId/compare?a=&b=`
- "Compare →" button + 2-pick selector on RunHistoryPage

So the §60-day "run-comparison UI" was **already complete** at frontend level.

## What this session added

A parallel **server-side** compare API at:
```
GET /api/cases/{case_id}/run-history/{run_a_id}/compare/{run_b_id}
```

Distinct from the existing frontend's 2-call client-side approach. The
new API hardens the diff math against edge cases:

| Feature | Client-side (existing) | Server-side (this commit) |
|---|---|---|
| Round-trips | 2× GET | 1× GET |
| Diff math location | TS in browser | Python in service |
| NaN handling | implicit (subtract → NaN propagates silently) | explicit `tainted=True` + `tainted_indices` |
| Type mismatch (scalar↔array) | unhandled | explicit `type_mismatch=True` + `a_kind`/`b_kind` labels |
| Empty-list edge case | unhandled | explicit `list_empty` kind |
| Path traversal safety | n/a | `_validate_segment` on all 3 path params, 400 reject |

Codex review arc: R1 CHANGES_REQUIRED (2 P1 + 2 P2) → R2
APPROVE_WITH_COMMENTS (1 P2 carry-over closed inline) → ship.

Tests: 17/17 pass (10 service math + 4 route + 3 edge cases).

Live-validated against this session's LDC dogfood data
(Re=100 vs Re=400, run_ids
2026-04-27T07-21-59Z + 2026-04-27T10-00-32Z): correctly captures
`task_spec_diff: [{Re: 100→400}]`, `u_centerline` 17-pt
`max_abs_dev=0.178` at index 4 (correct physics — secondary vortex
strengthens at higher Re).

## Deferred follow-up: refactor RunComparePage to use server endpoint

The frontend is currently **not** consuming the new API. Refactoring
it would:
- Cut round-trips 2→1 (small perf)
- Move diff math out of TS into vetted Python (correctness)
- Surface `tainted` / `type_mismatch` flags in UI for partially-NaN
  or scalar↔array runs (new visibility)

Cost: ~30 LOC TypeScript + new client method `getRunCompare(...)` +
new types in `run_history.ts` + Codex review (multi-file frontend
trigger).

Not blocking. Filed as a future routine-path patch.

## What anchor #4 cost vs delivered

| Cost | Delivered |
|---|---|
| ~1h elapsed (service write + 2 Codex rounds + tests + closeout) | Server-side compare API (more robust than client-side) |
| 1 Codex 2-round arc | New endpoint regression-tested (17 tests) + path-traversal hardened |
| 0 Kogami | Discovery: §60-day frontend was already done — informs roadmap accounting |

## Combined session arc · 7 commits this session

```
96e9f46  feat(api): run-vs-run comparison · ROADMAP §60-day item · Codex R1→R2 [ops]
a8c9b76  docs(dogfood): anchor-2 cylinder reclassified GREEN per case_profile [ops]
aeb59bc  docs(dogfood): anchor-3 NACA + LDC-edit-flow closeout · v6.2 dogfood arc COMPLETE [ops]
e66bd51  docs(dogfood): anchor-2 cylinder closeout · v6.2 first live arc complete [ops]
4875b7f  chore(frontend): vite.config env-driven proxy port (anchor #2 dogfood) [ops]
7bcd09b  fix(wizard): BUG-1 · SSE consumer disconnect no longer drops verdict [ops]
f764294  feat(governance): DEC-V61-087 W4-A · dependency-triggered Q1 canary [ops]
```

## Recommended next session

ROADMAP §60-day remaining:
- ⏸ Project/workspace minimal concept (next session, ~3-5h)
- ⏸ Wire RunComparePage to new server compare endpoint (small follow-up)

Or §90-day items if user wants a bigger jump.
