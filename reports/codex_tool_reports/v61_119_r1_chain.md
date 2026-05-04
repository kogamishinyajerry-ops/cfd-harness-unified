# DEC-V61-119 · LLM-wrapped completeness coaching · Codex pre-merge chain

**Backend (intended)**: 86gs `gpt-5.4` xhigh — actually executed entirely on **CRS `gpt-5.4` high** after consecutive 86gs Cloudflare 522 / stream-disconnect on every attempt
**Trigger**: RETRO-V61-001 multi-file backend + new operator endpoint + LLM-streaming integration + secrets-handling reuse
**Scope**: 14 files initial · ~1929 LOC across `services/llm_provider/` (extend), `services/llm_coach/` (new), `routes/ai_coach.py` (new), `routes/_loopback_guard.py` (extracted), `routes/ai_chat.py` (refactored), `main.py`, tests, DEC
**Self-estimated pass rate**: 50% (predicted 4-5 rounds)
**Actual**: 3 rounds — significantly better than predicted; scope-down discipline (no LLM tool-calling · no mid-stream fallback · no SSE reconnect) kept the surface narrow

---

## Round-by-round summary

| Round | Commit | Findings | Severity | Verdict | Backend |
|---|---|---|---|---|---|
| R1 | 7b00bdf | 1 | P1 | CHANGES_REQUIRED | CRS gpt-5.4 high (after 86gs 522) |
| R2 | 9631569 | 1 | P2 | CHANGES_REQUIRED | CRS gpt-5.4 high (after 86gs stream-disconnect) |
| R3 | 394ae27 | 0 | — | **APPROVE clean** | CRS gpt-5.4 high (retry after CRS disconnect; 86gs 522) |

---

## Round 1 · CHANGES_REQUIRED · 1 P1

- **P1 · Pre-stream upstream failures swallowed as 200 SSE error events.** When `provider.chat_stream()` rejected the request before yielding its first chunk (bad key / 429 / 4xx / 5xx / timeout), the route had already committed `200 text/event-stream` and could only deliver a final SSE error frame. Callers lost typed-status retry/auth handling. Fix in R2: peek the first chunk via `stream_iter.__anext__()` BEFORE returning `StreamingResponse`; map typed exceptions to HTTP 401/429/400/502/500 mirroring `/api/ai-chat`; only post-first-chunk failures surface as SSE error events (status already committed). Added pre-stream test cases for each typed exception + a separate mid-stream test using a generator that yields-then-raises.

## Round 2 · CHANGES_REQUIRED · 1 P2

- **P2 · Terminal-as-first-chunk path leaks the upstream iterator.** R1's pre-peek added an early-return branch (`if first_chunk.done: return`) that exited `event_source` without entering the `async for` loop; the underlying `httpx.AsyncClient.stream()` context was suspended until garbage collection, which would pile up under repeated short/empty completions. Same hazard on the empty-stream synthesized-done branch and the client-disconnect branch. Fix in R3: wrap the entire `event_source` body in try/finally; the finally clause calls `stream_iter.aclose()` (idempotent — Python async generators tolerate double-call, httpx's `__aexit__` is idempotent too). Added two tests using a custom `_AcloseTrackingProvider` that records whether its async-generator's `finally` clause ran.

## Round 3 · APPROVE clean · 0 findings

**Backend**: CRS `gpt-5.4` high. Verbatim verdict (Codex):

> "The change correctly adds deterministic cleanup for the streamed iterator on the newly covered exit paths without introducing a clear regression in the route behavior or tests. I did not find a discrete, actionable bug in the diff that would warrant blocking the patch."

86gs hit Cloudflare 522 on the initial R3 attempt (third consecutive 86gs failure across this chain). CRS picked it up cleanly on retry after one transient CRS stream-disconnect.

---

## Methodology lessons

### L1 · V1 explicit scope-down works as anti-cascade discipline

V61-118 lesson L1 ("at the third or fourth iteration on a single mechanism, ask 'is this mechanism necessary?'") was applied PROACTIVELY at DEC-authoring time for V61-119. The DEC explicitly excluded:

- **LLM-side tool calling** → replaced with server-side completeness pre-fetch + system-prompt injection (single tool, no orchestration round-trip)
- **Mid-stream fallback** → one model commits per stream
- **SSE reconnect / cursor** → request-scoped only
- **Frontend wiring** → backend-only DEC

