# DEC-V61-120 · AI coach chat panel UI · Codex pre-merge chain

**Backend (intended)**: 86gs `gpt-5.4` xhigh (initial); CRS `gpt-5.4` high reserved as fallback. **Actually executed**: CRS only — 86gs hit Cloudflare 522 on R1 attempt; switched to CRS-default for R2 per V61-119 §L2 sustained-instability lesson.
**Trigger**: RETRO-V61-001 multi-file frontend + new operator-facing UI surface + LLM-streaming consumer + post-user-UX-criticism first implementation
**Scope**: 5 files initial · 1047 LOC across `api/client.ts` (extend), `step_panel_shell/AICoachPanel.tsx` (new), `step_panel_shell/TaskPanel.tsx` (extend), `__tests__/AICoachPanel.test.tsx` (new), DEC
**Self-estimated pass rate**: 60% (predicted 3-4 rounds)
**Actual**: 2 rounds — even better than V61-119's 3-round cycle; scope-down discipline (no tool calling, no actions) kept findings to single-axis UX/contract issues

---

## Round-by-round summary

| Round | Commit | Findings | Severity | Verdict | Backend |
|---|---|---|---|---|---|
| R1 | f094f17 | 2 | P1 + P2 | CHANGES_REQUIRED | CRS gpt-5.4 high (after 86gs 522) |
| R2 | 8dabc54 | 0 | — | **APPROVE clean** | CRS gpt-5.4 high (default per V119 §L2) |

---

## Round 1 · CHANGES_REQUIRED · 1 P1 + 1 P2

- **P1 · Interrupted assistant turns leak into request history.** When a stream is cancelled (abort) or errors mid-flight (`onError` non-abort path), the panel flipped the placeholder assistant turn from `streaming: true` to `streaming: false` and left it in state. The next send's history filter `filter((t) => !t.streaming)` then forwarded that turn, breaking retries in two concrete ways: (a) abort BEFORE first delta produces an assistant turn with `content: ""`, which the V119 backend's `CoachHistoryMessage.content min_length=1` validator rejects as 422; (b) mid-stream error produces a TRUNCATED assistant reply that the LLM then sees as if it were complete prior context. **Fix**: introduce `complete: boolean` flag on `ChatTurn` set ONLY by `onDone`. History filter requires `t.role === "user" || t.complete === true`. User turns are always eligible (they have real content and never enter a streaming state). Two new tests cover the abort-before-delta and mid-stream-error retry paths.

- **P2 · IME composition Enter submits prematurely for CJK input.** Engineers using a Chinese / Japanese / Korean IME press Enter to commit the active candidate from the IME popup; the panel's keydown handler interpreted that as "submit" and shipped partial pinyin/romaji to the backend. **Fix**: guard on `e.nativeEvent.isComposing` (modern browsers) plus `keyCode === 229` (older Safari / legacy). New test asserts both flags suppress submit and a clean Enter still submits with the composed CJK content (`你好`).

## Round 2 · APPROVE clean · 0 findings

**Backend**: CRS `gpt-5.4` high. Verbatim verdict (Codex):

> "I didn't find any discrete, introduced regression in the history filtering or IME handling changes. The new logic is consistent with the surrounding request/stream contract and the added tests cover the intended paths."

86gs not attempted on R2 — V61-119 §L2 default-to-CRS workflow change applied for the first time, validated cleanly. Saves ~5 minutes wall-clock per round vs the retry-86gs-then-fallback pattern.

---

## Methodology lessons

### L1 · V61-119 §L2 default-to-CRS workflow change is now operational

This is the first arc where R2 went DIRECTLY to CRS without re-attempting 86gs after the R1 failure. Wall-clock saved: ~5 minutes (no second 522 timeout cycle). Self-pass-rate calibration on this anchor: 86gs sustained instability + frontend-only changes work cleanly on CRS. Recommend codifying in CLAUDE.md relay protocol: "if the immediately-preceding round on this arc failed via 86gs, default to CRS for the next round; restore 86gs-first only after 24h or after CRS itself fails on a round."

### L2 · Frontend SSE consumer + new UI panel anchor: 60% / 2-3 rounds

V120 calibration anchor confirmed at 2 rounds (predicted 60% / 3-4). Findings clustered on (a) the request/response contract boundary (history filter — backend constraint mismatch) and (b) accessibility / locale (IME composition). Both are well-trodden traps but small enough that single-round fixes apply. No cascade dimension: history filter does not interact with IME handling does not interact with SSE parsing.

### L3 · "Read-only adviser" V1 scope continues to pay off

V120 has zero risk surface for action execution / tool calling because the DEC explicitly scoped both out of V1. Findings are concentrated in the small, predictable axes the actual change introduces (history serialization, keyboard event handling, streaming display). V61-121 will reintroduce action-execution risk via tool calling — the V120-V121 split is the right partition.

### L4 · Codex's CJK awareness is a calibrated find

The IME composition issue (R1 P2) would have shipped to a Chinese-speaking user base and produced a high-frustration bug report. Codex caught it on a static review without simulating IME state. This is exactly the kind of locale-aware finding that justifies the per-risky-PR Codex baseline for any CJK-targeted UI. Worth noting for future intake-template risk_flag candidates.

---

## Files comprising V61-120

```
.planning/decisions/2026-05-04_v61_120_ai_coach_chat_panel_ui.md
ui/frontend/src/api/client.ts                                       (extend: streamAICoach + types)
ui/frontend/src/pages/workbench/step_panel_shell/AICoachPanel.tsx   (new ~290 LOC after R1 fix)
ui/frontend/src/pages/workbench/step_panel_shell/TaskPanel.tsx      (extend: mount AICoachPanel)
ui/frontend/src/pages/workbench/step_panel_shell/__tests__/AICoachPanel.test.tsx  (15 tests)
reports/codex_tool_reports/v61_120_r1_chain.md                       (this file)
```

15 panel tests pass. Frontend suite 201 pass (was 198 pre-V120). TypeScript clean.

## Successor pointers

- **V61-121 (immediate next)**: Tool-calling protocol + approval UX. Extends `streamAICoach` callbacks with `onToolCall`; AI emits structured tool_call frames; UI surfaces them as proposals with [Accept] / [Reject] / [Edit] inline; backend dispatches approved actions through existing route handlers. The actual differentiation step vs Fluent/StarCCM (AI gains hands).
- **RETRO follow-up**: codify "default-to-CRS-after-failure-on-this-arc" workflow refinement in CLAUDE.md relay protocol per §L1.
