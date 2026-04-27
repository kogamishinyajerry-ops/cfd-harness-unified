---
arc: anchor_02_cylinder
status: CLOSED · GREEN (corrected 2026-04-27T10:35 — see correction at bottom)
date_started: 2026-04-27T03:38:37Z
date_closed: 2026-04-27T07:42:35Z
case_id: circular_cylinder_wake
run_id_canonical: 2026-04-27T07-23-21Z
prior_run_id_lost: 2026-04-27T04-38-37Z (BUG-1 victim, no artifacts)
---

# Anchor #2 · Cylinder dogfood closeout

First live exercise of the v6.2 governance + M1-M4 closed-loop on a **transient pimpleFoam** case (anchor #1 LDC was steady simpleFoam, ~25s — too short to surface lifecycle bugs).

## Outcome

| Dimension | Status | Detail |
|---|---|---|
| M1 RealSolverDriver (transient) | ✅ GREEN | pimpleFoam Re=100, full 10s sim, 8354s wall |
| M3 run_history persistence | ✅ GREEN | 3-file artifact set landed; REST API surfaces it |
| BUG-1 fix (commit `7bcd09b`) | ✅ PROVEN | 2.3h prod run with done_callback persistence |
| Cylinder physics (St) | ⚠️ YELLOW | St=0.138 vs gold=0.164 (-15.9%, outside 5% tolerance) |
| Cylinder physics (Cd) | ✅ GREEN | Cd_mean=1.379 vs lit ~1.36 (+1.4%) |
| Codex review arc | ✅ R1→R2→R3 APPROVE_WITH_COMMENTS | 3-round arc within project limit |

## Findings

### BUG-1 · SSE-disconnect-loses-verdict — FIXED

- **Trigger**: prior cylinder run `2026-04-27T04-38-37Z` ran 2.5h to completion but **zero persistence** because curl SSE consumer was killed by Monitor 10-min timeout, cancelling the StreamingResponse coroutine before its inline `write_run_artifacts(...)` call. `asyncio.shield` protected the executor task; nothing protected the generator code downstream of the await.
- **Fix**: persistence moved to `exec_task.add_done_callback(_persist_callback)`. Callback fires on event-loop thread when `to_thread`'d `FoamAgentExecutor.execute()` returns, regardless of consumer state.
- **Codex arc**: R1 P1 (silent swallow) + P2 (cancelled-task path) → R2 P2 carry-over (heartbeat loop CancelledError on 3.11+) + test/spec drift → R3 APPROVE_WITH_COMMENTS.
- **Production validation**: LDC smoke (curl killed at 8s, verdict.json landed at 23.7s); cylinder full run (2.3h, all 3 artifact files landed).

### FRONTEND-1 · vite proxy hardcoded port — FIXED

- vite.config.ts proxy target was `http://127.0.0.1:8000`. When 8000 was owned by another project on the dev box, /api requests were silently routed to the wrong project.
- Made env-driven: `CFD_BACKEND_PORT` and `CFD_FRONTEND_PORT` now read in `vite.config.ts`. Tested with backend on 8010, frontend on 5190.
- Commit: `4875b7f`.

### CYLINDER-PHYSICS-1 · St under-prediction — DEFERRED

- Computed St=0.138 vs Williamson 1996 gold=0.164. Cd matches literature within 1.5%, FFT confidence flag = `false` (high), 400 samples / 7.98s window / 11+ shedding periods → not a sampling issue.
- Suspect causes (not investigated, candidate root-causes for a future case-quality phase):
  - Insufficient BL mesh resolution near cylinder
  - Domain blockage / aspect ratio (current: 10D upstream, 20D down, 12D height = ~8% blockage — generous but maybe still not enough)
  - Numerical diffusion in default `linearUpwind grad(U)` divScheme
  - `transient_trim_s = 2.0` may be too short for full transient settling at this mesh
- **NOT a workflow bug.** The closed loop correctly extracted, persisted, and surfaced what the solver computed. Filing as deferred follow-up.

## What anchor #2 cost vs delivered

| Cost | Delivered |
|---|---|
| ~5h elapsed (1 lost cylinder + 1 successful cylinder + fix dev) | BUG-1 (P1 lifecycle bug) caught + fixed + production-validated |
| 1 Codex 3-round review arc | M1+M3 transient-case validation |
| ~$2 Codex spend (3 rounds) | vite env-driven proxy (UI dev usability) |
| 0 Kogami invocations (per DEC-V61-087 §4.2 routine bugfix exemption) | First confirmation that v6.2 routine path works |

## Anchor #2 component status (vs original plan)

| Step | Status | Notes |
|---|---|---|
| 1. Baseline real run | ✅ DONE | run_id `2026-04-27T07-23-21Z` |
| 2. Edit endTime via /edit page | ⏸ DEFERRED | Cost-prohibitive (another 2.5h run) for a value already proven by anchor #1's LDC edit path; will exercise in anchor #3 (NACA, ~5min) |
| 3. Run history + auto-jump | ✅ IMPLICIT | `/api/cases/circular_cylinder_wake/run-history` returns the run |
| 4. Failure-classifier exercise | ⏸ DEFERRED | Same cost concern; better targeted at anchor #3 cheap runs |
| 5. First Kogami live trigger | ❌ N/A | Routine bugfix path — Kogami skipped per DEC §4.2; Codex 3-round was the gate |

## Recommended next

- **Anchor #3 NACA airfoil** (steady simpleFoam, ~5min) to exercise edit + classifier cheaply, validate v6.2 on a third whitelist case
- File CYLINDER-PHYSICS-1 as a Phase 8 / case-quality item (not blocking)

## Artifacts

- `reports/circular_cylinder_wake/runs/2026-04-27T07-23-21Z/{verdict.json, summary.json, measurement.yaml}`
- `reports/codex_tool_reports/bug1_sse_disconnect_persistence_r{1,2,3}.md`
- Commits: `7bcd09b` (BUG-1 fix), `4875b7f` (vite env config)

## Correction · 2026-04-27T10:35 — physics is GREEN, not YELLOW

While preparing the CYLINDER-PHYSICS-1 follow-up stub, I re-read
`.planning/case_profiles/circular_cylinder_wake.yaml` and found:

```yaml
tolerance_policy:
  strouhal_number:
    tolerance: 0.25  # 25% · 10s-endTime precision-limited; DEC-V61-053 R4
  cd_mean:
    tolerance: 0.05
```

Our run: St=-15.9%, Cd=+1.4%. Both are **within the case-profile's
documented per-observable tolerance bands** (25% / 5% respectively).

The 5% in `knowledge/whitelist.yaml` is the **aspirational** gold band;
the `tolerance_policy` in case_profile is the **operational** band, which
DEC-V61-053 R4 explicitly relaxed to 0.25 to account for the FFT
frequency-resolution limit Δf ≈ 1/(8s · 0.164) ≈ 0.76 → ΔSt/St ≈ 20% at
the 10s endTime.

So:
- The original closeout YELLOW classification was **incorrect** — read the
  whitelist's 5% but missed the case_profile's 25% override.
- No follow-up needed; CYLINDER-PHYSICS-1 stub NOT filed.
- This anchor is GREEN end-to-end at the policy that actually governs it.
- Independent path to tighter St precision **does** exist per DEC-V61-053
  comment: bump CYLINDER_ENDTIME_S 10→60s for ΔSt/St ≈ 3% precision.
  That's a separate scope item if/when the extra precision is needed,
  not a defect of this run.

This correction itself is a useful methodology signal: dogfood verdicts
should consult `.planning/case_profiles/<case_id>.yaml::tolerance_policy`
as the SSOT for "did the run pass?" — not the whitelist's nominal gold
band. The harness's auto_verifier already uses the case_profile path;
my manual closeout did not.
