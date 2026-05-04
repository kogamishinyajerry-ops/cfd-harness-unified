---
decision_id: DEC-V61-118
title: LLM provider integration · DeepSeek V4 Pro primary + V4 Flash fallback · POST /api/ai-chat foundation
status: Accepted (2026-05-04 · Codex pre-merge 9-round chain APPROVE on commit 583bc81 [R1 P1+P2+P3 → R2 P1+P2 → R3 P2×2 → R4 P1+P2 → R5 P1 → R6 P2 → R7 P1×2 → R8 P2 → R9 clean]; chain report at reports/codex_tool_reports/v61_118_r1_chain.md; user 2026-05-04 autonomous-mode mandate "全都按你的建议来" covers acceptance flip)
codex_tool_report_path: reports/codex_tool_reports/v61_118_r1_chain.md
codex_review_relay: 86gs gpt-5.4 xhigh (R1-R8) · CRS gpt-5.4 high (R9 fallback after 86gs 522 Cloudflare timeout, per CLAUDE.md relay protocol)
authored_by: Claude Code Opus 4.7 (1M context)
authored_at: 2026-05-04
authored_under: User 2026-05-04 design discussion — "AI助手的介入方式也需要真实介入LLM（例如DeepSeek v4 Pro、Minimax-M2.7-highspeed），不能完全依赖知识库已有的规则、知识、经验，否则交互体验很差". User 2026-05-04 mid-arc clarification updated the model choice from MiniMax to DeepSeek V4 Flash for the secondary slot (DeepSeek-only family, simpler integration, single API key). Five-DEC arc plan A→C→B→D→E confirmed by user "全都按你的建议来"; this is item D — the LLM provider foundation V61-119 will layer governance-aware coaching on top of.
parent_decisions:
  - DEC-V61-116 (case completeness analyzer · this DEC's eventual consumer; V61-119 will wrap completeness output as an LLM tool call — V61-118 is the prerequisite plumbing)
  - DEC-V61-117 (StepTree Fluent hierarchy · this DEC's UI surfacing point; AI assistant chat UI lands inside the right-rail TaskPanel V61-117 just hardened)
  - DEC-V61-088 (pre-implementation surface scan rule · this DEC carries Surface-scan trailer)
  - RETRO-V61-001 (risk-tier · multi-file backend + new operator endpoint + new external-API integration + secrets handling = mandatory Codex pre-merge)
parent_artifacts:
  - ui/backend/services/ai_actions/__init__.py:1-30 (existing rule-based AIActionEnvelope wrapper · V61-118 lives BESIDE this; rule-based path stays for deterministic actions; new LLM path is for free-form chat coaching)
  - ui/backend/main.py:161-167 (FastAPI router registration pattern)
  - ui/pyproject.toml:54-59 (`ui` optional dep group · `httpx>=0.27` already declared — V61-118 uses it without dep additions)
  - ui/backend/services/case_completeness/ (V61-116 output · V61-119 will plumb the analyzer's CaseCompletenessReport into the LLM system prompt; V61-118's response shape is provider-agnostic so V61-119 can swap prompts without re-touching the adapter)
counter_impact: +1 (autonomous_governance: true · new backend service + new operator endpoint, NOT a governance-rule change. Kogami-trigger check: not a phase-close, not a RETRO draft, not a high-risk PR — secrets-handling is via env-var convention already established for NOTION_TOKEN with no new auth/authz semantics; not arc-size retro; not a governance rule-change DEC · Kogami SKIP per DEC-V61-087 §4.2. Codex pre-merge MANDATORY per RETRO-V61-001 multi-file backend + new operator endpoint + external-API integration triggers.)
notion_sync_status: synced 2026-05-04 (https://www.notion.so/DEC-V61-118-LLM-provider-integration-DeepSeek-V4-Pro-primary-V4-Flash-fallback-POST-api-ai--356c68942bed81c8a537f343334b3e82)

---

# DEC-V61-118 · LLM provider integration foundation

## Why now

User feedback 2026-05-04 design-discussion turn (verbatim above). The current AI integration is purely rule-based (`ui/backend/services/ai_actions/classifier/` returns hard-coded BC suggestions for the LDC fixture path). User said this is fine for deterministic actions but feels "交互体验很差" (interaction experience is bad) for the free-form coaching dimension — engineers need an LLM that can read their case state and reason about it, not just match patterns.

The LLM integration is the SECOND of the user's three workbench redesign asks (after StepTree hierarchy V61-117 and rule-based completeness V61-116). Without it, V61-119's governance-aware coaching has nowhere to call into.

Mid-arc model-choice update (user 2026-05-04 follow-up): switch the secondary provider from MiniMax-M2.7-highspeed to DeepSeek V4 Flash. Rationale: same provider family as the primary, single API key (`DEEPSEEK_API_KEY` already in `~/.zshrc`), simpler V1 integration, V4 Flash is the explicitly cheap-fast variant of the same vendor.

## Surface scan (per DEC-V61-088)

**ROADMAP scan**: M-AI-COPILOT milestone (DEC-V61-098) defined the rule-based `AIActionEnvelope` contract for deterministic actions; M-AI-COPILOT did NOT spec free-form chat. V61-118 adds the chat surface that M-AI-COPILOT explicitly deferred. The five-DEC arc A→C→B→D→E (V61-115 → V61-116 → V61-117 → V61-118 → V61-119) is the post-M-PANELS workbench-UX track per user 2026-05-04 mandate.

**Existing-implementation grep** (`grep -rin "deepseek\|llm_provider\|ai_chat" ui/backend/`):
- No existing LLM provider abstraction or chat endpoint found
- `ui/backend/services/ai_actions/` exists for the rule-based classifier path — V61-118 lives in a DIFFERENT package (`llm_provider/`) so the rule-based path stays untouched

**No competing pre-existing implementation found.** Disposition: **parallel new** (new `services/llm_provider/` package + new `routes/ai_chat.py` route) — explicitly distinct from `ai_actions/` because the contracts are different (LLM chat is free-form streamable text; `ai_actions` is structured envelope with confidence + unresolved_questions).

## Decision

Add a minimal LLM provider abstraction with a DeepSeek adapter and a single non-streaming chat endpoint. Streaming, tool calling, and governance-aware system prompts are explicitly DEFERRED to V61-119.

### Architecture (V1 scope)

```
ui/backend/services/llm_provider/
  __init__.py            — public API exports
  base.py                — LLMProvider ABC + ChatMessage + ChatRequest + ChatResponse + error hierarchy
  deepseek.py            — DeepSeekProvider (OpenAI-compatible POST to api.deepseek.com)
  factory.py             — get_default_provider() reads DEEPSEEK_API_KEY env, picks adapter

ui/backend/routes/
  ai_chat.py             — POST /api/ai-chat (non-streaming · returns full response)
                           Request: {messages: [{role, content}], model?, temperature?}
                           Response: {content: string, model_used: string, fallback_used: bool}

ui/backend/tests/
  test_llm_provider.py   — provider abstraction unit tests (httpx mocked)
  test_ai_chat_route.py  — route-level tests (provider mocked)
```

### Public API contract (`base.py`)

```python
class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str

class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    model: Literal["deepseek-v4-pro", "deepseek-v4-flash"] = "deepseek-v4-pro"
    temperature: float = 0.7
    max_tokens: int = 2048

class ChatResponse(BaseModel):
    content: str
    model_used: str          # actual model that produced the response
    fallback_used: bool      # true if primary failed and we fell back
    usage: dict[str, int]    # {prompt_tokens, completion_tokens, total_tokens}

class LLMProvider(ABC):
    @abstractmethod
    async def chat(self, request: ChatRequest) -> ChatResponse: ...

# Error hierarchy (typed for upstream handling)
class LLMProviderError(Exception): ...
class LLMAuthError(LLMProviderError): ...        # 401/403 from upstream
class LLMRateLimitError(LLMProviderError): ...   # 429 from upstream
class LLMUpstreamError(LLMProviderError): ...    # 5xx from upstream
class LLMTimeoutError(LLMProviderError): ...     # client timeout
class LLMConfigError(LLMProviderError): ...      # missing API key, etc.
```

### DeepSeek adapter behavior (`deepseek.py`)

- Posts to `https://api.deepseek.com/v1/chat/completions` (OpenAI-compatible endpoint).
- Auth: `Authorization: Bearer {DEEPSEEK_API_KEY}`.
- Request payload: `{model, messages, temperature, max_tokens, stream: false}`.
- **Fallback chain**: if primary `deepseek-v4-pro` returns 5xx OR rate-limit (429), automatically retry once with `deepseek-v4-flash`. Set `fallback_used=true`. Auth errors (401/403) and config errors do NOT trigger fallback (different model won't fix auth). Timeout: 60s per request.
- **No streaming in V1**: V1 returns the full response synchronously (POST with await). SSE streaming lives at V61-119 because the streaming surface couples tightly to tool-calling.
- **Mock mode**: when `DEEPSEEK_API_KEY` env var is unset, `factory.get_default_provider()` returns a `MockLLMProvider` that returns synthetic responses (preserves CI/dev workflows; production path remains the real adapter when key is set).

### Endpoint contract (`/api/ai-chat`)

- **Method**: POST
- **Path**: `/api/ai-chat`
- **Auth**: none in V1 (matches existing endpoint convention; the surface is local-dev-only for now)
- **Body**: `ChatRequest` (Pydantic-validated)
- **Response**: 200 `ChatResponse` · 401 `LLMAuthError` · 429 `LLMRateLimitError` · 502 upstream/timeout · 500 config/unknown
- **Mock mode tagging**: when MockLLMProvider is in use, response sets `model_used="mock"` so frontend can surface "AI 助手处于演示模式（未配置真实 API key）" rather than silently behave as if real.

### What's explicitly out of scope (deferred to V61-119)

- **SSE streaming endpoint** — V61-119 needs streaming for live coaching UX
- **Tool calling** — V61-119 will register `analyze_case_completeness(case_id)` + manifest readers as LLM-callable tools
- **Governance-aware system prompt** — V61-119 will compose the system prompt from project rules + completeness output + manifest snapshot
- **Conversation memory / persistence** — V1 is stateless per-request; persistent threads land if/when dogfood demands it
- **Token budgeting / cost tracking** — V1 lets the backend pass through; V61-119 may add quotas

### Why this minimal-scope shape

Three guardrails:
1. **Codex window** — predicted 35-45% / 4-6 round chain. Scope creep to streaming + tool-calling pushes 8+ rounds and risks cascading findings on async SSE semantics.
2. **Test contract preservation** — the rule-based `ai_actions/` path stays unchanged. New code lives in a parallel package; no existing tests need modification.
3. **Secrets handling minimum** — env-var convention only (no new vault, no rotation, no audit log). Matches the existing `NOTION_TOKEN` pattern; expanding the secrets surface lands when real-deploy demands it.

## Acceptance criteria

1. `ui/backend/services/llm_provider/` package exists with `__init__.py`, `base.py`, `deepseek.py`, `factory.py`.
2. `LLMProvider` ABC + `ChatMessage`/`ChatRequest`/`ChatResponse` Pydantic models.
3. `DeepSeekProvider` calls api.deepseek.com via httpx with auth header, parses OpenAI-format response.
4. Fallback from `deepseek-v4-pro` to `deepseek-v4-flash` on 5xx + 429; `fallback_used` flag set.
5. `MockLLMProvider` returns synthetic response when `DEEPSEEK_API_KEY` is unset.
6. `factory.get_default_provider()` returns Real when key set, Mock otherwise.
7. POST `/api/ai-chat` endpoint registered in `main.py`, returns `ChatResponse` on 200.
8. Unit tests for provider with httpx mocked; route tests with provider mocked. ≥6 tests covering: success path · auth error · rate-limit fallback · 5xx fallback · mock mode · request validation.
9. `ruff check` + `mypy` clean (or no new violations vs baseline).
10. Backend pytest suite stays green (no regression).
11. Codex pre-merge APPROVE on 86gs `gpt-5.4` xhigh.
12. Surface-scan trailer applied per DEC-V61-088.

## Self-estimated pass rate

**40%** (per RETRO-V61-V088-V116 anchor for "new external-API integration" — predicted 35-45% / 4-6 rounds). Most-likely Codex finding categories:

- (a) **Secrets exposure** — Codex may flag if API key is logged anywhere (request bodies, error messages, repr). Mitigation: explicit redaction in error messages; no logging of full request payload.
- (b) **Fallback semantics** — Codex may probe edge cases: what if both models 429? what if primary returns 200 but body is malformed? Mitigation: explicit per-status-code matrix in adapter; `fallback_used=false` if primary's response was a non-recoverable structural error.
- (c) **Timeout handling** — Codex will probably ask: what if DeepSeek hangs for 90s? Mitigation: explicit `httpx.Timeout(60.0)` + `LLMTimeoutError` raised, route translates to 502.
- (d) **Mock mode safety** — Codex may catch that mock responses leak into prod if `DEEPSEEK_API_KEY` is misconfigured silently. Mitigation: log-warning on mock-mode startup; `model_used="mock"` in response so frontend can flag.
- (e) **Pydantic strictness** — Codex may want stricter validation on `messages` (non-empty, alternating roles, system-first if present). Mitigation: validators on `ChatRequest`.
- (f) **Async correctness** — Codex may flag thread-pool issues if adapter mixes sync/async httpx clients. Mitigation: pure async via `httpx.AsyncClient`.

Anchor confidence: I expect 4-5 round chain. P1 likely on (a) or (b); P2 likely on (c)/(e). 

## Plan

1. Write DEC (this file). ✓
2. Implement `services/llm_provider/` package (base + deepseek + factory + __init__).
3. Implement `routes/ai_chat.py`.
4. Register router in `main.py`.
5. Write unit tests for provider + route.
6. Run pytest (full backend suite); fix any failures.
7. Run `ruff check` + `mypy` (best-effort).
8. Commit with surface-scan trailer (`Surface-scan: parallel-new under services/llm_provider/`).
9. Codex round-1 via `codex-review-relay --commit <SHA>`.
10. Apply findings (round-2/3/4 as needed).
11. Final commit with `Codex-verified` trailer.
12. Sync to Notion.

## Risk register

- **R1 · Secrets in logs** — Adapter must NEVER log the API key or full Authorization header. Errors should redact.
- **R2 · Real API call in tests** — Tests must mock httpx; a misconfigured fixture could hit real api.deepseek.com and consume quota. Mitigation: use `respx` or manual `httpx.MockTransport` so tests cannot escape.
- **R3 · Fallback masking auth bugs** — If primary auth is broken, falling back to flash with the same broken auth wastes a request and confuses the error. Auth errors must NOT trigger fallback.
- **R4 · Mock mode in production** — A production deploy without `DEEPSEEK_API_KEY` would silently use mocks. Mitigation: `model_used="mock"` in response + startup log warning; production deploy checklist will add an explicit env-var presence check.
- **R5 · DeepSeek API contract drift** — DeepSeek may change OpenAI-compat surface. Mitigation: V1 uses a thin wrapper, easy to swap; integration test against real API is a manual smoke (not in CI).
- **R6 · In-process key rotation NOT supported** — `DEEPSEEK_API_KEY` is read at process startup. Rotating it without restart leaves the previously-cached provider's `httpx.AsyncClient` for GC (no eager `aclose`). Codex R3-R7 chain explored drain-based and time-delayed eviction designs; both opened cross-loop / cross-thread race surfaces (multi-event-loop atomicity, sync-vs-async drain wakeup) that exceed V1 scope. Decision: scope the cleanup contract to FastAPI lifespan-shutdown only; document in-process rotation as unsupported. Operators rotate keys via deploy-restart; CI/tests use `reset_default_provider()` and own the close themselves. Future Tier-2 may add multi-tenant + rotation if dogfood demands.

## Successor pointers

- DEC-V61-119 (item E · LLM-wrapped completeness coaching) consumes V61-118's `LLMProvider` interface and adds: SSE streaming, tool calling (completeness analyzer + case readers), governance-aware system prompt composition.
- Future Tier-2 work: persistent conversation threads, multi-tenant API key management, cost telemetry, prompt-caching layer. None in current arc.
