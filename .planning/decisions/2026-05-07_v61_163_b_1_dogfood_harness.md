---
decision_id: DEC-V61-163
title: B.1 · Multi-model subagent dogfood harness — orchestration scaffold (LLM clients + friction log + persona runner + tool executor)
status: Accepted
parent_dec: V61-162
phase: B
notion_sync_status: pending
---

# DEC-V61-163 · B.1 · Dogfood Harness Scaffold

## Scope

Land the orchestration backbone for the B-arc multi-model subagent
dogfood. Persona prompts (B.2), case briefs (B.3), and the actual
9-run execution (B.4) are downstream. This sub-DEC ships:

- `scripts/dogfood/` (NEW package) — package marker + README
- `scripts/dogfood/llm_clients.py` — `LLMClient` Protocol + 3 client
  classes (`AnthropicClient` for Sonnet 4.6, `DeepSeekClient` reusing
  workbench's HTTP shape, `OpenAICompatClient` pointed at 86gs relay
  for gpt-5.4) + factory + **non-Opus guard** (aborts harness if
  resolved model name matches `opus`/`claude-opus`)
- `scripts/dogfood/friction_log.py` — JSONL writer with typed events:
  `api_call` / `advisor_query` / `decision` / `drop` / `verdict` /
  `error` / `tool_use` / `budget_check`
- `scripts/dogfood/case_brief.py` — `CaseBrief` dataclass +
  `load_brief(path)` + `check_verdict(brief, observed) -> VerdictResult`
  (machine-checked tolerance comparison; persona's text verdict is
  ignored — only the structured observed value matters)
- `scripts/dogfood/workbench_tools.py` — tool definitions exposing
  HTTP-only surface to `localhost:8000`; tool executor with timeout
  + URL allowlist (only `/api/...` paths) + bytes-cap on responses
- `scripts/dogfood/persona_runner.py` — `run_persona(config, brief,
  client, log) -> RunResult` driving the LLM tool-use loop with
  step-budget + token-budget caps
- `scripts/dogfood/harness.py` — CLI entry: `python -m
  scripts.dogfood.harness --case <id> --persona <name> --model <id>
  --run-id <uuid>`
- `tests/dogfood/` — coverage for clients (mock HTTP), friction log
  (event schema), case brief (verdict tolerance edges), tools
  (allowlist + timeout), persona runner (mock LLM, mock tools), Opus
  guard (8 negative cases)

## V130 Principle B compliance (charter §workbench-first acceptance Q4)

- Tool surface is HTTP-only; no file/process/network tools beyond
  `http_get` + `http_post` against localhost:8000 allowlist
- Workbench mutating routes ARE callable (engineer-as-applier) but
  the persona system prompt (delivered in B.2) will forbid "AI told
  me to apply X" reasoning; B.1 enforces the structural prerequisite
  (HTTP-only surface, structured tool calls captured to friction log
  with rationale text per call so B.4 retro can grep violation
  patterns)
- The harness itself does NOT touch workbench mutating routes; it
  only wraps the persona's tool calls

## Multi-model API key surface

| Provider | Env var | Endpoint | Purpose |
|---|---|---|---|
| Anthropic (Sonnet 4.6) | `ANTHROPIC_API_KEY` | `api.anthropic.com/v1/messages` | persona reasoning |
| DeepSeek V4 Pro | `DEEPSEEK_API_KEY` (workbench reuses) | `api.deepseek.com/v1/chat/completions` | persona reasoning |
| gpt-5.4 via 86gs | `CODEX_RELAY_API_KEY` (or relay-internal env) | 86gs OpenAI-compat endpoint | persona reasoning |

Keys via env-var only; never logged; harness fingerprints with SHA-256
on startup (mirrors `factory.py` pattern). gpt-5.4 routing: the harness
calls the OpenAI-compat endpoint directly (NOT through `codex` CLI) —
this means a separate API key surface, documented in README.

## Four-question gate

| # | Question | Answer |
|---|---|---|
| Q1 | LLM offline → engineer can complete? | ✅ Harness itself doesn't modify workbench; workbench retains its own LLM-offline path (N6.5). Harness adds a `--workbench-llm-disabled` flag setting `LLM_PROVIDER=disabled` for the workbench subprocess so persona runs against an offline workbench |
| Q2 | Artifacts output? | ✅ Per run, three artifacts: `friction_log.jsonl` (structured events), `experience_report.md` (persona-authored, future B.2), `audit.zip` (workbench-produced, copied at run end). Persisted under `.planning/dogfood/runs/<run_id>/` |
| Q3 | TrustGate / completeness / audit explainable? | ✅ Each friction_log event carries `timestamp` + `event_type` + `payload` (URL, response_status, advisor_chunk_id if applicable, persona_rationale). Engineer can replay decision chain by reading the JSONL line-by-line |
| Q4 | AI advisory only (no mutating call)? | ✅ Tool executor allowlist is `/api/*` paths only; mutating routes call through the persona's structured tool_use, not via "AI advisor said" inference. Friction log retains `tool_use.rationale` text for B.4 grep on violation patterns |

## Verification

- All tests pass under `pytest tests/dogfood/`
- `python -m scripts.dogfood.harness --selftest` runs a mock-LLM
  smoke against a stubbed workbench (no real API key required) and
  exits 0 with a friction log written to a tmpdir
- Opus guard verified: 8 model-id strings tested
  (`claude-opus-4-7`, `claude-opus-4-7[1m]`, `OPUS-4`, etc.) all
  abort harness; non-Opus IDs pass
- HTTP allowlist verified: tool executor rejects URLs outside
  `localhost:8000/api/` (file://, http://evil.com, localhost:8000/
  without /api/ prefix)
- Bytes-cap verified: response >2 MiB truncated with explicit
  `truncated_at_bytes` marker in friction log
- Token budget verified: per-run cap stops persona loop with
  `budget_check` event in log (no silent overrun)

## Confidence

`high` — pure orchestration scaffold; no contract surface change;
no workbench code touched. New package isolated under `scripts/`;
new tests under `tests/dogfood/`. LLM client classes are thin
HTTP wrappers; verdict checker is closed-form tolerance comparison.

## Codex pre-merge review

Per charter: B.1 is "per Opus confidence" (orchestration, not
contract surface change). Confidence high; no Codex review.

## Notes

- Persona system prompt is INTENTIONALLY a stub in B.1 (placeholder:
  "You are a CFD engineer driving a 5-step workflow."). B.2 fills
  the real persona library with novice / experienced-Fluent / debug
  variants. This split lets B.1 ship a working harness without
  prejudicing B.2's persona language design.
- `scripts/smoke/dogfood_loop.py` is unrelated (M-AI-COPILOT
  classifier smoke replacing CFDJerry visual gate); name collision
  is benign — different scope, different consumers
- gpt-5.4 routing through OpenAI-compat endpoint (NOT `codex` CLI)
  because personas need raw chat-completion semantics with tool_use,
  not Codex CLI's wrapped invocation
- DeepSeek client implementation uses fresh code rather than
  importing workbench's `DeepSeekProvider` because workbench
  provider is async/streaming for chat-routes; persona tool-loop
  needs simple sync request/response

## References

- DEC-V61-162 · B-arc charter (parent)
- DEC-V61-118/119 · LLM provider abstraction (workbench-side; B.1
  intentionally does NOT extend this — persona-side providers live
  in `scripts/dogfood/llm_clients.py`)
- DEC-V61-132 · MUTATING_ROUTES contract (allowlist enforcement
  borrowed conceptually; B.1 doesn't change V132 itself)
