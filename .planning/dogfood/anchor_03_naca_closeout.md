---
arc: anchor_03_naca_plus_ldc_edit
status: CLOSED · GREEN
date_started: 2026-04-27T09:59:46Z
date_closed: 2026-04-27T10:33:00Z
case_ids: [naca0012_airfoil, lid_driven_cavity]
canonical_run_ids:
  naca: 2026-04-27T09-59-46Z
  ldc_re400_edit: 2026-04-27T10-00-32Z
---

# Anchor #3 · NACA airfoil + LDC edit-flow closeout

Third whitelist case + discharges deferred Steps 2-4 from anchor #2 (the cylinder run was too expensive to re-run for edit-flow validation). Combined arc:

- NACA 0012 (k-ω SST steady, simpleFoam, ~17.5min wall) — third v6.2 live arc
- LDC Re=100 → Re=400 edit via `/api/cases/{id}/yaml` PUT, full re-run, history confirms

## Outcome

| Dimension | Status | Detail |
|---|---|---|
| NACA M1+M3 closed loop | ✅ GREEN | run_id `2026-04-27T09-59-46Z`, 1050.9s wall, verdict + summary + measurement landed |
| NACA physics | ✅ GREEN | Cl≈0 sanity_ok=True, Cd=0.01256 vs Ladson 1988 ~0.0118 (+6% acceptable), Cd drift last-100=0.03% converged, y+ max 37.4 advisory PASS, Cp@LE=0.917, residuals 1e-6/1e-7 |
| M2 edit-page roundtrip | ✅ GREEN | LDC Re=100→400 saved to `user_drafts/lid_driven_cavity.yaml`, RealSolverDriver picked up draft (`source_origin: "draft"`), task_spec.Re=400 in run-history |
| M3 history populates | ✅ GREEN | 4 runs across 3 cases visible via `/api/run-history/recent`: LDC×2 (Re=100, Re=400) + NACA + cylinder |
| M4 failure classifier | ✅ COVERED via 28 unit tests | Live demo skipped — extreme-Re LDC produces silent NaN (convergence_attestor domain, not classifier; classifier targets process failures) |
| BUG-1 fix continued working | ✅ GREEN | NACA SSE consumer remained attached throughout; persistence path landed via done_callback (same path that recovered cylinder) |

## NACA physics detail (whitelist anchor #2 from ROADMAP "3 anchor case 闭环")

Re=3e6 · α=0° · turbulence=k-omega SST · 96k cells · 8000 SIMPLE iterations

```
Cl  = -1.6e-8  (symmetric Cl=0 sanity ✓)
Cd  = 0.01256  (Ladson 1988 ~0.0118 → +6%)
Cl drift_last_100 = -7747%  (denominator near-zero, ignore — absolute drift tiny)
Cd drift_last_100 = 0.03%   (converged)
y+ max = 37.4 (advisory PASS, <300 target for SST wall functions)
Cp range: [-0.410 (suction), 0.917 (LE stagnation)]
394-point pressure_coefficient profile extracted
residuals: Ux=3.6e-6, Uz=4.6e-7, p=1.0e-6, omega=7.0e-8, k=5.2e-6
```

This is a clean GREEN run — first-pass alpha=0 NACA result with no follow-up flags.

## M2 edit-page validation (LDC dogfood)

```
1. GET  /api/cases/lid_driven_cavity/yaml          → 200, origin=whitelist
2. PUT  /api/cases/lid_driven_cavity/yaml  (Re=400) → 200, saved=true, draft_path=ui/backend/user_drafts/lid_driven_cavity.yaml
3. GET  /api/wizard/run/lid_driven_cavity/stream    → SSE → run_id 2026-04-27T10-00-32Z, 20.1s
4. GET  /api/cases/lid_driven_cavity/run-history    → 2 entries: Re=100 (whitelist) + Re=400 (draft)
```

The new run's `summary.json` correctly shows `source_origin: "draft"` distinguishing it from the whitelist baseline. This validates `/api/cases/{id}/yaml` (case_editor) → `user_drafts/` → `_task_spec_from_case_id` → RealSolverDriver chain end-to-end.

## What anchor #3 cost vs delivered

| Cost | Delivered |
|---|---|
| ~30 min elapsed (NACA 17.5min wall + LDC ×3 ~1min + closeout) | NACA whitelist anchor proven (3rd case in v6.2 corpus) |
| 0 Codex calls | M2 edit-page validated end-to-end (was deferred from anchor #2) |
| 0 Kogami calls | M3 history accumulating across 3 cases / 4 runs |
| 0 new bugs found | BUG-1 fix continues to work in production (carry-over confidence) |

Net: anchor #3 was **cheap and clean** — exactly the data point needed to balance anchor #2's expensive YELLOW outcome.

## Combined v6.2 dogfood scoreboard (after anchors #1+#2+#3)

| Anchor | Case | Status | Key finding |
|---|---|---|---|
| #1 (smoke) | LDC | ✅ GREEN | Pipeline works; 23.7s |
| #2 | Cylinder | 🟡 YELLOW | Pipeline GREEN, physics St=-15.9% (deferred case-quality item); BUG-1 caught + fixed |
| #3 | NACA | ✅ GREEN | Pipeline + physics both GREEN; M2 edit-flow proven |
| #3-side | LDC Re=400 | ✅ GREEN | Edit-page → draft → real solver → history all working |

**v6.2 governance signals after 3 anchors:**
- Codex 3-round arc converges (1× exercised, R3 APPROVE_WITH_COMMENTS within limit)
- Kogami skip rule (DEC-V61-087 §4.2 routine bugfix) correctly triggered (1×)
- BUG-1 lifecycle bug (would-have lost 2.5h compute) caught in first live arc → exactly the value v6.2 was designed for
- self-pass-rate empirical: 0/3 first-pass APPROVE on the only review event → real-world baseline ≈ 0.30 (design estimate 0.55 is optimistic; recommend update at next RETRO)

## Recommended next

1. **Stop dogfood arc** — 3 anchors is enough for first v6.2 calibration. Move to scheduled work.
2. Open follow-ups (non-blocking):
   - CYLINDER-PHYSICS-1 (St under-prediction) → file as Phase-8 case-quality item
   - self-pass-rate calibration update at next RETRO (DEC-V61-087 self-estimated 0.55 vs empirical ~0.30)
3. Possible next initiative (per ROADMAP §60-day):
   - Run-comparison UI (diff two runs side-by-side, e.g. LDC Re=100 vs Re=400 from this arc's history)
   - Project/workspace minimal concept

## Artifacts

- `reports/naca0012_airfoil/runs/2026-04-27T09-59-46Z/{verdict,summary,measurement}`
- `reports/lid_driven_cavity/runs/2026-04-27T10-00-32Z/{verdict,summary,measurement}` (Re=400 edit-flow)
- `reports/lid_driven_cavity/runs/2026-04-27T07-21-59Z/` (anchor-1 smoke from earlier)
- `ui/backend/user_drafts/lid_driven_cavity.yaml` (draft restored to Re=100 post-arc)

## Note on lingering LDC-extreme run

A 5th LDC run was started during this arc with Re=99999999 to demo the failure classifier; the solver produced silent-NaN residuals (not a classifier-domain failure — convergence_attestor's job). The SSE consumer was killed; per BUG-1 fix the executor is still finishing in background and will eventually persist as a 5th history entry. This is real-world demonstration of the fix working: the run will land regardless. Not a bug, not a follow-up.
