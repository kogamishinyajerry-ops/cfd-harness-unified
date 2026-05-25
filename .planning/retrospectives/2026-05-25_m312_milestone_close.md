# M3.12 milestone close · 2026-05-25

> Parent charter: `DEC-V61-202-WORKBENCH-DYNAMIC-GUIDED`
> 1 cycle · spike-class (no DEC file) · 0 Codex rounds · 0 Kogami · final commit `b4564f7`

## 做了什么 (what)

Completed the M3.10 WebGL-degradation root-fix across **all** callers of the
shared `createKernel`. Added a try/catch in legacy `Viewport.tsx` (mirroring
ViewportV4) → existing `error` LoadState with new `kind: "webgl"`. Added a
regression test in `Viewport.test.tsx`. Now every caller of the guarded kernel
(ViewportV4 · legacy Viewport · VtkCanvasV3-its-own-guard) degrades gracefully
instead of throwing.

## 为什么 (why)

- **No half-guarded shared module.** After M3.10, `createKernel` throws a typed
  `WebGLUnavailableError`; ViewportV4 caught it but `Viewport.tsx` did not, so
  the same context-less situation would surface as an uncaught typed throw
  there. Consistency across all call sites is the right hygiene for a shared
  chokepoint.
- **Honesty about scope (important)**: `Viewport.tsx` is currently **not on any
  live route**. `App.tsx` consolidated all V3 routes into `WorkbenchShellV4`
  ("the ONLY shell now"); Viewport is reached only via the unrouted V3
  `StepPanelShell` (and the removed `/workbench/dev/viewport-mode` harness). So
  this is a **defensive / future-proofing consistency fix**, not a user-facing
  bug today. I considered skipping it as dead-code gold-plating, but it (a)
  closes the M3.10 retro's explicit follow-up, (b) keeps the shared kernel's
  contract uniform, (c) costs ~12 LOC + test. Net: worth completing, framed
  truthfully.

## v2.3 governance check

| Gate | Status | Note |
|---|---|---|
| DEC scope | ✅ spike-class | 21 ins / 2 del + test; no DEC file |
| Codex round cap=3 | ✅ N/A (0 rounds) | frontend render guard, no security/byte-repro/auth |
| Kogami opt-in | ✅ not invoked | |
| Four-question gate (V130) | ✅ Y/Y/Y/Y | LLM-offline · artifacts canonical (no change) · TrustGate (error kind+message) · AI advisory-only |
| Visual spot-check before close | ⚠️ **N/A (documented)** | component is unrouted — no live route renders legacy Viewport. Binding evidence: unit test (renders error state, no fetch) + M3.10's real-browser no-WebGL acceptance (same kernel guard). This is the honest disposition, not a skipped gate. |
| Build | ✅ `tsc -b` exit 0 | |
| Test | ✅ 35 pass | visualization suite incl. new Viewport webgl-path test |
| Port / date gating | ✅ honored / none | |

## 下次候选 (next)

- **M3.13 = frontend `tsc -b` pre-commit gate (RECOMMENDED · highest value)** —
  M3.11 existed only because no gate caught a red build. Add a scoped,
  fast-enough typecheck hook so a broken build can't reach HEAD again. Touches
  `.pre-commit-config.yaml` (governance-adjacent) — scope carefully so it
  doesn't slow non-frontend commits.
- **DRY `VtkCanvasV3` onto `webgl_support`** — low priority; V3 works with its
  own local detectWebGL.
- **M4 charter scoping** (deferred) — multi-day, needs Kogami opt-in (user召唤).
- Carry-overs: vscode:// jump · raw YAML viewer modal · "replace whole node"
  recovery · backend `gap.why` enrichment · workbench-basics ↔ manifest
  cross-validation.

## Bottom line

The WebGL root-fix is now complete and uniform across every caller of the shared
viewport kernel. M3.12 is deliberately honest about hardening a currently-unrouted
legacy component — it's consistency + future-proofing, evidenced by a unit test
rather than a (impossible) visual spot-check. The session's WebGL arc (M3.10
root-fix → M3.11 build unblock → M3.12 caller completion) is closed; the standout
next item is a build gate so the prior session's class of slip can't recur.
