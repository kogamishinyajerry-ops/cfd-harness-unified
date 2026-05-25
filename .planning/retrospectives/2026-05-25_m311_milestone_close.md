# M3.11 milestone close · 2026-05-25

> Parent charter: `DEC-V61-202-WORKBENCH-DYNAMIC-GUIDED`
> 1 cycle · spike-class (no DEC file) · 0 Codex rounds · 0 Kogami · final commit `06448b1`

## 做了什么 (what)

Unblocked the frontend build. `tsc -b` (and therefore `npm run build`) was
failing at `TopBarV4.tsx:67` — an optional `activeStep` prop
(`V4PipelineStepId | undefined`) passed to `useEffectiveCaseId`, whose 2nd
param was typed non-undefined. Widened the hook param to
`V4PipelineStepId | undefined`; added `useEffectiveCaseId.test.ts` (4 tests).

## 为什么 (why)

- **Discovered during M3.10**, not introduced by it — the error was at committed
  HEAD `2648adf` (the prior 7-milestone session), in a file untouched by
  M3.9/M3.10. The pre-commit hooks gate Python import-linter + corpus-drift but
  **not frontend tsc**, so a red `tsc -b` slipped through the prior session
  undetected. A broken build is higher-severity than its P-class suggests.
- **Root-correct over band-aid**: the hook's logic is already undefined-safe
  (an undefined step matches neither `"doe"` nor `"geometry"` → case mode). The
  type was over-constraining vs. the implementation, so widening it is honest
  and behavior-neutral — preferable to a call-site `?? "import"` magic default.
  Safe for all 3 callers (TopBar / LeftRail / KpiStrip): defined values stay
  assignable to the wider type; TS types erase at runtime → zero behavior change.

## v2.3 governance check

| Gate | Status | Note |
|---|---|---|
| DEC scope | ✅ spike-class | 7 ins / 2 del + 1 test file; behavior-neutral type widening → commit-message + test, no DEC file |
| Codex round cap=3 | ✅ N/A (0 rounds) | type-only; no security boundary / byte-repro / auth |
| Kogami opt-in | ✅ not invoked | |
| Four-question gate (V130) | ✅ Y / n-a | LLM-offline (build/type only) · artifacts n/a · TrustGate n/a · AI advisory-only (no AI) |
| Visual spot-check before close | ✅ done | TopBarV4 + shell render unchanged (`/tmp/m311_check/`) |
| Build verification | ✅ `tsc -b` exit 0 | was exit 1 (1 error); now green |
| Test | ✅ 4 pass | first test for the M3.8 `useEffectiveCaseId` hook |
| Port / date gating | ✅ honored / none | reused :8001 / :5188 |

## 下次候选 (next)

- **M3.12 = legacy `Viewport.tsx` caller-catch** ← *leaning toward this next*.
  Completes the M3.10 WebGL-degradation story: `Viewport.tsx` still calls
  `createKernel` unguarded (now gets the typed `WebGLUnavailableError` from the
  kernel guard instead of the Proxy crash, but lacks its own catch+fallback UI).
  Finish the root-fix across all callers. spike-class (check its error-state
  hook first).
- **DRY `VtkCanvasV3` onto `webgl_support`** — V3 still has a local detectWebGL;
  import the shared one. spike-class, low priority.
- **Add a frontend `tsc -b` pre-commit/CI gate** — this milestone exists because
  none did. Worth a small governance follow-up so a red build can't slip again.
- **M4 charter scoping** (deferred) — multi-day, needs Kogami opt-in (user召唤).
- Carry-overs: vscode:// jump · raw YAML viewer modal · "replace whole node"
  recovery · backend `gap.why` enrichment.

## Bottom line

A 7-line type fix that turns the build from red to green — small LOC, real
severity. Found by running `tsc` during M3.10's verification rather than
trusting the prior session's "7 milestones closed" status. Reinforces the
Anthropic-harness lesson: `passes` ≠ `COMPLETED` — the prior session marked
milestones done without a build gate, and the gap surfaced one commit later.
Recommend adding a frontend tsc gate so the next session inherits a verifiable
green baseline.
