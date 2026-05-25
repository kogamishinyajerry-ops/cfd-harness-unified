# M3.10 milestone close · 2026-05-25

> Parent charter: `DEC-V61-202-WORKBENCH-DYNAMIC-GUIDED`
> 1 cycle · single-functionality sub-DEC (no DEC file) · 0 Codex rounds · 0 Kogami
> final commit `89ebd82`

## 做了什么 (what)

**vtk.js proxy bug root-fix — graceful WebGL-unavailable degradation.** The P2
carried from M3.4 (B1 partial-fix caveat) and listed as the M3.9-retro's #1 next
candidate.

- New module `ui/frontend/src/visualization/webgl_support.ts` — vtk-free
  `detectWebGL()` + typed `WebGLUnavailableError`. Centralises the detectWebGL
  pattern previously local to `VtkCanvasV3.tsx`.
- `viewport_kernel.createKernel()` — pre-check + try/catch at the single
  vtk.js bootstrap chokepoint → throws the typed error instead of vtk.js's
  opaque `new Proxy(null,...)` TypeError. Protects every caller.
- `ViewportV4` — catches the typed error → existing `error` loadState
  (graceful "WebGL 不可用 · 3D 视口已降级" badge), no React-tree crash.
- `webgl_support.test.ts` — 3 unit tests (detector false under jsdom; typed
  error shape + cause).

## 为什么 (why)

- **The throw site is inside `node_modules` (`RenderWindow.js`), so the fix
  must live in our code.** The kernel is the one chokepoint all viewports flow
  through, so guarding there is the true root-fix (vs. patching each caller).
  A typed error lets callers `instanceof`-switch to a graceful fallback.
- **Standalone vtk-free module was forced by the test constraint**:
  `vite.config:50` documents that vtk.js `Profiles/*` side-effect imports crash
  vitest workers under jsdom, so the kernel can't be imported in a test. Pulling
  `detectWebGL` + the error type into their own module makes the guard
  unit-testable without WebGL/swiftshader.
- **Removes the app's hard dependency on `--use-gl=swiftshader`.** A user on a
  GPU-less machine or a lost-context situation now sees a degraded-viewport
  badge instead of a white-screen crash.

## v2.3 governance check

| Gate | Status | Note |
|---|---|---|
| DEC scope | ✅ single-functionality sub-DEC | ~38 LOC logic across new module + kernel guard + 1 caller; one cohesive feature, not ≥3 pre-existing shared paths → commit-message + tests, no DEC file |
| Codex round cap=3 | ✅ N/A (0 rounds) | not a sync-trigger (no security boundary / auth / signing / byte-repro). Frontend render guard, pattern-following, heavily verified → Opus 单飞 per v2.3 自主门控 |
| Kogami opt-in | ✅ not invoked | no charter-class trigger; no user召唤 |
| Four-question gate (V130) | ✅ Y/Y/Y/Y | LLM-offline (makes workbench MORE robust without GPU) · artifacts canonical (no format change) · TrustGate (badge states degrade reason) · AI advisory-only (no AI involvement) |
| Visual spot-check before close | ✅ done | happy path renders 3D cylinder (`/tmp/m310_happy/`); no-WebGL path shows graceful badge (`/tmp/m310_nowebgl_acceptance.png`) |
| Regression test non-vacuous | ✅ proven | targeted `git stash` demonstrated PRE-fix = 4× Proxy crashes / no badge; POST-fix = 0 crashes / badge present |
| Test suites | ✅ green | visualization + v4 → 16 files / 113 tests PASS |
| Port rule / date gating | ✅ honored / none | reused :8001 backend + :5188 vite from M3.9 |

## 下次候选 (next)

- **Pre-existing tsc error (NOT mine, flag for backlog)**: `tsc --noEmit`
  reports 1 error at `TopBarV4.tsx:67:32` (step `undefined` not assignable to
  the step union). The file is at committed HEAD, untouched by M3.10. The
  pre-commit hooks don't gate frontend tsc, so it slips through. Recommend a
  spike-class fix milestone OR fold into the next V4-shell touch.
- **Legacy `Viewport.tsx` caller-catch** (follow-up from this fix): now gets a
  typed `WebGLUnavailableError` instead of the Proxy crash (more debuggable, not
  worse) but still lacks its own catch+fallback. ~3 LOC + needs its error-state
  UI checked. spike-class.
- **DRY `VtkCanvasV3` onto `webgl_support`** — V3 still has its own local
  `detectWebGL`; could import the shared one now. spike-class, low priority.
- **M4 charter scoping** (deferred) — post-Step-7 solver_run / results / report /
  Notion sync. Multi-day; needs Kogami opt-in (user must召唤). NOT autonomous.
- Carry-overs: vscode:// jump · raw YAML viewer modal · "replace whole node" UI
  recovery · backend `gap.why` enrichment.

## Bottom line

M3.10 retires the last known correctness defect in the V4 viewport path with a
properly-rooted, before/after-proven fix: a typed guard at the kernel chokepoint
+ graceful caller degradation, verified by forcing WebGL off in a real browser
(4 Proxy crashes → 0) and confirming the happy path still renders. The
swiftshader headless flag is now a convenience for screenshot fidelity, no
longer a crash-avoidance crutch. Surfaced one pre-existing unrelated tsc error
for the backlog. Next candidate selection: see above — leaning toward the
TopBarV4 tsc fix (real, blocks `tsc -b` build) as the next quick milestone.
