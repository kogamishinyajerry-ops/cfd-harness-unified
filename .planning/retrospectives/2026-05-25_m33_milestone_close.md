# RETRO · M3.3 Real-User UX Validation milestone close · 2026-05-25

> Charter: close M3.2 retro § "What went poorly" #4 — "no real engineer used the toast / no real-user UX validation for cycles 4-5".
> Counter snapshot: M3.3 = 3 single-functionality sub-DECs (cycles 1-3) = **+0 to `autonomous_governance_counter_v61`** (all cycles are commit-message-only sub-DECs per v2.3 round-1 loosen — no DEC files filed).
> Kogami: not invoked (v2.3 opt-in only; user did not request).
> Codex: **0 invocations across all 3 cycles** (no risk-tier hits · test infra + visual fix + doc-only).
> post-R3 defects observed: **0** (no Codex review involved; not applicable).
> Multi-agent crew: activated mid-cycle 2 (user-mandated). 2 parallel Sonnet 4.6 subagents at cycles 2 + 3.

## Outcome

M3.3 ships **the real-user UX validation arc** that M3.2 retro predicted was missing:

- **Cycle 1** (`11ce392`): stage demo case `m33_ux_demo_seed` + start uvicorn :8001 + vite :5173 + verify backend serves rail with `severity` / `field_path` / `body_text`. Env setup for real-engineer click-through.
- **Cycle 2** (`26fafbc`): user-driven visual spot-check exposes 4 visual defects (A1-A4) in M3.2 cycles 4-5 UI affordances. Visual fix + cross-track backlog + permanent spot-check tool + methodology doc. Bundled because the user-triggered defect cascade exposed not just the A1-A4 fixes but the full process gap.
- **Cycle 3** (`f2eddd9`): cross-step spot-check (mesh / physics / boundary) reframes B1-B5 findings as step=geometry-specific empty-state cluster. Documentation-only commit (no production code change).

The milestone is a **process-light counter-experiment in the opposite direction from M3.2**: where M3.2 demonstrated v2.3 round-1 loosen at moderate scale (3 sub-DECs + 2 spike + 2 single-functionality), M3.3 demonstrates v2.3 at its **lightest** — every cycle is single-functionality sub-DEC, no DEC files, no Codex, no Kogami, no Notion sync. **The absence of these data is itself the data.**

## Arc map

| Cycle | Sub-DEC type | What landed | Codex rounds | Commit |
|---|---|---|---|---|
| 1 | single-functionality sub-DEC | demo seed + dev servers + backend verification | — (no Codex, test infra) | `11ce392` |
| 2 | single-functionality sub-DEC (bundled) | A1-A4 visual fix + spot-check tool + methodology doc + B1-B5 backlog | — (no Codex, visual + doc) | `26fafbc` |
| 3 | single-functionality sub-DEC | cross-step spot-check reframes B1-B5 as step=geometry-specific | — (no Codex, doc-only) | `f2eddd9` |

Total Codex synchronous invocations: **0** across 3 cycles (vs M3.2's 6, vs M3.1's 29). Driver = all M3.3 work is process-class-skip eligible (test infra / visual fix / doc-only) with zero risk-tier hits.

## User-ratification frequency

- All 3 cycles: **N/A** (no Codex involvement)

This continues M3.2's process-class trend (cycles 4-7 were also N/A). M3.3's 100% N/A rate is **expected** for a milestone whose entire scope is visual UX validation + doc capture — none of which is risk-tier triggering. The cycles that needed Codex would have gotten it; none did.

## What went well

1. **Multi-agent crew architecture worked first-time**. User explicitly invoked it mid-execution at cycle 2. Cycles 2-3 used parallel Sonnet 4.6 subagents: S1 wrote cross-track backlog (72 LOC), S2 wrote spot-check tool (67 LOC ≤ 80 cap) + methodology doc (60 LOC). Main session orchestrated, verified subagent outputs via Read before commit. No briefing/output thrash, no re-iteration loop. Clean structured artifacts.

2. **Spot-check tool generalized correctly on first iteration** after ESM module-resolution fix. 67 LOC tool, 60 LOC doc. Reusable for future UI milestones — every cycle touching `ui/frontend/src/pages/workbench/` can now reference this tool.

3. **Cross-step audit immediately reframed B1-B5 cluster**. 3 steps × 30 seconds each → all 5 findings reclassified from "workbench-wide" to "step=geometry-specific when CAD is absent". Saved future investigation cost; likely single-root-cause = missing empty-state component for pre-CAD-upload state.

