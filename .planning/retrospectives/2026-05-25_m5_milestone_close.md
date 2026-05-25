# M5 milestone close · Post-processing depth + truth-chain de-fake · 2026-05-25

> Parent charter: DEC-V61-205 · M5 sub-DEC arc (C2 → C3 → C4)
> C2 retro: `2026-05-25_m5_c2_progress.md` (VTP overlays · COMPLETE)
> C3 commit: `9970102` (verdict pill de-fake · pushed)
> C4 commits: `535f2f1` (C4-1) → `eb1672e` (C4-2) → `7c2fe19` (R1) → `ed659fd` (R2) → `a56ea27` (R2-close)
> Codex C4: R0 (3×P2) + R1 (1×P2 + 1×P3) + R2 (2×P2) · round cap=3 reached · all closed
> Push: `9970102..a56ea27` → origin/main (cadence hook Passed via `Codex-verified: RESOLVED` trailer; no override used)

## 做了什么 (what)

M5 took the V4 Post view from "renders real geometry but surrounds it with
fabricated telemetry" to "every surface is real run-derived data or an honest
no-data / illustrative state." The de-fake landed in three cycles:

**C2 · VTP overlays** (separate retro): surface field + integrated streamlines
render on a real solve (4 wiring bugs + the `postProcess -func` filename
gotcha). Legend reads the real foamToVTK scalar range (`0 → 0.86 m/s`).

**C3 · verdict pill** (`9970102`): the hardcoded `POST_BLUEPRINT_VERDICT`
("通过 · +4.2%") was replaced by `useComparisonVerdict` →
`/comparison-report/context`. Renders the real gold-vs-measured verdict
(PASS/PARTIAL/FAIL + N/M gold points) or the honest "无基准对比 · 仅可视化
结果 · 无 gold 基准" for cases with no reference. Live-confirmed on
backward_step (404 → 无基准对比).

**C4 · the remaining telemetry**:
- **Radial gauge** (`535f2f1`): was a hardcoded 65% "通过率"; now reads the
  REAL worst-equation convergence (`convergenceGaugeFromSeries` over the same
  residual-series endpoint TopBar/LeftRail trust). Honest "无残差数据" empty
  state when no series. Live: **48 · 收敛度 · Uz · 进展中** (p converged to
  6.5e-7 but Uz bounds overall convergence — both honest + consistent).
- **Mini profile charts** (`535f2f1`): no real per-quantity profile source
  exists for a generic case, so the three waveforms now carry an explicit
  **示意** badge + muted opacity and hide the terminal value — never silent
  fake data (charter: honest blueprint-labelled states).
- **KPI strip** (`eb1672e`): was 248.6 Pa / 3.62 kg/s / 96.4°C / 65% / +4.2%
  增益 (domain KPIs the workbench never computes); now real solver-truth
  facts — **求解状态 成功 / 用时 1.5s / 退出码 0 / 残差 p 6.5e-7 / 对比基准
  无基准** — + the real verdict.
- **Right cards** (`eb1672e`): was 对比基准·通过 / 增益+4.2% / 导出 PDF
  (fabricated PASS + invented gain + dead export affordance); now 求解结果
  (real) + 基准对比 (real verdict or honest 无 gold 基准) + 证据产物 (honest
  artifact description, gated on a successful run, no fake CTA).
- **Constant deletion** (`eb1672e`): `POST_BLUEPRINT_KPIS` / `_RADIAL_GAUGE` /
  `_RIGHT_CARDS` / `_VERDICT` were DELETED, not just unused, so they cannot
  silently re-fake. Only the illustrative MINI_CHARTS + TABS tokens remain.

Tests: 980 vitest green · typecheck clean. New honesty contracts:
PostTelemetryHonesty (5) · postVerdictKpi (4) · postBlueprint retired-const (1).

## 关键发现 (key findings)

