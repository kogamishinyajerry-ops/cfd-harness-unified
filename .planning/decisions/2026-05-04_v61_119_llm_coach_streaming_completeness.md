---
decision_id: DEC-V61-119
title: LLM-wrapped completeness coaching · SSE streaming + governance-aware system prompt · POST /api/ai-coach/stream
status: Accepted (2026-05-04 · Codex pre-merge 3-round chain APPROVE on commit 394ae27 [R1 P1 → R2 P2 → R3 clean]; chain report at reports/codex_tool_reports/v61_119_r1_chain.md; user 2026-05-04 autonomous-mode mandate "全都按你的建议来" covers acceptance flip · arc item E closes the five-DEC arc A→C→B→D→E)
codex_tool_report_path: reports/codex_tool_reports/v61_119_r1_chain.md
codex_review_relay: CRS gpt-5.4 high (R1-R3 · 86gs gpt-5.4 xhigh attempted on every round but failed via Cloudflare 522 / stream-disconnect; sustained 86gs instability triggered CRS fallback per CLAUDE.md relay protocol on each round — see chain report §L2 for the proposed default-to-CRS workflow change)
authored_by: Claude Code Opus 4.7 (1M context)
authored_at: 2026-05-04
authored_under: User 2026-05-04 autonomous-mode mandate "全都按你的建议来" covering five-DEC arc A→C→B→D→E (V61-115/116/117/118/119); this is item E — the LLM-wrapped governance-aware coaching surface that consumes V61-118's `LLMProvider` foundation + V61-116's `analyze_case_completeness` output and lands the chat experience inside the right-rail TaskPanel V61-117 just hardened.
parent_decisions:
  - DEC-V61-118 (LLM provider foundation · this DEC's prerequisite plumbing — `LLMProvider` ABC, `ChatRequest`/`ChatResponse`, error hierarchy, singleton/lifespan, loopback guard)
  - DEC-V61-116 (case completeness analyzer · this DEC's data source — `analyze_case_completeness(case_id) -> CaseCompletenessReport` is pre-injected into the LLM system prompt at request time)
  - DEC-V61-117 (StepTree Fluent hierarchy · this DEC's eventual UI mounting point inside TaskPanel right-rail)
  - DEC-V61-088 (pre-implementation surface scan rule · this DEC carries Surface-scan trailer)
  - RETRO-V61-001 (risk-tier · multi-file backend + new operator endpoint + LLM-streaming integration = mandatory Codex pre-merge)
parent_artifacts:
  - ui/backend/services/llm_provider/base.py:115-123 (LLMProvider ABC · V61-119 extends with chat_stream method)
  - ui/backend/services/llm_provider/deepseek.py:42-205 (DeepSeekProvider · V61-119 adds chat_stream alongside chat)
  - ui/backend/services/llm_provider/factory.py (singleton + lifespan-shutdown · V61-119 reuses unchanged)
  - ui/backend/routes/ai_chat.py:43-115 (loopback guard, proxy header detection, audit log helper · V61-119 extracts to shared helper and reuses)
  - ui/backend/services/case_completeness/__init__.py:24-42 (analyze_case_completeness + CaseCompletenessReport schema · V61-119 invokes synchronously before opening the stream)
counter_impact: +1 (autonomous_governance: true · new backend service + new operator endpoint extending an existing one. Kogami-trigger check: not a phase-close, not a RETRO draft, not an arc-size retro at counter 78, not a governance-rule change, not a high-risk PR pre-merge — V61-119 is a feature DEC analogous to V61-118 (which Kogami-skipped). Codex pre-merge MANDATORY per RETRO-V61-001 multi-file backend + new operator endpoint + external-API integration triggers.)
notion_sync_status: pending — Notion MCP server disconnected during chain close; will sync when reconnected
self_estimated_pass_rate: 50% (predicted 4-5 rounds) → ACTUAL 3 rounds (well-calibrated underestimate · scope-down discipline paid off · per chain report §L1 the "External-API integration WITHOUT cleanup-mechanism design" anchor is now ~50% / 3-4 rounds vs V61-118's "WITH cleanup contract" anchor at 25% / 7-9 rounds — deliberate exclusion of LLM-side tool calling + mid-stream fallback + SSE reconnect kept the cascade dimension count to 1)

---

# DEC-V61-119 · LLM-wrapped completeness coaching foundation

## Why now

V61-118 landed the bare LLM chat plumbing (`POST /api/ai-chat`, non-streaming). The user's verbatim 2026-05-04 design ask was that the AI assistant must "真实介入LLM，不能完全依赖知识库已有的规则、知识、经验" — i.e. the LLM has to see the actual case state, not just a generic chat prompt.

V61-119 is the first surface where the LLM gets governance-aware context: the `analyze_case_completeness` output for the case the engineer is working on is pre-fetched and injected into the system prompt before the stream opens. The engineer can then ask the LLM "what's blocking my archive?" or "explain why turbulence model is critical here" and get answers grounded in the actual completeness report, not generic CFD advice.

This is item **E** of the five-DEC arc the user authorized 2026-05-04 ("全都按你的建议来"). With it, the arc closes.

## Surface scan (per DEC-V61-088)

**ROADMAP scan**: post-W5 + workbench-rollout roadmaps return zero hits for `coaching` / `coach` / `llm`. M-AI-COPILOT (DEC-V61-098) defined the rule-based AIActionEnvelope contract and explicitly deferred free-form chat. V61-118 added the chat foundation; V61-119 adds the streaming + governance-context layer the user asked for. No competing or pre-existing roadmap item.

**Existing-implementation grep** (`grep -rln "completeness\|llm_provider\|ai_chat\|coach\|coaching" ui/backend/`):
- `ui/backend/services/llm_provider/` — V61-118 surface (will EXTEND: add `chat_stream` method)
- `ui/backend/routes/ai_chat.py` — V61-118 surface (will EXTEND: extract loopback guard helpers; new sibling route file)
- `ui/backend/services/case_completeness/` — V61-116 surface (READ-ONLY consumer)
- No `coach`/`coaching` files found anywhere in the backend or frontend

**Disposition**: **extend existing** (`llm_provider/base.py` + `llm_provider/deepseek.py` add streaming method · `routes/ai_chat.py` extracts shared loopback guard helper) AND **parallel new** (`services/llm_coach/` new package · `routes/ai_coach.py` new route file). The new package keeps coaching-specific concerns (system prompt composition, completeness pre-fetch) separate from the provider abstraction, which stays vendor-agnostic.

**Surface-scan trailer**: commits will carry `Surface-scan-found: ui/backend/services/llm_provider/, ui/backend/routes/ai_chat.py, ui/backend/services/case_completeness/ · disposition: extend (llm_provider, ai_chat) + parallel-new (llm_coach, ai_coach)`.

## Decision

Add streaming chat support to the existing `LLMProvider` abstraction, plus a new `services/llm_coach/` package that pre-fetches the completeness report and composes a governance-aware system prompt, plus a new `POST /api/ai-coach/stream` SSE route that wires them together. Loopback guard is extracted from `ai_chat.py` into a shared helper and reused (no copy-paste).

### Architecture (V1 scope)

```
ui/backend/services/llm_provider/
  base.py                — EXTEND: add ChatStreamChunk model + LLMProvider.chat_stream() abstract method
  deepseek.py            — EXTEND: add DeepSeekProvider.chat_stream() — SSE parsing of stream=true responses
  __init__.py            — EXTEND: re-export ChatStreamChunk
  (factory.py + MockLLMProvider unchanged for production singletons; MockLLMProvider gets a chat_stream impl that yields a fixed sequence of chunks for tests)

ui/backend/services/llm_coach/        — NEW PACKAGE
  __init__.py            — public API: build_coach_system_prompt
  prompts.py             — build_coach_system_prompt(report: CaseCompletenessReport, project_rules: str) -> str
                           Composes: case_id, case_kind, ready_for_archive, blocked_by_critical, missing field
                           list (capped to top-N critical), governance preamble (read-only role,
                           no auto-actions, point engineer at field paths, do not invent missing
                           data). Pure function, no I/O.

ui/backend/routes/
  _loopback_guard.py     — NEW: extracted from ai_chat.py — _LOOPBACK_HOSTS, _PROXY_FORWARDED_HEADERS,
                           _is_loopback_request, _non_loopback_override_enabled, _client_label_for_log,
                           require_loopback(request) helper that raises HTTPException(403) consistently.
                           ai_chat.py is refactored to import from here (NO behavior change; tests
                           preserved exactly as-is).
  ai_coach.py            — NEW: POST /api/ai-coach/stream
                           Request: {case_id: str, user_message: str, history?: list[ChatMessage]}
                           Response: text/event-stream — chunked content + final usage event + done event
                           Pre-fetches completeness report SYNCHRONOUSLY before opening the stream
                           (so a 404 on case_id surfaces as HTTP 404, not as a stream that errors mid-flight).
                           Inherits loopback guard via require_loopback().

ui/backend/tests/
  test_llm_provider_streaming.py  — NEW: chat_stream() unit tests with httpx.MockTransport simulating
                                    SSE responses (multiple chunk patterns: normal, single-shot, [DONE]
                                    marker placement, malformed event line, premature disconnect).
  test_llm_coach.py               — NEW: build_coach_system_prompt tests (composition rules, top-N
                                    cap, no leakage of suggested_default values that look like secrets).
  test_ai_coach_route.py          — NEW: route-level tests with provider+analyzer monkeypatched.
                                    Coverage: 200 stream success, 404 case_id, 400 bad request,
                                    403 non-loopback, 502 upstream error, override allowance,
                                    request validation. SSE stream is consumed via TestClient
                                    streaming response and asserted against chunk sequence.
  test_ai_chat_route.py           — UPDATED: re-import from new _loopback_guard helper module;
                                    behavior unchanged.
```

### V1 explicit scope-down (anti-cascade discipline)

Per V61-118's 9-round cascade methodology lesson L1 (cleanup-mechanism cascade), the V1 surface deliberately excludes the highest-risk axes:

| Excluded V1 | Why | Where it goes |
|---|---|---|
| **LLM-side tool calling** (LLM emits `tool_call` and we dispatch back) | OpenAI tool-calling spec has multiple compatibility traps with DeepSeek; round-trip orchestration adds a state machine | V61-120 if needed; V1 server pre-fetches completeness and injects it as system context, no tool round-trip |
| **Mid-stream fallback** (V4-Pro fails at chunk N → switch to V4-Flash and re-stream) | Non-trivial to expose to client cleanly; partial content delivered before failure complicates retry semantics | Out of V1 — stream commits to one model; mid-stream upstream failure surfaces a final `error` SSE event and closes |
| **SSE reconnect / cursor** | Adds session/state management we don't need for the V1 ask | Out of V1 — single request scope; client retries by re-issuing the request |
| **Frontend wiring (TaskPanel chat UI)** | Frontend integration needs design discussion + UI-spec separately | Out of V1 — V61-119 ships backend only; frontend follow-up is a separate DEC |
| **Multi-tool registry** | Single-tool case (completeness) doesn't justify a registry abstraction | Pre-injection of fetched report keeps it data-driven |
| **Streaming usage telemetry granularity** | DeepSeek emits `usage` only on the final chunk for some endpoints | V1 forwards what the upstream provides; no synthetic per-chunk usage |

### Public API contract

#### `ChatStreamChunk` (new in `base.py`)

```python
class ChatStreamChunk(BaseModel):
    """One frame in a streamed chat response.

    `delta` is the incremental content for this frame. `done` is True
    only on the terminal frame; that final frame may also carry the
    full `usage` totals if the provider reported them.
    """
    delta: str = ""
    done: bool = False
    usage: dict[str, int] | None = None
    model_used: str
    fallback_used: bool = False  # V1: always False — mid-stream fallback deferred
```

#### `LLMProvider.chat_stream` (extended in `base.py`)

```python
class LLMProvider(ABC):
    @abstractmethod
    async def chat(self, request: ChatRequest) -> ChatResponse: ...

    @abstractmethod
    def chat_stream(self, request: ChatRequest) -> AsyncIterator[ChatStreamChunk]:
        """Stream a chat completion. Yields chunks until done=True.
        Mid-stream upstream failure raises an LLMProviderError subclass;
        callers should wrap `async for` in a try/except and surface the
        terminal error to the client.
        """
```

#### `build_coach_system_prompt` (new in `services/llm_coach/prompts.py`)

```python
def build_coach_system_prompt(
    report: CaseCompletenessReport,
    project_rules: str = _DEFAULT_PROJECT_RULES,
    *,
    max_missing_to_inline: int = 8,
) -> str:
    """Compose the LLM system prompt for the coaching session.

    Layers (in order):
      1. Role preamble (read-only adviser, must not fabricate fields,
         must point engineer at field_path coordinates from the report).
      2. Project rules (governance preamble — explain ready_for_archive
         semantics, severity tiers, when warnings are acceptable).
      3. Case state snapshot (case_id, case_kind, percentage,
         ready_for_archive, blocked_by_critical).
      4. Top-N critical missing fields (capped at max_missing_to_inline
         to keep token budget bounded; remainder is summarized as
         "+ N more critical entries — ask for the full list to expand").

    Pure function. No external I/O. Never embeds api_key or any
    process secret. Never embeds suggested_default values verbatim if
    they look like secrets (heuristic: skip if value is a string >40
    chars matching common token shapes — sha256/jwt/etc).
    """
```

#### `POST /api/ai-coach/stream` (new route)

```
Request body:
  {
    "case_id": "lid_driven_cavity",
    "user_message": "什么字段还缺？",
    "history": [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
  }

Response:
  HTTP 200 · Content-Type: text/event-stream
  data: {"delta": "你的", "done": false, "model_used": "deepseek-v4-pro"}
  data: {"delta": "案例还差", "done": false, "model_used": "deepseek-v4-pro"}
  ...
  data: {"delta": "", "done": true, "model_used": "deepseek-v4-pro", "usage": {"prompt_tokens": 312, "completion_tokens": 64, "total_tokens": 376}}

  Each SSE event is a single `data: <json>\n\n` line. No event names, no
  retry directives — V1 keeps the protocol minimal.

Status code mapping (BEFORE stream opens):
  200 → stream opened (errors during stream emit a final SSE error event then close)
  400 → invalid request body / empty user_message
  403 → non-loopback caller without AI_CHAT_ALLOW_NON_LOOPBACK=1
  404 → case_id resolves to nothing (analyze_case_completeness returns None)
  502 → completeness analyzer crash (case data corrupt) — not the LLM yet
  500 → unexpected
```

## V1 wire format (DeepSeek SSE)

DeepSeek's `stream=true` response is OpenAI-compatible SSE:

```
data: {"id":"chatcmpl-...","choices":[{"delta":{"content":"你"},"finish_reason":null}]}\n\n
data: {"id":"chatcmpl-...","choices":[{"delta":{"content":"好"},"finish_reason":null}]}\n\n
data: {"id":"chatcmpl-...","choices":[{"delta":{},"finish_reason":"stop"}],"usage":{...}}\n\n
data: [DONE]\n\n
```

`DeepSeekProvider.chat_stream` parses each `data:` line:
- `[DONE]` marker → emit terminal chunk with `done=True` and final usage (carried over from prior frame)
- JSON line → parse `choices[0].delta.content` as the delta string; if `finish_reason` is set, the next iteration is the usage frame
- Malformed JSON → raise `LLMUpstreamError`
- HTTP non-200 BEFORE stream opens → same error mapping as `chat()` (401/429/4xx/5xx → typed exception); after stream opens, an upstream-side error mid-stream raises `LLMUpstreamError`
- `httpx.TimeoutException` mid-stream → `LLMTimeoutError`

## Risk register

| # | Risk | Likelihood | Mitigation | Status |
|---|---|---|---|---|
| 1 | SSE chunk-boundary parsing splits a JSON event across two TCP reads | Medium | Use `httpx.AsyncClient.stream("POST", ...)` + `aiter_lines()` (httpx handles line-buffered framing). Never byte-buffer manually | Mitigated by stdlib choice |
| 2 | Client disconnects mid-stream (browser tab close) leaving upstream connection dangling | Medium | FastAPI's `StreamingResponse` propagates disconnect via `await request.is_disconnected()`; stream loop polls and breaks. `httpx.AsyncClient.stream` cleans up via `__aexit__` | Plan-level |
| 3 | `[DONE]` marker arrives without prior usage frame | Low | Emit terminal chunk with `usage=None`; client tolerates missing usage | Spec-allowed |
| 4 | LLM ignores governance preamble and fabricates field paths | Low | Cannot prevent at provider level; UI surfaces the LLM response as advisory text only (no auto-actions) — same as V61-118's pattern | Accepted V1 limit |
| 5 | Governance system prompt grows unbounded as completeness reports grow large | Medium | `max_missing_to_inline=8` cap + remainder count summary. Tested at 50-missing case to confirm prompt stays under ~3KB | Bounded |
| 6 | Suggested-default values containing secrets leak into system prompt | Low | Heuristic skip in `build_coach_system_prompt` for >40-char strings matching token shapes; `MissingField.suggested_default` is operator-authored data, not pulled from env | Mitigated |
| 7 | Pre-fetching completeness report adds latency before stream opens | Medium | Acceptable — pre-fetch is bounded (analyzer is in-memory file reads), gives caller a clean 404 instead of mid-stream error. Documented as ~50-200ms expected | Accepted |

## Self-pass-rate calibration (RETRO-V61-001 anchor refinement)

V61-118 anchor for "External-API integration with persistent-client cleanup contract" hit ~25% / 9 rounds. V61-119 has DIFFERENT risk surface: NO new cleanup contract (reuses V61-118's), NO LLM tool calling, NO frontend integration. The new surfaces are SSE-parsing + system-prompt composition + extracted helper module. These have smaller cascade potential individually — likely candidates for findings:

- SSE event boundary edge case (single round)
- Disconnect/cancellation cleanup (single round)
- Helper-extraction breaking ai_chat.py tests (single round)
- System-prompt composition not respecting cap (single round)

50% / 4-5 rounds is a calibrated estimate. If actual exceeds 6 rounds, the next retro adds an SSE-streaming sub-anchor.

## Successor pointers

- **V61-120** (potential): tool-calling protocol — only if the V1 system-prompt-injection approach proves insufficient in practice (engineer feedback on V61-119 will tell)
- **V61-121** (potential): frontend TaskPanel chat UI wiring — separate DEC, separate UI-spec, separate Codex chain. Will consume V61-119's `/api/ai-coach/stream` route as-is

## Files comprising V61-119

```
.planning/decisions/2026-05-04_v61_119_llm_coach_streaming_completeness.md
ui/backend/services/llm_provider/base.py            (extend: ChatStreamChunk + chat_stream abstract)
ui/backend/services/llm_provider/deepseek.py        (extend: chat_stream impl)
ui/backend/services/llm_provider/__init__.py        (extend: re-export)
ui/backend/services/llm_coach/__init__.py           (new package)
ui/backend/services/llm_coach/prompts.py            (new: build_coach_system_prompt)
ui/backend/routes/_loopback_guard.py                (new: extracted from ai_chat.py)
ui/backend/routes/ai_chat.py                         (refactor: import from _loopback_guard)
ui/backend/routes/ai_coach.py                       (new: SSE streaming route)
ui/backend/main.py                                  (extend: register ai_coach router)
ui/backend/tests/test_llm_provider_streaming.py     (new)
ui/backend/tests/test_llm_coach.py                  (new)
ui/backend/tests/test_ai_coach_route.py             (new)
ui/backend/tests/test_ai_chat_route.py              (extend: re-import path only)
reports/codex_tool_reports/v61_119_r1_chain.md      (new — chain log)
```

Estimated LOC: ~900-1200 (smaller than V61-118 because no cleanup-contract design)