4. **User UX feedback → fix-shipped tight loop**. Cycle 1 set up env · user clicked through · user surfaced "UI 总工程师呢" complaint · cycle 2 fixed A1-A4 + tooled the gap. Same session, no context loss.

5. **AI advisor-not-driver contract held**. Four-question gate (LLM offline / artifacts canonical / TrustGate / advisor-only) answered Y/Y/Y/Y for every cycle including subagent-produced artifacts.

## What went poorly

1. **The whole reason M3.3 exists is a process failure from M3.2**. M3.2 closed with happy-path E2E "7/7 PASS" but the UI was visually broken in 4 specific ways. Unit + Playwright tests assert testid + click semantics; **neither validates visual layout, proportion, contrast, or discoverability**. The M3.2 retro's own §"What went poorly" #4 ("no real-user UX validation") was a self-prediction; M3.3 is the proof. This is a methodology-class gap, not a one-off.

2. **I shipped M3.3 cycle 1 by setting up the env without screenshot-spotting first**. Same blind spot as M3.2 cycles 4-5. User had to catch it AGAIN at the demo handoff. Process change to mandatory cycle-close screenshot only got codified at cycle 2 (the methodology doc), not before. Two-strike pattern; the rule needs teeth.

3. **ESM module resolution glitch on first subagent script handoff**. Subagent S2 wrote a correct-LOC spot-check script but used `import { chromium } from "playwright"` — works only when CWD has playwright in node_modules ancestry. Main session had to fix to `new URL(...)` pattern with explicit module path. Should bake "ESM modules don't follow CWD" into the subagent briefing template for any Node script handoffs going forward.

## V130 four-question gate audit (every M3.3 cycle answers Y/Y/Y/Y)

| Cycle | LLM offline | Artifacts canonical | TrustGate-explainable | Advisor-only |
|---|---|---|---|---|
| 1 | ✓ | ✓ (real manifest + audit JSONs from demo seed) | ✓ (provenance toggle in rail) | ✓ (env setup) |
| 2 | ✓ | ✓ (existing rail content rendered correctly) | ✓ (severity / field_path / body_text visible) | ✓ (visual + doc work) |
| 3 | ✓ | ✓ (cross-step screenshots captured) | ✓ (step-rail step state explainable) | ✓ (doc-only) |

All 3/3 cycles Y/Y/Y/Y.

## Codex round cap=3 observance per cycle

| Cycle | Rounds used | Closure | At-cap? |
|---|---|---|---|
| 1-3 | 0 | n/a (process-class skip) | n/a |

**Zero cycles invoked Codex.** All 3 cycles bypassed via single-functionality sub-DEC + no risk-tier hit. v2.3 round-1 loosen applied at its lightest configuration. If a future cycle in this domain hits charter-class scope (e.g., the M3.4 empty-state work touches ≥3 shared code paths), the cap=3 will matter again.

## Cross-track findings (B1-B5) — dispatch targets

Originally surfaced as "workbench-wide" cluster at cycle 2 user spot-check; reframed at cycle 3 cross-step audit as **step=geometry-specific when CAD is absent**.

1. **B1 · MainCanvas viewport error** (P1) → suggested track: V4 shell empty-state / VtkCanvas
2. **B2 · bottom-center number collision** (P2) → suggested track: V4 shell layout (same as B5)
3. **B3 · bottom banner duplicates rail content** (P2) → suggested track: M3.0 charter (DynamicBottomCards rendering policy)
4. **B4 · left sidebar empty space** (P3) → suggested track: V4 shell layout
5. **B5 · step rail overlap** (P2) → suggested track: V4 shell layout

**Reframed root cause hypothesis**: all 5 manifest as broken widgets when geometry step renders with no CAD upload. Likely single root cause = missing empty-state component for pre-CAD-upload state. Recommends a single-arc fix (see M3.4 charter proposal §1).

## Methodology lessons captured

1. **Visual spot-check is non-negotiable for UI cycles**. Codified at `.planning/methodology/screenshot_spot_check.md`. Every cycle touching `ui/frontend/src/pages/workbench/` MUST reference a screenshot path in its closing commit message. Unit + Playwright tests are necessary but not sufficient.

2. **Subagent briefings must include "module resolution context"** when handing off Node scripts. ESM bare-specifier resolution is location-based, not CWD-based. Default to `new URL(..., import.meta.url)` for any cross-directory imports. Bake into the subagent briefing template.

3. **Cross-step spot-check is a cheap diagnostic primitive**. 3 steps × 30 seconds → reframed 5 findings from "workbench-wide" to "step-specific". Should be standard first move for any UI defect investigation before escalating to root-cause analysis.