Result: 3 rounds vs V61-118's 9 rounds despite a similar surface size (~1929 LOC vs ~1700 LOC). The pattern Codex found in R1 (pre-stream error mapping) and R2 (cleanup on early-return paths) were both single-axis findings — fix in one place, no chain. V61-118's R3-R7 cascade was on a multi-axis cleanup mechanism (timing × concurrency × atomicity × cross-loop), which V61-119 deliberately did not introduce.

**Calibration anchor refinement**: "External-API integration WITHOUT cleanup-mechanism design" deserves ~50% / 3-4 rounds. V61-118 anchor (with cleanup contract: 25% / 7-9 rounds) and V61-119 anchor (without: 50% / 3 rounds) bracket the difference attributable to that single design axis.

### L2 · Multi-relay resilience: 86gs at sustained instability requires CRS-default workflow

V61-118 R9 hit 86gs 522 once. V61-119 hit 86gs failures on EVERY round (R1 522, R2 stream-disconnect, R3 522), forcing CRS fallback every time. This is no longer "occasional 522" — it is sustained 86gs instability. RETRO follow-up: when 86gs has 3 consecutive failures within an active arc, default to CRS for the rest of the arc rather than retry-then-fallback per round. The CRS effort downgrade (xhigh → high) cost is documented per round but has not yet been associated with any false APPROVE in either chain.

### L3 · Pre-stream peek pattern is the right SSE error-mapping idiom

The R1 fix is generalizable: SSE routes that wrap an async iterator backed by an HTTP request MUST validate the upstream response status BEFORE committing the streaming response. The simplest pattern is to peek the first item; alternatives (separate health-check round-trip, two-phase open) are heavier. Recommend codifying this in any future SSE route DEC as a baseline acceptance criterion: "the route MUST surface upstream `4xx`/`5xx`/`auth`/`config` errors as the appropriate HTTP status on attempts that fail BEFORE the first chunk is delivered, and as a terminal SSE `error` event AFTER the first chunk is delivered."

### L4 · async-generator cleanup discipline on every early return

R2 finding generalizes: any route whose `event_source` generator pulls from an async iterator backed by an open resource (httpx stream, websocket, file) MUST wrap its body in try/finally with `aclose()` on the upstream. The list of early-return paths grows quickly (terminal-as-first-chunk, empty-stream synthesized done, client disconnect, mid-stream error, branch on disconnect-detect polling) and a single one missed is a socket leak. The idempotent-aclose-in-finally pattern dominates the alternative of try/except per branch.

---

## Files comprising V61-119

```
.planning/decisions/2026-05-04_v61_119_llm_coach_streaming_completeness.md
ui/backend/services/llm_provider/base.py            (+ChatStreamChunk + chat_stream abstract)
ui/backend/services/llm_provider/deepseek.py        (+chat_stream SSE parsing)
ui/backend/services/llm_provider/__init__.py        (re-export ChatStreamChunk)
ui/backend/services/llm_coach/__init__.py           (new package)
ui/backend/services/llm_coach/prompts.py            (build_coach_system_prompt)
ui/backend/routes/_loopback_guard.py                (extracted from ai_chat.py)
ui/backend/routes/ai_chat.py                        (refactored to import shared guard)
ui/backend/routes/ai_coach.py                       (new SSE route + R1+R2 fixes)
ui/backend/main.py                                  (lifespan + ai_coach router register)
ui/backend/tests/test_llm_provider_streaming.py     (12 tests)
ui/backend/tests/test_llm_coach.py                  (14 tests)
ui/backend/tests/test_ai_coach_route.py             (19 tests after R2 additions)
ui/backend/tests/test_ai_chat_route.py              (helper module re-import + stub-shim)
reports/codex_tool_reports/v61_119_r1_chain.md      (this file)
```

71 LLM-area tests pass (12 streaming · 14 prompt · 19 route · 26 baseline V61-118 tests carried forward). Backend baseline 1106 pass, 5 pre-existing unrelated failures unchanged.

## Successor pointers

- **V61-120** (potential): tool-calling protocol — only if engineer feedback on V61-119 indicates the system-prompt-injection approach is insufficient
- **V61-121** (potential): frontend TaskPanel chat UI — separate DEC, separate UI-spec, consumes `/api/ai-coach/stream` as-is
- **V61-122** (proposed in §L2): RETRO addendum on default-to-CRS-on-sustained-86gs-instability workflow change
