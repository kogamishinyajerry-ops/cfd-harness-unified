# M5.5 close · Truth-chain extension to the construction steps · 2026-05-26

> Parent charter: DEC-V61-206 · M5.5 sub-DEC arc (C2 → C3 → C4)
> Commits: `9fef4ca` (charter) → `6c84e25` (C2 Tier-1) → `c90065c` (C3 DOE) →
> `b3ce291` (Codex R0 fixes) → `7d82a3a` (Codex R1 fixes) → `eca0836` (C4 boundary
> + DOE R2 P2) → `c3c9cd5` (C4 R1: boundary de-fake across the whole shell +
> setup-bc provenance fix) · pushed `455f34d..4f45921`
> Codex arc (86gs gpt-5.4 xhigh, code-only diff — STL artifact excluded):
> C2/C3 arc: R0 CHANGES_REQUIRED (2 P1 + 2 P2 + 1 P3) → R1 CHANGES_REQUIRED (2 P1)
> → R2 APPROVE_WITH_COMMENTS (1 P2 closed inline) · round cap=3 reached.
> C4 arc (reviewed separately): R0 CHANGES_REQUIRED (1 P1 + 2 P2) → R1
> CHANGES_REQUIRED (1 NEW P2: false setup-bc provenance) → resolved verbatim
> (v2.3 verbatim exception, round cap not consumed). Trailer verdict: RESOLVED.

## 做了什么 (what)

M5 de-faked only the Post step. After the turbine full-pipeline dogfood the user
observed the OTHER steps (esp. 边界设置 / 设计探索) still show fabricated SVG
telemetry. M5.5 extended the M5 truth-chain pattern — real run-derived data, or
an explicit 示意/待识别 state, never silent fake data — to the construction steps.

**C2 · Tier-1 fake-as-truth** (`6c84e25`): Physics dropped the hardcoded
`Re 8.4e5 · Pr 0.71`; Mesh's `18.86M · skew 0.128` fallback → `尚无网格指标`;
Solver iter overlay → real `迭代 N · 用时 HH:MM:SS` (live-verified on the turbine:
`迭代 13366 · 用时 00:09:03`); Solver KPI strip → real run-truth (`成功/543.6/0/
1.4e-6`, was a fabricated `18.76M/248.6/3.62/96.4/65`).

**C3 · DOE** (`c90065c`): the entirely-fabricated design-exploration step
(8 sample thumbnails with invented pressure/temperature, a Pareto "最优解 V-12",
`28/212.6/94.1/18h42m` KPIs) got a prominent 示意 banner + dimming + honest KPI
placeholder. No real sweep backend exists, so the honest treatment is "clearly
illustrative", not fake optima.

**C4 · boundary** (`eca0836`): the user's explicit complaint ("边界条件设置窗口里
总是 SVG 图，是 fake 的"). Real geometry now renders (was a fabricated SVG engine
scaffold); no-patches counts → honest 待识别. Plus the Codex R2 DOE "最优解 V-12"
close.