4. **User-triggered UX validation is the highest-leverage signal we have**. Unit tests test logic; Playwright tests test integration; **only a real engineer's eye catches visual proportion / discoverability / contrast issues**. Every milestone must have ≥1 cycle with user-clicked-through validation, ideally before milestone-close.

## Open questions for M3.4 charter

1. **What's M3.4's theme?** Two candidates surface from M3.3:
   - **(a · top recommendation)** "Geometry step graceful empty-state" — fix the empty-state UX so when a case has no CAD upload, step=geometry renders a clean placeholder instead of broken widgets cascading. Closes B1-B5 cluster in one milestone arc. Scope-natural extension of workbench-dynamic-guided (DEC-V61-202).
   - **(b)** original M3.3 close-list (Open in IDE / Raw YAML modal / Replace whole node UI recovery) — smaller-scope, less user-pain alignment.
   - User decides; this retro recommends (a) but does not pre-commit.

2. **Should the screenshot-spot-check rule have a pre-commit hook?** Mandatory methodology only works if the rule has teeth. Options: (i) honor system (current), (ii) commit-msg trailer (`Screenshot-spot-check: <path>` for UI commits), (iii) pre-commit hook scanning staged paths and requiring the trailer. v2.3 cadence-floor THRESHOLD 30 suggests against hooks; commit-msg trailer is the middle ground.

3. **Multi-agent crew threshold**. M3.3 used it for doc + tool generalization (low-stakes parallel work). Should there be a heuristic for when crew is worth it vs main session sequential? Default rule of thumb after M3.3: if 2+ artifacts can be produced in parallel with ≤80 LOC each and clear contract boundaries, crew is positive ROI. Below that, main session is cleaner.

## Recommendations for M3.4

1. **Pick (a) "Geometry step graceful empty-state"** as M3.4 charter. B1-B5 cluster is the highest-pain user-visible bug class in current workbench. One milestone arc closes it.

2. **Open with a 1-paragraph charter at cycle 1** (carry M3.2 retro recommendation forward). M3.3 worked without one because scope was so tight, but M3.4 empty-state will touch multiple components.

3. **Mandate screenshot spot-check at every UI cycle close**. Use the `.planning/methodology/screenshot_spot_check.md` tool. Commit message must reference a screenshot path or explicitly note "no UI surface touched".

4. **Update subagent briefing template** to include the "ESM module resolution" pattern. One-line addition: "For any Node script handoffs, use `new URL(..., import.meta.url)` for cross-directory imports; do not rely on CWD-based bare specifier resolution."

5. **Keep process-class diversification active**. M3.3 demonstrates that "no DEC, no Codex, no Kogami" is a valid milestone shape when scope is genuinely process-light. Don't artificially escalate M3.4 if scope stays bounded.

## Counter telemetry

| Milestone | Cycles | Counter delta | Codex rounds | post-R3 defects | User-ratifications |
|---|---|---|---|---|---|
| M3.0 | ? | ? | ? | ? | ? |
| M3.1 | 8 | +8 | 29 (avg 3.2) | 0 | 4 (50%) |
| M3.2 | 7 | +3 | 6 (avg 2.0 for cycles 1-3 · 0 for 4-7) | 0 | 0 (cycles 1-3 only) |
| M3.3 | 3 | +0 | 0 | 0 (n/a) | N/A (all cycles) |

Cumulative M3 counter delta unchanged by M3.3 (still ~+16 from M3.0 + M3.1 + M3.2). M3.3 is the **lightest-process M3 milestone to date** — entirely below the v2.3 process-class threshold.

## Bottom line

M3.3 ships in **3 cycles · 0 counter delta · 0 Codex rounds · 0 Kogami invocations · 0 Notion sync candidates · process-light by design**. The milestone exposed AND fixed the very gap it was created to address (M3.2 retro #4: no real-user UX validation).

The cross-step audit (cycle 3) reframed B1-B5 from "workbench broken" to "geometry step empty-state broken" — high-value triage in 90 seconds of tool runs. Multi-agent crew architecture (user-mandated at cycle 2) ran 2 parallel Sonnet subagents producing clean structured artifacts on first iteration after one ESM fix.

**The absence of Codex / Kogami / Notion data is itself the validation signal**: v2.3 round-1 loosen at its lightest configuration produced a defect-free arc with a real user-driven UX fix shipped same session. The empirical case for "process-light when scope is genuinely light" is strengthened.

**Recommendation**: close M3.3 · no Notion sync needed (zero Accepted DECs filed; per v2.3 Notion-only-syncs-Accepted) · open M3.4 with "Geometry step graceful empty-state" as proposed theme per §Recommendations #1.
