---
decision_id: DEC-V61-120
title: AI coach chat panel · TaskPanel right-rail mount · streaming consumer for /api/ai-coach/stream
status: Accepted (2026-05-04 · Codex pre-merge 2-round chain APPROVE on commit 8dabc54 [R1 P1+P2 → R2 clean]; chain report at reports/codex_tool_reports/v61_120_r1_chain.md; user 2026-05-04 mandate "先打 #1" covers acceptance flip · the AI coach is now visible in the UI — first user-visible deliverable of the differentiation pivot)
codex_tool_report_path: reports/codex_tool_reports/v61_120_r1_chain.md
codex_review_relay: CRS gpt-5.4 high (R1 fallback after 86gs 522, R2 default-to-CRS per V61-119 §L2 sustained-86gs-instability protocol — first arc to operationalize the workflow change)
authored_by: Claude Code Opus 4.7 (1M context)
authored_at: 2026-05-04
authored_under: User 2026-05-04 mid-session pivot — quote verbatim "推进到什么进度了？我感觉仍然没什么变化啊？并没有完成对标Fluent、StarCCM的转向啊". User authorized 2-step arc F→G ("先打 #1") to (a) finally make the AI coach VISIBLE in the UI (V61-120) and (b) give the AI hands-on capability via tool-calling + approval flow (V61-121). The five-DEC arc V61-115..V61-119 delivered foundations but the user-visible surface barely moved; this 2-step arc closes the foundation-to-differentiation gap.
parent_decisions:
  - DEC-V61-119 (LLM coach SSE backend · this DEC's data source — `POST /api/ai-coach/stream` consumed verbatim, no backend changes required for V120 V1)
  - DEC-V61-118 (LLM provider foundation · prerequisite plumbing, transitive)
  - DEC-V61-116 (case completeness analyzer · the system prompt's grounding data, transitive via V61-119)
  - DEC-V61-117 (StepTree Fluent hierarchy · the right-rail layout shell V120 mounts INTO; V117 hardened TaskPanel state-machine; V120 lives BELOW per-step Body, ABOVE StepNavigation)
  - DEC-V61-098 (M-AI-COPILOT rule-based AIActionEnvelope · this DEC's PARALLEL track; rule-based deterministic actions stay in DialogPanel + AnnotationPanel; V120's free-form chat is a distinct surface; V61-121 will rejoin the two via tool-calling)
  - DEC-V61-088 (pre-implementation surface scan rule · this DEC carries Surface-scan trailer)
  - RETRO-V61-001 (risk-tier · multi-file frontend + new operator-facing UI surface + LLM-streaming consumer = mandatory Codex pre-merge)
parent_artifacts:
  - ui/frontend/src/pages/workbench/step_panel_shell/TaskPanel.tsx:28-64 (V117 layout · V120 inserts AICoachPanel between Body div and StepNavigation; existing structure is the integration point)
  - ui/frontend/src/pages/workbench/step_panel_shell/CompletenessCard.tsx (V116 sibling · V120 follows same right-rail card patterns: text-xs font-mono, surface-* tokens, no new design system additions)
  - ui/frontend/src/api/client.ts (existing API client · V120 adds `streamAICoach(...)` method; existing methods follow fetch-based pattern)
  - ui/backend/routes/ai_coach.py:108-122 (V119 SSE endpoint · V120 consumes verbatim; pre-stream HTTP error mapping from V119 R1 P1 means UI needs to handle 401/429/400/502/500 BEFORE opening reader as well as mid-stream `error` SSE frames — UI logic mirrors backend dual-path)
  - ui/backend/services/llm_provider/base.py:68-85 (ChatStreamChunk schema · UI parses to this shape)
counter_impact: +1 (autonomous_governance: true · new UI surface + new API client method, NOT a governance-rule change. Kogami-trigger check: not a phase-close, not a RETRO draft, not arc-size retro at counter 79, not a governance-rule-change DEC. High-risk PR check: this is a USER-FACING UI change after explicit user UX criticism — RETRO-V61-001 "user UX批评后的首次实现" trigger DOES fire. Codex pre-merge MANDATORY. Kogami still SKIP per DEC-V61-087 §4.2 — this is a feature DEC, not a governance rule change · same disposition as V117/V120 sibling pattern.)
notion_sync_status: pending — Notion MCP server still disconnected; sync when reconnected
self_estimated_pass_rate: 60% (predicted 3-4 rounds) → ACTUAL 2 rounds (well-calibrated overestimate · scope-down kept findings to single-axis UX/contract issues · IME-composition CJK find from Codex was the calibrated win that would have shipped to user base otherwise — see chain report §L4)

---

# DEC-V61-120 · AI coach chat panel UI

## Why now

User feedback verbatim 2026-05-04:

> 推进到什么进度了？我感觉仍然没什么变化啊？并没有完成对标Fluent、StarCCM的转向啊

The five-DEC arc V61-115..V61-119 delivered backend plumbing + cosmetic UI but **the AI coach is not visible anywhere** in the engineer's workbench. V61-119 V1 explicitly scoped frontend out. This DEC closes that gap as item F of a 2-step arc F→G:

- **F (this DEC, V120)**: Mount the chat panel in TaskPanel right rail. Engineer can ask the AI questions about their case; AI responds via streamed completion grounded in V61-116's completeness snapshot. **No actions** — read-only adviser.
- **G (next DEC, V121)**: Tool-calling protocol so AI can propose case modifications; user approves via inline diff before they apply. This is the actual differentiator vs Fluent/StarCCM.

V120 is the visible-progress half of the differentiation arc. After it lands, an engineer opening the workbench will see — for the first time — an AI assistant offering grounded help inside the right rail.

## Surface scan (per DEC-V61-088)

**ROADMAP scan**: post-W5 + workbench-rollout roadmaps return zero hits for `chat_panel` / `coach_panel` / `AICoach`. M-AI-COPILOT (DEC-V61-098) defined `AIActionEnvelope` for rule-based deterministic actions; that surface lives in `DialogPanel` + `AnnotationPanel` for the structured-action flow. V61-119 added the free-form streaming chat backend with no UI; V120 adds the matching UI.

**Existing-implementation grep** (`grep -rln "ChatPanel\|ai-coach\|ai-chat" ui/frontend/src/`):
- Zero matches for `ChatPanel` or any chat-shaped component
- `api/client.ts` has no AI methods yet
- Existing right-rail panels (DialogPanel 296 LOC, AnnotationPanel 199 LOC, PatchClassificationPanel 349 LOC) are structural references — V120 follows their conventions but is not a refactor of any of them
- Existing `AIActionEnvelope` consumer (DialogPanel.tsx) is the rule-based path; V120's free-form chat is a parallel structure

**Disposition**: **parallel-new** — chat panel is structurally distinct from rule-based AIAction panels. Both paths coexist in the same TaskPanel right rail. V61-121 will introduce a bridge (tool-calling lets the chat panel emit AIActionEnvelope-shaped proposals).

**Surface-scan trailer**: commits will carry `Surface-scan-found: ui/frontend/src/pages/workbench/step_panel_shell/{TaskPanel,DialogPanel,AnnotationPanel}.tsx, ui/frontend/src/api/client.ts · disposition: parallel-new (AICoachPanel + streamAICoach client method); zero existing chat-panel code`.

## Decision

Add a single new component `AICoachPanel.tsx` mounted in `TaskPanel` between the per-step `<Body>` and the bottom-pinned `StepNavigation`. The panel consumes `/api/ai-coach/stream` via a new `streamAICoach()` method on the API client. V1 ships read-only chat with streaming display; **no tool calling, no action execution, no persistence** (deferred to V61-121).

### Architecture (V1 scope)

```
ui/frontend/src/api/
  client.ts                        — EXTEND: add streamAICoach(req, callbacks) method;
                                    fetch + ReadableStream + line-buffered SSE parse;
                                    parses each `data: {json}\n\n` frame; surface
                                    delta / done / error / pre-stream HTTP error.

ui/frontend/src/pages/workbench/step_panel_shell/
  AICoachPanel.tsx                 — NEW: chat UI component (~250 LOC budget).
                                    Pinned-bottom region in TaskPanel, ~280px
                                    fixed-height (mobile-friendly). Internal scroll
                                    for message history. Input + send + stop +
                                    error pill. Session-scoped history (useState).
  TaskPanel.tsx                    — EXTEND: insert <AICoachPanel caseId={caseId} />
                                    after the scrollable Body div, before
                                    <StepNavigation>. Layout split: scrollable
                                    region for completeness+body (flex-1 min-h-0)
                                    + fixed bottom AICoachPanel + StepNavigation.

ui/frontend/src/pages/workbench/step_panel_shell/__tests__/
  AICoachPanel.test.tsx            — NEW: vitest + Testing Library.
                                    Coverage: render empty state, send-then-
                                    receive-chunks, error-frame display, pre-
                                    stream 4xx/5xx display, stop button cancels
                                    in-flight request via AbortController,
                                    aria contracts for a11y, no-API-key mock-
                                    mode banner surfaces "demo mode".
  TaskPanel.test.tsx (if exists)   — UPDATE if needed: confirm AICoachPanel
                                    renders within TaskPanel; no behavioral
                                    regression on existing CompletenessCard.

ui/frontend/src/api/__tests__/
  client.test.ts (or new)          — EXTEND: streamAICoach() unit tests with
                                    a fetch-mock that returns chunked SSE;
                                    assert callback sequence + cancellation.
```

### V1 explicit scope-down (per V61-119 lesson L1: anti-cascade discipline)

| Excluded V1 | Why | Where it goes |
|---|---|---|
| **LLM-side tool calling** (LLM emits tool_call → UI dispatches) | This is V61-121's central feature; mixing into V120 collapses the 2-step arc and re-introduces V61-118-style multi-axis cascade risk | V61-121 |
| **Action proposals + approval UX** ([Accept]/[Reject]/[Edit] inline diff) | Same as above — V120 is read-only adviser only | V61-121 |
| **Persisted chat history** (across page reload, across cases) | localStorage + per-case keying is a separate scope; V1 lives in useState only — page reload clears | V61-122 if needed |
| **Multi-conversation tabs** | Single conversation per panel mount, period | Out of scope |
| **Custom prompt templates / model picker** | Default model = `deepseek-v4-pro`; default system prompt from V119 — no UI customization | Out of scope |
| **File upload / image attachment** | Backend doesn't support multimodal; V1 is text-only | Out of scope |
| **Markdown rendering of AI replies** | V1 displays plain text; LLM-generated markdown is rendered as plain text in `<pre>` block | V61-121 (when actions need code-block rendering for diffs) |
| **Voice input** | Not in scope ever for this arc | Permanently out |

### Public contract

#### `streamAICoach()` API client (in `api/client.ts`)

```typescript
export interface StreamAICoachRequest {
  case_id: string;
  user_message: string;
  history?: Array<{ role: "user" | "assistant"; content: string }>;
  model?: string;
  temperature?: number;
  max_tokens?: number;
}

export interface StreamAICoachCallbacks {
  onDelta: (delta: string) => void;
  onDone: (final: { usage?: Record<string, number>; model_used: string }) => void;
  onError: (err: { kind: "http" | "stream"; status?: number; detail: string }) => void;
}

export interface StreamAICoachHandle {
  cancel: () => void;
}

export function streamAICoach(
  req: StreamAICoachRequest,
  cb: StreamAICoachCallbacks,
): StreamAICoachHandle;
```

Implementation:
- POST to `/api/ai-coach/stream` with JSON body
- Pre-stream HTTP error (401/429/400/404/502/500): `cb.onError({kind: 'http', status, detail})` from response.json() before reading body
- For 200: read body via `response.body!.getReader()`; decode chunks; line-buffer on `\n\n`; parse each `data: {json}` frame:
  - `{delta, ...}` → `cb.onDelta(delta)`
  - `{done: true, usage, model_used}` → `cb.onDone(...)`
  - `{error, detail, done: true}` → `cb.onError({kind: 'stream', detail})`, then `cb.onDone(...)` semantics so UI cleans up
- AbortController plumbed; `handle.cancel()` aborts the fetch; reader propagates AbortError silently

#### `AICoachPanel.tsx` UI

Layout (~280px tall, fixed bottom of TaskPanel):

```
┌─ [AI助手 · Pro]                    [stop|×] ─┐
│ ┌────────────────────────────────────────┐  │
│ │ user:  缺什么字段？                       │  │
│ │ AI:    根据完整性快照, 你还差 1 项 critical │  │
│ │        - physics.turbulence_model         │  │
│ └────────────────────────────────────────┘  │  ← internal scroll
│ ┌────────────────────────────────────────┐  │
│ │ [textarea]                          [↑] │  │
│ └────────────────────────────────────────┘  │
└────────────────────────────────────────────┘
```

States:
- **idle**: empty, only the input + welcome line
- **sending**: spinner on send button, input disabled, stop button enabled
- **streaming**: assistant message growing as deltas arrive, stop button enabled
- **error**: red pill above input with `detail`; input re-enabled to allow retry
- **done**: assistant message complete, input re-enabled, stop hidden

Accessibility:
- `role="region"` `aria-label="AI助手对话"`
- Input: `<label>` "向 AI 助手提问"
- Streaming message: `aria-live="polite"` so screen readers narrate growth
- Error pill: `role="alert"`
- Stop button: keyboard-accessible (Enter/Space), `aria-label="终止当前回复"`

### Layout integration in `TaskPanel.tsx`

Current structure:
```jsx
<aside className="...flex flex-col">
  <header>{step.longLabel}</header>
  <div className="flex-1 overflow-y-auto">
    {caseId && <CompletenessCard caseId={caseId} />}
    <Body ... />
  </div>
  <StepNavigation ... />
</aside>
```

V120 structure:
```jsx
<aside className="...flex flex-col">
  <header>{step.longLabel}</header>
  <div className="flex-1 overflow-y-auto min-h-0">
    {caseId && <CompletenessCard caseId={caseId} />}
    <Body ... />
  </div>
  {caseId && <AICoachPanel caseId={caseId} />}  {/* NEW · ~280px fixed */}
  <StepNavigation ... />
</aside>
```

`min-h-0` is added to the scrollable area so it actually shrinks when AICoachPanel takes its 280px (otherwise flex-1 + content overflow keeps it growing). This is the only existing-file change to layout — backwards-compatible because `caseId &&` gating skips the panel on the case-less landing screen.

## Risk register

| # | Risk | Likelihood | Mitigation | Status |
|---|---|---|---|---|
| 1 | SSE chunk boundary splits a JSON `data:` event across two ReadableStream reads | Medium | Buffer incomplete tail, split on `\n\n`, only parse complete events; standard ReadableStream pattern | Mitigated by impl |
| 2 | AbortController abort during stream surfaces as a noisy error in console | Medium | Catch AbortError specifically and silently no-op `onError`; test asserts no error callback fires after `cancel()` | Mitigated |
| 3 | TaskPanel right rail height collapses on narrow viewports → AICoachPanel unusable | Medium | 280px fixed-height with internal scroll; below 600px viewport height the workbench is already non-functional (existing UI assumption) | Accepted |
| 4 | V61-119's pre-stream HTTP errors (401/429/400/502/500) leak raw upstream messages to UI | Low | Backend already maps to safe `detail` strings; UI displays `detail` verbatim — no additional parsing | V119 already mitigated |
| 5 | Mock-mode (DEEPSEEK_API_KEY unset) shows "[Mock LLM Provider]" prefix in chat — confusing | Low | Render a "demo mode" banner pill when `model_used === "mock"` so engineers know real LLM is offline | Mitigated |
| 6 | LLM emits markdown the user can't read (rendered as plain text) | Low | V1 limitation; V61-121 will add markdown rendering when tool-call diffs need code blocks | Accepted V1 |
| 7 | Race: user sends message-2 while message-1 is still streaming | Medium | UI disables send button while streaming; stop-then-send UX requires explicit cancel first | Mitigated |
| 8 | Long replies overflow internal scroll → engineer can't see the latest text | Low | Auto-scroll to bottom on new delta unless user has scrolled up (sticky-bottom heuristic) | Mitigated |

## Self-pass-rate calibration

V120 is a frontend-only DEC after V119 backend pass. Calibration anchor: "Frontend SSE consumer + new UI panel + abort/cancel" → 60% / 3-4 rounds. Risk surfaces are bounded and well-trodden:
- SSE parse loop edge cases (single round)
- AbortController cleanup (single round)
- Layout interaction with existing TaskPanel scrollable (single round)
- Accessibility / aria contracts (potentially one finding)

Anti-cascade signal: V120 shares NO mechanism axes with V61-118's cleanup-cascade pattern. Only LLM-related complexity (the system prompt, the streaming protocol) is INHERITED from V119 unchanged.

## Successor pointers

- **V61-121 (next, immediate)**: Tool-calling protocol + approval UX. Extends `streamAICoach` callback set with `onToolCall`; AI emits tool_call frames; UI surfaces them as proposals with [Accept]/[Reject]/[Edit] inline; backend dispatches approved actions through existing route handlers (e.g., `case_patch_classification.put_classification`). This is the actual differentiation step — AI gains hands.
- **V61-122 (potential)**: Persisted chat history per case_id (localStorage); multi-conversation tabs; markdown rendering. Only if engineer feedback after V121 indicates need.

## Files comprising V61-120

```
.planning/decisions/2026-05-04_v61_120_ai_coach_chat_panel_ui.md
ui/frontend/src/api/client.ts                                       (extend: streamAICoach method)
ui/frontend/src/pages/workbench/step_panel_shell/AICoachPanel.tsx   (new ~250 LOC)
ui/frontend/src/pages/workbench/step_panel_shell/TaskPanel.tsx      (extend: mount AICoachPanel)
ui/frontend/src/pages/workbench/step_panel_shell/__tests__/AICoachPanel.test.tsx  (new)
reports/codex_tool_reports/v61_120_r1_chain.md                       (new — chain log)
```

Estimated LOC: ~700-900 (smaller than V61-119 because no new backend logic and no LLM-protocol parsing — just SSE consumer + UI)