1. **De-fake surfaces hide in failure/fallback/loading states.** ALL THREE
   Codex rounds on C4 were about run-consistency in non-happy paths, never
   the happy path I'd verified visually:
   - R0 (3×P2) — failed-only cases collapsed to "待求解" (hiding real exit
     code/duration); the evidence card over-claimed artifacts with no
     successful run; the case-level residual gauge could describe a different
     run than the displayed surfaces.
   - R1 (1×P2 + 1×P3) — historical-success fallback rendered a plain green
     "成功" with no disclosure; the verdict's `loading` state flashed a false
     "无基准".
   - R2 (2×P2) — **my R1/R2 `loading` fix was itself a regression**:
     `useComparisonVerdict` returns `loading` for DISABLED queries, so
     unsolved/failed cases got stuck in "对比中…" forever; and the evidence
     card claimed matplotlib figures from solver-success alone, contradicting
     ReportFiguresPanel on matplotlib-missing builds.
   **Lesson**: a de-fake is only honest if it stays honest in the failure,
   fallback, AND loading states — the visual spot-check of one solved case
   can't surface those, and a fix for one edge state (loading disclosure) can
   regress another (disabled = perpetual pending). Edge-state honesty needs
   unit tests at the hook contract, not just visual confirmation.
2. **`showingFallbackRun` disclosure must be consistent across all Post
   chrome.** ModeRendererPost already had 历史成功/最新尝试; the new KPI strip
   + cards reintroduced the inconsistency until R1 caught it. When multiple
   components render the same run's status, the run-selection + disclosure
   logic should arguably be shared, not re-derived per component (future
   refactor candidate — noted, not done).
3. **Visual spot-check confirmed the happy path is genuinely real**, across
   both the default (DynamicFramePanel) and legacy (RightPanelV4) right-panel
   modes: gauge 48·收敛度·Uz, mini-charts 示意, KPI 成功/1.5s/0/6.5e-7/无基准,
   pill 无基准对比, cards 求解结果(real)+基准对比(无 gold)+证据产物(real),
   advisor framing "ADVISORY ONLY · 仅建议" preserved.

## 治理 (governance)

| Gate | Status |
|---|---|
| Four-question gate | ✅ LLM offline (no AI call in render) · artifacts canonical (foamToVTK/matplotlib provenance-labelled) · TrustGate (real verdict + honest no-baseline) · **AI advisory-only** ("ADVISORY ONLY · 仅建议" preserved on RightPanelV4) |
| Codex round cap=3 | ✅ R0 + R1 + R2 (final round) — R2's 2×P2 closed VERBATIM (no R3), one being a self-introduced regression I judged must-fix-before-ship rather than retro-queue. 0 P1 across all rounds. |
| Codex-verified trailer | ✅ `Codex-verified: RESOLVED` on HEAD (`a56ea27`) — cadence hook RISK-CLASS (508 LOC > 500) satisfied honestly; **no `CODEX_CADENCE_OVERRIDE`** used |
| confidence self-tag | high (all C4 commits) — Codex found 0 P1; all P2/P3 were non-happy-path consistency, closed inline/verbatim |
| Visual spot-check | ✅ mandatory pre-close check done (real solved case `9da7c214`, both default + legacy panel modes) |
| Notion sync | DEC-V61-205 (M5 charter) — sync at session-end if Status=Accepted |
| No date/schedule gating | ✅ |

## 下一步 / 风险 (next / risks)

- **RightPanelV4 renders only in `?legacy=1`** — the default view shows
  DynamicFramePanel. The C4 right-card de-fake is code-correct + tested but
  only user-visible in legacy mode. Worth confirming DynamicFramePanel itself
  carries no fabricated post telemetry (it showed solve-readiness, not fake
  results — likely fine, not audited this cycle).
- **Shared run-selection/disclosure helper** — the `showingFallbackRun` +
  `successfulRunDetail ?? runDetail` logic now lives in 3 components. A small
  shared hook would prevent the next divergence (the exact class of bug Codex
  R1 caught). Low priority.
- **Optional enhancement** — color the Post surface overlay by pressure `p`
  (varies on no-slip walls) instead of |U| (≈0 on walls). Noted in C2, not
  required.
- **M5 COMPLETE** — Post view is honest end-to-end. Next milestone per
  roadmap_v2: M6 (AI advisor stack) — but per `feedback_claude_code_is_the_advisor`
  the advisor UI is the Claude Code session itself, so M6 scope is narrow.