**C4 R1 · boundary shell** (`c3c9cd5`): Codex C4 R0 caught that the de-fake was
incomplete — I had fixed the center renderer + KPI strip but the boundary fake
ALSO rendered in the shell (LeftRailV4 `61/62` recognition + 入口×28 tree counts;
RightPanelV4 "AI 识别完成 98.4%" card + invented inlet/outlet CTAs; the no-GLB
scaffold's `x{count}`/`confirm x1`). Fixed all three surfaces + added 2 shell
regression guards. C4 R1 then caught a 4th-instance NEW falsehood (see finding
#1): the "honest" replacement card's 来源 said "运行 setup-bc 后入库", but this
panel reads the workbench-basics endpoint, not setup-bc — so a user following
that hint would still see 待识别. Corrected to "workbench-basics（暂无边界面）".

## 关键发现 (key findings)

1. **De-faking is itself error-prone — a fix can introduce a NEW fake.** Codex
   caught FOUR of my "honest" replacements that were themselves false:
   - Solver temperature "不可压缩求解无能量方程" — FALSE for the thermal solvers the
     backend supports (buoyantSimpleFoam/buoyantPimpleFoam). Two rounds to land
     on fully renderer-scoped wording ("温度时程暂未接入此视图") that claims nothing
     about the run or physics.
   - Physics velocity legend "待求解" — didn't land: the viewport kernel forces a
     blueprint scalar range, so the legend was still blueprint-scaled. The step
     is pre-solve → the legend is inherently illustrative (示意).
   - Solver KPI strip mirrored the Post pattern (`successfulRunDetail ?? runDetail`),
     which for the Solver step would report a FAILED latest run as 成功. Solver
     must key on the latest run.
   - **(C4 R1)** Boundary no-patches card 来源 = "运行 setup-bc 后入库" — a false
     *action* claim. The panel reads the workbench-basics endpoint
     (`knowledge/workbench_basics/<case>.yaml`); setup-bc fills the manifest, not
     that source. The honest card told the user to do something that would NOT
     fix the displayed state. Corrected to name the true source with no fix
     instruction.
   **Lesson**: "replace fake with honest" needs the same scrutiny as the
   original claim — the honest replacement must be true in EVERY case
   (all solver families, pre/post-solve, latest-vs-historical run, and the
   *provenance/next-action* text too, not just the numbers). The
   renderer-scoped rule (state only what THIS component can verify) is the
   safest default; a "来源 / 运行 X" hint is a claim and must be verified against
   the actual data path. Codex's independent read was load-bearing on all four;
   the visual spot-check alone would not have caught any of them.

   **Corollary (C4 R0)**: a de-fake must cover EVERY component that renders the
   same data, not just the obvious one. I de-faked the center renderer + KPI
   strip and thought boundary was done — but the same fake rendered in the left
   rail and right panel shell. The truth-chain is only as honest as its leakiest
   surface. Fix: grep every consumer of the faked constant (here
   `BOUNDARY_BLUEPRINT_*`) and de-fake all of them in one cycle; add a regression
   guard per surface so a re-fake fails a test.

2. **The boundary fake is a symptom of a deeper architecture gap.** The
   `workbench-basics` endpoint only serves hand-authored
   `knowledge/workbench_basics/<case>.yaml` (the ~10 canonical cases). EVERY
   imported case (including the turbine just proven end-to-end) gets a 404 →
   `ctx.basics` empty → boundary/physics/etc. fall back to ALL blueprint fakes.
   The real patch data exists in `case_manifest.yaml` but is never surfaced. C4
   stops the fake-as-truth (real geometry + honest placeholders), but the
   **real fix is a backend manifest→WorkbenchBasics deriver** so imported cases
   show real patch lists / counts / BC — deferred as the M5.5 follow-up
   (milestone-class; would fix all steps for imported cases at once).

3. **The dogfood + the de-fake reinforced each other.** The turbine dogfood gave
   a real solved imported case to spot-check every de-fake against (real iter
   count, real wall time, real geometry). Without it, the "looks plausible"
   fakes (28/27 patches, 543s) would have been much harder to distinguish from
   real values.

## 治理 (governance)

| Gate | Status |
|---|---|
| Four-question gate | ✅ all changes are read-only display of solve/mesh artifacts; no LLM, no AI action; honest provenance |
| Codex round cap=3 | ✅ C2/C3 arc: R0 → R1 → R2 (cap), APPROVE_WITH_COMMENTS, last P2 closed inline. C4 arc: R0 → R1 (CHANGES_REQUIRED, 1 new P2) → verbatim fix (round cap NOT consumed per v2.3 verbatim exception). |
| Codex governance relay | ✅ 86gs gpt-5.4 xhigh, code-only diff (104k-line STL artifact excluded as non-reviewable data) |
| No cadence override | ✅ push gated on the real Codex review + canonical `Codex-verified: RESOLVED` trailer, NOT `CODEX_CADENCE_OVERRIDE`. Cadence floor hook PASSED. |
| Visual spot-check | ✅ turbine case, each step: physics 示意 legend, mesh, solver (real iter/KPI/temp), DOE banner, boundary real geometry |
| confidence self-tag | high (all commits) |
| No date/schedule gating | ✅ |

## 下一步 / 风险 (next / risks)

- **manifest→WorkbenchBasics deriver** (the real boundary/physics fix · finding
  #2) — derive patches/geometry/solver/BC from `case_manifest.yaml` when no
  hand-authored basics yaml exists, so imported cases show real data across all
  steps. Milestone-class backend feature; the highest-value follow-up.
- **Geometry step intake fallback** (`17 零件 · 2 缝隙`) + **Solver host telemetry
  chips** (GPU/CPU/MEM — needs a real backend; currently disclaimer-only) —
  remaining Tier-2/3 items from the surface-scan, lower severity.
- **Dead blueprint constants** — several `*_BLUEPRINT_*` constants are now unused
  by the renderers (still imported by their *.test.ts). Deleting them (M5
  pattern: "delete fake constants so they can't silently re-fake") + updating
  the blueprint tests is a clean follow-up cycle.
- M5.5 construction-step truth-chain: **fake-as-truth removed across
  physics/mesh/solver/DOE/boundary**; real data shown where wired, honest
  示意/待识别 where not.
