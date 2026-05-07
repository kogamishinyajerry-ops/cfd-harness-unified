# scripts/dogfood — B-Arc Multi-Model Subagent Dogfood Harness

Implements DEC-V61-162 (charter) + DEC-V61-163 (B.1 scaffold).

## What this is

Orchestration backbone for letting **non-Opus persona subagents** drive
the cfd-harness-unified workbench through its 5-step workflow on real
geometries. Captures structured friction logs for retro analysis.

Three persona model families (charter §rationale):

- **Sonnet 4.6** — Anthropic Messages API
- **DeepSeek V4 Pro** — DeepSeek's OpenAI-compatible chat-completions
- **gpt-5.4** — via 86gs codex-relay's OpenAI-compatible endpoint

**Hard rule**: NO Opus personas. `assert_non_opus()` aborts the harness
on any model id matching `opus`/`claude-opus`. This mitigates the
Opus-reads-Opus echo chamber risk (workbench's AI advisor was authored
by Opus; an Opus persona would trivially "agree" with advisor output).

## Layout

```
scripts/dogfood/
├── __init__.py
├── README.md           — this file
├── harness.py          — CLI entry: `python -m scripts.dogfood.harness --selftest`
├── persona_runner.py   — single-persona tool-use loop driver
├── llm_clients.py      — AnthropicClient + OpenAICompatClient + factory + Opus guard
├── workbench_tools.py  — http_get / http_post tools + URL allowlist + bytes-cap
├── friction_log.py     — JSONL writer with typed events
└── case_brief.py       — CaseBrief + Reference + check_verdict
```

## Quick start

### Selftest (no API keys required)

```bash
python -m scripts.dogfood.harness --selftest
```

Runs a scripted mock LLM against a stubbed workbench transport; verifies
that the friction log + persona runner + tool executor wire together
correctly. Exit 0 = pass.

### Production run (requires API keys + running workbench)

```bash
# 1) Start workbench (LLM offline path tested by passing LLM_PROVIDER=disabled)
LLM_PROVIDER=disabled python -m ui.backend.main &

# 2) Run a persona × case
python -m scripts.dogfood.harness \
    --case tests/dogfood/fixtures/selftest_case.json \
    --persona experienced_fluent \
    --family openai_compat \
    --model gpt-5.4 \
    --workbench-base-url http://localhost:8000
```

## Environment

| Provider | Env var | Notes |
|---|---|---|
| Anthropic (Sonnet 4.6) | `ANTHROPIC_API_KEY` | required for `--family anthropic` |
| DeepSeek | `DEEPSEEK_API_KEY` | reuses workbench's existing var |
| gpt-5.4 (86gs relay) | `CODEX_RELAY_API_KEY` | base URL via `DOGFOOD_GPT54_BASE_URL` (default `https://api.86gamestore.com/v1`) |

Keys are SHA-256-fingerprinted on client init, **never logged in
plaintext**.

## Friction log schema

One JSONL file per run at `.planning/dogfood/runs/<run_id>/friction_log.jsonl`.
Event types (`event_type` field):

- `run_start` / `run_end` — bracket each run
- `api_call` — workbench HTTP call (URL, status, ok, rationale)
- `advisor_query` — explicit advisor lookup (chunk_id, source)
- `tool_use` — every tool_use issued by the model (rationale captured)
- `decision` — persona-emitted reasoning step
- `drop` — persona declined to complete
- `verdict` — terminal: observed value + machine-checked pass/fail
- `error` — transport/LLM/budget failure
- `budget_check` — token or step cap hit

## V130 advisory-only enforcement

- Tool surface is HTTP-only against `localhost:8000/api/...` (URL
  allowlist enforced in `workbench_tools._resolve_path`).
- The persona system prompt forbids "AI told me to apply X"
  reasoning (B.2 will harden this).
- Each `tool_use` event captures `rationale` text so B.4 retro can
  grep for V130 violation patterns.

## Out of scope (B.1)

- Real persona system prompts (B.2)
- Real case fixtures (B.3) — only `selftest` brief shipped
- Multi-run batch orchestration (B.4)
- Targeted fixes from retro backlog (B.5)
- Kogami strategic retro (B.6)

## Related work

- `scripts/smoke/dogfood_loop.py` — UNRELATED. That's the M-AI-COPILOT
  classifier smoke (replaces the old "Awaiting CFDJerry visual smoke"
  human gate); it does not interact with this harness.
- `ui/backend/services/llm_provider/` — workbench-side LLM provider
  factory; B.1 intentionally does NOT extend this. Persona-side
  clients live here in `scripts/dogfood/llm_clients.py`.
