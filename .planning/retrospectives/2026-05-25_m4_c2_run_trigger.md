# M4 cycle 2 close · V4 run-trigger · 2026-05-25

> Parent charter: DEC-V61-204 (Accepted) · sub-DEC (spike-class+, commit-governed)
> commit `e074c2c` · 0 Codex (no security boundary) · 0 Kogami

## 做了什么 (what)

Gave the V4 solver-step `submit_solve` topbar CTA ("提交求解") a working
handler. It was a **dead button**: V4 "solver" → backend step 5, whose
`workbench_frame` emits `submit_solve` with `target_step=null`, and the shell's
onClick early-returned on null targets. Now:

- **`useSolveRun.ts`** (new hook): React Query mutation mirroring the M3.0 PATCH
  loop (`useManifestPatch`). `api.solve(caseId)` → on success invalidates the
  post-run V4 queries (`v4-residual-series` / `v4-ctx-runs` / `v4-ctx-detail` /
  `v4-advisor-runs`) so Step-6/7 refresh. Guards against double-solve in flight.
- **`DynamicTopbarCta`**: additive `busy`/`busyLabel` props (default off →
  legacy `StepPanelShell` mount unchanged) → disabled spinner while running.
- **`WorkbenchShellV4`**: `submit_solve` branch fires `runSolve()` instead of the
  navigation early-return; renders a `v4-solve-run-status` element (converged +
  wall-time, or failure message).
- **`handlers.ts`**: MSW solve mock for dev/mock + tests.

## 为什么 (why)

- C2 is the charter's first implementation cycle: close the post-construction
  loop's **trigger** inside the V4 shell (the V3→V4 consolidation carried the
  results *display* over but left the run *trigger* behind).
- Surface-scan disposition was `parallel` — but it turned out **cleaner than
  net-new**: the CTA already existed and rendered; only its handler was missing.
  Reusing the existing `submit_solve` affordance (vs adding a new button) keeps
  the M3.0 dynamic-frame pattern intact and avoids a redundant control.
- Blocking call + spinner (not SSE) per the charter's decided default — `/solve`
  is already blocking; SSE was V3-wizard-era wiring for marginal UX.

## v2.3 governance check

| Gate | Status | Note |
|---|---|---|
| DEC scope | ✅ sub-DEC (spike-class+) | 1 shared component touched, no schema/security boundary → commit-message-governed, no DEC file |
| Codex | ✅ N/A | no security/auth/signing boundary; confidence:high; Opus-solo path |
| Kogami | ✅ N/A | opt-in; not summoned |
| Four-question gate (V130) | ✅ 4/4 | LLM-offline · canonical artifacts · TrustGate (run-status+residual labels) · AI advisory-only (engineer click) |
| Build / tests | ✅ green | tsc -b exit 0 · vitest 828 passed (77 files) incl. 5 useSolveRun + 2 busy-prop |
| Frontend gate (M3.13) | ✅ fired+Passed | commit touched `.tsx` → tsc -b ran |
| Visual spot-check | ✅ PASS | mock mode: idle "提交求解" → busy "求解中…" (disabled+spinner) → "✓ 求解完成 · 已收敛 · 42s" + CTA re-enabled (`/tmp/c2_spot/0{1,2,3}.png`) |
| Cadence | ✅ Passed | 133 insertions <500 · path globs not hit (WorkbenchShellV4 is 3-deep, modified +43<150) · count <30 |
| Push | ✅ e074c2c | 74881ed..e074c2c · admin direct-push (enforce_admins=false) |

## 下次候选 (next)

- **C3 · V4 report-bundle display** — surface the `/report-bundle` matplotlib
  figures (contour-streamlines / pressure / vorticity / centerline) in V4 Post
  as canonical artifacts, with the charter's graceful "report unavailable on
  this build" fallback when matplotlib is absent (no crash, no hard dep).
- **C4 · e2e dogfood + close retro** — real backend (circular_cylinder_wake or
  lid_driven_cavity): build → Run → results → report, scripted assertions
  (charter close-criterion 1-4) + visual spot-check. This is where the
  run-trigger gets its real-solver proof (mock-mode covered the UI surface).

## Bottom line

The V4 Run affordance is live and visually confirmed end-to-end in mock mode.
The dead `submit_solve` button now drives the existing backend solve and
refreshes results — the trigger half of the M4 closed loop. C3 wires the report
figures; C4 proves the whole loop against a real solver.
